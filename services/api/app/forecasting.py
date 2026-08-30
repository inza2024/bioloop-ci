from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from math import ceil
from typing import Protocol

from .models import (
    ForecastReport,
    DecisionServiceMetadata,
    MeasurementRecord,
    ProjectionMetric,
    ProjectionWindow,
    ProofLevel,
    Provenance,
    WasteDeclaration,
)


ProjectionInput = tuple[WasteDeclaration, MeasurementRecord | None]


class ForecastService(Protocol):
    def project_unit_intake(
        self,
        processing_unit_id: str,
        declarations: list[ProjectionInput],
        *,
        as_of: date,
    ) -> ForecastReport: ...


class DeterministicDeclarationForecastService:
    version = "deterministic-declaration-cadence-v1"

    @staticmethod
    def _occurrences(
        declaration: WasteDeclaration, *, period_days: int, as_of: date
    ) -> int:
        if declaration.frequency == "quotidienne":
            return period_days
        if declaration.frequency == "hebdomadaire":
            return ceil(period_days / 7)
        end_date = as_of + timedelta(days=period_days - 1)
        return int(as_of <= declaration.availability_date <= end_date)

    def project_unit_intake(
        self,
        processing_unit_id: str,
        declarations: list[ProjectionInput],
        *,
        as_of: date,
    ) -> ForecastReport:
        periods: list[ProjectionWindow] = []
        for period_days in (7, 30):
            declared_total = Decimal("0")
            measured_total = Decimal("0")
            measured_coverage = 0
            for declaration, measurement in declarations:
                occurrences = self._occurrences(
                    declaration, period_days=period_days, as_of=as_of
                )
                declared_total += declaration.quantity_kg * occurrences
                if measurement is not None:
                    measured_total += measurement.quantity_kg * occurrences
                    measured_coverage += 1
            periods.append(
                ProjectionWindow(
                    period_days=period_days,
                    declared=ProjectionMetric(
                        value_kg=declared_total,
                        basis_provenance=Provenance.DECLARED,
                        basis_proof_level=ProofLevel.P1,
                    ),
                    measured_basis=ProjectionMetric(
                        value_kg=measured_total,
                        basis_provenance=Provenance.MEASURED,
                        basis_proof_level=ProofLevel.P3,
                    ),
                    measured_coverage_declarations=measured_coverage,
                )
            )
        return ForecastReport(
            processing_unit_id=processing_unit_id,
            as_of=as_of,
            classification=(
                "projection opérationnelle déterministe — simulation illustrative"
            ),
            version=self.version,
            source=(
                "Déclarations affectées à l’unité et dernière mesure P3 disponible ; "
                "cadence déclarée appliquée sans modèle prédictif."
            ),
            periods=periods,
            limitations=[
                "Les fréquences déclarées sont prolongées mécaniquement sur 7 et 30 jours.",
                "Aucune saisonnalité, contamination, indisponibilité ou probabilité d’acceptation n’est prédite.",
                "Une base P3 améliore la masse d’entrée, mais le volume projeté reste un résultat P0.",
                "Toute décision de capacité ou tournée exige une validation humaine.",
            ],
            historical_data_required_before_ml=[
                "masses déclarées et mesurées",
                "fréquence et saison",
                "type de déchet et contamination",
                "acceptations et refus",
                "temps de collecte",
                "capacité disponible",
                "production réellement mesurée",
            ],
            decision_metadata=DecisionServiceMetadata(
                rule_or_model="cadence déclarée × occurrences calendaires",
                version=self.version,
                input_variables=[
                    "quantity_kg P1",
                    "latest measurement quantity_kg P3 when available",
                    "frequency",
                    "availability_date",
                ],
                period="7 et 30 jours à partir de as_of",
                uncertainty=(
                    "Non quantifiée : aucune distribution statistique ni validation terrain."
                ),
                limitations=[
                    "Simulation mécanique sans saisonnalité ni probabilité.",
                    "Les historiques synthétiques P0 ne servent pas à entraîner un modèle.",
                ],
                human_validation_required=True,
            ),
        )
