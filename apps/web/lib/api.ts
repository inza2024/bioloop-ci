import type {
  Catalog,
  Declaration,
  DeclarationTimeline,
  EvidenceRecord,
  LotDecision,
  LotRecord,
  MeasurementRecord,
  Proposal,
  RecalculationResult,
  UnitMatch,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof init?.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
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
  createDeclaration: (payload: {
    producer_id: string;
    waste_type_id: string;
    quantity_kg: string;
    frequency: string;
    availability_date: string;
    notes: string;
  }) =>
    request<Declaration>("/api/v1/declarations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  matches: (declarationId: string) =>
    request<UnitMatch[]>(`/api/v1/declarations/${declarationId}/matches`),
  proposal: (declarationId: string, processingUnitId: string) =>
    request<Proposal>(`/api/v1/declarations/${declarationId}/proposal`, {
      method: "POST",
      body: JSON.stringify({ processing_unit_id: processingUnitId }),
    }),
  createEvidence: (
    declarationId: string,
    file: File,
    metadata: {
      category: EvidenceRecord["category"];
      captured_at?: string;
      note: string;
    },
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
  ) =>
    request<MeasurementRecord>(`/api/v1/declarations/${declarationId}/measurements`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createLot: (
    declarationId: string,
    payload: { measurement_id: string; processing_unit_id: string; evidence_ids: string[] },
  ) =>
    request<LotRecord>(`/api/v1/declarations/${declarationId}/lots`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  decideLot: (
    lotId: string,
    payload: { decision: "accepted" | "refused"; reason: string; note: string },
  ) =>
    request<LotDecision>(`/api/v1/lots/${lotId}/decision`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
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
};
