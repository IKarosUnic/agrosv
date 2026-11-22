"""AGROSV — AgriculturalMultiAgentEngine (§5.9).

Difusión de una práctica en una red declarada. La red es un anillo con dos
vecinos más un lazo aleatorio; la información fluye por confianza y acceso a
información. Sin ruido externo: el resultado es reproducible con la semilla.

No se simula un mercado completo ni instituciones: solo intercambio de
información, cooperación básica y un shock común.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import governance as SG
from .adoption import TechnologyAdoptionEngine
from .resilience import SHOCKS

ENGINE = "agricultural_multiagent"
ENGINE_VERSION = SG.ENGINE_VERSION


class MultiAgentError(ValueError):
    pass


class AgriculturalMultiAgentEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.adoption = TechnologyAdoptionEngine()

    def run(self, agents: list[dict[str, Any]], *, steps: int = 10,
            seed: int = 7, practice: str = "drip_irrigation",
            threshold: float = 0.55,
            shock: str | None = None) -> dict[str, Any]:
        if not agents:
            raise MultiAgentError("se requiere al menos un agente")
        if not 1 <= steps <= 500:
            raise MultiAgentError("steps debe estar en 1–500")
        if shock is not None and shock not in SHOCKS:
            raise MultiAgentError(f"shock desconocido: {shock}")
        rng = np.random.default_rng(seed)
        n = len(agents)

        states = []
        for agent in agents:
            payload = dict(agent.get("state", {}).get("payload", {}))
            if not payload:
                raise MultiAgentError(
                    f"{agent.get('agent_id')} no tiene estado agrícola")
            adoption = self.adoption.evaluate(
                agent, practice, threshold=threshold)["result"]
            payload["_propensity"] = float(adoption["adoption_propensity"])
            payload["_feasible"] = adoption["decision"] != "not_feasible"
            states.append(payload)

        neighbors: list[list[int]] = []
        for i in range(n):
            ring = [(i - 1) % n, (i + 1) % n]
            extra = int(rng.integers(0, n))
            neighbors.append(sorted(set(ring + [extra])))

        if shock:
            severity = SHOCKS[shock]["severity"]
            for state in states:
                if not state.get("irrigated", False):
                    state["capital_usd"] = round(
                        float(state.get("capital_usd", 0.0))
                        * (1.0 - 0.3 * severity), 2)

        history = []
        adopted: set[str] = set()
        for step in range(steps):
            new_propensities = []
            for i, state in enumerate(states):
                if not state["_feasible"] or state["_propensity"] >= threshold:
                    new_propensities.append(state["_propensity"])
                    continue
                peer = float(np.mean([states[j]["_propensity"]
                                      for j in neighbors[i]]))
                info = float(state.get("info_access", 0.0))
                coop = 0.05 if state.get("cooperative", False) else 0.0
                delta = 0.30 * info * (peer - state["_propensity"]) + coop
                new_propensities.append(
                    round(min(1.0, max(0.0, state["_propensity"] + delta)), 4))
            for i, value in enumerate(new_propensities):
                states[i]["_propensity"] = value
                if value >= threshold and states[i]["_feasible"]:
                    adopted.add(agents[i]["agent_id"])
            count = sum(1 for s in states
                        if s["_propensity"] >= threshold and s["_feasible"])
            history.append({
                "step": step,
                "adopted": count,
                "adoption_fraction": round(count / n, 4),
                "mean_propensity": round(
                    float(np.mean([s["_propensity"] for s in states])), 4),
            })

        by_archetype: dict[str, dict[str, int]] = {}
        for agent in agents:
            bucket = by_archetype.setdefault(agent["archetype"],
                                             {"n": 0, "adopted": 0})
            bucket["n"] += 1
            if agent["agent_id"] in adopted:
                bucket["adopted"] += 1
        result = {
            "practice": practice,
            "seed": seed,
            "steps": steps,
            "agents": n,
            "threshold": threshold,
            "shock": shock,
            "final_adopted": len(adopted),
            "final_adoption_fraction": round(len(adopted) / n, 4),
            "history": history,
            "by_archetype": by_archetype,
            "adopted_ids": sorted(adopted),
            "network": {"type": "anillo + 1 lazo aleatorio",
                        "mean_degree": round(
                            float(np.mean([len(x) for x in neighbors])), 2)},
            "reproducible": True,
            "deterministic_given_seed": True,
            "is_national_forecast": False,
        }
        record = SG.make_record(
            "SIMULATION_HISTORY",
            {k: v for k, v in result.items() if k != "adopted_ids"},
            method=("difusión determinista de propensión en red con semilla; "
                    "adopción por umbral"),
            assumptions=[
                "la propensión inicial proviene del motor de adopción",
                "la red es sintética y no representa vínculos reales",
                "no hay mercado, precios ni instituciones endógenas",
                "el shock se aplica al capital de productores de secano",
            ],
            scenario_id=agents[0].get("state", {}).get("scenario_id"),
            validation_status="not_validated")
        return {
            "result": result,
            "record": record,
            "synthetic": True,
            "limitations": [
                "no predice adopción nacional",
                "la red y los umbrales son supuestos AGROSV",
                "no hay validación con datos de difusión tecnológica",
            ],
        }


__all__ = ["AgriculturalMultiAgentEngine", "MultiAgentError"]
