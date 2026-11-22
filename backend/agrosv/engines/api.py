"""AGROSV — API de motores territoriales y ambientales (Fase 5, §10).

Router nuevo bajo `/api/engines`. No modifica `/api`, `/api/v1` ni `/api/data`:
solo añade un prefijo y reutiliza sus datos.

Convenciones de todas las respuestas:

* coordenadas de consulta en EPSG:4326 (lon, lat), en grados decimales;
* métricas en EPSG:32616 y áreas en EPSG:6933;
* unidades del registro `agrosv.data.units`;
* `null` significa «sin dato», nunca cero;
* toda respuesta incluye `sources`, `limitations` y `coverage`;
* un punto fuera del rectángulo nacional devuelve 400, no un valor extrapolado.

Endpoints:

    GET /api/engines/meta                        motores, versiones, política
    GET /api/engines/coverage                    cobertura geográfica real
    GET /api/engines/datasets                    disponibilidad + ficha §8
    GET /api/engines/datasets/{dataset_id}       ficha y procedencia
    GET /api/engines/territory/search?q=&level=  búsqueda territorial
    GET /api/engines/territorial?lat=&lon=       perfil territorial
    GET /api/engines/terrain?lat=&lon=           características del terreno
    GET /api/engines/soil?lat=&lon=              perfil de suelo 0–30 cm
    GET /api/engines/hydrology?lat=&lon=         perfil hidrológico
    GET /api/engines/climate?lat=&lon=           perfil climático
    GET /api/engines/environmental?lat=&lon=     perfil ambiental completo
    GET /api/engines/cache                       estado del caché derivado
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from . import cache as CACHE
from . import governance as G
from . import territorial as TR
from .climate import ClimateDataError
from .hydrology import WindowError

router = APIRouter(prefix="/api/engines", tags=["engines"])

SERVICE_VERSION = G.ENGINE_VERSION


def _headers(engine: str = "agrosv", provenance: str = "") -> dict[str, str]:
    return {
        "X-AGROSV-Engine": engine,
        "X-AGROSV-Version": SERVICE_VERSION,
        "X-AGROSV-Data-Date": G.utcnow()[:10],
        **({"X-AGROSV-Provenance": provenance} if provenance else {}),
    }


def _coord(lat: float, lon: float) -> tuple[float, float]:
    try:
        return TR.validate_coordinate(lon, lat)
    except TR.CoverageError as exc:
        raise HTTPException(400, str(exc)) from None


def _wrap_error(exc: Exception) -> HTTPException:
    if isinstance(exc, G.SourceUnavailableError):
        return HTTPException(503, str(exc))
    if isinstance(exc, (TR.CoverageError, WindowError, ValueError)):
        return HTTPException(400, str(exc))
    if isinstance(exc, ClimateDataError):
        return HTTPException(503, str(exc))
    return HTTPException(500, f"{type(exc).__name__}: {exc}")


# --- metadatos ---------------------------------------------------------------
@router.get("/meta", summary="Motores disponibles, versiones y política científica")
def meta():
    return JSONResponse(
        content={
            "service_version": SERVICE_VERSION,
            "engines": G.ENGINES,
            "inherits": {
                "territory": "/api (Fase 1) y /api/data (Fase 4)",
                "science": "/api/v1 (Fase 2)",
                "datasets": "/api/data/datasets",
            },
            "conventions": {
                "crs_query": "EPSG:4326",
                "crs_metric": "EPSG:32616",
                "crs_area": "EPSG:6933",
                "nodata": "null en JSON",
                "units": "agrosv.data.units",
            },
            "policies": {
                "no_composite_index": (
                    "no se publica un índice ambiental o de aptitud sin fórmula, "
                    "pesos, limitaciones y validación"),
                "no_extrapolation": (
                    "un punto fuera de cobertura devuelve error, no un valor "
                    "interpolado"),
                "labeling": (
                    "observado / reanálisis / predicción modelada / derivado / "
                    "simulado se conservan hasta la respuesta"),
                "unavailable_data": (
                    "las variables ausentes se enumeran en /datasets con el "
                    "motivo y lo que haría falta"),
            },
            "cache": CACHE.DerivedCache().stats(),
        },
        headers=_headers(),
    )


@router.get("/coverage", summary="Cobertura geográfica y temporal real")
def coverage():
    return JSONResponse(
        content={**G.coverage_statement(),
                 "territorial_levels": TR.coverage()["territorial_levels"]},
        headers=_headers())


@router.get("/datasets", summary="Disponibilidad real de datasets y variables ausentes")
def datasets():
    payload = G.availability_report()
    return JSONResponse(content=payload, headers=_headers())


@router.get("/datasets/{dataset_id}", summary="Ficha §8 y procedencia de un dataset")
def dataset(dataset_id: str):
    try:
        payload = G.provenance(dataset_id)
    except KeyError:
        raise HTTPException(404, f"dataset desconocido: {dataset_id}") from None
    return JSONResponse(content=payload, headers=_headers())


# --- consultas espaciales ----------------------------------------------------
@router.get("/territory/search", summary="Búsqueda por identificador o nombre")
def territory_search(q: str = Query(..., min_length=1),
                     level: str | None = None):
    from .territorial import TerritorialEngine

    try:
        payload = TerritorialEngine().resolve_territory(q, level=level)
    except G.SourceUnavailableError as exc:
        raise HTTPException(503, str(exc)) from None
    return JSONResponse(content=payload, headers=_headers("territorial"))


@router.get("/territorial", summary="Perfil territorial por coordenadas")
def territorial(lat: float, lon: float, radius_cells: int = Query(2, ge=1, le=10)):
    lon, lat = _coord(lat, lon)
    from .territorial import TerritorialEngine

    try:
        payload = TerritorialEngine().profile(lon, lat, radius_cells=radius_cells)
    except Exception as exc:  # noqa: BLE001 — se traduce a HTTP concreto
        raise _wrap_error(exc) from None
    return JSONResponse(content=payload,
                        headers=_headers("territorial"))


@router.get("/terrain", summary="Elevación, pendiente, aspecto, TRI, TPI")
def terrain(lat: float, lon: float, radius_cells: int = Query(2, ge=1, le=10)):
    lon, lat = _coord(lat, lon)
    from .terrain import terrain_metrics

    metrics = terrain_metrics(lon, lat, radius_cells=radius_cells)
    if not metrics.get("available"):
        raise HTTPException(404, metrics.get("reason", "sin dato en el DEM"))
    payload = G.envelope(
        "territorial",
        result={"terrain": metrics},
        sources=["copdem30"],
        limitations=metrics["limitations"],
        processing=[G.step("métricas de terreno",
                           "agrosv.engines.terrain.terrain_metrics",
                           radius_cells=radius_cells)],
        query={"lon": lon, "lat": lat},
        coverage=G.coverage_statement()["terrain"],
    )
    return JSONResponse(content=payload, headers=_headers("territorial"))


@router.get("/soil", summary="Suelo 0–30 cm: propiedades, textura y limitaciones")
def soil(lat: float, lon: float):
    lon, lat = _coord(lat, lon)
    from .soil import SoilEngine

    try:
        payload = SoilEngine().sample(lon, lat)
    except Exception as exc:  # noqa: BLE001
        raise _wrap_error(exc) from None
    return JSONResponse(content=payload, headers=_headers("soil"))


@router.get("/hydrology", summary="Agua superficial, cuenca local y balance hídrico")
def hydrology(lat: float, lon: float, size_m: float = Query(8000, ge=1000, le=30000),
              fresh: bool = False):
    lon, lat = _coord(lat, lon)
    from .hydrology import HydrologyEngine

    try:
        payload = HydrologyEngine().profile(lon, lat, size_m=size_m,
                                            use_cache=not fresh)
    except Exception as exc:  # noqa: BLE001
        raise _wrap_error(exc) from None
    return JSONResponse(content=payload, headers=_headers("hydrology"))


@router.get("/climate", summary="Climatología del período, rachas, extremos y sequía")
def climate(lat: float, lon: float):
    lon, lat = _coord(lat, lon)
    from .climate import ClimateEngine

    try:
        payload = ClimateEngine().profile(lon, lat)
    except Exception as exc:  # noqa: BLE001
        raise _wrap_error(exc) from None
    return JSONResponse(content=payload, headers=_headers("climate"))


@router.get("/environmental", summary="Perfil ambiental integrado (sin índice compuesto)")
def environmental(lat: float, lon: float,
                  size_m: float = Query(6000, ge=1000, le=30000),
                  fresh: bool = False):
    lon, lat = _coord(lat, lon)
    from .environmental import EnvironmentalInteractionEngine

    try:
        payload = EnvironmentalInteractionEngine().profile(
            lon, lat, size_m=size_m, use_cache=not fresh)
    except Exception as exc:  # noqa: BLE001
        raise _wrap_error(exc) from None
    return JSONResponse(content=payload, headers=_headers("environmental"))


@router.get("/cache", summary="Estado del caché de resultados derivados")
def cache_status():
    return JSONResponse(content=CACHE.DerivedCache().stats(),
                        headers=_headers())
