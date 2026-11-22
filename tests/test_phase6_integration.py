"""Pruebas de Fase 6 — Subsistema C, API y contratos integrados."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agrosv.api import app
from agrosv.social.population import AgriculturalPopulationEngine
from agrosv.socio.analysis import SocioAgriculturalAnalysisEngine
from agrosv.socio.decision import AgriculturalDecisionEngine
from agrosv.socio.integration import (IntegrationError,
                                      SocioAgriculturalIntegrationEngine)
from agrosv.socio.scenario import AgriculturalScenarioEngine, ScenarioError

COFFEE_POINT = {"lat": 13.85, "lon": -89.45}
NODATA_POINT = {"lat": 13.69, "lon": -89.19}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _agents(size: int = 12, seed: int = 5):
    return AgriculturalPopulationEngine().generate(size, seed=seed)["result"]["agents"]


# --- integración ------------------------------------------------------------
def test_profile_without_soil_inputs_declares_water_not_evaluated():
    payload = SocioAgriculturalIntegrationEngine().profile(
        lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"], crop_id="coffee",
        planting_date="2024-05-15")
    water = payload["result"]["scientific"]["water_balance"]
    assert water["available"] is False
    assert "awc_mm_per_m" in water["required_inputs"]
    assert payload["result"]["llm_used"] is False


def test_profile_with_soil_inputs_runs_balance():
    payload = SocioAgriculturalIntegrationEngine().profile(
        lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"], crop_id="coffee",
        planting_date="2024-05-15", awc_mm_per_m=140, root_depth_cm=60,
        allow_reference_kc=True)
    water = payload["result"]["scientific"]["water_balance"]
    assert water["result"]["days"] > 0
    assert water["result"]["cycle_days_requested"] > water["result"]["days"]
    assert water["result"]["series_truncated"] is True


def test_profile_requires_planting_date_for_water():
    with pytest.raises(IntegrationError):
        SocioAgriculturalIntegrationEngine().profile(
            lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"], crop_id="coffee",
            awc_mm_per_m=140, root_depth_cm=60, allow_reference_kc=True)


def test_profile_with_human_keeps_blocks_separate():
    agent = _agents(1, seed=9)[0]
    payload = SocioAgriculturalIntegrationEngine().profile(
        lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"], crop_id="coffee",
        agent=agent, seed=9)
    assert payload["result"]["human"]["synthetic"] is True
    assert payload["result"]["scientific"]["suitability"]["result"]["class"]
    assert "scientific" in payload["result"]
    assert payload["result"]["component_classes"]["persona"] == "synthetic"


# --- decisión ---------------------------------------------------------------
def test_decision_refuses_when_no_crop_is_evaluable():
    agent = _agents(1)[0]
    agent["state"]["payload"]["crops"] = ["maize"]
    payload = AgriculturalDecisionEngine().decide(
        agent=agent, lon=NODATA_POINT["lon"], lat=NODATA_POINT["lat"])
    assert payload["result"]["decision_status"] == "no_evaluable_options"
    assert payload["result"]["llm_used"] is False


def test_decision_is_deterministic_and_reports_constraints():
    agent = _agents(1)[0]
    agent["state"]["payload"]["crops"] = ["coffee"]
    agent["state"]["payload"]["capital_usd"] = 100000
    engine = AgriculturalDecisionEngine()
    first = engine.decide(agent=agent, lon=COFFEE_POINT["lon"],
                          lat=COFFEE_POINT["lat"])
    second = engine.decide(agent=agent, lon=COFFEE_POINT["lon"],
                           lat=COFFEE_POINT["lat"])
    assert first["result"]["decision"] == second["result"]["decision"]
    assert "weights" in first["result"]
    assert first["result"]["agronomic_constraints_respected"] is True


def test_decision_honours_capital_constraint():
    agent = _agents(1)[0]
    agent["state"]["payload"]["crops"] = ["coffee"]
    agent["state"]["payload"]["capital_usd"] = 10
    payload = AgriculturalDecisionEngine().decide(
        agent=agent, lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"],
        options=[{"option_id": "crop:coffee", "expected_return": 1.0,
                  "risk": 0.2, "capital_required": 5000}])
    assert payload["result"]["decision"] is None
    assert payload["result"]["excluded"]


# --- escenarios -------------------------------------------------------------
def test_unknown_scenario_raises():
    with pytest.raises(ScenarioError):
        AgriculturalScenarioEngine().run(
            "Z_alien", lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"])


def test_scenario_rejects_large_size():
    with pytest.raises(ScenarioError):
        AgriculturalScenarioEngine().run(
            "A_drought", lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"],
            size=501)


def test_scenario_drought_reports_metrics_and_layers():
    payload = AgriculturalScenarioEngine().run(
        "A_drought", lon=COFFEE_POINT["lon"], lat=COFFEE_POINT["lat"],
        size=8, seed=2)
    metrics = payload["result"]["metrics"]
    assert metrics["n_agents"] == 8
    assert metrics["mean_impact_index"] is not None
    assert payload["result"]["is_prediction"] is False
    assert payload["layer_check"]["valid"] is True


def test_scenario_economy_needs_sheets_and_uses_them_when_given():
    from agrosv.agriculture.catalog import CROPS

    costs = {item: {"amount": 100.0, "unit": "USD/ha", "currency": "USD",
                    "date": "2026-01-01", "source": "TEST_FIXTURE"}
             for item in ("seed", "fertilizer", "pesticide", "labor",
                          "irrigation", "equipment", "transport")}
    prices = {crop: {"price_per_t": 200.0, "currency": "USD",
                     "unit": "USD/t", "date": "2026-01-01",
                     "market": "fixture", "source": "TEST_FIXTURE"}
              for crop in CROPS}
    payload = AgriculturalScenarioEngine().run(
        "C_production_costs", lon=COFFEE_POINT["lon"],
        lat=COFFEE_POINT["lat"], size=6, seed=2,
        costs=costs, prices=prices, yield_t_ha=3.0)
    economic = payload["result"]["metrics"]["economic"]
    assert economic["n"] > 0
    assert "mean_margin" in economic


# --- análisis ---------------------------------------------------------------
def test_analysis_compare_and_findings_are_simulation_only():
    engine = AgriculturalScenarioEngine()
    run_a = engine.run("A_drought", lon=COFFEE_POINT["lon"],
                       lat=COFFEE_POINT["lat"], size=6, seed=3)
    run_b = engine.run("G_support_program", lon=COFFEE_POINT["lon"],
                       lat=COFFEE_POINT["lat"], size=6, seed=3)
    analysis = SocioAgriculturalAnalysisEngine()
    comparison = analysis.compare([run_a, run_b])["result"]
    assert comparison["baseline"] == "A_drought"
    assert len(comparison["rows"]) == 2
    findings = analysis.findings([run_a, run_b])["findings"]
    assert findings
    assert all(f["evidence_class"] == "simulation" for f in findings)
    assert all(f["empirical_conclusion"] is False for f in findings)


def test_analysis_constraints_describe_synthetic_sample():
    population = AgriculturalPopulationEngine().generate(10, seed=4)
    payload = SocioAgriculturalAnalysisEngine().constraints(population)["result"]
    assert payload["n"] == 10
    assert 0 <= payload["no_irrigation"] <= 1
    assert "no son prevalencias" in " ".join(
        SocioAgriculturalAnalysisEngine().constraints(population)["limitations"])


# --- API --------------------------------------------------------------------
def test_api_agriculture_catalog_and_meta(client):
    assert client.get("/api/agriculture/meta").status_code == 200
    crops = client.get("/api/agriculture/crops").json()
    assert crops["count"] == 22
    assert client.get("/api/agriculture/crops/maize").status_code == 200
    assert client.get("/api/agriculture/crops/quinoa").status_code == 404


def test_api_agriculture_rejects_bad_coordinates(client):
    response = client.get(
        "/api/agriculture/suitability?crop_id=maize&lat=0&lon=0")
    assert response.status_code == 400


def test_api_agriculture_suitability_and_calendar(client):
    response = client.get(
        "/api/agriculture/suitability?crop_id=coffee&lat=13.85&lon=-89.45")
    assert response.status_code == 200
    assert response.json()["result"]["class"] in {"S1", "S2", "S3",
                                                  "not_evaluated"}
    calendar = client.get(
        "/api/agriculture/calendar?crop_id=maize&planting_date=2024-05-15")
    assert calendar.status_code == 200
    assert calendar.json()["result"]["classification"]["forecast_dependent"] is False


def test_api_simulate_requires_inputs_and_refuses_uncalibrated_forecast(client):
    bad = client.post("/api/agriculture/simulate", json={"crop_id": "maize"})
    assert bad.status_code == 400
    good = client.post("/api/agriculture/simulate", json={
        "crop_id": "maize", "planting_date": "2024-05-15",
        "awc_mm_per_m": 150, "root_depth_cm": 60,
        "allow_reference_kc": True})
    assert good.status_code == 200
    body = good.json()
    assert body["result"]["is_forecast"] is False
    assert body["result"]["outputs"]["yield"]["value_t_ha"] is None


def test_api_social_declares_synthetic(client):
    response = client.get("/api/social/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["policy"]["synthetic_only"] is True
    assert body["policy"]["population_inference_allowed"] is False
    assert client.get("/api/social/separation").json()["valid"] is True


def test_api_social_population_and_adoption(client):
    population = client.post("/api/social/population",
                             json={"size": 5, "seed": 2})
    assert population.status_code == 200
    assert population.json()["result"]["size"] == 5
    adoption = client.post("/api/social/adoption",
                           json={"seed": 2, "technology_id": "soil_testing"})
    assert adoption.status_code == 200
    assert "adoption_propensity" in adoption.json()["result"]


def test_api_social_rejects_unknown_technology(client):
    response = client.post("/api/social/adoption",
                           json={"technology_id": "teleport"})
    assert response.status_code in {400, 404}


def test_api_socio_scenario_and_analysis(client):
    scenario = client.post("/api/socio/scenario", json={
        "scenario_id": "E_diversification", "lat": 13.85, "lon": -89.45,
        "size": 5, "seed": 2})
    assert scenario.status_code == 200
    assert scenario.json()["result"]["is_prediction"] is False
    analysis = client.post("/api/socio/analysis", json={"runs": [
        {"scenario_id": "A_drought", "lat": 13.85, "lon": -89.45,
         "size": 4, "seed": 2},
        {"scenario_id": "G_support_program", "lat": 13.85, "lon": -89.45,
         "size": 4, "seed": 2},
    ]})
    assert analysis.status_code == 200
    assert analysis.json()["result"]["rows"]


def test_phase5_endpoints_still_work(client):
    assert client.get("/api/engines/meta").status_code == 200
