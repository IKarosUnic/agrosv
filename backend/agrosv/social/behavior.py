"""AGROSV — FarmerBehaviorEngine (§5.5).

Reglas explícitas, inspeccionables y deterministas (sin aleatoriedad en la
decisión). El modelo es un MAUT simple con pesos derivados de atributos
sintéticos; no es una teoría psicológica validada.

Restricciones duras: capital, agua, mano de obra y clase de aptitud `N`.
Ninguna preferencia puede anular una restricción científica o de recursos.
"""
from __future__ import annotations

from typing import Any, Iterable

from . import governance as SG

ENGINE = "farmer_behavior"
ENGINE_VERSION = SG.ENGINE_VERSION

DEFAULT_THRESHOLD = 0.0


class BehaviorError(ValueError):
    pass


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class FarmerBehaviorEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def weights(self, state: dict[str, Any]) -> dict[str, float]:
        risk_aversion = _clip01(state.get("risk_aversion", 0.5))
        info = _clip01(state.get("info_access", 0.2))
        experience = _clip01(float(state.get("experience_years", 5)) / 30.0)
        capital = max(0.0, float(state.get("capital_usd", 0.0)))
        capital_capacity = _clip01(capital / 20000.0)
        raw = {
            "return": 1.0 - 0.5 * risk_aversion,
            "risk": 0.2 + 0.6 * risk_aversion,
            "capital": 0.3 + 0.4 * (1.0 - capital_capacity),
            "information": 0.2 + 0.3 * info,
            "experience": 0.1 + 0.2 * experience,
        }
        total = sum(raw.values())
        return {k: round(v / total, 4) for k, v in raw.items()}

    def choose(self, options: Iterable[dict[str, Any]],
               state: dict[str, Any], *, context: dict[str, Any] | None = None,
               threshold: float = DEFAULT_THRESHOLD) -> dict[str, Any]:
        options = list(options)
        if not options:
            raise BehaviorError("se requiere al menos una opción")
        context = context or {}
        weights = self.weights(state)
        capital = float(state.get("capital_usd", 0.0))
        labor = float(state.get("labor_days_total", 0.0))
        water = context.get("water_available_mm")
        returns = [float(o.get("expected_return", 0.0)) for o in options]
        max_return = max(returns) or 1.0

        feasible, excluded = [], []
        for option in options:
            reasons = []
            if float(option.get("capital_required", 0.0)) > capital:
                reasons.append("capital insuficiente")
            if option.get("suitability_class") == "N":
                reasons.append("aptitud N: restricción científica")
            required_water = option.get("water_required_mm")
            if required_water is not None and water is not None and \
                    float(required_water) > float(water):
                reasons.append("agua insuficiente en el escenario")
            required_labor = option.get("labor_required_days")
            if required_labor is not None and float(required_labor) > labor:
                reasons.append("mano de obra insuficiente")
            if reasons:
                excluded.append({"option_id": option.get("option_id"),
                                 "reasons": reasons})
                continue
            capital_slack = 1.0 - _clip01(
                float(option.get("capital_required", 0.0)) / capital
                if capital > 0 else 0.0)
            score = (
                weights["return"] * (_clip01(float(
                    option.get("expected_return", 0.0)) / max_return))
                + weights["risk"] * (1.0 - _clip01(option.get("risk", 0.5)))
                + weights["capital"] * capital_slack
                + weights["information"] * _clip01(
                    state.get("info_access", 0.0))
                * _clip01(option.get("information_intensity", 0.0))
                + weights["experience"] * _clip01(
                    float(state.get("experience_years", 0)) / 30.0)
            )
            feasible.append({"option": option, "score": round(score, 4),
                             "capital_slack": round(capital_slack, 3)})

        if not feasible:
            return {
                "decision": None,
                "decision_status": "no_feasible_option",
                "excluded": excluded,
                "weights": weights,
                "rationale": ["ninguna opción cumple las restricciones duras"],
                "reproducible": True,
                "synthetic": True,
            }
        feasible.sort(key=lambda r: (-r["score"], str(
            r["option"].get("option_id"))))
        best = feasible[0]
        ranked = [{"option_id": r["option"].get("option_id"),
                   "score": r["score"]} for r in feasible]
        rationale = [
            f"pesos MAUT: {weights}",
            f"restricciones duras evaluadas: capital={capital}, "
            f"mano de obra={labor}, agua={water}",
            f"opciones excluidas: {excluded or 'ninguna'}",
            f"mejor puntuación: {ranked[0]}",
        ]
        status = "selected"
        if best["score"] < threshold:
            status = "selected_below_threshold"
            rationale.append(
                f"la puntuación {best['score']} es menor que el umbral "
                f"{threshold}: el agente podría aplazar la decisión")
        return {
            "decision": best["option"].get("option_id"),
            "decision_status": status,
            "selected": {k: v for k, v in best["option"].items()
                         if k != "expected_return"},
            "score": best["score"],
            "ranking": ranked,
            "excluded": excluded,
            "weights": weights,
            "rationale": rationale,
            "reproducible": True,
            "synthetic": True,
            "not_a_prediction": True,
        }

    def learn(self, agent: dict[str, Any], *, success: bool,
              source: str = "extension", magnitude: float = 0.05
              ) -> dict[str, Any]:
        if "state" not in agent:
            raise BehaviorError("el agente no tiene estado agrícola")
        if not 0 <= magnitude <= 1:
            raise BehaviorError("magnitude debe estar en [0, 1]")
        payload = dict(agent["state"]["payload"])
        delta = magnitude if success else -magnitude
        payload["info_access"] = round(_clip01(
            float(payload.get("info_access", 0.0)) + delta * 0.5), 3)
        payload["experience_years"] = int(min(
            60, int(payload.get("experience_years", 0)) + (1 if success else 0)))
        trust = dict(payload.get("trust_by_source", {}))
        trust[source] = round(_clip01(trust.get(source, 0.5) + delta), 3)
        payload["trust_by_source"] = trust
        record = SG.make_record(
            "SIMULATION_HISTORY", {"learning": payload, "success": success,
                                   "source": source},
            method="actualización acotada de experiencia y confianza",
            assumptions=["el aprendizaje es una regla declarada, no un modelo "
                         "cognitivo validado"],
            agent_id=agent["agent_id"],
            parent_ids=[agent["state"].get("record_id")],
            validation_status="not_validated")
        return {"agent_id": agent["agent_id"], "state": payload,
                "record": record, "synthetic": True}


__all__ = ["FarmerBehaviorEngine", "BehaviorError", "DEFAULT_THRESHOLD"]
