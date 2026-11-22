"""Pruebas de Fase 6 — Subsistema B (población sintética).

Verifican gobernanza de capas, reproducibilidad y consistencia interna. No
validan que los arquetipos representen a la población salvadoreña.
"""
from __future__ import annotations

import pytest

from agrosv.social import governance as SG
from agrosv.social.adoption import (TECHNOLOGIES, TechnologyAdoptionEngine,
                                    capital_class)
from agrosv.social.behavior import BehaviorError, FarmerBehaviorEngine
from agrosv.social.economy import (AgriculturalEconomyEngine, EconomyError,
                                   cost_sheet, price_sheet)
from agrosv.social.household import AgriculturalHouseholdEngine
from agrosv.social.multiagent import AgriculturalMultiAgentEngine
from agrosv.social.persona import AgriculturalPersonaEngine
from agrosv.social.population import (ARCHETYPES, AgriculturalPopulationEngine,
                                      PopulationError)
from agrosv.social.resilience import AgriculturalResilienceEngine


def _agents(size: int = 12, seed: int = 7):
    return AgriculturalPopulationEngine().generate(size, seed=seed)["result"]["agents"]


# --- población --------------------------------------------------------------
def test_population_is_reproducible_with_same_seed():
    first = AgriculturalPopulationEngine().generate(8, seed=11)
    second = AgriculturalPopulationEngine().generate(8, seed=11)
    assert [a["state"]["payload"] for a in first["result"]["agents"]] == \
        [a["state"]["payload"] for a in second["result"]["agents"]]
    assert first["result"]["counts"] == second["result"]["counts"]


def test_different_seed_changes_population():
    first = AgriculturalPopulationEngine().generate(8, seed=1)
    second = AgriculturalPopulationEngine().generate(8, seed=2)
    assert first["result"]["counts"] != second["result"]["counts"]


def test_population_declares_not_representative():
    payload = AgriculturalPopulationEngine().generate(4, seed=3)
    assert payload["synthetic"] is True
    assert payload["represents_real_people"] is False
    assert payload["result"]["representativeness"]["representative"] is False


def test_population_rejects_unknown_archetype_and_negative_size():
    engine = AgriculturalPopulationEngine()
    with pytest.raises(PopulationError):
        engine.generate(1, archetypes=["astronaut"])
    with pytest.raises(PopulationError):
        engine.generate(0)


def test_population_rejects_huge_default_generation():
    with pytest.raises(PopulationError):
        AgriculturalPopulationEngine().generate(100_001)


def test_weights_must_reference_selected_archetypes():
    with pytest.raises(PopulationError):
        AgriculturalPopulationEngine().generate(
            2, archetypes=["subsistence_maize"],
            weights={"coffee_smallholder": 1.0})


def test_population_records_pass_layer_separation():
    agents = _agents(6)
    check = SG.check_separation([a["state"] for a in agents])
    assert check["valid"] is True
    assert check["layers"] == {"SYNTHETIC_AGRICULTURAL_STATE": 6}


def test_every_agent_has_provenance_fields():
    agent = _agents(1)[0]
    record = agent["state"]
    assert record["generation_method"]
    assert record["assumptions"]
    assert record["validation_status"] == "not_validated"
    assert record["synthetic"] is True
    assert record["record_id"].startswith("SYN-")


# --- persona ----------------------------------------------------------------
def test_sample_profiles_are_real_rows_and_not_agricultural():
    payload = AgriculturalPersonaEngine().sample_profiles()
    assert payload["count"] == 3
    assert payload["agricultural_count"] == 0
    assert payload["profiles"][0]["profile"]["origin"] == "nemotron_sample"
    assert payload["profiles"][0]["profile"]["not_a_real_person"] is True


def test_persona_does_not_reassign_non_agricultural_source_role():
    agent = _agents(1)[0]
    sample = AgriculturalPersonaEngine().sample_profiles()["profiles"][0]
    result = AgriculturalPersonaEngine().compose(agent, source_profile=sample)
    assert result["attachable"] is False
    assert "no reasigna roles" in result["reason"]
    assert "source_profile" in result
    assert "synthetic_agricultural_state" in result


def test_persona_attaches_synthetic_profile_and_keeps_layers_separate():
    engine = AgriculturalPersonaEngine()
    agent = _agents(1)[0]
    payload = engine.compose(agent)
    assert payload["attachable"] is True
    card = payload["persona"]
    assert card["is_person"] is False
    assert card["source_profile"]["origin"] == "schema_compatible_synthetic"
    assert card["source_profile"]["from_nemotron_dataset"] is False
    assert card["source_profile"]["sex"] is None
    assert card["agricultural_state"]["archetype"] == agent["archetype"]


def test_profile_cannot_carry_agricultural_fields():
    record = SG.make_record(
        "SOURCE_PROFILE", {"crop_id": "maize"},
        method="prueba", assumptions=["prueba"])
    check = SG.check_separation([record])
    assert check["valid"] is False
    assert "agrícolas" in check["errors"][0]


def test_observed_layer_cannot_be_generated():
    with pytest.raises(SG.LayerError):
        SG.make_record("OBSERVED_VALIDATION_DATA", {"x": 1},
                       method="prueba", assumptions=["prueba"])


def test_synthetic_record_cannot_claim_observed_evidence():
    with pytest.raises(SG.LayerError):
        SG.make_record("HOUSEHOLD_STATE", {"x": 1},
                       method="prueba", assumptions=["prueba"],
                       evidence_class="observed_statistic")


# --- hogar ------------------------------------------------------------------
def test_household_is_internally_consistent():
    agent = _agents(1)[0]
    payload = AgriculturalHouseholdEngine().compose(agent)
    assert payload["consistency"]["valid"] is True
    assert payload["household"]["size"] <= 8
    assert abs(sum(payload["household"]["income_shares"].values()) - 1) <= 0.01
    assert payload["record"]["layer"] == "HOUSEHOLD_STATE"


def test_household_omits_sensitive_attributes():
    household = AgriculturalHouseholdEngine().compose(_agents(1)[0])["household"]
    assert "sexo" in household["sensitive_attributes_omitted"]
    assert "sex" not in household
    assert "religion" not in household


def test_household_labor_is_proportional_not_observed():
    household = AgriculturalHouseholdEngine().compose(_agents(1)[0])["household"]
    assert household["labor_availability_factor"] <= 1.0
    assert "no son ingresos" in household["note"]


# --- comportamiento ---------------------------------------------------------
def _state(**overrides):
    base = {"capital_usd": 1000.0, "risk_aversion": 0.8, "info_access": 0.2,
            "experience_years": 5, "labor_days_total": 300,
            "crops": ["maize"]}
    base.update(overrides)
    return base


def test_risk_averse_agent_prefers_low_risk_equal_return():
    decision = FarmerBehaviorEngine().choose([
        {"option_id": "risky", "expected_return": 100, "risk": 0.9,
         "capital_required": 100},
        {"option_id": "safe", "expected_return": 100, "risk": 0.05,
         "capital_required": 100},
    ], _state(risk_aversion=0.95))
    assert decision["decision"] == "safe"


def test_capital_and_suitability_are_hard_constraints():
    decision = FarmerBehaviorEngine().choose([
        {"option_id": "expensive", "expected_return": 200, "risk": 0.1,
         "capital_required": 9000},
        {"option_id": "not_suitable", "expected_return": 200, "risk": 0.1,
         "capital_required": 10, "suitability_class": "N"},
    ], _state())
    assert decision["decision"] is None
    assert decision["decision_status"] == "no_feasible_option"
    reasons = [e["reasons"] for e in decision["excluded"]]
    assert any("capital" in " ".join(r) for r in reasons)
    assert any("aptitud N" in " ".join(r) for r in reasons)


def test_behavior_requires_options():
    with pytest.raises(BehaviorError):
        FarmerBehaviorEngine().choose([], _state())


def test_learning_is_bounded_and_recorded():
    agent = _agents(1)[0]
    payload = FarmerBehaviorEngine().learn(
        agent, success=True, source="extension", magnitude=0.5)
    assert payload["state"]["info_access"] <= 1.0
    assert payload["record"]["layer"] == "SIMULATION_HISTORY"
    assert payload["record"]["parents"]


# --- economía ---------------------------------------------------------------
def _costs(amount: float = 100.0):
    return {item: {"amount": amount, "unit": "USD/ha", "currency": "USD",
                   "date": "2026-01-01", "source": "TEST_FIXTURE"}
            for item in ("seed", "fertilizer", "pesticide", "labor",
                         "irrigation", "equipment", "transport")}


def _prices(price: float = 200.0):
    return {"maize": {"price_per_t": price, "currency": "USD",
                      "unit": "USD/t", "date": "2026-01-01",
                      "market": "fixture", "source": "TEST_FIXTURE"}}


def test_economy_requires_source_date_currency_unit():
    with pytest.raises(EconomyError):
        cost_sheet({"seed": {"amount": 10, "unit": "USD/ha"}})


def test_economy_refuses_missing_price():
    with pytest.raises(EconomyError):
        AgriculturalEconomyEngine().evaluate(
            agent=_agents(1)[0], costs=_costs(), prices={},
            yield_t_ha=3.0)


def test_economy_margin_arithmetic():
    result = AgriculturalEconomyEngine().evaluate(
        agent=_agents(1)[0], costs=_costs(100), prices=_prices(200),
        yield_t_ha=3.0, area_ha=2.0, crop_id="maize")["result"]
    assert result["costs"]["total"] == 1400.0
    assert result["revenue"] == 1200.0
    assert result["margin"] == -200.0
    assert result["break_even_yield_t_ha"] == pytest.approx(3.5)
    assert result["is_accounting"] is False


def test_economy_rejects_currency_mismatch():
    prices = _prices()
    prices["maize"]["currency"] = "EUR"
    with pytest.raises(EconomyError):
        AgriculturalEconomyEngine().evaluate(
            agent=_agents(1)[0], costs=_costs(), prices=prices,
            yield_t_ha=3.0)


def test_price_sheet_requires_price():
    with pytest.raises(EconomyError):
        price_sheet({"maize": {"currency": "USD", "date": "2026-01-01",
                               "market": "x", "source": "TEST"}})


# --- adopción ---------------------------------------------------------------
def test_adoption_hard_barrier_water():
    agent = _agents(1)[0]
    agent["state"]["payload"]["irrigated"] = False
    agent["state"]["payload"]["capital_usd"] = 50_000
    payload = TechnologyAdoptionEngine().evaluate(agent, "drip_irrigation")
    assert payload["result"]["decision"] == "not_feasible"
    assert any(b["barrier"] == "agua" for b in payload["result"]["hard_barriers"])


def test_adoption_propensity_is_index_not_probability():
    payload = TechnologyAdoptionEngine().evaluate(
        _agents(1)[0], "soil_conservation")["result"]
    assert 0 <= payload["adoption_propensity"] <= 1
    assert payload["is_probability"] is False
    assert payload["is_national_rate"] is False


def test_adoption_unknown_technology_raises():
    with pytest.raises(Exception):
        TechnologyAdoptionEngine().evaluate(_agents(1)[0], "teleportation")


def test_every_technology_has_barriers_and_no_prices():
    for key, spec in TECHNOLOGIES.items():
        assert spec["barriers"]
        assert "cost_usd" not in spec
    assert capital_class(500) == "low"


# --- resiliencia ------------------------------------------------------------
def test_resilience_requires_known_shock():
    with pytest.raises(Exception):
        AgriculturalResilienceEngine().assess(
            _agents(1)[0], {}, shock_id="meteor")


def test_resilience_components_and_coping_options():
    agent = _agents(1)[0]
    payload = AgriculturalResilienceEngine().assess(
        agent, {"income_shares": {"farm": 1.0}}, shock_id="drought")["result"]
    assert 0 <= payload["impact_index"] <= 1
    assert payload["outcome_class"] in {"bajo", "moderado", "alto", "severo"}
    assert "reducir_insumos" in payload["coping_options"]
    assert payload["is_official_vulnerability"] is False


def test_more_capacity_never_increases_impact_for_same_shock():
    agent = _agents(1)[0]
    low = dict(agent["state"]["payload"], capital_usd=100, credit_access=0.0,
               irrigated=False, crops=["maize"], info_access=0.0,
               cooperative=False)
    high = dict(low, capital_usd=100000, credit_access=1.0, irrigated=True,
                crops=["maize", "beans", "coffee"], info_access=1.0,
                cooperative=True)
    engine = AgriculturalResilienceEngine()
    low_agent = {**agent, "state": {**agent["state"], "payload": low}}
    high_agent = {**agent, "state": {**agent["state"], "payload": high}}
    low_impact = engine.assess(low_agent, {}, shock_id="drought")["result"]
    high_impact = engine.assess(high_agent, {}, shock_id="drought")["result"]
    assert high_impact["impact_index"] <= low_impact["impact_index"]


# --- multiagente ------------------------------------------------------------
def test_multiagent_reproducible_with_same_seed():
    agents = _agents(10, seed=4)
    engine = AgriculturalMultiAgentEngine()
    first = engine.run(agents, steps=6, seed=99, practice="improved_seed")
    second = engine.run(agents, steps=6, seed=99, practice="improved_seed")
    assert first["result"]["history"] == second["result"]["history"]
    assert first["result"]["seed"] == 99


def test_multiagent_history_and_layers():
    payload = AgriculturalMultiAgentEngine().run(
        _agents(8), steps=4, seed=1, practice="climate_services")
    result = payload["result"]
    assert len(result["history"]) == 4
    assert result["reproducible"] is True
    assert result["is_national_forecast"] is False
    assert payload["record"]["layer"] == "SIMULATION_HISTORY"


def test_multiagent_rejects_bad_steps_and_shock():
    engine = AgriculturalMultiAgentEngine()
    with pytest.raises(Exception):
        engine.run(_agents(2), steps=0)
    with pytest.raises(Exception):
        engine.run(_agents(2), steps=2, shock="volcano")


def test_archetype_crops_exist_in_catalog():
    from agrosv.agriculture.catalog import CROPS
    for spec in ARCHETYPES.values():
        assert set(spec["crops"]) <= set(CROPS)
