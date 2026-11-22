import { apiPost } from "../api/client";
import type { FieldObservation } from "../../types/api";
import { listFieldDrafts, saveFieldDraft, type FieldObservationDraft } from "./storage";

export interface SyncSummary {
  attempted: number;
  synced: number;
  conflicts: number;
  errors: number;
  drafts: FieldObservationDraft[];
}

export async function syncQueuedFieldObservations(): Promise<SyncSummary> {
  const drafts = listFieldDrafts();
  const queued = drafts.filter((d) => d.syncStatus === "queued" || d.syncStatus === "error");
  let synced = 0;
  let conflicts = 0;
  let errors = 0;
  let current = drafts;

  for (const draft of queued) {
    try {
      const res = await apiPost<FieldObservation>("/api/monitoring/field-observations", draft.payload);
      const duplicateOf = (res as unknown as { quality_checks?: { duplicate_of?: string | null } })
        ?.quality_checks?.duplicate_of;
      current = saveFieldDraft({
        ...draft,
        updatedAt: new Date().toISOString(),
        syncStatus: duplicateOf ? "conflict" : "synced",
        serverObservationId: res.observation_id,
        lastError: duplicateOf ? `Posible duplicado detectado en servidor (${duplicateOf})` : undefined,
      });
      if (duplicateOf) conflicts += 1;
      else synced += 1;
    } catch (err) {
      errors += 1;
      const msg = err instanceof Error ? err.message : "Error de sincronización";
      current = saveFieldDraft({
        ...draft,
        updatedAt: new Date().toISOString(),
        syncStatus: "error",
        lastError: msg,
      });
    }
  }

  return {
    attempted: queued.length,
    synced,
    conflicts,
    errors,
    drafts: current,
  };
}
