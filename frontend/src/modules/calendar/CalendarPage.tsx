import { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { fmtNum, MONTH_NAMES_ES } from "../../utils/format";
import { MetricCard, PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  ErrorState,
  EvidenceBadge,
  LoadingState,
  UncertaintyPanel,
} from "../../components/data-status/DataStatus";
import type { CropSummary, EngineEnvelope } from "../../types/api";

export default function CalendarPage() {
  const { selectedCropId, setSelectedCropId, simpleMode } = useApp();
  const [crops, setCrops] = useState<CropSummary[]>([]);
  const [plantingDate, setPlantingDate] = useState("2025-05-15");
  const [calEnv, setCalEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    agrosvApi.crops(undefined, undefined, ac.signal)
      .then(({ data }) => setCrops(data.crops ?? []))
      .catch(() => undefined);
    return () => ac.abort();
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    agrosvApi.cropCalendar(selectedCropId, plantingDate || undefined, ac.signal)
      .then(({ data }) => {
        setCalEnv(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "No se pudo generar el calendario");
        setLoading(false);
      });
    return () => ac.abort();
  }, [selectedCropId, plantingDate]);

  const res = (calEnv?.result ?? {}) as Record<string, unknown>;
  const windows = (res.planting_windows ?? []) as Array<{ months: number[]; labels: string[]; criterion: string }>;
  const stages = (res.stages ?? []) as Array<{ stage: string; date: string; gdd_required?: number; days_after_planting?: number }>;
  const risks = (res.risk_periods ?? []) as Array<{ stage: string; month_label: string; precip_mm: number | null; et0_mm: number | null; risks: string[] }>;
  const unavailable = (res.unavailable ?? {}) as Record<string, string>;

  return (
    <div className="stack-md">
      <PageHeader
        title="Calendario Agrícola Derivado (Fase 6)"
        subtitle="Ventanas de siembra y etapas fenológicas térmicas basadas en climatología 2019–2025."
        actions={
          <div className="row-wrap">
            <select
              className="select"
              style={{ width: "auto" }}
              aria-label="Seleccionar cultivo"
              value={selectedCropId}
              onChange={(e) => setSelectedCropId(e.target.value)}
            >
              {crops.map((c) => (
                <option key={c.crop_id} value={c.crop_id}>{c.local_names[0] ?? c.crop_id}</option>
              ))}
            </select>
            <input
              type="date"
              className="input"
              style={{ width: "auto" }}
              aria-label="Fecha tentativa de siembra"
              value={plantingDate}
              onChange={(e) => setPlantingDate(e.target.value)}
            />
          </div>
        }
      />

      <div className="callout callout--warn">
        <strong>Calendario derivado (no oficial):</strong> el repositorio no contiene calendario histórico municipal ni recomendaciones CENTA/MAG georreferenciadas, ni pronóstico climático en vivo.
      </div>

      {error && <ErrorState message={error} />}

      {loading ? (
        <LoadingState />
      ) : (
        <div className="stack-md">
          <div className="grid-3">
            <MetricCard
              label="Ventanas de siembra estimadas"
              value={windows.length ? windows.map((w) => `${w.labels[0]}–${w.labels[w.labels.length - 1]}`).join(", ") : "Sin ventana"}
              detail="Criterio: P ≥ 60 mm y 0.5 ≤ P/ET0 ≤ 2.0"
              evidenceClass="model_estimate"
            />
            <MetricCard
              label="Práctica histórica municipal"
              value="No disponible"
              detail={unavailable.historical_practice}
              evidenceClass="unavailable"
            />
            <MetricCard
              label="Pronóstico estacional"
              value="No disponible"
              detail={unavailable.forecast}
              evidenceClass="unavailable"
            />
          </div>

          {stages.length > 0 && (
            <section className="card">
              <div className="row-wrap" style={{ justifyContent: "space-between", marginBottom: 10 }}>
                <h2 className="card-title">Etapas fenológicas estimadas desde {plantingDate}</h2>
                <EvidenceBadge evidenceClass="model_estimate" />
              </div>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr><th>Etapa</th><th>Fecha estimada</th><th>Días tras siembra</th><th>Riesgo hídrico climatológico</th></tr>
                  </thead>
                  <tbody>
                    {stages.map((st, idx) => {
                      const rk = risks[idx];
                      return (
                        <tr key={st.stage + idx}>
                          <td><strong>{st.stage}</strong></td>
                          <td className="tabular-nums">{st.date}</td>
                          <td className="tabular-nums">{st.days_after_planting ?? "—"}</td>
                          <td style={{ fontSize: 12.5 }}>
                            {rk ? `${rk.month_label} (P: ${fmtNum(rk.precip_mm, 0, "mm")}, ET0: ${fmtNum(rk.et0_mm, 0, "mm")}) — ${rk.risks.join("; ")}` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {Boolean(res.stage_error) && (
            <div className="callout callout--info">
              <span>{String(res.stage_error)}</span>
            </div>
          )}

          <section className="card">
            <h2 className="card-title">Componentes no disponibles en este calendario</h2>
            <ul style={{ margin: "8px 0 0 18px", padding: 0, fontSize: 13, display: "grid", gap: 4 }}>
              {Object.entries(unavailable).map(([k, v]) => (
                <li key={k}>
                  <DataStatusBadge tone="unavailable" label={k} /> <span>{v}</span>
                </li>
              ))}
            </ul>
            <div style={{ marginTop: 10, fontSize: 12, color: "var(--ink-muted)" }}>
              Meses de referencia: {MONTH_NAMES_ES.join(", ")}.
            </div>
          </section>

          <UncertaintyPanel collapsedByDefault={simpleMode} assumptions={calEnv?.assumptions} limitations={calEnv?.limitations} />
        </div>
      )}
    </div>
  );
}
