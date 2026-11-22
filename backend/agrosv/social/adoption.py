"""AGROSV — TechnologyAdoptionEngine (§5.7).

Índice de propensión a la adopción, **no** una probabilidad ni una tasa
nacional. Cada tecnología declara requisitos cualitativos y un costo relativo;
no se publican precios de equipos porque no hay fuente verificada.

Barreras evaluadas: capital, conocimiento, agua, superficie, mantenimiento,
alfabetización digital y acceso a mercado. Una barrera dura (agua o superficie)
lleva la propensión a 0 y la decisión a `not_feasible`.
"""
from __future__ import annotations

from typing import Any

from . import governance as SG

ENGINE = "technology_adoption"
ENGINE_VERSION = SG.ENGINE_VERSION

CAPITAL_CLASSES = {"low": 1000.0, "medium": 10000.0, "high": float("inf")}

TECHNOLOGIES: dict[str, dict[str, Any]] = {
    "drip_irrigation": {
        "label": "Riego por goteo",
        "capital_class": "high", "knowledge": 0.55, "water_access": True,
        "land_min_ha": 0.2, "maintenance": 0.55, "digital": 0.20,
        "market_access": 0.30,
        "barriers": ["inversión inicial", "conocimiento técnico",
                     "mantenimiento", "fuente de agua"],
    },
    "improved_seed": {
        "label": "Semilla mejorada",
        "capital_class": "low", "knowledge": 0.30, "water_access": False,
        "land_min_ha": 0.1, "maintenance": 0.10, "digital": 0.0,
        "market_access": 0.20,
        "barriers": ["acceso a semilla certificada", "costo recurrente"],
    },
    "soil_testing": {
        "label": "Análisis de suelo",
        "capital_class": "low", "knowledge": 0.45, "water_access": False,
        "land_min_ha": 0.1, "maintenance": 0.05, "digital": 0.10,
        "market_access": 0.20,
        "barriers": ["acceso a laboratorio", "interpretación", "costo"],
    },
    "agricultural_sensors": {
        "label": "Sensores agrícolas",
        "capital_class": "high", "knowledge": 0.70, "water_access": False,
        "land_min_ha": 0.5, "maintenance": 0.60, "digital": 0.60,
        "market_access": 0.20,
        "barriers": ["inversión", "conectividad", "conocimiento digital"],
    },
    "digital_advisory": {
        "label": "Servicios digitales de asesoría",
        "capital_class": "low", "knowledge": 0.30, "water_access": False,
        "land_min_ha": 0.0, "maintenance": 0.15, "digital": 0.50,
        "market_access": 0.0,
        "barriers": ["conectividad", "alfabetización digital", "confianza"],
    },
    "mechanization": {
        "label": "Mecanización",
        "capital_class": "high", "knowledge": 0.60, "water_access": False,
        "land_min_ha": 2.0, "maintenance": 0.65, "digital": 0.10,
        "market_access": 0.30,
        "barriers": ["inversión", "tamaño de parcela", "mantenimiento"],
    },
    "protected_agriculture": {
        "label": "Agricultura protegida (macrotúnel/invernadero)",
        "capital_class": "high", "knowledge": 0.65, "water_access": True,
        "land_min_ha": 0.05, "maintenance": 0.50, "digital": 0.15,
        "market_access": 0.45,
        "barriers": ["inversión", "conocimiento", "mercado"],
    },
    "climate_services": {
        "label": "Servicios de información climática",
        "capital_class": "low", "knowledge": 0.25, "water_access": False,
        "land_min_ha": 0.0, "maintenance": 0.05, "digital": 0.40,
        "market_access": 0.0,
        "barriers": ["acceso", "confianza", "conectividad"],
    },
    "soil_conservation": {
        "label": "Prácticas de conservación de suelo",
        "capital_class": "low", "knowledge": 0.40, "water_access": False,
        "land_min_ha": 0.1, "maintenance": 0.20, "digital": 0.0,
        "market_access": 0.0,
        "barriers": ["conocimiento", "mano de obra", "resultados a largo plazo"],
    },
}


class AdoptionError(ValueError):
    pass


def capital_class(capital_usd: float) -> str:
    for name, limit in CAPITAL_CLASSES.items():
        if capital_usd < limit:
            return name
    return "high"


class TechnologyAdoptionEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def technologies(self) -> dict[str, Any]:
        return {
            "count": len(TECHNOLOGIES),
            "technologies": [{"technology_id": k, **v,
                              "cost_values_published": False}
                             for k, v in TECHNOLOGIES.items()],
            "note": ("requisitos cualitativos; no hay precios de equipos "
                     "verificados en el repositorio"),
        }

    def _rank(self, cls: str) -> int:
        return {"low": 0, "medium": 1, "high": 2}[cls]

    def evaluate(self, agent: dict[str, Any], technology_id: str, *,
                 threshold: float = 0.55) -> dict[str, Any]:
        spec = TECHNOLOGIES.get(technology_id)
        if spec is None:
            raise AdoptionError(
                f"tecnología desconocida: {technology_id}; "
                f"disponibles {sorted(TECHNOLOGIES)}")
        state = agent.get("state", {}).get("payload", {})
        capital = float(state.get("capital_usd", 0.0))
        agent_class = capital_class(capital)
        land = float(state.get("area_ha", 0.0))
        info = float(state.get("info_access", 0.0))
        digital = float(state.get("digital_literacy", 0.0))
        market = float(state.get("market_access", 0.0))
        experience = min(1.0, float(state.get("experience_years", 0)) / 30.0)

        hard, soft = [], []
        gap = self._rank(spec["capital_class"]) - self._rank(agent_class)
        if gap > 0:
            hard.append({"barrier": "capital", "severity": 1.0,
                         "detail": f"requiere clase {spec['capital_class']}, "
                                   f"agente {agent_class}"})
        elif gap == 0:
            soft.append({"barrier": "capital", "severity": 0.35,
                         "detail": "capital en el límite de la clase"})
        if spec["water_access"] and not state.get("irrigated", False):
            hard.append({"barrier": "agua", "severity": 1.0,
                         "detail": "requiere acceso a riego declarado"})
        if land < spec["land_min_ha"]:
            hard.append({"barrier": "superficie", "severity": 1.0,
                         "detail": f"requiere ≥ {spec['land_min_ha']} ha"})
        knowledge_gap = max(0.0, spec["knowledge"] - min(1.0, info + 0.3
                                                        * experience))
        if knowledge_gap > 0:
            soft.append({"barrier": "conocimiento",
                         "severity": round(knowledge_gap, 3),
                         "detail": "conocimiento/experiencia insuficiente"})
        soft.append({"barrier": "mantenimiento", "severity": spec["maintenance"],
                     "detail": "carga de mantenimiento declarada"})
        digital_gap = max(0.0, spec["digital"] - digital)
        if digital_gap > 0:
            soft.append({"barrier": "alfabetización digital",
                         "severity": round(digital_gap, 3), "detail": None})
        market_gap = max(0.0, spec["market_access"] - market)
        if market_gap > 0:
            soft.append({"barrier": "mercado", "severity": round(market_gap, 3),
                         "detail": None})

        if hard:
            propensity = 0.0
            decision = "not_feasible"
        else:
            penalty = sum(b["severity"] for b in soft) / max(len(soft), 1)
            propensity = round(max(0.0, min(1.0, 1.0 - 0.7 * penalty)), 3)
            decision = ("consider_adoption" if propensity >= threshold
                        else "not_now")
        result = {
            "technology_id": technology_id,
            "technology": spec["label"],
            "agent_id": agent.get("agent_id"),
            "adoption_propensity": propensity,
            "decision": decision,
            "threshold": threshold,
            "hard_barriers": hard,
            "soft_barriers": soft,
            "agent_context": {"capital_usd": capital,
                              "capital_class": agent_class,
                              "area_ha": land,
                              "irrigated": bool(state.get("irrigated", False))},
            "is_probability": False,
            "is_national_rate": False,
        }
        return SG.synthetic_envelope(
            ENGINE, result=result,
            assumptions=[
                "los requisitos son cualitativos y definidos por AGROSV",
                "no hay costos de equipo ni curvas de adopción observadas",
                "la propensión es un índice, no una probabilidad",
            ],
            limitations=[
                "no predice adopción real ni tasas nacionales",
                "los umbrales de clase de capital son supuestos",
                "no se modela crédito, extensión ni política pública",
            ],
            sources=["agrosv_scenario"],
            query={"technology_id": technology_id,
                   "agent_id": agent.get("agent_id")},
        )


__all__ = ["TechnologyAdoptionEngine", "TECHNOLOGIES", "AdoptionError",
           "capital_class", "CAPITAL_CLASSES"]
