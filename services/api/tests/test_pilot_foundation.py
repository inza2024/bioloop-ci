from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from app.catalog import Catalog
from app.decision_services import (
    DeterministicAnomalyDetectionService,
    DeterministicMatchingService,
    DeterministicRoutingService,
)
from app.models import EvidenceLabel, ProofLevel, Provenance, WasteDeclaration
from app.repository import Repository


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_enriched_p0_dataset_is_reproducible_and_preserves_existing_ids() -> None:
    first = Catalog(PROJECT_ROOT / "data" / "fixtures", profile="enriched")
    second = Catalog(PROJECT_ROOT / "data" / "fixtures", profile="enriched")

    assert len(first.producers) == 40
    assert len(first.processing_units) == 4
    assert [item.model_dump() for item in first.producers] == [
        item.model_dump() for item in second.producers
    ]
    assert [item.id for item in first.producers[:8]] == [
        item.id for item in Catalog(PROJECT_ROOT / "data" / "fixtures").producers
    ]
    summary = first.synthetic_dataset.summary()
    assert summary["metadata"]["seed"] == 20_260_830
    assert summary["metadata"]["proof_level"] == "P0"
    assert summary["counts"]["historical_events"] >= 40
    assert summary["counts"]["clients"] >= 1
    assert all(
        item["declared_proof_level"]
        == item["measured_proof_level"]
        == item["decision_proof_level"]
        == "P0"
        for item in first.synthetic_dataset.operational_history
    )


def test_decision_service_contracts_are_versioned_and_require_human_review() -> None:
    catalog = Catalog(PROJECT_ROOT / "data" / "fixtures")
    producer = catalog.producers[0]
    declaration = WasteDeclaration(
        id="DECL-CONTRACT",
        producer_id=producer.id,
        producer_name=producer.name,
        producer_locality=producer.locality,
        waste_type_id=producer.default_waste_type_id,
        quantity_kg=Decimal("1000"),
        frequency="hebdomadaire",
        availability_date=date(2026, 9, 1),
        notes="",
        latitude=producer.latitude,
        longitude=producer.longitude,
        provenance=Provenance.DECLARED,
        proof_level=ProofLevel.P1,
        created_at=datetime(2026, 8, 30, tzinfo=UTC),
        field_evidence={
            "quantity_kg": EvidenceLabel(
                provenance=Provenance.DECLARED,
                proof_level=ProofLevel.P1,
                label="test",
            )
        },
    )
    match = DeterministicMatchingService().match(declaration, catalog)
    assert match.metadata.version == "compatibility-capacity-distance-v1"
    assert match.metadata.human_validation_required is True
    unit = catalog.processing_unit(match.matches[0].processing_unit_id)
    assert unit is not None
    route = DeterministicRoutingService().plan(declaration, unit, "a" * 64)
    assert route.metadata.proof_level == ProofLevel.P0
    assert route.route.approval_required is True
    anomaly = DeterministicAnomalyDetectionService().detect(
        declared_quantity_kg=1000, measured_quantity_kg=700
    )
    assert anomaly.flags[0].severity == "review"
    assert "non validé scientifiquement" in anomaly.metadata.uncertainty


def test_existing_legacy_database_receives_only_additive_auth_migration(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE waste_declarations (
                id TEXT PRIMARY KEY, producer_id TEXT NOT NULL,
                producer_name TEXT NOT NULL, producer_locality TEXT NOT NULL,
                waste_type_id TEXT NOT NULL, quantity_kg TEXT NOT NULL,
                frequency TEXT NOT NULL, availability_date TEXT NOT NULL,
                notes TEXT NOT NULL, latitude REAL NOT NULL,
                longitude REAL NOT NULL, created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO waste_declarations VALUES
            ('DECL-LEGACY00001', 'PROD-001', 'Historique', 'Abobo',
             'market_organic', '300', 'ponctuelle', '2026-08-30',
             'à conserver', 5.4, -4.0, '2026-08-30T00:00:00+00:00')
            """
        )

    Repository(db_path)
    from app.database import run_migrations, sqlite_url

    run_migrations(sqlite_url(db_path))
    with sqlite3.connect(db_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns = {row[1] for row in connection.execute("PRAGMA table_info(waste_declarations)")}
        preserved = connection.execute(
            "SELECT notes FROM waste_declarations WHERE id='DECL-LEGACY00001'"
        ).fetchone()[0]
    assert {"pilot_users", "pilot_organizations", "pilot_memberships", "pilot_sessions", "alembic_version"}.issubset(tables)
    assert "client_idempotency_key" in columns
    assert preserved == "à conserver"
