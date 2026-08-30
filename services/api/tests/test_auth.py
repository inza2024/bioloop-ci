from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.config import Settings
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def app_for(tmp_path: Path, *, secure_cookie: bool = False):
    return create_app(
        Settings(
            db_path=tmp_path / "auth.db",
            evidence_dir=tmp_path / "evidence",
            fixtures_dir=PROJECT_ROOT / "data" / "fixtures",
            factor_set_path=PROJECT_ROOT / "data" / "factor_sets" / "illustrative-normalized-v1.json",
            web_origin="http://localhost:3000",
            cookie_secure=secure_cookie,
        )
    )


async def csrf_headers(client: httpx.AsyncClient) -> dict[str, str]:
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    return {"X-CSRF-Token": token, "Origin": "http://localhost:3000"}


async def register(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    email: str,
    organization_type: str = "producer",
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "display_name": "Awa Pilote",
            "email": email,
            "password": "BioLoopPilot2026",
            "organization_name": f"Organisation {email}",
            "organization_type": organization_type,
        },
    )


def test_producer_registration_session_login_and_logout(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await csrf_headers(client)
            created = await register(client, headers, email="awa@example.test")
            assert created.status_code == 201, created.text
            assert created.json()["active_membership"]["status"] == "active"
            assert created.json()["portal_path"] == "/portal/producer"
            cookie = created.headers["set-cookie"]
            assert "HttpOnly" in cookie and "SameSite=lax" in cookie
            assert "bioloop_session=" in cookie

            me = await client.get("/api/v1/auth/me")
            assert me.status_code == 200
            assert me.json()["actor"]["authenticated_for_pilot"] is True
            assert me.json()["actor"]["authenticated_for_production"] is False

            no_csrf = await client.post("/api/v1/auth/logout")
            assert no_csrf.status_code == 403
            logged_out = await client.post("/api/v1/auth/logout", headers=headers)
            assert logged_out.status_code == 200
            assert (await client.get("/api/v1/auth/me")).status_code == 401

            logged_in = await client.post(
                "/api/v1/auth/login",
                headers=headers,
                json={"email": "AWA@example.test", "password": "BioLoopPilot2026"},
            )
            assert logged_in.status_code == 200
            assert logged_in.json()["user"]["email"] == "awa@example.test"

        with sqlite3.connect(tmp_path / "auth.db") as connection:
            password_hash = connection.execute(
                "SELECT password_hash FROM pilot_users WHERE email_normalized = ?",
                ("awa@example.test",),
            ).fetchone()[0]
            stored_token_hash = connection.execute(
                "SELECT token_hash FROM pilot_sessions ORDER BY created_at DESC LIMIT 1"
            ).fetchone()[0]
        assert password_hash.startswith("$argon2id$")
        assert len(stored_token_hash) == 64
        assert "BioLoopPilot2026" not in password_hash

    asyncio.run(scenario())


def test_wrong_password_expired_and_revoked_sessions_are_rejected(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await csrf_headers(client)
            assert (await register(client, headers, email="expiry@example.test")).status_code == 201
            assert (await client.post("/api/v1/auth/logout", headers=headers)).status_code == 200
            wrong = await client.post(
                "/api/v1/auth/login",
                headers=headers,
                json={"email": "expiry@example.test", "password": "WrongPassword2026"},
            )
            assert wrong.status_code == 401
            assert wrong.json()["detail"] == "Email ou mot de passe incorrect."
            good = await client.post(
                "/api/v1/auth/login",
                headers=headers,
                json={"email": "expiry@example.test", "password": "BioLoopPilot2026"},
            )
            assert good.status_code == 200
            with sqlite3.connect(tmp_path / "auth.db") as connection:
                connection.execute(
                    "UPDATE pilot_sessions SET expires_at = ? WHERE revoked_at IS NULL",
                    ((datetime.now(UTC) - timedelta(minutes=1)).isoformat(),),
                )
            assert (await client.get("/api/v1/auth/me")).status_code == 401

    asyncio.run(scenario())


def test_sensitive_self_registration_denied_and_operational_roles_pending(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        for organization_type in ("field_controller", "bioloop_coordinator"):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                headers = await csrf_headers(client)
                denied = await register(
                    client,
                    headers,
                    email=f"{organization_type}@example.test",
                    organization_type=organization_type,
                )
                assert denied.status_code == 403
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await csrf_headers(client)
            pending = await register(
                client,
                headers,
                email="logistics@example.test",
                organization_type="logistician",
            )
            assert pending.status_code == 201
            assert pending.json()["active_membership"]["status"] == "pending"
            forbidden = await client.post(
                "/api/v1/declarations",
                headers=headers,
                json={
                    "producer_id": "PROD-001",
                    "waste_type_id": "market_organic",
                    "quantity_kg": 100,
                    "frequency": "ponctuelle",
                    "availability_date": "2026-09-01",
                },
            )
            assert forbidden.status_code == 403

    asyncio.run(scenario())


def test_organization_isolation_and_idempotent_mobile_sync(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = app_for(tmp_path)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as first:
            first_headers = await csrf_headers(first)
            first_auth = await register(first, first_headers, email="first@example.test")
            assert first_auth.status_code == 201
            payload = {
                "producer_id": "PROD-001",
                "waste_type_id": "market_organic",
                "quantity_kg": "450",
                "frequency": "hebdomadaire",
                "availability_date": "2026-09-01",
                "notes": "Synchronisation mobile testée.",
                "client_idempotency_key": "offline:fixed-sync-key-001",
            }
            original = await first.post("/api/v1/declarations", headers=first_headers, json=payload)
            duplicate = await first.post("/api/v1/declarations", headers=first_headers, json=payload)
            assert original.status_code == duplicate.status_code == 201
            assert original.json()["id"] == duplicate.json()["id"]
            assert len((await first.get("/api/v1/declarations")).json()) == 1

            async with httpx.AsyncClient(transport=transport, base_url="http://test") as second:
                second_headers = await csrf_headers(second)
                assert (await register(second, second_headers, email="second@example.test")).status_code == 201
                assert (await second.get("/api/v1/declarations")).json() == []
                foreign = await second.get(
                    f"/api/v1/declarations/{original.json()['id']}/timeline"
                )
                assert foreign.status_code == 403

    asyncio.run(scenario())


def test_secure_cookie_flag_and_audit_redaction(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path, secure_cookie=True))
        async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
            headers = await csrf_headers(client)
            response = await register(client, headers, email="secure@example.test")
            assert response.status_code == 201
            assert "Secure" in response.headers["set-cookie"]
        with sqlite3.connect(tmp_path / "auth.db") as connection:
            serialized = " ".join(
                row[0] for row in connection.execute("SELECT payload FROM audit_events")
            )
        assert "secure@example.test" not in serialized
        assert "BioLoopPilot2026" not in serialized
        assert "bioloop_session" not in serialized

    asyncio.run(scenario())


def test_login_failure_counter_rate_limits_without_revealing_account_state(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await csrf_headers(client)
            assert (await register(client, headers, email="rate@example.test")).status_code == 201
            assert (await client.post("/api/v1/auth/logout", headers=headers)).status_code == 200
            for _ in range(5):
                failed = await client.post(
                    "/api/v1/auth/login",
                    headers=headers,
                    json={"email": "rate@example.test", "password": "WrongPassword2026"},
                )
                assert failed.status_code == 401
                assert failed.json()["detail"] == "Email ou mot de passe incorrect."
            limited = await client.post(
                "/api/v1/auth/login",
                headers=headers,
                json={"email": "rate@example.test", "password": "BioLoopPilot2026"},
            )
            assert limited.status_code == 429

    asyncio.run(scenario())


def test_multiple_memberships_can_switch_but_cannot_open_another_role_portal(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await csrf_headers(client)
            registration = await register(client, headers, email="multi@example.test")
            user_id = registration.json()["user"]["id"]
            with sqlite3.connect(tmp_path / "auth.db") as connection:
                connection.execute(
                    """
                    INSERT INTO pilot_organizations
                        (id, name, kind, approval_status, is_demo, created_at)
                    VALUES ('PORG-AAAAAAAAAAAAAAAA', 'Client secondaire', 'client',
                            'active', 0, '2026-08-30T00:00:00+00:00')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO pilot_memberships
                        (id, user_id, organization_id, role, status, created_at, approved_at)
                    VALUES ('PMEM-AAAAAAAAAAAAAAAA', ?, 'PORG-AAAAAAAAAAAAAAAA',
                            'client_farmer', 'active', '2026-08-30T00:00:00+00:00',
                            '2026-08-30T00:00:00+00:00')
                    """,
                    (user_id,),
                )
            before = await client.get("/api/v1/auth/portal/client_farmer")
            assert before.status_code == 403
            switched = await client.post(
                "/api/v1/auth/memberships/PMEM-AAAAAAAAAAAAAAAA/activate",
                headers=headers,
            )
            assert switched.status_code == 200
            assert switched.json()["portal_path"] == "/portal/client_farmer"
            assert (await client.get("/api/v1/auth/portal/client_farmer")).status_code == 200
            assert (await client.get("/api/v1/auth/portal/producer")).status_code == 403

    asyncio.run(scenario())


def test_correlation_security_headers_and_disableable_demo_mode(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "auth.db",
        evidence_dir=tmp_path / "evidence",
        fixtures_dir=PROJECT_ROOT / "data" / "fixtures",
        factor_set_path=PROJECT_ROOT / "data" / "factor_sets" / "illustrative-normalized-v1.json",
        web_origin="http://localhost:3000",
        demo_identities_enabled=False,
    )

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=create_app(settings))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            health = await client.get(
                "/health", headers={"X-Correlation-ID": "pilot-check-123"}
            )
            assert health.headers["X-Correlation-ID"] == "pilot-check-123"
            assert health.headers["X-Content-Type-Options"] == "nosniff"
            assert health.headers["X-Frame-Options"] == "DENY"
            assert (await client.get("/api/v1/demo/actors")).status_code == 404
            assert (await client.get("/api/v1/declarations")).status_code == 401

    asyncio.run(scenario())
