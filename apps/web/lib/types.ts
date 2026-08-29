export type ProofLevel = "P0" | "P1" | "P2" | "P3" | "P4" | "P5";

export interface EvidenceLabel {
  provenance: string;
  proof_level: ProofLevel;
  label: string;
}

export interface Producer {
  id: string;
  name: string;
  kind: string;
  locality: string;
  default_waste_type_id: string;
  proof_level: ProofLevel;
}

export interface WasteType {
  id: string;
  name: string;
  description: string;
  proof_level: ProofLevel;
}

export interface ProcessingUnit {
  id: string;
  name: string;
  process: string;
  locality: string;
  daily_capacity_kg: string;
  reserved_capacity_kg: string;
  accepted_waste_type_ids: string[];
  collection_window: string;
  proof_level: ProofLevel;
}

export interface Catalog {
  disclaimer: string;
  producers: Producer[];
  processing_units: ProcessingUnit[];
  waste_types: WasteType[];
  evidence_levels: EvidenceLabel[];
}

export interface Declaration {
  id: string;
  producer_id: string;
  producer_name: string;
  producer_locality: string;
  waste_type_id: string;
  quantity_kg: string;
  frequency: string;
  availability_date: string;
  notes: string;
  proof_level: ProofLevel;
  field_evidence: Record<string, EvidenceLabel>;
}

export interface UnitMatch {
  processing_unit_id: string;
  processing_unit_name: string;
  process: string;
  available_capacity_kg: string;
  distance_straight_line_km: string;
  collection_window: string;
  reasons: string[];
  proof_level: ProofLevel;
}

export interface EstimateScenario {
  key: "low" | "central" | "high";
  label: string;
  multiplier_uri_per_kg: string;
  value: string;
}

export interface Proposal {
  correlation_id: string;
  declaration: Declaration;
  selected_unit: ProcessingUnit;
  estimate: {
    id: string;
    factor_set_id: string;
    factor_set_version: string;
    classification: string;
    formula: string;
    input_quantity_kg: string;
    input_unit: string;
    output_unit: string;
    scenarios: EstimateScenario[];
    assumptions: string[];
    source: { title: string; reference: string; note: string };
    credibility_rule_reference: string;
    approved_for_scientific_claims: false;
    calculation_hash: string;
    input_provenance: string;
    input_proof_level: ProofLevel;
    source_measurement_id: string | null;
    supersedes_estimate_run_id: string | null;
    proof_level: ProofLevel;
  };
  route: {
    id: string;
    status: string;
    method: string;
    scheduled_date: string;
    quantity_kg: string;
    one_way_straight_line_km: string;
    total_straight_line_km: string;
    distance_unit: string;
    stops: Array<{
      order: number;
      site_id: string;
      name: string;
      role: string;
      window: string;
    }>;
    assumptions: string[];
    approval_required: true;
    proof_level: ProofLevel;
  };
}

export interface EvidenceRecord {
  id: string;
  declaration_id: string;
  category: "photo_gisement" | "bon_pesee" | "document_accompagnement" | "autre";
  original_filename: string;
  media_type: "image/jpeg" | "image/png" | "application/pdf";
  size_bytes: number;
  sha256: string;
  submitted_at: string;
  captured_at: string | null;
  note: string;
  provenance: "documented";
  proof_level: "P2";
}

export interface MeasurementRecord {
  id: string;
  declaration_id: string;
  quantity_kg: string;
  unit: "kg";
  method: "balance_plateforme" | "balance_mobile" | "balance_mecanique" | "autre";
  measured_at: string;
  device_reference: string | null;
  evidence_id: string | null;
  supersedes_measurement_id: string | null;
  note: string;
  created_at: string;
  provenance: "measured";
  proof_level: "P3";
}

export interface LotStatusEvent {
  id: string;
  lot_id: string;
  status: "measured" | "lot_created" | "accepted" | "refused";
  occurred_at: string;
  actor_label: string;
  detail: string;
}

export interface LotDecision {
  id: string;
  lot_id: string;
  processing_unit_id: string;
  decision: "accepted" | "refused";
  decided_at: string;
  reason: string;
  note: string;
  actor_label: string;
  actor_authenticated: false;
  provenance: "declared";
  proof_level: "P1";
}

export interface LotRecord {
  id: string;
  declaration_id: string;
  measurement_id: string;
  processing_unit_id: string;
  waste_type_id: string;
  measured_quantity_kg: string;
  quantity_unit: "kg";
  evidence_ids: string[];
  status: "lot_created" | "accepted" | "refused";
  created_at: string;
  input_provenance: "measured";
  input_proof_level: "P3";
  decision: LotDecision | null;
  status_history: LotStatusEvent[];
}

export interface EstimateRunSummary {
  id: string;
  processing_unit_id: string;
  input_quantity_kg: string;
  input_proof_level: ProofLevel;
  source_measurement_id: string | null;
  calculation_hash: string;
  factor_set_version: string;
  created_at: string;
  proof_level: "P0";
}

export interface RecalculationResult {
  correlation_id: string;
  previous_estimate: EstimateRunSummary;
  estimate: Proposal["estimate"];
  lineage: {
    parent_estimate_run_id: string;
    child_estimate_run_id: string;
    source_measurement_id: string;
    created_at: string;
  };
}

export interface AuditEvent {
  id: string;
  correlation_id: string;
  declaration_id: string;
  event_type: string;
  object_type: string;
  object_id: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface DeclarationTimeline {
  declaration: Declaration;
  evidence: EvidenceRecord[];
  measurements: MeasurementRecord[];
  lots: LotRecord[];
  estimate_runs: EstimateRunSummary[];
  estimate_lineage: RecalculationResult["lineage"][];
  audit_events: AuditEvent[];
}
