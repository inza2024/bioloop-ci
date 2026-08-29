from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from app.config import Settings
from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def app_for(tmp_path: Path):
    settings = Settings(
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
    return create_app(settings)


def test_vertical_slice_from_declaration_to_proposal(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as api:
            catalog = await api.get("/api/v1/catalog")
            assert catalog.status_code == 200
            assert len(catalog.json()["producers"]) == 8
            assert len(catalog.json()["processing_units"]) == 2
            assert all(
                item["proof_level"] == "P0"
                for item in catalog.json()["producers"]
            )

            created = await api.post(
                "/api/v1/declarations",
                json={
                    "producer_id": "PROD-001",
                    "waste_type_id": "market_organic",
                    "quantity_kg": "1500.00",
                    "frequency": "hebdomadaire",
                    "availability_date": "2026-09-01",
                    "notes": "Déclaration créée par le test du parcours.",
                },
            )
            assert created.status_code == 201
            declaration = created.json()
            assert declaration["proof_level"] == "P1"
            assert declaration["field_evidence"]["location"]["proof_level"] == "P0"

            matches = await api.get(
                f"/api/v1/declarations/{declaration['id']}/matches"
            )
            assert matches.status_code == 200
            assert len(matches.json()) == 2

            proposal = await api.post(
                f"/api/v1/declarations/{declaration['id']}/proposal",
                json={
                    "processing_unit_id": matches.json()[0]["processing_unit_id"]
                },
            )
            assert proposal.status_code == 200
            payload = proposal.json()
            assert [
                item["label"] for item in payload["estimate"]["scenarios"]
            ] == ["Bas", "Central", "Haut"]
            assert payload["estimate"]["approved_for_scientific_claims"] is False
            assert payload["estimate"]["output_unit"].startswith("URI")
            assert payload["route"]["approval_required"] is True
            assert len(payload["route"]["stops"]) == 3

    asyncio.run(scenario())


def test_invalid_quantity_is_rejected_before_business_execution(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as api:
            response = await api.post(
                "/api/v1/declarations",
                json={
                    "producer_id": "PROD-001",
                    "waste_type_id": "market_organic",
                    "quantity_kg": -1,
                    "frequency": "ponctuelle",
                    "availability_date": "2026-09-01",
                },
            )
            assert response.status_code == 422

    asyncio.run(scenario())


def test_incompatible_unit_is_rejected(tmp_path: Path) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app_for(tmp_path))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as api:
            created = (
                await api.post(
                    "/api/v1/declarations",
                    json={
                        "producer_id": "PROD-004",
                        "waste_type_id": "cattle_manure",
                        "quantity_kg": 1000,
                        "frequency": "quotidienne",
                        "availability_date": "2026-09-01",
                    },
                )
            ).json()
            response = await api.post(
                f"/api/v1/declarations/{created['id']}/proposal",
                json={"processing_unit_id": "UNIT-002"},
            )
            assert response.status_code == 422

    asyncio.run(scenario())
