import type {
  Catalog,
  CollectionRecord,
  Declaration,
  DeclarationTimeline,
  DemoActorCatalog,
  DemoWorkspace,
  EvidenceRecord,
  LotDecision,
  LotRecord,
  MeasurementRecord,
  Proposal,
  RecalculationResult,
  UnitMatch,
  VerificationRecord,
  AuditEvent,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  init?: RequestInit,
  demoUserId?: string,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof init?.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (demoUserId) headers.set("X-Demo-User-ID", demoUserId);
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Erreur API (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  catalog: () => request<Catalog>("/api/v1/catalog"),
  demoActors: () => request<DemoActorCatalog>("/api/v1/demo/actors"),
  demoWorkspace: (demoUserId: string, asOf?: string) => {
    const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
    return request<DemoWorkspace>(`/api/v1/demo/workspace${query}`, undefined, demoUserId);
  },
  createDeclaration: (payload: {
    producer_id: string;
    waste_type_id: string;
    quantity_kg: string;
    frequency: string;
    availability_date: string;
    notes: string;
  }, demoUserId?: string) =>
    request<Declaration>("/api/v1/declarations", {
      method: "POST",
      body: JSON.stringify(payload),
    }, demoUserId),
  matches: (declarationId: string, demoUserId?: string) =>
    request<UnitMatch[]>(`/api/v1/declarations/${declarationId}/matches`, undefined, demoUserId),
  proposal: (declarationId: string, processingUnitId: string, demoUserId?: string) =>
    request<Proposal>(`/api/v1/declarations/${declarationId}/proposal`, {
      method: "POST",
      body: JSON.stringify({ processing_unit_id: processingUnitId }),
    }, demoUserId),
  createEvidence: (
    declarationId: string,
    file: File,
    metadata: {
      category: EvidenceRecord["category"];
      captured_at?: string;
      note: string;
    },
    demoUserId?: string,
  ) => {
    const query = new URLSearchParams({
      category: metadata.category,
      original_filename: file.name,
      note: metadata.note,
    });
    if (metadata.captured_at) query.set("captured_at", metadata.captured_at);
    return request<EvidenceRecord>(
      `/api/v1/declarations/${declarationId}/evidence?${query.toString()}`,
      {
        method: "POST",
        body: file,
        headers: { "Content-Type": file.type },
      },
      demoUserId,
    );
  },
  createMeasurement: (
    declarationId: string,
    payload: {
      quantity_kg: string;
      unit: "kg";
      method: MeasurementRecord["method"];
      measured_at: string;
      device_reference: string | null;
      evidence_id: string | null;
      supersedes_measurement_id: string | null;
      note: string;
    },
    demoUserId?: string,
  ) =>
    request<MeasurementRecord>(`/api/v1/declarations/${declarationId}/measurements`, {
      method: "POST",
      body: JSON.stringify(payload),
    }, demoUserId),
  createLot: (
    declarationId: string,
    payload: { measurement_id: string; processing_unit_id: string; evidence_ids: string[] },
    demoUserId?: string,
  ) =>
    request<LotRecord>(`/api/v1/declarations/${declarationId}/lots`, {
      method: "POST",
      body: JSON.stringify(payload),
    }, demoUserId),
  decideLot: (
    lotId: string,
    payload: { decision: "accepted" | "refused"; reason: string; note: string },
    demoUserId?: string,
  ) =>
    request<LotDecision>(`/api/v1/lots/${lotId}/decision`, {
      method: "POST",
      body: JSON.stringify(payload),
    }, demoUserId),
  recalculate: (declarationId: string, measurementId: string, processingUnitId: string) =>
    request<RecalculationResult>(`/api/v1/declarations/${declarationId}/recalculations`, {
      method: "POST",
      body: JSON.stringify({
        measurement_id: measurementId,
        processing_unit_id: processingUnitId,
      }),
    }),
  timeline: (declarationId: string) =>
    request<DeclarationTimeline>(`/api/v1/declarations/${declarationId}/timeline`),
  confirmCollection: (
    collectionId: string,
    evidenceId: string,
    measurementId: string,
    demoUserId: string,
  ) =>
    request<CollectionRecord>(`/api/v1/demo/collections/${collectionId}/confirm`, {
      method: "POST",
      body: JSON.stringify({ evidence_id: evidenceId, measurement_id: measurementId }),
    }, demoUserId),
  createVerification: (
    payload: {
      subject_type: "waste_lot";
      subject_id: string;
      outcome: "verified" | "non_conform";
      note: string;
      idempotency_key: string;
    },
    demoUserId: string,
  ) =>
    request<VerificationRecord>("/api/v1/demo/verifications", {
      method: "POST",
      body: JSON.stringify(payload),
    }, demoUserId),
  audit: (
    demoUserId: string,
    filters: {
      actor_user_id?: string;
      organization_id?: string;
      object_type?: string;
      correlation_id?: string;
    },
  ) => {
    const query = new URLSearchParams(filters);
    return request<AuditEvent[]>(`/api/v1/demo/audit?${query.toString()}`, undefined, demoUserId);
  },
};
