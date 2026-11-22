"""AGROSV — API socio-agrícola sintética bajo `/api/social`.

Ningún endpoint devuelve datos observados. Toda respuesta declara
`synthetic: true`, `represents_real_people: false` y
`population_inference_allowed: false`.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from ..engines import governance as G5
from . import governance as SG
from . import saltbor_adapter
from .adoption import AdoptionError, TechnologyAdoptionEngine
from .behavior import BehaviorError, FarmerBehaviorEngine
from .economy import AgriculturalEconomyEngine, EconomyError
from .household import AgriculturalHouseholdEngine
from .multiagent import AgriculturalMultiAgentEngine, MultiAgentError
from .persona import AgriculturalPersonaEngine, PersonaError
from .population import AgriculturalPopulationEngine, PopulationError
from .resilience import AgriculturalResilienceEngine, ResilienceError

router = APIRouter(prefix="/api/social", tags=["social"])
SERVICE_VERSION = SG.ENGINE_VERSION

population = AgriculturalPopulationEngine()
persona = AgriculturalPersonaEngine()
household = AgriculturalHouseholdEngine()
behavior = FarmerBehaviorEngine()
economy = AgriculturalEconomyEngine()
adoption = TechnologyAdoptionEngine()
resilience = AgriculturalResilienceEngine()
multiagent = AgriculturalMultiAgentEngine()


def _headers(engine: str) -> dict[str, str]:
    return {"X-AGROSV-Engine": engine, "X-AGROSV-Version": SERVICE_VERSION,
            "X-AGROSV-Synthetic": "true"}


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(404, str(exc).strip("'\""))
    if isinstance(exc, G5.SourceUnavailableError):
        return HTTPException(503, str(exc))
    if isinstance(exc, (PopulationError, PersonaError, BehaviorError,
                        EconomyError, AdoptionError, ResilienceError,
                        MultiAgentError, ValueError)):
        return HTTPException(400, str(exc))
    return HTTPException(500, f"{type(exc).__name__}: {exc}")


def _agent(*, seed: int, index: int, size: int | None = None) -> dict[str, Any]:
    total = size or index + 1
    if index < 0 or index >= total:
        raise HTTPException(400, "index debe estar en [0, size)")
    generated = population.generate(total, seed=seed)
    return generated["result"]["agents"][index]


@router.get("/meta", summary="Motores sociales, capas y política")
def meta() -> JSONResponse:
    return JSONResponse(
        content={
            "service_version": SERVICE_VERSION,
            "layers": list(SG.LAYERS),
            "engines": ["agricultural_population", "agricultural_persona",
                        "agricultural_household", "farmer_behavior",
                        "agricultural_economy", "technology_adoption",
                        "agricultural_resilience",
                        "agricultural_multiagent"],
            "policy": {
                "synthetic_only": True,
                "represents_real_people": False,
                "population_inference_allowed": False,
                "llm_used": False,
                "empirical_validation": False,
            },
            "nemotron": SG.NEMOTRON,
        },
        headers=_headers("social"))


@router.get("/layers", summary="Capas de datos y su separación")
def layers() -> JSONResponse:
    return JSONResponse(content={
        "layers": [{"layer": layer,
                    "synthetic": layer != "OBSERVED_VALIDATION_DATA",
                    "description": {
                        "SOURCE_PROFILE": "perfil de origen Nemotron o "
                                          "esquema compatible",
                        "SYNTHETIC_AGRICULTURAL_STATE": "variables agrícolas "
                                                        "generadas",
                        "HOUSEHOLD_STATE": "hogar y recursos sintéticos",
                        "SIMULATION_HISTORY": "decisiones y resultados",
                        "OBSERVED_VALIDATION_DATA": "evidencia real "
                                                    "independiente; no generada",
                    }[layer]} for layer in SG.LAYERS],
        "rule": "nunca se fusionan; se transportan con procedencia",
    }, headers=_headers("governance"))


@router.get("/archetypes", summary="Arquetipos de simulación (no censo)")
def archetypes() -> JSONResponse:
    return JSONResponse(content=population.archetypes(),
                        headers=_headers("agricultural_population"))


@router.get("/technologies", summary="Tecnologías y requisitos cualitativos")
def technologies() -> JSONResponse:
    return JSONResponse(content=adoption.technologies(),
                        headers=_headers("technology_adoption"))


@router.get("/shocks", summary="Choques de escenario")
def shocks() -> JSONResponse:
    return JSONResponse(content=resilience.shocks(),
                        headers=_headers("agricultural_resilience"))


@router.get("/personas/sample", summary="Filas reales de la muestra Nemotron")
def sample(limit: int = Query(3, ge=1, le=3)) -> JSONResponse:
    try:
        payload = persona.sample_profiles(limit)
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=payload, headers=_headers("persona"))


@router.post("/population", summary="Generar población sintética")
def generate_population(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        result = population.generate(
            int(payload.get("size", 100)),
            seed=int(payload.get("seed", 42)),
            archetypes=payload.get("archetypes"),
            weights=payload.get("weights"))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result,
                        headers=_headers("agricultural_population"))


@router.post("/persona", summary="Componer persona sintética")
def compose_persona(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        agent = _agent(seed=int(payload.get("seed", 42)),
                       index=int(payload.get("index", 0)))
        source = None
        if payload.get("source") == "sample":
            samples = persona.sample_profiles()
            source = samples["profiles"][int(payload.get("sample_index", 0))]
        result = persona.compose(
            agent, source_profile=source,
            allow_role_extension=bool(payload.get("allow_role_extension",
                                                  False)))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("persona"))


@router.post("/household", summary="Componer hogar sintético")
def compose_household(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        agent = _agent(seed=int(payload.get("seed", 42)),
                       index=int(payload.get("index", 0)))
        profile = persona.synthetic_source_profile(
            agent, seed=int(payload.get("seed", 42)))["profile"]
        result = household.compose(agent, profile=profile,
                                   seed=int(payload.get("seed", 42)))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("household"))


@router.post("/behavior", summary="Decisión MAUT inspeccionable")
def run_behavior(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    options = payload.get("options")
    if not options:
        raise HTTPException(400, "se requiere 'options'")
    try:
        agent = _agent(seed=int(payload.get("seed", 42)),
                       index=int(payload.get("index", 0)))
        result = behavior.choose(options, agent["state"]["payload"],
                                 context=payload.get("context"),
                                 threshold=float(payload.get("threshold", 0.0)))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("behavior"))


@router.post("/economy", summary="Margen con hoja de costos y precios aportada")
def run_economy(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    for field in ("costs", "prices", "yield_t_ha"):
        if payload.get(field) is None:
            raise HTTPException(400, f"falta '{field}'")
    try:
        agent = _agent(seed=int(payload.get("seed", 42)),
                       index=int(payload.get("index", 0)))
        result = economy.evaluate(
            agent=agent, costs=payload["costs"], prices=payload["prices"],
            yield_t_ha=float(payload["yield_t_ha"]),
            area_ha=payload.get("area_ha"))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("economy"))


@router.post("/adoption", summary="Propensión a adoptar una tecnología")
def run_adoption(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    technology = payload.get("technology_id")
    if not technology:
        raise HTTPException(400, "falta 'technology_id'")
    try:
        agent = _agent(seed=int(payload.get("seed", 42)),
                       index=int(payload.get("index", 0)))
        result = adoption.evaluate(agent, technology,
                                   threshold=float(payload.get("threshold",
                                                               0.55)))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("adoption"))


@router.post("/resilience", summary="Impacto de un choque (índice sintético)")
def run_resilience(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    shock = payload.get("shock_id")
    if not shock:
        raise HTTPException(400, "falta 'shock_id'")
    try:
        seed = int(payload.get("seed", 42))
        agent = _agent(seed=seed, index=int(payload.get("index", 0)))
        profile = persona.synthetic_source_profile(agent, seed=seed)["profile"]
        home = household.compose(agent, profile=profile, seed=seed)
        result = resilience.assess(agent, home["household"], shock_id=shock)
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("resilience"))


@router.post("/multiagent", summary="Difusión multiagente reproducible")
def run_multiagent(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        src_mode = str(payload.get("population_source", "synthetic")).lower()
        if src_mode == "nemotron":
            generated = population.generate_from_nemotron(
                int(payload.get("size", 50)),
                seed=int(payload.get("seed", 42)),
                department=payload.get("department"),
                municipality=payload.get("municipality"),
                area=payload.get("area"),
            )
        else:
            generated = population.generate(
                int(payload.get("size", 50)),
                seed=int(payload.get("seed", 42)),
            )
        result = multiagent.run(
            generated["result"]["agents"],
            steps=int(payload.get("steps", 10)),
            seed=int(payload.get("social_seed", 7)),
            practice=payload.get("practice", "drip_irrigation"),
            threshold=float(payload.get("threshold", 0.55)),
            shock=payload.get("shock_id"))
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result,
                        headers=_headers("multiagent"))


@router.get("/nemotron/agricultural", summary="Perfiles agrícolas reales de Nemotron SV")
def nemotron_agricultural(
    department: str | None = Query(None),
    municipality: str | None = Query(None),
    area: str | None = Query(None),
    archetype: str | None = Query(None),
    occupation: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    live: bool = Query(False),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    try:
        payload = persona.nemotron_agricultural_profiles(
            department=department,
            municipality=municipality,
            area=area,
            archetype=archetype,
            occupation_query=occupation,
            limit=limit,
            live=live,
            offset=offset,
        )
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=payload, headers=_headers("nemotron"))


@router.post("/nemotron/population", summary="Población agrícola anclada a Nemotron SV")
def generate_nemotron_population(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        result = population.generate_from_nemotron(
            int(payload.get("size", 20)),
            seed=int(payload.get("seed", 42)),
            department=payload.get("department"),
            municipality=payload.get("municipality"),
            area=payload.get("area"),
            archetype=payload.get("archetype"),
            live=bool(payload.get("live", False)),
            offset=int(payload.get("offset", 0)),
        )
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result, headers=_headers("nemotron_population"))


@router.get("/saltbor/contract", summary="Contrato de interoperabilidad E7 con IKarosUnic/sv-people")
def saltbor_contract() -> JSONResponse:
    return JSONResponse(content={
        "contract_version": saltbor_adapter.CONTRACT_VERSION,
        "target_repo": saltbor_adapter.TARGET_REPO,
        "coupling": "http_json_only",
        "exports_to_sv_people": [
            "saltbor.population.factory.PopulationFactory.create_from_profiles",
            "saltbor.domain.agriculture.FarmPlot",
        ],
        "imports_from_sv_people": ["profiles", "humans", "farm_plots"],
        "manzana_to_ha": saltbor_adapter.MANZANA_TO_HA,
        "nemotron_dataset": SG.NEMOTRON,
    }, headers=_headers("saltbor_adapter"))


@router.post("/saltbor/export", summary="Exportar población/parcelas AGROSV+Nemotron hacia sv-people")
def saltbor_export(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    try:
        size = int(payload.get("size", 10))
        seed = int(payload.get("seed", 42))
        src_mode = str(payload.get("population_source", "nemotron")).lower()
        if src_mode == "nemotron":
            generated = population.generate_from_nemotron(
                size=size,
                seed=seed,
                department=payload.get("department"),
                municipality=payload.get("municipality"),
                area=payload.get("area"),
                archetype=payload.get("archetype"),
                live=bool(payload.get("live", False)),
                scenario_id=payload.get("scenario_id"),
            )
        else:
            generated = population.generate(
                size=size, seed=seed, scenario_id=payload.get("scenario_id")
            )
        bundle = saltbor_adapter.to_saltbor_bundle(
            generated["result"]["agents"],
            scenario_id=payload.get("scenario_id"),
            soil_moisture_level=float(payload.get("soil_moisture_level", 0.75)),
            current_growth_stage=str(payload.get("current_growth_stage", "vegetative")),
        )
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=bundle, headers=_headers("saltbor_adapter"))


@router.post("/saltbor/import", summary="Importar perfiles/parcelas desde sv-people hacia AGROSV")
def saltbor_import(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        imported = saltbor_adapter.from_saltbor_payload(payload)
        if payload.get("evaluate_suitability") and payload.get("lat") is not None and payload.get("lon") is not None:
            from ..agriculture.suitability import CropSuitabilityEngine

            suit_engine = CropSuitabilityEngine()
            lat = float(payload["lat"])
            lon = float(payload["lon"])
            evaluations = []
            for agent in imported["agents"]:
                crop_id = agent["state"]["payload"]["primary_crop"]
                ev = suit_engine.evaluate(
                    crop_id, lon, lat,
                    irrigation_available=bool(agent["state"]["payload"].get("irrigated")),
                )
                evaluations.append({
                    "agent_id": agent["agent_id"],
                    "crop_id": crop_id,
                    "suitability_class": ev["result"]["class"],
                    "limiting_factors": ev["result"].get("limiting_factors", []),
                })
            imported["agronomic_evaluations"] = evaluations
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=imported, headers=_headers("saltbor_adapter"))


@router.get("/separation", summary="Verificar separación de capas")
def separation() -> JSONResponse:
    try:
        samples = persona.sample_profiles()
        result = SG.check_separation(samples["records"])
    except Exception as exc:
        raise _error(exc) from None
    return JSONResponse(content=result,
                        headers=_headers("governance"))
