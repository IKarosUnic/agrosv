"""AGROSV — VegetationIndexEngine (Fase 7, §4.2).

Ocho índices espectrales documentados. Cada uno declara fórmula, bandas
requeridas, sensores compatibles, resolución nativa, rango y limitaciones.

Reglas:

* nodata y máscara de nube → NaN, nunca cero (cero es un valor válido);
* denominador nulo → NaN, nunca infinito;
* se recorta a [−1, 1] porque fuera de ese rango la razón normalizada deja de
  describir el índice;
* **ningún índice diagnostica plaga, enfermedad ni deficiencia nutricional.**
  El motor describe la señal (verdor, agua, suelo, fuego) y nada más.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from . import governance as G

ENGINE = "vegetation_index"
ENGINE_VERSION = G.ENGINE_VERSION


def _spec(source_bands: list[str], formula: str, measures: str,
          resolution_m: int, limitations: list[str],
          cannot: list[str], reference: str) -> dict[str, Any]:
    return {
        "formula": formula, "bands": source_bands, "measures": measures,
        "resolution_m": resolution_m, "range": [-1.0, 1.0],
        "limitations": limitations, "cannot_conclude": cannot,
        "reference": reference,
    }


INDEX_SPECS: dict[str, dict[str, Any]] = {
    "ndvi": _spec(
        ["nir", "red"], "(NIR - R) / (NIR + R)",
        "verdour y fenología de la vegetación", 10,
        ["satura en dosel denso", "sensible a suelo desnudo en cobertura baja",
         "píxeles mixtos a 10 m"],
        ["no identifica especie ni cultivo",
         "no diagnostica plaga, enfermedad ni nutrición"],
        "Rouse et al. 1974 (ERTS-1)"),
    "evi": _spec(
        ["nir", "red", "blue"], "2.5·(NIR - R) / (NIR + 6R - 7.5B + 1)",
        "biomasa en coberturas densas", 10,
        ["sensible a aerosoles y corrección atmosférica",
         "requiere banda azul despejada", "puede superar 1 en casos extremos"],
        ["no mide altura ni biomasa directamente"],
        "Huete et al. 1997 (MODIS EVI)"),
    "savi": _spec(
        ["nir", "red"], "((NIR - R) / (NIR + R + L)) · (1 + L)",
        "verdour con corrección por suelo desnudo", 10,
        ["L = 0,5 es una convención; no se ajusta por parcela",
         "reduce pero no elimina el efecto del suelo"],
        ["no corrige sombra de relieve", "no distingue cultivo de maleza"],
        "Huete 1988 (SAVI)"),
    "msavi": _spec(
        ["nir", "red"],
        "(2NIR + 1 - √((2NIR + 1)² - 8(NIR - R))) / 2",
        "verdour con corrección automática de suelo", 10,
        ["la raíz exige 2NIR+1 ≥ 8(NIR-R); fuera de eso el valor es inválido",
         "amplifica ruido cuando la diferencia NIR-R es pequeña"],
        ["no sustituye una clasificación de cobertura"],
        "Qi et al. 1994 (MSAVI2)"),
    "ndwi": _spec(
        ["green", "nir"], "(G - NIR) / (G + NIR)",
        "agua superficial", 10,
        ["no mide humedad del suelo",
         "confunde agua somera con sombra en relieve abrupto"],
        ["no es un índice de estrés hídrico del cultivo"],
        "McFeeters 1996"),
    "ndmi": _spec(
        ["nir", "swir1"], "(NIR - SWIR1) / (NIR + SWIR1)",
        "contenido de agua de la vegetación", 20,
        ["SWIR1 es de 20 m en Sentinel-2: resolución efectiva 20 m",
         "sensible a humedad de suelo desnudo en cobertura baja"],
        ["no mide potencial hídrico ni turgencia",
         "no equivale a humedad de suelo medida"],
        "Gao 1996 (NDWI/NDMI)"),
    "nbr": _spec(
        ["nir", "swir2"], "(NIR - SWIR2) / (NIR + SWIR2)",
        "severidad de incendio y cobertura post-fuego", 20,
        ["SWIR2 es de 20 m en Sentinel-2", "no distingue quema de senescencia"],
        ["no mide daño agrícola por plaga", "no sustituye verificación de campo"],
        "Key & Benson 2006 (NBR)"),
    "ndre": _spec(
        ["nir", "red_edge"], "(NIR - RE) / (NIR + RE)",
        "proxy de clorofila y estrés temprano", 20,
        ["requiere banda red-edge (B05 en Sentinel-2); no existe en Landsat 8/9",
         "sensible a calibración atmosférica", "relación con clorofila no validada "
         "localmente"],
        ["no cuantifica clorofila sin muestras de laboratorio"],
        "Barnes et al. 2000 (NDRE)"),
}

#: Sensores compatibles por índice (bandas realmente disponibles).
SENSOR_BANDS: dict[str, dict[str, dict[str, str]]] = {
    "sentinel2": {
        "nir": "B08", "red": "B04", "blue": "B02", "green": "B03",
        "red_edge": "B05", "swir1": "B11", "swir2": "B12",
    },
    "landsat8": {
        "nir": "B5", "red": "B4", "blue": "B2", "green": "B3",
        "swir1": "B6", "swir2": "B7",
    },
    "modis": {
        "nir": "sur_refl_b02", "red": "sur_refl_b01", "blue": "sur_refl_b03",
        "green": "sur_refl_b04", "swir1": "sur_refl_b06", "swir2": "sur_refl_b07",
    },
}


class IndexError_(G.MonitoringError):
    """Índice desconocido o banda ausente."""


@dataclass
class IndexResult:
    name: str
    values: np.ndarray
    valid_mask: np.ndarray
    formula: str
    bands: list[str]
    resolution_m: int
    sensor: str | None = None

    @property
    def valid_pixels(self) -> int:
        return int(self.valid_mask.sum())

    def stats(self) -> dict[str, Any]:
        vals = self.values[np.isfinite(self.values)]
        return {
            "name": self.name, "formula": self.formula,
            "bands": self.bands, "resolution_m": self.resolution_m,
            "sensor": self.sensor,
            "valid_pixels": int(vals.size),
            "total_pixels": int(self.values.size),
            "valid_fraction": round(vals.size / self.values.size, 6)
            if self.values.size else 0.0,
            "min": float(vals.min()) if vals.size else None,
            "mean": float(vals.mean()) if vals.size else None,
            "max": float(vals.max()) if vals.size else None,
            "nodata_is_zero": False,
        }


def _clean(arr: np.ndarray) -> np.ndarray:
    data = np.ma.asarray(arr, dtype="float32")
    out = np.asarray(data.filled(np.nan), dtype="float32")
    return np.where(np.isfinite(out), out, np.nan).astype("float32")


def _norm(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    n = np.asarray(num, dtype="float32")
    d = np.asarray(den, dtype="float32")
    if n.shape != d.shape:
        raise G.MonitoringError(f"bandas de distinta forma: {n.shape} vs {d.shape}")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = n / d
    out = np.where(np.abs(d) < 1e-6, np.nan, out)
    out = np.where(np.isfinite(out), out, np.nan)
    return np.clip(out, -1.0, 1.0).astype("float32")


def savi(nir: np.ndarray, red: np.ndarray, *, l: float = 0.5) -> np.ndarray:
    if not 0 <= l <= 1:
        raise G.MonitoringError("L de SAVI debe estar en [0, 1]")
    n = np.asarray(nir, dtype="float32")
    r = np.asarray(red, dtype="float32")
    den = n + r + l
    with np.errstate(divide="ignore", invalid="ignore"):
        out = ((n - r) / np.where(np.abs(den) < 1e-6, np.nan, den)) * (1.0 + l)
    return np.clip(np.where(np.isfinite(out), out, np.nan), -1.0, 1.0).astype("float32")


def msavi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    n = np.asarray(nir, dtype="float32")
    r = np.asarray(red, dtype="float32")
    inner = (2.0 * n + 1.0) ** 2 - 8.0 * (n - r)
    with np.errstate(invalid="ignore"):
        out = (2.0 * n + 1.0 - np.sqrt(np.where(inner < 0, np.nan, inner))) / 2.0
    return np.clip(np.where(np.isfinite(out), out, np.nan), -1.0, 1.0).astype("float32")


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    return _norm(np.asarray(nir, "float32") - red,
                 np.asarray(nir, "float32") + red)


def evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    n, r, b = (np.asarray(x, "float32") for x in (nir, red, blue))
    return _norm(2.5 * (n - r), n + 6.0 * r - 7.5 * b + 1.0)


def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    g = np.asarray(green, "float32")
    return _norm(g - nir, g + np.asarray(nir, "float32"))


def ndmi(nir: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    n = np.asarray(nir, "float32")
    return _norm(n - swir1, n + np.asarray(swir1, "float32"))


def nbr(nir: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    n = np.asarray(nir, "float32")
    return _norm(n - swir2, n + np.asarray(swir2, "float32"))


def ndre(nir: np.ndarray, red_edge: np.ndarray) -> np.ndarray:
    n = np.asarray(nir, "float32")
    return _norm(n - red_edge, n + np.asarray(red_edge, "float32"))


_FORMULAS = {
    "ndvi": lambda b: ndvi(b["nir"], b["red"]),
    "evi": lambda b: evi(b["nir"], b["red"], b["blue"]),
    "savi": lambda b: savi(b["nir"], b["red"]),
    "msavi": lambda b: msavi(b["nir"], b["red"]),
    "ndwi": lambda b: ndwi(b["green"], b["nir"]),
    "ndmi": lambda b: ndmi(b["nir"], b["swir1"]),
    "nbr": lambda b: nbr(b["nir"], b["swir2"]),
    "ndre": lambda b: ndre(b["nir"], b["red_edge"]),
}


class VegetationIndexEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def specs(self) -> dict[str, Any]:
        return {"count": len(INDEX_SPECS),
                "indices": {k: dict(v) for k, v in INDEX_SPECS.items()},
                "sensor_bands": SENSOR_BANDS,
                "policy": ("un índice de vegetación describe una señal "
                           "espectral; no identifica cultivo ni diagnostica "
                           "plaga, enfermedad o nutrición")}

    def available_for(self, sensor: str) -> list[str]:
        bands = SENSOR_BANDS.get(sensor)
        if bands is None:
            raise KeyError(f"sensor desconocido: {sensor}; use {sorted(SENSOR_BANDS)}")
        return [name for name, spec in INDEX_SPECS.items()
                if all(b in bands for b in spec["bands"])]

    def compute(self, name: str, bands: Mapping[str, np.ndarray], *,
                cloud_mask: np.ndarray | None = None,
                sensor: str | None = None,
                savi_l: float = 0.5) -> IndexResult:
        key = name.lower()
        if key not in INDEX_SPECS:
            raise IndexError_(f"índice desconocido: {name}; use {sorted(INDEX_SPECS)}")
        spec = INDEX_SPECS[key]
        missing = [b for b in spec["bands"] if b not in bands]
        if missing:
            raise IndexError_(f"{key} requiere las bandas {missing}")
        clean = {b: _clean(bands[b]) for b in spec["bands"]}
        shapes = {arr.shape for arr in clean.values()}
        if len(shapes) != 1:
            raise G.MonitoringError(
                f"bandas de distinta forma en {key}: "
                f"{ {b: a.shape for b, a in clean.items()} }")
        if key == "savi":
            values = savi(clean["nir"], clean["red"], l=savi_l)
        else:
            values = _FORMULAS[key](clean)
        valid = np.isfinite(values)
        if cloud_mask is not None:
            mask = np.asarray(cloud_mask, dtype=bool)
            if mask.shape != values.shape:
                raise G.MonitoringError(
                    f"máscara de nube {mask.shape} no coincide con {values.shape}")
            valid &= mask
        values = np.where(valid, values, np.nan).astype("float32")
        return IndexResult(name=key, values=values, valid_mask=valid,
                           formula=spec["formula"], bands=list(spec["bands"]),
                           resolution_m=int(spec["resolution_m"]), sensor=sensor)

    def describe(self, name: str) -> dict[str, Any]:
        key = name.lower()
        if key not in INDEX_SPECS:
            raise KeyError(f"índice desconocido: {name}")
        return dict(INDEX_SPECS[key]) | {"name": key}

    @staticmethod
    def water_fraction(ndwi: np.ndarray, *, threshold: float = 0.0) -> dict[str, Any]:
        """Fracción de píxeles con NDWI > umbral (convención McFeeters).

        El umbral 0 es una convención de la literatura, no una validación
        local; se declara y se puede cambiar.
        """
        vals = np.asarray(ndwi, dtype="float32")
        valid = np.isfinite(vals)
        if not valid.any():
            return {"fraction": None, "valid_pixels": 0, "threshold": threshold}
        return {"fraction": round(float((vals[valid] > threshold).mean()), 6),
                "valid_pixels": int(valid.sum()), "threshold": threshold,
                "note": "convención de literatura; no validada en campo"}
