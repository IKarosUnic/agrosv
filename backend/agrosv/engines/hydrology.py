"""AGROSV — HydrologyEngine (Fase 5, §5).

Contesta «¿cómo se mueve el agua en este territorio?» con tres bloques
separados, porque no son la misma clase de dato:

A. **Agua superficial mapeada** — cauces y cuerpos de agua de OpenStreetMap.
   Se informa distancia y atributos del elemento más cercano. Un cauce mapeado
   no implica caudal permanente ni agua disponible.
B. **Cuenca derivada del DEM** — D8 sobre una ventana métrica. Es una
   derivación geomorfológica local, **no** una cuenca oficial, y se marca
   `truncated: true` cuando el área aportante toca el borde de la ventana.
C. **Balance hídrico climático** — precipitación y ET0 de reanálisis en el
   punto climático más cercano. El agua que sale de un balance
   precipitación−evapotranspiración no es agua infiltrada, ni recarga, ni agua
   autorizada.

Agua subterránea: **no disponible**. No se infiere acuífero, nivel ni recarga a
partir de la proximidad de un río o de una capa profunda. Las ausencias se
devuelven con su motivo (`governance.UNAVAILABLE`).

Métodos:
  * priority-flood (Barnes et al., 2014) para relleno de depresiones;
  * D8 (O'Callaghan & Mark, 1984);
  * acumulación de flujo y cuenca por recorrido inverso;
  * escorrentía anual estimada por Budyko–Fu (1979/1981) con ω=2 y análisis de
    sensibilidad ω ∈ {1,5; 3,0}; es una cota macroclimática, no un caudal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
import pyproj
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject

from .. import config as C
from ..science import hydrology as H
from . import governance as G

ENGINE = "hydrology"
ENGINE_VERSION = G.ENGINE_VERSION


class WindowError(ValueError):
    """La ventana solicitada no es utilizable (tamaño, CRS o cobertura)."""


@dataclass
class DemWindow:
    data: np.ndarray
    transform: Any
    crs: str
    res_m: float
    row: int
    col: int
    bounds_m: tuple[float, float, float, float]
    nodata_share: float

    @property
    def shape(self) -> tuple[int, int]:
        return self.data.shape

    @property
    def cell_area_km2(self) -> float:
        return (self.res_m ** 2) / 1e6


def dem_window_metric(lon: float, lat: float, size_m: float,
                      *, res_m: float = 30.0) -> DemWindow:
    """Lee una ventana del DEM y la reproyecta a una rejilla métrica en memoria.

    Se reproyecta **la ventana**, no el país: el proceso es acotado en memoria
    (ventana de 12 km → 400×400 celdas ≈ 1,3 MB). La rejilla resultante tiene
    30 m en EPSG:32616 aunque el DEM nativo sea de 1 arcosegundo; es un
    remuestreo declarado, no un aumento de resolución.
    """
    if not 5 <= size_m <= 60_000:
        raise WindowError(
            f"tamaño de ventana fuera de rango: {size_m} m (5–60.000 m)")
    if res_m <= 0:
        raise WindowError("res_m debe ser positivo")
    if size_m < 2 * res_m:
        # Una ventana menor que dos celdas no se puede remuestrear: devolver
        # una cuenca de 10 m desde un DEM de 30 m sería una invención.
        raise WindowError(
            f"tamaño de ventana {size_m} m menor que dos celdas de {res_m} m: "
            "no hay resolución suficiente")
    src_path = C.DEM_WGS84
    if not src_path.exists():
        raise G.SourceUnavailableError("copdem30", [str(src_path)])

    target = C.CRS_METRIC
    transformer = pyproj.Transformer.from_crs(C.CRS_STORAGE, target,
                                              always_xy=True)
    x, y = transformer.transform(lon, lat)
    half = size_m / 2.0
    n = max(3, int(round(size_m / res_m)))
    width = height = n
    left, top = x - half, y + half
    dst_transform = from_origin(left, top, res_m, res_m)
    dest = np.full((height, width), np.nan, dtype="float64")

    with rasterio.open(src_path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dest,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=dst_transform,
            dst_crs=target,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
            num_threads=1,
        )

    row, col = height // 2, width // 2
    valid = np.isfinite(dest)
    return DemWindow(
        data=dest, transform=dst_transform, crs=target, res_m=res_m,
        row=row, col=col,
        bounds_m=(left, top - size_m, left + size_m, top),
        nodata_share=round(1.0 - float(valid.mean()), 4),
    )


# --- agua superficial (OSM) --------------------------------------------------
@lru_cache(maxsize=1)
def _water_layers():
    import geopandas as gpd

    path = C.INFRA_GPKG
    if not path.exists():
        return None
    waterways = gpd.read_file(path, layer="waterways")
    bodies = gpd.read_file(path, layer="water_bodies")
    return waterways, bodies


def surface_water(lon: float, lat: float, *, max_km: float = 10.0) -> dict[str, Any]:
    """Elemento hidrográfico mapeado más cercano y su distancia real.

    La distancia se mide en EPSG:32616 (metros). Se buscan candidatos con el
    índice espacial y se mide solo la geometría candidata, no la capa completa.
    """
    from shapely.geometry import Point

    layers = _water_layers()
    if layers is None:
        return {
            "available": False,
            "reason": "capa de infraestructura ausente",
            "waterways": None,
            "water_bodies": None,
            "note": "no se infiere hidrografía de otra capa",
        }
    waterways, bodies = layers
    point = Point(lon, lat)
    transformer = pyproj.Transformer.from_crs(C.CRS_STORAGE, C.CRS_METRIC,
                                              always_xy=True)
    px, py = transformer.transform(lon, lat)
    metric_point = Point(px, py)
    to_metric = pyproj.Transformer.from_crs(C.CRS_STORAGE, C.CRS_METRIC,
                                            always_xy=True)

    def nearest(gdf, kind: str) -> dict[str, Any] | None:
        if gdf is None or len(gdf) == 0:
            return None
        try:
            hit = gdf.sindex.nearest(point, return_all=False)
            positions = np.atleast_1d(hit[1])
        except Exception:  # noqa: BLE001 — índice espacial no disponible
            positions = np.array([int(gdf.distance(point).values.argmin())])
        best = None
        for pos in positions[:5]:
            row = gdf.iloc[int(pos)]
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            metric_geom = _to_metric_geom(geom, to_metric)
            distance_m = float(metric_point.distance(metric_geom))
            if best is None or distance_m < best["distance_m"]:
                best = {
                    "kind": kind,
                    "osm_id": _clean_attr(row.get("osm_id")),
                    "name": _clean_attr(row.get("name")),
                    "class": _clean_attr(row.get("waterway_class")
                                         or row.get("water_type")
                                         or row.get("waterway")),
                    "distance_m": round(distance_m, 1),
                    "distance_km": round(distance_m / 1000.0, 3),
                }
        return best

    wway = nearest(waterways, "waterway")
    wbody = nearest(bodies, "water_body")
    candidates = [c for c in (wway, wbody) if c]
    nearest_any = min(candidates, key=lambda c: c["distance_m"]) if candidates else None
    within = [c for c in candidates if c["distance_km"] <= max_km]
    return {
        "available": True,
        "query": {"lon": lon, "lat": lat, "max_km": max_km},
        "nearest_waterway": wway,
        "nearest_water_body": wbody,
        "nearest_any": nearest_any,
        "within_max_distance": within,
        "distance_method": "distancia euclídea en EPSG:32616 desde el punto al elemento",
        "source": "osm_sv",
        "caveats": [
            "un cauce mapeado no implica caudal permanente ni agua disponible",
            "la ausencia en OSM no implica ausencia en el terreno",
            "la proximidad a un cauce no dice nada sobre agua subterránea",
        ],
    }


def _clean_attr(value: Any) -> Any:
    """Atributo de GeoPandas listo para JSON: NaN/vacío → None."""
    if value is None:
        return None
    try:
        if isinstance(value, float) and not math.isfinite(value):
            return None
    except TypeError:
        return None
    text = str(value).strip()
    return text or None


def _to_metric_geom(geom, transformer):
    from shapely.ops import transform as shapely_transform

    return shapely_transform(transformer.transform, geom)


# --- cuenca derivada ---------------------------------------------------------
def watershed_from_point(lon: float, lat: float, *, size_m: float = 8000.0,
                         stream_threshold_ratio: float = 0.01
                         ) -> dict[str, Any]:
    """Cuenca aguas arriba de la celda del punto, en una ventana métrica."""
    window = dem_window_metric(lon, lat, size_m)
    z = window.data
    if not np.isfinite(z).any():
        raise WindowError(
            "la ventana no contiene celdas válidas del DEM (cobertura o NoData)")
    aoi = H.compute_aoi(z, window.res_m,
                        stream_threshold_ratio=stream_threshold_ratio)
    filled = aoi["filled"]
    dirs = aoi["directions"]
    acc = aoi["accumulation"]
    mask = H.watershed(dirs, (window.row, window.col),
                       valid=np.isfinite(filled))

    touches_edge = bool(
        mask[0, :].any() or mask[-1, :].any()
        or mask[:, 0].any() or mask[:, -1].any())
    cells = int(mask.sum())
    area_km2 = cells * window.cell_area_km2
    watershed_km2 = float(mask.sum() * (window.res_m ** 2) / 1e6)
    local_upstream_cells = int(acc[window.row, window.col])
    local_upstream_km2 = local_upstream_cells * window.cell_area_km2
    outlet_r, outlet_c = H.outlet_cell(acc)
    dx = (outlet_c - window.col) * window.res_m
    dy = (window.row - outlet_r) * window.res_m

    valid_cells = int(np.isfinite(filled).sum())
    total_cells = int(filled.size)
    return {
        "window": {
            "size_m": size_m,
            "cells": [int(window.shape[1]), int(window.shape[0])],
            "res_m": window.res_m,
            "crs": window.crs,
            "nodata_share": window.nodata_share,
            "valid_cells": valid_cells,
            "total_cells": total_cells,
            "source_resampling": (
                "DEM nativo 1 arcosegundo (~30 m) reproyectado a 30 m "
                "EPSG:32616: remuestreo declarado, no resolución nueva"),
        },
        "pour_point": {"row": window.row, "col": window.col,
                       "lon": lon, "lat": lat},
        "upstream_area_km2": round(area_km2, 4),
        "upstream_area_from_accumulation_km2": round(local_upstream_km2, 4),
        "truncated": touches_edge,
        "outlet": {
            "row": outlet_r, "col": outlet_c,
            "offset_m": {"east": round(dx, 1), "north": round(dy, 1)},
            "accumulation_cells": int(acc[outlet_r, outlet_c]),
        },
        "diagnostics": aoi["diagnostics"],
        "mask": mask,
        "res_m": window.res_m,
        "method": (
            "priority-flood + D8 + recorrido inverso de la cuenca desde la "
            "celda del punto; área = celdas de la cuenca × 900 m²"),
        "limitations": [
            "no es una cuenca oficial: es una derivación D8 local del DEM",
            "si el área toca el borde de la ventana, la cuenca está truncada",
            "el DEM de 30 m no resuelve obras hidráulicas ni cauces menores",
            "las zonas planas y los sumideros rellenados tienen orden de flujo "
            "arbitrario (diagnóstico incluido)",
        ],
    }


# --- balance hídrico ---------------------------------------------------------
def _budyko_runoff(precip_mm: float, pet_mm: float, *, omega: float) -> float | None:
    """Escorrentía anual (mm) por Budyko–Fu: E/P = 1+PET/P−(1+(PET/P)^ω)^(1/ω)."""
    if precip_mm <= 0 or pet_mm < 0:
        return None
    phi = pet_mm / precip_mm
    evap_ratio = 1.0 + phi - (1.0 + phi ** omega) ** (1.0 / omega)
    evap_ratio = min(max(evap_ratio, 0.0), 1.0)
    return precip_mm * (1.0 - evap_ratio)


def water_balance(lon: float, lat: float) -> dict[str, Any]:
    """Balance hídrico climático anual a partir de reanálisis en el punto cercano.

    No es un balance de suelo: no hay humedad de suelo, ni capacidad de agua
    disponible, ni percolación. Es P − ET0 y una cota macroclimática de
    escorrentía.
    """
    from . import climate as CL

    engine = CL.ClimateEngine()
    point = engine.nearest_point(lon, lat)
    precip = engine.annual_series(point["dataset_id"], "precipitation")
    et0 = engine.annual_series("open_meteo_point", "et0")
    if not precip or not et0:
        raise WindowError("no hay serie climática suficiente para el balance")

    years = sorted(set(precip) & set(et0))
    if not years:
        return {"available": False,
                "reason": "los años de precipitación y ET0 no se solapan"}
    rows = []
    for year in years:
        p = precip[year]["value"]
        e = et0[year]["value"]
        rows.append({
            "year": year,
            "precipitation_mm": p,
            "et0_mm": e,
            "precipitation_minus_et0_mm": round(p - e, 1),
            "aridity_index_p_over_et0": round(p / e, 3) if e else None,
            "budyko_runoff_mm_omega2": (round(q, 1) if (q := _budyko_runoff(
                p, e, omega=2.0)) is not None else None),
        })
    p_mean = sum(r["precipitation_mm"] for r in rows) / len(rows)
    e_mean = sum(r["et0_mm"] for r in rows) / len(rows)
    # Mayor ω en Budyko–Fu ⇒ mayor fracción evaporada ⇒ menor escorrentía.
    # Por eso ω=3,0 acota por abajo y ω=1,5 por arriba.
    q_low = _budyko_runoff(p_mean, e_mean, omega=3.0)
    q_high = _budyko_runoff(p_mean, e_mean, omega=1.5)
    q_mid = _budyko_runoff(p_mean, e_mean, omega=2.0)
    return {
        "available": True,
        "point": point,
        "years": years,
        "annual": rows,
        "mean": {
            "precipitation_mm": round(p_mean, 1),
            "et0_mm": round(e_mean, 1),
            "precipitation_minus_et0_mm": round(p_mean - e_mean, 1),
            "aridity_index_p_over_et0": round(p_mean / e_mean, 3) if e_mean else None,
            "budyko_runoff_mm": round(q_mid, 1) if q_mid is not None else None,
            "budyko_runoff_range_mm_omega_1.5_3.0": (
                [round(q_low, 1), round(q_high, 1)]
                if q_high is not None and q_low is not None else None),
            "budyko_range_note": (
                "[cota inferior con ω=3,0; cota superior con ω=1,5]: mayor ω "
                "implica más evaporación y menos escorrentía"),
        },
        "method": (
            "P y ET0 anuales de reanálisis; déficit = P − ET0. Escorrentía "
            "estimada por Budyko–Fu con ω=2 (curva de Budyko) y sensibilidad "
            "ω=1,5–3,0. Ningún parámetro se calibró con aforos."),
        "assumptions": [
            "estado estacionario anual: no hay cambio de almacenamiento",
            "ω=2 es una elección documentada, no calibrada en El Salvador",
            "la escorrentía de Budyko incluye todo el excedente; no separa "
            "infiltración, recarga ni caudal base",
            "P y ET0 provienen de puntos distintos (NASA POWER y Open-Meteo)",
        ],
        "limitations": [
            "no es un caudal ni un volumen aprovechable",
            "no es recarga de acuífero",
            "no incorpora extracciones, riego ni regulación",
            "un punto de reanálisis no representa una cuenca",
        ],
        "uncertainty": {
            "method": "rango entre productos de precipitación y sensibilidad de ω",
            "note": ("el rango NO es un intervalo de confianza: no hay estaciones "
                     "de referencia"),
        },
    }


def groundwater_availability() -> dict[str, Any]:
    """Interfaz de agua subterránea: declara lo que no existe, sin inventarlo."""
    keys = ["groundwater_aquifers", "groundwater_levels", "groundwater_recharge",
            "water_quality", "water_rights"]
    return {
        "available": False,
        "variables": {k: G.UNAVAILABLE[k] for k in keys},
        "note": (
            "no se infiere agua subterránea de la proximidad de un río, de un "
            "cuerpo de agua ni de la geología superficial; la ausencia es una "
            "propiedad del repositorio, no un resultado del motor"),
        "what_would_be_needed": [
            "polígono de acuíferos con fuente y licencia (MARN/ANDA)",
            "series de nivel piezométrico con datum y fecha",
            "parámetros hidráulicos o modelo calibrado para estimar recarga",
        ],
    }


# --- motor -------------------------------------------------------------------
class HydrologyEngine:
    """Motor hidrológico de Fase 5. Envuelve el núcleo D8 de Fase 2."""

    engine = ENGINE
    version = ENGINE_VERSION

    def surface(self, lon: float, lat: float, *, max_km: float = 10.0
                ) -> dict[str, Any]:
        return surface_water(lon, lat, max_km=max_km)

    def watershed(self, lon: float, lat: float, *, size_m: float = 8000.0
                  ) -> dict[str, Any]:
        result = watershed_from_point(lon, lat, size_m=size_m)
        result.pop("mask", None)
        return result

    def balance(self, lon: float, lat: float) -> dict[str, Any]:
        return water_balance(lon, lat)

    def groundwater(self) -> dict[str, Any]:
        return groundwater_availability()

    def profile(self, lon: float, lat: float, *, size_m: float = 8000.0,
                use_cache: bool = True) -> dict[str, Any]:
        """Perfil hidrológico completo: superficial + cuenca + balance + subterránea."""
        from .cache import DerivedCache

        def build() -> dict[str, Any]:
            steps = [G.step("superficie: cauce/cuerpo más cercano",
                            "agrosv.engines.hydrology.surface_water",
                            max_km=10.0)]
            surface = self.surface(lon, lat)
            steps.append(G.step("cuenca derivada D8", "watershed_from_point",
                                size_m=size_m))
            basin = self.watershed(lon, lat, size_m=size_m)
            steps.append(G.step("balance hídrico climático", "water_balance"))
            try:
                balance = self.balance(lon, lat)
            except Exception as exc:  # noqa: BLE001 — se declara, no se oculta
                balance = {"available": False, "reason": str(exc)}
            gw = self.groundwater()
            result = {
                "surface_water": surface,
                "watershed": basin,
                "water_balance": balance,
                "groundwater": gw,
                "hydrological_interpretation": {
                    "physically_present_water": (
                        "cuenca aportante y balance climático calculados"),
                    "not_computed": [
                        "caudal (sin aforos)", "recarga (sin acuífero)",
                        "almacenamiento de suelo (sin AWC)",
                        "agua autorizada o comprometida (no es un dato físico)",
                    ],
                    "rule": ("potencial hidrológico ≠ acceso legal ni operativo "
                             "al agua"),
                },
            }
            return G.envelope(
                ENGINE,
                result=result,
                sources=["copdem30", "osm_sv", "nasa_power_point",
                         "open_meteo_point"],
                limitations=[
                    "la cuenca es una derivación local del DEM, no una cuenca oficial",
                    "no hay aforos: ningún caudal está calibrado ni validado",
                    "no hay datos de agua subterránea",
                    "el balance P−ET0 no separa escorrentía, infiltración ni recarga",
                    "cobertura de cauces OSM incompleta y de precisión variable",
                ],
                processing=steps,
                query={"lon": lon, "lat": lat, "size_m": size_m},
                coverage=G.coverage_statement()["hydrology"],
            )

        payload, info = DerivedCache().get_or_compute(
            engine=ENGINE, version=self.version,
            params={"lon": round(lon, 6), "lat": round(lat, 6),
                    "size_m": size_m},
            paths=[C.DEM_WGS84, C.INFRA_GPKG, C.DATA / "validated" /
                   "agrosv_data.sqlite"],
            build=build, use_cache=use_cache)
        payload["cache"] = info.as_dict()
        return payload


__all__ = [
    "HydrologyEngine", "dem_window_metric", "surface_water",
    "watershed_from_point", "water_balance", "groundwater_availability",
    "WindowError", "DemWindow",
]
