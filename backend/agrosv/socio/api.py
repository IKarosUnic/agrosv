"""AGROSV — API de simulación socio-agrícola bajo `/api/socio`."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

from ..engines import governance as G5
from ..engines.territorial import CoverageError, validate_coordinate
from ..agriculture import governance as AG
from ..social import governance as SG
from ..social.population import AgriculturalPopulationEngine
from .analysis import AnalysisError, SocioAgriculturalAnalysisEngine
from .decision import AgriculturalDecisionEngine, DecisionError
from .integration import IntegrationError, SocioAgriculturalIntegrationEngine
from .scenario import AgriculturalScenarioEngine, ScenarioError

router = APIRouter(prefix="/api/socio", tags=["socio"])
SERVICE_VERSION = AG.ENGINE_VERSION

integration = SocioAgriculturalIntegrationEngine()
decision = AgriculturalDecisionEngine()
scenario = AgriculturalScenarioEngine()
analysis = SocioAgriculturalAnalysisEngine()
population = AgriculturalPopulationEngine()


def _headers(engine: str) -> dict[str, str]:
    return {"X-AGROSV-Engine": engine, "X-AGROSV-Version": SERVICE_VERSION,
            "X-AGROSV-Synthetic": "mixed"}


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
    if isinstance(exc, (ValueError, ScenarioError, DecisionError,
                        IntegrationError, AnalysisError)):
        return HTTPException(400, str(exc))
    return HTTPException(500, f"{type(exc).__name__}: {exc}")


@router.get("/meta", summary="Motores integrados y reglas de composición")
def meta() -> JSONResponse:
    return JSONResponse(content={
        "service_version": SERVICE_VERSION,
        "engines": ["socio_agricultural_integration", "agricultural_decision",
                    "agricultural_scenario", "socio_agricultural_analysis"],
        "llm_used": False,
        "synthetic_components": True,
        "rule": ("los cálculos agronómicos pertenecen a los motores "
                 "científicos; los componentes sintéticos aportan contexto "
                 "humano y decisiones"),
    }, headers=_headers("socio"))


@router.get("/scenarios", summary="Escenarios A–G")
def scenarios() -> JSONResponse:
    return JSONResponse(content=scenario.scenarios(),
                        headers=_headers("scenario"))


@router.get("/research-questions", summary="Preguntas de investigación")
def questions() -> JSONResponse:
    return JSONResponse(content=analysis.research_questions(),
                        headers=_headers("analysis"))


@router.post("/integrate", summary="Perfil agronómico + contexto humano")
def integrate(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    for field in ("crop_id", "lat", "lon"):
        if payload.get(field) is None:
            raise HTTPException(400, f"falta '{field}'")
    lat, lon = _coord(float(payload["lat"]), float(payload["lon"]))
    try:
        agent = None
        if payload.get("include_human"):
            if str(payload.get("population_source", "synthetic")).lower() == "nemotron":
                generated = population.generate_from_nemotron(
                    int(payload.get("size", 1)),
                    seed=int(payload.get("seed", 42)),
                    department=payload.get("department"),
                    municipality=payload.get("municipality"),
                    area=payload.get("area"),
                )
            else:
                generated = population.generate(
                    int(payload.get("size", 1)),
                    seed=int(payload.get("seed", 42)))
            agent = generated["result"]["agents"][0]
        result = integration.profile(
            lon=lon, lat=lat, crop_id=payload["crop_id"],
            system=payload.get("system", "rainfed"),
            planting_date=payload.get("planting_date"),
            awc_mm_per_m=payload.get("awc_mm_per_m"),
            root_depth_cm=payload.get("root_depth_cm"),
            initial_depletion_mm=float(payload.get("initial_depletion_mm",
                                                   0.0)),
            kc=payload.get("kc"),
            allow_reference_kc=bool(payload.get("allow_reference_kc", False)),
            agent=agent, seed=int(payload.get("seed", 42)))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("integration"))


@router.post("/decision", summary="Decisión agrícola con restricciones")
def run_decision(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    for field in ("lat", "lon"):
        if payload.get(field) is None:
            raise HTTPException(400, f"falta '{field}'")
    lat, lon = _coord(float(payload["lat"]), float(payload["lon"]))
    try:
        if str(payload.get("population_source", "synthetic")).lower() == "nemotron":
            generated = population.generate_from_nemotron(
                int(payload.get("size", 1)),
                seed=int(payload.get("seed", 42)),
                department=payload.get("department"),
                municipality=payload.get("municipality"),
                area=payload.get("area"),
            )
        else:
            generated = population.generate(
                int(payload.get("size", 1)), seed=int(payload.get("seed", 42)))
        agent = generated["result"]["agents"][int(payload.get("index", 0))]
        result = decision.decide(
            agent=agent, lon=lon, lat=lat,
            options=payload.get("options"),
            context=payload.get("context"),
            require_evaluated=bool(payload.get("require_evaluated", True)))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("decision"))


@router.post("/scenario", summary="Ejecutar un escenario A–G")
def run_scenario(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    for field in ("scenario_id", "lat", "lon"):
        if payload.get(field) is None:
            raise HTTPException(400, f"falta '{field}'")
    lat, lon = _coord(float(payload["lat"]), float(payload["lon"]))
    try:
        result = scenario.run(
            payload["scenario_id"], lon=lon, lat=lat,
            size=int(payload.get("size", 60)),
            seed=int(payload.get("seed", 42)),
            costs=payload.get("costs"), prices=payload.get("prices"),
            yield_t_ha=payload.get("yield_t_ha"),
            population_source=payload.get("population_source", "synthetic"),
            department=payload.get("department"),
            municipality=payload.get("municipality"),
            area=payload.get("area"))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("scenario"))


@router.post("/analysis", summary="Comparar escenarios y restricciones")
def run_analysis(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    runs_request = payload.get("runs") or []
    if not runs_request:
        raise HTTPException(400, "se requiere 'runs'")
    if len(runs_request) > 7:
        raise HTTPException(400, "máximo 7 corridas por análisis")
    results = []
    try:
        for item in runs_request:
            lat, lon = _coord(float(item["lat"]), float(item["lon"]))
            results.append(scenario.run(
                item["scenario_id"], lon=lon, lat=lat,
                size=int(item.get("size", 60)),
                seed=int(item.get("seed", 42))))
    except Exception as exc:
        raise _error(exc) from None
    comparison = analysis.compare(results)
    comparison["findings"] = analysis.findings(results)["findings"]
    return JSONResponse(content=comparison, headers=_headers("analysis"))
