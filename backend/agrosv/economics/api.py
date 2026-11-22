"""AGROSV Phase 8 — API de Economía Agrícola, Producción, Mercados y Cadena de Valor (`/api/economics`)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from . import governance as EG
from . import list_engines
from .costs import (
    AgriculturalCostEngine,
    InputCostEngine,
    IrrigationCostEngine,
    LaborCostEngine,
    MachineryAndEquipmentCostEngine,
    PostHarvestCostEngine,
    ProductionBudgetEngine,
)
from .household_econ import (
    AgriculturalEconomicBehaviorEngine,
    AgriculturalHouseholdEconomyEngine,
    AgriculturalLivelihoodEngine,
    AgriculturalResourceAllocationEngine,
    AgriculturalTechnologyEconomicsEngine,
)
from .integration import (
    AgriculturalDecisionSupportEngine,
    AgriculturalEconomicAnalysisEngine,
    AgriculturalEconomicIntegrationEngine,
    AgriculturalEconomicReportingEngine,
    AgriculturalEconomicScenarioEngine,
)
from .markets import (
    AgriculturalMarketEngine,
    AgriculturalPriceEngine,
    MarketComparisonEngine,
    MarketOpportunityEngine,
    MarketSupplyDemandEngine,
    PriceHistoryEngine,
)
from .production import (
    AgriculturalProductionEngine,
    AgriculturalProductivityEngine,
    CropYieldAnalysisEngine,
    HarvestEstimationEngine,
    ProductionStatisticsEngine,
    ProductionSystemEngine,
)
from .profitability import (
    AgriculturalEconomicRiskEngine,
    AgriculturalInvestmentAnalysisEngine,
    AgriculturalProfitabilityEngine,
    BreakEvenAnalysisEngine,
    GrossMarginEngine,
    NetMarginEngine,
    RevenueAnalysisEngine,
)
from .supply_chain import (
    AgriculturalDistributionEngine,
    AgriculturalLogisticsEngine,
    AgriculturalSupplyChainEngine,
    AgriculturalValueChainEngine,
    MarketAccessEngine,
    StorageAndPostHarvestEngine,
)

router = APIRouter(prefix="/api/economics", tags=["economics"])
SERVICE_VERSION = EG.ENGINE_VERSION

_prod = AgriculturalProductionEngine()
_yield = CropYieldAnalysisEngine()
_systems = ProductionSystemEngine()
_productivity = AgriculturalProductivityEngine()
_harvest = HarvestEstimationEngine()
_stats = ProductionStatisticsEngine()

_cost = AgriculturalCostEngine()
_input_cost = InputCostEngine()
_labor_cost = LaborCostEngine()
_irrigation_cost = IrrigationCostEngine()
_machinery_cost = MachineryAndEquipmentCostEngine()
_postharvest_cost = PostHarvestCostEngine()
_budget = ProductionBudgetEngine()

_market = AgriculturalMarketEngine()
_price = AgriculturalPriceEngine()
_price_hist = PriceHistoryEngine()
_supply_demand = MarketSupplyDemandEngine()
_market_cmp = MarketComparisonEngine()
_market_opp = MarketOpportunityEngine()

_prof = AgriculturalProfitabilityEngine()
_rev = RevenueAnalysisEngine()
_be = BreakEvenAnalysisEngine()
_gm = GrossMarginEngine()
_nm = NetMarginEngine()
_inv = AgriculturalInvestmentAnalysisEngine()
_econ_risk = AgriculturalEconomicRiskEngine()

_chain = AgriculturalSupplyChainEngine()
_logistics = AgriculturalLogisticsEngine()
_access = MarketAccessEngine()
_storage = StorageAndPostHarvestEngine()
_dist = AgriculturalDistributionEngine()
_vc = AgriculturalValueChainEngine()

_hh_econ = AgriculturalHouseholdEconomyEngine()
_res_alloc = AgriculturalResourceAllocationEngine()
_livelihood = AgriculturalLivelihoodEngine()
_tech_econ = AgriculturalTechnologyEconomicsEngine()
_econ_beh = AgriculturalEconomicBehaviorEngine()

_econ_int = AgriculturalEconomicIntegrationEngine()
_econ_scen = AgriculturalEconomicScenarioEngine()
_decision_sup = AgriculturalDecisionSupportEngine()
_econ_analysis = AgriculturalEconomicAnalysisEngine()
_reporting = AgriculturalEconomicReportingEngine()


def _headers(engine: str) -> dict[str, str]:
    return {"X-AGROSV-Engine": engine, "X-AGROSV-Version": SERVICE_VERSION}


def _err(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(404, str(exc).strip("'\""))
    if isinstance(exc, (EG.EconomicError, ValueError)):
        return HTTPException(400, str(exc))
    return HTTPException(500, f"{type(exc).__name__}: {exc}")


# --- Meta y Gobernanza ------------------------------------------------------
@router.get("/meta", summary="Motores y fuentes de Fase 8")
def meta() -> JSONResponse:
    return JSONResponse(
        content={
            "service_version": SERVICE_VERSION,
            "engines_count": len(list_engines()),
            "engines": list_engines(),
            "sources": EG.SOURCE_REGISTRY,
            "llm_used": False,
        },
        headers=_headers("economics_meta"),
    )


# --- Subsistema A: Producción -----------------------------------------------
@router.post("/production", summary="Análisis de producción multi-escala")
def production_assess(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _prod.assess(
            crop_id=payload["crop_id"],
            scale=payload.get("scale", "parcel"),
            system_id=payload.get("system_id", "rainfed"),
            area_ha=float(payload.get("area_ha", 1.0)),
            lon=payload.get("lon"),
            lat=payload.get("lat"),
            department=payload.get("department"),
            planting_date=payload.get("planting_date"),
            reference_yield_t_ha=payload.get("reference_yield_t_ha"),
            management=payload.get("management"),
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_prod.engine))


@router.post("/production/yield", summary="Análisis de rendimiento y variabilidad")
def yield_analyze(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _yield.analyze(
            crop_id=payload["crop_id"],
            observations=payload.get("observations") or [],
            target_unit=payload.get("target_unit", "t/ha"),
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_yield.engine))


@router.get("/production/systems", summary="Catálogo de sistemas productivos")
def production_systems() -> JSONResponse:
    return JSONResponse(content=_systems.catalog(), headers=_headers(_systems.engine))


@router.post("/production/productivity", summary="Indicadores físicos y económicos de productividad")
def productivity_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _productivity.evaluate(
            crop_id=payload["crop_id"],
            production_t=float(payload["production_t"]),
            area_ha=float(payload["area_ha"]),
            labor_days=payload.get("labor_days"),
            water_m3=payload.get("water_m3"),
            input_cost_usd=payload.get("input_cost_usd"),
            energy_mj=payload.get("energy_mj"),
            gross_revenue_usd=payload.get("gross_revenue_usd"),
            total_cost_usd=payload.get("total_cost_usd"),
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_productivity.engine))


@router.post("/production/harvest", summary="Estimación de ventana de cosecha y producción")
def harvest_estimate(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _harvest.estimate(
            crop_id=payload["crop_id"],
            planting_date=payload["planting_date"],
            area_ha=float(payload.get("area_ha", 1.0)),
            variety=payload.get("variety"),
            reference_yield_t_ha=payload.get("reference_yield_t_ha"),
            awc_mm_per_m=payload.get("awc_mm_per_m"),
            root_depth_cm=payload.get("root_depth_cm"),
            allow_reference_kc=bool(payload.get("allow_reference_kc", False)),
            satellite_ndvi_anomaly=payload.get("satellite_ndvi_anomaly"),
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_harvest.engine))


@router.get("/production/statistics", summary="Estadísticas oficiales verificadas (CAP 2025 / WDI)")
def production_statistics(
    crop_id: str | None = Query(None),
    scale: str = Query("national"),
    department: str | None = Query(None),
    municipality: str | None = Query(None),
) -> JSONResponse:
    try:
        res = _stats.summary(
            crop_id=crop_id, scale=scale, department=department, municipality=municipality
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_stats.engine))


# --- Subsistema B: Costos ---------------------------------------------------
@router.post("/costs/aggregate", summary="Agregación configurable de costos")
def costs_aggregate(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _cost.aggregate(
            items=payload.get("items") or [],
            area_value=float(payload.get("area_value", 1.0)),
            area_unit=payload.get("area_unit", "ha"),
            production_value=payload.get("production_value"),
            production_unit=payload.get("production_unit", "t"),
            currency=payload.get("currency", "USD"),
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_cost.engine))


@router.post("/costs/inputs", summary="Costos de insumos con trazabilidad y vigencia")
def costs_inputs(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _input_cost.evaluate(
            inputs=payload.get("inputs") or [],
            reference_date=payload.get("reference_date"),
            stale_after_days=int(payload.get("stale_after_days", 90)),
            currency=payload.get("currency", "USD"),
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_input_cost.engine))


@router.post("/costs/labor", summary="Costos de mano de obra (pagada y familiar)")
def costs_labor(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _labor_cost.evaluate(
            entries=payload.get("entries") or [],
            family_labor_valuation_method=payload.get("family_labor_valuation_method", "opportunity_shadow_wage"),
            currency=payload.get("currency", "USD"),
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_labor_cost.engine))


@router.post("/costs/irrigation", summary="Costos de riego e integración hídrica")
def costs_irrigation(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _irrigation_cost.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_irrigation_cost.engine))


@router.post("/costs/machinery", summary="Costos de maquinaria (propia, alquiler, compartida)")
def costs_machinery(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _machinery_cost.compare_models(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_machinery_cost.engine))


@router.post("/costs/post-harvest", summary="Costos y pérdidas poscosecha")
def costs_postharvest(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _postharvest_cost.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_postharvest_cost.engine))


@router.post("/budgets", summary="Presupuestos de producción (observado/referencia/escenario)")
def production_budget(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _budget.build(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_budget.engine))


# --- Subsistema C: Mercados y Precios ---------------------------------------
@router.get("/markets", summary="Catálogo de mercados verificados (WFP + OSM)")
def markets_catalog(
    department: str | None = Query(None),
    source: str | None = Query(None),
    named_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
) -> JSONResponse:
    return JSONResponse(
        content=_market.catalog(department=department, source=source, named_only=named_only, limit=limit),
        headers=_headers(_market.engine),
    )


@router.get("/prices", summary="Precios agrícolas normalizados (WFP El Salvador)")
def prices_query(
    crop_id: str | None = Query(None),
    commodity: str | None = Query(None),
    market: str | None = Query(None),
    price_type: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    target_unit: str = Query("t"),
    limit: int = Query(50, ge=1, le=500),
) -> JSONResponse:
    try:
        res = _price.query(
            crop_id=crop_id,
            commodity=commodity,
            market=market,
            price_type=price_type,
            start_date=start_date,
            end_date=end_date,
            target_unit=target_unit,
            limit=limit,
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_price.engine))


@router.get("/prices/history", summary="Análisis histórico y estacional de precios")
def prices_history(
    crop_id: str | None = Query(None),
    commodity: str | None = Query(None),
    market: str = Query("San Salvador"),
    price_type: str = Query("wholesale"),
    target_unit: str = Query("t"),
) -> JSONResponse:
    try:
        res = _price_hist.analyze(
            crop_id=crop_id, commodity=commodity, market=market, price_type=price_type, target_unit=target_unit
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_price_hist.engine))


@router.post("/markets/supply-demand", summary="Balance de oferta y disponibilidad aparente")
def markets_supply_demand(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _supply_demand.balance(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_supply_demand.engine))


@router.post("/markets/compare", summary="Comparación de mercados (precio bruto vs neto)")
def markets_compare(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _market_cmp.compare(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_market_cmp.engine))


@router.post("/markets/opportunities", summary="Oportunidades potenciales de comercialización")
def markets_opportunities(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _market_opp.identify(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_market_opp.engine))


# --- Subsistema D: Rentabilidad y Riesgo ------------------------------------
@router.post("/profitability", summary="Rentabilidad agrícola integrada")
def profitability_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _prof.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_prof.engine))


@router.post("/revenue", summary="Análisis de ingresos por canal y poscosecha")
def revenue_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _rev.analyze(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_rev.engine))


@router.post("/break-even", summary="Punto de equilibrio (precio, rendimiento, volumen, área)")
def breakeven_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _be.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_be.engine))


@router.post("/gross-margin", summary="Margen bruto")
def gross_margin_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _gm.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_gm.engine))


@router.post("/net-margin", summary="Margen neto (caja, contable, económico)")
def net_margin_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _nm.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_nm.engine))


@router.post("/investment", summary="Evaluación financiera de inversión (Payback, VAN, TIR)")
def investment_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _inv.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_inv.engine))


@router.post("/risk", summary="Exposición al riesgo económico (integrado con Fase 7)")
def economic_risk_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _econ_risk.assess(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_econ_risk.engine))


# --- Subsistema E: Cadena y Logística ---------------------------------------
@router.post("/supply-chain", summary="Mapa de cadena de suministro")
def supply_chain_map(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _chain.map_chain(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_chain.engine))


@router.post("/logistics", summary="Logística, distancia vial OSM y mercados cercanos")
def logistics_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _logistics.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_logistics.engine))


@router.post("/market-access", summary="Evaluación de acceso práctico al mercado")
def market_access_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _access.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_access.engine))


@router.post("/storage", summary="Almacenamiento y parámetros poscosecha")
def storage_eval(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _storage.assess(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_storage.engine))


@router.post("/distribution", summary="Rutas y escenarios de distribución")
def distribution_plan(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _dist.plan(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_dist.engine))


@router.post("/value-chain", summary="Análisis de creación y participación de valor")
def value_chain_analyze(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _vc.analyze(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_vc.engine))


# --- Subsistema F: Economía de Hogares (reutiliza Nemotron Fase 6) ----------
@router.post("/household", summary="Economía de hogar agrícola sintético (Nemotron Fase 6)")
def household_economy(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        res = _hh_econ.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_hh_econ.engine))


@router.post("/household/allocation", summary="Asignación de recursos del hogar bajo restricciones")
def resource_allocation(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        agent = payload.get("agent")
        if agent is None:
            from ..social.population import AgriculturalPopulationEngine

            pop = AgriculturalPopulationEngine()
            agent = (
                pop.generate_from_nemotron(1, seed=int(payload.get("seed", 42)))["result"]["agents"][0]
                if payload.get("use_nemotron", True)
                else pop.generate(1, seed=int(payload.get("seed", 42)))["result"]["agents"][0]
            )
        res = _res_alloc.allocate(
            agent=agent,
            activities=payload.get("activities") or [],
            objective=payload.get("objective", "balanced_food_security_and_margin"),
            seed=int(payload.get("seed", 42)),
        )
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_res_alloc.engine))


@router.post("/household/livelihoods", summary="Estrategias de medios de vida del hogar")
def household_livelihoods(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        agent = payload.pop("agent", None)
        if agent is None:
            from ..social.population import AgriculturalPopulationEngine

            agent = AgriculturalPopulationEngine().generate_from_nemotron(
                1, seed=int(payload.get("seed", 42))
            )["result"]["agents"][0]
        res = _livelihood.analyze(agent=agent, **payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_livelihood.engine))


@router.post("/household/technology", summary="Economía de adopción tecnológica (reutiliza Fase 6)")
def technology_economics(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        agent = payload.pop("agent", None)
        if agent is None:
            from ..social.population import AgriculturalPopulationEngine

            agent = AgriculturalPopulationEngine().generate_from_nemotron(
                1, seed=int(payload.pop("seed", 42))
            )["result"]["agents"][0]
        res = _tech_econ.evaluate(agent=agent, **payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_tech_econ.engine))


@router.post("/household/behavior", summary="Comportamiento económico sintético (reutiliza Fase 6)")
def economic_behavior(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        agent = payload.pop("agent", None)
        if agent is None:
            from ..social.population import AgriculturalPopulationEngine

            agent = AgriculturalPopulationEngine().generate_from_nemotron(
                1, seed=int(payload.pop("seed", 42))
            )["result"]["agents"][0]
        res = _econ_beh.decide(agent=agent, **payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_econ_beh.engine))


# --- Subsistema G: Inteligencia Económica Integrada -------------------------
@router.post("/integrate", summary="Integración Fases 5+6+7+8")
def economic_integrate(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _econ_int.evaluate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_econ_int.engine))


@router.get("/scenarios", summary="Listado de los 15 escenarios económicos configurables")
def scenarios_list() -> JSONResponse:
    return JSONResponse(content=_econ_scen.list_scenarios(), headers=_headers(_econ_scen.engine))


@router.post("/scenarios/run", summary="Ejecutar simulación condicional de escenario económico")
def scenarios_run(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _econ_scen.run(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_econ_scen.engine))


@router.post("/decision-support", summary="Matriz de compensaciones (trade-offs) entre alternativas")
def decision_support(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _decision_sup.compare_alternatives(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_decision_sup.engine))


@router.get("/analysis", summary="Análisis descriptivo nacional de mercados y producción")
def economic_analysis(market: str = Query("San Salvador")) -> JSONResponse:
    try:
        res = _econ_analysis.analyze_market_and_production(market=market)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_econ_analysis.engine))


@router.post("/report", summary="Generar informe económico estructurado con procedencia")
def economic_report(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        res = _reporting.generate(**payload)
    except Exception as exc:
        raise _err(exc) from None
    return JSONResponse(content=res, headers=_headers(_reporting.engine))
