"""AGROSV — AgriculturalScenarioEngine (§7.3).

Escenarios A–G con sobrescrituras declaradas. No son pronósticos: cada
resultado es una simulación condicionada a supuestos y a una población
sintética. Los escenarios económicos solo se evalúan si el usuario aporta hoja
de costos y precios; sin ellas el bloque económico queda `not_evaluated`.
"""
from __future__ import annotations

from typing import Any, Mapping

from ..agriculture.suitability import CropSuitabilityEngine
from ..social import governance as SG
from ..social.adoption import TechnologyAdoptionEngine
from ..social.economy import AgriculturalEconomyEngine, EconomyError
from ..social.household import AgriculturalHouseholdEngine
from ..social.population import AgriculturalPopulationEngine
from ..social.resilience import AgriculturalResilienceEngine
from .decision import AgriculturalDecisionEngine

ENGINE = "agricultural_scenario"
ENGINE_VERSION = SG.ENGINE_VERSION

SCENARIOS: dict[str, dict[str, Any]] = {
    "A_drought": {
        "label": "A — Sequía",
        "description": "reducción de agua disponible y shock de sequía",
        "overrides": {"water_multiplier": 0.6, "shock": "drought"},
        "practice": None,
    },
    "B_technology": {
        "label": "B — Adopción tecnológica",
        "description": "riego por goteo, semilla mejorada y asesoría digital",
        "overrides": {"info_add": 0.10},
        "practice": "drip_irrigation",
        "secondary_practices": ["improved_seed", "digital_advisory"],
    },
    "C_production_costs": {
        "label": "C — Costos de producción",
        "description": "aumento de costos de insumos y transporte",
        "overrides": {"capital_multiplier": 0.85, "cost_multiplier": 1.30},
        "practice": None,
    },
    "D_market_shock": {
        "label": "D — Choque de mercado",
        "description": "caída de precios de venta",
        "overrides": {"price_multiplier": 0.70},
        "practice": None,
    },
    "E_diversification": {
        "label": "E — Diversificación productiva",
        "description": "incorporación de un segundo cultivo",
        "overrides": {"diversify": True},
        "practice": None,
    },
    "F_climate_variability": {
        "label": "F — Variabilidad climática",
        "description": "condición más seca/más húmeda, no una proyección",
        "overrides": {"water_multiplier": 0.8, "planting_shift_days": 15},
        "practice": None,
    },
    "G_support_program": {
        "label": "G — Programa de apoyo",
        "description": "asistencia técnica, capital semilla y crédito (hipotético)",
        "overrides": {"capital_add": 500.0, "credit_add": 0.20,
                      "info_add": 0.15},
        "practice": "soil_conservation",
    },
}


class ScenarioError(ValueError):
    pass


class AgriculturalScenarioEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.population = AgriculturalPopulationEngine()
        self.decision = AgriculturalDecisionEngine()
        self.adoption = TechnologyAdoptionEngine()
        self.resilience = AgriculturalResilienceEngine()
        self.household = AgriculturalHouseholdEngine()
        self.economy = AgriculturalEconomyEngine()
        self.suitability = CropSuitabilityEngine()

    def scenarios(self) -> dict[str, Any]:
        return {
            "count": len(SCENARIOS),
            "scenarios": [{"scenario_id": k, **{kk: vv for kk, vv in v.items()
                                               if kk != "overrides"},
                           "overrides": v["overrides"]}
                          for k, v in SCENARIOS.items()],
            "warning": "escenarios de simulación, no predicciones",
        }

    def _apply_overrides(self, agent: dict[str, Any], overrides: Mapping[str, Any],
                         scenario_id: str) -> dict[str, Any]:
        payload = dict(agent["state"]["payload"])
        if "capital_multiplier" in overrides:
            payload["capital_usd"] = round(
                float(payload.get("capital_usd", 0.0))
                * float(overrides["capital_multiplier"]), 2)
        if "capital_add" in overrides:
            payload["capital_usd"] = round(
                float(payload.get("capital_usd", 0.0))
                + float(overrides["capital_add"]), 2)
        if "credit_add" in overrides:
            payload["credit_access"] = round(min(1.0, float(
                payload.get("credit_access", 0.0))
                + float(overrides["credit_add"])), 3)
        if "info_add" in overrides:
            payload["info_access"] = round(min(1.0, float(
                payload.get("info_access", 0.0))
                + float(overrides["info_add"])), 3)
        if overrides.get("diversify") and len(payload.get("crops", [])) <= 1:
            extra = "beans" if payload.get("primary_crop") != "beans" else "maize"
            payload["crops"] = list(payload.get("crops", [])) + [extra]
            payload["diversified_by_scenario"] = extra
        record = SG.make_record(
            "SYNTHETIC_AGRICULTURAL_STATE", payload,
            method=f"sobrescritura del escenario {scenario_id}",
            assumptions=["las sobrescrituras son supuestos de escenario"],
            scenario_id=scenario_id,
            agent_id=agent["agent_id"],
            parent_ids=[agent["state"].get("record_id")],
            validation_status="not_validated")
        out = {"agent_id": agent["agent_id"],
               "archetype": agent["archetype"], "index": agent["index"],
               "seed": agent["seed"], "state": record}
        if "source_profile" in agent:
            out["source_profile"] = agent["source_profile"]
        if "nemotron_uuid" in agent:
            out["nemotron_uuid"] = agent["nemotron_uuid"]
        return out

    def run(self, scenario_id: str, *, lon: float, lat: float,
            size: int = 60, seed: int = 42,
            costs: Mapping[str, Mapping[str, Any]] | None = None,
            prices: Mapping[str, Mapping[str, Any]] | None = None,
            yield_t_ha: float | None = None,
            population_source: str = "synthetic",
            department: str | None = None,
            municipality: str | None = None,
            area: str | None = None) -> dict[str, Any]:
        spec = SCENARIOS.get(scenario_id)
        if spec is None:
            raise ScenarioError(
                f"escenario desconocido: {scenario_id}; "
                f"disponibles {sorted(SCENARIOS)}")
        if size > 500:
            raise ScenarioError(
                "size > 500 en un escenario: use lotes para no bloquear la API")
        src_mode = str(population_source or "synthetic").strip().lower()
        if src_mode not in {"synthetic", "nemotron"}:
            raise ScenarioError(
                f"population_source inválido: {population_source!r}; use 'synthetic' o 'nemotron'"
            )
        if src_mode == "nemotron":
            population = self.population.generate_from_nemotron(
                size=size,
                seed=seed,
                department=department,
                municipality=municipality,
                area=area,
                scenario_id=scenario_id,
            )
        else:
            population = self.population.generate(
                size, seed=seed, scenario_id=scenario_id
            )
        agents = [self._apply_overrides(a, spec["overrides"], scenario_id)
                  for a in population["result"]["agents"]]

        water_factor = float(spec["overrides"].get("water_multiplier", 1.0))
        practice = spec.get("practice")
        shock = spec["overrides"].get("shock")
        decisions: dict[str, int] = {}
        statuses: dict[str, int] = {}
        adoption = {"considered": 0, "not_now": 0, "not_feasible": 0}
        impacts, margins = [], []
        records = []
        n = 0
        for agent in agents:
            household = self.household.compose(agent, seed=seed)
            context = {"water_available_mm": 900.0 * water_factor}
            decision = self.decision.decide(
                agent=agent, lon=lon, lat=lat, household=household["household"],
                context=context)
            payload = decision["result"]
            decisions[payload["decision"] or "sin_decisión"] = decisions.get(
                payload["decision"] or "sin_decisión", 0) + 1
            statuses[payload["decision_status"]] = statuses.get(
                payload["decision_status"], 0) + 1
            if payload["decision"] is not None:
                n += 1
            if practice:
                adopt = self.adoption.evaluate(agent, practice)["result"]
                key = {"consider_adoption": "considered",
                       "not_now": "not_now",
                       "not_feasible": "not_feasible"}[adopt["decision"]]
                adoption[key] += 1
            if shock:
                impact = self.resilience.assess(
                    agent, household["household"], shock_id=shock)["result"]
                impacts.append(impact["impact_index"])
            if costs and prices and yield_t_ha is not None:
                try:
                    margin = self.economy.evaluate(
                        agent=agent, costs=costs,
                        prices={k: {**v, "price_per_t": float(
                            v["price_per_t"]) * float(
                            spec["overrides"].get("price_multiplier", 1.0))}
                            for k, v in prices.items()},
                        yield_t_ha=yield_t_ha)["result"]["margin"]
                    margins.append(margin)
                except EconomyError:
                    pass
            records.append(decision)

        metrics = {
            "n_agents": size,
            "decisions_count": n,
            "decision_distribution": decisions,
            "decision_status": statuses,
            "adoption": ({**adoption,
                          "fraction_considering": round(
                              adoption["considered"] / size, 3)}
                         if practice else None),
            "mean_impact_index": (round(sum(impacts) / len(impacts), 3)
                                  if impacts else None),
            "economic": ({"n": len(margins),
                          "mean_margin": round(sum(margins) / len(margins), 2)}
                         if margins else
                         {"available": False,
                          "reason": "sin hoja de costos/precios o rendimiento"}),
            "water_available_mm_assumed": round(900.0 * water_factor, 1),
        }
        result = {
            "scenario_id": scenario_id,
            "label": spec["label"],
            "description": spec["description"],
            "overrides": spec["overrides"],
            "practice": practice,
            "shock": shock,
            "population": {
                "size": size, "seed": seed,
                "population_source": src_mode,
                "nemotron_backed": src_mode == "nemotron",
                "archetypes": population["result"]["counts"],
                "representative": False,
            },
            "location": {"lon": lon, "lat": lat},
            "metrics": metrics,
            "is_prediction": False,
            "is_national_estimate": False,
        }
        separation = SG.check_separation(
            [a["state"] for a in agents] +
            [r for r in records if isinstance(r, dict) and "layer" in r])
        return SG.synthetic_envelope(
            ENGINE, result=result,
            assumptions=[
                "población sintética con semilla reproducible",
                "las sobrescrituras son supuestos de escenario",
                "la aptitud se calcula una vez por cultivo y punto",
                "el agua disponible del escenario es un valor declarado "
                f"({metrics['water_available_mm_assumed']} mm)",
                "los escenarios económicos requieren hojas aportadas",
            ],
            limitations=[
                "no es un pronóstico ni una proyección",
                "no representa a la población agrícola salvadoreña",
                "los resultados dependen de arquetipos y umbrales AGROSV",
                "sin validación empírica de decisiones ni adopción",
                "F no es un escenario climático modelado: es un multiplicador",
            ],
            sources=["agrosv_scenario", "crop_parameters_catalog", "copdem30",
                     "soilgrids_2", "open_meteo_point"],
            scenario_id=scenario_id,
            processing=[
                SG.AG.step("población sintética", "AgriculturalPopulationEngine"),
                SG.AG.step("sobrescrituras", "_apply_overrides"),
                SG.AG.step("decisión", "AgriculturalDecisionEngine"),
                SG.AG.step("adopción/resiliencia", "adoption/resilience"),
                SG.AG.step("verificación de capas", "check_separation"),
            ],
            query={"scenario_id": scenario_id, "lon": lon, "lat": lat,
                   "size": size, "seed": seed},
        ) | {"layer_check": separation}


__all__ = ["AgriculturalScenarioEngine", "SCENARIOS", "ScenarioError"]
