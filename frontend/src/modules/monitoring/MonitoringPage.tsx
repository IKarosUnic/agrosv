import React, { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import {
  listFieldDrafts,
  removeFieldDraft,
  saveFieldDraft,
  type FieldObservationDraft,
} from "../../services/offline/storage";
import { syncQueuedFieldObservations } from "../../services/offline/sync";
import { useApp } from "../../stores/AppContext";
import { fmtCoord } from "../../utils/format";
import { PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  EmptyState,
  ErrorState,
  EvidenceBadge,
  LoadingState,
} from "../../components/data-status/DataStatus";
import type { FieldObservation } from "../../types/api";

type TabId = "satellite" | "health" | "pests" | "field";

const OBS_TYPES = [
  { id: "crop_observation", label: "Observación general de cultivo" },
  { id: "pest_suspected", label: "Sospecha de plaga" },
  { id: "disease_symptoms", label: "Síntomas de enfermedad" },
  { id: "water_stress", label: "Estrés hídrico / sequía" },
  { id: "flood_damage", label: "Daño por inundación / exceso" },
  { id: "heat_damage", label: "Daño por calor" },
  { id: "crop_loss", label: "Pérdida de cultivo" },
  { id: "management_practice", label: "Práctica de manejo" },
];

export default function MonitoringPage() {
  const { selectedLocation, selectedCropId, isOnline } = useApp();
  const [tab, setTab] = useState<TabId>("field");

  // Satellites & Indices
  const [sources, setSources] = useState<Array<Record<string, unknown>>>([]);
  const [indices, setIndices] = useState<Array<Record<string, unknown>>>([]);
  const [indexName, setIndexName] = useState("ndvi");
  const [nirVal, setNirVal] = useState("0.45");
  const [redVal, setRedVal] = useState("0.12");
  const [indexResult, setIndexResult] = useState<Record<string, unknown> | null>(null);

  // Crop health
  const [ndviAnom, setNdviAnom] = useState("-1.2");
  const [ndmiAnom, setNdmiAnom] = useState("-0.8");
  const [rainAnom, setRainAnom] = useState("-1.5");
  const [healthRes, setHealthRes] = useState<Record<string, unknown> | null>(null);

  // Pests & diseases
  const [pests, setPests] = useState<Array<Record<string, unknown>>>([]);
  const [diseases, setDiseases] = useState<Array<Record<string, unknown>>>([]);
  const [loadingCatalogs, setLoadingCatalogs] = useState(false);

  // Field observations + offline drafts
  const [serverObs, setServerObs] = useState<FieldObservation[]>([]);
  const [drafts, setDrafts] = useState<FieldObservationDraft[]>(() => listFieldDrafts());
  const [obsType, setObsType] = useState("crop_observation");
  const [observedOn, setObservedOn] = useState(new Date().toISOString().slice(0, 10));
  const [severity, setSeverity] = useState("moderate");
  const [contributorId, setContributorId] = useState("productor-sv");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [obsMsg, setObsMsg] = useState<string | null>(null);
  const [obsErr, setObsErr] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    if (tab === "satellite") {
      Promise.allSettled([agrosvApi.monitoringSources(ac.signal), agrosvApi.monitoringIndices(ac.signal)]).then(([s, i]) => {
        if (s.status === "fulfilled") setSources((s.value.data.sources as Array<Record<string, unknown>>) ?? []);
        if (i.status === "fulfilled") setIndices((i.value.data.indices as Array<Record<string, unknown>>) ?? []);
      });
    } else if (tab === "pests") {
      setLoadingCatalogs(true);
      Promise.allSettled([agrosvApi.pests(undefined, ac.signal), agrosvApi.diseases(undefined, ac.signal)]).then(([p, d]) => {
        if (p.status === "fulfilled") setPests((p.value.data.pests as Array<Record<string, unknown>>) ?? []);
        if (d.status === "fulfilled") setDiseases((d.value.data.diseases as Array<Record<string, unknown>>) ?? []);
        setLoadingCatalogs(false);
      });
    } else if (tab === "field") {
      agrosvApi.fieldObservations(ac.signal)
        .then(({ data }) => setServerObs(data.observations ?? []))
        .catch(() => undefined);
    }
    return () => ac.abort();
  }, [tab]);

  const computeCustomIndex = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await agrosvApi.computeIndex({
      name: indexName,
      bands: { NIR: [[Number(nirVal)]], RED: [[Number(redVal)]], GREEN: [[0.1]], SWIR1: [[0.2]], BLUE: [[0.08]] },
      sensor: "sentinel2_msi",
    });
    setIndexResult(res);
  };

  const evaluateHealth = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await agrosvApi.cropHealthAssess({
      crop_id: selectedCropId,
      stage: "vegetative",
      ndvi_anomaly: Number(ndviAnom),
      ndmi_anomaly: Number(ndmiAnom),
      rainfall_anomaly: Number(rainAnom),
      n_observations: 6,
      baseline_years: 3,
    });
    setHealthRes(res);
  };

  const buildDraft = (syncStatus: FieldObservationDraft["syncStatus"]): FieldObservationDraft => {
    const now = new Date().toISOString();
    return {
      draftId: `DRAFT-${Date.now()}`,
      createdAt: now,
      updatedAt: now,
      syncStatus,
      payload: {
        observation_type: obsType,
        latitude: selectedLocation.lat,
        longitude: selectedLocation.lon,
        observed_on: observedOn,
        crop_id: selectedCropId,
        severity,
        notes: notes.trim() || undefined,
        contributor_id: contributorId.trim() || "productor-sv",
        contributor_type: "community",
      },
    };
  };

  const handleFieldSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setObsErr(null);
    setObsMsg(null);
    if (!isOnline) {
      const next = saveFieldDraft(buildDraft("queued"));
      setDrafts(next);
      setNotes("");
      setObsMsg("Sin conexión: observación guardada en cola local para sincronizar automáticamente.");
      return;
    }
    setSubmitting(true);
    try {
      const created = await agrosvApi.submitFieldObservation(buildDraft("queued").payload);
      setServerObs((prev) => [created, ...prev]);
      setNotes("");
      setObsMsg(`Observación registrada (${created.observation_id}) con estado "${created.status}". No constituye confirmación científica automática.`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error enviando observación";
      setObsErr(msg);
      setDrafts(saveFieldDraft({ ...buildDraft("error"), lastError: msg }));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSyncQueue = async () => {
    const summary = await syncQueuedFieldObservations();
    setDrafts(summary.drafts);
    setObsMsg(`Sincronización: ${summary.synced} enviadas, ${summary.conflicts} posibles duplicados, ${summary.errors} errores.`);
    agrosvApi.fieldObservations().then(({ data }) => setServerObs(data.observations ?? [])).catch(() => undefined);
  };

  return (
    <div className="stack-md">
      <PageHeader
        title="Monitoreo Satelital, Sanidad y Campo (Fase 7)"
        subtitle={`Ubicación: ${selectedLocation.label} (${fmtCoord(selectedLocation.lat, selectedLocation.lon)}) · Cultivo: ${selectedCropId}`}
      />

      <div className="tabs" role="tablist" aria-label="Submódulos de monitoreo">
        {([
          ["field", "Observaciones de campo"],
          ["pests", "Plagas y enfermedades"],
          ["satellite", "Satélites e índices"],
          ["health", "Evaluador de sanidad"],
        ] as [TabId, string][]).map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className="tab-btn" onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "field" && (
        <div className="grid-2">
          <form onSubmit={handleFieldSubmit} className="card stack-sm">
            <div className="row-wrap" style={{ justifyContent: "space-between" }}>
              <h2 className="card-title">Reportar observación de campo</h2>
              <EvidenceBadge evidenceClass="field_observation" />
            </div>
            <p className="card-subtitle">
              Los reportes comunitarios quedan sujetos a revisión y control de calidad.
            </p>

            <label className="field">
              <span className="field-label">Tipo de observación</span>
              <select className="select" value={obsType} onChange={(e) => setObsType(e.target.value)}>
                {OBS_TYPES.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
              </select>
            </label>

            <div className="grid-2">
              <label className="field">
                <span className="field-label">Fecha observada</span>
                <input type="date" className="input" value={observedOn} onChange={(e) => setObservedOn(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Severidad percibida</span>
                <select className="select" value={severity} onChange={(e) => setSeverity(e.target.value)}>
                  <option value="low">Baja</option>
                  <option value="moderate">Moderada</option>
                  <option value="high">Alta</option>
                </select>
              </label>
            </div>

            <label className="field">
              <span className="field-label">Identificador de colaborador</span>
              <input className="input" value={contributorId} onChange={(e) => setContributorId(e.target.value)} />
            </label>

            <label className="field">
              <span className="field-label">Síntomas, manejo o descripción</span>
              <textarea className="textarea" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Describe hojas, plaga observada, humedad o daño…" />
            </label>

            <div className="row-wrap">
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? "Enviando…" : isOnline ? "Enviar observación" : "Guardar en cola offline"}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setDrafts(saveFieldDraft(buildDraft("draft")));
                  setNotes("");
                  setObsMsg("Borrador guardado localmente.");
                }}
              >
                Guardar borrador
              </button>
            </div>

            {obsMsg && <div className="callout callout--info">{obsMsg}</div>}
            {obsErr && <ErrorState message={obsErr} />}
          </form>

          <div className="stack-md">
            <section className="card">
              <div className="row-wrap" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                <h2 className="card-title">Borradores y cola de sincronización ({drafts.length})</h2>
                <button type="button" className="btn btn-sm" onClick={handleSyncQueue} disabled={!isOnline}>
                  Sincronizar cola
                </button>
              </div>
              {drafts.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--ink-muted)", margin: 0 }}>Sin borradores locales.</p>
              ) : (
                <div className="stack-sm">
                  {drafts.map((d) => (
                    <div key={d.draftId} style={{ padding: 10, borderRadius: 8, background: "var(--bg-subtle)", fontSize: 12.5 }}>
                      <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                        <strong>{d.payload.observation_type} · {d.payload.observed_on}</strong>
                        <DataStatusBadge
                          tone={d.syncStatus === "synced" ? "ok" : d.syncStatus === "conflict" || d.syncStatus === "error" ? "warn" : "info"}
                          label={d.syncStatus}
                        />
                      </div>
                      {d.lastError && <div style={{ color: "var(--status-warn)", marginTop: 4 }}>{d.lastError}</div>}
                      <button type="button" className="btn btn-sm" style={{ marginTop: 6 }} onClick={() => setDrafts(removeFieldDraft(d.draftId))}>
                        Eliminar
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="card">
              <h2 className="card-title">Observaciones registradas en sesión ({serverObs.length})</h2>
              {serverObs.length === 0 ? (
                <EmptyState
                  title="Sin observaciones registradas en el servidor"
                  description="Las observaciones enviadas aparecerán aquí con su estado (received, needs_evidence, in_review, accepted, rejected)."
                />
              ) : (
                <div className="stack-sm" style={{ marginTop: 8 }}>
                  {serverObs.map((o) => (
                    <div key={o.observation_id} style={{ padding: 10, borderRadius: 8, border: "1px solid var(--border-subtle)", fontSize: 13 }}>
                      <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                        <strong>{o.observation_id} · {o.observation_type}</strong>
                        <DataStatusBadge tone={o.status === "accepted" ? "ok" : "warn"} label={o.status} />
                      </div>
                      <div style={{ color: "var(--ink-muted)", marginTop: 4 }}>
                        Fecha: {o.observed_on} · Cultivo: {o.crop_id ?? "—"} · Verificado científicamente: {o.verified_scientific_record ? "Sí" : "No"}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {tab === "pests" && (
        <div className="stack-md">
          <div className="callout callout--info">
            <strong>Idoneidad ambiental ≠ presencia confirmada:</strong> el catálogo distingue entre presencia nacional confirmada, registro regional y riesgo ambiental teórico.
          </div>
          {loadingCatalogs ? (
            <LoadingState />
          ) : (
            <div className="grid-2">
              <section className="card">
                <h2 className="card-title">Plagas documentadas ({pests.length})</h2>
                <div className="stack-sm" style={{ marginTop: 10 }}>
                  {pests.map((p) => {
                    const dist = (p.distribution ?? {}) as { presence_scope?: string };
                    return (
                      <article key={String(p.pest_id)} style={{ padding: 10, borderRadius: 8, background: "var(--bg-subtle)" }}>
                        <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                          <strong>{((p.common_names as string[]) ?? [])[0] ?? String(p.pest_id)}</strong>
                          <DataStatusBadge tone={dist.presence_scope === "national_confirmed" ? "warn" : "info"} label={String(dist.presence_scope ?? "documentado")} />
                        </div>
                        <div style={{ fontSize: 12, fontStyle: "italic", color: "var(--ink-muted)" }}>{String(p.scientific_name)}</div>
                        <div style={{ fontSize: 12.5, marginTop: 4 }}>Cultivos: {((p.affected_crops as string[]) ?? []).join(", ")}</div>
                        <div style={{ fontSize: 12.5, marginTop: 4 }}>{String(p.damage)}</div>
                      </article>
                    );
                  })}
                </div>
              </section>

              <section className="card">
                <h2 className="card-title">Enfermedades documentadas ({diseases.length})</h2>
                <div className="stack-sm" style={{ marginTop: 10 }}>
                  {diseases.map((d) => {
                    const dist = (d.distribution ?? {}) as { presence_scope?: string };
                    return (
                      <article key={String(d.disease_id)} style={{ padding: 10, borderRadius: 8, background: "var(--bg-subtle)" }}>
                        <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                          <strong>{((d.common_names as string[]) ?? [])[0] ?? String(d.disease_id)}</strong>
                          <DataStatusBadge tone={dist.presence_scope === "national_confirmed" ? "warn" : "info"} label={String(dist.presence_scope ?? "documentado")} />
                        </div>
                        <div style={{ fontSize: 12, fontStyle: "italic", color: "var(--ink-muted)" }}>{String(d.scientific_name)}</div>
                        <div style={{ fontSize: 12.5, marginTop: 4 }}>Cultivos: {((d.affected_crops as string[]) ?? []).join(", ")}</div>
                        <div style={{ fontSize: 12.5, marginTop: 4 }}>{String(d.symptoms ?? d.damage ?? "")}</div>
                      </article>
                    );
                  })}
                </div>
              </section>
            </div>
          )}
        </div>
      )}

      {tab === "satellite" && (
        <div className="stack-md">
          <div className="callout callout--warn">
            <strong>Sin escenas satelitales ingeridas en disco:</strong> <code>satellite_scenes_ingested: false</code>. Puedes consultar las fuentes evaluadas, fórmulas de índices espectrales y calcular índices sobre reflectancias aportadas.
          </div>
          <div className="grid-2">
            <section className="card">
              <h2 className="card-title">Fuentes satelitales evaluadas</h2>
              <ul style={{ margin: "10px 0 0 18px", padding: 0, fontSize: 13, display: "grid", gap: 6 }}>
                {sources.map((s) => (
                  <li key={String(s.source_id)}>
                    <strong>{String(s.name)}</strong> · {String(s.resolution_m ?? s.spatial_resolution ?? "")} · Estado: <span className="mono">{String(s.status ?? "evaluated")}</span>
                  </li>
                ))}
              </ul>
            </section>
            <section className="card">
              <h2 className="card-title">Calculadora de índices espectrales</h2>
              <form onSubmit={computeCustomIndex} className="stack-sm" style={{ marginTop: 8 }}>
                <label className="field">
                  <span className="field-label">Índice</span>
                  <select className="select" value={indexName} onChange={(e) => setIndexName(e.target.value)}>
                    {(indices.length ? indices : [{ name: "ndvi" }, { name: "evi" }, { name: "savi" }, { name: "ndwi" }, { name: "ndmi" }]).map((idx) => (
                      <option key={String(idx.name)} value={String(idx.name)}>{String(idx.name).toUpperCase()}</option>
                    ))}
                  </select>
                </label>
                <div className="grid-2">
                  <label className="field">
                    <span className="field-label">Reflectancia NIR (0–1)</span>
                    <input type="number" step="0.01" className="input" value={nirVal} onChange={(e) => setNirVal(e.target.value)} />
                  </label>
                  <label className="field">
                    <span className="field-label">Reflectancia RED (0–1)</span>
                    <input type="number" step="0.01" className="input" value={redVal} onChange={(e) => setRedVal(e.target.value)} />
                  </label>
                </div>
                <button type="submit" className="btn btn-primary btn-sm">Calcular índice</button>
              </form>
              {indexResult && (
                <pre style={{ marginTop: 10, padding: 10, borderRadius: 8, background: "var(--bg-subtle)", fontSize: 12, overflowX: "auto" }}>
                  {JSON.stringify(indexResult, null, 2)}
                </pre>
              )}
            </section>
          </div>
        </div>
      )}

      {tab === "health" && (
        <div className="stack-md">
          <div className="callout callout--info">
            <strong>Interpretación transparente:</strong> una anomalía espectral o climática nunca equivale a un diagnóstico agronómico confirmado.
          </div>
          <form onSubmit={evaluateHealth} className="card stack-sm">
            <h2 className="card-title">Evaluador de estado de cultivo ({selectedCropId})</h2>
            <div className="grid-3">
              <label className="field">
                <span className="field-label">Anomalía NDVI (z-score)</span>
                <input type="number" step="0.1" className="input" value={ndviAnom} onChange={(e) => setNdviAnom(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Anomalía NDMI (z-score)</span>
                <input type="number" step="0.1" className="input" value={ndmiAnom} onChange={(e) => setNdmiAnom(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Anomalía lluvia (z-score)</span>
                <input type="number" step="0.1" className="input" value={rainAnom} onChange={(e) => setRainAnom(e.target.value)} />
              </label>
            </div>
            <div>
              <button type="submit" className="btn btn-primary">Evaluar estado</button>
            </div>
          </form>
          {healthRes && (
            <div className="card">
              <pre style={{ margin: 0, fontSize: 12.5, overflowX: "auto" }}>{JSON.stringify(healthRes, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
