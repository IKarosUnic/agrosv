"""AGROSV — API agrícola (Fase 6) bajo `/api/agriculture`.

Endpoints nuevos; no modifican los contratos de Fase 1–5. Convenciones:
`lat`/`lon` en EPSG:4326, `null` = sin dato, toda respuesta lleva fuentes,
limitaciones y versión del motor.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from ..engines import governance as G5
from ..engines.territorial import CoverageError, validate_coordinate
from . import governance as AG
from .calendar import AgriculturalCalendarEngine, CalendarError
from .catalog import CROPS, CropKnowledgeEngine
from .phenology import CropPhenologyEngine, PhenologyError
from .simulation import AdapterUnavailable, CropSimulationEngine, detect
from .suitability import CropSuitabilityEngine
from .water_nutrient import CropWaterNutrientEngine, WaterNutrientError

router = APIRouter(prefix="/api/agriculture", tags=["agriculture"])
SERVICE_VERSION = AG.ENGINE_VERSION

catalog = CropKnowledgeEngine()
phenology = CropPhenologyEngine()
suitability = CropSuitabilityEngine()
water = CropWaterNutrientEngine()
simulation = CropSimulationEngine()
calendar = AgriculturalCalendarEngine()


def _headers(engine: str) -> dict[str, str]:
    return {"X-AGROSV-Engine": engine,
            "X-AGROSV-Version": SERVICE_VERSION,
            "X-AGROSV-Synthetic": "false"}


def _coord(lat: float, lon: float) -> tuple[float, float]:
    try:
        lon_v, lat_v = validate_coordinate(lon, lat)
        return lat_v, lon_v
    except CoverageError as exc:
        raise HTTPException(400, str(exc)) from None


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(404, str(exc).strip("'\""))
    if isinstance(exc, G5.SourceUnavailableError):
        return HTTPException(503, str(exc))
    if isinstance(exc, (ValueError, PhenologyError, CalendarError,
                        WaterNutrientError, AdapterUnavailable)):
        return HTTPException(400, str(exc))
    return HTTPException(500, f"{type(exc).__name__}: {exc}")


@router.get("/meta", summary="Motores agrícolas, versión y política")
def meta() -> JSONResponse:
    return JSONResponse(
        content={
            "service_version": SERVICE_VERSION,
            "engines": ["crop_knowledge", "crop_phenology",
                        "crop_suitability", "crop_water_nutrient",
                        "crop_simulation", "agricultural_calendar"],
            "crops": len(CROPS),
            "policy": {
                "llm_used": False,
                "calibrated": False,
                "validated": False,
                "returns_yield_forecast": False,
                "gaps_are_null": True,
            },
        },
        headers=_headers("agriculture"))


@router.get("/crops", summary="Catálogo de cultivos")
def crops(crop_type: str | None = None,
          production_system: str | None = None) -> JSONResponse:
    try:
        payload = catalog.list_crops(crop_type=crop_type,
                                     production_system=production_system)
    except Exception as exc:  # pragma: no cover - contrato de error
        raise _error(exc) from None
    payload["engine"] = "crop_knowledge"
    payload["engine_version"] = SERVICE_VERSION
    return JSONResponse(content=payload, headers=_headers("crop_knowledge"))


@router.get("/crops/{crop_id}", summary="Ficha de cultivo y procedencia")
def crop(crop_id: str) -> JSONResponse:
    try:
        payload = catalog.get(crop_id)
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=payload, headers=_headers("crop_knowledge"))


@router.get("/search", summary="Buscar cultivo por nombre común o científico")
def search(q: str = Query(..., min_length=2)) -> JSONResponse:
    return JSONResponse(content=catalog.find(q),
                        headers=_headers("crop_knowledge"))


@router.get("/audit", summary="Auditoría de vacíos del catálogo")
def audit() -> JSONResponse:
    return JSONResponse(content=catalog.audit(),
                        headers=_headers("crop_knowledge"))


@router.get("/phenology", summary="Etapas fenológicas por tiempo térmico")
def run_phenology(crop_id: str, planting_date: str,
                  gdd_to_maturity: float | None = None,
                  tbase_c: float | None = None) -> JSONResponse:
    variety: dict[str, Any] = {}
    if gdd_to_maturity is not None:
        variety["gdd_to_maturity"] = gdd_to_maturity
        variety["source"] = "query"
    if tbase_c is not None:
        variety["tbase_c"] = tbase_c
    try:
        payload = phenology.run(crop_id, planting_date,
                                variety=variety or None)
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=payload, headers=_headers("crop_phenology"))


@router.get("/suitability", summary="Aptitud S1/S2/S3/N con factores limitantes")
def run_suitability(crop_id: str, lat: float, lon: float,
                    system: str = "rainfed",
                    irrigation_available: bool = False) -> JSONResponse:
    lat, lon = _coord(lat, lon)
    try:
        payload = suitability.evaluate(
            crop_id, lon, lat, system=system,
            irrigation_available=irrigation_available)
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=payload, headers=_headers("crop_suitability"))


@router.get("/calendar", summary="Calendario derivado (no oficial)")
def run_calendar(crop_id: str, planting_date: str | None = None) -> JSONResponse:
    try:
        payload = calendar.generate(crop_id, planting_date=planting_date)
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=payload,
                        headers=_headers("agricultural_calendar"))


@router.get("/adapters", summary="Detección de adaptadores de simulación")
def adapters() -> JSONResponse:
    return JSONResponse(content=simulation.compare() | {"detection": detect()},
                        headers=_headers("crop_simulation"))


@router.get("/nutrients", summary="Demanda de nutrientes (no es dosis)")
def nutrients(crop_id: str, yield_t_ha: float,
              yield_source: str = Query(..., min_length=3)) -> JSONResponse:
    try:
        payload = water.nutrient_demand(crop_id, yield_t_ha,
                                        yield_source=yield_source)
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=payload,
                        headers=_headers("crop_water_nutrient"))


@router.post("/water", summary="Balance hídrico FAO-56 diario")
def run_water(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    required = ("crop_id", "planting_date", "awc_mm_per_m", "root_depth_cm")
    missing = [k for k in required if payload.get(k) is None]
    if missing:
        raise HTTPException(400, f"faltan campos: {missing}")
    try:
        result = water.water_balance(
            crop_id=payload["crop_id"],
            planting_date=payload["planting_date"],
            awc_mm_per_m=float(payload["awc_mm_per_m"]),
            root_depth_cm=float(payload["root_depth_cm"]),
            initial_depletion_mm=float(payload.get("initial_depletion_mm", 0.0)),
            kc=payload.get("kc"),
            allow_reference_kc=bool(payload.get("allow_reference_kc", False)),
            p_depletion=float(payload.get("p_depletion", 0.5)),
            irrigation={str(k): float(v) for k, v in
                        (payload.get("irrigation") or {}).items()},
            rain_method=payload.get("rain_method", "min_p_etc"))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result,
                        headers=_headers("crop_water_nutrient"))


@router.post("/simulate", summary="Simulación por adaptador (no calibrada)")
def run_simulation(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    required = ("crop_id", "planting_date", "awc_mm_per_m", "root_depth_cm")
    missing = [k for k in required if payload.get(k) is None]
    if missing:
        raise HTTPException(400, f"faltan campos: {missing}")
    try:
        result = simulation.simulate(
            crop_id=payload["crop_id"],
            planting_date=payload["planting_date"],
            awc_mm_per_m=float(payload["awc_mm_per_m"]),
            root_depth_cm=float(payload["root_depth_cm"]),
            initial_depletion_mm=float(payload.get("initial_depletion_mm", 0.0)),
            kc=payload.get("kc"),
            allow_reference_kc=bool(payload.get("allow_reference_kc", False)),
            irrigation={str(k): float(v) for k, v in
                        (payload.get("irrigation") or {}).items()},
            potential_yield_t_ha=payload.get("potential_yield_t_ha"),
            ky=payload.get("ky"),
            ky_source=payload.get("ky_source"),
            variety=payload.get("variety"),
            adapter=payload.get("adapter", "agrosv_water_balance"))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("crop_simulation"))
