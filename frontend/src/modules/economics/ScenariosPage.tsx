import React, { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { fmtNum, fmtUsd } from "../../utils/format";
import { MetricCard, PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  ErrorState,
  EvidenceBadge,
  LoadingState,
  UncertaintyPanel,
} from "../../components/data-status/DataStatus";
import type { EconomicScenarioSpec, EngineEnvelope } from "../../types/api";

export default function ScenariosPage() {
  const { selectedCropId, selectedLocation } = useApp();
  const [tab, setTab] = useState<"economic" | "socio">("economic");

  // Phase 8 Economic Scenarios
  const [econScenarios, setEconScenarios] = useState<EconomicScenarioSpec[]>([]);
  const [scenarioId, setScenarioId] = useState("");
  const [baseYield, setBaseYield] = useState("3.0");
  const [basePrice, setBasePrice] = useState("450");
  const [econResult, setEconResult] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [loadingEcon, setLoadingEcon] = useState(false);

  // Phase 6 Nemotron Socio-Agricultural
  const [nemotronProfiles, setNemotronProfiles] = useState<Array<Record<string, unknown>>>([]);
  const [socioScenarios, setSocioScenarios] = useState<Record<string, Record<string, unknown>>>({});
  const [selectedSocioId, setSelectedSocioId] = useState("A");
  const [socioRunRes, setSocioRunRes] = useState<Record<string, unknown> | null>(null);
  const [loadingSocio, setLoadingSocio] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    agrosvApi.economicScenarios(ac.signal)
      .then(({ data }) => {
        const list = data.result?.scenarios ?? [];
        setEconScenarios(list);
        if (list.length) setScenarioId(list[0].scenario_id);
      })
      .catch(() => undefined);
    return () => ac.abort();
  }, []);

  useEffect(() => {
    if (tab !== "socio") return;
    const ac = new AbortController();
    setLoadingSocio(true);
    Promise.allSettled([
      agrosvApi.nemotronProfiles(selectedLocation.departmentName, 8, ac.signal),
      agrosvApi.socioScenarios(ac.signal),
    ]).then(([np, sc]) => {
      if (np.status === "fulfilled") {
        setNemotronProfiles((np.value.data.profiles as Array<Record<string, unknown>>) ?? []);
      }
      if (sc.status === "fulfilled") {
        const map = (sc.value.data.scenarios as Record<string, Record<string, unknown>>) ?? {};
        setSocioScenarios(map);
      }
      setLoadingSocio(false);
    });
    return () => ac.abort();
  }, [tab, selectedLocation.departmentName]);

  const runEcon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scenarioId) return;
    setLoadingEcon(true);
    setError(null);
    try {
      const res = await agrosvApi.runEconomicScenario({
        scenario_id: scenarioId,
        crop_id: selectedCropId,
        area_ha: 1.0,
        baseline_yield_t_ha: Number(baseYield) || 3.0,
        baseline_price_per_t: Number(basePrice) || 450,
        baseline_costs: { seed: 90, fertilizer: 280, labor: 320, pesticide: 70, transport: 60 },
        fixed_costs: 120,
        baseline_post_harvest_loss: 0.05,
      });
      setEconResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error ejecutando escenario");
    } finally {
      setLoadingEcon(false);
    }
  };

  const runSocio = async () => {
    setLoadingSocio(true);
    setError(null);
    try {
      const res = await agrosvApi.runSocioScenario({
        scenario_id: selectedSocioId,
        lat: selectedLocation.lat,
        lon: selectedLocation.lon,
        size: 30,
        population_source: "nemotron",
      });
      setSocioRunRes(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error ejecutando escenario socio-agrícola");
    } finally {
      setLoadingSocio(false);
    }
  };

  const econRes = (econResult?.result ?? {}) as Record<string, unknown>;
  const baseline = (econRes.baseline ?? {}) as Record<string, number>;
  const scenarioOut = (econRes.scenario_result ?? {}) as Record<string, number>;
  const delta = (econRes.delta_vs_baseline ?? {}) as Record<string, number>;

  return (
    <div className="stack-md">
      <PageHeader
        title="Análisis de Escenarios y Modelado Socio-Agrícola"
        subtitle="Comparación condicional de choques económicos (Fase 8) y perfiles agrícolas sintéticos Nemotron (Fase 6)."
      />

      <div className="tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab === "economic"} className="tab-btn" onClick={() => setTab("economic")}>
          Escenarios económicos ({econScenarios.length})
        </button>
        <button type="button" role="tab" aria-selected={tab === "socio"} className="tab-btn" onClick={() => setTab("socio")}>
          Socio-agrícola sintético (Nemotron SV)
        </button>
      </div>

      {error && <ErrorState message={error} />}

      {tab === "economic" && (
        <div className="stack-md">
          <div className="callout callout--synthetic">
            <strong>Simulación condicional (no es pronóstico):</strong> compara cómo cambia el margen operativo respecto a tu línea base bajo supuestos declarados.
          </div>

          <form onSubmit={runEcon} className="card stack-sm">
            <div className="grid-3">
              <label className="field">
                <span className="field-label">Escenario configurable</span>
                <select className="select" value={scenarioId} onChange={(e) => setScenarioId(e.target.value)}>
                  {econScenarios.map((s) => (
                    <option key={s.scenario_id} value={s.scenario_id}>{s.label}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Rendimiento base (t/ha)</span>
                <input type="number" step="0.1" className="input" value={baseYield} onChange={(e) => setBaseYield(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Precio base (USD/t)</span>
                <input type="number" step="1" className="input" value={basePrice} onChange={(e) => setBasePrice(e.target.value)} />
              </label>
            </div>
            <div>
              <button type="submit" className="btn btn-primary" disabled={loadingEcon}>
                {loadingEcon ? "Simulando…" : "Comparar contra línea base"}
              </button>
            </div>
          </form>

          {econResult && (
            <div className="stack-md">
              <div className="grid-3">
                <MetricCard label="Margen neto línea base" value={fmtUsd(baseline.net_operating_margin)} evidenceClass="model_estimate" />
                <MetricCard label="Margen neto escenario" value={fmtUsd(scenarioOut.net_operating_margin)} synthetic />
                <MetricCard label="Diferencia vs línea base" value={fmtUsd(delta.net_margin_delta)} detail={`Δ Costos: ${fmtUsd(delta.cost_delta)}`} synthetic />
              </div>
              <UncertaintyPanel assumptions={econResult.assumptions} limitations={econResult.limitations} />
            </div>
          )}
        </div>
      )}

      {tab === "socio" && (
        <div className="stack-md">
          <div className="callout callout--synthetic">
            <strong>Simulación sintética — no es un hogar real observado ni encuestado.</strong> Los perfiles derivados de Nemotron Personas El Salvador y los escenarios A–G exploran restricciones hipotéticas y nunca sustituyen un censo oficial.
          </div>

          <div className="grid-2">
            <section className="card stack-sm">
              <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                <h2 className="card-title">Escenarios socio-agrícolas (A–G)</h2>
                <EvidenceBadge synthetic />
              </div>
              <label className="field">
                <span className="field-label">Escenario</span>
                <select className="select" value={selectedSocioId} onChange={(e) => setSelectedSocioId(e.target.value)}>
                  {Object.entries(socioScenarios).map(([id, spec]) => (
                    <option key={id} value={id}>{id}: {String(spec.name ?? spec.label ?? id)}</option>
                  ))}
                  {Object.keys(socioScenarios).length === 0 && <option value="A">Escenario A</option>}
                </select>
              </label>
              <button type="button" className="btn btn-primary btn-sm" onClick={runSocio} disabled={loadingSocio}>
                {loadingSocio ? "Ejecutando…" : "Simular escenario socio-agrícola"}
              </button>
              {socioRunRes && (
                <pre style={{ margin: 0, padding: 10, borderRadius: 8, background: "var(--bg-subtle)", fontSize: 11.5, overflowX: "auto", maxHeight: 280 }}>
                  {JSON.stringify(socioRunRes.result ?? socioRunRes, null, 2)}
                </pre>
              )}
            </section>

            <section className="card stack-sm">
              <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                <h2 className="card-title">Muestra de perfiles agrícolas Nemotron SV</h2>
                <DataStatusBadge tone="synthetic" label="Sintético" />
              </div>
              {loadingSocio && nemotronProfiles.length === 0 ? (
                <LoadingState />
              ) : (
                <div className="stack-sm">
                  {nemotronProfiles.slice(0, 6).map((p, idx) => (
                    <div key={String(p.uuid ?? idx)} style={{ padding: 10, borderRadius: 8, background: "var(--bg-subtle)", fontSize: 12.5 }}>
                      <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                        <strong>{String(p.occupation ?? "Perfil agrícola")}</strong>
                        <span>{String(p.department ?? "SV")} · {String(p.area ?? "")}</span>
                      </div>
                      <div style={{ color: "var(--ink-muted)", marginTop: 3 }}>
                        Arquetipo sugerido: {String(p.archetype_hint ?? "—")} · Edad: {fmtNum(p.age as number, 0)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
