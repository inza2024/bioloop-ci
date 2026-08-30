import { api } from "./api";


const DB_NAME = "bioloop-pilot-offline-v1";
const STORE_NAME = "declarations";
const DB_VERSION = 1;

export type OfflineStatus = "pending" | "syncing" | "synced" | "failed";

export interface OfflineDeclaration {
  id: string;
  client_idempotency_key: string;
  payload: {
    producer_id: string;
    waste_type_id: string;
    quantity_kg: string;
    frequency: string;
    availability_date: string;
    notes: string;
    client_idempotency_key: string;
  };
  status: OfflineStatus;
  created_at: string;
  updated_at: string;
  server_declaration_id?: string;
  error?: string;
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      const store = database.createObjectStore(STORE_NAME, { keyPath: "id" });
      store.createIndex("status", "status");
      store.createIndex("idempotency", "client_idempotency_key", { unique: true });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function put(item: OfflineDeclaration): Promise<void> {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).put(item);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
  database.close();
  window.dispatchEvent(new Event("bioloop-offline-queue-change"));
}

export async function queueDeclaration(
  payload: Omit<OfflineDeclaration["payload"], "client_idempotency_key">,
): Promise<OfflineDeclaration> {
  const id = crypto.randomUUID();
  const key = `offline:${id}`;
  const now = new Date().toISOString();
  const item: OfflineDeclaration = {
    id,
    client_idempotency_key: key,
    payload: { ...payload, client_idempotency_key: key },
    status: "pending",
    created_at: now,
    updated_at: now,
  };
  await put(item);
  return item;
}

export async function listQueuedDeclarations(): Promise<OfflineDeclaration[]> {
  const database = await openDatabase();
  const items = await new Promise<OfflineDeclaration[]>((resolve, reject) => {
    const request = database.transaction(STORE_NAME).objectStore(STORE_NAME).getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  database.close();
  return items.sort((left, right) => left.created_at.localeCompare(right.created_at));
}

export async function syncQueuedDeclarations(): Promise<void> {
  if (!navigator.onLine) return;
  const items = (await listQueuedDeclarations()).filter(
    (item) => item.status === "pending" || item.status === "failed",
  );
  for (const item of items) {
    await put({ ...item, status: "syncing", updated_at: new Date().toISOString() });
    try {
      const declaration = await api.createDeclaration(item.payload);
      await put({
        ...item,
        status: "synced",
        server_declaration_id: declaration.id,
        error: undefined,
        updated_at: new Date().toISOString(),
      });
    } catch (reason) {
      await put({
        ...item,
        status: navigator.onLine ? "failed" : "pending",
        error: navigator.onLine && reason instanceof Error ? reason.message : undefined,
        updated_at: new Date().toISOString(),
      });
      if (!navigator.onLine) break;
    }
  }
}
