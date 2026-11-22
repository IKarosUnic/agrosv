"""AGROSV Phase 8 — Subsistema D: Rentabilidad y Análisis Financiero.

Contiene los 7 motores del Subsistema D:
1. AgriculturalProfitabilityEngine
2. RevenueAnalysisEngine
3. BreakEvenAnalysisEngine
4. GrossMarginEngine
5. NetMarginEngine
6. AgriculturalInvestmentAnalysisEngine
7. AgriculturalEconomicRiskEngine
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..monitoring.risks import AgriculturalRiskEngine
from . import governance as EG

ENGINE_VERSION = EG.ENGINE_VERSION


class RevenueAnalysisEngine:
    """Estima ingresos bajo cosecha, mermas poscosecha, calidad, canales y fletes."""

    engine = "revenue_analysis"
    version = ENGINE_VERSION

    def analyze(
        self,
        *,
        harvested_t: float,
        channels: Iterable[Mapping[str, Any]],
        post_harvest_loss_fraction: float = 0.0,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if harvested_t < 0:
            raise EG.EconomicError("harvested_t debe ser >= 0")
        if not (0.0 <= post_harvest_loss_fraction <= 1.0):
            raise EG.EconomicError("post_harvest_loss_fraction debe estar en [0, 1]")

        saleable_t = harvested_t * (1.0 - post_harvest_loss_fraction)
        ch_list = list(channels)
        if not ch_list:
            raise EG.EconomicError("se requiere al menos un canal de comercialización")

        share_sum = sum(float(c.get("share", 0.0)) for c in ch_list)
        if abs(share_sum - 1.0) > 0.01:
            raise EG.EconomicError(f"las proporciones de canales deben sumar 1.0 (recibido {share_sum})")

        gross_rev = 0.0
        net_rev = 0.0
        breakdown: list[dict[str, Any]] = []
        for c in ch_list:
            share = float(c["share"])
            qty_t = saleable_t * share
            price_t = float(c["price_per_t"])
            q_factor = float(c.get("quality_factor", 1.0))
            transport_t = float(c.get("transport_per_t", 0.0))
            comm_t = float(c.get("commercialization_per_t", 0.0))
            ch_gross = qty_t * price_t * q_factor
            ch_net = ch_gross - qty_t * (transport_t + comm_t)
            gross_rev += ch_gross
            net_rev += ch_net
            breakdown.append({
                "channel": c.get("channel", "unspecified"),
                "share": share,
                "volume_t": round(qty_t, 4),
                "price_per_t": round(price_t, 2),
                "quality_factor": q_factor,
                "gross_revenue": round(ch_gross, 2),
                "marketing_and_transport_cost": round(qty_t * (transport_t + comm_t), 2),
                "net_revenue": round(ch_net, 2),
            })

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "harvested_t": round(harvested_t, 4),
                "post_harvest_loss_t": round(harvested_t - saleable_t, 4),
                "saleable_t": round(saleable_t, 4),
                "gross_revenue": round(gross_rev, 2),
                "net_revenue_after_marketing": round(net_rev, 2),
                "weighted_net_price_per_t": round(net_rev / saleable_t, 2) if saleable_t > 0 else None,
                "channels": breakdown,
            },
            sources=["agrosv_scenario"],
            assumptions=["el volumen vendible se reparte exactamente entre los canales declarados"],
            limitations=["no asume que el 100% de la cosecha alcance el precio máximo de plaza"],
            evidence_class="model_estimate",
            query={"harvested_t": harvested_t, "n_channels": len(breakdown)},
        )


class GrossMarginEngine:
    """Calcula margen bruto = ingresos - costos variables directos explícitos."""

    engine = "gross_margin"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        gross_revenue: float,
        variable_costs: Mapping[str, float],
        area_ha: float = 1.0,
        excluded_costs: Iterable[str] = ("fixed_costs", "depreciation", "family_unpaid_labor", "financing"),
        currency: str = "USD",
    ) -> dict[str, Any]:
        if area_ha <= 0:
            raise EG.EconomicError("area_ha debe ser > 0")
        total_var = sum(float(v) for v in variable_costs.values())
        gm = gross_revenue - total_var
        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "formula": "gross_margin = gross_revenue - sum(variable_costs)",
                "gross_revenue": round(gross_revenue, 2),
                "total_variable_cost": round(total_var, 2),
                "gross_margin": round(gm, 2),
                "gross_margin_per_ha": round(gm / area_ha, 2),
                "gross_margin_ratio": round(gm / gross_revenue, 4) if gross_revenue > 0 else None,
                "included_variable_costs": {k: round(float(v), 2) for k, v in variable_costs.items()},
                "excluded_costs": list(excluded_costs),
                "is_net_profit": False,
            },
            sources=["agrosv_scenario"],
            assumptions=["solo incluye costos variables directos declarados"],
            limitations=["el margen bruto NO es utilidad neta; excluye costos fijos y depreciación"],
            evidence_class="model_estimate",
            query={"area_ha": area_ha},
        )


class NetMarginEngine:
    """Calcula rentabilidad operativa neta distinguiendo caja, contable y económica."""

    engine = "net_margin"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        gross_revenue: float,
        variable_costs: float,
        fixed_cash_costs: float = 0.0,
        depreciation: float = 0.0,
        financing_costs: float = 0.0,
        unpaid_family_labor: float = 0.0,
        opportunity_cost_land_or_capital: float = 0.0,
        area_ha: float = 1.0,
        cost_model_complete: bool = True,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if area_ha <= 0:
            raise EG.EconomicError("area_ha debe ser > 0")
        cash_operating = gross_revenue - variable_costs - fixed_cash_costs
        accounting_before_fin = cash_operating - depreciation
        accounting_net = accounting_before_fin - financing_costs
        economic_net = accounting_net - unpaid_family_labor - opportunity_cost_land_or_capital

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "area_ha": round(area_ha, 4),
                "cash_operating_result": round(cash_operating, 2),
                "accounting_excluding_financing": round(accounting_before_fin, 2),
                "accounting_net_result": round(accounting_net, 2),
                "economic_result_with_family_labor": round(economic_net, 2),
                "economic_result_per_ha": round(economic_net / area_ha, 2),
                "cost_model_complete": cost_model_complete,
                "completeness_warning": (
                    None
                    if cost_model_complete
                    else "modelo de costos incompleto: no interpretar como utilidad neta integral"
                ),
            },
            sources=["agrosv_scenario"],
            assumptions=[
                "resultado de caja excluye depreciación y trabajo familiar no pagado",
                "resultado económico deduce trabajo familiar imputado y costo de oportunidad",
            ],
            limitations=["la validez depende de la completitud de costos declarados"],
            evidence_class="model_estimate",
            query={"area_ha": area_ha, "cost_model_complete": cost_model_complete},
        )


class BreakEvenAnalysisEngine:
    """Calcula puntos de equilibrio (precio, rendimiento, volumen, área) y sensibilidad."""

    engine = "break_even_analysis"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        fixed_costs: float,
        variable_cost_per_ha: float,
        area_ha: float,
        expected_yield_t_ha: float,
        price_per_t: float,
        variable_selling_cost_per_t: float = 0.0,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if area_ha <= 0 or expected_yield_t_ha < 0 or price_per_t < 0:
            raise EG.EconomicError("parámetros de área/rendimiento/precio inválidos")

        total_cost = fixed_costs + variable_cost_per_ha * area_ha
        total_vol_t = expected_yield_t_ha * area_ha
        net_price_t = price_per_t - variable_selling_cost_per_t

        be_price_t = (total_cost / total_vol_t + variable_selling_cost_per_t) if total_vol_t > 0 else None
        be_yield_t_ha = (total_cost / (area_ha * net_price_t)) if net_price_t > 0 else None
        be_volume_t = (total_cost / net_price_t) if net_price_t > 0 else None

        margin_per_ha_before_fixed = expected_yield_t_ha * net_price_t - variable_cost_per_ha
        be_area_ha = (fixed_costs / margin_per_ha_before_fixed) if margin_per_ha_before_fixed > 0 else None

        # Sensibilidad a cambios de costo total (-10%, +10%, +25%)
        sensitivity = []
        for delta in (-0.10, 0.0, 0.10, 0.25):
            adj_cost = total_cost * (1.0 + delta)
            sensitivity.append({
                "cost_change_pct": round(delta * 100.0, 1),
                "adjusted_total_cost": round(adj_cost, 2),
                "break_even_price_per_t": round(adj_cost / total_vol_t + variable_selling_cost_per_t, 2)
                if total_vol_t > 0
                else None,
                "break_even_yield_t_ha": round(adj_cost / (area_ha * net_price_t), 4)
                if net_price_t > 0
                else None,
            })

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "total_cost": round(total_cost, 2),
                "expected_volume_t": round(total_vol_t, 4),
                "break_even_price_per_t": round(be_price_t, 2) if be_price_t is not None else None,
                "break_even_price_per_qq46": (
                    round(EG.normalize_unit_price(be_price_t, "t", target_unit="46 kg"), 2)
                    if be_price_t is not None
                    else None
                ),
                "break_even_yield_t_ha": round(be_yield_t_ha, 4) if be_yield_t_ha is not None else None,
                "break_even_yield_qq_mz": (
                    round(EG.convert_mass(be_yield_t_ha, "t", "qq") * EG.MANZANA_TO_HA, 2)
                    if be_yield_t_ha is not None
                    else None
                ),
                "break_even_volume_t": round(be_volume_t, 4) if be_volume_t is not None else None,
                "break_even_area_ha": round(be_area_ha, 4) if be_area_ha is not None else None,
                "formulas": {
                    "break_even_price_per_t": "(fixed + var_ha * area) / (yield * area) + selling_cost_t",
                    "break_even_yield_t_ha": "total_cost / (area * (price_t - selling_cost_t))",
                    "break_even_volume_t": "total_cost / (price_t - selling_cost_t)",
                    "break_even_area_ha": "fixed_costs / (yield * (price_t - selling_cost_t) - var_ha)",
                },
                "cost_sensitivity": sensitivity,
            },
            sources=["agrosv_scenario"],
            assumptions=["costos fijos constantes dentro del rango evaluado"],
            limitations=["no modela cambios no lineales de rendimiento con el área"],
            evidence_class="model_estimate",
            query={"area_ha": area_ha, "expected_yield_t_ha": expected_yield_t_ha, "price_per_t": price_per_t},
        )


class AgriculturalProfitabilityEngine:
    """Motor unificado de rentabilidad por ha, ciclo y unidad."""

    engine = "agricultural_profitability"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        crop_id: str,
        area_ha: float,
        yield_t_ha: float,
        price_per_t: float,
        variable_cost_total: float,
        fixed_cost_total: float = 0.0,
        post_harvest_loss_fraction: float = 0.0,
        marketing_cost_per_t: float = 0.0,
        unpaid_family_labor: float = 0.0,
        investment_base: float | None = None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if area_ha <= 0 or yield_t_ha < 0 or price_per_t < 0:
            raise EG.EconomicError("parámetros inválidos para rentabilidad")
        harvested_t = area_ha * yield_t_ha
        rev = RevenueAnalysisEngine().analyze(
            harvested_t=harvested_t,
            post_harvest_loss_fraction=post_harvest_loss_fraction,
            channels=[{"channel": "primary", "share": 1.0, "price_per_t": price_per_t, "commercialization_per_t": marketing_cost_per_t}],
            currency=currency,
        )["result"]
        net_rev = rev["net_revenue_after_marketing"]
        total_cost = variable_cost_total + fixed_cost_total
        gross_margin = net_rev - variable_cost_total
        net_operating = net_rev - total_cost
        economic_profit = net_operating - unpaid_family_labor
        saleable_t = rev["saleable_t"]

        roi = None
        inv_denom = investment_base if investment_base and investment_base > 0 else (total_cost if total_cost > 0 else None)
        if inv_denom:
            roi = round(net_operating / inv_denom, 4)

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop_id,
                "currency": currency.upper(),
                "area_ha": round(area_ha, 4),
                "harvested_t": round(harvested_t, 4),
                "saleable_t": saleable_t,
                "gross_revenue": rev["gross_revenue"],
                "net_revenue_after_marketing": net_rev,
                "total_production_cost": round(total_cost, 2),
                "gross_margin": round(gross_margin, 2),
                "net_operating_margin": round(net_operating, 2),
                "economic_profit_after_family_labor": round(economic_profit, 2),
                "profit_per_ha": round(net_operating / area_ha, 2),
                "profit_per_cycle": round(net_operating, 2),
                "profit_per_t": round(net_operating / saleable_t, 2) if saleable_t > 0 else None,
                "return_on_cost_or_investment": roi,
                "distinction": {
                    "accounting_operating_margin": round(net_operating, 2),
                    "economic_estimate_with_imputed_labor": round(economic_profit, 2),
                },
            },
            sources=["agrosv_scenario"],
            assumptions=["cálculos deterministas de ingreso neto menos costos declarados"],
            limitations=["no constituye contabilidad auditada ni utilidad garantizada"],
            evidence_class="model_estimate",
            query={"crop_id": crop_id, "area_ha": area_ha, "yield_t_ha": yield_t_ha, "price_per_t": price_per_t},
        )


class AgriculturalInvestmentAnalysisEngine:
    """Evalúa payback, VAN (NPV) y TIR (IRR) sobre flujos explícitos."""

    engine = "agricultural_investment_analysis"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        investment_type: str,
        initial_investment: float,
        annual_cash_flows: Iterable[float] | None = None,
        annual_benefit: float | None = None,
        annual_operating_cost: float = 0.0,
        annual_maintenance: float = 0.0,
        useful_life_years: int | None = None,
        discount_rate: float | None = None,
        discount_rate_justification: str | None = None,
        financing_terms: Mapping[str, Any] | None = None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if initial_investment <= 0:
            raise EG.EconomicError("initial_investment debe ser > 0")

        if annual_cash_flows is not None:
            flows = [float(f) for f in annual_cash_flows]
        elif annual_benefit is not None and useful_life_years and useful_life_years > 0:
            net_yr = float(annual_benefit) - float(annual_operating_cost) - float(annual_maintenance)
            flows = [net_yr] * int(useful_life_years)
        else:
            raise EG.EconomicError("aporte annual_cash_flows o (annual_benefit + useful_life_years)")

        # Payback simple
        cum = -float(initial_investment)
        payback: float | None = None
        for idx, cf in enumerate(flows, start=1):
            prev = cum
            cum += cf
            if cum >= 0 and payback is None:
                payback = round((idx - 1) + (-prev / cf), 2) if cf > 0 else float(idx)

        npv = None
        if discount_rate is not None:
            if not discount_rate_justification:
                raise EG.EconomicError("discount_rate requiere 'discount_rate_justification'")
            r = float(discount_rate)
            npv = -float(initial_investment) + sum(
                cf / ((1.0 + r) ** t) for t, cf in enumerate(flows, start=1)
            )
            npv = round(npv, 2)

        # TIR por bisección cuando hay cambio de signo
        irr = None
        all_cf = [-float(initial_investment)] + flows
        if any(x > 0 for x in flows):
            def _npv_at(rate: float) -> float:
                return sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(all_cf))

            lo, hi = -0.95, 5.0
            f_lo, f_hi = _npv_at(lo), _npv_at(hi)
            if f_lo * f_hi <= 0:
                for _ in range(80):
                    mid = (lo + hi) / 2.0
                    f_mid = _npv_at(mid)
                    if abs(f_mid) < 1e-6:
                        lo = hi = mid
                        break
                    if f_lo * f_mid <= 0:
                        hi, f_hi = mid, f_mid
                    else:
                        lo, f_lo = mid, f_mid
                irr = round((lo + hi) / 2.0, 4)

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "investment_type": investment_type,
                "initial_investment": round(initial_investment, 2),
                "years": len(flows),
                "annual_net_cash_flows": [round(f, 2) for f in flows],
                "payback_years": payback,
                "discount_rate": discount_rate,
                "discount_rate_justification": discount_rate_justification,
                "npv": npv,
                "irr": irr,
                "financing_terms": dict(financing_terms) if financing_terms else "not_supplied",
                "returns_guaranteed": False,
            },
            sources=["agrosv_scenario"],
            assumptions=["flujos netos constantes o explícitamente aportados por año"],
            limitations=[
                "no inventa tasas de interés bancarias ni garantiza retornos financieros",
            ],
            evidence_class="model_estimate",
            query={"investment_type": investment_type, "initial_investment": initial_investment},
        )


class AgriculturalEconomicRiskEngine:
    """Evalúa exposición económica y la enlaza con motores de riesgo de Fase 7."""

    engine = "agricultural_economic_risk"
    version = ENGINE_VERSION

    EXPOSURE_FACTORS = (
        "input_price_increase",
        "output_price_decrease",
        "yield_reduction",
        "drought",
        "flooding",
        "pest_outbreak",
        "disease",
        "transport_disruption",
        "labor_shortage",
        "storage_loss",
        "credit_cost",
    )

    def __init__(self) -> None:
        self.phase7_risk = AgriculturalRiskEngine()

    def assess(
        self,
        *,
        baseline_revenue: float,
        baseline_cost: float,
        exposures: Mapping[str, float] | None = None,
        phase7_hazard: float | None = None,
        phase7_vulnerability: float | None = None,
        yield_shock_fraction: float = 0.0,
        price_shock_fraction: float = 0.0,
        input_cost_shock_fraction: float = 0.0,
        storage_loss_fraction: float = 0.0,
        currency: str = "USD",
    ) -> dict[str, Any]:
        exp_map = {k: round(float(v), 4) for k, v in (exposures or {}).items() if k in self.EXPOSURE_FACTORS}
        p7_res = None
        if phase7_hazard is not None and phase7_vulnerability is not None:
            exp_val = max(exp_map.values()) if exp_map else 0.5
            p7_res = self.phase7_risk.assess(
                hazard=phase7_hazard,
                exposure=min(1.0, max(0.0, exp_val)),
                vulnerability=phase7_vulnerability,
            )

        stressed_rev = (
            baseline_revenue
            * (1.0 - max(0.0, min(1.0, yield_shock_fraction)))
            * (1.0 - max(0.0, min(1.0, price_shock_fraction)))
            * (1.0 - max(0.0, min(1.0, storage_loss_fraction)))
        )
        stressed_cost = baseline_cost * (1.0 + max(0.0, input_cost_shock_fraction))
        base_margin = baseline_revenue - baseline_cost
        stressed_margin = stressed_rev - stressed_cost

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "baseline_margin": round(base_margin, 2),
                "stressed_revenue": round(stressed_rev, 2),
                "stressed_cost": round(stressed_cost, 2),
                "stressed_margin": round(stressed_margin, 2),
                "modeled_margin_impact": round(stressed_margin - base_margin, 2),
                "exposures": exp_map,
                "phase7_risk_integration": p7_res,
                "is_actual_financial_loss": False,
            },
            sources=["agrosv_scenario"],
            assumptions=["la exposición modelada aplica choques multiplicativos declarados"],
            limitations=[
                "exposición modelada no equivale a pérdida financiera real observada",
            ],
            evidence_class="model_estimate",
            query={"baseline_revenue": baseline_revenue, "baseline_cost": baseline_cost},
        )


__all__ = [
    "AgriculturalEconomicRiskEngine",
    "AgriculturalInvestmentAnalysisEngine",
    "AgriculturalProfitabilityEngine",
    "BreakEvenAnalysisEngine",
    "GrossMarginEngine",
    "NetMarginEngine",
    "RevenueAnalysisEngine",
]
