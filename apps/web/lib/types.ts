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
  synthetic_profile: "small" | "enriched";
  synthetic_data: {
    metadata: Record<string, unknown>;
    counts: Record<string, number>;
  };
}

export interface Declaration {
  id: string;
  owner_organization_id: string | null;
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
  client_idempotency_key: string | null;
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
  actor_user_id: string | null;
  actor_organization_id: string | null;
  actor_role: string | null;
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
  declaration_id: string | null;
  event_type: string;
  object_type: string;
  object_id: string;
  payload: Record<string, unknown>;
  actor_user_id: string | null;
  actor_organization_id: string | null;
  actor_role: string | null;
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

export type DemoRole =
  | "producer"
  | "logistician"
  | "processing_unit_operator"
  | "field_controller"
  | "bioloop_coordinator"
  | "client_farmer";

export interface DemoActor {
  user_id: string;
  display_name: string;
  organization_id: string;
  organization_name: string;
  role: DemoRole;
  site_type: "producer" | "processing_unit" | null;
  site_id: string | null;
  is_demo: boolean;
  authenticated_for_pilot: boolean;
  authenticated_for_production: false;
  membership_id: string | null;
  membership_status: "active" | "pending";
}

export interface DemoActorCatalog {
  mode_label: "mode démonstration — aucune authentification de production";
  actors: DemoActor[];
}

export interface NotificationRecord {
  id: string;
  organization_id: string;
  target_role: DemoRole | null;
  event_type: string;
  subject_type: string;
  subject_id: string;
  message: string;
  created_at: string;
  read_at: string | null;
}

export interface CollectionRecord {
  id: string;
  declaration_id: string;
  route_id: string;
  processing_unit_id: string;
  logistician_organization_id: string;
  status: "assigned" | "collected";
  scheduled_date: string;
  expected_quantity_kg: string;
  quantity_unit: "kg";
  total_straight_line_km: string;
  distance_unit: string;
  route_method: string;
  stops: Proposal["route"]["stops"];
  evidence_id: string | null;
  measurement_id: string | null;
  confirmed_at: string | null;
  confirmed_by_user_id: string | null;
  confirmed_by_organization_id: string | null;
  created_at: string;
  status_provenance: "simulated" | "declared";
  status_proof_level: "P0" | "P1";
  route_provenance: "simulated";
  route_proof_level: "P0";
  human_validation_required: true;
}

export interface ForecastMetric {
  value_kg: string;
  basis_provenance: string;
  basis_proof_level: ProofLevel;
  result_provenance: "simulated";
  result_proof_level: "P0";
}

export interface ForecastReport {
  processing_unit_id: string;
  as_of: string;
  classification: string;
  version: string;
  source: string;
  periods: Array<{
    period_days: 7 | 30;
    declared: ForecastMetric;
    measured_basis: ForecastMetric;
    measured_coverage_declarations: number;
  }>;
  limitations: string[];
  historical_data_required_before_ml: string[];
  decision_metadata: {
    rule_or_model: string;
    version: string;
    input_variables: string[];
    period: string;
    proof_level: "P0";
    uncertainty: string;
    limitations: string[];
    human_validation_required: boolean;
  };
}

export interface VerificationRecord {
  id: string;
  subject_type: "waste_lot";
  subject_id: string;
  outcome: "verified" | "non_conform";
  note: string;
  verified_at: string;
  actor_user_id: string;
  actor_organization_id: string;
  actor_role: "field_controller";
  provenance: "verified";
  proof_level: "P4";
}

export interface DemoWorkspace {
  actor: DemoActor;
  mode_label: DemoActorCatalog["mode_label"];
  permissions: string[];
  notifications: NotificationRecord[];
  producer_declarations: Array<{
    declaration: Declaration;
    proposed_unit_id: string | null;
    collection_status: string | null;
    lot_status: string | null;
    next_action: string;
  }>;
  logistics_collections: Array<{
    collection: CollectionRecord;
    producer_name: string;
    waste_type_name: string;
    processing_unit_name: string;
    available_capacity_kg: string;
    capacity_proof_level: "P0";
  }>;
  incoming_lots: Array<{
    lot: LotRecord;
    producer_name: string;
    waste_type_name: string;
    compatibility: boolean;
    available_capacity_kg: string;
    compatibility_proof_level: "P0";
  }>;
  pending_controls: Array<{
    lot: LotRecord;
    producer_name: string;
    existing_verification: VerificationRecord | null;
  }>;
  projections: ForecastReport[];
  coordinator_counts: Record<string, number>;
  audit_events: AuditEvent[];
  products: Array<Record<string, unknown>>;
  product_empty_state: string | null;
}

export interface PilotMembership {
  id: string;
  organization_id: string;
  organization_name: string;
  organization_kind: string;
  site_id: string | null;
  role: DemoRole;
  status: "active" | "pending";
}

export interface AuthContext {
  user: { id: string; display_name: string; email: string };
  active_membership: PilotMembership;
  memberships: PilotMembership[];
  actor: DemoActor;
  portal_path: string;
  pilot_security_label: string;
}

export interface AuthPortal {
  context: AuthContext;
  notifications: NotificationRecord[];
  declarations: Declaration[];
  counters: Record<string, number>;
  proof_summary: string;
  next_action: string;
}

export type ProductCategory =
  | "measured_biogas"
  | "raw_digestate"
  | "liquid_fraction"
  | "solid_fraction"
  | "compost_amendment"
  | "potential_fertilizing_product"
  | "other_coproduct";

export interface PendingMembership {
  id: string;
  user_id: string;
  display_name: string;
  organization_id: string;
  organization_name: string;
  organization_kind: string;
  role: DemoRole;
  status: "pending";
  created_at: string;
}

export interface AdminAction {
  id: string;
  action: string;
  subject_type: string;
  subject_id: string;
  decision: string | null;
  reason: string;
  actor_user_id: string;
  actor_organization_id: string;
  actor_role: string;
  correlation_id: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AdminSession {
  id: string;
  user_id: string;
  display_name: string;
  active_membership_id: string;
  created_at: string;
  expires_at: string;
  last_seen_at: string;
}

export interface TransformationInput {
  lot_id: string;
  measured_quantity: string;
  unit: "kg";
  measurement_method: string;
  measured_at: string;
  provenance: "measured";
  proof_level: "P3";
}

export interface TransformationRun {
  id: string;
  operator_organization_id: string;
  processing_unit_id: string;
  process: string;
  status: "planned" | "in_progress" | "completed" | "cancelled";
  started_at: string | null;
  completed_at: string | null;
  operator_user_id: string;
  loss_quantity: string | null;
  loss_unit: string | null;
  loss_method: string | null;
  loss_measured_at: string | null;
  loss_proof_level: ProofLevel | null;
  correlation_id: string;
  created_at: string;
  inputs: TransformationInput[];
  evidence_ids: string[];
  output_product_ids: string[];
  scientific_derivation: false;
  measurement_warning: string;
}

export interface QualityTest {
  id: string;
  product_batch_id: string;
  parameter: string;
  value: string;
  unit: string;
  method: string;
  laboratory_or_actor: string;
  document_reference: string | null;
  tested_at: string;
  provenance: "measured" | "verified";
  proof_level: "P3" | "P4";
}

export interface ProductBatch {
  id: string;
  transformation_id: string;
  owner_organization_id: string;
  category: ProductCategory;
  quantity: string;
  unit: "kg" | "L" | "m3";
  measurement_method: string;
  measured_at: string;
  evidence_id: string | null;
  provenance: "measured";
  proof_level: "P3";
  quality_status: "quarantine" | "pending_analysis" | "released" | "rejected";
  location: string;
  correlation_id: string;
  created_at: string;
  on_hand_quantity: string;
  reserved_quantity: string;
  available_quantity: string;
  quality_tests: QualityTest[];
  release_proof_level: ProofLevel | null;
  quality_warning: string;
}

export interface CustomerReservation {
  id: string;
  product_batch_id: string;
  customer_organization_id: string;
  quantity: string;
  unit: "kg" | "L" | "m3";
  status: "active" | "cancelled" | "delivered";
  idempotency_key: string;
  actor_user_id: string;
  correlation_id: string;
  created_at: string;
  cancelled_at: string | null;
  delivered_at: string | null;
}

export interface OperationsWorkspace {
  actor: DemoActor;
  accepted_lots: Array<{
    id: string;
    declaration_id: string;
    processing_unit_id: string;
    waste_type_id: string;
    measured_quantity_kg: string;
    quantity_unit: "kg";
    input_provenance: "measured";
    input_proof_level: "P3";
    evidence_ids: string[];
  }>;
  transformations: TransformationRun[];
  products: ProductBatch[];
  reservations: CustomerReservation[];
  scientific_notice: string;
}
