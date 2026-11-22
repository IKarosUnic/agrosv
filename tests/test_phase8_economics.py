"""AGROSV Phase 8 — Pruebas completas de los 7 subsistemas (42 motores), datos reales y API."""
from __future__ import annotations

import time
import pytest
from fastapi.testclient import TestClient

from agrosv.api import app
from agrosv.economics import get_engine, list_engines
from agrosv.economics import governance as EG
from agrosv.economics.costs import (
    AgriculturalCostEngine,
    InputCostEngine,
    IrrigationCostEngine,
    LaborCostEngine,
    MachineryAndEquipmentCostEngine,
    PostHarvestCostEngine,
    ProductionBudgetEngine,
)
from agrosv.economics.household_econ import (
    AgriculturalEconomicBehaviorEngine,
    AgriculturalHouseholdEconomyEngine,
    AgriculturalLivelihoodEngine,
    AgriculturalResourceAllocationEngine,
    AgriculturalTechnologyEconomicsEngine,
)
from agrosv.economics.integration import (
    ECONOMIC_SCENARIOS,
    AgriculturalDecisionSupportEngine,
    AgriculturalEconomicAnalysisEngine,
    AgriculturalEconomicIntegrationEngine,
    AgriculturalEconomicReportingEngine,
    AgriculturalEconomicScenarioEngine,
)
from agrosv.economics.markets import (
    AgriculturalMarketEngine,
    AgriculturalPriceEngine,
    MarketComparisonEngine,
    MarketOpportunityEngine,
    MarketSupplyDemandEngine,
    PriceHistoryEngine,
)
from agrosv.economics.production import (
    AgriculturalProductionEngine,
    AgriculturalProductivityEngine,
    CropYieldAnalysisEngine,
    HarvestEstimationEngine,
    ProductionStatisticsEngine,
    ProductionSystemEngine,
)
from agrosv.economics.profitability import (
    AgriculturalEconomicRiskEngine,
    AgriculturalInvestmentAnalysisEngine,
    AgriculturalProfitabilityEngine,
    BreakEvenAnalysisEngine,
    GrossMarginEngine,
    NetMarginEngine,
    RevenueAnalysisEngine,
)
from agrosv.economics.supply_chain import (
    AgriculturalDistributionEngine,
    AgriculturalLogisticsEngine,
    AgriculturalSupplyChainEngine,
    AgriculturalValueChainEngine,
    MarketAccessEngine,
    StorageAndPostHarvestEngine,
)
from agrosv.social.population import AgriculturalPopulationEngine

COFFEE_POINT = {"lat": 13.85, "lon": -89.45}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# --- Registry & Governance --------------------------------------------------
def test_all_42_engines_registered_and_instantiable():
    names = list_engines()
    assert len(names) == 42
    for name in names:
        eng = get_engine(name)
        assert eng is not None


def test_explicit_unit_conversions_el_salvador():
    assert EG.convert_area(1.0, "mz", "ha") == pytest.approx(0.70)
    assert EG.convert_area(0.70, "ha", "mz") == pytest.approx(1.0)
    assert EG.convert_mass(1.0, "qq", "kg") == pytest.approx(46.0)
    assert EG.convert_mass(1.0, "t", "kg") == pytest.approx(1000.0)
    assert EG.normalize_unit_price(45.0, "45 KG", target_unit="kg") == pytest.approx(1.0)
    assert EG.normalize_unit_price(46.0, "46 KG", target_unit="t") == pytest.approx(1000.0)


# --- Subsystem A: Production ------------------------------------------------
def test_production_statistics_real_cap2025_and_refuses_municipal_inference():
    stats = ProductionStatisticsEngine()
    nat = stats.summary(crop_id="maize", scale="national")
    assert nat["result"]["available"] is True
    rec = nat["result"]["cap_2025_records"][0]
    assert rec["evidence_class"] == "official_statistic"
    assert rec["value"]["harvested_area_mz"] == 293458.0

    mun = stats.summary(crop_id="maize", scale="municipal", municipality="Santa Ana")
    assert mun["result"]["available"] is False
    assert "prohíbe inferirlas" in mun["result"]["reason"]


def test_yield_analysis_separates_classes_and_computes_cv():
    res = CropYieldAnalysisEngine().analyze(
        crop_id="maize",
        observations=[
            {"yield_class": "official_observed", "yield_value": 35.0, "mass_unit": "qq", "area_unit": "mz", "region": "Ahuachapán"},
            {"yield_class": "experimental", "yield_value": 4.5, "mass_unit": "t", "area_unit": "ha", "region": "CENTA"},
        ],
    )["result"]
    assert res["mixed_evidence_classes"] is True
    assert res["national_statistic_claimed"] is False
    assert "official_observed" in res["stats_by_yield_class"]
    assert "experimental" in res["stats_by_yield_class"]


def test_production_systems_productivity_and_harvest():
    sys_prof = ProductionSystemEngine().profile("agroforestry", crop_id="coffee", area_ha=1.4)["result"]
    assert sys_prof["area_mz"] == pytest.approx(2.0)
    assert sys_prof["standardized_farm_assumed"] is False

    prod = AgriculturalProductivityEngine().evaluate(
        crop_id="maize", production_t=4.0, area_ha=2.0, labor_days=80, water_m3=5000
    )["result"]
    assert prod["physical_productivity"]["land_productivity_t_ha"] == 2.0
    assert prod["physical_productivity"]["labor_productivity_kg_per_day"] == 50.0
    assert prod["physical_productivity"]["water_productivity_kg_per_m3"] == 0.8

    harv = HarvestEstimationEngine().estimate(
        crop_id="maize", planting_date="2024-05-15", area_ha=2.0, reference_yield_t_ha=2.5,
        satellite_ndvi_anomaly=-0.05,
    )["result"]
    assert harv["is_observed_harvest_date"] is False
    assert harv["satellite_context"]["direct_production_measurement"] is False
    assert harv["estimated_production_t"] == 5.0

    prod_full = AgriculturalProductionEngine().assess(
        crop_id="coffee", scale="parcel", system_id="agroforestry", area_ha=2.0,
        lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"], planting_date="2024-05-15",
    )["result"]
    assert prod_full["territorial_suitability"]["class"] in {"S1", "S2", "S3", "not_evaluated"}


# --- Subsystem B: Costs -----------------------------------------------------
def test_cost_aggregation_and_budgets_never_mix_types():
    items = [
        {"name": "Semilla", "category": "seed", "nature": "variable", "allocation": "direct", "cost_class": "operating", "amount": 80.0, "per": "ha"},
        {"name": "Fertilizante", "category": "fertilizer", "nature": "variable", "allocation": "direct", "cost_class": "operating", "amount": 220.0, "per": "ha"},
        {"name": "Renta tierra", "category": "land", "nature": "fixed", "allocation": "indirect", "cost_class": "opportunity", "amount": 150.0, "per": "cycle"},
    ]
    agg = AgriculturalCostEngine().aggregate(items=items, area_value=2.0, area_unit="ha", production_value=5.0, production_unit="t")["result"]
    assert agg["totals"]["total"] == 750.0
    assert agg["totals"]["by_nature"]["variable"] == 600.0
    assert agg["totals"]["by_nature"]["fixed"] == 150.0
    assert agg["unit_costs"]["per_ha"] == 375.0
    assert agg["unit_costs"]["per_t"] == 150.0

    bdg = ProductionBudgetEngine().build(
        budget_type="reference", crop_id="maize", system_id="rainfed", area_ha=2.0, cycle="2025-A", items=items, expected_production_t=5.0
    )
    assert bdg["evidence_class"] == "institutional_reference"
    assert bdg["result"]["total_estimated_cost"] == 750.0


def test_input_cost_flags_outdated_and_enforces_pesticide_label():
    with pytest.raises(EG.EconomicError):
        InputCostEngine().evaluate(
            inputs=[{
                "category": "pesticides", "product": "Insecticida X", "price": 15.0,
                "price_type": "retail", "observation_date": "2026-11-01",
            }]
        )
    res = InputCostEngine().evaluate(
        reference_date="2026-11-22",
        inputs=[{
            "category": "fertilizers", "product": "Urea 46%", "price": 32.0, "quantity": 4,
            "price_type": "quoted", "observation_date": "2025-01-01", "source": "fixture",
        }],
    )["result"]
    assert res["total_input_cost"] == 128.0
    assert res["outdated_warnings"]


def test_labor_irrigation_machinery_and_postharvest_costs():
    lab = LaborCostEngine().evaluate(
        entries=[
            {"activity": "planting", "mode": "daily", "quantity": 4, "rate": 12.0, "wage_reference": "fixture 2026"},
            {"activity": "weed_control", "mode": "family_unpaid", "quantity": 5, "rate": 10.0, "wage_reference": "shadow 2026"},
        ]
    )["result"]
    assert lab["paid_labor_cost"] == 48.0
    assert lab["unpaid_family_labor_imputed"] == 50.0

    irr = IrrigationCostEngine().evaluate(
        system_type="drip", area_ha=1.0, water_required_mm=200.0, energy_cost_per_m3=0.05, capex_usd=1000.0, useful_life_cycles=10
    )["result"]
    assert irr["available"] is True
    assert irr["costs"]["depreciation_per_cycle"] == 100.0
    assert irr["water_access_verified"] is False

    mach = MachineryAndEquipmentCostEngine().compare_models(
        hours_per_cycle=10.0, purchase_price=12000.0, salvage_value=2000.0, useful_life_hours=2000.0, rental_rate_per_hour=25.0, fuel_cost_per_hour=6.0
    )["result"]
    assert mach["ownership"]["depreciation_per_hour"] == 5.0
    assert mach["cheaper_option_for_cycle"] == "ownership"

    ph = PostHarvestCostEngine().evaluate(
        harvested_quantity_t=10.0, drying_per_t=12.0, post_harvest_loss_fraction=0.05, loss_fraction_source="user_measurement"
    )["result"]
    assert ph["saleable_quantity_t"] == 9.5
    assert ph["separated_from_field_production_loss"] is True


# --- Subsystem C: Real Markets & Prices -------------------------------------
def test_real_wfp_markets_prices_and_history():
    mkts = AgriculturalMarketEngine().catalog(limit=200)["result"]
    assert mkts["total_catalog_size"] >= 100  # 71 WFP + 39 OSM

    prices = AgriculturalPriceEngine().query(crop_id="maize", market="San Salvador", price_type="wholesale", target_unit="t", limit=10)["result"]
    assert prices["available"] is True
    assert prices["count"] == 10
    assert prices["latest_observation_date"] >= "2026-01-01"

    hist = PriceHistoryEngine().analyze(crop_id="beans", market="San Salvador", price_type="wholesale")["result"]
    assert hist["available"] is True
    assert hist["long_term_forecast_provided"] is False
    assert len(hist["seasonal_monthly_index"]) == 12

    cmp_res = MarketComparisonEngine().compare(crop_id="maize", quantity_t=5.0, origin_lon=COFFEE_POINT["lon"], origin_lat=COFFEE_POINT["lat"])["result"]
    assert cmp_res["count"] >= 5
    assert cmp_res["alternatives"][0]["net_producer_price_per_t"] <= cmp_res["alternatives"][0]["gross_price_per_t"]

    opp = MarketOpportunityEngine().identify(crop_id="maize", quantity_t=5.0, harvest_month=11)["result"]
    assert opp["guaranteed_buyer"] is False

    sd = MarketSupplyDemandEngine().balance(crop_id="maize", reference_year="2024-2025")["result"]
    assert sd["production_t"] == 500020.0
    assert "imports_t" in sd["missing_components"]


# --- Subsystem D: Profitability & Investment --------------------------------
def test_profitability_margins_breakeven_investment_and_risk():
    prof = AgriculturalProfitabilityEngine().evaluate(
        crop_id="maize", area_ha=2.0, yield_t_ha=3.0, price_per_t=400.0, variable_cost_total=1200.0, fixed_cost_total=300.0
    )["result"]
    assert prof["gross_revenue"] == 2400.0
    assert prof["gross_margin"] == 1200.0
    assert prof["net_operating_margin"] == 900.0

    gm = GrossMarginEngine().evaluate(gross_revenue=2400.0, variable_costs={"seed": 200, "fert": 1000}, area_ha=2.0)["result"]
    assert gm["is_net_profit"] is False

    nm = NetMarginEngine().evaluate(
        gross_revenue=2400.0, variable_costs=1200.0, fixed_cash_costs=200.0, depreciation=100.0, unpaid_family_labor=300.0, cost_model_complete=False
    )["result"]
    assert nm["cash_operating_result"] == 1000.0
    assert nm["accounting_net_result"] == 900.0
    assert nm["economic_result_with_family_labor"] == 600.0
    assert nm["completeness_warning"] is not None

    be = BreakEvenAnalysisEngine().evaluate(
        fixed_costs=300.0, variable_cost_per_ha=600.0, area_ha=2.0, expected_yield_t_ha=3.0, price_per_t=400.0
    )["result"]
    assert be["break_even_price_per_t"] == pytest.approx(250.0)
    assert be["break_even_yield_t_ha"] == pytest.approx(1.875)

    inv = AgriculturalInvestmentAnalysisEngine().evaluate(
        investment_type="drip_irrigation", initial_investment=1000.0, annual_cash_flows=[400.0, 400.0, 400.0, 400.0],
        discount_rate=0.10, discount_rate_justification="tasa real de referencia de escenario",
    )["result"]
    assert inv["payback_years"] == pytest.approx(2.5)
    assert inv["npv"] > 0
    assert inv["irr"] > 0.10

    risk = AgriculturalEconomicRiskEngine().assess(
        baseline_revenue=2400.0, baseline_cost=1500.0, phase7_hazard=0.6, phase7_vulnerability=0.5, yield_shock_fraction=0.25
    )["result"]
    assert risk["stressed_margin"] == 300.0
    assert risk["is_actual_financial_loss"] is False


# --- Subsystem E: Supply Chain & Logistics ----------------------------------
def test_supply_chain_logistics_access_storage_distribution_value_chain():
    chain = AgriculturalSupplyChainEngine().map_chain(crop_id="coffee")["result"]
    assert chain["hypothetical_links_count"] == 5

    log = AgriculturalLogisticsEngine().evaluate(lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"], crop_id="coffee", quantity_t=2.0)["result"]
    assert log["nearest_osm_road"]["available"] is True
    assert log["nearest_markets"]

    acc = MarketAccessEngine().evaluate(lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"], crop_id="maize", quantity_t=2.0, expected_gross_value_usd=800.0)["result"]
    assert acc["geographic_proximity_index"] > 0

    stor = StorageAndPostHarvestEngine().assess(crop_id="maize", quantity_t=5.0, storage_days=60, observed_moisture_pct=15.0)["result"]
    assert stor["moisture_status"] == "elevated"

    dist = AgriculturalDistributionEngine().plan(origin_lon=COFFEE_POINT["lon"], origin_lat=COFFEE_POINT["lat"], quantity_t=3.0)["result"]
    assert dist["routing_separated_from_cost_assumptions"] is True

    vc = AgriculturalValueChainEngine().analyze(crop_id="maize", market="San Salvador")["result"]
    assert vc["wfp_data_used"] is True
    assert vc["market_power_inferred"] is False


# --- Subsystem F: Household Economics (Nemotron Reused) ---------------------
def test_household_economics_reuses_nemotron_and_stays_synthetic():
    agent = AgriculturalPopulationEngine().generate_from_nemotron(1, seed=5)["result"]["agents"][0]
    econ = AgriculturalHouseholdEconomyEngine().evaluate(
        agent=agent, seed=5, production_expense_usd=400.0, agricultural_revenue_usd=950.0, non_agricultural_income_usd=200.0, consumption_usd=600.0
    )
    assert econ["synthetic"] is True
    assert econ["result"]["economy"]["nemotron_backed"] is True
    assert econ["result"]["economy"]["net_agricultural_cashflow_usd"] == 550.0

    alloc = AgriculturalResourceAllocationEngine().allocate(
        agent=agent,
        activities=[
            {"name": "maize", "expected_margin_per_ha": 400.0, "cost_per_ha": 250.0, "labor_days_per_ha": 40, "is_staple_food": True},
            {"name": "tomato", "expected_margin_per_ha": 1200.0, "cost_per_ha": 900.0, "labor_days_per_ha": 90, "requires_irrigation": True},
        ],
    )["result"]
    assert alloc["profit_only_assumed"] is False

    liv = AgriculturalLivelihoodEngine().analyze(agent=agent, crop_income_usd=500.0, non_ag_wage_income_usd=300.0)["result"]
    assert liv["agricultural_share_of_total"] == pytest.approx(500.0 / 800.0)

    tech = AgriculturalTechnologyEconomicsEngine().evaluate(
        agent=agent, technology_id="improved_seed", capex_usd=80.0, expected_annual_net_benefit_usd=180.0
    )["result"]
    assert tech["automatic_profit_improvement_assumed"] is False

    beh = AgriculturalEconomicBehaviorEngine().decide(
        agent=agent,
        decision_domain="crop_selection",
        options=[
            {"option_id": "maize", "expected_return": 300, "risk": 0.2, "capital_required": 50},
            {"option_id": "beans", "expected_return": 450, "risk": 0.5, "capital_required": 50},
        ],
    )["result"]
    assert beh["represents_observed_farmer_behavior"] is False


# --- Subsystem G: Integration, 15 Scenarios, Trade-offs, Reporting, API -----
def test_integration_all_15_scenarios_decision_support_and_reporting():
    t0 = time.perf_counter()
    integ = AgriculturalEconomicIntegrationEngine().evaluate(
        lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"], crop_id="maize", area_ha=2.0,
        expected_yield_t_ha=2.8, use_wfp_reference_price=True,
        cost_items=[{"name": "Insumos", "category": "fertilizer", "amount": 300.0, "per": "ha"}],
        include_nemotron_household=True,
    )["result"]
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 5000
    assert integ["phase8_profitability"]["available"] is True
    assert integ["phase6_nemotron_household"]["economy"]["nemotron_backed"] is True

    scen_engine = AgriculturalEconomicScenarioEngine()
    assert len(ECONOMIC_SCENARIOS) == 15
    for sid in ECONOMIC_SCENARIOS:
        res = scen_engine.run(
            scenario_id=sid, crop_id="maize", area_ha=1.0, baseline_yield_t_ha=2.5,
            baseline_price_per_t=420.0, baseline_costs={"seed": 60.0, "fertilizer": 180.0, "transport": 40.0},
        )
        assert res["result"]["is_prediction"] is False
        assert "delta_vs_baseline" in res["result"]

    ds = AgriculturalDecisionSupportEngine().compare_alternatives(
        alternatives=[
            {"alternative_id": "maize_rainfed", "gross_revenue": 1000, "total_cost": 600, "risk_index": 0.3},
            {"alternative_id": "tomato_drip", "gross_revenue": 3500, "total_cost": 2200, "risk_index": 0.7},
        ]
    )["result"]
    assert ds["single_unsupported_recommendation_issued"] is False

    an = AgriculturalEconomicAnalysisEngine().analyze_market_and_production()["result"]
    assert an["analysis_classification"]["causal_inference_claimed"] is False

    rpt = AgriculturalEconomicReportingEngine().generate(
        report_scope="crop", subject_id="maize", sections={"summary": "ok"},
        methodology="determinista", uncertainty="sensibilidad de escenario",
    )["result"]
    assert rpt["report_id"].startswith("RPT-")


def test_phase8_api_endpoints_and_backward_compatibility(client):
    assert client.get("/api/economics/meta").json()["engines_count"] == 42
    assert client.get("/api/economics/production/statistics?crop_id=maize&scale=national").status_code == 200
    assert client.get("/api/economics/markets?limit=10").json()["result"]["count"] == 10
    assert client.get("/api/economics/prices?crop_id=maize&limit=5").json()["result"]["available"] is True
    assert client.get("/api/economics/prices/history?crop_id=maize").json()["result"]["available"] is True
    assert client.get("/api/economics/scenarios").json()["count"] == 15
    assert client.get("/api/economics/analysis").status_code == 200
    assert client.post("/api/economics/profitability", json={
        "crop_id": "maize", "area_ha": 1.0, "yield_t_ha": 3.0, "price_per_t": 400.0, "variable_cost_total": 600.0,
    }).status_code == 200
    # Compatibilidad con fases anteriores
    assert client.get("/api/agriculture/meta").status_code == 200
    assert client.get("/api/social/meta").status_code == 200
