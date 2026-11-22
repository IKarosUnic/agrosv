import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiGet, clearMemoryCache } from "../services/api/client";
import {
  clearApiCache,
  getLastSyncTimestamp,
  listFieldDrafts,
  listSavedBudgets,
  saveBudgetLocal,
  saveFieldDraft,
} from "../services/offline/storage";
import { syncQueuedFieldObservations } from "../services/offline/sync";

describe("Offline caching, draft persistence, and synchronization", () => {
  beforeEach(() => {
    clearMemoryCache();
    clearApiCache();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("serves cached response with cachedAt timestamp when network fails", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const live = await apiGet<{ status: string }>("/api/meta");
    expect(live.fromCache).toBe(false);
    expect(live.data.status).toBe("ok");
    expect(getLastSyncTimestamp()).not.toBeNull();

    fetchMock.mockRejectedValueOnce(new Error("Network down"));
    const offline = await apiGet<{ status: string }>("/api/meta");
    expect(offline.fromCache).toBe(true);
    expect(offline.cachedAt).not.toBeNull();
    expect(offline.data.status).toBe("ok");
  });

  it("queues field observations locally and handles sync + duplicate conflict", async () => {
    saveFieldDraft({
      draftId: "D-1",
      createdAt: "2026-11-22T10:00:00Z",
      updatedAt: "2026-11-22T10:00:00Z",
      syncStatus: "queued",
      payload: {
        observation_type: "water_stress",
        latitude: 13.69,
        longitude: -89.19,
        observed_on: "2026-11-20",
        contributor_id: "prod-1",
      },
    });
    saveFieldDraft({
      draftId: "D-2",
      createdAt: "2026-11-22T10:01:00Z",
      updatedAt: "2026-11-22T10:01:00Z",
      syncStatus: "queued",
      payload: {
        observation_type: "pest_suspected",
        latitude: 13.69,
        longitude: -89.19,
        observed_on: "2026-11-20",
        contributor_id: "prod-1",
      },
    });

    const fetchMock = vi.fn().mockImplementation((_url: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body ?? "{}")) as { observation_type?: string };
      const duplicate_of = body.observation_type === "pest_suspected" ? "FLD-0" : null;
      return Promise.resolve(
        new Response(JSON.stringify({ observation_id: duplicate_of ? "FLD-2" : "FLD-1", quality_checks: { duplicate_of } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const summary = await syncQueuedFieldObservations();
    expect(summary.attempted).toBe(2);
    expect(summary.synced).toBe(1);
    expect(summary.conflicts).toBe(1);
    expect(listFieldDrafts().find((d) => d.draftId === "D-2")?.syncStatus).toBe("conflict");
  });

  it("persists local production cost budgets", () => {
    saveBudgetLocal({
      id: "B-1",
      name: "Maíz 1 mz",
      cropId: "maize",
      areaValue: 1,
      areaUnit: "mz",
      savedAt: "2026-11-22T10:00:00Z",
      items: [{ category: "seeds", description: "Semilla", amount: 85, nature: "variable", per: "cycle" }],
    });
    expect(listSavedBudgets()).toHaveLength(1);
  });
});
