import React, { useEffect, useMemo, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { fmtCoord } from "../../utils/format";
import { MetricCard, PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  ErrorState,
  EvidenceBadge,
  LoadingState,
  SourceAttribution,
  UncertaintyPanel,
} from "../../components/data-status/DataStatus";
import type { CropDetail, CropParam, CropSummary, EngineEnvelope, SuitabilityResult } from "../../types/api";

type TabId = "catalog" | "detail" | "suitability" | "simulation";

function renderParam(p?: CropParam): string {
  if (!p || p.value === null || p.value === undefined) return "Sin dato (GAP)";
  if (Array.isArray(p.value)) return `${p.value.join(" – ")} ${p.unit}`.trim();
  if (typeof p.value === "boolean") return p.value ? "Sí" : "No";
  return `${p.value} ${p.unit}`.trim();
}

export default function CropsPage() {
  const { selectedLocation, selectedCropId, setSelectedCropId, simpleMode } = useApp();
  const [tab, setTab] = useState<TabId>("catalog");
  const [search, setSearch] = useState("");
  const [cropTypeFilter, setCropTypeFilter] = useState("");
  const [crops, setCrops] = useState<CropSummary[]>([]);
  const [cropTypes, setCropTypes] = useState<string[]>([]);
  const [detail, setDetail] = useState<CropDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Suitability
  const [system, setSystem] = useState<"rainfed" | "irrigated" | "urban" | "periurban">("rainfed");
  const [irrigationAvail, setIrrigationAvail] = useState(false);
  const [suitEnv, setSuitEnv] = useState<EngineEnvelope<SuitabilityResult> | null>(null);
  const [suitLoading, setSuitLoading] = useState(false);

  // Simulation
  const [adapters, setAdapters] = useState<Record<string, Record<string, unknown>>>({});
  const [plantingDate, setPlantingDate] = useState("2024-05-15");
  const [awcMmM, setAwcMmM] = useState("140");
  const [rootCm, setRootCm] = useState("60");
  const [allowRefKc, setAllowRefKc] = useState(true);
  const [simEnv, setSimEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);

  // Nutrients (N-P-K demand)
  const [targetYield, setTargetYield] = useState("3.0");
  const [nutrientData, setNutrientData] = useState<Record<string, unknown> | null>(null);
  const [nutrientLoading, setNutrientLoading] = useState(false);

  useEffect(() => {
    const ac = new AbortController();
    setLoadingList(true);
    agrosvApi.crops(cropTypeFilter || undefined, undefined, ac.signal)
      .then(({ data }) => {
        setCrops(data.crops ?? []);
        if (data.types) setCropTypes(data.types);
        setLoadingList(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "No se pudo cargar catálogo de cultivos");
        setLoadingList(false);
      });
    return () => ac.abort();
  }, [cropTypeFilter]);

  useEffect(() => {
    const ac = new AbortController();
    agrosvApi.cropDetail(selectedCropId, ac.signal)
      .then(({ data }) => {
        const d = ((data as unknown as { result?: CropDetail }).result ?? data) as CropDetail;
        setDetail(d);
      })
      .catch(() => setDetail(null));
    return () => ac.abort();
  }, [selectedCropId]);

  useEffect(() => {
    if (tab !== "detail") return;
    const ac = new AbortController();
    const yieldVal = Number(targetYield);
    if (!yieldVal || yieldVal <= 0) return;
    setNutrientLoading(true);
    agrosvApi.nutrientDemand(selectedCropId, yieldVal, "user_reference", ac.signal)
      .then(({ data }) => {
        setNutrientData((data as unknown as { demand_kg_ha?: Record<string, unknown> })?.demand_kg_ha ?? null);
        setNutrientLoading(false);
      })
      .catch(() => {
        setNutrientData(null);
        setNutrientLoading(false);
      });
    return () => ac.abort();
  }, [tab, selectedCropId, targetYield]);

  useEffect(() => {
    if (tab !== "suitability") return;
    const ac = new AbortController();
    setSuitLoading(true);
    agrosvApi.cropSuitability(selectedCropId, selectedLocation.lat, selectedLocation.lon, system, irrigationAvail, ac.signal)
      .then(({ data }) => {
        setSuitEnv(data);
        setSuitLoading(false);
      })
      .catch(() => {
        setSuitEnv(null);
        setSuitLoading(false);
      });
    return () => ac.abort();
  }, [tab, selectedCropId, selectedLocation.lat, selectedLocation.lon, system, irrigationAvail]);

  useEffect(() => {
    if (tab !== "simulation") return;
    const ac = new AbortController();
    agrosvApi.simulationAdapters(ac.signal)
      .then(({ data }) => {
        const det = (data.detection as Record<string, unknown> | undefined)?.adapters as Record<string, Record<string, unknown>> | undefined;
        if (det) setAdapters(det);
      })
      .catch(() => undefined);
    return () => ac.abort();
  }, [tab]);

  const filteredCrops = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return crops;
    return crops.filter((c) =>
      `${c.crop_id} ${c.scientific_name} ${c.local_names.join(" ")}`.toLowerCase().includes(q),
    );
  }, [crops, search]);

  const runSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimLoading(true);
    setSimError(null);
    try {
      const res = await agrosvApi.simulateCrop({
        crop_id: selectedCropId,
        planting_date: plantingDate,
        awc_mm_per_m: Number(awcMmM),
        root_depth_cm: Number(rootCm),
        allow_reference_kc: allowRefKc,
        adapter: "agrosv_water_balance",
      });
      setSimEnv(res);
    } catch (err) {
      setSimError(err instanceof Error ? err.message : "Error ejecutando simulación");
      setSimEnv(null);
    } finally {
      setSimLoading(false);
    }
  };

  const suit = suitEnv?.result;
  const simRes = (simEnv?.result ?? {}) as Record<string, unknown>;

  return (
    <div className="stack-md">
      <PageHeader
        title="Inteligencia de Cultivos (Fase 6)"
        subtitle={`Cultivo activo: ${detail?.local_names?.[0] ?? selectedCropId} · Ubicación: ${selectedLocation.label} (${fmtCoord(selectedLocation.lat, selectedLocation.lon)})`}
        actions={
          <label className="row-wrap">
            <span className="field-label">Cultivo activo:</span>
            <select
              className="select"
              style={{ width: "auto" }}
              value={selectedCropId}
              onChange={(e) => setSelectedCropId(e.target.value)}
            >
              {crops.map((c) => (
                <option key={c.crop_id} value={c.crop_id}>
                  {c.local_names[0] ?? c.crop_id} ({c.scientific_name})
                </option>
              ))}
            </select>
          </label>
        }
      />

      {error && <ErrorState message={error} />}

      <div className="tabs" role="tablist" aria-label="Vistas de cultivos">
        {([
          ["catalog", `Catálogo (${crops.length})`],
          ["detail", "Ficha técnica"],
          ["suitability", "Aptitud S1–N"],
          ["simulation", "Simulación hídrica"],
        ] as [TabId, string][]).map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className="tab-btn" onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "catalog" && (
        <div className="stack-md">
          <div className="row-wrap">
            <input
              type="search"
              className="input"
              style={{ flex: "1 1 260px" }}
              placeholder="Buscar cultivo por nombre común o científico…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              className="select"
              style={{ width: "auto", minWidth: 180 }}
              aria-label="Filtrar por categoría"
              value={cropTypeFilter}
              onChange={(e) => setCropTypeFilter(e.target.value)}
            >
              <option value="">Todas las categorías</option>
              {cropTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          {loadingList ? (
            <LoadingState />
          ) : (
            <div className="grid-3">
              {filteredCrops.map((c) => {
                const isSelected = c.crop_id === selectedCropId;
                return (
                  <article key={c.crop_id} className="card" style={{ borderColor: isSelected ? "var(--accent-primary)" : undefined }}>
                    <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                      <strong>{c.local_names[0] ?? c.crop_id}</strong>
                      <DataStatusBadge tone={isSelected ? "ok" : "info"} label={c.crop_type} />
                    </div>
                    <div style={{ fontSize: 12.5, fontStyle: "italic", color: "var(--ink-muted)", marginTop: 2 }}>
                      {c.scientific_name}
                    </div>
                    <div style={{ fontSize: 13, marginTop: 8 }}>
                      Ciclo: <strong>{renderParam(c.cycle_days)}</strong> · {c.lifecycle}
                    </div>
                    <div className="row-wrap" style={{ marginTop: 8, fontSize: 11.5, color: "var(--ink-muted)" }}>
                      <span>REF: {c.parameter_status?.REF ?? 0}</span>
                      <span>NAC: {c.parameter_status?.NAC ?? 0}</span>
                      <span>GAP: {c.parameter_status?.GAP ?? 0}</span>
                    </div>
                    <div className="row-wrap" style={{ marginTop: 12 }}>
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => {
                          setSelectedCropId(c.crop_id);
                          setTab("detail");
                        }}
                      >
                        Ver ficha
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => {
                          setSelectedCropId(c.crop_id);
                          setTab("suitability");
                        }}
                      >
                        Evaluar aptitud
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      )}

      {tab === "detail" && detail && (
        <div className="stack-md">
          <div className="card">
            <div className="row-wrap" style={{ justifyContent: "space-between" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 18 }}>{detail.local_names.join(" / ")}</h2>
                <div style={{ fontStyle: "italic", color: "var(--ink-muted)", fontSize: 13.5 }}>
                  {detail.scientific_name} · Familia {detail.family}
                </div>
              </div>
              <DataStatusBadge tone="info" label={`Confianza catálogo: ${detail.confidence}`} />
            </div>

            <div className="grid-2" style={{ marginTop: 14 }}>
              <dl className="kv-list">
                <div className="kv-row"><dt>Ciclo productivo</dt><dd>{renderParam(detail.cycle_days)}</dd></div>
                <div className="kv-row"><dt>Temp. óptima</dt><dd>{renderParam(detail.temperature?.opt_c)}</dd></div>
                <div className="kv-row"><dt>Temp. base (GDD)</dt><dd>{renderParam(detail.temperature?.tbase_c)}</dd></div>
                <div className="kv-row"><dt>Límites térmicos absolutos</dt><dd>{renderParam(detail.temperature?.abs_c)}</dd></div>
                <div className="kv-row"><dt>ETc estacional</dt><dd>{renderParam(detail.water?.etc_season_mm)}</dd></div>
              </dl>
              <dl className="kv-list">
                <div className="kv-row"><dt>pH de suelo</dt><dd>{renderParam(detail.soil?.ph_range)}</dd></div>
                <div className="kv-row"><dt>Profundidad mínima</dt><dd>{renderParam(detail.soil?.depth_min_cm)}</dd></div>
                <div className="kv-row"><dt>Pendiente máxima</dt><dd>{renderParam(detail.soil?.slope_max_pct)}</dd></div>
                <div className="kv-row"><dt>Kc local por etapa</dt><dd>{renderParam(detail.kc)}</dd></div>
                <div className="kv-row"><dt>Sistemas documentados</dt><dd>{detail.production_systems.join(", ")}</dd></div>
              </dl>
            </div>
          </div>

          <div className="card stack-sm">
            <div className="row-wrap" style={{ justifyContent: "space-between" }}>
              <h3 className="card-title">Demanda nutricional estimada (N – P₂O₅ – K₂O)</h3>
              <div className="row-wrap" style={{ alignItems: "center", gap: 8 }}>
                <label style={{ fontSize: 13, display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <span>Meta de rendimiento:</span>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="30"
                    className="input input-sm"
                    style={{ width: 85 }}
                    value={targetYield}
                    onChange={(e) => setTargetYield(e.target.value)}
                  />
                  <span>t/ha</span>
                </label>
              </div>
            </div>
            {nutrientLoading ? (
              <LoadingState message="Calculando extracción de nutrientes…" />
            ) : nutrientData ? (
              <div className="grid-3" style={{ marginTop: 8 }}>
                {Object.entries(nutrientData).map(([elem, val]) => {
                  const spec = val as { kg_ha?: [number, number]; kg_per_t?: [number, number]; status?: string };
                  const rangeHa = spec.kg_ha ? `${spec.kg_ha[0]} – ${spec.kg_ha[1]} kg/ha` : "Sin dato";
                  const rangePerT = spec.kg_per_t ? `(${spec.kg_per_t[0]} – ${spec.kg_per_t[1]} kg/t cosechada)` : "";
                  return (
                    <div key={elem} className="metric-card">
                      <div className="metric-label">{elem} (Extracción del cultivo)</div>
                      <div className="metric-value" style={{ fontSize: 20 }}>{rangeHa}</div>
                      <div className="metric-detail">{rangePerT} · Ref. bibliográfica internacional ({spec.status ?? "REF"})</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ fontSize: 13, color: "var(--ink-muted)" }}>
                Sin curvas de extracción nutricional validadas para este cultivo en el catálogo.
              </div>
            )}
          </div>

          <div className="grid-2">
            <section className="card">
              <h3 className="card-title">Plagas y enfermedades documentadas</h3>
              <div style={{ marginTop: 8 }}>
                <strong style={{ fontSize: 13 }}>Plagas:</strong>
                {detail.pests.length ? (
                  <div className="row-wrap" style={{ marginTop: 6, gap: 6 }}>
                    {detail.pests.map((p) => (
                      <span key={p} className="badge badge-warn" style={{ fontSize: 12 }}>{p}</span>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>Sin plagas registradas en catálogo</p>
                )}
              </div>
              <div style={{ marginTop: 12 }}>
                <strong style={{ fontSize: 13 }}>Enfermedades:</strong>
                {detail.diseases.length ? (
                  <div className="row-wrap" style={{ marginTop: 6, gap: 6 }}>
                    {detail.diseases.map((d) => (
                      <span key={d} className="badge badge-crit" style={{ fontSize: 12 }}>{d}</span>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>Sin enfermedades registradas en catálogo</p>
                )}
              </div>
            </section>
            <section className="card">
              <h3 className="card-title">Vacíos documentados (GAP)</h3>
              {detail.gaps.length > 0 ? (
                <ul style={{ margin: "8px 0 0 18px", padding: 0, fontSize: 13 }}>
                  {detail.gaps.map((g, i) => <li key={i}>{g}</li>)}
                </ul>
              ) : (
                <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>Sin vacíos declarados.</p>
              )}
            </section>
          </div>
          <SourceAttribution sources={detail.sources} />
        </div>
      )}

      {tab === "suitability" && (
        <div className="stack-md">
          <div className="card row-wrap">
            <label className="field" style={{ minWidth: 200 }}>
              <span className="field-label">Sistema de producción</span>
              <select className="select" value={system} onChange={(e) => setSystem(e.target.value as typeof system)}>
                <option value="rainfed">Secano (rainfed)</option>
                <option value="irrigated">Bajo riego (irrigated)</option>
                <option value="urban">Urbano (urban)</option>
                <option value="periurban">Periurbano (periurban)</option>
              </select>
            </label>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 8, marginTop: 18, fontSize: 13.5 }}>
              <input
                type="checkbox"
                checked={irrigationAvail}
                onChange={(e) => setIrrigationAvail(e.target.checked)}
              />
              <span>Confirmo disponibilidad real de riego en parcela</span>
            </label>
          </div>

          {suitLoading ? (
            <LoadingState message="Evaluando aptitud agroecológica en el servidor…" />
          ) : suit ? (
            <div className="stack-md">
              <div className="grid-3">
                <MetricCard
                  label="Clase de aptitud"
                  value={suit.class}
                  detail={suit.class_label}
                  evidenceClass="model_estimate"
                />
                <MetricCard
                  label="Factores limitantes"
                  value={suit.limiting_factors.length ? suit.limiting_factors.join(", ") : "Ninguno"}
                  detail="Evaluación por umbrales declarados"
                />
                <MetricCard
                  label="Ventana lluviosa evaluada"
                  value={suit.growing_window_months ? suit.growing_window_months.join(", ") : "—"}
                  detail="Meses de mayor precipitación"
                />
              </div>

              <div className="card">
                <h2 className="card-title">Desglose por factor evaluado</h2>
                <div className="table-wrap" style={{ marginTop: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr><th>Factor</th><th>Valor observado/estimado</th><th>Severidad</th><th>Crítico</th><th>Nota</th></tr>
                    </thead>
                    <tbody>
                      {suit.factors.map((f) => (
                        <tr key={f.factor}>
                          <td><strong>{f.factor}</strong></td>
                          <td className="tabular-nums">
                            {f.value === null ? "Sin dato" : typeof f.value === "object" ? JSON.stringify(f.value) : `${String(f.value)} ${f.unit}`}
                          </td>
                          <td>
                            <DataStatusBadge
                              tone={f.rating === "none" ? "ok" : f.rating === "moderate" ? "warn" : f.rating === "severe" ? "crit" : "unavailable"}
                              label={f.rating ?? "not_evaluated"}
                            />
                          </td>
                          <td>{f.critical ? "Sí" : "No"}</td>
                          <td style={{ fontSize: 12.5 }}>{f.note ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <UncertaintyPanel collapsedByDefault={simpleMode} limitations={suitEnv?.limitations} />
            </div>
          ) : (
            <ErrorState message="No se pudo obtener la evaluación de aptitud para este punto." />
          )}
        </div>
      )}

      {tab === "simulation" && (
        <div className="stack-md">
          <div className="callout callout--warn">
            <strong>Motor no calibrado para pronóstico de rendimiento:</strong> el único adaptador ejecutable es el balance hídrico diario FAO-56 (<code>agrosv_water_balance</code>). AquaCrop-OSPy, WOFOST y DSSAT se detectan y declaran sin ejecutarse.
          </div>

          <form onSubmit={runSimulation} className="card stack-md">
            <h2 className="card-title">Configurar simulación hídrica FAO-56</h2>
            <div className="grid-4">
              <label className="field">
                <span className="field-label">Fecha de siembra</span>
                <input type="date" className="input" value={plantingDate} onChange={(e) => setPlantingDate(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">AWC del suelo (mm/m)</span>
                <input type="number" className="input" min={20} max={350} value={awcMmM} onChange={(e) => setAwcMmM(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Profundidad radicular (cm)</span>
                <input type="number" className="input" min={15} max={250} value={rootCm} onChange={(e) => setRootCm(e.target.value)} />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 22, fontSize: 13 }}>
                <input type="checkbox" checked={allowRefKc} onChange={(e) => setAllowRefKc(e.target.checked)} />
                <span>Usar Kc de referencia FAO-56</span>
              </label>
            </div>
            <div>
              <button type="submit" className="btn btn-primary" disabled={simLoading}>
                {simLoading ? "Simulando…" : "Ejecutar balance hídrico"}
              </button>
            </div>
          </form>

          {simError && <ErrorState message={simError} />}

          {simEnv && (() => {
            const outputs = (simRes.outputs ?? {}) as Record<string, unknown>;
            const water = (outputs.water ?? {}) as Record<string, number | undefined>;
            const stress = (outputs.stress ?? {}) as Record<string, number | undefined>;
            const yld = (outputs.yield ?? {}) as Record<string, unknown>;
            return (
              <div className="card stack-md">
                <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                  <h3 className="card-title">Balance Hídrico del Ciclo ({selectedCropId})</h3>
                  <EvidenceBadge evidenceClass="simulated" />
                </div>

                <div className="grid-3">
                  <MetricCard
                    label="Precipitación del ciclo"
                    value={water.precip_mm != null ? `${water.precip_mm.toFixed(1)} mm` : "—"}
                    detail={`Efectiva: ${water.effective_precip_mm != null ? `${water.effective_precip_mm.toFixed(1)} mm` : "—"}`}
                    evidenceClass="reanalysis"
                  />
                  <MetricCard
                    label="Evapotranspiración del cultivo"
                    value={water.eta_mm != null ? `${water.eta_mm.toFixed(1)} mm (ETa)` : "—"}
                    detail={`Demanda máxima ETm: ${water.etm_mm != null ? `${water.etm_mm.toFixed(1)} mm` : "—"}`}
                    evidenceClass="simulated"
                  />
                  <MetricCard
                    label="Estrés hídrico detectado"
                    value={stress.stress_days != null ? `${stress.stress_days} días` : "0 días"}
                    detail={`Relación ETa/ETm: ${stress.eta_etm_ratio != null ? stress.eta_etm_ratio.toFixed(3) : "—"}`}
                    evidenceClass="simulated"
                  />
                </div>

                <div className="callout callout--info" style={{ fontSize: 13 }}>
                  <strong>Rendimiento simulado:</strong> {String(yld.reason ?? "Sin estimación (requiere Ky local y variedad calibrada)")}.
                  El motor calcula el balance de agua del suelo conforme a FAO-56 sin extrapolar producción comercial sin datos empíricos.
                </div>

                <UncertaintyPanel limitations={simEnv.limitations} assumptions={simEnv.assumptions} />
              </div>
            );
          })()}

          {Object.keys(adapters).length > 0 && (
            <section className="card">
              <h2 className="card-title">Estado de adaptadores de simulación</h2>
              <div className="table-wrap" style={{ marginTop: 10 }}>
                <table className="data-table">
                  <thead>
                    <tr><th>Adaptador</th><th>Estado</th><th>Alcance</th><th>Requisitos faltantes / Notas</th></tr>
                  </thead>
                  <tbody>
                    {Object.entries(adapters).map(([id, spec]) => (
                      <tr key={id}>
                        <td><strong>{String(spec.name)}</strong> <span className="mono">({String(spec.version)})</span></td>
                        <td>
                          <DataStatusBadge
                            tone={spec.executable ? "ok" : "unavailable"}
                            label={spec.executable ? "Ejecutable" : String(spec.status)}
                          />
                        </td>
                        <td style={{ fontSize: 12.5 }}>{String(spec.scope)}</td>
                        <td style={{ fontSize: 12.5 }}>{String(spec.calibration)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
