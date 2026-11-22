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
  const [droughtRes, setDroughtRes] = useState<Record<string, unknown> | null>(null);
  const [floodRes, setFloodRes] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const runDroughtAndFlood = async () => {
    const [d, f] = await Promise.all([
      agrosvApi.assessDrought({ precip_percentile: 18, cdd_days: 16, soil_deficit_fraction: 0.45 }),
      agrosvApi.assessFloodRisk({ rainfall_24h_mm: 85, rainfall_72h_mm: 150, slope_deg: 2.5 }),
    ]);
    setDroughtRes(d);
    setFloodRes(f);
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

      <div className="grid-2">
        <section className="card stack-sm">
          <h2 className="card-title">Alertas registradas ({alerts.length})</h2>
          {alerts.length === 0 ? (
            <EmptyState
              title="Sin alertas activas en esta sesión"
              description="Crea una alerta estructurada con evidencia para probar el ciclo de vida (DETECTED → verificación)."
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
            <h3 style={{ margin: 0, fontSize: 14 }}>Registrar nueva alerta con evidencia</h3>
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
                <div className="kv-row"><dt>Estado</dt><dd>{selectedAlert.status}</dd></div>
                <div className="kv-row"><dt>Confianza</dt><dd>{selectedAlert.confidence}</dd></div>
                <div className="kv-row"><dt>Cultivo</dt><dd>{selectedAlert.crop_id ?? "General"}</dd></div>
                <div className="kv-row"><dt>Verificación recomendada</dt><dd>{selectedAlert.recommended_verification}</dd></div>
              </dl>
              <button type="button" className="btn btn-sm" onClick={verifySelected}>
                Registrar verificación técnica
              </button>
            </div>
          ) : (
            <p style={{ fontSize: 13.5, color: "var(--ink-muted)" }}>Selecciona una alerta para ver evidencia y verificación.</p>
          )}

          <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border-subtle)" }}>
            <div className="row-wrap" style={{ justifyContent: "space-between" }}>
              <h3 style={{ margin: 0, fontSize: 14 }}>Evaluadores rápidos (Sequía y Exceso)</h3>
              <button type="button" className="btn btn-sm" onClick={runDroughtAndFlood}>Evaluar ejemplo</button>
            </div>
            {(droughtRes || floodRes) && (
              <pre style={{ marginTop: 8, padding: 10, borderRadius: 8, background: "var(--bg-subtle)", fontSize: 11.5, overflowX: "auto" }}>
                {JSON.stringify({ drought: droughtRes, flood: floodRes }, null, 2)}
              </pre>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
