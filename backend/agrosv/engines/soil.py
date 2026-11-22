"""AGROSV — SoilEngine (Fase 5, §4).

Qué responde: textura, pH, carbono y nitrógeno del suelo en un punto, con su
clase textural USDA, las limitaciones agrícolas que se siguen **por reglas
declaradas** y la comparación entre fuentes disponibles.

Qué no responde, y por qué:

* **No hay perfiles por horizonte.** La única profundidad integrada es 0–30 cm
  (media ponderada 5/30–10/30–15/30 de SoilGrids). El modelo de perfil declara
  los intervalos 5–15, 15–30, 30–60, 60–100 y 100–200 cm como ausentes.
* **No es medición.** SoilGrids 2.0 es una predicción global de machine
  learning a 250 m. No se mezcla con una muestra de laboratorio sin declararlo
  y no se presenta como equivalente al Mapa Digital de Suelos del CENTA, que
  está restringido.
* **No hay profundidad efectiva, densidad aparente, fragmentos gruesos, CEC,
  agua disponible ni salinidad.** Se declaran ausentes; no se estiman por
  pedotransferencia sin los insumos y la validación que eso exigiría.

La materia orgánica se calcula solo con un factor documentado (Van Bemmelen,
1,724) y se etiqueta como derivada, nunca como medición.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
import pyproj
import rasterio
from rasterio.windows import Window

from .. import config as C
from . import governance as G

ENGINE = "soil"
ENGINE_VERSION = G.ENGINE_VERSION

#: Intervalos de profundidad normalizados por AGROSV (cm).
DEPTH_INTERVALS: tuple[tuple[int, int], ...] = (
    (0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200),
)

#: Factor de Van Bemmelen: materia orgánica = carbono orgánico × 1,724.
#: Es una convención empírica; el rango publicado habitual es 1,7–2,0.
VAN_BEMMELEN = 1.724

SOIL_VARIABLES: dict[str, dict[str, Any]] = {
    "clay": {"file": "clay_0-30cm.tif", "unit": "%", "variable": "clay",
             "label": "arcilla"},
    "sand": {"file": "sand_0-30cm.tif", "unit": "%", "variable": "sand",
             "label": "arena"},
    "silt": {"file": "silt_0-30cm.tif", "unit": "%", "variable": "silt",
             "label": "limo"},
    "ph": {"file": "phh2o_0-30cm.tif", "unit": "", "variable": "ph",
           "label": "pH (H2O)"},
    "soil_organic_carbon": {"file": "soc_0-30cm.tif", "unit": "g kg-1",
                            "variable": "soil_organic_carbon",
                            "label": "carbono orgánico"},
    "soil_nitrogen": {"file": "nitrogen_0-30cm.tif", "unit": "g kg-1",
                      "variable": "soil_nitrogen", "label": "nitrógeno total"},
}


def _sample(path, lon: float, lat: float) -> tuple[float | None, dict[str, Any]]:
    """Muestreo puntual con escala y NoData declarados por el propio archivo."""
    if not path.exists():
        return None, {"available": False, "reason": "archivo ausente",
                      "path": str(path)}
    with rasterio.open(path) as ds:
        transformer = pyproj.Transformer.from_crs(C.CRS_STORAGE, ds.crs,
                                                  always_xy=True)
        x, y = transformer.transform(lon, lat)
        try:
            row, col = ds.index(x, y)
        except Exception:  # noqa: BLE001
            return None, {"available": False, "reason": "fuera de extensión"}
        if not (0 <= row < ds.height and 0 <= col < ds.width):
            return None, {"available": False, "reason": "fuera de extensión"}
        value = ds.read(1, window=Window(col, row, 1, 1), masked=True)
        meta = {
            "available": True,
            "crs": str(ds.crs),
            "res": [abs(ds.res[0]), abs(ds.res[1])],
            "nodata": ds.nodata,
            "scale": float(ds.scales[0]) if ds.scales else 1.0,
            "cell": {"row": int(row), "col": int(col)},
        }
        if value.size == 0 or np.ma.is_masked(value[0, 0]):
            meta["available"] = False
            meta["reason"] = "celda NoData (agua, costa o fuera de la máscara)"
            return None, meta
        raw = float(value[0, 0])
        if not math.isfinite(raw) or (ds.nodata is not None
                                      and raw == float(ds.nodata)):
            meta["available"] = False
            meta["reason"] = "NoData"
            return None, meta
        return raw * meta["scale"], meta


def usda_texture_class(sand: float, silt: float, clay: float) -> str:
    """Clase textural USDA a partir de arena, limo y arcilla (%).

    Implementa las fronteras de la clase textural del USDA-NRCS en orden de
    especificidad. Si la suma no es 100 ± 5 o ninguna regla aplica, devuelve
    ``"sin_clasificar"`` en lugar de forzar una clase.
    """
    total = sand + silt + clay
    if not (95 <= total <= 105):
        return "sin_clasificar"
    s, si, c = sand, silt, clay
    if c >= 40 and si >= 40:
        return "arcilla limosa"
    if c >= 40 and s <= 45:
        return "arcilla"
    if c >= 35 and s >= 45:
        return "arcilla arenosa"
    if 27 <= c < 40 and s <= 20:
        return "franco arcillo-limoso"
    if 27 <= c < 40 and 20 < s <= 45:
        return "arcilla franca"
    if 20 <= c < 35 and si < 28 and s > 45:
        return "franco arcillo-arenoso"
    if 20 <= c < 35 and si >= 28:
        return "franco arcilloso" if si < 40 else "franco arcillo-limoso"
    if si >= 80 and c < 12:
        return "limo"
    if si >= 50 and c < 12:
        return "franco limoso"
    if si >= 50 and c < 27:
        return "franco limoso"
    if 7 <= c < 27 and 28 <= si < 50 and 23 <= s <= 52:
        return "franco"
    if s >= 85 and c < 10 and si <= 15:
        return "arena"
    if s >= 70 and c < 15 and si <= 30:
        return "arena franca"
    if c < 20 and s > 52:
        return "franco arenoso"
    if c < 7 and si < 50 and s > 43:
        return "franco arenoso"
    return "sin_clasificar"


def profile_model() -> dict[str, Any]:
    """Modelo de perfil con intervalos estandarizados y su disponibilidad real."""
    intervals = []
    for top, bottom in DEPTH_INTERVALS:
        available = top == 0 and bottom == 30
        intervals.append({
            "top_cm": top,
            "bottom_cm": bottom,
            "midpoint_cm": round((top + bottom) / 2, 1),
            "status": "available" if available else "not_available",
            "source": "soilgrids_2" if available else None,
            "reason": None if available else (
                "SoilGrids se descargó agregado a 0–30 cm; no hay capa para "
                "este intervalo y no se interpola entre profundidades"),
        })
    return {
        "standard_intervals_cm": [list(iv) for iv in DEPTH_INTERVALS],
        "intervals": intervals,
        "available_intervals": [iv for iv, s in zip(DEPTH_INTERVALS, intervals)
                                if s["status"] == "available"],
        "depth_weighting": "media 0–30 cm con pesos 5/30, 10/30 y 15/30",
        "rule": ("no se inventa una propiedad a una profundidad que no se "
                 "descargó ni se mide"),
    }


def organic_matter(soc_g_kg: float | None) -> dict[str, Any] | None:
    """Materia orgánica estimada con factor de Van Bemmelen, declarado."""
    if soc_g_kg is None:
        return None
    percent = soc_g_kg * VAN_BEMMELEN / 10.0
    return {
        "value": round(percent, 2),
        "unit": "%",
        "method": f"SOC (g/kg) × {VAN_BEMMELEN} / 10",
        "factor": VAN_BEMMELEN,
        "factor_range": [1.7, 2.0],
        "label": "derivado",
        "note": ("conversión empírica, no una medición de materia orgánica; "
                 "con factor 1,7–2,0 el valor cambia ±8 %"),
    }


# --- reglas de limitación ----------------------------------------------------
# Reglas declaradas: cada una produce un hallazgo con umbral y consecuencia.
# No hay puntuación agregada ni ponderaciones arbitrarias.
LIMITATION_RULES: tuple[dict[str, Any], ...] = (
    {
        "code": "acidez_fuerte",
        "variable": "ph",
        "test": lambda v: v < 5.5,
        "threshold": 5.5,
        "implication": ("acidez que puede limitar la disponibilidad de fósforo "
                        "y aumentar la toxicidad de aluminio; requiere "
                        "verificación con análisis de laboratorio"),
    },
    {
        "code": "acidez_moderada",
        "variable": "ph",
        "test": lambda v: 5.5 <= v < 6.0,
        "threshold": "5,5–6,0",
        "implication": "acidez moderada; puede requerir encalado según cultivo",
    },
    {
        "code": "alcalinidad",
        "variable": "ph",
        "test": lambda v: v > 7.8,
        "threshold": 7.8,
        "implication": ("pH alcalino: posible menor disponibilidad de "
                        "micronutrientes; verificar carbonatos"),
    },
    {
        "code": "arcilla_alta",
        "variable": "clay",
        "test": lambda v: v >= 35.0,
        "threshold": 35.0,
        "implication": ("textura arcillosa: riesgo de compactación, laboreo "
                        "dificultoso y drenaje lento; la clase textural se "
                        "deriva de una predicción"),
    },
    {
        "code": "arena_alta",
        "variable": "sand",
        "test": lambda v: v >= 70.0,
        "threshold": 70.0,
        "implication": ("textura arenosa: baja retención de agua y nutrientes; "
                        "la capacidad de agua disponible no se calculó"),
    },
    {
        "code": "carbono_organico_bajo",
        "variable": "soil_organic_carbon",
        "test": lambda v: v < 10.0,
        "threshold": 10.0,
        "implication": ("carbono orgánico bajo para 0–30 cm: menor estructura "
                        "y fertilidad potencial; no es un diagnóstico agronómico"),
    },
    {
        "code": "ph_fuera_de_rango",
        "variable": "ph",
        "test": lambda v: v < 3.5 or v > 10.0,
        "threshold": "3,5–10,0",
        "implication": ("valor de pH extremo: revisar antes de usarlo; puede "
                        "ser un artefacto de predicción o de escala"),
    },
)

LIMITATION_CONFIDENCE = {
    "soilgrids_2": "baja",
}


def evaluate_limitations(values: dict[str, float | None]) -> list[dict[str, Any]]:
    """Aplica las reglas declaradas. Devuelve hallazgos, nunca un puntaje."""
    findings: list[dict[str, Any]] = []
    for rule in LIMITATION_RULES:
        value = values.get(rule["variable"])
        if value is None:
            continue
        if rule["test"](value):
            findings.append({
                "code": rule["code"],
                "variable": rule["variable"],
                "value": value,
                "threshold": rule["threshold"],
                "implication": rule["implication"],
                "evidence_class": "modeled_prediction",
                "confidence": "baja",
                "rule": (f"{rule['variable']} {rule['threshold']} — regla "
                         "declarada en SoilEngine.LIMITATION_RULES"),
                "caveat": ("una regla sobre una predicción global no es un "
                           "diagnóstico de campo ni una recomendación"),
            })
    return findings


def compare_sources(values: dict[str, float | None]) -> dict[str, Any]:
    """Comparación entre fuentes de suelo. Hoy solo hay una utilizable."""
    available = [{
        "dataset_id": "soilgrids_2",
        "role": "predicción global 250 m, 0–30 cm",
        "variables": [k for k, v in values.items()
                      if v is not None and k in SOIL_VARIABLES],
        "evidence_class": "modeled_prediction",
    }]
    unavailable = [{
        "dataset_id": "centa_suelos",
        "role": "cartografía nacional de suelos (referencia local)",
        "status": "RESTRICTED",
        "reason": ("sin acceso ni licencia verificados: no se usa y no se "
                   "presenta como si existiera"),
    }]
    return {
        "available_sources": available,
        "unavailable_sources": unavailable,
        "conflicts": [],
        "comparison_possible": False,
        "note": (
            "no se puede comparar una predicción global con una fuente nacional "
            "que no está accesible; por eso no hay detección de conflictos que "
            "mostrar"),
    }


class SoilEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def sample(self, lon: float, lat: float) -> dict[str, Any]:
        values: dict[str, float | None] = {}
        cells: dict[str, Any] = {}
        for key, spec in SOIL_VARIABLES.items():
            path = C.SOILS_RASTER_DIR / spec["file"]
            value, meta = _sample(path, lon, lat)
            values[key] = value
            cells[key] = meta

        texture = None
        sand, silt, clay = values.get("sand"), values.get("silt"), values.get("clay")
        if None not in (sand, silt, clay):
            texture = {
                "sand_pct": round(sand, 1),
                "silt_pct": round(silt, 1),
                "clay_pct": round(clay, 1),
                "sum_pct": round(sand + silt + clay, 1),
                "usda_class": usda_texture_class(sand, silt, clay),
                "method": "triángulo textural USDA-NRCS sobre predicción 250 m",
                "caveat": ("la clase textural se calcula sobre porcentajes "
                           "predichos; el redondeo del ráster (±0,05 %) puede "
                           "mover una celda de clase cerca de una frontera"),
            }
        om = organic_matter(values.get("soil_organic_carbon"))
        limitations = evaluate_limitations(values)
        result = {
            "query": {"lon": lon, "lat": lat},
            "depth_interval_cm": [0, 30],
            "properties": {
                key: {
                    "value": (round(v, 3) if v is not None else None),
                    "unit": SOIL_VARIABLES[key]["unit"],
                    "label": SOIL_VARIABLES[key]["label"],
                    "evidence_class": "modeled_prediction",
                    "dataset_id": "soilgrids_2",
                    "cell": cells[key],
                    "available": v is not None,
                } for key, v in values.items()
            },
            "derived": {
                "organic_matter": om,
                "texture_class": texture,
            },
            "limitations_found": limitations,
            "profile": profile_model(),
            "comparison": compare_sources(values),
            "not_available": {k: G.UNAVAILABLE[k] for k in (
                "soil_profile_by_horizon", "soil_depth", "soil_bulk_density",
                "soil_coarse_fragments", "soil_cec", "soil_awc",
                "soil_salinity", "soil_national_map")},
            "interpretation_rule": (
                "las limitaciones son reglas declaradas sobre una predicción "
                "global; no constituyen un índice de aptitud ni una "
                "recomendación agronómica"),
        }
        return G.envelope(
            ENGINE,
            result=result,
            sources=["soilgrids_2"],
            limitations=[
                "SoilGrids es una predicción de machine learning a 250 m, no una "
                "medición de laboratorio",
                "solo existe la profundidad 0–30 cm",
                "no hay CEC, densidad aparente, fragmentos gruesos, agua "
                "disponible ni salinidad",
                "la fuente nacional CENTA está restringida: no se compara",
                "las limitaciones son reglas, no un índice de aptitud",
            ],
            processing=[
                G.step("muestreo de 6 propiedades 0–30 cm",
                       "agrosv.engines.soil._sample"),
                G.step("clase textural USDA", "usda_texture_class"),
                G.step("reglas de limitación", "evaluate_limitations"),
            ],
            query={"lon": lon, "lat": lat},
            coverage=G.coverage_statement()["soils"],
        )

    def profile_model(self) -> dict[str, Any]:
        return profile_model()

    def limitations(self, lon: float, lat: float) -> dict[str, Any]:
        sample = self.sample(lon, lat)
        return {
            "query": sample["query"],
            "findings": sample["result"]["limitations_found"],
            "rules": LIMITATION_RULES and [
                {k: v for k, v in rule.items() if k != "test"}
                for rule in LIMITATION_RULES],
            "not_an_index": True,
            "sources": sample["sources"],
            "limitations": sample["limitations"],
        }

    def texture(self, lon: float, lat: float) -> dict[str, Any]:
        sample = self.sample(lon, lat)
        return {
            "query": sample["query"],
            "texture": sample["result"]["derived"]["texture_class"],
            "properties": {k: sample["result"]["properties"][k]
                           for k in ("sand", "silt", "clay")},
            "sources": sample["sources"],
            "limitations": sample["limitations"],
        }


__all__ = [
    "SoilEngine", "usda_texture_class", "profile_model", "organic_matter",
    "evaluate_limitations", "LIMITATION_RULES", "DEPTH_INTERVALS",
    "VAN_BEMMELEN",
]
