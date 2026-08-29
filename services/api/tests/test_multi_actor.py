from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import httpx

from app.config import Settings
from app.forecasting import DeterministicDeclarationForecastService
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PDF_CONTENT = b"%PDF-1.7\nBioLoop multi actor evidence\n%%EOF\n"


def app_for(tmp_path: Path):
    return create_app(
        Settings(
            db_path=tmp_path / "test.db",
            evidence_dir=tmp_path / "evidence",
            fixtures_dir=PROJECT_ROOT / "data" / "fixtures",
            factor_set_path=(
                PROJECT_ROOT
                / "data"
                / "factor_sets"
                / "illustrative-normalized-v1.json"
            ),
            web_origin="http://localhost:3000",
        )
    )


def actor(user_id: str, *, content_type: str | None = None) -> dict[str, str]:
    headers = {"X-Demo-User-ID": user_id}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def create_assigned_declaration(api: httpx.AsyncClient) -> tuple[dict, dict]:
    declaration_response = await api.post(
        "/api/v1/declarations",
        headers=actor("USER-PROD-001"),
        json={
            "producer_id": "PROD-001",
            "waste_type_id": "market_organic",
            "quantity_kg": "1500.00",
            "frequency": "hebdomadaire",
            "availability_date": "2026-09-01",
            "notes": "Gisement multi-acteurs de démonstration.",
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
    return declaration, proposal_response.json()


async def create_collected_lot(api: httpx.AsyncClient) -> tuple[dict, dict, dict]:
    declaration, proposal = await create_assigned_declaration(api)
    logistics_workspace = await api.get(
        "/api/v1/demo/workspace",
        headers=actor("USER-LOG-001"),
        params={"as_of": "2026-09-01"},
    )
    assert logistics_workspace.status_code == 200, logistics_workspace.text
    collection = logistics_workspace.json()["logistics_collections"][0]["collection"]

    evidence_response = await api.post(
        f"/api/v1/declarations/{declaration['id']}/evidence",
        headers=actor("USER-LOG-001", content_type="application/pdf"),
        params={
            "category": "bon_pesee",
            "original_filename": "bon-pesee-demo.pdf",
            "captured_at": "2026-09-01T08:00:00Z",
            "note": "Pièce logistique P2 de démonstration.",
        },
        content=PDF_CONTENT,
    )
    assert evidence_response.status_code == 201, evidence_response.text
    evidence = evidence_response.json()
    measurement_response = await api.post(
        f"/api/v1/declarations/{declaration['id']}/measurements",
        headers=actor("USER-LOG-001"),
        json={
            "quantity_kg": "1200.00",
            "unit": "kg",
            "method": "balance_mobile",
            "measured_at": "2026-09-01T09:30:00Z",
            "device_reference": "BAL-DEMO-01",
            "evidence_id": evidence["id"],
            "note": "Pesée P3 de démonstration.",
        },
    )
    assert measurement_response.status_code == 201, measurement_response.text
    measurement = measurement_response.json()
    confirmation = await api.post(
        f"/api/v1/demo/collections/{collection['id']}/confirm",
        headers=actor("USER-LOG-001"),
        json={"evidence_id": evidence["id"], "measurement_id": measurement["id"]},
    )
    assert confirmation.status_code == 200, confirmation.text
    lot_response = await api.post(
        f"/api/v1/declarations/{declaration['id']}/lots",
        headers=actor("USER-LOG-001"),
        json={
            "measurement_id": measurement["id"],
            "processing_unit_id": proposal["selected_unit"]["id"],
            "evidence_ids": [evidence["id"]],
        },
    )
    assert lot_response.status_code == 201, lot_response.text
    return declaration, collection, lot_response.json()


def test_multi_actor_journey_notifications_and_audit(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration, collection, lot = await create_collected_lot(api)

            unit_workspace = await api.get(
                "/api/v1/demo/workspace",
                headers=actor("USER-UNIT-001"),
                params={"as_of": "2026-09-01"},
            )
            assert unit_workspace.status_code == 200
            workspace = unit_workspace.json()
            assert workspace["incoming_lots"][0]["lot"]["id"] == lot["id"]
            assert workspace["incoming_lots"][0]["compatibility"] is True
            assert workspace["notifications"][0]["event_type"] == "lot.incoming"
            projection = workspace["projections"][0]
            assert projection["version"] == "deterministic-declaration-cadence-v1"
            assert {period["period_days"] for period in projection["periods"]} == {7, 30}
            assert all(
                period["declared"]["result_proof_level"] == "P0"
                and period["measured_basis"]["basis_proof_level"] == "P3"
                for period in projection["periods"]
            )

            decision = await api.post(
                f"/api/v1/lots/{lot['id']}/decision",
                headers=actor("USER-UNIT-001"),
                json={"decision": "accepted", "reason": "", "note": "Lot reçu."},
            )
            assert decision.status_code == 201, decision.text
            assert decision.json()["actor_user_id"] == "USER-UNIT-001"

            producer_workspace = await api.get(
                "/api/v1/demo/workspace", headers=actor("USER-PROD-001")
            )
            producer_payload = producer_workspace.json()
            assert producer_payload["producer_declarations"][0]["declaration"]["id"] == declaration["id"]
            assert producer_payload["producer_declarations"][0]["lot_status"] == "accepted"
            producer_events = {
                item["event_type"] for item in producer_payload["notifications"]
            }
            assert {"proposal.available", "lot.decision_recorded"}.issubset(producer_events)

            controller_workspace = await api.get(
                "/api/v1/demo/workspace", headers=actor("USER-CONTROL-001")
            )
            assert controller_workspace.json()["pending_controls"][0]["lot"]["id"] == lot["id"]
            controller_events = {
                item["event_type"]
                for item in controller_workspace.json()["notifications"]
            }
            assert "control.required" in controller_events

            audit = await api.get(
                "/api/v1/demo/audit",
                headers=actor("USER-COORD-001"),
                params={"organization_id": "ORG-LOG-001", "limit": 50},
            )
            assert audit.status_code == 200
            assert audit.json()
            assert all(item["actor_organization_id"] == "ORG-LOG-001" for item in audit.json())
            assert collection["status"] == "assigned"

    asyncio.run(scenario())


def test_horizontal_access_is_denied_between_producers(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration, _ = await create_assigned_declaration(api)
            own_list = await api.get(
                "/api/v1/declarations", headers=actor("USER-PROD-002")
            )
            foreign_timeline = await api.get(
                f"/api/v1/declarations/{declaration['id']}/timeline",
                headers=actor("USER-PROD-002"),
            )
            impersonated_site = await api.post(
                "/api/v1/declarations",
                headers=actor("USER-PROD-002"),
                json={
                    "producer_id": "PROD-001",
                    "waste_type_id": "market_organic",
                    "quantity_kg": "100",
                    "frequency": "ponctuelle",
                    "availability_date": "2026-09-02",
                },
            )
            assert own_list.status_code == 200
            assert own_list.json() == []
            assert foreign_timeline.status_code == 403
            assert impersonated_site.status_code == 403

    asyncio.run(scenario())


def test_role_boundaries_and_explicit_p4_event(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            _, _, lot = await create_collected_lot(api)
            logistics_decision = await api.post(
                f"/api/v1/lots/{lot['id']}/decision",
                headers=actor("USER-LOG-001"),
                json={"decision": "accepted", "reason": "", "note": "Interdit."},
            )
            unauthorized_verifications = []
            for user_id in ("USER-PROD-001", "USER-LOG-001", "USER-UNIT-001"):
                unauthorized_verifications.append(
                    await api.post(
                        "/api/v1/demo/verifications",
                        headers=actor(user_id),
                        json={
                            "subject_type": "waste_lot",
                            "subject_id": lot["id"],
                            "outcome": "verified",
                            "note": "Tentative non autorisée.",
                            "idempotency_key": f"{user_id.lower()}-cannot-verify",
                        },
                    )
                )
            payload = {
                "subject_type": "waste_lot",
                "subject_id": lot["id"],
                "outcome": "verified",
                "note": "Contrôle terrain explicite de démonstration.",
                "idempotency_key": "control-lot-verified-001",
            }
            verified = await api.post(
                "/api/v1/demo/verifications",
                headers=actor("USER-CONTROL-001"),
                json=payload,
            )
            repeated = await api.post(
                "/api/v1/demo/verifications",
                headers=actor("USER-CONTROL-001"),
                json=payload,
            )
            conflicting_retry = await api.post(
                "/api/v1/demo/verifications",
                headers=actor("USER-CONTROL-001"),
                json={**payload, "outcome": "non_conform"},
            )
            assert logistics_decision.status_code == 403
            assert all(response.status_code == 403 for response in unauthorized_verifications)
            assert verified.status_code == 201, verified.text
            assert verified.json()["proof_level"] == "P4"
            assert verified.json()["actor_user_id"] == "USER-CONTROL-001"
            assert repeated.json()["id"] == verified.json()["id"]
            assert conflicting_retry.status_code == 409

    asyncio.run(scenario())


def test_notifications_are_idempotent_and_demo_identity_is_explicit(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration, _ = await create_assigned_declaration(api)
            repeated = await api.post(
                f"/api/v1/declarations/{declaration['id']}/proposal",
                headers=actor("USER-PROD-001"),
                json={"processing_unit_id": "UNIT-001"},
            )
            assert repeated.status_code == 200
            logistics_notifications = await api.get(
                "/api/v1/demo/notifications", headers=actor("USER-LOG-001")
            )
            assert logistics_notifications.status_code == 200
            assignments = [
                item
                for item in logistics_notifications.json()
                if item["event_type"] == "collection.assigned"
            ]
            assert len(assignments) == 1
            missing_actor = await api.get("/api/v1/demo/workspace")
            unknown_actor = await api.get(
                "/api/v1/demo/workspace", headers=actor("USER-UNKNOWN-001")
            )
            malformed_identifier = await api.get(
                "/api/v1/lots/not-valid",
                headers=actor("USER-COORD-001"),
            )
            assert missing_actor.status_code == 401
            assert unknown_actor.status_code == 401
            assert malformed_identifier.status_code == 422

    asyncio.run(scenario())


def test_deterministic_forecast_repeats_exactly() -> None:
    from app.models import WasteDeclaration

    declaration = WasteDeclaration(
        id="DECL-DETERMINISTIC",
        owner_organization_id="ORG-PROD-ABOBO",
        producer_id="PROD-001",
        producer_name="Producteur fictif",
        producer_locality="Abobo",
        waste_type_id="market_organic",
        quantity_kg="100",
        frequency="hebdomadaire",
        availability_date="2026-09-01",
        notes="",
        latitude=5.4,
        longitude=-4.0,
        created_at="2026-08-29T00:00:00Z",
        field_evidence={},
    )
    service = DeterministicDeclarationForecastService()
    first = service.project_unit_intake(
        "UNIT-001", [(declaration, None)], as_of=date(2026, 9, 1)
    )
    second = service.project_unit_intake(
        "UNIT-001", [(declaration, None)], as_of=date(2026, 9, 1)
    )
    assert first == second
    assert first.periods[0].declared.value_kg == 100
    assert first.periods[1].declared.value_kg == 500
    assert first.periods[0].declared.result_proof_level.value == "P0"
