"""AGROSV — CropWaterNutrientEngine (Fase 6, §4.4).

Agua
----
Balance diario de agua en la zona radicular según FAO-56:

    Dr,i = Dr,i−1 − (P − RO) − I + ETa,i + DP
    TAW  = AWC × Zr
    RAW  = p × TAW
    Ks   = (TAW − Dr) / (TAW − RAW)   si Dr > RAW, si no 1
    ETa  = Ks × ETc

AGROSV **no** publica AWC ni profundidad radicular: SoilGrids se descargó
agregado a 0–30 cm y no hay densidad aparente. El llamador debe aportar
`awc_mm_per_m`, `root_depth_cm` e `initial_depletion_mm`; sin ellos no se
ejecuta el balance. La escorrentía se fija en 0 y se declara.

Lluvia efectiva: FAO-56 no prescribe una fórmula única. AGROSV usa
`min(P, ETc)` como cota superior declarada, o una fracción fija opt-in. No es
un método oficial.

Nutrientes
----------
La demanda se calcula como remoción por tonelada (valores REF del catálogo)
multiplicada por un rendimiento **aportado**. No es una recomendación de
fertilización: no hay análisis de suelo, eficiencia de uso ni dosis.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Sequence

from ..engines import governance as G5
from . import governance as AG
from .catalog import CROPS

ENGINE = "crop_water_nutrient"
ENGINE_VERSION = AG.ENGINE_VERSION

WEATHER_DATASET = "open_meteo_point"


class WaterNutrientError(ValueError):
    """Faltan entradas obligatorias o son inconsistentes."""


def _date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise WaterNutrientError(f"fecha inválida: {value!r}") from None


def _weather(start: date, end: date) -> dict[str, dict[str, float]]:
    from ..engines.climate import ClimateDataError, ClimateEngine

    engine = ClimateEngine()
    try:
        p = engine.series(WEATHER_DATASET, "precipitation", "sum")["series"]
        e = engine.series(WEATHER_DATASET, "et0", "sum")["series"]
    except (ClimateDataError, G5.SourceUnavailableError) as exc:
        raise WaterNutrientError(f"clima no disponible: {exc}") from None
    precip = {row["date"]: float(row["value"]) for row in p}
    et0 = {row["date"]: float(row["value"]) for row in e}
    days = [d for d in sorted(set(precip) & set(et0))
            if start.isoformat() <= d <= end.isoformat()]
    if not days:
        raise WaterNutrientError(
            "la serie climática no cubre el intervalo solicitado")
    return {d: {"precip_mm": precip[d], "et0_mm": et0[d]} for d in days}


def effective_precipitation(precip_mm: float, etc_mm: float, *,
                            method: str = "min_p_etc",
                            fraction: float = 0.8) -> float:
    if method == "min_p_etc":
        return max(0.0, min(precip_mm, etc_mm))
    if method == "fixed_fraction":
        if not 0 < fraction <= 1:
            raise WaterNutrientError("fraction debe estar en (0, 1]")
        return max(0.0, precip_mm * fraction)
    if method == "none":
        return 0.0
    raise WaterNutrientError(
        "method debe ser min_p_etc, fixed_fraction o none")


def kc_series(kc: dict[str, float], total_days: int, *,
              mid_fraction: float = 0.60,
              end_fraction: float = 0.85) -> list[float]:
    """Kc diario interpolado entre inicio, medio y final del ciclo.

    Las fracciones 0,60 y 0,85 son una convención AGROSV para colocar el Kc
    medio y el final; no son etapas fenológicas calibradas.
    """
    for key in ("ini", "mid", "end"):
        if key not in kc:
            raise WaterNutrientError(f"falta kc.{key}")
    if not 0 < mid_fraction < end_fraction < 1:
        raise WaterNutrientError("se requiere 0 < mid < end < 1")
    points = [(0.0, float(kc["ini"])),
              (mid_fraction, float(kc["mid"])),
              (end_fraction, float(kc["end"])),
              (1.0, float(kc["end"]))]
    out: list[float] = []
    for day in range(total_days):
        x = day / max(total_days - 1, 1)
        for i in range(1, len(points)):
            x0, y0 = points[i - 1]
            x1, y1 = points[i]
            if x <= x1:
                out.append(y0 + (y1 - y0) * ((x - x0) / (x1 - x0)
                                            if x1 > x0 else 0.0))
                break
        else:
            out.append(points[-1][1])
    return out


def resolve_kc(kc: dict[str, Any] | None, *, allow_reference_kc: bool
               ) -> dict[str, Any]:
    if kc is not None:
        values = {k: kc.get(k) for k in ("ini", "mid", "end")}
        if any(v is None for v in values.values()):
            raise WaterNutrientError("kc requiere ini, mid y end")
        for v in values.values():
            if not 0.05 <= float(v) <= 1.5:
                raise WaterNutrientError("Kc fuera de 0,05–1,5: revise unidades")
        return {"values": {k: float(v) for k, v in values.items()},
                "status": kc.get("status", "REF"),
                "source": kc.get("source"),
                "note": kc.get("note")}
    if allow_reference_kc:
        return {
            "values": {"ini": 1.0, "mid": 1.0, "end": 1.0},
            "status": "SCENARIO", "source": "AGROSV reference surface",
            "note": ("Kc = 1,0 para toda la temporada es una superficie de "
                     "referencia, NO un coeficiente de cultivo"),
        }
    raise WaterNutrientError(
        "no hay Kc del cultivo: aporte kc={ini,mid,end} con fuente o active "
        "allow_reference_kc para un ejercicio de balance con superficie de "
        "referencia")


class CropWaterNutrientEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    # --- agua --------------------------------------------------------------
    def water_balance(self, *, crop_id: str, planting_date: str | date,
                      awc_mm_per_m: float, root_depth_cm: float,
                      initial_depletion_mm: float = 0.0,
                      kc: dict[str, Any] | None = None,
                      allow_reference_kc: bool = False,
                      p_depletion: float = 0.5,
                      irrigation: dict[str, float] | None = None,
                      rain_method: str = "min_p_etc",
                      weather: dict[str, dict[str, float]] | None = None
                      ) -> dict[str, Any]:
        key = crop_id.strip().lower()
        if key not in CROPS:
            raise KeyError(f"cultivo desconocido: {crop_id}")
        for name, value in (("awc_mm_per_m", awc_mm_per_m),
                            ("root_depth_cm", root_depth_cm)):
            if value is None or value <= 0:
                raise WaterNutrientError(f"{name} debe ser > 0")
        if not 0 < p_depletion < 1:
            raise WaterNutrientError("p_depletion debe estar en (0, 1)")
        if initial_depletion_mm < 0:
            raise WaterNutrientError("initial_depletion_mm no puede ser negativo")

        kc_info = resolve_kc(kc, allow_reference_kc=allow_reference_kc)
        start = _date(planting_date)
        cycle = CROPS[key]["cycle_days"]["value"]
        if cycle is None:
            raise WaterNutrientError(
                f"{key} no tiene ciclo en el catálogo; indique un ciclo "
                "explícito antes de un balance")
        total_days = int(round(sum(cycle) / 2))
        series = weather or _weather(
            start, date.fromordinal(start.toordinal() + total_days - 1))
        days = sorted(series)[:total_days]

        taw = awc_mm_per_m * (root_depth_cm / 100.0)
        raw = p_depletion * taw
        if initial_depletion_mm > taw:
            raise WaterNutrientError("la depleción inicial supera TAW")
        ks_values = kc_series(kc_info["values"], len(days))

        dr = float(initial_depletion_mm)
        rows = []
        etm_total = eta_total = precip_total = eff_total = irr_total = 0.0
        deep_percolation = 0.0
        stress_days = 0
        irrigation = irrigation or {}
        for i, day in enumerate(days):
            row = series[day]
            precip = float(row["precip_mm"])
            et0 = float(row["et0_mm"])
            etc = et0 * ks_values[i]
            eff = effective_precipitation(precip, etc, method=rain_method)
            ks = 1.0 if dr <= raw else max(
                0.0, min(1.0, (taw - dr) / (taw - raw)))
            eta = etc * ks
            if ks < 0.999:
                stress_days += 1
            applied = float(irrigation.get(day, 0.0))
            # balance FAO-56 simplificado, RO = 0
            dr = dr - eff - applied + eta
            if dr < 0:
                deep_percolation += -dr
                dr = 0.0
            elif dr > taw:
                dr = taw
            rows.append({
                "date": day, "precip_mm": round(precip, 2),
                "effective_precip_mm": round(eff, 2),
                "et0_mm": round(et0, 2), "kc": round(ks_values[i], 3),
                "etc_mm": round(etc, 2), "ks": round(ks, 3),
                "eta_mm": round(eta, 2), "irrigation_mm": round(applied, 2),
                "depletion_mm": round(dr, 2),
            })
            etm_total += etc
            eta_total += eta
            precip_total += precip
            eff_total += eff
            irr_total += applied

        deficit_days = sum(1 for r in rows if r["depletion_mm"] > raw)
        truncated = len(days) < total_days
        result = {
            "crop_id": key,
            "planting_date": start.isoformat(),
            "days": len(rows),
            "cycle_days_requested": total_days,
            "series_truncated": truncated,
            "soil": {
                "awc_mm_per_m": awc_mm_per_m,
                "root_depth_cm": root_depth_cm,
                "taw_mm": round(taw, 1),
                "raw_mm": round(raw, 1),
                "p_depletion": p_depletion,
                "initial_depletion_mm": round(initial_depletion_mm, 1),
                "source": "aportado por el llamador (no hay AWC en AGROSV)",
            },
            "kc": {**kc_info["values"], "status": kc_info["status"],
                   "source": kc_info["source"], "note": kc_info["note"]},
            "totals": {
                "precip_mm": round(precip_total, 1),
                "effective_precip_mm": round(eff_total, 1),
                "irrigation_mm": round(irr_total, 1),
                "et0_mm": round(sum(r["et0_mm"] for r in rows), 1),
                "etm_mm": round(etm_total, 1),
                "eta_mm": round(eta_total, 1),
                "deep_percolation_mm": round(deep_percolation, 1),
            },
            "stress": {
                "stress_days": stress_days,
                "deficit_days": deficit_days,
                "eta_etm_ratio": round(eta_total / etm_total, 3)
                if etm_total else None,
            },
            "daily": rows,
            "assumptions": [
                "escorrentía superficial = 0",
                "no hay capilaridad ni flujo lateral",
                "la profundidad radicular es constante durante el ciclo",
                "no se modela salinidad ni fertilidad",
                "el balance no produce rendimiento",
            ],
        }
        limitations = [
            "AWC y profundidad radicular son entradas del usuario, no datos AGROSV",
            "clima de un punto de reanálisis; no del lote",
            "el Kc solo es válido si proviene de una fuente declarada",
            "balance FAO-56 simplificado; no es AquaCrop ni DSSAT",
            "no se emite rendimiento ni recomendación de riego",
        ]
        if not kc:
            limitations.append(
                "se usó Kc = 1,0 de referencia: el resultado no describe un "
                "cultivo específico")
        if truncated:
            limitations.append(
                f"la serie cubre {len(days)} de {total_days} días del ciclo: "
                "el balance está truncado")
        return AG.envelope(
            ENGINE, result=result,
            sources=["crop_parameters_catalog", WEATHER_DATASET, "fao_56"],
            limitations=limitations,
            processing=[
                AG.step("serie diaria P/ET0", "ClimateEngine"),
                AG.step("curva Kc por etapas", "kc_series"),
                AG.step("balance FAO-56", "water_balance"),
            ],
            query={"crop_id": key, "planting_date": start.isoformat(),
                   "awc_mm_per_m": awc_mm_per_m,
                   "root_depth_cm": root_depth_cm,
                   "kc": kc},
        )

    def irrigation_schedule(self, balance: dict[str, Any], *,
                            application_efficiency: float = 1.0
                            ) -> dict[str, Any]:
        """Riego mínimo para mantener la depleción en RAW cada día."""
        if not 0 < application_efficiency <= 1:
            raise WaterNutrientError("application_efficiency debe estar en (0, 1]")
        raw = balance["result"]["soil"]["raw_mm"]
        prev = 0.0
        total = 0.0
        events = []
        for row in balance["result"]["daily"]:
            deficit = max(0.0, row["depletion_mm"] - prev)
            if row["depletion_mm"] > raw and deficit > 0:
                gross = deficit / application_efficiency
                events.append({"date": row["date"], "net_mm": round(deficit, 1),
                               "gross_mm": round(gross, 1)})
                total += gross
            prev = row["depletion_mm"]
        return {
            "events": events,
            "gross_total_mm": round(total, 1),
            "application_efficiency": application_efficiency,
            "rule": "aplicar cuando la depleción supera RAW; no es una "
                    "recomendación agronómica",
            "limitations": [
                "no considera costos, energía, turnos ni pérdidas por "
                "conducción",
                "el balance base usa AWC y Kc aportados por el usuario",
            ],
        }

    # --- nutrientes --------------------------------------------------------
    def nutrient_demand(self, crop_id: str, yield_t_ha: float, *,
                        yield_source: str) -> dict[str, Any]:
        key = crop_id.strip().lower()
        if key not in CROPS:
            raise KeyError(f"cultivo desconocido: {crop_id}")
        if yield_t_ha is None or yield_t_ha <= 0:
            raise WaterNutrientError("yield_t_ha debe ser > 0")
        if not yield_source:
            raise WaterNutrientError("yield_source es obligatorio")
        record = CROPS[key]
        out = {}
        for nutrient, field in (("N", "n_kg_per_t"),
                                ("P2O5", "p2o5_kg_per_t"),
                                ("K2O", "k2o_kg_per_t")):
            param = record["nutrition"][field]
            if param["status"] == "GAP" or param["value"] is None:
                out[nutrient] = {"kg_ha": None, "status": "GAP",
                                 "note": "sin coeficiente de remoción"}
                continue
            lo, hi = param["value"]
            out[nutrient] = {
                "kg_ha": [round(lo * yield_t_ha, 1), round(hi * yield_t_ha, 1)],
                "kg_per_t": [lo, hi],
                "status": "REF",
            }
        return {
            "crop_id": key,
            "yield_t_ha": yield_t_ha,
            "yield_source": yield_source,
            "demand_kg_ha": out,
            "is_fertilizer_recommendation": False,
            "warning": (
                "remoción estimada de nutrientes, NO dosis de fertilizante. "
                "Una recomendación exige análisis de suelo, eficiencia de uso, "
                "dinámica del nutriente y contexto de manejo."),
            "missing": [k for k, v in out.items() if v["status"] == "GAP"],
            "sources": ["crop_parameters_catalog"],
        }

    def nutrient_balance(self) -> dict[str, Any]:
        return {
            "available": False,
            "reason": (
                "SoilGrids aporta nitrógeno total (g/kg), no nitrógeno "
                "disponible; no hay fósforo, potasio, CEC ni análisis de suelo"),
            "not_evaluated": ["N_disponible", "P_extraible", "K_intercambiable",
                              "CEC", "materia_orgánica_labil"],
            "sources": ["soilgrids_2"],
        }


__all__ = ["CropWaterNutrientEngine", "WaterNutrientError",
           "effective_precipitation", "kc_series", "resolve_kc",
           "WEATHER_DATASET"]
