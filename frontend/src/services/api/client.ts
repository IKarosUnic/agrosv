import { getCachedResponse, setCachedResponse } from "../offline/storage";

export const API_BASE = import.meta.env.VITE_API ?? "";

export class ApiError extends Error {
  status: number;
  detail: string;
  unavailable: boolean;

  constructor(message: string, status: number, detail = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.unavailable = status === 503 || status === 404 || status === 0;
  }
}

export interface ApiResult<T> {
  data: T;
  fromCache: boolean;
  cachedAt: string | null;
}

const memCache = new Map<string, { data: unknown; expiresAt: number }>();

function extractErrorMessage(body: unknown, status: number): string {
  if (typeof body === "string" && body.trim()) return body;
  if (body && typeof body === "object") {
    const rec = body as Record<string, unknown>;
    if (typeof rec.detail === "string") return rec.detail;
    if (rec.detail && typeof rec.detail === "object") return JSON.stringify(rec.detail);
    if (typeof rec.error === "string") return rec.error;
    if (typeof rec.message === "string") return rec.message;
  }
  if (status === 503) return "Servicio o conjunto de datos no disponible en el servidor.";
  if (status === 404) return "Recurso o endpoint no encontrado.";
  return `Error HTTP ${status}`;
}

export async function apiGet<T>(
  path: string,
  options?: {
    signal?: AbortSignal;
    ttlMs?: number;
    persistOffline?: boolean;
    timeoutMs?: number;
  },
): Promise<ApiResult<T>> {
  const url = `${API_BASE}${path}`;
  const ttlMs = options?.ttlMs ?? 0;
  const persistOffline = options?.persistOffline ?? true;

  if (ttlMs > 0) {
    const hit = memCache.get(url);
    if (hit && hit.expiresAt > Date.now()) {
      return { data: hit.data as T, fromCache: false, cachedAt: null };
    }
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options?.timeoutMs ?? 20000);
  const onParentAbort = () => controller.abort();
  options?.signal?.addEventListener("abort", onParentAbort, { once: true });

  try {
    const res = await fetch(url, { signal: controller.signal });
    const ct = res.headers.get("content-type") ?? "";
    const parsed = ct.includes("application/json") ? await res.json() : await res.text();
    if (!res.ok) {
      throw new ApiError(extractErrorMessage(parsed, res.status), res.status);
    }
    if (ttlMs > 0) {
      memCache.set(url, { data: parsed, expiresAt: Date.now() + ttlMs });
    }
    if (persistOffline) {
      setCachedResponse(url, parsed);
    }
    return { data: parsed as T, fromCache: false, cachedAt: null };
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError" && options?.signal?.aborted) {
      throw err;
    }
    if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
      throw err;
    }
    if (persistOffline) {
      const cached = getCachedResponse<T>(url);
      if (cached) {
        return { data: cached.data, fromCache: true, cachedAt: cached.cachedAt };
      }
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      navigator.onLine
        ? "No se pudo conectar con la API de AGROSV."
        : "Sin conexión a la red y sin copia en caché local.",
      0,
    );
  } finally {
    clearTimeout(timeoutId);
    options?.signal?.removeEventListener("abort", onParentAbort);
  }
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options?.timeoutMs ?? 25000);
  const onParentAbort = () => controller.abort();
  options?.signal?.addEventListener("abort", onParentAbort, { once: true });

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const ct = res.headers.get("content-type") ?? "";
    const parsed = ct.includes("application/json") ? await res.json() : await res.text();
    if (!res.ok) {
      throw new ApiError(extractErrorMessage(parsed, res.status), res.status);
    }
    return parsed as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError" && options?.signal?.aborted) {
      throw err;
    }
    throw new ApiError(
      navigator.onLine
        ? "Error de red al consultar el motor científico."
        : "Operación no disponible sin conexión.",
      0,
    );
  } finally {
    clearTimeout(timeoutId);
    options?.signal?.removeEventListener("abort", onParentAbort);
  }
}

export function clearMemoryCache(): void {
  memCache.clear();
}
