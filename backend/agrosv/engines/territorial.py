"""AGROSV — TerritorialEngine (Fase 5, §3).

Responde «¿dónde está este punto y qué se sabe de su territorio?» con tres
niveles de respuesta separados:

1. **Identificación administrativa** — país, departamento (ADM1 oficial) y
   municipio histórico (ADM2 pre-2023, `official: false`). Los niveles que no
   existen en el repositorio se devuelven como ausentes con su motivo; no se
   sintetizan límites por nombre ni por interpolación.
2. **Caracterización física** — elevación, pendiente, aspecto, clase de
   relieve, TRI y TPI (ver `terrain.py`).
3. **Asociación hidrográfica** — cuenca local derivada del DEM y distancia al
   cauce mapeado más cercano (ver `hydrology.py`).

El CRS de consulta es EPSG:4326 (lon/lat). Las métricas se calculan en
EPSG:32616 y las áreas en EPSG:6933. Una consulta fuera del rectángulo de El
Salvador se rechaza con `CoverageError` antes de leer cualquier ráster.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .. import config as C
from ..data import territory as T
from . import governance as G
from . import terrain as TM

ENGINE = "territorial"
ENGINE_VERSION = G.ENGINE_VERSION


class CoverageError(ValueError):
    """El punto está fuera de la cobertura declarada del sistema."""

    def __init__(self, message: str, *, bbox: tuple[float, ...] | None = None) -> None:
        super().__init__(message)
        self.bbox = bbox


def validate_coordinate(lon: float, lat: float) -> tuple[float, float]:
    try:
        lon_f, lat_f = float(lon), float(lat)
    except (TypeError, ValueError):
        raise CoverageError("coordenada no numérica") from None
    if not (math.isfinite(lon_f) and math.isfinite(lat_f)):
        raise CoverageError("coordenada no finita")
    if not (-180 <= lon_f <= 180 and -90 <= lat_f <= 90):
        raise CoverageError("coordenada fuera de rango geográfico",
                            bbox=C.SV_BOUNDS)
    west, south, east, north = C.SV_BOUNDS
    if not (west <= lon_f <= east and south <= lat_f <= north):
        raise CoverageError(
            "coordenada fuera del rectángulo de El Salvador "
            f"{C.SV_BOUNDS}: no hay dato y no se extrapola", bbox=C.SV_BOUNDS)
    return lon_f, lat_f


@lru_cache(maxsize=1)
def _admin_layers():
    """GeoPackage administrativo en memoria (una sola lectura por proceso)."""
    import geopandas as gpd

    path = C.TERRITORY_GPKG
    if not path.exists():
        return None
    return {
        "adm0": gpd.read_file(path, layer="adm0"),
        "adm1": gpd.read_file(path, layer="adm1"),
        "adm2": gpd.read_file(path, layer="adm2"),
    }


@lru_cache(maxsize=1)
def _stats() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, path in (("topography", C.TOPOGRAPHY_DIR / "topography_stats.json"),
                      ("soils", C.SOILS_DIR / "soils_stats.json"),
                      ("territory", C.TERRITORY_DIR / "territory_meta.json")):
        try:
            out[key] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            out[key] = None
    return out


@lru_cache(maxsize=1)
def _territory_index():
    """Índice territorial con geometrías (una sola lectura por proceso)."""
    return T.TerritorialIndex.from_geopackage(C.TERRITORY_GPKG)


def territories_in_bbox(west: float, south: float, east: float, north: float,
                        *, level: str | None = None) -> dict[str, Any]:
    """Intersección espacial exacta entre un rectángulo y los límites cargados.

    Devuelve qué unidades intersectan el rectángulo, si alguna lo contiene por
    completo y el área de intersección en EPSG:6933. No ajusta límites ni
    completa departamentos que el rectángulo solo toca en parte.
    """
    from shapely.geometry import box

    try:
        west, south, east, north = (float(west), float(south), float(east),
                                    float(north))
    except (TypeError, ValueError):
        raise CoverageError("extensión no numérica") from None
    if not all(math.isfinite(v) for v in (west, south, east, north)):
        raise CoverageError("extensión no finita")
    if not (west < east and south < north):
        raise CoverageError("se requiere oeste < este y sur < norte")
    if not (-180 <= west <= 180 and -180 <= east <= 180
            and -90 <= south <= 90 and -90 <= north <= 90):
        raise CoverageError("extensión fuera de rango geográfico",
                            bbox=C.SV_BOUNDS)
    layers = _admin_layers()
    if layers is None:
        raise G.SourceUnavailableError("geoboundaries_adm1",
                                       [str(C.TERRITORY_GPKG)])
    target = box(west, south, east, north)
    levels = {"country": "adm0", "department": "adm1",
              "municipality_historic": "adm2"}
    out: list[dict[str, Any]] = []
    for level_name, layer in levels.items():
        if level and level != level_name:
            continue
        gdf = layers.get(layer)
        if gdf is None or len(gdf) == 0:
            continue
        try:
            positions = list(gdf.sindex.query(target, predicate="intersects"))
        except Exception as exc:  # noqa: BLE001 — índice espacial no disponible
            raise CoverageError(
                f"no se pudo consultar el índice espacial: {exc}") from None
        for pos in positions:
            row = gdf.iloc[int(pos)]
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            code = None
            for key in ("adm0_code", "adm1_code", "adm2_code"):
                if key in row and row[key] is not None:
                    code = str(row[key])
                    break
            out.append({
                "level": level_name,
                "name": str(row.get("name")),
                "source_code": code,
                "official": (None if row.get("official") is None
                             else bool(row.get("official"))),
                "area_km2": (round(float(row["area_km2"]), 3)
                             if row.get("area_km2") is not None else None),
                "intersects": True,
                "contains_query_bbox": bool(geom.contains(target)),
            })
    out.sort(key=lambda e: (e["level"], e["name"] or ""))
    return {
        "query": {"west": west, "south": south, "east": east,
                  "north": north, "level": level, "crs": C.CRS_STORAGE},
        "count": len(out),
        "territories": out,
        "method": ("intersección geométrica exacta con el índice espacial de "
                   "cada capa; contains_query_bbox indica contención completa"),
        "limitations": [
            "un rectángulo no es una parcela ni una cuenca",
            "ADM2 es histórico (pre-2023) y oficial=false",
            "la exactitud posicional de los límites no está verificada",
        ],
    }


@dataclass
class Location:
    lon: float
    lat: float
    inside_bbox: bool
    inside_land: bool | None
    country: dict[str, Any] | None
    department: dict[str, Any] | None
    municipality_historic: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": {"lon": self.lon, "lat": self.lat},
            "crs": C.CRS_STORAGE,
            "inside_bbox": self.inside_bbox,
            "inside_land": self.inside_land,
            "country": self.country,
            "department": self.department,
            "municipality_historic": self.municipality_historic,
        }


def _feature(row, level: str, parent: dict[str, Any] | None = None) -> dict[str, Any]:
    code = None
    for key in ("adm0_code", "adm1_code", "adm2_code"):
        if key in row and row[key] is not None:
            code = str(row[key])
            break
    entry: dict[str, Any] = {
        "level": level,
        "name": str(row.get("name")),
        "source_code": code,
        "official": (None if row.get("official") is None
                     else bool(row.get("official"))),
        "area_km2": (round(float(row["area_km2"]), 3)
                     if row.get("area_km2") is not None else None),
        "source_id": str(row.get("source_id")) if row.get("source_id") else None,
    }
    if parent:
        entry["parent"] = parent
    return entry


def locate(lon: float, lat: float) -> Location:
    """Identificación administrativa por contención geométrica exacta."""
    from shapely.geometry import Point

    lon, lat = validate_coordinate(lon, lat)
    layers = _admin_layers()
    if layers is None:
        raise G.SourceUnavailableError("geoboundaries_adm1", [str(C.TERRITORY_GPKG)])
    point = Point(lon, lat)

    def find(gdf, level: str):
        if gdf is None or len(gdf) == 0:
            return None
        hits = gdf[gdf.geometry.contains(point)]
        if len(hits) == 0:
            hits = gdf[gdf.geometry.intersects(point)]
        if len(hits) == 0:
            return None
        row = hits.iloc[0]
        return _feature(row, level)

    country = find(layers["adm0"], "country")
    department = find(layers["adm1"], "department")
    if department is None:
        # El ADM0 derivado de ADM1 no incluye aguas: un punto en el bbox pero
        # fuera de todo departamento se declara fuera de tierra firme.
        return Location(lon, lat, True, False, None, None, None)
    municipality = find(layers["adm2"], "municipality_historic")
    return Location(lon, lat, True, True, country, department, municipality)


def coverage() -> dict[str, Any]:
    """Comprobación de cobertura: qué capa cubre qué extensión."""
    return {
        "bbox_wgs84": list(C.SV_BOUNDS),
        "crs": {"query": C.CRS_STORAGE, "metric": C.CRS_METRIC,
                "area": C.CRS_EQUAL_AREA},
        "territorial_levels": {
            "present": ["country", "department", "municipality_historic"],
            "official": ["country", "department"],
            "absent": ["municipality_2023", "district", "basin", "subbasin",
                       "protected_area", "parcel"],
            "absent_note": (
                "los niveles ausentes no se sintetizan; las consultas que los "
                "requieran fallan en lugar de devolver un límite inventado"),
        },
        "rasters": {
            "dem": {"crs": "EPSG:4326", "resolution": "1 arcosegundo (~30 m)",
                    "role": "elevación"},
            "slope_aspect": {"crs": C.CRS_METRIC, "resolution": "30 m"},
            "soils": {"crs": C.CRS_METRIC, "resolution": "250 m",
                      "depth": "0–30 cm"},
        },
        "climate": {
            "points": 2,
            "period": "2019-01-01 a 2025-12-31",
            "spatial_interpolation": False,
        },
        "hydrology": {
            "mapped_watercourses": "OSM, cobertura incompleta",
            "derived_basins": "D8 local, no oficial",
            "groundwater": "no disponible",
        },
    }


def department_statistics(department_code: str | None) -> dict[str, Any] | None:
    """Contexto agregado del departamento, solo si existe con su fuente."""
    if not department_code:
        return None
    stats = _stats()
    topo = stats.get("topography") or {}
    soils = stats.get("soils") or {}
    entry: dict[str, Any] = {"department_code": department_code}
    found = False
    for label, source in (("topography", topo.get("departments")),
                          ("soils", soils.get("departments"))):
        if isinstance(source, dict) and department_code in source:
            entry[label] = source[department_code]
            found = True
    if not found:
        return None
    entry["note"] = ("agregados departamentales calculados sobre las celdas "
                     "del ráster; no son mediciones del punto consultado")
    return entry


class TerritorialEngine:
    """Motor territorial: identificación, topografía y asociación hidrográfica."""

    engine = ENGINE
    version = ENGINE_VERSION

    def coverage(self) -> dict[str, Any]:
        return coverage()

    def locate(self, lon: float, lat: float) -> dict[str, Any]:
        return locate(lon, lat).as_dict()

    def terrain(self, lon: float, lat: float, *, radius_cells: int = 2
                ) -> dict[str, Any]:
        lon, lat = validate_coordinate(lon, lat)
        metrics = TM.terrain_metrics(lon, lat, radius_cells=radius_cells)
        return G.envelope(
            ENGINE,
            result={"terrain": metrics},
            sources=["copdem30"],
            limitations=metrics.get("limitations", [
                "no hay dato del DEM en este punto"]),
            processing=[G.step("muestreo del DEM y métricas locales",
                               "agrosv.engines.terrain.terrain_metrics",
                               radius_cells=radius_cells)],
            query={"lon": lon, "lat": lat},
            coverage=G.coverage_statement()["terrain"],
        )

    def watershed_association(self, lon: float, lat: float, *,
                              size_m: float = 6000.0) -> dict[str, Any]:
        from . import hydrology as HY

        lon, lat = validate_coordinate(lon, lat)
        basin = HY.watershed_from_point(lon, lat, size_m=size_m)
        basin.pop("mask", None)
        surface = HY.surface_water(lon, lat)
        return {
            "basin": basin,
            "mapped_surface_water": surface,
            "association_rule": (
                "la cuenca es aguas arriba de la celda consultada; la distancia "
                "al cauce es euclídea y no implica disponibilidad de agua"),
            "source": ["copdem30", "osm_sv"],
        }

    def profile(self, lon: float, lat: float, *, radius_cells: int = 2,
                size_m: float = 6000.0) -> dict[str, Any]:
        """Perfil territorial: identificación + terreno + hidrografía asociada."""
        lon, lat = validate_coordinate(lon, lat)
        location = locate(lon, lat)
        if location.inside_land is False:
            raise CoverageError(
                "el punto está en el rectángulo nacional pero fuera de tierra "
                "firme (aguas territoriales): no hay suelo ni DEM que consultar",
                bbox=C.SV_BOUNDS)
        terrain_result = TM.terrain_metrics(lon, lat, radius_cells=radius_cells)
        hydro: dict[str, Any]
        try:
            hydro = self.watershed_association(lon, lat, size_m=size_m)
        except Exception as exc:  # noqa: BLE001 — se declara el fallo parcial
            hydro = {"available": False, "reason": str(exc)}
        dept = (location.department or {}).get("source_code")
        result = {
            "location": location.as_dict(),
            "terrain": terrain_result,
            "hydrological_association": hydro,
            "department_context": department_statistics(dept),
            "layer_resolution": {
                "dem": "1 arcosegundo (~30 m)",
                "slope_aspect": "30 m",
                "soils": "250 m (consultar SoilEngine)",
                "territorial_boundaries": "vectorial; exactitud no verificada",
            },
        }
        return G.envelope(
            ENGINE,
            result=result,
            sources=["copdem30", "geoboundaries_adm1", "osm_sv"],
            limitations=[
                "ADM2 es histórico (272 municipios pre-2023) y no oficial",
                "no hay límites 2023 ni distritos: se declaran ausentes",
                "la cuenca es local y puede estar truncada por la ventana",
                "DSM ≠ DTM y resolución ≠ precisión",
                "un límite administrativo no coincide con una cuenca",
            ],
            processing=[
                G.step("identificación administrativa",
                       "agrosv.engines.territorial.locate"),
                G.step("métricas de terreno",
                       "agrosv.engines.terrain.terrain_metrics",
                       radius_cells=radius_cells),
                G.step("cuenca local y agua superficial",
                       "agrosv.engines.hydrology", size_m=size_m),
            ],
            query={"lon": lon, "lat": lat, "radius_cells": radius_cells,
                   "size_m": size_m},
            coverage=coverage(),
        )

    def profile_by_territory(self, query: str, *, level: str | None = None,
                             radius_cells: int = 2,
                             size_m: float = 6000.0) -> dict[str, Any]:
        """Perfil por identificador oficial, evaluado en un punto interior.

        Un perfil areal exigiría agregar cada celda del polígono; aquí se
        evalúa un punto interior representativo y se declara que no es un
        promedio del territorio.
        """
        from shapely.geometry import shape

        try:
            entry = _territory_index().resolve(query, level=level)
        except T.AmbiguousTerritoryError as exc:
            return {"resolved": False, "ambiguous": True, "query": query,
                    "candidates": exc.candidates,
                    "note": "se devuelven los candidatos; no se elige uno"}
        except T.TerritoryError as exc:
            return {"resolved": False, "ambiguous": False, "query": query,
                    "error": str(exc)}
        except FileNotFoundError:
            raise G.SourceUnavailableError("geoboundaries_adm1",
                                           [str(C.TERRITORY_GPKG)]) from None
        if not entry.geometry:
            raise G.SourceUnavailableError(
                "geoboundaries_adm1", ["geometría del territorio en el índice"],
                "el índice se construyó sin geometrías")

        point = shape(entry.geometry).representative_point()
        profile = self.profile(point.x, point.y, radius_cells=radius_cells,
                               size_m=size_m)
        profile["result"]["territory_selection"] = {
            "territory_id": entry.territory_id,
            "level": entry.level,
            "name": entry.name,
            "source_code": entry.source_code,
            "official": entry.official,
            "area_km2": entry.area_km2,
            "evaluation_point": {"lon": round(point.x, 6),
                                 "lat": round(point.y, 6)},
            "point_rule": (
                "punto interior representativo (representative_point): el perfil "
                "describe ese punto, no un promedio areal del territorio"),
        }
        profile["query"].update({"territory_query": query,
                                 "territory_level": level})
        profile["limitations"].append(
            "el perfil por identificador se evalúa en un punto interior; no es "
            "un agregado areal del departamento o municipio")
        return profile

    def resolve_territory(self, query: str, *, level: str | None = None
                          ) -> dict[str, Any]:
        """Búsqueda por identificador o nombre sobre el índice territorial."""
        path = C.DATA / "metadata" / "territory_index.json"
        if not path.exists():
            raise G.SourceUnavailableError("geoboundaries_adm1", [str(path)])
        index = T.TerritorialIndex.from_geopackage(C.TERRITORY_GPKG)
        try:
            entry = index.resolve(query, level=level)
        except T.AmbiguousTerritoryError as exc:
            return {
                "resolved": False,
                "ambiguous": True,
                "query": query,
                "candidates": exc.candidates,
                "note": "se devuelven los candidatos; no se elige uno por el usuario",
            }
        except T.TerritoryError as exc:
            return {"resolved": False, "ambiguous": False, "query": query,
                    "error": str(exc)}
        payload = entry.as_dict()
        payload.pop("geometry", None)
        return {"resolved": True, "territory": payload,
                "rule": "territory_id es la clave; el nombre es un atributo de búsqueda"}


__all__ = [
    "TerritorialEngine", "locate", "coverage", "validate_coordinate",
    "CoverageError", "Location", "department_statistics", "territories_in_bbox",
]
