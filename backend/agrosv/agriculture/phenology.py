"""AGROSV — CropPhenologyEngine (Fase 6, §4.2).

Desarrollo por **tiempo térmico** (growing degree days) con parámetros
explícitos. No se implementa fotoperíodo ni respuesta a estrés hídrico: se
declaran como no disponibles en lugar de aproximarlos sin modelo.

    GDD_día = max(0, (Tmax + Tmin)/2 − Tbase)

El objetivo de GDD a madurez puede:

* provenir de la variedad (`gdd_to_maturity`, estado REF/SCENARIO), o
* derivarse del ciclo del catálogo y del clima del período
  (`MODEL_DERIVED`, con rango de incertidumbre por el ciclo mínimo/máximo).

Una fecha de madurez derivada **no** es una recomendación de siembra ni un
calendario validado.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable, Sequence

from ..engines import governance as G5
from . import governance as AG
from .catalog import CROPS, CropKnowledgeEngine

ENGINE = "crop_phenology"
ENGINE_VERSION = AG.ENGINE_VERSION

DEFAULT_STAGES: tuple[tuple[str, float], ...] = (
    ("emergence", 0.08),
    ("vegetative", 0.45),
    ("flowering", 0.62),
    ("grain_fill", 0.85),
    ("maturity", 1.00),
)

WEATHER_DATASET = "open_meteo_point"
WEATHER_DATASET_FALLBACK = "nasa_power_point"


class PhenologyError(ValueError):
    """Parámetros insuficientes o inconsistentes."""


def _as_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise PhenologyError(f"fecha inválida: {value!r}; use YYYY-MM-DD") from None


def daily_gdd(tmin: float, tmax: float, tbase_c: float,
              tmax_cap_c: float | None = None) -> float:
    """GDD de un día por el método de la media, acotado inferiormente a 0."""
    if tmax < tmin:
        tmin, tmax = tmax, tmin
    if tmax_cap_c is not None:
        tmax = min(tmax, tmax_cap_c)
        tmin = min(tmin, tmax_cap_c)
    return max(0.0, (tmax + tmin) / 2.0 - tbase_c)


def accumulate(tmin: Sequence[float], tmax: Sequence[float], tbase_c: float,
               *, tmax_cap_c: float | None = None) -> list[float]:
    total = 0.0
    out = []
    for lo, hi in zip(tmin, tmax):
        total += daily_gdd(lo, hi, tbase_c, tmax_cap_c)
        out.append(round(total, 2))
    return out


def _weather_series(dataset_id: str) -> dict[str, dict[str, float]]:
    """Series diarias Tmin/Tmax del punto de reanálisis (no interpoladas)."""
    from ..engines.climate import ClimateDataError, ClimateEngine

    engine = ClimateEngine()
    try:
        lo = engine.series(dataset_id, "temperature", "min")
        hi = engine.series(dataset_id, "temperature", "max")
    except (ClimateDataError, G5.SourceUnavailableError):
        if dataset_id == WEATHER_DATASET_FALLBACK:
            raise
        return _weather_series(WEATHER_DATASET_FALLBACK)
    tmin = {row["date"]: float(row["value"]) for row in lo["series"]}
    tmax = {row["date"]: float(row["value"]) for row in hi["series"]}
    return {d: {"tmin": tmin[d], "tmax": tmax[d]}
            for d in sorted(set(tmin) & set(tmax))}


class CropPhenologyEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self, catalog: CropKnowledgeEngine | None = None) -> None:
        self.catalog = catalog or CropKnowledgeEngine()

    # --- parámetros --------------------------------------------------------
    def resolve_parameters(self, crop_id: str, variety: dict[str, Any] | None
                           ) -> dict[str, Any]:
        record = CROPS.get(crop_id.lower())
        if record is None:
            raise KeyError(f"cultivo desconocido: {crop_id}")
        variety = dict(variety or {})
        tbase = variety.get("tbase_c", record["temperature"]["tbase_c"]["value"])
        if tbase is None:
            raise PhenologyError(
                f"{crop_id}: no hay temperatura base en el catálogo ni en la "
                "variedad; no se estima")
        fractions = variety.get("stage_fractions") or dict(DEFAULT_STAGES)
        self._check_fractions(fractions)
        target = variety.get("gdd_to_maturity")
        target_status = "REF" if target is not None else None
        uncertainty = None
        assumptions = [
            "método de la media diaria (Tmax+Tmin)/2 − Tbase",
            "sin fotoperíodo, sin vernalización y sin efecto del estrés hídrico",
        ]
        if target is not None:
            target = float(target)
            if target <= 0:
                raise PhenologyError("gdd_to_maturity debe ser > 0")
        return {
            "crop_id": crop_id.lower(),
            "tbase_c": float(tbase),
            "tmax_cap_c": variety.get("tmax_cap_c"),
            "gdd_to_maturity": target,
            "gdd_status": target_status,
            "stage_fractions": {k: float(v) for k, v in fractions.items()},
            "uncertainty_gdd": uncertainty,
            "assumptions": assumptions,
            "variety_id": variety.get("variety_id"),
            "variety_source": variety.get("source"),
            "photoperiod_sensitive": bool(variety.get("photoperiod_sensitive",
                                                      False)),
            "cycle_days": record["cycle_days"],
        }

    @staticmethod
    def _check_fractions(fractions: dict[str, float]) -> None:
        values = list(fractions.values())
        if any(not 0 < v <= 1 for v in values):
            raise PhenologyError("las fracciones de etapa deben estar en (0, 1]")
        if sorted(values) != values:
            raise PhenologyError("las etapas deben ser crecientes")
        if abs(values[-1] - 1.0) > 1e-9:
            raise PhenologyError("la última etapa debe ser 1,0")

    # --- ejecución ---------------------------------------------------------
    def run(self, crop_id: str, planting_date: str | date, *,
            variety: dict[str, Any] | None = None,
            weather: dict[str, dict[str, float]] | None = None,
            weather_dataset: str = WEATHER_DATASET) -> dict[str, Any]:
        params = self.resolve_parameters(crop_id, variety)
        start = _as_date(planting_date)
        series = weather if weather is not None else _weather_series(
            weather_dataset)
        if not series:
            raise PhenologyError("no hay serie diaria de temperatura")

        days = sorted(d for d in series if d >= start.isoformat())
        if not days:
            raise PhenologyError(
                f"la serie climática termina antes de {start.isoformat()}")

        tbase = params["tbase_c"]
        cap = params["tmax_cap_c"]
        cumulative = 0.0
        target = params["gdd_to_maturity"]
        derived = None

        if target is None:
            cycle = params["cycle_days"]
            if cycle["status"] == "GAP":
                raise PhenologyError(
                    f"{crop_id}: sin GDD de variedad ni ciclo en el catálogo")
            mean_t = sum((series[d]["tmin"] + series[d]["tmax"]) / 2
                         for d in days) / len(days)
            rate = mean_t - tbase
            if rate <= 0:
                raise PhenologyError(
                    "la temperatura media no supera la base térmica: no se "
                    "puede derivar GDD")
            lo_days, hi_days = cycle["value"]
            mid = (lo_days + hi_days) / 2
            target = round(rate * mid, 1)
            derived = {
                "method": "temperatura media del período × ciclo medio",
                "rate_degc_per_day": round(rate, 3),
                "cycle_days_mid": mid,
                "bounds_gdd": [round(rate * lo_days, 1),
                               round(rate * hi_days, 1)],
            }
            params["gdd_status"] = "MODEL_DERIVED"
            params["uncertainty_gdd"] = derived["bounds_gdd"]

        stages = params["stage_fractions"]
        thresholds = {name: target * frac for name, frac in stages.items()}
        reached: dict[str, dict[str, Any]] = {}
        for day in days:
            row = series[day]
            cumulative += daily_gdd(row["tmin"], row["tmax"], tbase, cap)
            for name, threshold in thresholds.items():
                if name not in reached and cumulative >= threshold:
                    reached[name] = {
                        "stage": name,
                        "date": day,
                        "gdd_cum": round(cumulative, 1),
                        "threshold_gdd": round(threshold, 1),
                        "days_after_planting": (_as_date(day) - start).days,
                    }
            if cumulative >= target:
                break

        ordered = [reached[name] for name, _ in stages.items() if name in reached]
        complete = "maturity" in reached
        limitations = [
            "tiempo térmico derivado de un punto de reanálisis, no de una "
            "estación local",
            "sin fotoperíodo, vernalización ni efecto del estrés hídrico",
            "las fracciones de etapa son una convención AGROSV, no una "
            "calibración varietal",
            "una fecha de madurez no es un calendario de siembra validado",
        ]
        if derived:
            limitations.append(
                "el GDD a madurez se derivó del ciclo del catálogo y de la "
                "temperatura del período; su rango es indicativo")
        if params["photoperiod_sensitive"]:
            limitations.append(
                "la variedad se declara sensible al fotoperíodo, pero AGROSV "
                "no implementa ese efecto: el resultado es solo térmico")
        if not complete:
            limitations.append(
                "la serie disponible no alcanza la madurez: no se extrapola")

        result = {
            "crop_id": params["crop_id"],
            "planting_date": start.isoformat(),
            "variety_id": params["variety_id"],
            "parameters": {
                "tbase_c": tbase,
                "tmax_cap_c": cap,
                "gdd_to_maturity": round(target, 1),
                "gdd_status": params["gdd_status"],
                "uncertainty_gdd": params["uncertainty_gdd"],
                "stage_fractions": stages,
                "derivation": derived,
            },
            "stages": ordered,
            "stages_expected": list(stages),
            "complete": complete,
            "gdd_accumulated": round(cumulative, 1),
            "days_observed": len(days[:ordered[-1]["days_after_planting"] + 1])
            if ordered else 0,
            "weather": {
                "dataset_id": weather_dataset if weather is None else "custom",
                "evidence_class": "reanalysis",
                "point_series": True,
                "note": ("serie de un punto de reanálisis; no representa el "
                         "lote sembrado"),
            },
            "assumptions": params["assumptions"],
        }
        return AG.envelope(
            ENGINE,
            result=result,
            sources=[s for s in ("crop_parameters_catalog", WEATHER_DATASET,
                                 WEATHER_DATASET_FALLBACK)
                     if s != WEATHER_DATASET_FALLBACK or weather is None],
            limitations=limitations,
            processing=[
                AG.step("resolución de parámetros", "resolve_parameters"),
                AG.step("acumulación diaria de GDD", "daily_gdd"),
                AG.step("cruces de umbral por etapa", "run"),
            ],
            query={"crop_id": params["crop_id"],
                   "planting_date": start.isoformat(),
                   "variety": params["variety_id"]},
        )


__all__ = ["CropPhenologyEngine", "PhenologyError", "daily_gdd", "accumulate",
           "DEFAULT_STAGES"]
