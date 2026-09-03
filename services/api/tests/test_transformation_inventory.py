from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PDF_CONTENT = b"%PDF-1.7\nBioLoop tranche 05 evidence\n%%EOF\n"


def app_for(tmp_path: Path):
    return create_app(
        Settings(
            db_path=tmp_path / "test.db",
            evidence_dir=tmp_path / "evidence",
            fixtures_dir=PROJECT_ROOT / "data" / "fixtures",
            factor_set_path=PROJECT_ROOT / "data" / "factor_sets" / "illustrative-normalized-v1.json",
            web_origin="http://localhost:3000",
        )
    )


def actor(user_id: str, *, content_type: str | None = None) -> dict[str, str]:
    headers = {"X-Demo-User-ID": user_id}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def csrf_headers(client: httpx.AsyncClient) -> dict[str, str]:
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    return {"X-CSRF-Token": token, "Origin": "http://localhost:3000"}


async def register(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    email: str,
    organization_type: str,
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "display_name": f"Pilote {organization_type}",
            "email": email,
            "password": "BioLoopPilot2026",
            "organization_name": f"Organisation {organization_type}",
            "organization_type": organization_type,
        },
    )


async def create_collected_lot(api: httpx.AsyncClient) -> dict:
    declaration_response = await api.post(
        "/api/v1/declarations",
        headers=actor("USER-PROD-001"),
        json={
            "producer_id": "PROD-001",
            "waste_type_id": "market_organic",
            "quantity_kg": "1500",
            "frequency": "hebdomadaire",
            "availability_date": "2026-09-01",
            "notes": "Intrant de transformation tranche 05.",
        },
    )
    assert declaration_response.status_code == 201, declaration_response.text
    declaration = declaration_response.json()
    proposal_response = await api.post(
        f"/api/v1/declarations/{declaration['id']}/proposal",
        headers=actor("USER-PROD-001"),
        json={"processing_unit_id": "UNIT-001"},
    )
    assert proposal_response.status_code == 200, proposal_response.text
    workspace = (
        await api.get("/api/v1/demo/workspace", headers=actor("USER-LOG-001"))
    ).json()
    collection = workspace["logistics_collections"][0]["collection"]
    evidence_response = await api.post(
        f"/api/v1/declarations/{declaration['id']}/evidence",
        headers=actor("USER-LOG-001", content_type="application/pdf"),
        params={
            "category": "bon_pesee",
            "original_filename": "transformation-source.pdf",
            "captured_at": "2026-09-01T08:00:00Z",
            "note": "Pièce P2 de l’intrant.",
        },
        content=PDF_CONTENT,
    )
    assert evidence_response.status_code == 201, evidence_response.text
    evidence = evidence_response.json()
    measurement_response = await api.post(
        f"/api/v1/declarations/{declaration['id']}/measurements",
        headers=actor("USER-LOG-001"),
        json={
            "quantity_kg": "1200",
            "unit": "kg",
            "method": "balance_mobile",
            "measured_at": "2026-09-01T09:00:00Z",
            "device_reference": "BAL-TRANCHE-05",
            "evidence_id": evidence["id"],
            "note": "Pesée P3 de l’intrant.",
        },
    )
    assert measurement_response.status_code == 201, measurement_response.text
    measurement = measurement_response.json()
    confirmed = await api.post(
        f"/api/v1/demo/collections/{collection['id']}/confirm",
        headers=actor("USER-LOG-001"),
        json={"evidence_id": evidence["id"], "measurement_id": measurement["id"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    lot_response = await api.post(
        f"/api/v1/declarations/{declaration['id']}/lots",
        headers=actor("USER-LOG-001"),
        json={
            "measurement_id": measurement["id"],
            "processing_unit_id": "UNIT-001",
            "evidence_ids": [evidence["id"]],
        },
    )
    assert lot_response.status_code == 201, lot_response.text
    return {
        "declaration": declaration,
        "collection": collection,
        "evidence": evidence,
        "measurement": measurement,
        "lot": lot_response.json(),
    }


async def create_transformation_and_products(api: httpx.AsyncClient) -> tuple[dict, list[dict], dict]:
    chain = await create_collected_lot(api)
    lot = chain["lot"]
    accepted = await api.post(
        f"/api/v1/lots/{lot['id']}/decision",
        headers=actor("USER-UNIT-001"),
        json={"decision": "accepted", "reason": "", "note": "Intrant accepté."},
    )
    assert accepted.status_code == 201, accepted.text
    transformation_response = await api.post(
        "/api/v1/transformations",
        headers=actor("USER-UNIT-001"),
        json={
            "processing_unit_id": "UNIT-001",
            "process": "Méthanisation pilote — procédé déclaré",
            "started_at": "2026-09-02T08:00:00Z",
            "inputs": [
                {
                    "lot_id": lot["id"],
                    "measured_quantity": "1180",
                    "unit": "kg",
                    "measurement_method": "balance_plateforme",
                    "measured_at": "2026-09-02T07:45:00Z",
                    "evidence_ids": [chain["evidence"]["id"]],
                }
            ],
        },
    )
    assert transformation_response.status_code == 201, transformation_response.text
    transformation = transformation_response.json()
    outputs_response = await api.post(
        f"/api/v1/transformations/{transformation['id']}/outputs",
        headers=actor("USER-UNIT-001"),
        json={
            "outputs": [
                {
                    "category": "measured_biogas",
                    "quantity": "95",
                    "unit": "m3",
                    "measurement_method": "débitmètre opérateur",
                    "measured_at": "2026-09-03T08:00:00Z",
                    "location": "Anyama — stockage gaz pilote",
                },
                {
                    "category": "raw_digestate",
                    "quantity": "920",
                    "unit": "kg",
                    "measurement_method": "balance plateforme sortie",
                    "measured_at": "2026-09-03T08:15:00Z",
                    "location": "Anyama — zone quarantaine",
                },
            ]
        },
    )
    assert outputs_response.status_code == 201, outputs_response.text
    return transformation, outputs_response.json(), chain


def test_admin_approves_refuses_blocks_self_approval_and_hashes_invitation(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = app_for(tmp_path)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as signup:
            headers = await csrf_headers(signup)
            unit = await register(
                signup, headers, email="unit@example.test", organization_type="processing_unit"
            )
            assert unit.status_code == 201
            unit_membership = unit.json()["active_membership"]["id"]
            signup.cookies.clear()
            headers = await csrf_headers(signup)
            logistics = await register(
                signup, headers, email="log@example.test", organization_type="logistician"
            )
            assert logistics.status_code == 201
            logistics_membership = logistics.json()["active_membership"]["id"]

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as admin:
            pending = await admin.get(
                "/api/v1/admin/memberships/pending", headers=actor("USER-COORD-001")
            )
            assert pending.status_code == 200
            assert {item["id"] for item in pending.json()} == {
                unit_membership,
                logistics_membership,
            }
            approved = await admin.post(
                f"/api/v1/admin/memberships/{unit_membership}/decision",
                headers=actor("USER-COORD-001"),
                json={
                    "decision": "approved",
                    "reason": "Unité pilote revue.",
                    "processing_unit_id": "UNIT-001",
                },
            )
            refused = await admin.post(
                f"/api/v1/admin/memberships/{logistics_membership}/decision",
                headers=actor("USER-COORD-001"),
                json={"decision": "refused", "reason": "Dossier local incomplet."},
            )
            assert approved.status_code == 200, approved.text
            assert approved.json()["status"] == "active"
            assert refused.status_code == 200, refused.text
            assert refused.json()["status"] == "refused"

            with sqlite3.connect(tmp_path / "test.db") as connection:
                connection.execute(
                    "INSERT INTO pilot_users VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        "USER-COORD-001",
                        "Coordinateur test",
                        "coord@example.test",
                        "unused-hash",
                        "active",
                        "2026-09-02T00:00:00+00:00",
                    ),
                )
                connection.execute(
                    "INSERT INTO pilot_organizations (id, name, kind, approval_status, is_demo, created_at, site_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        "PORG-CCCCCCCCCCCCCCCC",
                        "Coordination attente",
                        "bioloop_coordinator",
                        "pending",
                        0,
                        "2026-09-02T00:00:00+00:00",
                        None,
                    ),
                )
                connection.execute(
                    "INSERT INTO pilot_memberships (id, user_id, organization_id, role, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        "PMEM-CCCCCCCCCCCCCCCC",
                        "USER-COORD-001",
                        "PORG-CCCCCCCCCCCCCCCC",
                        "bioloop_coordinator",
                        "pending",
                        "2026-09-02T00:00:00+00:00",
                    ),
                )
            self_approval = await admin.post(
                "/api/v1/admin/memberships/PMEM-CCCCCCCCCCCCCCCC/decision",
                headers=actor("USER-COORD-001"),
                json={"decision": "approved", "reason": "Interdit."},
            )
            assert self_approval.status_code == 403

            invitation = await admin.post(
                "/api/v1/admin/invitations",
                headers=actor("USER-COORD-001"),
                json={
                    "email": "controller@example.test",
                    "role": "field_controller",
                    "organization_name": "Contrôle pilote local",
                    "expires_in_hours": 24,
                },
            )
            assert invitation.status_code == 201, invitation.text
            raw_token = invitation.json()["token"]
            with sqlite3.connect(tmp_path / "test.db") as connection:
                stored = connection.execute(
                    "SELECT token_hash FROM pilot_role_invitations WHERE id = ?",
                    (invitation.json()["id"],),
                ).fetchone()[0]
            assert stored == hashlib.sha256(raw_token.encode()).hexdigest()
            assert raw_token not in stored

            sessions = await admin.get(
                "/api/v1/admin/sessions", headers=actor("USER-COORD-001")
            )
            assert sessions.status_code == 200
            assert len(sessions.json()) >= 1
            revoked_session = await admin.post(
                f"/api/v1/admin/sessions/{sessions.json()[0]['id']}/revoke",
                headers=actor("USER-COORD-001"),
                json={"reason": "Session pilote fermée par le coordinateur."},
            )
            assert revoked_session.status_code == 200
            revoked_membership = await admin.post(
                f"/api/v1/admin/memberships/{unit_membership}/revoke",
                headers=actor("USER-COORD-001"),
                json={"reason": "Accès unité retiré du pilote local."},
            )
            assert revoked_membership.status_code == 200

            forbidden = await admin.get(
                "/api/v1/admin/memberships/pending", headers=actor("USER-PROD-001")
            )
            assert forbidden.status_code == 403
            history = await admin.get(
                "/api/v1/admin/history", headers=actor("USER-COORD-001")
            )
            assert history.status_code == 200
            assert {item["action"] for item in history.json()} >= {
                "membership.decision",
                "invitation.created",
                "membership.revoked",
                "session.revoked",
            }

    asyncio.run(scenario())


def test_expired_controller_invitation_is_rejected(tmp_path: Path) -> None:
    async def scenario() -> None:
        app = app_for(tmp_path)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as member:
            headers = await csrf_headers(member)
            registered = await register(
                member, headers, email="controller@example.test", organization_type="producer"
            )
            assert registered.status_code == 201
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as admin:
                invitation = await admin.post(
                    "/api/v1/admin/invitations",
                    headers=actor("USER-COORD-001"),
                    json={
                        "email": "controller@example.test",
                        "role": "field_controller",
                        "organization_name": "Contrôle expiration",
                        "expires_in_hours": 1,
                    },
                )
            assert invitation.status_code == 201
            with sqlite3.connect(tmp_path / "test.db") as connection:
                connection.execute(
                    "UPDATE pilot_role_invitations SET expires_at = ? WHERE id = ?",
                    (
                        (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                        invitation.json()["id"],
                    ),
                )
            expired = await member.post(
                f"/api/v1/auth/invitations/{invitation.json()['token']}/accept",
                headers=headers,
            )
            assert expired.status_code == 409
            assert "expir" in expired.json()["detail"].lower()

    asyncio.run(scenario())


def test_transformation_requires_accepted_lot_and_outputs_are_explicit_measurements(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            chain = await create_collected_lot(api)
            lot = chain["lot"]
            payload = {
                "processing_unit_id": "UNIT-001",
                "process": "Méthanisation pilote déclarée",
                "started_at": "2026-09-02T08:00:00Z",
                "inputs": [
                    {
                        "lot_id": lot["id"],
                        "measured_quantity": "1180",
                        "unit": "kg",
                        "measurement_method": "balance_plateforme",
                        "measured_at": "2026-09-02T07:45:00Z",
                        "evidence_ids": [chain["evidence"]["id"]],
                    }
                ],
            }
            rejected = await api.post(
                "/api/v1/transformations",
                headers=actor("USER-UNIT-001"),
                json=payload,
            )
            assert rejected.status_code == 409
            assert (
                await api.post(
                    f"/api/v1/lots/{lot['id']}/decision",
                    headers=actor("USER-UNIT-001"),
                    json={"decision": "accepted", "reason": "", "note": "Accepté."},
                )
            ).status_code == 201
            created = await api.post(
                "/api/v1/transformations",
                headers=actor("USER-UNIT-001"),
                json=payload,
            )
            assert created.status_code == 201, created.text
            assert created.json()["output_product_ids"] == []
            assert created.json()["scientific_derivation"] is False
            missing_physical_quantity = await api.post(
                f"/api/v1/transformations/{created.json()['id']}/outputs",
                headers=actor("USER-UNIT-001"),
                json={
                    "outputs": [
                        {
                            "category": "measured_biogas",
                            "unit": "m3",
                            "measurement_method": "débitmètre",
                            "measured_at": "2026-09-03T08:00:00Z",
                            "location": "Anyama",
                        }
                    ]
                },
            )
            assert missing_physical_quantity.status_code == 422
            outputs = await api.post(
                f"/api/v1/transformations/{created.json()['id']}/outputs",
                headers=actor("USER-UNIT-001"),
                json={
                    "outputs": [
                        {
                            "category": "measured_biogas",
                            "quantity": "95",
                            "unit": "m3",
                            "measurement_method": "débitmètre opérateur",
                            "measured_at": "2026-09-03T08:00:00Z",
                            "location": "Anyama",
                        },
                        {
                            "category": "solid_fraction",
                            "quantity": "800",
                            "unit": "kg",
                            "measurement_method": "balance sortie",
                            "measured_at": "2026-09-03T08:10:00Z",
                            "location": "Anyama",
                        },
                    ]
                },
            )
            assert outputs.status_code == 201, outputs.text
            assert len(outputs.json()) == 2
            assert all(item["proof_level"] == "P3" for item in outputs.json())
            assert all(item["quality_status"] == "quarantine" for item in outputs.json())
            wrong_unit = await api.post(
                "/api/v1/transformations",
                headers=actor("USER-PROD-001"),
                json=payload,
            )
            assert wrong_unit.status_code == 403

    asyncio.run(scenario())


def test_release_visibility_reservation_idempotence_negative_stock_and_isolation(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            _, products, _ = await create_transformation_and_products(api)
            product = products[1]
            hidden = await api.get("/api/v1/products", headers=actor("USER-CLIENT-001"))
            assert hidden.status_code == 200
            assert hidden.json() == []
            quality = await api.post(
                f"/api/v1/products/{product['id']}/quality-tests",
                headers=actor("USER-CONTROL-001"),
                json={
                    "parameter": "Matière sèche — valeur de démonstration",
                    "value": "18.4",
                    "unit": "%",
                    "method": "méthode locale déclarée non accréditée",
                    "laboratory_or_actor": "Contrôle terrain Démo CI",
                    "document_reference": "RAPPORT-DEMO-P0-001",
                    "tested_at": "2026-09-03T10:00:00Z",
                },
            )
            assert quality.status_code == 201, quality.text
            assert quality.json()["proof_level"] == "P4"
            released = await api.post(
                f"/api/v1/products/{product['id']}/release",
                headers=actor("USER-CONTROL-001"),
                json={
                    "status": "released",
                    "note": "Libération interne P4 ; aucune certification P5.",
                },
            )
            assert released.status_code == 200, released.text
            assert released.json()["release_proof_level"] == "P4"
            visible = await api.get(
                "/api/v1/products",
                headers=actor("USER-CLIENT-001"),
                params={
                    "category": "raw_digestate",
                    "location": "Anyama",
                    "proof_level": "P3",
                },
            )
            assert [item["id"] for item in visible.json()] == [product["id"]]
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as foreign_unit:
                foreign_headers = await csrf_headers(foreign_unit)
                registration = await register(
                    foreign_unit,
                    foreign_headers,
                    email="foreign-unit@example.test",
                    organization_type="processing_unit",
                )
                assert registration.status_code == 201
                foreign_membership = registration.json()["active_membership"]["id"]
                approved_foreign = await api.post(
                    f"/api/v1/admin/memberships/{foreign_membership}/decision",
                    headers=actor("USER-COORD-001"),
                    json={
                        "decision": "approved",
                        "reason": "Seconde unité créée pour vérifier l'isolation.",
                        "processing_unit_id": "UNIT-002",
                    },
                )
                assert approved_foreign.status_code == 200
                other_unit_products = await foreign_unit.get("/api/v1/products")
                assert other_unit_products.status_code == 200
                assert other_unit_products.json() == []
                foreign_adjustment = await foreign_unit.post(
                    f"/api/v1/products/{product['id']}/inventory-adjustments",
                    headers=foreign_headers,
                    json={
                        "quantity_delta": "1",
                        "unit": "kg",
                        "reason": "Tentative depuis une autre organisation.",
                        "idempotency_key": "foreign-unit-adjustment-001",
                    },
                )
                assert foreign_adjustment.status_code == 403
            reservation_payload = {
                "quantity": "100",
                "unit": "kg",
                "idempotency_key": "client-reservation-fixed-001",
            }
            first = await api.post(
                f"/api/v1/products/{product['id']}/reservations",
                headers=actor("USER-CLIENT-001"),
                json=reservation_payload,
            )
            duplicate = await api.post(
                f"/api/v1/products/{product['id']}/reservations",
                headers=actor("USER-CLIENT-001"),
                json=reservation_payload,
            )
            assert first.status_code == duplicate.status_code == 201
            assert first.json()["id"] == duplicate.json()["id"]
            after = await api.get("/api/v1/products", headers=actor("USER-CLIENT-001"))
            assert after.json()[0]["available_quantity"] == "820"
            negative = await api.post(
                f"/api/v1/products/{product['id']}/inventory-adjustments",
                headers=actor("USER-UNIT-001"),
                json={
                    "quantity_delta": "-900",
                    "unit": "kg",
                    "reason": "Ajustement impossible testé.",
                    "idempotency_key": "negative-stock-attempt-001",
                },
            )
            assert negative.status_code == 409
            foreign_cancel = await api.post(
                f"/api/v1/reservations/{first.json()['id']}/cancel",
                headers=actor("USER-PROD-001"),
            )
            assert foreign_cancel.status_code == 403
            cancelled = await api.post(
                f"/api/v1/reservations/{first.json()['id']}/cancel",
                headers=actor("USER-CLIENT-001"),
            )
            assert cancelled.status_code == 200
            restored = await api.get("/api/v1/products", headers=actor("USER-CLIENT-001"))
            assert restored.json()[0]["available_quantity"] == "920"

            movements = await api.get(
                f"/api/v1/products/{product['id']}/inventory-movements",
                headers=actor("USER-CLIENT-001"),
            )
            reservation_movements = [
                item for item in movements.json()
                if item["movement_type"] in {"reservation", "cancellation"}
            ]
            assert {item["provenance"] for item in reservation_movements} == {"declared"}
            assert {item["proof_level"] for item in reservation_movements} == {"P1"}

            with sqlite3.connect(tmp_path / "test.db") as connection:
                movement_id = connection.execute(
                    "SELECT id FROM inventory_movements LIMIT 1"
                ).fetchone()[0]
                with pytest.raises(sqlite3.IntegrityError):
                    connection.execute(
                        "UPDATE inventory_movements SET reason = 'silencieux' WHERE id = ?",
                        (movement_id,),
                    )

    asyncio.run(scenario())


def test_complete_provenance_analytics_and_additive_migration(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE legacy_slice_marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO legacy_slice_marker VALUES ('preserved')")

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            transformation, products, chain = await create_transformation_and_products(api)
            product = products[0]
            quality = await api.post(
                f"/api/v1/products/{product['id']}/quality-tests",
                headers=actor("USER-CONTROL-001"),
                json={
                    "parameter": "Composition gaz déclarée",
                    "value": "non certifiée",
                    "unit": "texte",
                    "method": "contrôle documentaire local",
                    "laboratory_or_actor": "Contrôle terrain Démo CI",
                    "tested_at": "2026-09-03T10:00:00Z",
                },
            )
            assert quality.status_code == 201
            assert (
                await api.post(
                    f"/api/v1/products/{product['id']}/release",
                    headers=actor("USER-CONTROL-001"),
                    json={"status": "released", "note": "Libération P4 locale seulement."},
                )
            ).status_code == 200
            reservation = await api.post(
                f"/api/v1/products/{product['id']}/reservations",
                headers=actor("USER-CLIENT-001"),
                json={
                    "quantity": "10",
                    "unit": "m3",
                    "idempotency_key": "provenance-reservation-001",
                },
            )
            assert reservation.status_code == 201
            provenance = await api.get(
                f"/api/v1/products/{product['id']}/provenance",
                headers=actor("USER-CLIENT-001"),
            )
            assert provenance.status_code == 200, provenance.text
            payload = provenance.json()
            assert payload["chain"] == [
                "declaration",
                "evidence",
                "measurement",
                "collection",
                "input_lot",
                "transformation",
                "product_batch",
                "quality_control",
                "inventory",
                "reservation",
            ]
            assert payload["declarations_to_inputs"][0]["declaration_id"] == chain["declaration"]["id"]
            assert payload["transformation"]["id"] == transformation["id"]
            assert payload["quality_controls"][0]["proof_level"] == "P4"
            assert payload["reservations"][0]["id"] == reservation.json()["id"]
            analytics = await api.get(
                "/api/v1/analytics/transformation-dataset",
                headers=actor("USER-COORD-001"),
            )
            assert analytics.status_code == 200
            assert analytics.json()["schema_version"] == "transformation-analytics-v1"
            assert analytics.json()["training_authorized"] is False
            assert analytics.json()["external_llm_used"] is False
            assert analytics.json()["rows"]

    asyncio.run(scenario())

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert connection.execute("SELECT value FROM legacy_slice_marker").fetchone()[0] == "preserved"
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0005_transformation_inventory"
    assert {
        "pilot_admin_actions",
        "transformation_runs",
        "transformation_inputs",
        "product_batches",
        "product_quality_tests",
        "product_release_events",
        "inventory_movements",
        "customer_reservations",
    }.issubset(tables)
