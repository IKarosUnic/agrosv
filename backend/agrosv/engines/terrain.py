"""AGROSV — Terrain analysis (Fase 5, §3, parte topográfica).

Métricas derivadas del DEM con metodología explícita:

    elevation              muestreo del DEM (m)
    slope                  pendiente de la capa métrica (grados y %)
    aspect                 azimut de máxima pendiente (0=N, 90=E)
    relief_class           clase por umbrales de pendiente (config.RELIEF_BREAKS)
    TRI                    índice de rugosidad del terreno (Riley et al., 1999)
    TPI                    índice de posición topográfica (z0 − media 3×3)
    position               cresta / ladera / valle según TPI y su umbral

Reglas:

* **DSM ≠ DTM.** Copernicus GLO-30 es un modelo de superficie: incluye dosel y
  edificios. La pendiente bajo vegetación densa puede estar sobreestimada y la
  elevación no es la del suelo desnudo.
* **Resolución ≠ precisión.** 30 m es el espaciado de la rejilla; la exactitud
  vertical no se ha validado con puntos de control en este repositorio.
* El TPI y el TRI se calculan en una ventana local (~150 m). No describen una
  forma del terreno a escala de cuenca.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pyproj
import rasterio
from rasterio.windows import Window

from .. import config as C

#: Umbral de TPI (m) para clasificar posición topográfica en una ventana 3×3.
#: Es una convención declarada, no una norma universal: otros umbrales producen
#: otras proporciones de crestas y valles.
TPI_FLAT_M = 0.5
TPI_RIDGE_M = 2.0
TPI_VALLEY_M = -2.0

RELIEF_LABELS = {i: label for i, (_, _, label) in enumerate(C.RELIEF_BREAKS)}


@dataclass
class TerrainWindow:
    elevation: np.ndarray
    row: int
    col: int
    res_m: float
    crs: str
    radius_cells: int

    @property
    def center(self) -> float | None:
        value = float(self.elevation[self.row, self.col])
        return value if math.isfinite(value) else None


def _sample(path, lon: float, lat: float) -> float | None:
    """Muestreo puntual por vecino más cercano, aplicando escala declarada."""
    if not path.exists():
        return None
    with rasterio.open(path) as ds:
        transformer = pyproj.Transformer.from_crs(C.CRS_STORAGE, ds.crs,
                                                  always_xy=True)
        x, y = transformer.transform(lon, lat)
        try:
            row, col = ds.index(x, y)
        except Exception:  # noqa: BLE001 — fuera de la extensión
            return None
        if not (0 <= row < ds.height and 0 <= col < ds.width):
            return None
        value = ds.read(1, window=Window(col, row, 1, 1), masked=True)
        if value.size == 0 or np.ma.is_masked(value[0, 0]):
            return None
        raw = float(value[0, 0])
        if not math.isfinite(raw):
            return None
        if ds.nodata is not None and raw == float(ds.nodata):
            return None
        scale = ds.scales[0] if ds.scales else 1.0
        return raw * float(scale)


def sample_elevation(lon: float, lat: float) -> float | None:
    return _sample(C.DEM_WGS84, lon, lat)


def sample_slope_deg(lon: float, lat: float) -> float | None:
    return _sample(C.SLOPE, lon, lat)


def sample_aspect_deg(lon: float, lat: float) -> float | None:
    return _sample(C.ASPECT, lon, lat)


def sample_relief_class(lon: float, lat: float) -> int | None:
    value = _sample(C.RELIEF_CLASS, lon, lat)
    return int(round(value)) if value is not None else None


def slope_pct(slope_deg: float | None) -> float | None:
    """Pendiente en % = tan(grados)·100 (no es un factor de conversión lineal)."""
    if slope_deg is None:
        return None
    return round(math.tan(math.radians(slope_deg)) * 100.0, 2)


def relief_class_of(slope_deg: float | None) -> dict[str, Any] | None:
    if slope_deg is None:
        return None
    for code, (lo, hi, label) in enumerate(C.RELIEF_BREAKS):
        if lo <= slope_deg < hi:
            return {"code": code, "label": label, "min_deg": lo, "max_deg": hi}
    return {"code": None, "label": "sin_clase", "min_deg": None, "max_deg": None}


def _local_window(lon: float, lat: float, radius_cells: int) -> TerrainWindow:
    """Ventana (2r+1)² del DEM en su rejilla nativa, sin remuestreo."""
    if not 1 <= radius_cells <= 10:
        raise ValueError("radius_cells debe estar entre 1 y 10")
    with rasterio.open(C.DEM_WGS84) as ds:
        x, y = pyproj.Transformer.from_crs(C.CRS_STORAGE, ds.crs,
                                           always_xy=True).transform(lon, lat)
        row, col = ds.index(x, y)
        window = Window(col - radius_cells, row - radius_cells,
                        2 * radius_cells + 1, 2 * radius_cells + 1)
        window = window.intersection(Window(0, 0, ds.width, ds.height))
        data = ds.read(1, window=window, masked=True).astype("float64")
        if np.ma.isMaskedArray(data):
            data = data.filled(np.nan)
        if ds.nodata is not None:
            data[data == float(ds.nodata)] = np.nan
        # Tamaño de celda aproximado en metros (solo para TRI, que pondera
        # vecinos); la pendiente oficial no usa esta aproximación.
        lat_c = (ds.bounds.bottom + ds.bounds.top) / 2
        res_x_m = abs(ds.res[0]) * 111_320.0 * math.cos(math.radians(lat_c))
        res_y_m = abs(ds.res[1]) * 111_132.0
        # La ventana puede haberse recortado: se guarda la fila/columna reales.
        return TerrainWindow(
            elevation=data,
            row=int(row - int(window.row_off)),
            col=int(col - int(window.col_off)),
            res_m=float((res_x_m + res_y_m) / 2.0),
            crs=str(ds.crs),
            radius_cells=radius_cells,
        )


def tri_riley(elevation: np.ndarray, row: int, col: int, res_m: float) -> float | None:
    """Terrain Ruggedness Index (Riley et al., 1999): √Σ(z_ij − z0)²."""
    if elevation.shape != (3, 3):
        raise ValueError("TRI requiere una ventana 3×3")
    z0 = elevation[row, col]
    if not math.isfinite(z0):
        return None
    total = 0.0
    for r in range(3):
        for c in range(3):
            if r == row and c == col:
                continue
            z = elevation[r, c]
            if not math.isfinite(z):
                return None
            total += (z - z0) ** 2
    return math.sqrt(total)


def tpi(elevation: np.ndarray, row: int, col: int,
        *, radius: int = 1) -> float | None:
    """Índice de posición topográfica: z0 − media del entorno (sin el centro)."""
    size = 2 * radius + 1
    if elevation.shape != (size, size):
        raise ValueError(f"TPI requiere una ventana {size}×{size}")
    z0 = elevation[row, col]
    if not math.isfinite(z0):
        return None
    neighbours = [elevation[r, c] for r in range(size) for c in range(size)
                  if not (r == row and c == col) and math.isfinite(elevation[r, c])]
    if not neighbours:
        return None
    return float(z0 - sum(neighbours) / len(neighbours))


def tpi_position(value: float | None) -> str | None:
    if value is None:
        return None
    if value >= TPI_RIDGE_M:
        return "cresta"
    if value <= TPI_VALLEY_M:
        return "valle"
    if abs(value) <= TPI_FLAT_M:
        return "plano_local"
    return "ladera"


def aspect_compass(aspect_deg: float | None) -> str | None:
    if aspect_deg is None:
        return None
    names = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    idx = int(((aspect_deg % 360) + 22.5) // 45) % 8
    return names[idx]


def terrain_metrics(lon: float, lat: float, *, radius_cells: int = 2
                    ) -> dict[str, Any]:
    """Elevación, pendiente, aspecto, clase, TRI, TPI y posición."""
    elevation = sample_elevation(lon, lat)
    if elevation is None:
        return {
            "available": False,
            "reason": ("el punto no tiene dato en el DEM: fuera de cobertura, "
                       "NoData o en el borde del ráster"),
            "source": "copdem30",
        }
    slope = sample_slope_deg(lon, lat)
    aspect = sample_aspect_deg(lon, lat)
    relief = sample_relief_class(lon, lat)

    window = _local_window(lon, lat, radius_cells)
    z3 = _center_crop(window.elevation, 3)
    row3 = _center_index(window, 3)
    tri = tri_riley(z3, row3, row3, window.res_m) if z3 is not None else None
    tpi_value = tpi(z3, row3, row3) if z3 is not None else None

    return {
        "available": True,
        "query": {"lon": lon, "lat": lat, "radius_cells": radius_cells},
        "elevation_m": round(elevation, 2),
        "slope_deg": round(slope, 2) if slope is not None else None,
        "slope_pct": slope_pct(slope),
        "aspect_deg": round(aspect, 1) if aspect is not None else None,
        "aspect_compass": aspect_compass(aspect),
        "relief_class": relief_class_of(slope) if slope is not None else
        ({"code": relief, "label": RELIEF_LABELS.get(relief, "?")}
         if relief is not None else None),
        "tri_m": round(tri, 2) if tri is not None else None,
        "tpi_m": round(tpi_value, 2) if tpi_value is not None else None,
        "topographic_position": tpi_position(tpi_value),
        "window": {
            "radius_cells": radius_cells,
            "cells": [int(window.elevation.shape[1]),
                      int(window.elevation.shape[0])],
            "approx_cell_m": round(window.res_m, 1),
            "crs": window.crs,
            "extent_m": round(
                window.elevation.shape[0] * window.res_m, 1),
        },
        "methods": {
            "elevation": "muestreo del DEM Copernicus GLO-30 (DSM)",
            "slope": ("diferencias finitas centrales sobre rejilla de 30 m "
                      "EPSG:32616 (Fase 1)"),
            "aspect": ("azimut de máxima pendiente, 0=N, 90=E "
                       "(arctan2(−dz/dx, −dz/dy))"),
            "relief_class": ("umbrales de pendiente declarados en "
                             "config.RELIEF_BREAKS"),
            "tri": "Riley et al. (1999), ventana 3×3, √Σ(z−z0)²",
            "tpi": ("z0 − media de 8 vecinos; cresta ≥ +2 m, valle ≤ −2 m, "
                    "plano local ≤ 0,5 m (convención AGROSV)"),
            "cell_size_for_tri": ("aproximación 111.132 m/grado (N-S) y "
                                  "111.320·cos(lat) m/grado (E-O)"),
        },
        "terrain_classification": {
            "scheme": "clases de relieve por pendiente (AGROSV)",
            "thresholds_deg": [{"label": label, "min": lo, "max": hi}
                               for lo, hi, label in C.RELIEF_BREAKS],
            "documented": True,
            "note": ("una clase de relieve describe pendiente, no uso del "
                     "suelo, fertilidad ni aptitud de cultivo"),
        },
        "source": "copdem30",
        "limitations": [
            "DSM (superficie) ≠ DTM (terreno desnudo): incluye dosel y edificios",
            "resolución de 30 m ≠ exactitud posicional de 30 m",
            "TRI y TPI describen una ventana local de ~150 m, no una cuenca",
            "en zonas planas el aspecto es inestable y puede ser nulo",
        ],
    }


def _center_crop(array: np.ndarray, size: int) -> np.ndarray | None:
    h, w = array.shape
    if size > h or size > w:
        # Se rellena con NaN para conservar la posición del centro; una ventana
        # incompleta no produce métricas inventadas.
        pad = np.full((size, size), np.nan)
        top = (size - h) // 2
        left = (size - w) // 2
        pad[top:top + h, left:left + w] = array
        return pad
    row = (h - size) // 2
    col = (w - size) // 2
    return array[row:row + size, col:col + size]


def _center_index(window: TerrainWindow, size: int) -> int:
    return size // 2


__all__ = [
    "terrain_metrics", "sample_elevation", "sample_slope_deg",
    "sample_aspect_deg", "sample_relief_class", "slope_pct", "relief_class_of",
    "tri_riley", "tpi", "tpi_position", "aspect_compass", "TerrainWindow",
    "TPI_RIDGE_M", "TPI_VALLEY_M", "TPI_FLAT_M",
]
