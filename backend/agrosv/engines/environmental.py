"""AGROSV — EnvironmentalInteractionEngine (Fase 5, §7).

Une los cuatro motores anteriores en un **perfil ambiental documentado**. Su
función no es puntuar: es mostrar relaciones y restricciones con su regla.

Lo que produce:

    identification        país, departamento, municipio histórico, coords
    terrain               elevación, pendiente, aspecto, clase, TRI/TPI
    soil                  propiedades 0–30 cm, textura, materia orgánica
    hydrology             agua superficial mapeada, cuenca local, balance P−ET0
    climate               climatología del período, rachas, extremos, sequía
    constraints           reglas declaradas: variable, umbral, consecuencia
    data_coverage         qué componente existe y cuál no
    uncertainty           clase de evidencia y cuantificación por componente
    sources               ficha §8 de cada dataset usado
    processing_history    pasos ejecutados, con herramienta y parámetros

**No hay puntuación ambiental compuesta.** No se suman pendiente, pH y lluvia
porque no hay pesos validados ni una variable objetivo; un índice así ocultaría
las reglas y las ausencias. Si en el futuro se implementa uno, §7 exige fórmula,
variables, pesos, limitaciones y validación: este módulo lo rechaza mientras no
existan (`CompositeIndicatorError`).

El perfil es tolerante a fallos parciales: si falta una capa, ese componente se
marca `available: false` con el motivo y el resto se devuelve igualmente.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .. import config as C
from . import cache as CACHE
from . import climate as CL
from . import governance as G
from . import hydrology as HY
from . import soil as SL
from . import terrain as TM
from . import territorial as TR

ENGINE = "environmental"
ENGINE_VERSION = G.ENGINE_VERSION


class CompositeIndicatorError(ValueError):
    """Se intentó producir un índice compuesto sin metodología validada."""


# --- reglas de interacción ---------------------------------------------------
# Cada regla cruza dos dominios y declara su consecuencia. Son reglas
# agronómicas generales, no un modelo calibrado para El Salvador.
INTERACTION_RULES: tuple[dict[str, Any], ...] = (
    {
        "code": "erosion_pendiente_textura",
        "requires": ("slope_deg", "clay"),
        "test": lambda v: v["slope_deg"] >= 25.0 and v["clay"] < 35.0,
        "rule": ("pendiente ≥ 25° con textura no arcillosa: alta "
                 "susceptibilidad a erosión hídrica en cultivos anuales con "
                 "suelo desnudo"),
        "domains": ("terrain", "soil"),
        "implication": ("priorizar cobertura del suelo, terrazas o cultivos "
                        "perennes; verificar con erosión medida"),
    },
    {
        "code": "erosion_pendiente",
        "requires": ("slope_deg",),
        "test": lambda v: 12.0 <= v["slope_deg"] < 25.0,
        "rule": ("pendiente 12–25°: relieve pronunciado (clase 'quebrado'), "
                 "limita mecanización y aumenta el riesgo de erosión"),
        "domains": ("terrain",),
        "implication": "laboreo conservacionista; no es una prohibición de uso",
    },
    {
        "code": "infiltracion_baja_arcilla",
        "requires": ("clay", "slope_deg"),
        "test": lambda v: v["clay"] >= 35.0 and v["slope_deg"] < 5.0,
        "rule": ("arcilla ≥ 35 % en terreno casi plano: drenaje lento y riesgo "
                 "de encharcamiento"),
        "domains": ("soil", "terrain"),
        "implication": ("el balance P−ET0 no representa encharcamiento; el "
                        "estudio requiere permeabilidad medida"),
    },
    {
        "code": "deficit_hidrico",
        "requires": ("precipitation_mm", "et0_mm"),
        "test": lambda v: v["precipitation_mm"] - v["et0_mm"] < 0,
        "rule": "precipitación media anual < ET0 de referencia",
        "domains": ("climate", "hydrology"),
        "implication": ("déficit climático anual: la producción dependiente de "
                        "lluvia queda expuesta; no cuantifica riego necesario"),
    },
    {
        "code": "aridez",
        "requires": ("aridity_index",),
        "test": lambda v: v["aridity_index"] is not None and v["aridity_index"] < 0.5,
        "rule": "índice de aridez P/ET0 < 0,5 (criterio de tierras secas)",
        "domains": ("climate",),
        "implication": "condición semiárida del período analizado en ese punto",
    },
    {
        "code": "racha_seca_prolongada",
        "requires": ("max_dry_days",),
        "test": lambda v: v["max_dry_days"] is not None and v["max_dry_days"] >= 20,
        "rule": "racha seca máxima ≥ 20 días consecutivos con P < 1 mm",
        "domains": ("climate", "hydrology"),
        "implication": ("exposición a veranillos; su efecto depende de suelo y "
                        "cultivo, que no se modelan aquí"),
    },
    {
        "code": "suelo_superficial_limitado",
        "requires": ("soil_depth_cm",),
        "test": lambda v: v["soil_depth_cm"] is not None and v["soil_depth_cm"] < 50,
        "rule": "profundidad efectiva < 50 cm",
        "domains": ("soil",),
        "implication": "menor reservorio de agua y nutrientes",
    },
    # Las dos reglas siguientes declaran una AUSENCIA: por eso se ejecutan
    # también cuando el insumo es None (allow_missing). Sin ese indicador el
    # filtro general las descartaría y la ausencia nunca se publicaría.
    {
        "code": "sin_dato_de_profundidad",
        "requires": ("soil_depth_cm",),
        "allow_missing": True,
        "test": lambda v: v.get("soil_depth_cm") is None,
        "rule": ("profundidad efectiva no disponible en el repositorio: no se "
                 "asume un valor"),
        "domains": ("soil",),
        "implication": ("cualquier balance de agua del suelo quedaría incompleto; "
                        "se declara en vez de suponer"),
    },
    {
        "code": "cobertura_hidrica_incompleta",
        "requires": ("nearest_waterway_km",),
        "allow_missing": True,
        "test": lambda v: v.get("nearest_waterway_km") is None,
        "rule": "no hay cauce mapeado en el radio de búsqueda declarado",
        "domains": ("hydrology",),
        "implication": ("ausencia en OSM ≠ ausencia de agua; no se infiere "
                        "disponibilidad"),
    },
)


def apply_interaction_rules(values: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for rule in INTERACTION_RULES:
        if not rule.get("allow_missing") and any(
                values.get(key) is None for key in rule["requires"]):
            continue
        try:
            matched = bool(rule["test"](values))
        except (TypeError, KeyError):
            matched = False
        if matched:
            findings.append({
                "code": rule["code"],
                "rule": rule["rule"],
                "domains": list(rule["domains"]),
                "implication": rule["implication"],
                "inputs": {key: values.get(key) for key in rule["requires"]},
                "evidence_class": "derived_from_rule",
                "declares_absence": bool(rule.get("allow_missing")),
                "validated": False,
            })
    return findings


def _safe(name: str, builder, errors: dict[str, str]) -> Any:
    try:
        return builder()
    except Exception as exc:  # noqa: BLE001 — se declara el componente fallido
        errors[name] = f"{type(exc).__name__}: {exc}"
        return None


class EnvironmentalInteractionEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.territorial = TR.TerritorialEngine()
        self.soil = SL.SoilEngine()
        self.hydrology = HY.HydrologyEngine()
        self.climate = CL.ClimateEngine()

    def composite_indicator(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Rechazo explícito: §7 exige metodología validada antes de puntuar."""
        raise CompositeIndicatorError(
            "no se implementa un índice ambiental compuesto: no hay variables "
            "objetivo, pesos validados ni datos de referencia con los que "
            "verificarlo. El perfil devuelve hechos y reglas, no una puntuación.")

    def profile(self, lon: float, lat: float, *, size_m: float = 6000.0,
                radius_cells: int = 2, use_cache: bool = True) -> dict[str, Any]:
        lon, lat = TR.validate_coordinate(lon, lat)

        def build() -> dict[str, Any]:
            errors: dict[str, str] = {}
            steps = []

            steps.append(G.step("identificación territorial",
                                "agrosv.engines.territorial.locate"))
            location = _safe("territorial", lambda: TR.locate(lon, lat).as_dict(),
                             errors)
            steps.append(G.step("métricas de terreno",
                                "agrosv.engines.terrain.terrain_metrics",
                                radius_cells=radius_cells))
            terrain = _safe("terrain", lambda: TM.terrain_metrics(
                lon, lat, radius_cells=radius_cells), errors)
            steps.append(G.step("suelo 0–30 cm", "agrosv.engines.soil.SoilEngine.sample"))
            soil = _safe("soil", lambda: self.soil.sample(lon, lat)["result"],
                         errors)
            steps.append(G.step("hidrología superficial y cuenca local",
                                "agrosv.engines.hydrology", size_m=size_m))
            surface = _safe("surface_water", lambda: HY.surface_water(lon, lat),
                            errors)
            basin = _safe("watershed", lambda: HY.watershed_from_point(
                lon, lat, size_m=size_m) | {"mask": None}, errors)
            if isinstance(basin, dict):
                basin.pop("mask", None)
            balance = _safe("water_balance", lambda: HY.water_balance(lon, lat),
                            errors)
            steps.append(G.step("climatología del punto más cercano",
                                "agrosv.engines.climate.ClimateEngine.profile"))
            climate = _safe("climate", lambda: self.climate.profile(lon, lat),
                            errors)

            values = self._constraint_inputs(terrain, soil, basin, surface,
                                             balance, climate)
            constraints = apply_interaction_rules(values)

            coverage = self._coverage(location, terrain, soil, surface, basin,
                                      balance, climate, errors)
            uncertainty = self._uncertainty(terrain, soil, climate, balance)

            result = {
                "identification": location,
                "terrain": terrain,
                "soil": soil,
                "hydrology": {
                    "surface_water": surface,
                    "watershed": basin,
                    "water_balance": balance,
                    "groundwater": HY.groundwater_availability(),
                },
                "climate": climate,
                "environmental_constraints": constraints,
                "environmental_profile_rule": (
                    "el perfil enumera hechos y reglas; no produce una "
                    "puntuación ni una recomendación de uso"),
                "data_coverage": coverage,
                "uncertainty": uncertainty,
                "component_errors": errors,
                "processing_history": steps,
            }
            envelope = G.envelope(
                ENGINE,
                result=result,
                sources=["copdem30", "geoboundaries_adm1", "soilgrids_2",
                         "osm_sv", "nasa_power_point", "open_meteo_point"],
                limitations=[
                    "no hay índice compuesto: no existen pesos validados",
                    "el clima proviene de dos puntos de reanálisis, no del lugar",
                    "el suelo es una predicción global 250 m de 0–30 cm",
                    "no hay agua subterránea, profundidad de suelo, AWC ni "
                    "datos de estaciones",
                    "las reglas de interacción son generales y no están "
                    "validadas con rendimientos locales",
                    "un perfil completo no es una validación científica",
                ],
                processing=steps,
                query={"lon": lon, "lat": lat, "size_m": size_m,
                       "radius_cells": radius_cells},
                coverage=G.coverage_statement(),
                extra={"uncertainty_policy": (
                    "cada componente conserva su clase de evidencia; ninguno se "
                    "cuantifica con datos de referencia porque no existen")},
            )
            return envelope

        payload, info = CACHE.DerivedCache().get_or_compute(
            engine=ENGINE, version=self.version,
            params={"lon": round(lon, 6), "lat": round(lat, 6),
                    "size_m": size_m, "radius_cells": radius_cells},
            paths=[C.DEM_WGS84, C.SLOPE, C.ASPECT, C.RELIEF_CLASS,
                   C.TERRITORY_GPKG, C.INFRA_GPKG,
                   *[C.SOILS_RASTER_DIR / spec["file"]
                     for spec in SL.SOIL_VARIABLES.values()],
                   CL.DB_PATH],
            build=build, use_cache=use_cache)
        payload["cache"] = info.as_dict()
        return payload

    # --- composición de entradas de reglas ---------------------------------
    @staticmethod
    def _constraint_inputs(terrain, soil, basin, surface, balance,
                           climate) -> dict[str, Any]:
        properties = (soil or {}).get("properties", {})
        return {
            "slope_deg": (terrain or {}).get("slope_deg"),
            "clay": (properties.get("clay") or {}).get("value"),
            "sand": (properties.get("sand") or {}).get("value"),
            "ph": (properties.get("ph") or {}).get("value"),
            "soil_organic_carbon": (properties.get("soil_organic_carbon")
                                    or {}).get("value"),
            "precipitation_mm": ((balance or {}).get("mean") or {}).get(
                "precipitation_mm"),
            "et0_mm": ((balance or {}).get("mean") or {}).get("et0_mm"),
            "aridity_index": ((balance or {}).get("mean") or {}).get(
                "aridity_index_p_over_et0"),
            "max_dry_days": (((climate or {}).get("result") or {})
                             .get("dry_spells") or {}).get("series_max_dry_days"),
            "soil_depth_cm": None,
            "nearest_waterway_km": (((surface or {}).get("nearest_waterway")
                                     or {}).get("distance_km")),
        }

    @staticmethod
    def _coverage(location, terrain, soil, surface, basin, balance, climate,
                  errors) -> dict[str, Any]:
        return {
            "identification": {
                "available": location is not None,
                "levels": ["country", "department", "municipality_historic"],
                "missing": ["municipality_2023", "district"],
            },
            "terrain": {
                "available": bool((terrain or {}).get("available")),
                "resolution": "30 m (DSM)",
                "extent": "nacional",
            },
            "soil": {
                "available": any((p or {}).get("available") for p in
                                 ((soil or {}).get("properties") or {}).values()),
                "depth": "0–30 cm",
                "resolution": "250 m",
                "note": "predicción, no medición",
            },
            "surface_water": {
                "available": bool((surface or {}).get("available")),
                "note": "OSM: cobertura incompleta",
            },
            "watershed": {
                "available": basin is not None,
                "truncated": (basin or {}).get("truncated"),
                "note": "derivación D8 local; no es cuenca oficial",
            },
            "water_balance": {
                "available": bool((balance or {}).get("available")),
                "note": "P−ET0 de reanálisis; no es caudal ni recarga",
            },
            "groundwater": {"available": False,
                            "reason": "sin capa ni series"},
            "climate": {
                "available": climate is not None,
                "points": 2,
                "spatial_representativity": "no evaluada; el punto está a "
                                            "distancia declarada",
            },
            "failed_components": errors,
        }

    @staticmethod
    def _uncertainty(terrain, soil, climate, balance) -> dict[str, Any]:
        return {
            "terrain": {
                "evidence_class": "modeled_prediction",
                "components": {
                    "vertical": "no cuantificada (sin puntos de control)",
                    "horizontal": "no cuantificada",
                    "model": "DSM incluye dosel y edificios",
                },
                "confidence": "baja",
            },
            "soil": {
                "evidence_class": "modeled_prediction",
                "components": {
                    "model": "error de SoilGrids no declarado por celda",
                    "spatial": "soporte de 250 m y agregación 0–30 cm",
                    "measurement": "no aplica: no hay medición",
                    "provenance": "cadena de custodia del producto global",
                },
                "confidence": "baja",
            },
            "climate": {
                "evidence_class": "reanalysis",
                "components": {
                    "model": "reanálisis de celda gruesa",
                    "spatial": "representatividad de celda, no de punto",
                    "temporal": "serie 2019–2025, sin homogeneización",
                    "measurement": "no aplica: no hay estación",
                },
                "confidence": "baja",
            },
            "hydrology": {
                "evidence_class": "simulation",
                "components": {
                    "model": "D8 y Budyko no calibrados",
                    "spatial": "DEM 30 m y ventana finita",
                },
                "confidence": "baja",
                "note": (balance or {}).get("uncertainty"),
            },
            "aggregate": {
                "quantified": False,
                "reason": (
                    "no hay datos de referencia para cuantificar ningún "
                    "componente; publicar un compuesto numérico sería inventarlo"),
                "policy": "confianza 'baja' en todo el perfil",
            },
        }

    # --- entorno cercano ----------------------------------------------------
    def neighbors(self, lon: float, lat: float, *, radius_km: float = 25.0,
                  limit: int = 10) -> dict[str, Any]:
        """Puntos climáticos y ocurrencias cercanas: contexto, no interpolación."""
        pts = []
        for point in CL.points():
            distance = CL.haversine_km(lon, lat, point["longitude"],
                                       point["latitude"])
            if distance <= radius_km:
                pts.append({**point, "distance_km": round(distance, 2)})
        return {
            "climate_points": sorted(pts, key=lambda p: p["distance_km"]),
            "radius_km": radius_km,
            "limit": limit,
            "note": ("se listan puntos existentes dentro del radio; no se crean "
                     "puntos nuevos ni se interpola entre ellos"),
        }


__all__ = [
    "EnvironmentalInteractionEngine", "INTERACTION_RULES",
    "apply_interaction_rules", "CompositeIndicatorError",
]
