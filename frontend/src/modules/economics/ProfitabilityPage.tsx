import React, { useEffect, useState } from "react";
import { agrosvApi } from "../../services/api/endpoints";
import { useApp } from "../../stores/AppContext";
import { convertArea, convertMass, fmtNum, fmtUsd } from "../../utils/format";
import { MetricCard, PageHeader } from "../../components/dashboard/MetricCard";
import {
  DataStatusBadge,
  ErrorState,
  UncertaintyPanel,
} from "../../components/data-status/DataStatus";
import type { EngineEnvelope } from "../../types/api";

type TabId = "margins" | "investment" | "household";

interface InvestmentPreset {
  id: string;
  name: string;
  initial: number;
  benefit: number;
  opCost: number;
  maintenance: number;
  lifeYears: number;
  description: string;
}

const INVESTMENT_PRESETS: InvestmentPreset[] = [
  {
    id: "irrigation_drip",
    name: "Sistema de riego por goteo (1 mz)",
    initial: 2200,
    benefit: 850,
    opCost: 120,
    maintenance: 80,
    lifeYears: 5,
    description: "Cintas de goteo, cabezal de filtrado y fertirriego para hortalizas o granos básicos.",
  },
  {
    id: "water_reservoir",
    name: "Reservorio de geomembrana (captación lluvia)",
    initial: 3500,
    benefit: 1200,
    opCost: 60,
    maintenance: 150,
    lifeYears: 8,
    description: "Almacenamiento de agua de escorrentía para riego suplementario durante la canícula.",
  },
  {
    id: "solar_pumping",
    name: "Bombeo solar fotovoltaico para pozo",
    initial: 4200,
    benefit: 1400,
    opCost: 40,
    maintenance: 100,
    lifeYears: 10,
    description: "Paneles solares e inversor con bomba sumergible; elimina el costo recurrente de diésel o electricidad.",
  },
  {
    id: "metal_silo",
    name: "Módulo de silos metálicos herméticos CENTA (18 qq)",
    initial: 650,
    benefit: 280,
    opCost: 15,
    maintenance: 20,
    lifeYears: 7,
    description: "Conservación poscosecha hermética sin plaguicidas químicos; previene merma de granos básicos.",
  },
  {
    id: "greenhouse",
    name: "Macrotúnel / Casa malla hortícola",
    initial: 2800,
    benefit: 1100,
    opCost: 180,
    maintenance: 140,
    lifeYears: 4,
    description: "Estructura de protección contra vectores fitosanitarios (mosca blanca) y exceso de lluvia.",
  },
];

export default function ProfitabilityPage() {
  const { selectedCropId, setSelectedCropId, areaUnit, setAreaUnit, simpleMode } = useApp();
  const [tab, setTab] = useState<TabId>("margins");

  // Tab 1: Margins & Break-even
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

  // Tab 2: Financial Investment Evaluation
  const [selectedPresetId, setSelectedPresetId] = useState("irrigation_drip");
  const [invType, setInvType] = useState("irrigation_drip");
  const [invInitial, setInvInitial] = useState("2200");
  const [invAnnualBenefit, setInvAnnualBenefit] = useState("850");
  const [invOpCost, setInvOpCost] = useState("120");
  const [invMaint, setInvMaint] = useState("80");
  const [invLifeYears, setInvLifeYears] = useState("5");
  const [invDiscountRate, setInvDiscountRate] = useState("8");
  const [invEnv, setInvEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [invLoading, setInvLoading] = useState(false);
  const [invError, setInvError] = useState<string | null>(null);

  // Tab 3: Household Economy (Nemotron)
  const [hhAgRev, setHhAgRev] = useState("3200");
  const [hhProdExp, setHhProdExp] = useState("1800");
  const [hhNonAgInc, setHhNonAgInc] = useState("750");
  const [hhConsump, setHhConsump] = useState("2640");
  const [hhCredit, setHhCredit] = useState("250");
  const [hhEnv, setHhEnv] = useState<EngineEnvelope<Record<string, unknown>> | null>(null);
  const [hhLoading, setHhLoading] = useState(false);
  const [hhError, setHhError] = useState<string | null>(null);

  const areaHa = convertArea(Number(areaVal) || 1, areaUnit, "ha");
  const yieldTHa =
    areaUnit === "mz"
      ? convertMass(Number(yieldPerUnit) || 0, "qq", "t") / 0.7
      : Number(yieldPerUnit) || 0;
  const pricePerT = (Number(pricePerQq) || 0) * (1000 / 46);
  const marketingPerT = (Number(marketingPerQq) || 0) * (1000 / 46);

  const evaluateMargins = async (e?: React.FormEvent) => {
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

  const evaluateInvestment = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setInvLoading(true);
    setInvError(null);
    try {
      const res = await agrosvApi.investment({
        investment_type: invType,
        initial_investment: Number(invInitial) || 1000,
        annual_benefit: Number(invAnnualBenefit) || 0,
        annual_operating_cost: Number(invOpCost) || 0,
        annual_maintenance: Number(invMaint) || 0,
        useful_life_years: Number(invLifeYears) || 5,
        discount_rate: (Number(invDiscountRate) || 8) / 100,
        discount_rate_justification: "Tasa de descuento de referencia BCR El Salvador (8%)",
        currency: "USD",
      });
      setInvEnv(res);
    } catch (err) {
      setInvError(err instanceof Error ? err.message : "Error evaluando inversión");
    } finally {
      setInvLoading(false);
    }
  };

  const evaluateHousehold = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setHhLoading(true);
    setHhError(null);
    try {
      const res = await agrosvApi.householdEconomy({
        agricultural_revenue_usd: Number(hhAgRev) || 0,
        production_expense_usd: Number(hhProdExp) || 0,
        non_agricultural_income_usd: Number(hhNonAgInc) || 0,
        consumption_usd: Number(hhConsump) || 0,
        credit_obligation_usd: Number(hhCredit) || 0,
      });
      setHhEnv(res);
    } catch (err) {
      setHhError(err instanceof Error ? err.message : "Error analizando economía del hogar");
    } finally {
      setHhLoading(false);
    }
  };

  const applyPreset = (preset: InvestmentPreset) => {
    setSelectedPresetId(preset.id);
    setInvType(preset.id);
    setInvInitial(String(preset.initial));
    setInvAnnualBenefit(String(preset.benefit));
    setInvOpCost(String(preset.opCost));
    setInvMaint(String(preset.maintenance));
    setInvLifeYears(String(preset.lifeYears));
  };

  useEffect(() => {
    evaluateMargins();
    evaluateInvestment();
    evaluateHousehold();
  }, []);

  const prof = (profEnv?.result ?? {}) as Record<string, unknown>;
  const be = (beEnv?.result ?? {}) as Record<string, unknown>;
  const sensitivity = (be.cost_sensitivity ?? []) as Array<Record<string, number | null>>;
  const incompleteWarnings: string[] = [];
  if ((Number(fixedCostTotal) || 0) === 0) incompleteWarnings.push("Costos fijos = $0 (renta, depreciación u overhead excluidos)");
  if ((Number(unpaidFamilyLabor) || 0) === 0) incompleteWarnings.push("Mano de obra familiar no remunerada = $0");

  const invRes = (invEnv?.result ?? {}) as Record<string, unknown>;
  const cashFlows = (invRes.annual_net_cash_flows ?? []) as number[];

  const hhRes = (hhEnv?.result ?? {}) as Record<string, unknown>;
  const hhEcon = (hhRes.economy ?? {}) as Record<string, unknown>;
  const hhState = (hhEcon.household_state ?? {}) as Record<string, unknown>;

  return (
    <div className="stack-md">
      <PageHeader
        title="Rentabilidad, Inversión y Economía del Hogar (Fase 8)"
        subtitle="Evaluación financiera científica: márgenes operativos, punto de equilibrio, retorno de capital (VAN/TIR) y balance familiar."
        actions={
          <select className="select" style={{ width: "auto" }} aria-label="Unidad" value={areaUnit} onChange={(e) => setAreaUnit(e.target.value as "mz" | "ha")}>
            <option value="mz">Trabajar en Manzanas y Quintales</option>
            <option value="ha">Trabajar en Hectáreas y Toneladas</option>
          </select>
        }
      />

      <div className="tabs" role="tablist" aria-label="Submódulos de rentabilidad">
        {[
          ["margins", "Margen y punto de equilibrio"],
          ["investment", "Evaluación de inversiones (VAN, TIR)"],
          ["household", "Economía del hogar (Nemotron)"],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className="tab-btn"
            onClick={() => setTab(id as TabId)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* TAB 1: MARGENES Y EQUILIBRIO */}
      {tab === "margins" && (
        <div className="stack-md">
          {incompleteWarnings.length > 0 && (
            <div className="callout callout--warn">
              <strong>Cálculo financiero parcial:</strong> {incompleteWarnings.join(" · ")}. El resultado operativo no debe interpretarse como utilidad contable integral si faltan categorías de costo.
            </div>
          )}

          <form onSubmit={evaluateMargins} className="card stack-md">
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
      )}

      {/* TAB 2: INVERSION FINANCIERA */}
      {tab === "investment" && (
        <div className="stack-md">
          <div className="callout callout--info">
            <strong>Evaluación de inversiones de capital (Criterio VAN / TIR / Payback):</strong> Evalúa si una inversión productiva (riego, reservorio, silos) genera retorno económico sobre el costo de oportunidad del capital (tasa de corte 8% BCR).
          </div>

          <section className="card stack-sm">
            <h2 className="card-title">Plantillas de inversión agropecuaria en El Salvador</h2>
            <div className="row-wrap" style={{ gap: 8 }}>
              {INVESTMENT_PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={`btn btn-sm ${selectedPresetId === p.id ? "btn-primary" : ""}`}
                  onClick={() => applyPreset(p)}
                >
                  {p.name}
                </button>
              ))}
            </div>
            {INVESTMENT_PRESETS.find((p) => p.id === selectedPresetId) && (
              <p style={{ fontSize: 13, color: "var(--ink-secondary)", margin: "4px 0 0" }}>
                {INVESTMENT_PRESETS.find((p) => p.id === selectedPresetId)?.description}
              </p>
            )}
          </section>

          <form onSubmit={evaluateInvestment} className="card stack-md">
            <div className="grid-3">
              <label className="field">
                <span className="field-label">Inversión inicial (USD)</span>
                <input type="number" step="50" min="50" className="input" value={invInitial} onChange={(e) => setInvInitial(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Beneficio anual adicional (USD)</span>
                <input type="number" step="50" min="0" className="input" value={invAnnualBenefit} onChange={(e) => setInvAnnualBenefit(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Costo operativo anual (USD)</span>
                <input type="number" step="10" min="0" className="input" value={invOpCost} onChange={(e) => setInvOpCost(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Mantenimiento anual (USD)</span>
                <input type="number" step="10" min="0" className="input" value={invMaint} onChange={(e) => setInvMaint(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Vida útil estimada (años)</span>
                <input type="number" step="1" min="1" max="25" className="input" value={invLifeYears} onChange={(e) => setInvLifeYears(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Tasa de descuento anual (%)</span>
                <input type="number" step="0.5" min="1" max="30" className="input" value={invDiscountRate} onChange={(e) => setInvDiscountRate(e.target.value)} />
              </label>
            </div>

            <div className="row-wrap" style={{ justifyContent: "flex-end" }}>
              <button type="submit" className="btn btn-primary" disabled={invLoading}>
                {invLoading ? "Evaluando…" : "Calcular viabilidad financiera"}
              </button>
            </div>
          </form>

          {invError && <ErrorState message={invError} />}

          {invEnv && (
            <div className="stack-md">
              <div className="grid-3">
                <MetricCard
                  label="Periodo de recuperación (Payback)"
                  value={invRes.payback_years !== null ? fmtNum(invRes.payback_years as number, 1, "años") : "No recupera"}
                  detail={`Vida útil: ${invRes.years ?? invLifeYears} años`}
                  evidenceClass="model_estimate"
                />
                <MetricCard
                  label="Valor Actual Neto (VAN / NPV)"
                  value={fmtUsd(invRes.npv as number)}
                  detail={(invRes.npv as number) >= 0 ? "Viable (VAN ≥ 0)" : "No viable con esta tasa"}
                  evidenceClass="model_estimate"
                />
                <MetricCard
                  label="Tasa Interna de Retorno (TIR / IRR)"
                  value={invRes.irr !== null ? fmtNum((invRes.irr as number) * 100, 1, "%") : "Indeterminada"}
                  detail={`Tasa de corte: ${invDiscountRate}% BCR`}
                  evidenceClass="model_estimate"
                />
              </div>

              {cashFlows.length > 0 && (
                <section className="card">
                  <h2 className="card-title">Proyección de flujos netos anuales</h2>
                  <div className="table-wrap" style={{ marginTop: 10 }}>
                    <table className="data-table">
                      <thead>
                        <tr><th>Año</th><th>Flujo de caja neto</th><th>Estado acumulado</th></tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td><strong>Año 0 (Inversión inicial)</strong></td>
                          <td className="tabular-nums" style={{ color: "var(--crimson)" }}>−{fmtUsd(Number(invInitial))}</td>
                          <td className="tabular-nums">−{fmtUsd(Number(invInitial))}</td>
                        </tr>
                        {cashFlows.map((cf, idx) => (
                          <tr key={idx}>
                            <td>Año {idx + 1}</td>
                            <td className="tabular-nums" style={{ color: "var(--primary-dark)" }}>+{fmtUsd(cf)}</td>
                            <td className="tabular-nums">Operación en marcha</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}

              <UncertaintyPanel
                collapsedByDefault={simpleMode}
                assumptions={invEnv.assumptions}
                limitations={invEnv.limitations}
              />
            </div>
          )}
        </div>
      )}

      {/* TAB 3: ECONOMIA DEL HOGAR */}
      {tab === "household" && (
        <div className="stack-md">
          <div className="callout callout--info">
            <strong>Modelo sintético de economía del hogar (Nemotron Fase 6):</strong> Evalúa la sostenibilidad económica de la unidad familiar agraria considerando ingresos de campo, trabajo extra-predial, remesas, cuotas de deuda y el costo de vida rural en El Salvador.
          </div>

          <form onSubmit={evaluateHousehold} className="card stack-md">
            <div className="grid-3">
              <label className="field">
                <span className="field-label">Ingresos agrícolas brutos (USD/año)</span>
                <input type="number" step="50" min="0" className="input" value={hhAgRev} onChange={(e) => setHhAgRev(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Gastos de producción agrícola (USD/año)</span>
                <input type="number" step="50" min="0" className="input" value={hhProdExp} onChange={(e) => setHhProdExp(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Ingresos fuera de finca / remesas (USD/año)</span>
                <input type="number" step="50" min="0" className="input" value={hhNonAgInc} onChange={(e) => setHhNonAgInc(e.target.value)} />
              </label>
              <label className="field">
                <span className="field-label">Consumo básico familiar (USD/año)</span>
                <input type="number" step="50" min="0" className="input" value={hhConsump} onChange={(e) => setHhConsump(e.target.value)} />
                <span style={{ fontSize: 11, color: "var(--ink-muted)" }}>Ref. Canasta Básica Rural salvadoreña ~$220/mes ($2,640/año)</span>
              </label>
              <label className="field">
                <span className="field-label">Obligaciones de crédito (USD/año)</span>
                <input type="number" step="50" min="0" className="input" value={hhCredit} onChange={(e) => setHhCredit(e.target.value)} />
              </label>
            </div>

            <div className="row-wrap" style={{ justifyContent: "flex-end" }}>
              <button type="submit" className="btn btn-primary" disabled={hhLoading}>
                {hhLoading ? "Calculando…" : "Analizar economía del hogar"}
              </button>
            </div>
          </form>

          {hhError && <ErrorState message={hhError} />}

          {hhEnv && (
            <div className="stack-md">
              <div className="grid-3">
                <MetricCard
                  label="Flujo de caja agrícola neto"
                  value={fmtUsd(hhEcon.net_agricultural_cashflow_usd as number)}
                  detail="Ingresos agrícolas − costos productivos"
                  evidenceClass="model_estimate"
                />
                <MetricCard
                  label="Saldo neto de ahorro del hogar"
                  value={fmtUsd(hhEcon.net_savings_change_usd as number)}
                  detail={(hhEcon.net_savings_change_usd as number) >= 0 ? "Superávit familiar" : "Déficit / consumo de capital"}
                  evidenceClass="model_estimate"
                />
                <MetricCard
                  label="Brecha de liquidez estimada"
                  value={fmtUsd(hhEcon.liquidity_gap_usd as number)}
                  detail="Capital operativo de amortiguación"
                  evidenceClass="model_estimate"
                />
              </div>

              {hhState && (
                <section className="card">
                  <div className="card-header">
                    <div>
                      <h2 className="card-title">Composición del hogar sintético (Nemotron)</h2>
                      <div className="card-subtitle">Estructura demográfica y disponibilidad de fuerza de trabajo</div>
                    </div>
                    <DataStatusBadge tone="info" label="Sintético Nemotron" />
                  </div>
                  <div className="grid-3" style={{ marginTop: 10 }}>
                    <dl className="kv-list" style={{ background: "var(--bg-subtle)", padding: 12, borderRadius: 8 }}>
                      <div className="kv-row"><dt>Tipo de hogar</dt><dd>{String(hhState.household_type ?? "Extendida")}</dd></div>
                      <div className="kv-row"><dt>Miembros</dt><dd>{String(hhState.size ?? 5)} personas</dd></div>
                      <div className="kv-row"><dt>Adultos / Niños</dt><dd>{String(hhState.adults ?? 3)} / {String(hhState.children ?? 2)}</dd></div>
                    </dl>
                    <dl className="kv-list" style={{ background: "var(--bg-subtle)", padding: 12, borderRadius: 8 }}>
                      <div className="kv-row"><dt>Jornadas familiares/año</dt><dd>{String(hhState.labor_days_household ?? 434)} días</dd></div>
                      <div className="kv-row"><dt>Disponibilidad laboral</dt><dd>{fmtNum((hhState.labor_availability_factor as number) * 100, 1, "%")}</dd></div>
                      <div className="kv-row"><dt>Presupuesto operativo</dt><dd>{fmtUsd(hhEcon.operating_budget_usd as number)}</dd></div>
                    </dl>
                    <div style={{ background: "var(--bg-subtle)", padding: 12, borderRadius: 8, fontSize: 13 }}>
                      <strong>Opciones de adaptación identif.:</strong>
                      <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
                        {((hhState.adaptation_options as string[]) ?? ["Diversificación de cultivos", "Riego"]).map((opt, i) => (
                          <li key={i}>{opt}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </section>
              )}

              <UncertaintyPanel
                collapsedByDefault={simpleMode}
                assumptions={hhEnv.assumptions}
                limitations={hhEnv.limitations}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
