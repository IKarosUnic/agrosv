const PREFIX = "agrosv_v1_";
const CACHE_KEY = `${PREFIX}api_cache`;
const DRAFTS_KEY = `${PREFIX}field_obs_drafts`;
const BUDGETS_KEY = `${PREFIX}cost_budgets`;
const PREFS_KEY = `${PREFIX}preferences`;
const MAX_CACHE_ENTRIES = 45;

export interface CachedEntry<T = unknown> {
  data: T;
  cachedAt: string;
}

export interface FieldObservationDraft {
  draftId: string;
  createdAt: string;
  updatedAt: string;
  syncStatus: "draft" | "queued" | "synced" | "conflict" | "error";
  lastError?: string;
  serverObservationId?: string;
  payload: {
    observation_type: string;
    latitude: number;
    longitude: number;
    observed_on: string;
    crop_id?: string;
    crop_stage?: string;
    severity?: string;
    notes?: string;
    contributor_id: string;
    contributor_type?: string;
    publish_coordinates?: boolean;
  };
}

export interface SavedCostBudget {
  id: string;
  name: string;
  cropId: string;
  areaValue: number;
  areaUnit: "ha" | "mz";
  savedAt: string;
  items: Array<{
    category: string;
    description: string;
    amount: number;
    nature: "variable" | "fixed";
    per: "cycle" | "ha";
  }>;
  result?: Record<string, unknown>;
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage quota full: trim API cache and retry once
    if (key !== CACHE_KEY) {
      localStorage.removeItem(CACHE_KEY);
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch {
        // Ignore if still full
      }
    }
  }
}

export function loadPrefs<T>(fallback: T): T {
  return readJson<T>(PREFS_KEY, fallback);
}

export function savePrefs(prefs: unknown): void {
  writeJson(PREFS_KEY, prefs);
}

export function getCachedResponse<T>(url: string): CachedEntry<T> | null {
  const store = readJson<Record<string, CachedEntry<T>>>(CACHE_KEY, {});
  return store[url] ?? null;
}

export function setCachedResponse<T>(url: string, data: T): string {
  const cachedAt = new Date().toISOString();
  const store = readJson<Record<string, CachedEntry<unknown>>>(CACHE_KEY, {});
  store[url] = { data, cachedAt };
  const keys = Object.keys(store);
  if (keys.length > MAX_CACHE_ENTRIES) {
    const sorted = keys.sort((a, b) => store[a].cachedAt.localeCompare(store[b].cachedAt));
    for (const oldKey of sorted.slice(0, keys.length - MAX_CACHE_ENTRIES)) {
      delete store[oldKey];
    }
  }
  writeJson(CACHE_KEY, store);
  return cachedAt;
}

export function getLastSyncTimestamp(): string | null {
  const store = readJson<Record<string, CachedEntry>>(CACHE_KEY, {});
  const stamps = Object.values(store).map((v) => v.cachedAt).sort();
  return stamps.length ? stamps[stamps.length - 1] : null;
}

export function clearApiCache(): void {
  localStorage.removeItem(CACHE_KEY);
}

export function listFieldDrafts(): FieldObservationDraft[] {
  return readJson<FieldObservationDraft[]>(DRAFTS_KEY, []);
}

export function saveFieldDraft(draft: FieldObservationDraft): FieldObservationDraft[] {
  const all = listFieldDrafts();
  const idx = all.findIndex((d) => d.draftId === draft.draftId);
  const next = idx >= 0
    ? all.map((d, i) => (i === idx ? draft : d))
    : [draft, ...all];
  writeJson(DRAFTS_KEY, next);
  return next;
}

export function removeFieldDraft(draftId: string): FieldObservationDraft[] {
  const next = listFieldDrafts().filter((d) => d.draftId !== draftId);
  writeJson(DRAFTS_KEY, next);
  return next;
}

export function listSavedBudgets(): SavedCostBudget[] {
  return readJson<SavedCostBudget[]>(BUDGETS_KEY, []);
}

export function saveBudgetLocal(budget: SavedCostBudget): SavedCostBudget[] {
  const all = listSavedBudgets().filter((b) => b.id !== budget.id);
  const next = [budget, ...all].slice(0, 25);
  writeJson(BUDGETS_KEY, next);
  return next;
}

export function deleteBudgetLocal(id: string): SavedCostBudget[] {
  const next = listSavedBudgets().filter((b) => b.id !== id);
  writeJson(BUDGETS_KEY, next);
  return next;
}
