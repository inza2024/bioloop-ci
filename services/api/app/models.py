from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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

