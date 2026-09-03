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
  AuthContext,
  AuthPortal,
  AdminAction,
  AdminSession,
  CustomerReservation,
  OperationsWorkspace,
  PendingMembership,
  ProductBatch,
  ProductCategory,
  QualityTest,
  TransformationRun,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
let csrfToken = "";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  const response = await fetch(`${API_URL}/api/v1/auth/csrf`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new ApiError("Protection CSRF indisponible.", response.status);
  const payload = await response.json() as { csrf_token: string };
  csrfToken = payload.csrf_token;
  return csrfToken;
}

async function request<T>(
  path: string,
  init?: RequestInit,
  demoUserId?: string,
): Promise<T> {
  const headers = new Headers(init?.headers);
  const method = (init?.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRF-Token", await ensureCsrf());
  }
  if (typeof init?.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (demoUserId) headers.set("X-Demo-User-ID", demoUserId);
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = Array.isArray(payload?.detail)
      ? payload.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(" · ")
      : payload?.detail;
    throw new ApiError(detail ?? `Erreur API (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (payload: {
    display_name: string;
    email: string;
    password: string;
    organization_name: string;
    organization_type: string;
  }) => request<AuthContext>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  login: (payload: { email: string; password: string }) =>
    request<AuthContext>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  me: () => request<AuthContext>("/api/v1/auth/me"),
  logout: () => request<{ status: string }>("/api/v1/auth/logout", { method: "POST" }),
  activateMembership: (membershipId: string) =>
    request<AuthContext>(`/api/v1/auth/memberships/${membershipId}/activate`, { method: "POST" }),
  authPortal: (role: string) => request<AuthPortal>(`/api/v1/auth/portal/${role}`),
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
    client_idempotency_key?: string;
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
  operationsWorkspace: (demoUserId: string) =>
    request<OperationsWorkspace>("/api/v1/operations/workspace", undefined, demoUserId),
  pendingMemberships: (demoUserId: string) =>
    request<PendingMembership[]>("/api/v1/admin/memberships/pending", undefined, demoUserId),
  adminHistory: (demoUserId: string) =>
    request<AdminAction[]>("/api/v1/admin/history", undefined, demoUserId),
  activeAdminSessions: (demoUserId: string) =>
    request<AdminSession[]>("/api/v1/admin/sessions", undefined, demoUserId),
  decideMembership: (
    membershipId: string,
    payload: { decision: "approved" | "refused"; reason: string; processing_unit_id?: string },
    demoUserId: string,
  ) => request<{ membership_id: string; decision: string; status: string }>(
    `/api/v1/admin/memberships/${membershipId}/decision`,
    { method: "POST", body: JSON.stringify(payload) },
    demoUserId,
  ),
  createInvitation: (
    payload: {
      email: string;
      role: "field_controller" | "bioloop_coordinator";
      organization_name: string;
      expires_in_hours: number;
    },
    demoUserId: string,
  ) => request<{
    id: string;
    token: string;
    organization_id: string;
    role: DemoWorkspace["actor"]["role"];
    expires_at: string;
    delivery: "local_demo_only";
  }>("/api/v1/admin/invitations", { method: "POST", body: JSON.stringify(payload) }, demoUserId),
  revokeMembership: (membershipId: string, reason: string, demoUserId: string) =>
    request<{ status: "revoked" }>(
      `/api/v1/admin/memberships/${membershipId}/revoke`,
      { method: "POST", body: JSON.stringify({ reason }) },
      demoUserId,
    ),
  revokeAdminSession: (sessionId: string, reason: string, demoUserId: string) =>
    request<{ status: "revoked" }>(
      `/api/v1/admin/sessions/${sessionId}/revoke`,
      { method: "POST", body: JSON.stringify({ reason }) },
      demoUserId,
    ),
  createTransformation: (
    payload: {
      processing_unit_id: string;
      process: string;
      started_at: string;
      inputs: Array<{
        lot_id: string;
        measured_quantity: string;
        unit: "kg";
        measurement_method: string;
        measured_at: string;
        evidence_ids: string[];
      }>;
    },
    demoUserId: string,
  ) => request<TransformationRun>(
    "/api/v1/transformations",
    { method: "POST", body: JSON.stringify(payload) },
    demoUserId,
  ),
  createProductOutputs: (
    transformationId: string,
    outputs: Array<{
      category: ProductCategory;
      quantity: string;
      unit: "kg" | "L" | "m3";
      measurement_method: string;
      measured_at: string;
      evidence_id?: string;
      location: string;
    }>,
    demoUserId: string,
  ) => request<ProductBatch[]>(
    `/api/v1/transformations/${transformationId}/outputs`,
    { method: "POST", body: JSON.stringify({ outputs }) },
    demoUserId,
  ),
  addQualityTest: (
    productId: string,
    payload: {
      parameter: string;
      value: string;
      unit: string;
      method: string;
      laboratory_or_actor: string;
      document_reference?: string;
      tested_at: string;
    },
    demoUserId: string,
  ) => request<QualityTest>(
    `/api/v1/products/${productId}/quality-tests`,
    { method: "POST", body: JSON.stringify(payload) },
    demoUserId,
  ),
  releaseProduct: (
    productId: string,
    payload: { status: "released" | "rejected"; note: string },
    demoUserId: string,
  ) => request<ProductBatch>(
    `/api/v1/products/${productId}/release`,
    { method: "POST", body: JSON.stringify(payload) },
    demoUserId,
  ),
  reserveProduct: (
    productId: string,
    payload: { quantity: string; unit: "kg" | "L" | "m3"; idempotency_key: string },
    demoUserId: string,
  ) => request<CustomerReservation>(
    `/api/v1/products/${productId}/reservations`,
    { method: "POST", body: JSON.stringify(payload) },
    demoUserId,
  ),
  cancelReservation: (reservationId: string, demoUserId: string) =>
    request<CustomerReservation>(
      `/api/v1/reservations/${reservationId}/cancel`,
      { method: "POST" },
      demoUserId,
    ),
  productProvenance: (productId: string, demoUserId: string) =>
    request<Record<string, unknown>>(`/api/v1/products/${productId}/provenance`, undefined, demoUserId),
};
