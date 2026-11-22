"""AGROSV — AgriculturalCalendarEngine (Fase 6, §4.6).

Calendarios **derivados**, no oficiales. El repositorio no contiene un
calendario agrícola nacional ni prácticas históricas por municipio, así que:

    historical_practice      = null
    technical_recommendation = null
    model_estimate           = ventanas calculadas con clima y fenología
    forecast_dependent       = false (no hay pronóstico)

Ventanas de siembra: meses en que la precipitación climatológica cubre al menos
la mitad de la ET0 mensual y no hay exceso (P > 2·ET0). Umbrales AGROSV
declarados, no una recomendación.

Riesgos por etapa: déficit (P_mes < ET0_mes), exceso (P_mes > 2·ET0_mes) y
lluvia mensual < 60 mm (convención de mes seco). El riesgo de calor no se
evalúa porque el catálogo no publica límites absolutos.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..engines import governance as G5
from . import governance as AG
from .catalog import CROPS
from .phenology import CropPhenologyEngine, PhenologyError

ENGINE = "agricultural_calendar"
ENGINE_VERSION = AG.ENGINE_VERSION

PLANTING_RATIO_MIN = 0.5
EXCESS_RATIO = 2.0
DRY_MONTH_MM = 60.0
MONTH_NAMES = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio",
               "julio", "agosto", "septiembre", "octubre", "noviembre",
               "diciembre")


class CalendarError(ValueError):
    pass


def _climatology() -> dict[str, Any]:
    from ..engines.climate import ClimateDataError, ClimateEngine

    engine = ClimateEngine()
    try:
        p = engine.monthly_climatology("open_meteo_point", "precipitation",
                                       "sum")
        e = engine.monthly_climatology("open_meteo_point", "et0", "sum")
        tx = engine.monthly_climatology("open_meteo_point", "temperature", "max")
        tn = engine.monthly_climatology("open_meteo_point", "temperature", "min")
    except (ClimateDataError, G5.SourceUnavailableError) as exc:
        raise CalendarError(f"climatología no disponible: {exc}") from None
    return {
        "precip_mm": {r["month"]: r["mean"] for r in p["months"]},
        "et0_mm": {r["month"]: r["mean"] for r in e["months"]},
        "tmax_c": {r["month"]: r["mean"] for r in tx["months"]},
        "tmin_c": {r["month"]: r["mean"] for r in tn["months"]},
        "period": p.get("period") or p.get("method"),
    }


def _runs(months: list[int]) -> list[list[int]]:
    if not months:
        return []
    groups = [[months[0]]]
    for month in months[1:]:
        if month == groups[-1][-1] + 1:
            groups[-1].append(month)
        else:
            groups.append([month])
    if len(groups) > 1 and groups[0][0] == 1 and groups[-1][-1] == 12:
        groups[0] = groups.pop() + groups[0]
    return groups


class AgriculturalCalendarEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.phenology = CropPhenologyEngine()

    def generate(self, crop_id: str, *, planting_date: str | None = None,
                 variety: dict[str, Any] | None = None) -> dict[str, Any]:
        key = crop_id.strip().lower()
        if key not in CROPS:
            raise KeyError(f"cultivo desconocido: {crop_id}")
        climate = _climatology()
        p = climate["precip_mm"]
        et0 = climate["et0_mm"]

        suitable_months = []
        for month in range(1, 13):
            if p[month] is None or et0[month] is None:
                continue
            ratio = p[month] / et0[month] if et0[month] else None
            if ratio is None:
                continue
            if (p[month] >= DRY_MONTH_MM
                    and ratio >= PLANTING_RATIO_MIN
                    and ratio <= EXCESS_RATIO):
                suitable_months.append(month)

        windows = [{
            "months": group,
            "labels": [MONTH_NAMES[m] for m in group],
            "criterion": (f"P_mes ≥ {DRY_MONTH_MM:.0f} mm y "
                          f"{PLANTING_RATIO_MIN} ≤ P/ET0 ≤ {EXCESS_RATIO}"),
        } for group in _runs(suitable_months)]

        stages = None
        stage_error = None
        if planting_date:
            try:
                stages = self.phenology.run(key, planting_date,
                                            variety=variety)["result"]
            except (PhenologyError, G5.SourceUnavailableError) as exc:
                stage_error = str(exc)

        risk_periods = []
        if stages:
            for row in stages["stages"]:
                month = int(row["date"][5:7])
                p_m, e_m = p.get(month), et0.get(month)
                risks = []
                if p_m is not None and e_m is not None:
                    if p_m < e_m:
                        risks.append("déficit hídrico (P_mes < ET0_mes)")
                    if p_m > EXCESS_RATIO * e_m:
                        risks.append("exceso de lluvia (P_mes > 2·ET0_mes)")
                    if p_m < DRY_MONTH_MM:
                        risks.append(f"mes seco (P_mes < {DRY_MONTH_MM:.0f} mm)")
                risk_periods.append({
                    "stage": row["stage"], "month": month,
                    "month_label": MONTH_NAMES[month],
                    "precip_mm": p_m, "et0_mm": e_m,
                    "risks": risks or ["sin riesgo según los umbrales"],
                })

        result = {
            "crop_id": key,
            "variety_id": (variety or {}).get("variety_id"),
            "planting_date": planting_date,
            "planting_windows": windows,
            "planting_months_catalog": CROPS[key]["planting_months"],
            "stages": stages["stages"] if stages else None,
            "stage_error": stage_error,
            "risk_periods": risk_periods,
            "classification": {
                "historical_practice": None,
                "technical_recommendation": None,
                "model_estimate": "ventanas y riesgos calculados con "
                                   "climatología 2019–2025 y fenología térmica",
                "forecast_dependent": False,
                "forecast_available": False,
            },
            "unavailable": {
                "historical_practice": "no hay calendario histórico por "
                                       "municipio en el repositorio",
                "technical_recommendation": "no hay recomendación CENTA/MAG "
                                            "georreferenciada",
                "fertilization_windows": "no hay dosis ni épocas verificadas",
                "irrigation_windows": "requiere balance con AWC del lote",
                "pest_monitoring": "no hay umbrales ni datos de monitoreo",
                "forecast": "no se ingirió pronóstico climático",
            },
            "criteria": {
                "planting": (f"P_mes ≥ {DRY_MONTH_MM} mm, "
                             f"{PLANTING_RATIO_MIN} ≤ P/ET0 ≤ {EXCESS_RATIO}"),
                "dry_month_mm": DRY_MONTH_MM,
                "heat_stress": "no evaluado: faltan límites absolutos por cultivo",
            },
            "assumptions": [
                "climatología mensual de un punto de reanálisis",
                "la fenología es térmica y sin fotoperíodo",
                "los umbrales son convenciones AGROSV, no locales",
            ],
        }
        return AG.envelope(
            ENGINE, result=result,
            sources=["crop_parameters_catalog", "open_meteo_point"],
            limitations=[
                "no es un calendario agrícola oficial ni una recomendación",
                "no hay prácticas históricas ni pronóstico",
                "clima de un punto de reanálisis, no del municipio",
                "los umbrales P/ET0 son convenciones AGROSV",
                "las ventanas de siembra no consideran variedad, mercado ni "
                "mano de obra",
            ],
            processing=[
                AG.step("climatología mensual", "ClimateEngine"),
                AG.step("ventanas P/ET0", "generate"),
                AG.step("fenología térmica", "CropPhenologyEngine.run"),
            ],
            query={"crop_id": key, "planting_date": planting_date},
        )


__all__ = ["AgriculturalCalendarEngine", "CalendarError", "DRY_MONTH_MM",
           "PLANTING_RATIO_MIN", "EXCESS_RATIO"]
