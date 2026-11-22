"""AGROSV — AgriculturalDecisionEngine (§7.2).

Decisión MAUT sobre opciones con restricciones duras. Los retornos esperados de
una opción de cultivo **no** son económicos: se usa la clase de aptitud como
proxy agronómico (S1=1,0; S2=0,7; S3=0,4). Sin hoja de precios no hay margen.

Un cultivo con aptitud `N` o `not_evaluated` se excluye cuando
`require_evaluated=True`. Ningún LLM participa: `llm_used` es `false`.
"""
from __future__ import annotations

from typing import Any

from ..agriculture.suitability import CropSuitabilityEngine
from ..social.behavior import BehaviorError, FarmerBehaviorEngine
from ..social import governance as SG

ENGINE = "agricultural_decision"
ENGINE_VERSION = SG.ENGINE_VERSION

CLASS_RETURN = {"S1": 1.0, "S2": 0.7, "S3": 0.4}
CLASS_RISK = {"S1": 0.15, "S2": 0.30, "S3": 0.50}


class DecisionError(ValueError):
    pass


class AgriculturalDecisionEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.suitability = CropSuitabilityEngine()
        self.behavior = FarmerBehaviorEngine()
        self._cache: dict[tuple, dict[str, Any]] = {}

    def _evaluate_crop(self, crop_id: str, lon: float, lat: float,
                       system: str) -> dict[str, Any]:
        key = (crop_id, round(lon, 4), round(lat, 4), system)
        if key not in self._cache:
            self._cache[key] = self.suitability.evaluate(
                crop_id, lon, lat, system=system)
        return self._cache[key]

    def decide(self, *, agent: dict[str, Any], lon: float, lat: float,
               options: list[dict[str, Any]] | None = None,
               household: dict[str, Any] | None = None,
               context: dict[str, Any] | None = None,
               require_evaluated: bool = True,
               threshold: float = 0.0) -> dict[str, Any]:
        if "state" not in agent:
            raise DecisionError("el agente no tiene estado agrícola")
        state = dict(agent["state"]["payload"])
        if household:
            state["labor_days_total"] = household.get("labor_days_total", 0)
        context = dict(context or {})

        evidence = []
        excluded_by_science = []
        if options is None:
            options = []
            system = "irrigated" if state.get("irrigated") else "rainfed"
            for crop_id in state.get("crops", []):
                evaluation = self._evaluate_crop(crop_id, lon, lat, system)
                payload = evaluation["result"]
                crop_class = payload["class"]
                evidence.append({
                    "crop_id": crop_id,
                    "class": crop_class,
                    "confidence": payload["confidence"],
                    "limiting_factors": payload["limiting_factors"],
                    "critical_missing": payload.get("critical_missing", []),
                })
                if require_evaluated and crop_class in {"N", "not_evaluated"}:
                    excluded_by_science.append({
                        "crop_id": crop_id, "class": crop_class,
                        "reason": ("aptitud no favorable o no evaluable: no se "
                                   "ofrece como opción"),
                    })
                    continue
                options.append({
                    "option_id": f"crop:{crop_id}",
                    "crop_id": crop_id,
                    "expected_return": CLASS_RETURN.get(crop_class, 0.0),
                    "risk": CLASS_RISK.get(crop_class, 0.6),
                    "capital_required": 0.0,
                    "suitability_class": crop_class,
                    "information_intensity": 0.3,
                    "return_basis": ("proxy agronómico por clase de aptitud; "
                                     "NO es un retorno económico"),
                })
        else:
            enriched = []
            for option in options:
                crop_id = option.get("crop_id")
                if crop_id:
                    evaluation = self._evaluate_crop(
                        crop_id, lon, lat,
                        "irrigated" if state.get("irrigated") else "rainfed")
                    crop_class = evaluation["result"]["class"]
                    option = {**option, "suitability_class": crop_class}
                    evidence.append({"crop_id": crop_id, "class": crop_class,
                                     "limiting_factors": evaluation["result"]
                                     ["limiting_factors"]})
                    if require_evaluated and crop_class in {"N",
                                                            "not_evaluated"}:
                        excluded_by_science.append({
                            "crop_id": crop_id, "class": crop_class,
                            "reason": "aptitud no favorable o no evaluable"})
                        continue
                enriched.append(option)
            options = enriched

        if not options:
            return SG.synthetic_envelope(
                ENGINE,
                result={
                    "decision": None,
                    "decision_status": "no_evaluable_options",
                    "agent_id": agent["agent_id"],
                    "scientific_evidence": evidence,
                    "excluded_by_science": excluded_by_science,
                    "llm_used": False,
                    "reason": ("ningún cultivo del agente tiene una clase de "
                               "aptitud evaluable; no se decide con datos "
                               "faltantes"),
                },
                assumptions=["no se sustituyen datos faltantes por supuestos"],
                limitations=["sin opciones evaluables no hay decisión"],
                sources=["crop_parameters_catalog", "agrosv_scenario"],
                query={"agent_id": agent["agent_id"]})

        try:
            decision = self.behavior.choose(
                options, state, context=context, threshold=threshold)
        except BehaviorError as exc:
            raise DecisionError(str(exc)) from None

        result = {
            "agent_id": agent["agent_id"],
            "archetype": agent["archetype"],
            "decision": decision["decision"],
            "decision_status": decision["decision_status"],
            "score": decision.get("score"),
            "ranking": decision.get("ranking"),
            "excluded": decision.get("excluded", []),
            "excluded_by_science": excluded_by_science,
            "weights": decision["weights"],
            "rationale": decision["rationale"],
            "scientific_evidence": evidence,
            "llm_used": False,
            "agronomic_constraints_respected": True,
            "synthetic": True,
            "not_a_prediction": True,
        }
        return SG.synthetic_envelope(
            ENGINE, result=result,
            assumptions=[
                "el retorno esperado es un proxy por clase de aptitud",
                "los pesos MAUT se derivan de atributos sintéticos",
                "la decisión es determinista",
            ],
            limitations=[
                "no es una predicción de decisión real",
                "no hay precios ni costos en la decisión",
                "la aptitud es una regla AGROSV sin validación local",
                "no se modela aprendizaje social en esta llamada",
            ],
            sources=["crop_parameters_catalog", "copdem30", "soilgrids_2",
                     "open_meteo_point", "fao_aez", "agrosv_scenario"],
            scenario_id=agent.get("state", {}).get("scenario_id"),
            processing=[
                SG.AG.step("aptitud por cultivo",
                           "CropSuitabilityEngine.evaluate"),
                SG.AG.step("decisión MAUT", "FarmerBehaviorEngine.choose"),
            ],
            query={"agent_id": agent["agent_id"], "lon": lon, "lat": lat})


__all__ = ["AgriculturalDecisionEngine", "DecisionError", "CLASS_RETURN",
           "CLASS_RISK"]
