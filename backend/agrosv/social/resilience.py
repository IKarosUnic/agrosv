"""AGROSV — AgriculturalResilienceEngine (§5.8).

Impacto y capacidad de adaptación como **índices de escenario**. Los
multiplicadores son supuestos declarados, no coeficientes estimados: no hay
datos de pérdidas por sequía, inundación o precios para El Salvador en el
repositorio.

Ningún resultado es una clasificación oficial de vulnerabilidad de comunidades
reales.
"""
from __future__ import annotations

import math
from typing import Any

from . import governance as SG

ENGINE = "agricultural_resilience"
ENGINE_VERSION = SG.ENGINE_VERSION

SHOCKS: dict[str, dict[str, Any]] = {
    "drought": {"label": "Sequía", "severity": 0.60, "dimension": "water",
                "loss_factor": 0.30},
    "excess_rain": {"label": "Lluvia excesiva", "severity": 0.50,
                    "dimension": "water", "loss_factor": 0.25},
    "flood": {"label": "Inundación", "severity": 0.80, "dimension": "water",
              "loss_factor": 0.45},
    "heat": {"label": "Estrés térmico", "severity": 0.50, "dimension": "heat",
             "loss_factor": 0.20},
    "pest_outbreak": {"label": "Brote de plaga", "severity": 0.55,
                      "dimension": "biotic", "loss_factor": 0.30},
    "input_price_increase": {"label": "Aumento de precios de insumos",
                             "severity": 0.40, "dimension": "cost",
                             "loss_factor": 0.15},
    "market_price_drop": {"label": "Caída de precios de venta",
                          "severity": 0.50, "dimension": "income",
                          "loss_factor": 0.25},
    "supply_interruption": {"label": "Interrupción de suministro",
                            "severity": 0.40, "dimension": "logistics",
                            "loss_factor": 0.15},
}

OUTCOME_CLASSES = (
    (0.20, "bajo"),
    (0.40, "moderado"),
    (0.65, "alto"),
    (1.01, "severo"),
)


class ResilienceError(ValueError):
    pass


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class AgriculturalResilienceEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def shocks(self) -> dict[str, Any]:
        return {"count": len(SHOCKS),
                "shocks": [{"shock_id": k, **v} for k, v in SHOCKS.items()],
                "note": "multiplicadores de escenario, no coeficientes "
                        "estimados"}

    def assess(self, agent: dict[str, Any], household: dict[str, Any], *,
               shock_id: str) -> dict[str, Any]:
        shock = SHOCKS.get(shock_id)
        if shock is None:
            raise ResilienceError(
                f"shock desconocido: {shock_id}; disponibles {sorted(SHOCKS)}")
        state = agent.get("state", {}).get("payload", {})
        capital = float(state.get("capital_usd", 0.0))
        crops = list(state.get("crops", []))
        rainfed = not state.get("irrigated", False)
        exposure_components = {
            "rainfed": 0.25 if rainfed else 0.0,
            "single_crop": 0.15 if len(crops) <= 1 else 0.0,
            "low_capital": 0.15 if capital < 1000 else 0.0,
            "low_market_access": 0.10 if float(
                state.get("market_access", 0.0)) < 0.3 else 0.0,
            "no_credit": 0.10 if float(
                state.get("credit_access", 0.0)) < 0.2 else 0.0,
        }
        exposure = _clip01(sum(exposure_components.values()))

        capacity_components = {
            "capital_buffer": 0.25 * _clip01(math.log10(capital + 1) / 5.0),
            "credit": 0.20 * _clip01(state.get("credit_access", 0.0)),
            "irrigation": 0.20 if state.get("irrigated", False) else 0.0,
            "diversification": 0.15 * _clip01(len(crops) / 4.0),
            "information": 0.10 * _clip01(state.get("info_access", 0.0)),
            "cooperative": 0.10 if state.get("cooperative", False) else 0.0,
        }
        capacity = _clip01(sum(capacity_components.values()))

        impact = _clip01(shock["severity"] * (0.5 + 0.5 * exposure)
                         * (1.0 - 0.7 * capacity))
        outcome = next(label for limit, label in OUTCOME_CLASSES
                       if impact < limit)

        shares = (household or {}).get("income_shares", {})
        options = []
        if capital >= 1000:
            options.append("usar_ahorros")
        if float(state.get("credit_access", 0.0)) >= 0.4:
            options.append("crédito")
        if state.get("irrigated", False):
            options.append("riego_complementario")
        if len(crops) > 1:
            options.append("diversificación")
        if float(shares.get("off_farm", 0.0)) >= 0.2:
            options.append("trabajo_fuera_de_la_finca")
        if state.get("cooperative", False):
            options.append("apoyo_de_cooperativa")
        options.append("reducir_insumos")
        if shock_id in {"drought", "excess_rain", "flood"}:
            options.append("ajustar_fecha_de_siembra")

        result = {
            "shock_id": shock_id,
            "shock": shock,
            "agent_id": agent.get("agent_id"),
            "exposure": round(exposure, 3),
            "exposure_components": {k: round(v, 3)
                                    for k, v in exposure_components.items()},
            "adaptive_capacity": round(capacity, 3),
            "capacity_components": {k: round(v, 3)
                                    for k, v in capacity_components.items()},
            "impact_index": round(impact, 3),
            "outcome_class": outcome,
            "production_loss_fraction_scenario": round(
                impact * shock["loss_factor"] * 2.0, 3),
            "coping_options": options,
            "recovery_steps": int(math.ceil(impact * 6)),
            "is_official_vulnerability": False,
            "is_prediction": False,
        }
        return SG.synthetic_envelope(
            ENGINE, result=result,
            assumptions=[
                "los multiplicadores de shock son supuestos de escenario",
                "la exposición y la capacidad son índices aditivos declarados",
                "el hogar solo aporta opciones de ingreso, no montos",
            ],
            limitations=[
                "no es una clasificación oficial de vulnerabilidad",
                "no hay datos de pérdidas ni de recuperación observada",
                "el índice no tiene validación empírica",
                "no se modela ayuda institucional ni seguros",
            ],
            sources=["agrosv_scenario"],
            scenario_id=agent.get("state", {}).get("scenario_id"),
            query={"shock_id": shock_id, "agent_id": agent.get("agent_id")},
        )

    def compare(self, agents: list[dict[str, Any]],
                households: dict[str, dict[str, Any]], *,
                shock_id: str) -> dict[str, Any]:
        rows = []
        for agent in agents:
            household = households.get(agent["agent_id"], {})
            payload = self.assess(agent, household, shock_id=shock_id)["result"]
            rows.append({
                "agent_id": agent["agent_id"],
                "archetype": agent["archetype"],
                "impact_index": payload["impact_index"],
                "outcome_class": payload["outcome_class"],
                "adaptive_capacity": payload["adaptive_capacity"],
            })
        by_archetype: dict[str, list[float]] = {}
        for row in rows:
            by_archetype.setdefault(row["archetype"], []).append(
                row["impact_index"])
        return {
            "shock_id": shock_id,
            "n": len(rows),
            "mean_impact": round(sum(r["impact_index"] for r in rows)
                                 / len(rows), 3) if rows else None,
            "by_archetype": {k: {"n": len(v),
                                 "mean_impact": round(sum(v) / len(v), 3)}
                             for k, v in by_archetype.items()},
            "rows": rows,
            "synthetic": True,
            "not_a_prediction": True,
        }


__all__ = ["AgriculturalResilienceEngine", "SHOCKS", "ResilienceError",
           "OUTCOME_CLASSES"]
