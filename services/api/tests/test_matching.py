from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from app.catalog import Catalog
from app.matching import compatible_units
from app.models import EvidenceLabel, ProofLevel, Provenance, WasteDeclaration


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG = Catalog(PROJECT_ROOT / "data" / "fixtures")


def make_declaration(waste_type: str, quantity: str) -> WasteDeclaration:
    producer = CATALOG.producers[0]
    return WasteDeclaration(
        id="DECL-MATCH",
        producer_id=producer.id,
        producer_name=producer.name,
        producer_locality=producer.locality,
        waste_type_id=waste_type,
        quantity_kg=Decimal(quantity),
        frequency="hebdomadaire",
        availability_date=date(2026, 9, 1),
        notes="",
        latitude=producer.latitude,
        longitude=producer.longitude,
        provenance=Provenance.DECLARED,
        proof_level=ProofLevel.P1,
        created_at=datetime(2026, 8, 28, tzinfo=UTC),
        field_evidence={
            "quantity_kg": EvidenceLabel(
                provenance=Provenance.DECLARED,
                proof_level=ProofLevel.P1,
                label="test",
            )
        },
    )


def test_matching_filters_by_declared_compatibility() -> None:
    matches = compatible_units(
        make_declaration("cattle_manure", "1500"), CATALOG
    )

    assert [match.processing_unit_id for match in matches] == ["UNIT-001"]
    assert all(match.proof_level == ProofLevel.P0 for match in matches)


def test_matching_filters_when_simulated_capacity_is_insufficient() -> None:
    matches = compatible_units(
        make_declaration("market_organic", "10000"), CATALOG
    )

    assert matches == []


def test_matches_are_sorted_by_reproducible_distance() -> None:
    matches = compatible_units(
        make_declaration("market_organic", "1000"), CATALOG
    )

    assert len(matches) == 2
    assert matches[0].distance_straight_line_km <= matches[1].distance_straight_line_km

