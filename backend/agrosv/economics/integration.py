"""AGROSV Phase 8 — Subsistema G: Inteligencia Económica Integrada.

Contiene los 5 motores del Subsistema G:
1. AgriculturalEconomicIntegrationEngine
2. AgriculturalEconomicScenarioEngine (15 escenarios configurables)
3. AgriculturalDecisionSupportEngine
4. AgriculturalEconomicAnalysisEngine
5. AgriculturalEconomicReportingEngine
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..agriculture.calendar import AgriculturalCalendarEngine
from ..agriculture.catalog import CROPS
from ..agriculture.suitability import CropSuitabilityEngine
from ..engines.territorial import TerritorialEngine, validate_coordinate
from ..monitoring.risks import AgriculturalRiskEngine
from ..social.population import AgriculturalPopulationEngine
from . import governance as EG
from .costs import AgriculturalCostEngine, ProductionBudgetEngine
from .household_econ import AgriculturalHouseholdEconomyEngine
from .markets import (
    AGROSV_TO_WFP_COMMODITIES,
    AgriculturalPriceEngine,
    MarketComparisonEngine,
    PriceHistoryEngine,
)
from .production import AgriculturalProductionEngine, ProductionStatisticsEngine
from .profitability import (
    AgriculturalProfitabilityEngine,
    BreakEvenAnalysisEngine,
)
from .supply_chain import AgriculturalLogisticsEngine, AgriculturalValueChainEngine, MarketAccessEngine

ENGINE_VERSION = EG.ENGINE_VERSION

ECONOMIC_SCENARIOS: dict[str, dict[str, Any]] = {
    "fertilizer_price_increase": {
        "label": "Alza en precio de fertilizantes",
        "changes": {"fertilizer_cost_mult": 1.35},
    },
    "seed_price_increase": {
        "label": "Alza en precio de semillas",
        "changes": {"seed_cost_mult": 1.30},
    },
    "fuel_price_increase": {
        "label": "Alza en precio de combustible y flete",
        "changes": {"fuel_cost_mult": 1.40, "transport_mult": 1.35},
    },
    "reduced_yield": {
        "label": "Reducción de rendimiento",
        "changes": {"yield_mult": 0.75},
    },
    "lower_market_price": {
        "label": "Caída de precio de mercado",
        "changes": {"price_mult": 0.75},
    },
    "higher_market_price": {
        "label": "Alza de precio de mercado",
        "changes": {"price_mult": 1.25},
    },
    "drought": {
        "label": "Sequía / canícula severa",
        "changes": {"yield_mult": 0.65, "irrigation_cost_mult": 1.25},
    },
    "excess_rainfall": {
        "label": "Exceso de lluvia / anegamiento",
        "changes": {"yield_mult": 0.72, "post_harvest_loss_add": 0.05},
    },
    "pest_or_disease_damage": {
        "label": "Daño por plagas o enfermedades",
        "changes": {"yield_mult": 0.78, "pesticide_cost_mult": 1.40},
    },
    "irrigation_adoption": {
        "label": "Adopción de riego tecnificado",
        "changes": {"yield_mult": 1.25, "irrigation_cost_mult": 1.50, "fixed_cost_add": 120.0},
    },
    "crop_diversification": {
        "label": "Diversificación de cultivos",
        "changes": {"yield_mult": 0.95, "price_mult": 1.12, "other_cost_mult": 1.10},
    },
    "protected_agriculture": {
        "label": "Agricultura protegida",
        "changes": {"yield_mult": 1.60, "fixed_cost_add": 450.0, "other_cost_mult": 1.35},
    },
    "improved_storage": {
        "label": "Almacenamiento mejorado",
        "changes": {"post_harvest_loss_mult": 0.30, "storage_cost_add": 35.0, "price_mult": 1.08},
    },
    "alternative_commercialization": {
        "label": "Canal de comercialización alternativo",
        "changes": {"price_mult": 1.15, "transport_mult": 1.15},
    },
    "transport_disruption": {
        "label": "Disrupción de transporte y acceso vial",
        "changes": {"transport_mult": 1.80, "post_harvest_loss_add": 0.04},
    },
}


class AgriculturalEconomicIntegrationEngine:
    """Integra Fases 5, 6, 7 y 8 para una consulta territorial-productiva-económica."""

    engine = "agricultural_economic_integration"
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.territory = TerritorialEngine()
        self.suitability = CropSuitabilityEngine()
        self.calendar = AgriculturalCalendarEngine()
        self.production = AgriculturalProductionEngine()
        self.prices = AgriculturalPriceEngine()
        self.logistics = AgriculturalLogisticsEngine()
        self.access = MarketAccessEngine()
        self.profitability = AgriculturalProfitabilityEngine()
        self.break_even = BreakEvenAnalysisEngine()
        self.risk = AgriculturalRiskEngine()
        self.population = AgriculturalPopulationEngine()
        self.household_econ = AgriculturalHouseholdEconomyEngine()

    def evaluate(
        self,
        *,
        lon: float,
        lat: float,
        crop_id: str,
        system_id: str = "rainfed",
        area_ha: float = 1.0,
        planting_date: str | None = None,
        cost_items: Iterable[Mapping[str, Any]] | None = None,
        expected_yield_t_ha: float | None = None,
        price_per_t: float | None = None,
        use_wfp_reference_price: bool = False,
        market: str = "San Salvador",
        phase7_hazard: float | None = None,
        phase7_vulnerability: float | None = None,
        include_nemotron_household: bool = False,
        seed: int = 42,
        currency: str = "USD",
    ) -> dict[str, Any]:
        lon_v, lat_v = validate_coordinate(lon, lat)
        crop = crop_id.strip().lower()
        if crop not in CROPS:
            raise EG.EconomicError(f"cultivo desconocido: {crop_id!r}")

        terr = self.territory.locate(lon_v, lat_v)
        prod = self.production.assess(
            crop_id=crop,
            scale="parcel",
            system_id=system_id,
            area_ha=area_ha,
            lon=lon_v,
            lat=lat_v,
            department=terr.get("administrative", {}).get("department", {}).get("name"),
            planting_date=planting_date,
            reference_yield_t_ha=expected_yield_t_ha,
        )["result"]

        log_res = self.logistics.evaluate(
            lon=lon_v, lat=lat_v, crop_id=crop, quantity_t=max(0.1, (expected_yield_t_ha or 1.0) * area_ha)
        )["result"]

        # Precio: explícito o referencia WFP (etiquetada como plaza mayorista, no precio en finca)
        resolved_price = price_per_t
        price_source = "user_supplied" if price_per_t is not None else None
        if resolved_price is None and use_wfp_reference_price and crop in AGROSV_TO_WFP_COMMODITIES:
            wq = self.prices.query(crop_id=crop, market=market, price_type="wholesale", target_unit="t", limit=1)
            if wq["result"]["records"]:
                rec = wq["result"]["records"][0]
                resolved_price = rec["normalized_price"]
                price_source = f"WFP wholesale ({rec['market']}, {rec['observation_date']})"

        # Costos y rentabilidad solo si se aportan costos; nunca inventar costos
        cost_block: dict[str, Any] = {"available": False, "reason": "sin cost_items aportados"}
        profit_block: dict[str, Any] = {"available": False, "reason": "faltan costos, rendimiento o precio"}
        be_block: dict[str, Any] = {"available": False}

        items_list = list(cost_items or [])
        if items_list:
            agg = AgriculturalCostEngine().aggregate(
                items=items_list,
                area_value=area_ha,
                area_unit="ha",
                production_value=(expected_yield_t_ha * area_ha) if expected_yield_t_ha is not None else None,
                currency=currency,
            )["result"]
            cost_block = {"available": True, **agg}

            if expected_yield_t_ha is not None and resolved_price is not None:
                var_total = agg["totals"]["by_nature"]["variable"]
                fix_total = agg["totals"]["by_nature"]["fixed"]
                profit_block = self.profitability.evaluate(
                    crop_id=crop,
                    area_ha=area_ha,
                    yield_t_ha=expected_yield_t_ha,
                    price_per_t=resolved_price,
                    variable_cost_total=var_total,
                    fixed_cost_total=fix_total,
                    currency=currency,
                )["result"]
                profit_block["available"] = True
                profit_block["price_source"] = price_source
                be_block = self.break_even.evaluate(
                    fixed_costs=fix_total,
                    variable_cost_per_ha=var_total / area_ha,
                    area_ha=area_ha,
                    expected_yield_t_ha=expected_yield_t_ha,
                    price_per_t=resolved_price,
                    currency=currency,
                )["result"]
                be_block["available"] = True

        risk_block = (
            self.risk.assess(
                hazard=phase7_hazard,
                exposure=0.5,
                vulnerability=phase7_vulnerability,
            )
            if phase7_hazard is not None and phase7_vulnerability is not None
            else {"available": False, "reason": "sin factores de riesgo Fase 7 aportados"}
        )

        hh_block = None
        if include_nemotron_household:
            dept = (terr.get("administrative", {}).get("department") or {}).get("name")
            try:
                agent = self.population.generate_from_nemotron(
                    1, seed=seed, department=dept
                )["result"]["agents"][0]
            except Exception:
                agent = self.population.generate_from_nemotron(1, seed=seed)["result"]["agents"][0]
            hh_block = self.household_econ.evaluate(
                agent=agent,
                seed=seed,
                production_expense_usd=cost_block.get("totals", {}).get("total") if cost_block.get("available") else None,
                agricultural_revenue_usd=profit_block.get("gross_revenue") if profit_block.get("available") else None,
            )["result"]

        return EG.economic_envelope(
            self.engine,
            result={
                "location": {"lon": lon_v, "lat": lat_v, "territory": terr.get("administrative")},
                "phase6_production_and_suitability": prod,
                "phase7_risk_context": risk_block,
                "phase8_logistics": log_res,
                "phase8_costs": cost_block,
                "phase8_profitability": profit_block,
                "phase8_break_even": be_block,
                "phase6_nemotron_household": hh_block,
            },
            sources=["crop_parameters_catalog", "wfp_food_prices_slv", "osm_markets_slv", "nemotron_personas_sv"],
            assumptions=[
                "cada capa conserva su clase de evidencia y no se rellenan costos o rendimientos faltantes",
                "si se usa precio mayorista WFP como referencia, se declara que no equivale a precio en finca",
            ],
            limitations=[
                "la rentabilidad integrada depende de los costos y rendimientos aportados",
                "el bloque de hogar Nemotron es sintético",
            ],
            evidence_class="model_estimate",
            synthetic=include_nemotron_household,
            query={"lon": lon_v, "lat": lat_v, "crop_id": crop, "system_id": system_id, "area_ha": area_ha},
        )


class AgriculturalEconomicScenarioEngine:
    """Ejecuta los 15 escenarios económicos configurables como simulaciones condicionales."""

    engine = "agricultural_economic_scenario"
    version = ENGINE_VERSION

    def list_scenarios(self) -> dict[str, Any]:
        return {
            "count": len(ECONOMIC_SCENARIOS),
            "scenarios": [{"scenario_id": k, **v} for k, v in ECONOMIC_SCENARIOS.items()],
        }

    def run(
        self,
        *,
        scenario_id: str,
        crop_id: str,
        area_ha: float,
        baseline_yield_t_ha: float,
        baseline_price_per_t: float,
        baseline_costs: Mapping[str, float],
        fixed_costs: float = 0.0,
        baseline_post_harvest_loss: float = 0.0,
        custom_overrides: Mapping[str, float] | None = None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if scenario_id not in ECONOMIC_SCENARIOS:
            raise EG.EconomicError(
                f"escenario desconocido: {scenario_id!r}; use {sorted(ECONOMIC_SCENARIOS)}"
            )
        spec = ECONOMIC_SCENARIOS[scenario_id]
        changes = {**spec["changes"], **(dict(custom_overrides) if custom_overrides else {})}

        prof_engine = AgriculturalProfitabilityEngine()
        base_var = sum(float(v) for v in baseline_costs.values())
        baseline_res = prof_engine.evaluate(
            crop_id=crop_id,
            area_ha=area_ha,
            yield_t_ha=baseline_yield_t_ha,
            price_per_t=baseline_price_per_t,
            variable_cost_total=base_var,
            fixed_cost_total=fixed_costs,
            post_harvest_loss_fraction=baseline_post_harvest_loss,
            currency=currency,
        )["result"]

        # Aplicar multiplicadores declarados por rubro
        adj_costs = dict(baseline_costs)
        key_map = {
            "fertilizer_cost_mult": ("fertilizer",),
            "seed_cost_mult": ("seed",),
            "fuel_cost_mult": ("fuel", "equipment"),
            "transport_mult": ("transport",),
            "irrigation_cost_mult": ("irrigation",),
            "pesticide_cost_mult": ("pesticide",),
        }
        for ch_k, targets in key_map.items():
            if ch_k in changes:
                mult = float(changes[ch_k])
                for t in targets:
                    if t in adj_costs:
                        adj_costs[t] = float(adj_costs[t]) * mult

        if "other_cost_mult" in changes:
            m = float(changes["other_cost_mult"])
            adj_costs = {k: float(v) * m for k, v in adj_costs.items()}
        if "storage_cost_add" in changes:
            adj_costs["storage"] = float(adj_costs.get("storage", 0.0)) + float(changes["storage_cost_add"]) * area_ha

        scen_var = sum(float(v) for v in adj_costs.values())
        scen_fix = fixed_costs + float(changes.get("fixed_cost_add", 0.0)) * area_ha
        scen_yield = baseline_yield_t_ha * float(changes.get("yield_mult", 1.0))
        scen_price = baseline_price_per_t * float(changes.get("price_mult", 1.0))
        scen_loss = min(
            1.0,
            max(
                0.0,
                baseline_post_harvest_loss * float(changes.get("post_harvest_loss_mult", 1.0))
                + float(changes.get("post_harvest_loss_add", 0.0)),
            ),
        )

        scen_res = prof_engine.evaluate(
            crop_id=crop_id,
            area_ha=area_ha,
            yield_t_ha=scen_yield,
            price_per_t=scen_price,
            variable_cost_total=scen_var,
            fixed_cost_total=scen_fix,
            post_harvest_loss_fraction=scen_loss,
            currency=currency,
        )["result"]

        delta_margin = round(scen_res["net_operating_margin"] - baseline_res["net_operating_margin"], 2)
        return EG.economic_envelope(
            self.engine,
            result={
                "scenario_id": scenario_id,
                "label": spec["label"],
                "simulation_date": EG.utcnow()[:10],
                "model_versions": {"economics": ENGINE_VERSION},
                "is_prediction": False,
                "input_data": {
                    "crop_id": crop_id,
                    "area_ha": area_ha,
                    "baseline_yield_t_ha": baseline_yield_t_ha,
                    "baseline_price_per_t": baseline_price_per_t,
                    "baseline_costs": dict(baseline_costs),
                    "fixed_costs": fixed_costs,
                },
                "changed_parameters": changes,
                "baseline": baseline_res,
                "scenario_result": scen_res,
                "delta_vs_baseline": {
                    "revenue_delta": round(scen_res["gross_revenue"] - baseline_res["gross_revenue"], 2),
                    "cost_delta": round(scen_res["total_production_cost"] - baseline_res["total_production_cost"], 2),
                    "net_margin_delta": delta_margin,
                },
                "uncertainty": "sensibilidad determinista condicionada; sin distribución empírica de choques",
            },
            sources=["agrosv_scenario"],
            assumptions=[
                f"escenario condicional '{scenario_id}' con parámetros cambiados declarados",
                "los choques se aplican sobre la línea base aportada por el usuario",
            ],
            limitations=[
                "los escenarios son simulaciones condicionales, nunca pronósticos ni resultados garantizados",
            ],
            evidence_class="synthetic_scenario",
            synthetic=True,
            query={"scenario_id": scenario_id, "crop_id": crop_id, "area_ha": area_ha},
        )


class AgriculturalDecisionSupportEngine:
    """Compara alternativas mostrando compensaciones (trade-offs) sin dictar una única orden."""

    engine = "agricultural_decision_support"
    version = ENGINE_VERSION

    def compare_alternatives(
        self,
        *,
        alternatives: Iterable[Mapping[str, Any]],
        currency: str = "USD",
    ) -> dict[str, Any]:
        alt_list = list(alternatives)
        if len(alt_list) < 2:
            raise EG.EconomicError("se requieren al menos 2 alternativas para analizar compensaciones")

        matrix: list[dict[str, Any]] = []
        for alt in alt_list:
            rev = float(alt.get("gross_revenue", 0.0))
            cost = float(alt.get("total_cost", 0.0))
            margin = rev - cost
            inv = float(alt.get("investment_usd", 0.0))
            matrix.append({
                "alternative_id": alt["alternative_id"],
                "crop_id": alt.get("crop_id"),
                "expected_production_t": alt.get("expected_production_t"),
                "total_cost": round(cost, 2),
                "gross_revenue": round(rev, 2),
                "net_margin": round(margin, 2),
                "water_demand_mm": alt.get("water_demand_mm"),
                "environmental_exposure": alt.get("environmental_exposure"),
                "labor_days": alt.get("labor_days"),
                "investment_usd": round(inv, 2),
                "market_access_score": alt.get("market_access_score"),
                "risk_index": alt.get("risk_index"),
                "uncertainty": alt.get("uncertainty") or "sin cuantificación probabilística",
            })

        best_margin = max(matrix, key=lambda x: x["net_margin"])["alternative_id"]
        lowest_risk = min(
            (m for m in matrix if m["risk_index"] is not None),
            key=lambda x: x["risk_index"],
            default=None,
        )
        lowest_cost = min(matrix, key=lambda x: x["total_cost"])["alternative_id"]

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "count": len(matrix),
                "tradeoff_matrix": matrix,
                "highlights_by_criterion": {
                    "highest_modeled_margin": best_margin,
                    "lowest_total_cost": lowest_cost,
                    "lowest_modeled_risk": lowest_risk["alternative_id"] if lowest_risk else None,
                },
                "single_unsupported_recommendation_issued": False,
            },
            sources=["agrosv_scenario"],
            assumptions=["cada criterio se reporta por separado para evidenciar compensaciones"],
            limitations=["la selección final depende de objetivos, aversión al riesgo y restricciones reales del productor"],
            evidence_class="model_estimate",
            query={"n_alternatives": len(matrix)},
        )


class AgriculturalEconomicAnalysisEngine:
    """Análisis descriptivos y comparativos separando descripción, modelo e inferencia causal."""

    engine = "agricultural_economic_analysis"
    version = ENGINE_VERSION

    def analyze_market_and_production(
        self,
        *,
        crop_ids: Iterable[str] = ("maize", "beans", "rice", "sorghum"),
        market: str = "San Salvador",
    ) -> dict[str, Any]:
        stats_engine = ProductionStatisticsEngine()
        hist_engine = PriceHistoryEngine()
        vc_engine = AgriculturalValueChainEngine()

        crop_summaries: list[dict[str, Any]] = []
        for cid in crop_ids:
            p_stats = stats_engine.summary(crop_id=cid, scale="national")["result"]
            w_hist = hist_engine.analyze(crop_id=cid, market=market, price_type="wholesale")["result"]
            r_hist = hist_engine.analyze(crop_id=cid, market=market, price_type="retail")["result"]
            vc = vc_engine.analyze(crop_id=cid, market=market)["result"]
            crop_summaries.append({
                "crop_id": cid,
                "cap_2025_statistics": p_stats.get("cap_2025_records"),
                "wholesale_price_history": w_hist.get("descriptive_stats") if w_hist.get("available") else None,
                "retail_price_history": r_hist.get("descriptive_stats") if r_hist.get("available") else None,
                "wholesale_to_retail_spread_usd_t": vc.get("wholesale_to_retail_spread_per_t"),
            })

        return EG.economic_envelope(
            self.engine,
            result={
                "market": market,
                "crops_analyzed": crop_summaries,
                "analysis_classification": {
                    "descriptive_statistics": ["cap_2025_statistics", "wholesale_price_history", "retail_price_history"],
                    "derived_metrics": ["wholesale_to_retail_spread_usd_t"],
                    "causal_inference_claimed": False,
                },
            },
            sources=["cap_2025_public_aggregates", "wfp_food_prices_slv"],
            assumptions=["precios WFP normalizados a USD/t; estadísticas CAP 2025 preliminares"],
            limitations=[
                "análisis puramente descriptivo; no establece causalidad entre producción y precios",
            ],
            evidence_class="official_statistic",
            query={"crop_ids": list(crop_ids), "market": market},
        )


class AgriculturalEconomicReportingEngine:
    """Genera informes económicos estructurados con fuentes, fechas, unidades e incertidumbre."""

    engine = "agricultural_economic_reporting"
    version = ENGINE_VERSION

    def generate(
        self,
        *,
        report_scope: str,
        subject_id: str,
        sections: Mapping[str, Any],
        methodology: str,
        uncertainty: str,
        sources: Iterable[str] = ("wfp_food_prices_slv", "cap_2025_public_aggregates"),
        assumptions: Iterable[str] = ("unidades métricas explícitas y trazables",),
        limitations: Iterable[str] = ("informe estructurado sujeto a cobertura de datos declarada",),
    ) -> dict[str, Any]:
        valid_scopes = ("crop", "farm", "municipality", "agricultural_zone", "production_system", "market", "scenario")
        if report_scope not in valid_scopes:
            raise EG.EconomicError(f"report_scope inválido: {report_scope!r}; use {valid_scopes}")

        return EG.economic_envelope(
            self.engine,
            result={
                "report_id": EG.stable_id("RPT", report_scope, subject_id, EG.utcnow()[:10]),
                "report_scope": report_scope,
                "subject_id": subject_id,
                "generated_at_utc": EG.utcnow(),
                "methodology": methodology,
                "uncertainty": uncertainty,
                "sections": dict(sections),
            },
            sources=sources,
            assumptions=assumptions,
            limitations=limitations,
            evidence_class="model_estimate",
            query={"report_scope": report_scope, "subject_id": subject_id},
        )


__all__ = [
    "AgriculturalDecisionSupportEngine",
    "AgriculturalEconomicAnalysisEngine",
    "AgriculturalEconomicIntegrationEngine",
    "AgriculturalEconomicReportingEngine",
    "AgriculturalEconomicScenarioEngine",
    "ECONOMIC_SCENARIOS",
]
