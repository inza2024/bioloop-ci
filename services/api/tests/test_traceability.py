from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from pathlib import Path

import httpx

from app.config import Settings
from app.evidence import MAX_EVIDENCE_BYTES
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PDF_CONTENT = b"%PDF-1.7\nBioLoop evidence demo\n%%EOF\n"


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


async def create_declaration(
    api: httpx.AsyncClient,
    *,
    producer_id: str = "PROD-001",
    waste_type_id: str = "market_organic",
    quantity_kg: str = "1500.00",
) -> dict:
    response = await api.post(
        "/api/v1/declarations",
        json={
            "producer_id": producer_id,
            "waste_type_id": waste_type_id,
            "quantity_kg": quantity_kg,
            "frequency": "hebdomadaire",
            "availability_date": "2026-09-01",
            "notes": "Déclaration de test.",
        },
    )
    assert response.status_code == 201
    return response.json()


async def upload_pdf(api: httpx.AsyncClient, declaration_id: str) -> dict:
    response = await api.post(
        f"/api/v1/declarations/{declaration_id}/evidence",
        params={
            "category": "bon_pesee",
            "original_filename": "bon-pesee.pdf",
            "captured_at": "2026-09-01T08:00:00Z",
            "note": "Document fourni pour la démonstration.",
        },
        content=PDF_CONTENT,
        headers={"Content-Type": "application/pdf"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_measurement_record(
    api: httpx.AsyncClient,
    declaration_id: str,
    *,
    quantity_kg: str = "1200.00",
    evidence_id: str | None = None,
    supersedes_measurement_id: str | None = None,
) -> dict:
    response = await api.post(
        f"/api/v1/declarations/{declaration_id}/measurements",
        json={
            "quantity_kg": quantity_kg,
            "unit": "kg",
            "method": "balance_mobile",
            "measured_at": "2026-09-01T09:30:00Z",
            "device_reference": "BAL-DEMO-01",
            "evidence_id": evidence_id,
            "supersedes_measurement_id": supersedes_measurement_id,
            "note": "Pesée saisie pour le test.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_valid_evidence_is_p2_hashed_and_stored_under_server_name(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api)
            evidence = await upload_pdf(api, declaration["id"])

            assert evidence["proof_level"] == "P2"
            assert evidence["provenance"] == "documented"
            assert evidence["original_filename"] == "bon-pesee.pdf"
            assert evidence["sha256"] == hashlib.sha256(PDF_CONTENT).hexdigest()
            assert evidence["size_bytes"] == len(PDF_CONTENT)
            stored = list((tmp_path / "evidence").iterdir())
            assert len(stored) == 1
            assert stored[0].name.startswith("EVID-")
            assert stored[0].name != evidence["original_filename"]

    asyncio.run(scenario())


def test_oversized_evidence_is_rejected_without_partial_file(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api)
            response = await api.post(
                f"/api/v1/declarations/{declaration['id']}/evidence",
                params={
                    "category": "photo_gisement",
                    "original_filename": "preuve.png",
                },
                content=b"\x89PNG\r\n\x1a\n" + b"0" * MAX_EVIDENCE_BYTES,
                headers={"Content-Type": "image/png"},
            )
            assert response.status_code == 413
            assert list((tmp_path / "evidence").iterdir()) == []

    asyncio.run(scenario())


def test_disallowed_type_and_mismatched_extension_are_rejected(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api)
            text_response = await api.post(
                f"/api/v1/declarations/{declaration['id']}/evidence",
                params={"category": "autre", "original_filename": "preuve.txt"},
                content=b"not allowed",
                headers={"Content-Type": "text/plain"},
            )
            mismatch_response = await api.post(
                f"/api/v1/declarations/{declaration['id']}/evidence",
                params={"category": "autre", "original_filename": "preuve.jpg"},
                content=PDF_CONTENT,
                headers={"Content-Type": "application/pdf"},
            )
            assert text_response.status_code == 422
            assert mismatch_response.status_code == 422

    asyncio.run(scenario())


def test_path_traversal_filename_is_rejected(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api)
            response = await api.post(
                f"/api/v1/declarations/{declaration['id']}/evidence",
                params={
                    "category": "document_accompagnement",
                    "original_filename": "../../outside.pdf",
                },
                content=PDF_CONTENT,
                headers={"Content-Type": "application/pdf"},
            )
            assert response.status_code == 422
            assert not (tmp_path / "outside.pdf").exists()
            assert list((tmp_path / "evidence").iterdir()) == []

    asyncio.run(scenario())


def test_measurement_is_p3_and_invalid_quantity_is_rejected(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api)
            evidence = await upload_pdf(api, declaration["id"])
            measurement = await create_measurement_record(
                api, declaration["id"], evidence_id=evidence["id"]
            )
            invalid = await api.post(
                f"/api/v1/declarations/{declaration['id']}/measurements",
                json={
                    "quantity_kg": 0,
                    "unit": "kg",
                    "method": "balance_mobile",
                    "measured_at": "2026-09-01T09:30:00Z",
                },
            )
            assert measurement["proof_level"] == "P3"
            assert measurement["provenance"] == "measured"
            assert measurement["unit"] == "kg"
            assert invalid.status_code == 422

    asyncio.run(scenario())


def test_measurement_correction_creates_a_new_immutable_record(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api)
            first = await create_measurement_record(api, declaration["id"], quantity_kg="1200")
            correction = await create_measurement_record(
                api,
                declaration["id"],
                quantity_kg="1195",
                supersedes_measurement_id=first["id"],
            )
            listed = (
                await api.get(f"/api/v1/declarations/{declaration['id']}/measurements")
            ).json()

            assert correction["id"] != first["id"]
            assert correction["supersedes_measurement_id"] == first["id"]
            assert len(listed) == 2
            assert listed[0]["quantity_kg"] == "1200"
            assert listed[1]["quantity_kg"] == "1195"

    asyncio.run(scenario())


def test_lot_uses_measured_mass_and_rejects_incompatible_unit(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api, quantity_kg="1500")
            measurement = await create_measurement_record(
                api, declaration["id"], quantity_kg="1175"
            )
            lot_response = await api.post(
                f"/api/v1/declarations/{declaration['id']}/lots",
                json={
                    "measurement_id": measurement["id"],
                    "processing_unit_id": "UNIT-001",
                    "evidence_ids": [],
                },
            )
            assert lot_response.status_code == 201
            lot = lot_response.json()
            assert lot["measured_quantity_kg"] == "1175"
            assert lot["measured_quantity_kg"] != declaration["quantity_kg"]
            assert [event["status"] for event in lot["status_history"]] == [
                "measured",
                "lot_created",
            ]

            manure = await create_declaration(
                api,
                producer_id="PROD-004",
                waste_type_id="cattle_manure",
                quantity_kg="1000",
            )
            manure_measurement = await create_measurement_record(api, manure["id"])
            incompatible = await api.post(
                f"/api/v1/declarations/{manure['id']}/lots",
                json={
                    "measurement_id": manure_measurement["id"],
                    "processing_unit_id": "UNIT-002",
                },
            )
            assert incompatible.status_code == 422

    asyncio.run(scenario())


def test_refusal_requires_reason_and_existing_decision_is_not_overwritten(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api)
            measurement = await create_measurement_record(api, declaration["id"])
            lot = (
                await api.post(
                    f"/api/v1/declarations/{declaration['id']}/lots",
                    json={
                        "measurement_id": measurement["id"],
                        "processing_unit_id": "UNIT-001",
                    },
                )
            ).json()
            missing_reason = await api.post(
                f"/api/v1/lots/{lot['id']}/decision",
                json={"decision": "refused", "reason": "", "note": ""},
            )
            refused = await api.post(
                f"/api/v1/lots/{lot['id']}/decision",
                json={
                    "decision": "refused",
                    "reason": "Contamination visuelle déclarée pour la démo.",
                    "note": "Décision non authentifiée.",
                },
            )
            overwrite = await api.post(
                f"/api/v1/lots/{lot['id']}/decision",
                json={"decision": "accepted", "reason": "", "note": ""},
            )

            assert missing_reason.status_code == 422
            assert refused.status_code == 201
            assert refused.json()["proof_level"] == "P1"
            assert refused.json()["actor_authenticated"] is False
            assert overwrite.status_code == 409
            persisted = (await api.get(f"/api/v1/lots/{lot['id']}")).json()
            assert persisted["status"] == "refused"
            assert persisted["decision"]["decision"] == "refused"

    asyncio.run(scenario())


def test_recalculation_preserves_initial_estimate_and_timeline_is_correlated(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            declaration = await create_declaration(api, quantity_kg="1500")
            proposal = await api.post(
                f"/api/v1/declarations/{declaration['id']}/proposal",
                json={"processing_unit_id": "UNIT-001"},
            )
            assert proposal.status_code == 200
            initial_estimate = proposal.json()["estimate"]
            evidence = await upload_pdf(api, declaration["id"])
            measurement = await create_measurement_record(
                api,
                declaration["id"],
                quantity_kg="1200",
                evidence_id=evidence["id"],
            )
            lot = (
                await api.post(
                    f"/api/v1/declarations/{declaration['id']}/lots",
                    json={
                        "measurement_id": measurement["id"],
                        "processing_unit_id": "UNIT-001",
                        "evidence_ids": [evidence["id"]],
                    },
                )
            ).json()
            accepted = await api.post(
                f"/api/v1/lots/{lot['id']}/decision",
                json={"decision": "accepted", "reason": "", "note": "Démo locale."},
            )
            assert accepted.status_code == 201
            recalculated = await api.post(
                f"/api/v1/declarations/{declaration['id']}/recalculations",
                json={
                    "measurement_id": measurement["id"],
                    "processing_unit_id": "UNIT-001",
                },
            )
            assert recalculated.status_code == 201, recalculated.text
            result = recalculated.json()
            assert result["previous_estimate"]["id"] == initial_estimate["id"]
            assert result["estimate"]["id"] != initial_estimate["id"]
            assert result["estimate"]["input_quantity_kg"] == "1200"
            assert result["estimate"]["input_proof_level"] == "P3"
            assert result["estimate"]["source_measurement_id"] == measurement["id"]
            assert result["estimate"]["proof_level"] == "P0"
            assert result["estimate"]["approved_for_scientific_claims"] is False
            assert result["estimate"]["calculation_hash"] != initial_estimate["calculation_hash"]

            timeline_response = await api.get(
                f"/api/v1/declarations/{declaration['id']}/timeline"
            )
            assert timeline_response.status_code == 200
            timeline = timeline_response.json()
            assert {run["id"] for run in timeline["estimate_runs"]} == {
                initial_estimate["id"],
                result["estimate"]["id"],
            }
            assert timeline["estimate_lineage"][0]["parent_estimate_run_id"] == initial_estimate["id"]
            event_types = {event["event_type"] for event in timeline["audit_events"]}
            assert {
                "evidence.created",
                "measurement.recorded",
                "lot.created",
                "lot.accepted",
                "estimate.recalculated_from_measurement",
            }.issubset(event_types)
            assert all(
                event["declaration_id"] == declaration["id"]
                for event in timeline["audit_events"]
            )
            serialized_events = str(timeline["audit_events"])
            assert "BioLoop evidence demo" not in serialized_events

    asyncio.run(scenario())


def test_existing_database_schema_is_migrated_without_deletion(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE waste_declarations (
                id TEXT PRIMARY KEY, producer_id TEXT NOT NULL,
                producer_name TEXT NOT NULL, producer_locality TEXT NOT NULL,
                waste_type_id TEXT NOT NULL, quantity_kg TEXT NOT NULL,
                frequency TEXT NOT NULL, availability_date TEXT NOT NULL,
                notes TEXT NOT NULL, latitude REAL NOT NULL,
                longitude REAL NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE estimate_runs (
                id TEXT PRIMARY KEY, declaration_id TEXT NOT NULL,
                processing_unit_id TEXT NOT NULL, factor_set_id TEXT NOT NULL,
                factor_set_version TEXT NOT NULL, calculation_hash TEXT NOT NULL,
                input_snapshot TEXT NOT NULL, output_snapshot TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE audit_events (
                id TEXT PRIMARY KEY, correlation_id TEXT NOT NULL,
                event_type TEXT NOT NULL, object_type TEXT NOT NULL,
                object_id TEXT NOT NULL, payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            INSERT INTO waste_declarations VALUES (
                'DECL-ABCDEF123456', 'PROD-001', 'Ancien producteur', 'Abobo',
                'market_organic', '900', 'hebdomadaire', '2026-08-30',
                'Ligne antérieure à la migration', 5.4161, -4.0159,
                '2026-08-28T00:00:00+00:00'
            );
            INSERT INTO audit_events VALUES (
                'AUD-OLD', 'CORR-OLD', 'legacy.event', 'legacy',
                'OLD-1', '{}', '2026-08-28T00:00:00+00:00'
            );
            """
        )

    app_for(tmp_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        audit_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(audit_events)")
        }
        legacy_count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE id = 'AUD-OLD'"
        ).fetchone()[0]
        legacy_declaration = connection.execute(
            """
            SELECT notes, owner_organization_id FROM waste_declarations
            WHERE id = 'DECL-ABCDEF123456'
            """
        ).fetchone()

    assert {
        "evidence",
        "measurements",
        "lots",
        "lot_decisions",
        "estimate_lineage",
        "organizations",
        "demo_users",
        "memberships",
        "collections",
        "notifications",
        "verifications",
    }.issubset(tables)
    assert {
        "declaration_id",
        "actor_user_id",
        "actor_organization_id",
        "actor_role",
    }.issubset(audit_columns)
    assert legacy_count == 1
    assert legacy_declaration == (
        "Ligne antérieure à la migration",
        "ORG-PROD-ABOBO",
    )
