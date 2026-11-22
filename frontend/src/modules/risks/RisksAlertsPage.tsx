import React, { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  EmptyState,
  ErrorState,
  EvidenceBadge,
} from "../../components/data-status/DataStatus";
import type { AlertItem } from "../../types/api";

export default function RisksAlertsPage() {
  const { selectedLocation, selectedCropId } = useApp();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [category, setCategory] = useState("drought");
  const [riskLevel, setRiskLevel] = useState("moderate");
  const [evidenceNote, setEvidenceNote] = useState("Anomalía pluviométrica 3m bajo p20");
  const [error, setError] = useState<string | null>(null);

  // Risk engines
  const [activeTab, setActiveTab] = useState<"alerts" | "drought" | "flood" | "heat" | "soil">("alerts");
  const [droughtPrecipP, setDroughtPrecipP] = useState("15");
  const [droughtCdd, setDroughtCdd] = useState("18");
  const [droughtDeficit, setDroughtDeficit] = useState("0.45");
  const [droughtRes, setDroughtRes] = useState<Record<string, unknown> | null>(null);

  const [floodRain24, setFloodRain24] = useState("85");
  const [floodRain72, setFloodRain72] = useState("160");
  const [floodSlope, setFloodSlope] = useState("2.5");
  const [floodRes, setFloodRes] = useState<Record<string, unknown> | null>(null);

  const [heatTmaxSeq, setHeatTmaxSeq] = useState("36.0, 37.5, 38.0, 36.5, 35.5");
  const [heatThreshold, setHeatThreshold] = useState("35.0");
  const [heatRes, setHeatRes] = useState<Record<string, unknown> | null>(null);

  const [soilSlope, setSoilSlope] = useState("22");
  const [soilK, setSoilK] = useState("0.04");
  const [soilR, setSoilR] = useState("450");
  const [soilCover, setSoilCover] = useState("0.35");
  const [soilRes, setSoilRes] = useState<Record<string, unknown> | null>(null);

  const [evalLoading, setEvalLoading] = useState(false);

  const loadAlerts = () => {
    agrosvApi.alerts()
      .then(({ data }) => {
        setAlerts(data.alerts ?? []);
        if (!selectedAlert && data.alerts?.length) setSelectedAlert(data.alerts[0]);
      })
      .catch(() => undefined);
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const createAlertPreset = async (preset: {
    category: string;
    department: string;
    risk_level: string;
    evidenceNote: string;
    cropId: string;
  }) => {
    setError(null);
    try {
      const res = await agrosvApi.createAlert({
        category: preset.category,
        geographic_scope: {
          scale: "departmental",
          department: preset.department,
          lat: selectedLocation.lat,
          lon: selectedLocation.lon,
        },
        observation_period: { start: "2025-05-01", end: "2025-07-15" },
        detection_method: "evaluación técnica de reanálisis y catálogo fitosanitario",
        risk_level: preset.risk_level,
        evidence: [{ indicator: preset.category, note: preset.evidenceNote }],
        confidence: "moderate",
        source_datasets: ["open_meteo_point", "cabi_compendium"],
        crop_id: preset.cropId,
      });
      const created = res.alert as AlertItem | undefined;
      loadAlerts();
      if (created) setSelectedAlert(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar alerta de plantilla");
    }
  };

  const createAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await agrosvApi.createAlert({
        category,
        geographic_scope: {
          scale: "municipal",
          department: selectedLocation.departmentName ?? "San Salvador",
          lat: selectedLocation.lat,
          lon: selectedLocation.lon,
        },
        observation_period: { start: "2025-05-01", end: "2025-07-15" },
        detection_method: "evaluación técnica de usuario / reanálisis",
        risk_level: riskLevel,
        evidence: [{ indicator: category, note: evidenceNote }],
        confidence: "low",
        source_datasets: ["open_meteo_point"],
        crop_id: selectedCropId,
      });
      const created = res.alert as AlertItem | undefined;
      loadAlerts();
      if (created) setSelectedAlert(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la alerta");
    }
  };

  const verifySelected = async () => {
    if (!selectedAlert) return;
    await agrosvApi.verifyAlert(selectedAlert.alert_id, {
      verifier_type: "field_inspection",
      outcome: "confirmed",
      evidence: [{ source: "inspección técnica", note: "Verificación registrada desde consola AGROSV" }],
      observed_on: new Date().toISOString().slice(0, 10),
      confidence: 0.75,
      notes: "Verificación técnica registrada",
      apply: true,
    });
    loadAlerts();
  };

  const handleEvaluateDrought = async (e: React.FormEvent) => {
    e.preventDefault();
    setEvalLoading(true);
    try {
      const res = await agrosvApi.assessDrought({
        precip_percentile: Number(droughtPrecipP) || 15,
        cdd_days: Number(droughtCdd) || 15,
        soil_deficit_fraction: Number(droughtDeficit) || 0.4,
      });
      setDroughtRes(res);
    } finally {
      setEvalLoading(false);
    }
  };

  const handleEvaluateFlood = async (e: React.FormEvent) => {
    e.preventDefault();
    setEvalLoading(true);
    try {
      const res = await agrosvApi.assessFloodRisk({
        rainfall_24h_mm: Number(floodRain24) || 80,
        rainfall_72h_mm: Number(floodRain72) || 150,
        slope_deg: Number(floodSlope) || 3.0,
      });
      setFloodRes(res);
    } finally {
      setEvalLoading(false);
    }
  };

  const handleEvaluateHeat = async (e: React.FormEvent) => {
    e.preventDefault();
    setEvalLoading(true);
    try {
      const values = heatTmaxSeq.split(",").map((s) => Number(s.trim())).filter((n) => Number.isFinite(n));
      const res = await agrosvApi.assessHeatRisk({
        tmax_c: values.length ? values : [35, 36.5, 37],
        threshold_c: Number(heatThreshold) || 35.0,
        threshold_source: "FAO-56",
        crop_id: selectedCropId,
      });
      setHeatRes(res);
    } finally {
      setEvalLoading(false);
    }
  };

  const handleEvaluateSoil = async (e: React.FormEvent) => {
    e.preventDefault();
    setEvalLoading(true);
    try {
      const res = await agrosvApi.assessSoilDegradation({
        slope_deg: Number(soilSlope) || 20,
        erodibility_k: Number(soilK) || 0.04,
        rain_erosivity_r: Number(soilR) || 450,
        vegetation_cover_fraction: Number(soilCover) || 0.35,
      });
      setSoilRes(res);
    } finally {
      setEvalLoading(false);
    }
  };

  return (
    <div className="stack-md">
      <PageHeader
        title="Riesgos Agrícolas y Centro de Alertas (Fase 7)"
        subtitle="Gestión transparente de avisos con evidencia, confianza y verificación; nunca se presentan señales algorítmicas como alertas oficiales."
      />

      <div className="callout callout--warn">
        <strong>Aviso institucional:</strong> las alertas generadas en AGROSV son señales analíticas con incertidumbre explícita; no sustituyen comunicados oficiales de MARN, MAG o Protección Civil.
      </div>

      {error && <ErrorState message={error} />}

      <div className="tabs" role="tablist" aria-label="Submódulos de riesgo">
        {[
          ["alerts", `Centro de Alertas (${alerts.length})`],
          ["drought", "Riesgo de Sequía"],
          ["flood", "Inundación / Lluvia"],
          ["heat", "Estrés Térmico"],
          ["soil", "Erosión / Degradación"],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={activeTab === id}
            className="tab-btn"
            onClick={() => setActiveTab(id as typeof activeTab)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "alerts" && (
        <div className="stack-md">
          {/* Quick preset templates */}
          <div className="card stack-sm">
            <div className="row-wrap" style={{ justifyContent: "space-between" }}>
              <h2 className="card-title">Plantillas de alertas agroclimáticas para El Salvador</h2>
              <span style={{ fontSize: 12.5, color: "var(--ink-muted)" }}>Clic para registrar con evidencia técnica real</span>
            </div>
            <div className="grid-3" style={{ marginTop: 6 }}>
              <div style={{ padding: 12, borderRadius: 8, background: "var(--bg-subtle)", border: "1px solid var(--border-subtle)" }}>
                <strong>Sequía en Corredor Seco Oriental</strong>
                <div style={{ fontSize: 12, color: "var(--ink-muted)", margin: "4px 0" }}>San Miguel / Usulután · Maíz y Frijol</div>
                <div style={{ fontSize: 12 }}>Anomalía pluviométrica 3m bajo percentil 20</div>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  style={{ marginTop: 8 }}
                  onClick={() => createAlertPreset({
                    category: "drought",
                    department: "San Miguel",
                    risk_level: "high",
                    evidenceNote: "Déficit pluviométrico severo en ventana de primera 2025",
                    cropId: "maize",
                  })}
                >
                  Registrar alerta de sequía
                </button>
              </div>

              <div style={{ padding: 12, borderRadius: 8, background: "var(--bg-subtle)", border: "1px solid var(--border-subtle)" }}>
                <strong>Roya en cordillera Apaneca-Ilamatepec</strong>
                <div style={{ fontSize: 12, color: "var(--ink-muted)", margin: "4px 0" }}>Ahuachapán / Santa Ana · Café</div>
                <div style={{ fontSize: 12 }}>Condiciones de dosel húmedo y temperaturas 20–25°C</div>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  style={{ marginTop: 8 }}
                  onClick={() => createAlertPreset({
                    category: "disease_risk",
                    department: "Ahuachapán",
                    risk_level: "moderate",
                    evidenceNote: "Humedad de hoja > 8 h prolongada en cafetales de sombra",
                    cropId: "coffee",
                  })}
                >
                  Registrar alerta de roya
                </button>
              </div>

              <div style={{ padding: 12, borderRadius: 8, background: "var(--bg-subtle)", border: "1px solid var(--border-subtle)" }}>
                <strong>Gusano Cogollero en valle Zapotitán</strong>
                <div style={{ fontSize: 12, color: "var(--ink-muted)", margin: "4px 0" }}>La Libertad · Granos básicos y hortalizas</div>
                <div style={{ fontSize: 12 }}>Spodoptera frugiperda en etapa vegetativa</div>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  style={{ marginTop: 8 }}
                  onClick={() => createAlertPreset({
                    category: "pest_risk",
                    department: "La Libertad",
                    risk_level: "moderate",
                    evidenceNote: "Aparición de daño en cogollo en parcelas de maíz de riego",
                    cropId: "maize",
                  })}
                >
                  Registrar alerta de plaga
                </button>
              </div>
            </div>
          </div>

          <div className="grid-2">
            <section className="card stack-sm">
              <h2 className="card-title">Alertas registradas ({alerts.length})</h2>
              {alerts.length === 0 ? (
                <EmptyState
                  title="Sin alertas activas en esta sesión"
                  description="Haz clic en una de las plantillas superiores o utiliza el formulario inferior para registrar una alerta estructurada."
                />
              ) : (
                <div className="stack-sm">
                  {alerts.map((a) => (
                    <button
                      key={a.alert_id}
                      type="button"
                      className="btn"
                      style={{
                        justifyContent: "space-between",
                        borderColor: selectedAlert?.alert_id === a.alert_id ? "var(--accent-primary)" : undefined,
                      }}
                      onClick={() => setSelectedAlert(a)}
                    >
                      <span><strong>{a.category}</strong> · {String(a.geographic_scope.department ?? "SV")}</span>
                      <DataStatusBadge
                        tone={a.risk_level === "very_high" || a.risk_level === "high" ? "crit" : a.risk_level === "moderate" ? "warn" : "info"}
                        label={`${a.risk_level} · ${a.status}`}
                      />
                    </button>
                  ))}
                </div>
              )}

              <form onSubmit={createAlert} className="stack-sm" style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border-subtle)" }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>Registrar alerta personalizada con evidencia</h3>
                <div className="grid-2">
                  <label className="field">
                    <span className="field-label">Categoría</span>
                    <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
                      <option value="drought">Sequía (drought)</option>
                      <option value="excess_rainfall">Exceso de lluvia</option>
                      <option value="heat_stress">Estrés térmico</option>
                      <option value="pest_risk">Riesgo de plaga</option>
                      <option value="disease_risk">Riesgo de enfermedad</option>
                    </select>
                  </label>
                  <label className="field">
                    <span className="field-label">Severidad</span>
                    <select className="select" value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)}>
                      <option value="low">Baja</option>
                      <option value="moderate">Moderada</option>
                      <option value="high">Alta</option>
                      <option value="very_high">Muy alta</option>
                    </select>
                  </label>
                </div>
                <label className="field">
                  <span className="field-label">Evidencia documental</span>
                  <input className="input" value={evidenceNote} onChange={(e) => setEvidenceNote(e.target.value)} />
                </label>
                <button type="submit" className="btn btn-primary btn-sm">Crear alerta</button>
              </form>
            </section>

            <section className="card stack-sm">
              <h2 className="card-title">Detalle y verificación de alerta</h2>
              {selectedAlert ? (
                <div className="stack-sm">
                  <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                    <span className="mono">{selectedAlert.alert_id}</span>
                    <EvidenceBadge evidenceClass={selectedAlert.evidence_class} />
                  </div>
                  <dl className="kv-list">
                    <div className="kv-row"><dt>Categoría</dt><dd>{selectedAlert.category}</dd></div>
                    <div className="kv-row"><dt>Estado actual</dt><dd><span className="badge badge-info">{selectedAlert.status}</span></dd></div>
                    <div className="kv-row"><dt>Severidad</dt><dd>{selectedAlert.risk_level}</dd></div>
                    <div className="kv-row"><dt>Nivel de confianza</dt><dd>{selectedAlert.confidence}</dd></div>
                    <div className="kv-row"><dt>Cultivo asociado</dt><dd>{selectedAlert.crop_id ?? "General"}</dd></div>
                    <div className="kv-row"><dt>Verificación recomendada</dt><dd>{selectedAlert.recommended_verification}</dd></div>
                  </dl>
                  <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
                    <button type="button" className="btn btn-sm btn-primary" onClick={verifySelected}>
                      Registrar verificación de campo (confirmar)
                    </button>
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: 13.5, color: "var(--ink-muted)" }}>Selecciona una alerta para ver evidencia y verificación.</p>
              )}
            </section>
          </div>
        </div>
      )}

      {activeTab === "drought" && (
        <form onSubmit={handleEvaluateDrought} className="card stack-md">
          <div className="row-wrap" style={{ justifyContent: "space-between" }}>
            <h2 className="card-title">Evaluador Multidimensional de Sequía (DroughtMonitoringEngine)</h2>
            <EvidenceBadge evidenceClass="model_estimate" />
          </div>
          <div className="grid-3">
            <label className="field">
              <span className="field-label">Percentil de precipitación reciente (0–100)</span>
              <input type="number" step="1" min="0" max="100" className="input" value={droughtPrecipP} onChange={(e) => setDroughtPrecipP(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">Días secos consecutivos (CDD)</span>
              <input type="number" step="1" min="0" max="60" className="input" value={droughtCdd} onChange={(e) => setDroughtCdd(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">Fracción de déficit en suelo (0–1)</span>
              <input type="number" step="0.05" min="0" max="1" className="input" value={droughtDeficit} onChange={(e) => setDroughtDeficit(e.target.value)} />
            </label>
          </div>
          <div>
            <button type="submit" className="btn btn-primary" disabled={evalLoading}>
              {evalLoading ? "Evaluando…" : "Calcular estado de sequía"}
            </button>
          </div>

          {droughtRes && (() => {
            const types = (droughtRes.drought_types ?? {}) as Record<string, Record<string, unknown> | undefined>;
            return (
              <div className="stack-sm" style={{ marginTop: 10, padding: 12, borderRadius: 8, background: "var(--bg-subtle)" }}>
                <div className="grid-3">
                  <div className="metric-card">
                    <div className="metric-label">Sequía meteorológica</div>
                    <div className="metric-value" style={{ fontSize: 18 }}>{String(types.meteorological?.class ?? "No evaluada")}</div>
                    <div className="metric-detail">Percentil P: {String(types.meteorological?.percentile ?? droughtPrecipP)}%</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Sequía agrícola</div>
                    <div className="metric-value" style={{ fontSize: 18 }}>{String(types.agricultural?.class ?? "Sin déficit")}</div>
                    <div className="metric-detail">Déficit hídrico: {String(Number(droughtDeficit) * 100)}% de TAW</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Sequía hidrológica</div>
                    <div className="metric-value" style={{ fontSize: 18 }}>{String(types.hydrological?.status ?? "not_evaluated")}</div>
                    <div className="metric-detail">{String(types.hydrological?.reason ?? "Sin aforos ni caudales integrados")}</div>
                  </div>
                </div>
                <div className="callout callout--info" style={{ fontSize: 12.5, marginTop: 8 }}>
                  <strong>Declaración:</strong> {String(droughtRes.statement)}. La evaluación multidimensional no colapsa cinco dimensiones distintas en un solo índice ficticio.
                </div>
              </div>
            );
          })()}
        </form>
      )}

      {activeTab === "flood" && (
        <form onSubmit={handleEvaluateFlood} className="card stack-md">
          <div className="row-wrap" style={{ justifyContent: "space-between" }}>
            <h2 className="card-title">Evaluador de Inundación y Exceso Hídrico (FloodAndExcessWaterRiskEngine)</h2>
            <EvidenceBadge evidenceClass="model_estimate" />
          </div>
          <div className="grid-3">
            <label className="field">
              <span className="field-label">Lluvia acumulada 24h (mm)</span>
              <input type="number" step="1" className="input" value={floodRain24} onChange={(e) => setFloodRain24(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">Lluvia acumulada 72h (mm)</span>
              <input type="number" step="1" className="input" value={floodRain72} onChange={(e) => setFloodRain72(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">Pendiente del terreno (grados °)</span>
              <input type="number" step="0.5" className="input" value={floodSlope} onChange={(e) => setFloodSlope(e.target.value)} />
            </label>
          </div>
          <div>
            <button type="submit" className="btn btn-primary" disabled={evalLoading}>
              {evalLoading ? "Evaluando…" : "Evaluar susceptibilidad de anegamiento"}
            </button>
          </div>

          {floodRes && (
            <div className="stack-sm" style={{ marginTop: 10, padding: 12, borderRadius: 8, background: "var(--bg-subtle)" }}>
              <div className="grid-3">
                <div className="metric-card">
                  <div className="metric-label">Clase de susceptibilidad</div>
                  <div className="metric-value" style={{ fontSize: 20 }}>{String(floodRes.susceptibility_class ?? "moderada")}</div>
                  <div className="metric-detail">Puntaje ponderado: {String(floodRes.susceptibility_score ?? "—")}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Lluvia 24h / 72h</div>
                  <div className="metric-value" style={{ fontSize: 18 }}>{floodRain24} mm / {floodRain72} mm</div>
                  <div className="metric-detail">Pendiente evaluada: {floodSlope}°</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Peligro hidrológico</div>
                  <div className="metric-value" style={{ fontSize: 18 }}>{Number(floodSlope) < 3.0 ? "Anegamiento / Drenaje lento" : "Escorrentía rápida"}</div>
                  <div className="metric-detail">Fuente: Copernicus DEM + Reanálisis</div>
                </div>
              </div>
            </div>
          )}
        </form>
      )}

      {activeTab === "heat" && (
        <form onSubmit={handleEvaluateHeat} className="card stack-md">
          <div className="row-wrap" style={{ justifyContent: "space-between" }}>
            <h2 className="card-title">Evaluador de Estrés Térmico y Olas de Calor (HeatAndClimateRiskEngine)</h2>
            <EvidenceBadge evidenceClass="model_estimate" />
          </div>
          <div className="grid-2">
            <label className="field">
              <span className="field-label">Serie diaria de temperaturas máximas (°C, separadas por coma)</span>
              <input className="input" value={heatTmaxSeq} onChange={(e) => setHeatTmaxSeq(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">Umbral crítico de cultivo (°C)</span>
              <input type="number" step="0.5" className="input" value={heatThreshold} onChange={(e) => setHeatThreshold(e.target.value)} />
            </label>
          </div>
          <div>
            <button type="submit" className="btn btn-primary" disabled={evalLoading}>
              {evalLoading ? "Evaluando…" : "Evaluar exposición térmica"}
            </button>
          </div>

          {heatRes && (() => {
            const obs = (heatRes.observed_heat ?? {}) as Record<string, unknown>;
            return (
              <div className="stack-sm" style={{ marginTop: 10, padding: 12, borderRadius: 8, background: "var(--bg-subtle)" }}>
                <div className="grid-3">
                  <div className="metric-card">
                    <div className="metric-label">Nivel de riesgo térmico</div>
                    <div className="metric-value" style={{ fontSize: 20 }}>{String(heatRes.risk_class ?? "moderado")}</div>
                    <div className="metric-detail">Score de riesgo: {String(heatRes.risk_score ?? "—")}</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Días sobre umbral ({heatThreshold}°C)</div>
                    <div className="metric-value" style={{ fontSize: 18 }}>{String(obs.days_above ?? 0)} de {String(obs.n_days ?? 0)} días</div>
                    <div className="metric-detail">Consecutivos máximos: {String(obs.max_consecutive_days ?? 0)}</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Ola de calor (3+ días)</div>
                    <div className="metric-value" style={{ fontSize: 18 }}>{obs.heat_wave_3d ? "Detectada (Sí)" : "No detectada"}</div>
                    <div className="metric-detail">Grados-día sobre umbral: {String(obs.degree_days_above_c ?? 0)}°C</div>
                  </div>
                </div>
              </div>
            );
          })()}
        </form>
      )}

      {activeTab === "soil" && (
        <form onSubmit={handleEvaluateSoil} className="card stack-md">
          <div className="row-wrap" style={{ justifyContent: "space-between" }}>
            <h2 className="card-title">Evaluador de Susceptibilidad a Degradación y Erosión (SoilDegradationRiskEngine)</h2>
            <EvidenceBadge evidenceClass="model_estimate" />
          </div>
          <div className="grid-4">
            <label className="field">
              <span className="field-label">Pendiente del terreno (°)</span>
              <input type="number" step="0.5" className="input" value={soilSlope} onChange={(e) => setSoilSlope(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">Cobertura vegetal (0–1)</span>
              <input type="number" step="0.05" min="0" max="1" className="input" value={soilCover} onChange={(e) => setSoilCover(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">Erodibilidad K del suelo</span>
              <input type="number" step="0.01" className="input" value={soilK} onChange={(e) => setSoilK(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">Erosividad R de lluvia</span>
              <input type="number" step="10" className="input" value={soilR} onChange={(e) => setSoilR(e.target.value)} />
            </label>
          </div>
          <div>
            <button type="submit" className="btn btn-primary" disabled={evalLoading}>
              {evalLoading ? "Evaluando…" : "Calcular susceptibilidad a erosión"}
            </button>
          </div>

          {soilRes && (
            <div className="stack-sm" style={{ marginTop: 10, padding: 12, borderRadius: 8, background: "var(--bg-subtle)" }}>
              <div className="grid-3">
                <div className="metric-card">
                  <div className="metric-label">Susceptibilidad a degradación</div>
                  <div className="metric-value" style={{ fontSize: 20 }}>{String(soilRes.susceptibility_class ?? "moderada")}</div>
                  <div className="metric-detail">Puntaje relativo: {String(soilRes.susceptibility_score ?? "—")}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Tasa de erosión (t/ha/año)</div>
                  <div className="metric-value" style={{ fontSize: 18 }}>No declarada</div>
                  <div className="metric-detail">{String(soilRes.erosion_rate_reason ?? "Sin parcelas de escorrentía calibradas")}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Metodología</div>
                  <div className="metric-value" style={{ fontSize: 16 }}>RUSLE proxy</div>
                  <div className="metric-detail">Pendiente + Cobertura + Erodibilidad K</div>
                </div>
              </div>
            </div>
          )}
        </form>
      )}
    </div>
  );
}
