import type { Catalog, Declaration, Proposal, UnitMatch } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
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
};

