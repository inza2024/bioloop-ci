from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from .catalog import Catalog
from .matching import compatible_units
from .models import (
    DecisionServiceMetadata,
    ProcessingUnit,
    RoutePlan,
    UnitMatch,
    WasteDeclaration,
)
from .routing import propose_route


class MatchDecision(BaseModel):
    matches: list[UnitMatch]
    metadata: DecisionServiceMetadata


class RouteDecision(BaseModel):
    route: RoutePlan
    metadata: DecisionServiceMetadata


class AnomalyFlag(BaseModel):
    code: str
    severity: str
    message: str


class AnomalyDecision(BaseModel):
    flags: list[AnomalyFlag]
    metadata: DecisionServiceMetadata


class MatchingService(Protocol):
    def match(self, declaration: WasteDeclaration, catalog: Catalog) -> MatchDecision: ...


class RoutingService(Protocol):
    def plan(
        self,
        declaration: WasteDeclaration,
        unit: ProcessingUnit,
        calculation_hash: str,
    ) -> RouteDecision: ...


class AnomalyDetectionService(Protocol):
    def detect(
        self, *, declared_quantity_kg: float, measured_quantity_kg: float
    ) -> AnomalyDecision: ...


class DeterministicMatchingService:
    version = "compatibility-capacity-distance-v1"

    def match(self, declaration: WasteDeclaration, catalog: Catalog) -> MatchDecision:
        return MatchDecision(
            matches=compatible_units(declaration, catalog),
            metadata=DecisionServiceMetadata(
                rule_or_model="filtre compatibilité + capacité, tri distance haversine",
                version=self.version,
                input_variables=["waste_type_id", "quantity_kg", "accepted_waste_type_ids", "available_capacity_kg", "coordinates P0"],
                period="instantané",
                uncertainty="Distance routière, trafic et qualité matière non représentés.",
                limitations=["Catalogue entièrement fictif P0.", "Aucune analyse matière."],
                human_validation_required=True,
            ),
        )


class DeterministicRoutingService:
    version = "direct-haversine-roundtrip-v1"

    def plan(
        self,
        declaration: WasteDeclaration,
        unit: ProcessingUnit,
        calculation_hash: str,
    ) -> RouteDecision:
        return RouteDecision(
            route=propose_route(declaration, unit, calculation_hash),
            metadata=DecisionServiceMetadata(
                rule_or_model="aller-retour direct par distance haversine",
                version=self.version,
                input_variables=["producer coordinates P0", "unit coordinates P0", "availability_date", "quantity_kg"],
                period="date de disponibilité déclarée",
                uncertainty="Aucune distance routière, durée ou condition de circulation.",
                limitations=["Un seul gisement.", "Aucun solveur multi-véhicules."],
                human_validation_required=True,
            ),
        )


class DeterministicAnomalyDetectionService:
    """Reference rule only; it never promotes or rejects a proof automatically."""

    version = "declared-measured-gap-rule-v1"

    def detect(
        self, *, declared_quantity_kg: float, measured_quantity_kg: float
    ) -> AnomalyDecision:
        flags: list[AnomalyFlag] = []
        if declared_quantity_kg > 0:
            relative_gap = abs(measured_quantity_kg - declared_quantity_kg) / declared_quantity_kg
            if relative_gap >= 0.25:
                flags.append(
                    AnomalyFlag(
                        code="LARGE_DECLARED_MEASURED_GAP",
                        severity="review",
                        message="Écart relatif ≥ 25 % : contrôle humain recommandé, sans conclusion automatique.",
                    )
                )
        return AnomalyDecision(
            flags=flags,
            metadata=DecisionServiceMetadata(
                rule_or_model="seuil logiciel explicite sur écart relatif",
                version=self.version,
                input_variables=["declared_quantity_kg P1", "measured_quantity_kg P3"],
                period="comparaison ponctuelle",
                uncertainty="Seuil opérationnel non validé scientifiquement.",
                limitations=["Ne détecte ni fraude, ni contamination, ni erreur de capteur."],
                human_validation_required=True,
            ),
        )
