import React, { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { convertArea, convertMass, fmtNum, fmtUsd } from "../../utils/format";
import { MetricCard, PageHeader } from "../../components/dashboard/MetricCard";
import {
  ErrorState,
  UncertaintyPanel,
} from "../../components/data-status/DataStatus";
import type { EngineEnvelope } from "../../types/api";

export default function ProfitabilityPage() {
  const { selectedCropId, setSelectedCropId, areaUnit, setAreaUnit, simpleMode } = useApp();

  const [areaVal, setAreaVal] = useState("2");
  const [yieldPerUnit, setYieldPerUnit] = useState("45"); // qq/mz o t/ha
  const [pricePerQq, setPricePerQq] = useState("22");
  const [varCostTotal, setVarCostTotal] = useState("1580");
  const [fixedCostTotal, setFixedCostTotal] = useState("240");
  const [postHarvestLossPct, setPostHarvestLossPct] = useState("5");
  const [marketingPerQq, setMarketingPerQq] = useState("1.5");
  const [unpaidFamilyLabor, setUnpaidFamilyLabor] = useState("0");

  const [profEnv, setProfEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [beEnv, setBeEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const areaHa = convertArea(Number(areaVal) || 1, areaUnit, "ha");
  const yieldTHa =
    areaUnit === "mz"
      ? convertMass(Number(yieldPerUnit) || 0, "qq", "t") / 0.7
      : Number(yieldPerUnit) || 0;
  const pricePerT = (Number(pricePerQq) || 0) * (1000 / 46);
  const marketingPerT = (Number(marketingPerQq) || 0) * (1000 / 46);

  const evaluate = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const [pRes, bRes] = await Promise.all([
        agrosvApi.profitability({
          crop_id: selectedCropId,
          area_ha: areaHa,
          yield_t_ha: yieldTHa,
          price_per_t: pricePerT,
          variable_cost_total: Number(varCostTotal) || 0,
          fixed_cost_total: Number(fixedCostTotal) || 0,
          post_harvest_loss_fraction: (Number(postHarvestLossPct) || 0) / 100,
          marketing_cost_per_t: marketingPerT,
          unpaid_family_labor: Number(unpaidFamilyLabor) || 0,
          currency: "USD",
        }),
        agrosvApi.breakEven({
          fixed_costs: Number(fixedCostTotal) || 0,
          variable_cost_per_ha: (Number(varCostTotal) || 0) / Math.max(areaHa, 0.01),
          area_ha: areaHa,
          expected_yield_t_ha: yieldTHa,
          price_per_t: pricePerT,
          variable_selling_cost_per_t: marketingPerT,
          currency: "USD",
        }),
      ]);
      setProfEnv(pRes);
      setBeEnv(bRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error calculando rentabilidad");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    evaluate();
  }, []);

  const prof = (profEnv?.result ?? {}) as Record<string, unknown>;
  const be = (beEnv?.result ?? {}) as Record<string, unknown>;
  const sensitivity = (be.cost_sensitivity ?? []) as Array<Record<string, number | null>>;
  const incompleteWarnings: string[] = [];
  if ((Number(fixedCostTotal) || 0) === 0) incompleteWarnings.push("Costos fijos = $0 (renta, depreciación u overhead excluidos)");
  if ((Number(unpaidFamilyLabor) || 0) === 0) incompleteWarnings.push("Mano de obra familiar no remunerada = $0");

  return (
    <div className="stack-md">
      <PageHeader
        title="Calculadora de Rentabilidad y Punto de Equilibrio (Fase 8)"
        subtitle="Fórmulas explícitas, conversión automática de unidades salvadoreñas y sensibilidad ante variación de costos."
        actions={
          <select className="select" style={{ width: "auto" }} aria-label="Unidad" value={areaUnit} onChange={(e) => setAreaUnit(e.target.value as "mz" | "ha")}>
            <option value="mz">Trabajar en Manzanas y Quintales</option>
            <option value="ha">Trabajar en Hectáreas y Toneladas</option>
          </select>
        }
      />

      {incompleteWarnings.length > 0 && (
        <div className="callout callout--warn">
          <strong>Cálculo financiero parcial:</strong> {incompleteWarnings.join(" · ")}. El resultado operativo no debe interpretarse como utilidad contable integral si faltan categorías de costo.
        </div>
      )}

      <form onSubmit={evaluate} className="card stack-md">
        <div className="grid-4">
          <label className="field">
            <span className="field-label">Cultivo</span>
            <select className="select" value={selectedCropId} onChange={(e) => setSelectedCropId(e.target.value)}>
              <option value="maize">Maíz (maize)</option>
              <option value="beans">Frijol (beans)</option>
              <option value="rice">Arroz (rice)</option>
              <option value="sorghum">Sorgo (sorghum)</option>
              <option value="coffee">Café (coffee)</option>
              <option value="tomato">Tomate (tomato)</option>
            </select>
          </label>
          <label className="field">
            <span className="field-label">Superficie ({areaUnit})</span>
            <input type="number" step="0.1" min="0.1" className="input" value={areaVal} onChange={(e) => setAreaVal(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Rendimiento ({areaUnit === "mz" ? "qq/mz" : "t/ha"})</span>
            <input type="number" step="0.1" min="0" className="input" value={yieldPerUnit} onChange={(e) => setYieldPerUnit(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Precio de venta (USD / qq 46 kg)</span>
            <input type="number" step="0.1" min="0" className="input" value={pricePerQq} onChange={(e) => setPricePerQq(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Costos variables totales (USD)</span>
            <input type="number" step="1" min="0" className="input" value={varCostTotal} onChange={(e) => setVarCostTotal(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Costos fijos totales (USD)</span>
            <input type="number" step="1" min="0" className="input" value={fixedCostTotal} onChange={(e) => setFixedCostTotal(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Merma poscosecha (%)</span>
            <input type="number" step="0.5" min="0" max="100" className="input" value={postHarvestLossPct} onChange={(e) => setPostHarvestLossPct(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Flete/comercialización (USD/qq)</span>
            <input type="number" step="0.1" min="0" className="input" value={marketingPerQq} onChange={(e) => setMarketingPerQq(e.target.value)} />
          </label>
        </div>

        <div className="row-wrap">
          <label className="field" style={{ maxWidth: 280 }}>
            <span className="field-label">Valoración trabajo familiar no pagado (USD)</span>
            <input type="number" step="1" min="0" className="input" value={unpaidFamilyLabor} onChange={(e) => setUnpaidFamilyLabor(e.target.value)} />
          </label>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ alignSelf: "flex-end" }}>
            {loading ? "Calculando…" : "Calcular rentabilidad"}
          </button>
        </div>
      </form>

      {error && <ErrorState message={error} />}

      {profEnv && (
        <div className="stack-md">
          <div className="grid-4">
            <MetricCard label="Ingreso bruto" value={fmtUsd(prof.gross_revenue as number)} detail={`Vol. vendible: ${fmtNum(prof.saleable_t as number, 2, "t")}`} evidenceClass="model_estimate" />
            <MetricCard label="Margen bruto" value={fmtUsd(prof.gross_margin as number)} detail="Ingreso neto − costos variables" evidenceClass="model_estimate" />
            <MetricCard label="Resultado operativo neto" value={fmtUsd(prof.net_operating_margin as number)} detail={`Por ha: ${fmtUsd(prof.profit_per_ha as number)}`} evidenceClass="model_estimate" />
            <MetricCard label="Precio de equilibrio" value={fmtUsd(be.break_even_price_per_qq46 as number)} unit="/ qq" detail={`Rend. equilibrio: ${fmtNum(be.break_even_yield_qq_mz as number, 1, "qq/mz")}`} evidenceClass="model_estimate" />
          </div>

          {sensitivity.length > 0 && (
            <section className="card">
              <h2 className="card-title">Análisis de sensibilidad ante cambios en costos</h2>
              <div className="table-wrap" style={{ marginTop: 10 }}>
                <table className="data-table">
                  <thead>
                    <tr><th>Variación costo</th><th>Costo total ajustado</th><th>Precio equilibrio (USD/t)</th><th>Rendimiento equilibrio (t/ha)</th></tr>
                  </thead>
                  <tbody>
                    {sensitivity.map((row) => (
                      <tr key={String(row.cost_change_pct)}>
                        <td className="tabular-nums"><strong>{(row.cost_change_pct ?? 0) >= 0 ? `+${row.cost_change_pct}%` : `${row.cost_change_pct}%`}</strong></td>
                        <td className="tabular-nums">{fmtUsd(row.adjusted_total_cost)}</td>
                        <td className="tabular-nums">{fmtUsd(row.break_even_price_per_t)}</td>
                        <td className="tabular-nums">{fmtNum(row.break_even_yield_t_ha, 2, "t/ha")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <UncertaintyPanel collapsedByDefault={simpleMode} assumptions={profEnv.assumptions} limitations={profEnv.limitations} />
        </div>
      )}
    </div>
  );
}
