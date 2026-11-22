"""AGROSV — motores territoriales y ambientales (Fase 5).

Cinco motores ejecutables sobre los datos verificados de Fase 1–4:

    territorial   identificación administrativa, topografía, cuenca asociada
    terrain       elevación, pendiente, aspecto, TRI, TPI, clase de relieve
    soil          propiedades 0–30 cm, textura USDA, limitaciones por regla
    hydrology     agua superficial mapeada, cuenca D8, balance P−ET0, subterránea
    climate       climatología del período, rachas, extremos ETCCDI, sequía
    environmental composición de los anteriores, sin índice arbitrario

Las importaciones son perezosas a propósito: `agrosv.api` monta el router sin
cargar geopandas ni rasterio hasta que se consulta un motor.
"""
from __future__ import annotations

from typing import Any

from . import governance

__all__ = [
    "governance", "territorial", "terrain", "soil", "hydrology", "climate",
    "environmental", "api", "cache",
    "get_engine",
]

_ENGINE_MODULES = {
    "territorial": ("territorial", "TerritorialEngine"),
    "soil": ("soil", "SoilEngine"),
    "hydrology": ("hydrology", "HydrologyEngine"),
    "climate": ("climate", "ClimateEngine"),
    "environmental": ("environmental", "EnvironmentalInteractionEngine"),
}


def get_engine(name: str) -> Any:
    """Devuelve una instancia del motor por nombre, importando solo el módulo."""
    key = name.strip().lower()
    if key not in _ENGINE_MODULES:
        raise KeyError(
            f"motor desconocido: {name}; disponibles {sorted(_ENGINE_MODULES)}")
    module_name, class_name = _ENGINE_MODULES[key]
    import importlib

    module = importlib.import_module(f".{module_name}", __name__)
    return getattr(module, class_name)()
