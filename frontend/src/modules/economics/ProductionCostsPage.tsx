import React, { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { deleteBudgetLocal, listSavedBudgets, saveBudgetLocal, type SavedCostBudget } from "../../services/offline/storage";
import { useApp } from "../../stores/AppContext";
import { downloadCsv } from "../../utils/csv";
import { convertArea, convertMass, fmtNum, fmtUsd } from "../../utils/format";
import { MetricCard, PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  ErrorState,
  EvidenceBadge,
  LoadingState,
  UncertaintyPanel,
} from "../../components/data-status/DataStatus";
import { ChartFrame, SvgBarChart } from "../../components/charts/Charts";
import type { CropSummary, EngineEnvelope } from "../../types/api";

interface CostItemForm {
  id: string;
  category: string;
  description: string;
  amount: string;
  nature: "variable" | "fixed";
  per: "cycle" | "ha";
}

const DEFAULT_ITEMS: CostItemForm[] = [
  { id: "c1", category: "seeds", description: "Semilla certificada", amount: "85", nature: "variable", per: "cycle" },
  { id: "c2", category: "fertilizers", description: "Fertilizante (fórmula + urea)", amount: "260", nature: "variable", per: "cycle" },
  { id: "c3", category: "labor", description: "Mano de obra (siembra, limpia, cosecha)", amount: "310", nature: "variable", per: "cycle" },
  { id: "c4", category: "pesticides", description: "Control fitosanitario", amount: "65", nature: "variable", per: "cycle" },
  { id: "c5", category: "transport", description: "Transporte y poscosecha", amount: "70", nature: "variable", per: "cycle" },
  { id: "c6", category: "land_or_equipment", description: "Arrendamiento / equipo fijo", amount: "120", nature: "fixed", per: "cycle" },
];

export default function ProductionCostsPage() {
  const { selectedCropId, setSelectedCropId, areaUnit, setAreaUnit, simpleMode } = useApp();
  const [tab, setTab] = useState<"costs" | "production">("costs");
  const [crops, setCrops] = useState<CropSummary[]>([]);

  // Production stats
  const [statsEnv, setStatsEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [systems, setSystems] = useState<Record<string, Record<string, unknown>>>({});
  const [loadingStats, setLoadingStats] = useState(false);

  // Cost calculator
  const [areaVal, setAreaVal] = useState("1");
  const [expectedProd, setExpectedProd] = useState("45");
  const [prodUnit, setProdUnit] = useState<"qq" | "t" | "kg">("qq");
  const [items, setItems] = useState<CostItemForm[]>(DEFAULT_ITEMS);
  const [costEnv, setCostEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [calcErr, setCalcErr] = useState<string | null>(null);
  const [savedBudgets, setSavedBudgets] = useState<SavedCostBudget[]>(() => listSavedBudgets());

  useEffect(() => {
    const ac = new AbortController();
    agrosvApi.crops(undefined, undefined, ac.signal).then(({ data }) => setCrops(data.crops ?? [])).catch(() => undefined);
    return () => ac.abort();
  }, []);

  useEffect(() => {
    if (tab !== "production") return;
    const ac = new AbortController();
    setLoadingStats(true);
    Promise.allSettled([
      agrosvApi.productionStatistics(undefined, "national", undefined, ac.signal),
      agrosvApi.productionSystems(ac.signal),
    ]).then(([st, sy]) => {
      if (st.status === "fulfilled") setStatsEnv(st.value.data);
      if (sy.status === "fulfilled") setSystems((sy.value.data.result?.systems as typeof systems) ?? {});
      setLoadingStats(false);
    });
    return () => ac.abort();
  }, [tab]);

  const calculateCosts = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setCalcLoading(true);
    setCalcErr(null);
    try {
      const res = await agrosvApi.aggregateCosts({
        items: items.map((it) => ({
          category: it.category,
          description: it.description,
          amount: Number(it.amount) || 0,
          nature: it.nature,
          per: it.per,
          currency: "USD",
        })),
        area_value: Number(areaVal) || 1,
        area_unit: areaUnit,
        production_value: Number(expectedProd) > 0 ? Number(expectedProd) : undefined,
        production_unit: prodUnit,
        currency: "USD",
      });
      setCostEnv(res);
    } catch (err) {
      setCalcErr(err instanceof Error ? err.message : "Error calculando costos");
    } finally {
      setCalcLoading(false);
    }
  };

  useEffect(() => {
    calculateCosts();
  }, []);

  const addItem = () => {
    setItems((prev) => [
      ...prev,
      { id: `c-${Date.now()}`, category: "other", description: "Nuevo rubro", amount: "0", nature: "variable", per: "cycle" },
    ]);
  };

  const updateItem = (id: string, patch: Partial<CostItemForm>) => {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, ...patch } : it)));
  };

  const removeItem = (id: string) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
  };

  const saveCurrentBudget = () => {
    const budget: SavedCostBudget = {
      id: `BDG-${Date.now()}`,
      name: `${selectedCropId} · ${areaVal} ${areaUnit}`,
      cropId: selectedCropId,
      areaValue: Number(areaVal) || 1,
      areaUnit,
      savedAt: new Date().toISOString(),
      items: items.map(({ category, description, amount, nature, per }) => ({
        category,
        description,
        amount: Number(amount) || 0,
        nature,
        per,
      })),
      result: (costEnv?.result ?? undefined) as Record<string, unknown> | undefined,
    };
    setSavedBudgets(saveBudgetLocal(budget));
  };

  const costRes = (costEnv?.result ?? {}) as Record<string, unknown>;
  const totals = (costRes.totals ?? {}) as Record<string, unknown>;
  const byCategory = (totals.by_category ?? {}) as Record<string, number>;
  const byNature = (totals.by_nature ?? {}) as Record<string, number>;
  const unitCosts = (costRes.unit_costs ?? {}) as Record<string, number | null>;
  const areaNum = Number(areaVal) || 1;
  const haConverted = convertArea(areaNum, areaUnit, "ha");
  const mzConverted = convertArea(areaNum, areaUnit, "mz");
  const prodNum = Number(expectedProd) || 0;
  const prodTons = convertMass(prodNum, prodUnit, "t");

  const capRecords = ((statsEnv?.result?.cap_2025_records ?? []) as Array<Record<string, unknown>>);

  return (
    <div className="stack-md">
      <PageHeader
        title="Producción y Costos Agrícolas (Fase 8)"
        subtitle="Calculadora de costos en unidades salvadoreñas (manzanas, quintales) y estadísticas oficiales nacionales."
        actions={
          <div className="row-wrap">
            <select className="select" style={{ width: "auto" }} aria-label="Cultivo" value={selectedCropId} onChange={(e) => setSelectedCropId(e.target.value)}>
              {crops.map((c) => <option key={c.crop_id} value={c.crop_id}>{c.local_names[0] ?? c.crop_id}</option>)}
            </select>
            <select className="select" style={{ width: "auto" }} aria-label="Unidad de superficie" value={areaUnit} onChange={(e) => setAreaUnit(e.target.value as "mz" | "ha")}>
              <option value="mz">Manzanas (mz)</option>
              <option value="ha">Hectáreas (ha)</option>
            </select>
          </div>
        }
      />

      <div className="tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab === "costs"} className="tab-btn" onClick={() => setTab("costs")}>
          Calculadora de costos
        </button>
        <button type="button" role="tab" aria-selected={tab === "production"} className="tab-btn" onClick={() => setTab("production")}>
          Estadísticas de producción (CAP 2025)
        </button>
      </div>

      {tab === "costs" && (
        <div className="stack-md">
          <div className="callout callout--info">
            <strong>Conversiones explícitas:</strong> 1 manzana (mz) = 0.70 ha · 1 quintal (qq) = 46 kg · 1 tonelada (t) = 1,000 kg.
            Tu superficie equivale a <strong className="tabular-nums">{fmtNum(mzConverted, 2, "mz")}</strong> (<strong className="tabular-nums">{fmtNum(haConverted, 2, "ha")}</strong>) y tu cosecha esperada a <strong className="tabular-nums">{fmtNum(prodTons, 2, "t")}</strong>.
          </div>

          <form onSubmit={calculateCosts} className="card stack-md">
            <div className="grid-3">
              <label className="field">
                <span className="field-label">Superficie cultivada ({areaUnit})</span>
                <input type="number" step="0.1" min="0.1" className="input" value={areaVal} onChange={(e) => setAreaVal(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Producción esperada ({prodUnit})</span>
                <input type="number" step="0.1" min="0" className="input" value={expectedProd} onChange={(e) => setExpectedProd(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Unidad de producción</span>
                <select className="select" value={prodUnit} onChange={(e) => setProdUnit(e.target.value as typeof prodUnit)}>
                  <option value="qq">Quintales (46 kg)</option>
                  <option value="t">Toneladas (1000 kg)</option>
                  <option value="kg">Kilogramos (kg)</option>
                </select>
              </label>
            </div>

            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Categoría</th><th>Descripción del gasto</th><th>Naturaleza</th><th>Monto (USD)</th><th>Base</th><th /></tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.id}>
                      <td>
                        <select className="select" aria-label="Categoría" value={it.category} onChange={(e) => updateItem(it.id, { category: e.target.value })}>
                          <option value="seeds">Semillas</option>
                          <option value="fertilizers">Fertilizantes</option>
                          <option value="pesticides">Fitosanitarios</option>
                          <option value="labor">Mano de obra</option>
                          <option value="irrigation">Riego</option>
                          <option value="transport">Transporte / poscosecha</option>
                          <option value="land_or_equipment">Tierra / maquinaria</option>
                          <option value="other">Otros</option>
                        </select>
                      </td>
                      <td>
                        <input className="input" aria-label="Descripción" value={it.description} onChange={(e) => updateItem(it.id, { description: e.target.value })} />
                      </td>
                      <td>
                        <select className="select" aria-label="Naturaleza" value={it.nature} onChange={(e) => updateItem(it.id, { nature: e.target.value as "variable" | "fixed" })}>
                          <option value="variable">Variable</option>
                          <option value="fixed">Fijo</option>
                        </select>
                      </td>
                      <td>
                        <input type="number" min="0" step="0.01" className="input" aria-label="Monto USD" value={it.amount} onChange={(e) => updateItem(it.id, { amount: e.target.value })} />
                      </td>
                      <td>
                        <select className="select" aria-label="Base" value={it.per} onChange={(e) => updateItem(it.id, { per: e.target.value as "cycle" | "ha" })}>
                          <option value="cycle">Total ciclo</option>
                          <option value="ha">Por ha</option>
                        </select>
                      </td>
                      <td>
                        <button type="button" className="btn btn-sm" onClick={() => removeItem(it.id)}>Quitar</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="row-wrap">
              <button type="button" className="btn" onClick={addItem}>+ Agregar rubro</button>
              <button type="submit" className="btn btn-primary" disabled={calcLoading}>
                {calcLoading ? "Calculando…" : "Calcular costos"}
              </button>
              <button type="button" className="btn" onClick={saveCurrentBudget}>Guardar presupuesto local</button>
              {!simpleMode && (
                <button type="button" className="btn" onClick={() => downloadCsv(`costos_${selectedCropId}.csv`, items as unknown as Array<Record<string, unknown>>)}>
                  Exportar CSV
                </button>
              )}
            </div>
          </form>

          {calcErr && <ErrorState message={calcErr} />}

          {costEnv && (
            <div className="stack-md">
              <div className="grid-4">
                <MetricCard label="Costo total del ciclo" value={fmtUsd(totals.total as number)} detail={`Variables: ${fmtUsd(byNature.variable)} · Fijos: ${fmtUsd(byNature.fixed)}`} evidenceClass="producer_reported" />
                <MetricCard label="Costo por manzana" value={fmtUsd(unitCosts.cost_per_mz)} unit="/ mz" evidenceClass="derived" />
                <MetricCard label="Costo por hectárea" value={fmtUsd(unitCosts.cost_per_ha)} unit="/ ha" evidenceClass="derived" />
                <MetricCard label="Costo por quintal (46 kg)" value={fmtUsd(unitCosts.cost_per_qq46)} detail={`Por tonelada: ${fmtUsd(unitCosts.cost_per_t)}`} evidenceClass="derived" />
              </div>

              {Object.keys(byCategory).length > 0 && (
                <ChartFrame
                  title="Desglose de costos por categoría"
                  unit="USD"
                  source="Presupuesto ingresado por el usuario · AgriculturalCostEngine"
                  rows={Object.entries(byCategory).map(([cat, amt]) => ({ Categoría: cat, "Costo (USD)": amt }))}
                >
                  <SvgBarChart
                    data={Object.entries(byCategory).map(([cat, amt]) => ({ label: cat, value: amt }))}
                    unit="USD"
                  />
                </ChartFrame>
              )}

              <UncertaintyPanel collapsedByDefault={simpleMode} assumptions={costEnv.assumptions} limitations={costEnv.limitations} />
            </div>
          )}

          {savedBudgets.length > 0 && (
            <section className="card">
              <h2 className="card-title">Presupuestos guardados localmente ({savedBudgets.length})</h2>
              <div className="stack-sm" style={{ marginTop: 8 }}>
                {savedBudgets.map((b) => (
                  <div key={b.id} className="row-wrap" style={{ justifyContent: "space-between", padding: 8, background: "var(--bg-subtle)", borderRadius: 8 }}>
                    <span><strong>{b.name}</strong> · {b.items.length} rubros · {b.savedAt.slice(0, 10)}</span>
                    <button type="button" className="btn btn-sm" onClick={() => setSavedBudgets(deleteBudgetLocal(b.id))}>Eliminar</button>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {tab === "production" && (
        <div className="stack-md">
          <div className="callout callout--warn">
            <strong>Alcance oficial CAP 2025:</strong> los tabulados públicos disponibles cubren totales nacionales y participaciones departamentales. No existen microdatos municipales ni parcelarios abiertos; AGROSV no los infiere.
          </div>
          {loadingStats ? (
            <LoadingState />
          ) : (
            <>
              <section className="card">
                <div className="row-wrap" style={{ justifyContent: "space-between", marginBottom: 10 }}>
                  <h2 className="card-title">V Censo Agropecuario 2025 (entregas públicas preliminares)</h2>
                  <EvidenceBadge evidenceClass="official_statistic" />
                </div>
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr><th>Cultivo</th><th>Superficie cosechada (mz)</th><th>Producción (qq)</th><th>Periodo</th><th>Fuente</th></tr>
                    </thead>
                    <tbody>
                      {capRecords.map((r) => {
                        const v = (r.value ?? {}) as Record<string, unknown>;
                        return (
                          <tr key={String(r.record_id)}>
                            <td><strong>{String(v.crop_name_es ?? r.product_or_activity)}</strong></td>
                            <td className="tabular-nums">{fmtNum(v.harvested_area_mz as number, 0, "mz")}</td>
                            <td className="tabular-nums">{fmtNum(v.production_qq as number, 0, "qq")}</td>
                            <td className="tabular-nums">{String(r.reference_period)}</td>
                            <td style={{ fontSize: 12 }}>{String(r.source)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="card">
                <h2 className="card-title">Sistemas productivos documentados ({Object.keys(systems).length})</h2>
                <div className="grid-3" style={{ marginTop: 10 }}>
                  {Object.entries(systems).map(([id, sys]) => (
                    <div key={id} style={{ padding: 10, borderRadius: 8, background: "var(--bg-subtle)", fontSize: 13 }}>
                      <div className="row-wrap" style={{ justifyContent: "space-between" }}>
                        <strong>{String(sys.label)}</strong>
                        <DataStatusBadge tone="info" label={String(sys.water_regime)} />
                      </div>
                      <div style={{ color: "var(--ink-muted)", marginTop: 4, fontSize: 12 }}>
                        {((sys.characteristics as string[]) ?? []).join(" · ")}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      )}
    </div>
  );
}
