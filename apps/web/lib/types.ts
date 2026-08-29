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

