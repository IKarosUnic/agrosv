"""AGROSV — Fase 6: inteligencia agrícola (Subsistema A).

Módulos:

    governance      fichas de fuente y envoltura de respuesta §8
    catalog         CropKnowledgeEngine y catálogo de cultivos
    phenology       CropPhenologyEngine (tiempo térmico)
    suitability     CropSuitabilityEngine (FAO AEZ simplificado)
    water_nutrient  CropWaterNutrientEngine (FAO-56, demanda de nutrientes)
    simulation      CropSimulationEngine y adaptadores externos
    calendar        AgriculturalCalendarEngine
    api             router `/api/agriculture`

Las importaciones pesadas (clima, suelo, terreno) son perezosas: el catálogo y
las reglas se pueden usar sin rasterio.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "governance", "catalog", "phenology", "suitability", "water_nutrient",
    "simulation", "calendar", "api", "get_engine",
]

_ENGINES = {
    "crop_knowledge": ("catalog", "CropKnowledgeEngine"),
    "crop_phenology": ("phenology", "CropPhenologyEngine"),
    "crop_suitability": ("suitability", "CropSuitabilityEngine"),
    "crop_water_nutrient": ("water_nutrient", "CropWaterNutrientEngine"),
    "crop_simulation": ("simulation", "CropSimulationEngine"),
    "agricultural_calendar": ("calendar", "AgriculturalCalendarEngine"),
}


def get_engine(name: str) -> Any:
    key = name.strip().lower()
    if key not in _ENGINES:
        raise KeyError(f"motor agrícola desconocido: {name}; "
                       f"disponibles {sorted(_ENGINES)}")
    module_name, class_name = _ENGINES[key]
    import importlib

    module = importlib.import_module(f".{module_name}", __name__)
    return getattr(module, class_name)()
