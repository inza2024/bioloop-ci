from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

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

    producer_id: str = Field(pattern=r"^PROD-[0-9]{3}$")
    waste_type_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,59}$")
    quantity_kg: Decimal = Field(gt=0, le=50_000, max_digits=10, decimal_places=2)
    frequency: Frequency
    availability_date: date
    notes: str = Field(default="", max_length=280)


class WasteDeclaration(WasteDeclarationCreate):
    id: str
    owner_organization_id: str | None = None
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
    processing_unit_id: str = Field(pattern=r"^UNIT-[0-9]{3}$")


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
    evidence_id: str | None = Field(
        default=None, pattern=r"^EVID-[A-F0-9]{24}$"
    )
    supersedes_measurement_id: str | None = Field(
        default=None, pattern=r"^MEAS-[A-F0-9]{12}$"
    )
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


EvidenceId = Annotated[str, Field(pattern=r"^EVID-[A-F0-9]{24}$")]


class LotCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    measurement_id: str = Field(pattern=r"^MEAS-[A-F0-9]{12}$")
    processing_unit_id: str = Field(pattern=r"^UNIT-[0-9]{3}$")
    evidence_ids: list[EvidenceId] = Field(default_factory=list, max_length=20)


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
    actor_label: str
    actor_authenticated: Literal[False] = False
    actor_user_id: str | None = None
    actor_organization_id: str | None = None
    actor_role: str | None = None
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

    measurement_id: str = Field(pattern=r"^MEAS-[A-F0-9]{12}$")
    processing_unit_id: str = Field(pattern=r"^UNIT-[0-9]{3}$")


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
    actor_user_id: str | None = None
    actor_organization_id: str | None = None
    actor_role: str | None = None
    created_at: datetime


class DeclarationTimeline(BaseModel):
    declaration: WasteDeclaration
    evidence: list[EvidenceRecord]
    measurements: list[MeasurementRecord]
    lots: list[LotRecord]
    estimate_runs: list[EstimateRunSummary]
    estimate_lineage: list[EstimateLineage]
    audit_events: list[AuditEventRecord]


class DemoRole(str, Enum):
    PRODUCER = "producer"
    LOGISTICIAN = "logistician"
    UNIT_OPERATOR = "processing_unit_operator"
    FIELD_CONTROLLER = "field_controller"
    COORDINATOR = "bioloop_coordinator"
    CLIENT = "client_farmer"


class DemoOrganization(BaseModel):
    id: str
    name: str
    kind: str
    site_type: Literal["producer", "processing_unit"] | None = None
    site_id: str | None = None
    is_demo: Literal[True] = True


class DemoUser(BaseModel):
    id: str
    display_name: str
    is_demo: Literal[True] = True


class DemoMembership(BaseModel):
    id: str
    user_id: str
    organization_id: str
    role: DemoRole
    status: Literal["active"] = "active"


class DemoActor(BaseModel):
    user_id: str
    display_name: str
    organization_id: str
    organization_name: str
    role: DemoRole
    site_type: Literal["producer", "processing_unit"] | None = None
    site_id: str | None = None
    is_demo: Literal[True] = True
    authenticated_for_production: Literal[False] = False


class DemoActorCatalog(BaseModel):
    mode_label: Literal["mode démonstration — aucune authentification de production"]
    actors: list[DemoActor]


class NotificationRecord(BaseModel):
    id: str
    organization_id: str
    target_role: DemoRole | None = None
    event_type: str
    subject_type: str
    subject_id: str
    message: str
    created_at: datetime
    read_at: datetime | None = None


class CollectionRecord(BaseModel):
    id: str
    declaration_id: str
    route_id: str
    processing_unit_id: str
    logistician_organization_id: str
    status: Literal["assigned", "collected"]
    scheduled_date: date
    expected_quantity_kg: Decimal
    quantity_unit: Literal["kg"] = "kg"
    total_straight_line_km: Decimal
    distance_unit: Literal["km géodésiques illustratifs"]
    route_method: str
    stops: list[RouteStop]
    evidence_id: str | None = None
    measurement_id: str | None = None
    confirmed_at: datetime | None = None
    confirmed_by_user_id: str | None = None
    confirmed_by_organization_id: str | None = None
    created_at: datetime
    status_provenance: Provenance = Provenance.DECLARED
    status_proof_level: ProofLevel = ProofLevel.P1
    route_provenance: Provenance = Provenance.SIMULATED
    route_proof_level: ProofLevel = ProofLevel.P0
    human_validation_required: Literal[True] = True


class CollectionConfirmCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=40, pattern=r"^EVID-[A-F0-9]{24}$")
    measurement_id: str = Field(min_length=1, max_length=40, pattern=r"^MEAS-[A-F0-9]{12}$")


class VerificationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    subject_type: Literal["waste_lot"] = "waste_lot"
    subject_id: str = Field(min_length=1, max_length=40, pattern=r"^LOT-[A-F0-9]{12}$")
    outcome: Literal["verified", "non_conform"]
    note: str = Field(min_length=3, max_length=500)
    idempotency_key: str = Field(
        min_length=8,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$",
    )


class VerificationRecord(BaseModel):
    id: str
    subject_type: Literal["waste_lot"]
    subject_id: str
    outcome: Literal["verified", "non_conform"]
    note: str
    verified_at: datetime
    actor_user_id: str
    actor_organization_id: str
    actor_role: Literal[DemoRole.FIELD_CONTROLLER]
    provenance: Provenance = Provenance.VERIFIED
    proof_level: ProofLevel = ProofLevel.P4


class ProjectionMetric(BaseModel):
    value_kg: Decimal
    basis_provenance: Provenance
    basis_proof_level: ProofLevel
    result_provenance: Provenance = Provenance.SIMULATED
    result_proof_level: ProofLevel = ProofLevel.P0


class ProjectionWindow(BaseModel):
    period_days: Literal[7, 30]
    declared: ProjectionMetric
    measured_basis: ProjectionMetric
    measured_coverage_declarations: int


class ForecastReport(BaseModel):
    processing_unit_id: str
    as_of: date
    classification: Literal["projection opérationnelle déterministe — simulation illustrative"]
    version: str
    source: str
    periods: list[ProjectionWindow]
    limitations: list[str]
    historical_data_required_before_ml: list[str]


class ProducerDeclarationView(BaseModel):
    declaration: WasteDeclaration
    proposed_unit_id: str | None = None
    collection_status: str | None = None
    lot_status: str | None = None
    next_action: str


class LogisticsCollectionView(BaseModel):
    collection: CollectionRecord
    producer_name: str
    waste_type_name: str
    processing_unit_name: str
    available_capacity_kg: Decimal
    capacity_proof_level: ProofLevel = ProofLevel.P0


class IncomingLotView(BaseModel):
    lot: LotRecord
    producer_name: str
    waste_type_name: str
    compatibility: bool
    available_capacity_kg: Decimal
    compatibility_proof_level: ProofLevel = ProofLevel.P0


class PendingControlView(BaseModel):
    lot: LotRecord
    producer_name: str
    existing_verification: VerificationRecord | None = None


class DemoWorkspace(BaseModel):
    actor: DemoActor
    mode_label: Literal["mode démonstration — aucune authentification de production"]
    permissions: list[str]
    notifications: list[NotificationRecord]
    producer_declarations: list[ProducerDeclarationView] = Field(default_factory=list)
    logistics_collections: list[LogisticsCollectionView] = Field(default_factory=list)
    incoming_lots: list[IncomingLotView] = Field(default_factory=list)
    pending_controls: list[PendingControlView] = Field(default_factory=list)
    projections: list[ForecastReport] = Field(default_factory=list)
    coordinator_counts: dict[str, int] = Field(default_factory=dict)
    audit_events: list[AuditEventRecord] = Field(default_factory=list)
    products: list[dict] = Field(default_factory=list)
    product_empty_state: str | None = None
