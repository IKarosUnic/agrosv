"""AGROSV — API de incorporación de datos externos.

Solo lee archivos bajo `data/external/` o `data/reference/`; rechaza rutas
absolutas y escape de directorio. Validar no modifica el archivo ni imputa
valores.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from .. import config as C
from ..agriculture import governance as AG
from . import dem, municipalities, registry, validators

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])
VERSION = AG.ENGINE_VERSION

ALLOWED_ROOTS = (C.DATA / "external", C.DATA / "reference")


def _headers(engine: str) -> dict[str, str]:
    return {"X-AGROSV-Engine": engine, "X-AGROSV-Version": VERSION}


def _resolve(raw: str | None) -> Path:
    if not raw:
        raise HTTPException(400, "falta 'path'")
    candidate = Path(raw)
    if candidate.is_absolute():
        raise HTTPException(400, "se requiere una ruta relativa al proyecto")
    resolved = (C.ROOT / candidate).resolve()
    if not any(root.resolve() == resolved or root.resolve() in resolved.parents
               for root in ALLOWED_ROOTS):
        raise HTTPException(
            400, "la ruta debe estar bajo data/external/ o data/reference/")
    if not resolved.exists():
        raise HTTPException(404, f"no existe: {raw}")
    return resolved


@router.get("/meta", summary="Fuentes externas y estado de adquisición")
def meta() -> JSONResponse:
    return JSONResponse(
        content={
            "service_version": VERSION,
            "sources": registry.sources(),
            "municipalities": municipalities.summary()["counts"],
            "policy": {
                "imputes_values": False,
                "fabricates_series": False,
                "acquired_sources": ["municipality_crosswalk_2023"],
                "not_acquired": [s for s in registry.SOURCES
                                 if s != "municipality_crosswalk_2023"],
            },
        }, headers=_headers("onboarding"))


@router.get("/sources", summary="Registro de fuentes y requisitos")
def sources() -> JSONResponse:
    return JSONResponse(content=registry.sources(),
                        headers=_headers("onboarding"))


@router.get("/sources/{source_id}", summary="Ficha de una fuente externa")
def source(source_id: str) -> JSONResponse:
    try:
        payload = registry.source(source_id).as_dict()
    except KeyError as exc:
        raise HTTPException(404, str(exc).strip("'\"")) from None
    return JSONResponse(content=payload, headers=_headers("onboarding"))


@router.get("/municipalities/summary",
            summary="Correspondencia 2023: 14/44/262")
def crosswalk_summary() -> JSONResponse:
    try:
        payload = municipalities.summary()
    except Exception as exc:
        raise HTTPException(503, f"{type(exc).__name__}: {exc}") from None
    return JSONResponse(content=payload, headers=_headers("municipalities"))


@router.get("/municipalities/lookup",
            summary="Municipio vigente de un distrito histórico")
def crosswalk_lookup(district: str = Query(..., min_length=2),
                     department: str | None = None) -> JSONResponse:
    try:
        payload = municipalities.municipality_of(district, department)
    except Exception as exc:
        raise HTTPException(503, f"{type(exc).__name__}: {exc}") from None
    return JSONResponse(content=payload, headers=_headers("municipalities"))


@router.get("/municipalities/districts",
            summary="Distritos de un municipio vigente")
def crosswalk_districts(municipality: str = Query(..., min_length=2),
                        department: str | None = None) -> JSONResponse:
    try:
        payload = municipalities.districts_of(municipality, department)
    except Exception as exc:
        raise HTTPException(503, f"{type(exc).__name__}: {exc}") from None
    return JSONResponse(content=payload, headers=_headers("municipalities"))


@router.post("/validate", summary="Validar un archivo externo sin imputar")
def validate_file(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    kind = payload.get("kind")
    if not kind:
        raise HTTPException(400, "falta 'kind'")
    path = _resolve(payload.get("path"))
    try:
        report = validators.validate(kind, path)
    except KeyError as exc:
        raise HTTPException(400, str(exc).strip("'\"")) from None
    if report["n_rows"] == 0 and report["valid"]:
        report["valid"] = False
        report["errors"].append("el archivo no contiene filas")
        report["error_count"] = 1
    return JSONResponse(content=report, headers=_headers("onboarding"))


@router.post("/dem-error", summary="Error vertical del DEM con puntos GNSS")
def dem_error(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    path = _resolve(payload.get("path"))
    try:
        result = dem.dem_error(path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return JSONResponse(content=result, headers=_headers("dem"))
