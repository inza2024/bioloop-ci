from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from app.estimation import EstimationEngine
from app.models import EvidenceLabel, ProofLevel, Provenance, WasteDeclaration


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def declaration(quantity: str = "1000.00") -> WasteDeclaration:
    return WasteDeclaration(
        id="DECL-GOLDEN",
        producer_id="PROD-001",
        producer_name="Producteur test",
        producer_locality="Abidjan",
        waste_type_id="market_organic",
        quantity_kg=Decimal(quantity),
        frequency="ponctuelle",
        availability_date=date(2026, 9, 1),
        notes="",
        latitude=5.4,
        longitude=-4.0,
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


def engine() -> EstimationEngine:
    return EstimationEngine(
        PROJECT_ROOT
        / "data"
        / "factor_sets"
        / "illustrative-normalized-v1.json"
    )


def test_golden_three_scenarios_are_explicitly_illustrative() -> None:
    result = engine().calculate(declaration(), "UNIT-001")

    assert [scenario.value for scenario in result.scenarios] == [
        Decimal("800.00"),
        Decimal("1000.00"),
        Decimal("1200.00"),
    ]
    assert result.output_unit == "URI (unité de rendement illustrative)"
    assert result.classification == "simulation illustrative"
    assert result.proof_level == ProofLevel.P0
    assert result.approved_for_scientific_claims is False
    assert "ne représentent ni du biogaz" in result.source.note


def test_same_inputs_and_factor_version_reproduce_values_and_hash() -> None:
    first = engine().calculate(declaration("1250.50"), "UNIT-002")
    second = engine().calculate(declaration("1250.50"), "UNIT-002")

    assert first.calculation_hash == second.calculation_hash
    assert first.id == second.id
    assert first.scenarios == second.scenarios


def test_material_input_changes_calculation_hash() -> None:
    first = engine().calculate(declaration("1000.00"), "UNIT-001")
    second = engine().calculate(declaration("1001.00"), "UNIT-001")

    assert first.calculation_hash != second.calculation_hash


def test_distinct_declarations_keep_unique_runs_for_the_same_calculation() -> None:
    first_declaration = declaration("1000.00")
    second_declaration = first_declaration.model_copy(update={"id": "DECL-OTHER"})

    first = engine().calculate(first_declaration, "UNIT-001")
    second = engine().calculate(second_declaration, "UNIT-001")

    assert first.calculation_hash == second.calculation_hash
    assert first.scenarios == second.scenarios
    assert first.id != second.id
