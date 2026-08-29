from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .models import EstimateRun, EstimateScenario, EstimateSource, WasteDeclaration


class EstimationEngine:
    def __init__(self, factor_set_path: Path) -> None:
        with factor_set_path.open(encoding="utf-8") as stream:
            self.factor_set = json.load(stream)
        self._validate_factor_set()

    def _validate_factor_set(self) -> None:
        factor_set = self.factor_set
        if factor_set.get("status") != "simulation_illustrative":
            raise ValueError("Le jeu initial doit être une simulation illustrative.")
        if factor_set.get("approved_for_scientific_claims") is not False:
            raise ValueError("Le jeu illustratif ne peut autoriser une allégation scientifique.")
        if factor_set.get("proof_level") != "P0":
            raise ValueError("Le jeu illustratif doit conserver le niveau de preuve P0.")
        keys = [scenario.get("key") for scenario in factor_set.get("scenarios", [])]
        if keys != ["low", "central", "high"]:
            raise ValueError("Les scénarios doivent être ordonnés bas, central, haut.")
        multipliers = [Decimal(item["multiplier"]) for item in factor_set["scenarios"]]
        if not multipliers[0] < multipliers[1] < multipliers[2]:
            raise ValueError("Les multiplicateurs doivent être strictement croissants.")

    def calculate(
        self, declaration: WasteDeclaration, processing_unit_id: str
    ) -> EstimateRun:
        factor_set = self.factor_set
        canonical_inputs = {
            "factor_set_id": factor_set["id"],
            "factor_set_version": factor_set["version"],
            "mass_kg": str(declaration.quantity_kg),
            "processing_unit_id": processing_unit_id,
            "waste_type_id": declaration.waste_type_id,
        }
        encoded = json.dumps(
            canonical_inputs,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        calculation_hash = hashlib.sha256(encoded).hexdigest()
        run_hash = hashlib.sha256(
            f"{declaration.id}:{calculation_hash}".encode("utf-8")
        ).hexdigest()
        scenarios = []
        for scenario in factor_set["scenarios"]:
            multiplier = Decimal(scenario["multiplier"])
            value = (declaration.quantity_kg * multiplier).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            scenarios.append(
                EstimateScenario(
                    key=scenario["key"],
                    label=scenario["label"],
                    multiplier_uri_per_kg=multiplier,
                    value=value,
                )
            )
        return EstimateRun(
            id=f"EST-{run_hash[:16].upper()}",
            declaration_id=declaration.id,
            factor_set_id=factor_set["id"],
            factor_set_version=factor_set["version"],
            classification="simulation illustrative",
            formula=factor_set["formula"],
            input_quantity_kg=declaration.quantity_kg,
            input_unit=factor_set["input_unit"],
            output_unit=factor_set["output_unit"],
            scenarios=scenarios,
            assumptions=factor_set["assumptions"],
            source=EstimateSource.model_validate(factor_set["source"]),
            credibility_rule_reference=factor_set["credibility_rule_reference"],
            approved_for_scientific_claims=False,
            calculation_hash=calculation_hash,
            created_at=datetime.now(UTC),
        )
