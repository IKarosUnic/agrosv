"""AGROSV — Fase 6: simulación socio-agrícola integrada (Subsistema C).

Conecta los motores científicos (Subsistema A) con los motores sintéticos
(Subsistema B) sin sustituir cálculos agronómicos por texto generado. No hay
LLM en ninguna ruta de decisión: las restricciones y los cálculos son
deterministas y auditables.
"""
from __future__ import annotations

__all__ = ["integration", "decision", "scenario", "analysis", "api"]

_ENGINES = {
    "socio_agricultural_integration": ("integration",
                                       "SocioAgriculturalIntegrationEngine"),
    "agricultural_decision": ("decision", "AgriculturalDecisionEngine"),
    "agricultural_scenario": ("scenario", "AgriculturalScenarioEngine"),
    "socio_agricultural_analysis": ("analysis",
                                    "SocioAgriculturalAnalysisEngine"),
}


def get_engine(name: str):
    import importlib

    key = name.strip().lower()
    if key not in _ENGINES:
        raise KeyError(f"motor socio-agrícola desconocido: {name}; "
                       f"disponibles {sorted(_ENGINES)}")
    module_name, class_name = _ENGINES[key]
    module = importlib.import_module(f".{module_name}", __name__)
    return getattr(module, class_name)()
