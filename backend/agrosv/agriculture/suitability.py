"""AGROSV — CropSuitabilityEngine (Fase 6, §4.3).

Clasificación S1/S2/S3/N por **factores limitantes declarados**, inspirada en el
marco FAO de evaluación de tierras / zonificación agroecológica. No es el
algoritmo de PyAEZ ni usa sus LUT: es una reimplementación AGROSV con umbrales
explícitos y auditables.

Reglas:

* Cada factor se evalúa por separado y publica valor, umbral y clase.
* Si falta un factor **crítico**, el resultado es `not_evaluated`; no se
  completa con un supuesto ni se degrada silenciosamente la clase.
* Un factor no crítico ausente reduce la confianza y se declara.
* La ventana de crecimiento es la de 5 meses consecutivos con mayor
  precipitación (convención AGROSV), no un calendario de manejo.

Clases: S1 sin limitaciones, S2 una limitación moderada, S3 dos o más
moderadas, N al menos una severa.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..engines import governance as G5
from . import governance as AG
from .catalog import CROPS, CropKnowledgeEngine

ENGINE = "crop_suitability"
ENGINE_VERSION = AG.ENGINE_VERSION

GROWING_WINDOW_MONTHS = 5
MODERATE_TEMP_MARGIN_C = 3.0
MODERATE_PH_MARGIN = 0.5
SLOPE_MODERATE_FACTOR = 1.5

CLASS_LABELS = {
    "S1": "muy apto",
    "S2": "moderadamente apto",
    "S3": "marginalmente apto",
    "N": "no apto según los criterios evaluados",
    "not_evaluated": "no evaluado: faltan datos críticos",
}


class SuitabilityDataError(RuntimeError):
    """No hay datos suficientes para intentar la evaluación."""


@lru_cache(maxsize=1)
def _climatology() -> dict[str, Any]:
    from ..engines.climate import ClimateDataError, ClimateEngine

    engine = ClimateEngine()
    try:
        precip = engine.monthly_climatology("open_meteo_point", "precipitation",
                                           "sum")
        tmax = engine.monthly_climatology("open_meteo_point", "temperature",
                                          "max")
        tmin = engine.monthly_climatology("open_meteo_point", "temperature",
                                          "min")
        et0 = engine.monthly_climatology("open_meteo_point", "et0", "sum")
    except (ClimateDataError, G5.SourceUnavailableError) as exc:
        raise SuitabilityDataError(str(exc)) from None
    p = {row["month"]: row["mean"] for row in precip["months"]}
    hi = {row["month"]: row["mean"] for row in tmax["months"]}
    lo = {row["month"]: row["mean"] for row in tmin["months"]}
    e = {row["month"]: row["mean"] for row in et0["months"]}
    if any(v is None for v in p.values()):
        raise SuitabilityDataError("climatología de precipitación incompleta")
    return {"precip_mm": p, "tmax_c": hi, "tmin_c": lo, "et0_mm": e,
            "period": precip.get("period") or precip.get("method")}


def growing_window(precip_mm: dict[int, float],
                   length: int = GROWING_WINDOW_MONTHS) -> list[int]:
    """Ventana circular de `length` meses con mayor precipitación total."""
    best: tuple[float, int] | None = None
    for start in range(1, 13):
        months = [((start - 1 + i) % 12) + 1 for i in range(length)]
        total = sum(precip_mm[m] for m in months)
        if best is None or total > best[0]:
            best = (total, start)
    assert best is not None
    return [((best[1] - 1 + i) % 12) + 1 for i in range(length)]


def _factor(name: str, *, value: Any, unit: str, thresholds: Any,
            rating: str | None, critical: bool, note: str | None = None
            ) -> dict[str, Any]:
    return {
        "factor": name,
        "value": value,
        "unit": unit,
        "thresholds": thresholds,
        "rating": rating,          # none | moderate | severe | not_evaluated
        "critical": critical,
        "note": note,
    }


class CropSuitabilityEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self, catalog: CropKnowledgeEngine | None = None) -> None:
        self.catalog = catalog or CropKnowledgeEngine()

    # --- evaluación --------------------------------------------------------
    def evaluate(self, crop_id: str, lon: float, lat: float, *,
                 system: str = "rainfed",
                 irrigation_available: bool = False) -> dict[str, Any]:
        key = crop_id.strip().lower()
        if key not in CROPS:
            raise KeyError(f"cultivo desconocido: {crop_id}")
        if system not in {"rainfed", "irrigated", "urban", "periurban"}:
            raise ValueError("system debe ser rainfed, irrigated, urban o "
                             "periurban")
        record = CROPS[key]
        limitations: list[str] = []
        factors: list[dict[str, Any]] = []

        try:
            climate = _climatology()
        except SuitabilityDataError as exc:
            return self._unevaluated(key, lon, lat, system,
                                     reason=f"climatología no disponible: {exc}")

        window = growing_window(climate["precip_mm"])
        p_window = sum(climate["precip_mm"][m] for m in window)
        et0_window = (sum(climate["et0_mm"][m] for m in window)
                      if all(climate["et0_mm"].get(m) is not None
                             for m in window) else None)
        tmean_window = sum(
            (climate["tmax_c"].get(m, 0) + climate["tmin_c"].get(m, 0)) / 2
            for m in window) / len(window)
        tmax_window = max(climate["tmax_c"].get(m, float("-inf")) for m in window)
        tmin_window = min(climate["tmin_c"].get(m, float("inf")) for m in window)

        # --- temperatura ---------------------------------------------------
        opt = record["temperature"]["opt_c"]["value"]
        if opt:
            lo, hi = opt
            if lo <= tmean_window <= hi:
                rating, note = "none", None
            elif lo - MODERATE_TEMP_MARGIN_C <= tmean_window <= \
                    hi + MODERATE_TEMP_MARGIN_C:
                rating, note = "moderate", "media de la ventana fuera del óptimo"
            else:
                rating, note = "severe", "media de la ventana fuera del óptimo"
            factors.append(_factor(
                "temperature", value=round(tmean_window, 2), unit="degC",
                thresholds={"opt_c": opt,
                            "moderate_margin_c": MODERATE_TEMP_MARGIN_C},
                rating=rating, critical=True, note=note))
            factors.append(_factor(
                "temperature_extremes",
                value={"tmax_mean_c": round(tmax_window, 2),
                       "tmin_mean_c": round(tmin_window, 2)},
                unit="degC", thresholds=None, rating="not_evaluated",
                critical=False,
                note=("el catálogo no publica límites absolutos por cultivo; "
                      "solo se informan los extremos mensuales")))
        else:
            factors.append(_factor(
                "temperature", value=None, unit="degC", thresholds=None,
                rating="not_evaluated", critical=True,
                note="el catálogo no publica temperatura óptima"))

        # --- agua ----------------------------------------------------------
        etc = record["water"]["etc_season_mm"]["value"]
        if system in {"irrigated"}:
            if irrigation_available:
                factors.append(_factor(
                    "water", value={"precip_window_mm": round(p_window, 1),
                                   "etc_season_mm": etc},
                    unit="mm",
                    thresholds={"requirement": "riego declarado por el usuario"},
                    rating="none", critical=True,
                    note="la clase supone riego disponible; no se evalúa la fuente"))
            else:
                factors.append(_factor(
                    "water", value={"precip_window_mm": round(p_window, 1),
                                   "etc_season_mm": etc},
                    unit="mm", thresholds=None,
                    rating="not_evaluated", critical=True,
                    note=("no existe capa de acceso a riego; el usuario debe "
                          "declarar irrigation_available=True como supuesto")))
        elif system in {"urban", "periurban"}:
            factors.append(_factor(
                "water", value=p_window, unit="mm", thresholds=None,
                rating="not_evaluated", critical=True,
                note="no hay datos de agua disponible en agricultura urbana"))
        elif etc:
            etc_mid = sum(etc) / len(etc) if isinstance(etc, list) else etc
            ratio = p_window / etc_mid
            thresholds = {"ratio_precip_etc": [1.0, 0.7, 0.5],
                          "etc_used_mm": round(etc_mid, 1)}
            if ratio >= 1.0:
                rating = "none"
            elif ratio >= 0.7:
                rating = "moderate"
            elif ratio >= 0.5:
                rating = "severe"
            else:
                rating = "severe"
            factors.append(_factor(
                "water", value={"ratio": round(ratio, 3),
                               "precip_window_mm": round(p_window, 1),
                               "etc_season_mm": etc_mid},
                unit="ratio", thresholds=thresholds, rating=rating,
                critical=True,
                note=("proporción precipitación de la ventana / ETc de "
                      "referencia; no es un balance de suelo")))
        else:
            factors.append(_factor(
                "water", value=None, unit="mm", thresholds=None,
                rating="not_evaluated", critical=True,
                note="el catálogo no publica ETc estacional"))

        # --- suelo y terreno ----------------------------------------------
        ph, slope_pct, texture, elevation = self._soil_and_terrain(
            lon, lat, factors, limitations)
        ph_range = record["soil"]["ph_range"]["value"]
        if ph_range and ph is not None:
            lo, hi = ph_range
            if lo <= ph <= hi:
                rating = "none"
            elif lo - MODERATE_PH_MARGIN <= ph <= hi + MODERATE_PH_MARGIN:
                rating = "moderate"
            else:
                rating = "severe"
            factors.append(_factor(
                "ph", value=round(ph, 2), unit="pH",
                thresholds={"range": ph_range,
                            "moderate_margin": MODERATE_PH_MARGIN},
                rating=rating, critical=True))
        else:
            factors.append(_factor(
                "ph", value=ph, unit="pH", thresholds=ph_range,
                rating="not_evaluated", critical=True,
                note="pH ausente en el punto o rango ausente en el catálogo"))

        slope_max = record["soil"]["slope_max_pct"]["value"]
        if slope_max is not None and slope_pct is not None:
            if slope_pct <= slope_max:
                rating = "none"
            elif slope_pct <= slope_max * SLOPE_MODERATE_FACTOR:
                rating = "moderate"
            else:
                rating = "severe"
            factors.append(_factor(
                "slope", value=round(slope_pct, 2), unit="%",
                thresholds={"max_pct": slope_max,
                            "moderate_factor": SLOPE_MODERATE_FACTOR},
                rating=rating, critical=True))
        else:
            factors.append(_factor(
                "slope", value=slope_pct, unit="%", thresholds=slope_max,
                rating="not_evaluated",
                critical=slope_max is not None,
                note=("pendiente ausente o umbral no publicado")))

        depth_min = record["soil"]["depth_min_cm"]["value"]
        factors.append(_factor(
            "soil_depth", value=None, unit="cm",
            thresholds={"min_cm": depth_min},
            rating="not_evaluated", critical=False,
            note="SoilGrids se descargó agregado a 0–30 cm: no hay profundidad"))
        factors.append(_factor(
            "salinity", value=None, unit="dS/m", thresholds=None,
            rating="not_evaluated", critical=False,
            note="no hay dato de salinidad del suelo"))
        factors.append(_factor(
            "texture", value=texture, unit="USDA class",
            thresholds=record["soil"]["texture_pref"]["value"],
            rating="not_evaluated", critical=False,
            note=("el catálogo no publica preferencia textural por cultivo")))
        factors.append(_factor(
            "nutrients", value=None, unit="kg/ha", thresholds=None,
            rating="not_evaluated", critical=False,
            note=("no hay análisis de suelo ni recomendación de fertilización; "
                  "la demanda del cultivo no es una limitación medida")))

        # --- integración ---------------------------------------------------
        evaluated = [f for f in factors if f["rating"] not in
                     ("not_evaluated", None)]
        critical_missing = [f["factor"] for f in factors
                            if f["critical"] and f["rating"] ==
                            "not_evaluated"]
        severe = [f["factor"] for f in evaluated if f["rating"] == "severe"]
        moderate = [f["factor"] for f in evaluated if f["rating"] == "moderate"]

        if critical_missing:
            crop_class = "not_evaluated"
            limitations.append(
                "faltan factores críticos: " + ", ".join(critical_missing))
        elif severe:
            crop_class = "N"
        elif len(moderate) >= 2:
            crop_class = "S3"
        elif len(moderate) == 1:
            crop_class = "S2"
        else:
            crop_class = "S1"

        unevaluated = [f["factor"] for f in factors
                       if f["rating"] == "not_evaluated"]
        confidence = "alta" if not unevaluated else (
            "media" if len(unevaluated) <= 2 else "baja")
        limitations.extend([
            "clasificación de reglas AGROSV, no el algoritmo FAO/PyAEZ",
            "clima de un punto de reanálisis (2019–2025), no del lote",
            "suelo: predicción SoilGrids 250 m, 0–30 cm",
            "sin validación contra rendimientos observados",
            "una clase de aptitud no es una recomendación de siembra",
        ])
        if system != "rainfed":
            limitations.append(
                f"el sistema '{system}' se evalúa solo con los factores "
                "disponibles; los específicos (riego, espacio, luz) faltan")

        result = {
            "crop_id": key,
            "system": system,
            "class": crop_class,
            "class_label": CLASS_LABELS[crop_class],
            "limiting_factors": severe + moderate,
            "factors": factors,
            "critical_missing": critical_missing,
            "not_evaluated_factors": unevaluated,
            "confidence": confidence,
            "context": {
                "lon": lon, "lat": lat,
                "growing_window_months": window,
                "precip_window_mm": round(p_window, 1),
                "et0_window_mm": round(et0_window, 1) if et0_window else None,
                "tmean_window_c": round(tmean_window, 2),
                "slope_pct": slope_pct,
                "ph": ph,
                "elevation_m": elevation,
                "climate_point_note": ("climatología de reanálisis de un punto; "
                                       "no se interpola espacialmente"),
            },
            "rule": {
                "S1": "ninguna limitación moderada o severa",
                "S2": "una limitación moderada",
                "S3": "dos o más limitaciones moderadas",
                "N": "al menos una limitación severa",
                "not_evaluated": "falta al menos un factor crítico",
            },
        }
        return AG.envelope(
            ENGINE, result=result,
            sources=["crop_parameters_catalog", "copdem30", "soilgrids_2",
                     "open_meteo_point", "fao_aez"],
            limitations=limitations,
            processing=[
                AG.step("climatología mensual", "ClimateEngine"),
                AG.step("ventana de 5 meses más húmedos", "growing_window"),
                AG.step("muestreo de suelo y terreno", "SoilEngine/TerrainEngine"),
                AG.step("reglas de aptitud", "CropSuitabilityEngine.evaluate"),
            ],
            query={"crop_id": key, "lon": lon, "lat": lat, "system": system,
                   "irrigation_available": irrigation_available},
        )

    def _soil_and_terrain(self, lon: float, lat: float,
                          factors: list[dict[str, Any]],
                          limitations: list[str]
                          ) -> tuple[float | None, float | None,
                                     str | None, float | None]:
        from ..engines.soil import SoilEngine
        from ..engines.terrain import terrain_metrics

        ph = slope = None
        texture = None
        elevation = None
        try:
            terrain = terrain_metrics(lon, lat)
        except (G5.SourceUnavailableError, FileNotFoundError) as exc:
            terrain = {"available": False, "reason": str(exc)}
        if terrain.get("available"):
            elevation = terrain.get("elevation_m")
            slope = terrain.get("slope_pct")
        else:
            limitations.append(f"terreno no disponible: {terrain.get('reason')}")

        try:
            sample = SoilEngine().sample(lon, lat)
            props = sample["result"]["properties"]
            ph = props["ph"]["value"]
            derived = sample["result"].get("derived", {})
            texture_obj = derived.get("texture_class") or {}
            texture = texture_obj.get("usda_class")
            limitations.extend(sample.get("limitations", [])[:3])
        except (G5.SourceUnavailableError, FileNotFoundError, KeyError) as exc:
            limitations.append(f"suelo no disponible: {exc}")
        return ph, slope, texture, elevation

    def _unevaluated(self, crop_id: str, lon: float, lat: float, system: str,
                     *, reason: str) -> dict[str, Any]:
        return AG.envelope(
            ENGINE,
            result={
                "crop_id": crop_id, "system": system,
                "class": "not_evaluated",
                "class_label": CLASS_LABELS["not_evaluated"],
                "reason": reason, "factors": [],
                "critical_missing": ["clima"], "limiting_factors": [],
                "confidence": "sin datos",
            },
            sources=["crop_parameters_catalog", "fao_aez"],
            limitations=[reason,
                         "no se emite una clase cuando falta información crítica"],
            query={"crop_id": crop_id, "lon": lon, "lat": lat},
        )


__all__ = ["CropSuitabilityEngine", "SuitabilityDataError", "growing_window",
           "CLASS_LABELS", "GROWING_WINDOW_MONTHS"]
