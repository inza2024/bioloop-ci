from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Provenance(str, Enum):
    SIMULATED = "simulated"
    DECLARED = "declared"
    DOCUMENTED = "documented"
    MEASURED = "measured"
    VERIFIED = "verified"
    CERTIFIED = "certified"


class ProofLevel(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"


class EvidenceLabel(BaseModel):
    provenance: Provenance
    proof_level: ProofLevel
    label: str


class Producer(BaseModel):
    id: str
    name: str
    kind: str
    locality: str
    latitude: float
    longitude: float
    default_waste_type_id: str
    provenance: Provenance
    proof_level: ProofLevel


class WasteType(BaseModel):
    id: str
    name: str
    description: str
    provenance: Provenance
    proof_level: ProofLevel


class ProcessingUnit(BaseModel):
    id: str
    name: str
    process: str
    locality: str
    latitude: float
    longitude: float
    daily_capacity_kg: Decimal
    reserved_capacity_kg: Decimal
    accepted_waste_type_ids: list[str]
    collection_window: str
    provenance: Provenance
    proof_level: ProofLevel


Frequency = Literal["ponctuelle", "quotidienne", "hebdomadaire"]


class WasteDeclarationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    producer_id: str = Field(min_length=1, max_length=40)
    waste_type_id: str = Field(min_length=1, max_length=60)
    quantity_kg: Decimal = Field(gt=0, le=50_000, max_digits=10, decimal_places=2)
    frequency: Frequency
    availability_date: date
    notes: str = Field(default="", max_length=280)


class WasteDeclaration(WasteDeclarationCreate):
    id: str
    producer_name: str
    producer_locality: str
    latitude: float
    longitude: float
    provenance: Provenance = Provenance.DECLARED
    proof_level: ProofLevel = ProofLevel.P1
    created_at: datetime
    field_evidence: dict[str, EvidenceLabel]


class UnitMatch(BaseModel):
    processing_unit_id: str
    processing_unit_name: str
    process: str
    available_capacity_kg: Decimal
    distance_straight_line_km: Decimal
    collection_window: str
    compatible: bool = True
    reasons: list[str]
    provenance: Provenance = Provenance.SIMULATED
    proof_level: ProofLevel = ProofLevel.P0


class ProposalCreate(BaseModel):
    processing_unit_id: str = Field(min_length=1, max_length=40)


class EstimateScenario(BaseModel):
    key: Literal["low", "central", "high"]
    label: str
    multiplier_uri_per_kg: Decimal
    value: Decimal


class EstimateSource(BaseModel):
    title: str
    reference: str
    note: str


class EstimateRun(BaseModel):
    id: str
    declaration_id: str
    factor_set_id: str
    factor_set_version: str
    classification: Literal["simulation illustrative"]
    formula: str
    input_quantity_kg: Decimal
    input_unit: str
    output_unit: str
    scenarios: list[EstimateScenario]
    assumptions: list[str]
    source: EstimateSource
    credibility_rule_reference: str
    approved_for_scientific_claims: bool = False
    calculation_hash: str
    input_provenance: Provenance = Provenance.DECLARED
    input_proof_level: ProofLevel = ProofLevel.P1
    source_measurement_id: str | None = None
    supersedes_estimate_run_id: str | None = None
    provenance: Provenance = Provenance.SIMULATED
    proof_level: ProofLevel = ProofLevel.P0
    created_at: datetime


class RouteStop(BaseModel):
    order: int
    site_id: str
    name: str
    role: Literal["départ", "collecte", "livraison"]
    window: str


class RoutePlan(BaseModel):
    id: str
    status: Literal["proposée — validation humaine requise"]
    method: str
    scheduled_date: date
    quantity_kg: Decimal
    one_way_straight_line_km: Decimal
    total_straight_line_km: Decimal
    distance_unit: Literal["km géodésiques illustratifs"]
    stops: list[RouteStop]
    assumptions: list[str]
    approval_required: bool = True
    provenance: Provenance = Provenance.SIMULATED
    proof_level: ProofLevel = ProofLevel.P0


class Proposal(BaseModel):
    correlation_id: str
    declaration: WasteDeclaration
    selected_unit: ProcessingUnit
    estimate: EstimateRun
    route: RoutePlan


EvidenceCategory = Literal[
    "photo_gisement",
    "bon_pesee",
    "document_accompagnement",
    "autre",
]


class EvidenceRecord(BaseModel):
    id: str
    declaration_id: str
    category: EvidenceCategory
    original_filename: str
    media_type: Literal["image/jpeg", "image/png", "application/pdf"]
    size_bytes: int
    sha256: str
    submitted_at: datetime
    captured_at: datetime | None = None
    note: str = ""
    provenance: Provenance = Provenance.DOCUMENTED
    proof_level: ProofLevel = ProofLevel.P2


MeasurementMethod = Literal[
    "balance_plateforme",
    "balance_mobile",
    "balance_mecanique",
    "autre",
]


class MeasurementCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    quantity_kg: Decimal = Field(gt=0, le=50_000, max_digits=10, decimal_places=2)
    unit: Literal["kg"] = "kg"
    method: MeasurementMethod
    measured_at: datetime
    device_reference: str | None = Field(default=None, max_length=100)
    evidence_id: str | None = Field(default=None, max_length=40)
    supersedes_measurement_id: str | None = Field(default=None, max_length=40)
    note: str = Field(default="", max_length=500)

    @field_validator("measured_at")
    @classmethod
    def measured_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("La date de mesure doit inclure un fuseau horaire.")
        return value


class MeasurementRecord(MeasurementCreate):
    id: str
    declaration_id: str
    created_at: datetime
    provenance: Provenance = Provenance.MEASURED
    proof_level: ProofLevel = ProofLevel.P3


class LotCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    measurement_id: str = Field(min_length=1, max_length=40)
    processing_unit_id: str = Field(min_length=1, max_length=40)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)


class LotStatusEvent(BaseModel):
    id: str
    lot_id: str
    status: Literal["measured", "lot_created", "accepted", "refused"]
    occurred_at: datetime
    actor_label: str
    detail: str


class LotDecisionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    decision: Literal["accepted", "refused"]
    reason: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def refusal_requires_reason(self) -> "LotDecisionCreate":
        if self.decision == "refused" and not self.reason:
            raise ValueError("Un motif est obligatoire en cas de refus.")
        return self


class LotDecisionRecord(BaseModel):
    id: str
    lot_id: str
    processing_unit_id: str
    decision: Literal["accepted", "refused"]
    decided_at: datetime
    reason: str
    note: str
    actor_label: Literal["Opérateur unité — démonstration non authentifiée"]
    actor_authenticated: Literal[False] = False
    provenance: Provenance = Provenance.DECLARED
    proof_level: ProofLevel = ProofLevel.P1


class LotRecord(BaseModel):
    id: str
    declaration_id: str
    measurement_id: str
    processing_unit_id: str
    waste_type_id: str
    measured_quantity_kg: Decimal
    quantity_unit: Literal["kg"] = "kg"
    evidence_ids: list[str]
    status: Literal["lot_created", "accepted", "refused"]
    created_at: datetime
    input_provenance: Provenance = Provenance.MEASURED
    input_proof_level: ProofLevel = ProofLevel.P3
    decision: LotDecisionRecord | None = None
    status_history: list[LotStatusEvent] = Field(default_factory=list)


class RecalculationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    measurement_id: str = Field(min_length=1, max_length=40)
    processing_unit_id: str = Field(min_length=1, max_length=40)


class EstimateLineage(BaseModel):
    parent_estimate_run_id: str
    child_estimate_run_id: str
    source_measurement_id: str
    created_at: datetime


class EstimateRunSummary(BaseModel):
    id: str
    processing_unit_id: str
    input_quantity_kg: Decimal
    input_proof_level: ProofLevel
    source_measurement_id: str | None
    calculation_hash: str
    factor_set_version: str
    created_at: datetime
    proof_level: ProofLevel = ProofLevel.P0


class RecalculationResult(BaseModel):
    correlation_id: str
    previous_estimate: EstimateRunSummary
    estimate: EstimateRun
    lineage: EstimateLineage


class AuditEventRecord(BaseModel):
    id: str
    correlation_id: str
    declaration_id: str | None
    event_type: str
    object_type: str
    object_id: str
    payload: dict
    created_at: datetime


class DeclarationTimeline(BaseModel):
    declaration: WasteDeclaration
    evidence: list[EvidenceRecord]
    measurements: list[MeasurementRecord]
    lots: list[LotRecord]
    estimate_runs: list[EstimateRunSummary]
    estimate_lineage: list[EstimateLineage]
    audit_events: list[AuditEventRecord]
