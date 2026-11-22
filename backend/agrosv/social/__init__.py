"""AGROSV — Fase 6: inteligencia socio-agrícola sintética (Subsistema B).

Cinco capas que **nunca** se fusionan:

    SOURCE_PROFILE              perfil de origen (Nemotron o esquema compatible)
    SYNTHETIC_AGRICULTURAL_STATE variables agrícolas generadas por AGROSV
    HOUSEHOLD_STATE             hogar sintético y sus recursos
    SIMULATION_HISTORY          decisiones, interacciones y resultados
    OBSERVED_VALIDATION_DATA    evidencia real independiente (no generada)

Toda persona es sintética. Ningún registro representa a una persona real ni
permite inferir distribuciones poblacionales.
"""
from __future__ import annotations

__all__ = [
    "governance", "population", "persona", "household", "behavior",
    "economy", "adoption", "resilience", "multiagent", "api",
]

_ENGINES = {
    "agricultural_population": ("population", "AgriculturalPopulationEngine"),
    "agricultural_persona": ("persona", "AgriculturalPersonaEngine"),
    "agricultural_household": ("household", "AgriculturalHouseholdEngine"),
    "farmer_behavior": ("behavior", "FarmerBehaviorEngine"),
    "agricultural_economy": ("economy", "AgriculturalEconomyEngine"),
    "technology_adoption": ("adoption", "TechnologyAdoptionEngine"),
    "agricultural_resilience": ("resilience", "AgriculturalResilienceEngine"),
    "agricultural_multiagent": ("multiagent", "AgriculturalMultiAgentEngine"),
}


def get_engine(name: str):
    import importlib

    key = name.strip().lower()
    if key not in _ENGINES:
        raise KeyError(f"motor social desconocido: {name}; "
                       f"disponibles {sorted(_ENGINES)}")
    module_name, class_name = _ENGINES[key]
    module = importlib.import_module(f".{module_name}", __name__)
    return getattr(module, class_name)()
