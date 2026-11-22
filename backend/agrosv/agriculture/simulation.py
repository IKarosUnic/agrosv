"""AGROSV — CropSimulationEngine (Fase 6, §4.5).

Arquitectura de **adaptadores**. El único adaptador ejecutable en Fase 6 es el
balance hídrico FAO-56 de AGROSV; AquaCrop-OSPy, PCSE/WOFOST y DSSAT se
**detectan** y se declaran con sus requisitos, pero no se ejecutan ni se
presentan como integrados.

Ningún resultado es un pronóstico de producción:

* `calibration_status` = `uncalibrated` salvo que el llamador aporte una
  calibración documentada;
* `validation_status` = `not_validated`;
* el rendimiento solo se calcula si el llamador aporta potencial y Ky con
  fuente; en caso contrario es `null`.
"""
from __future__ import annotations

import importlib.util
import shutil
from typing import Any

from ..engines import governance as G5
from . import governance as AG
from .catalog import CROPS
from .phenology import CropPhenologyEngine, PhenologyError
from .water_nutrient import (CropWaterNutrientEngine, WaterNutrientError,
                             WEATHER_DATASET)

ENGINE = "crop_simulation"
ENGINE_VERSION = AG.ENGINE_VERSION

ADAPTERS: dict[str, dict[str, Any]] = {
    "agrosv_water_balance": {
        "name": "AGROSV FAO-56 water balance",
        "version": ENGINE_VERSION,
        "license": "AGROSV",
        "language": "Python",
        "scope": "balance hídrico diario; sin crecimiento ni rendimiento",
        "implemented": True,
        "executable": True,
        "requires": ["awc_mm_per_m", "root_depth_cm", "kc o Kc de referencia",
                     "fecha de siembra", "serie P/ET0"],
        "outputs": ["ETa/ETm", "días de estrés", "demanda de riego",
                    "fechas de etapa"],
        "calibration": "no requiere calibración para el balance; cualquier "
                       "rendimiento sí la requiere",
        "limitations": [
            "no simula biomasa, fenología acoplada ni nitrógeno",
            "no incluye escorrentía, capilaridad ni salinidad",
        ],
    },
    "aquacrop_ospy": {
        "name": "AquaCrop-OSPy",
        "version": "3.1.2 (PyPI, verificado 2026-11)",
        "license": "Apache-2.0",
        "language": "Python",
        "scope": "balance de agua, biomasa y rendimiento; 7.1 sin salinidad, "
                 "fertilidad, malezas ni perennes",
        "implemented": False,
        "executable": False,
        "package": "aquacrop",
        "requires": ["Tmin/Tmax/P/ET0 diarios", "suelo", "cultivo calibrado",
                     "riego y fecha de siembra"],
        "outputs": ["biomasa", "rendimiento", "agua del suelo"],
        "calibration": "coeficientes de cultivo locales inexistentes para El "
                       "Salvador",
        "limitations": [
            "no se instaló ni se validó en Fase 6",
            "requiere parámetros de cultivo que AGROSV no posee",
        ],
    },
    "pcse_wofost": {
        "name": "PCSE / WOFOST",
        "version": "6.x (verificado 2026-11)",
        "license": "EUPL-1.2",
        "language": "Python",
        "scope": "WOFOST/LINTUL3/LINGRA/ALCEPAS; potencial, agua y N",
        "implemented": False,
        "executable": False,
        "package": "pcse",
        "requires": ["suelo", "cultivo y variedad", "clima diario", "manejo"],
        "outputs": ["biomasa", "rendimiento", "balance de agua y N"],
        "calibration": "sin variedades salvadoreñas",
        "limitations": [
            "no se instaló ni se validó en Fase 6",
            "EUPL-1.2 impone obligaciones si se distribuye una obra derivada",
        ],
    },
    "dssat_csm": {
        "name": "DSSAT-CSM",
        "version": "4.8.6 (verificado 2026-11)",
        "license": "BSD-3-Clause",
        "language": "Fortran/C",
        "scope": "45+ cultivos, coeficientes genéticos",
        "implemented": False,
        "executable": False,
        "binary": "dssat",
        "requires": ["coeficientes genéticos (GENCALC/GLUE)", "suelo", "clima",
                     "archivos .SOL/.WTH/.CUL"],
        "outputs": ["fenología", "biomasa", "rendimiento", "N"],
        "calibration": "requiere calibración varietal; no hay coeficientes "
                       "salvadoreños",
        "limitations": [
            "no se instaló ni se ejecutó en Fase 6",
            "dependencia Fortran y formato de archivos propietario",
        ],
    },
}


class SimulationError(ValueError):
    """Solicitud de simulación inválida."""


class AdapterUnavailable(RuntimeError):
    """El adaptador no está instalado o no está validado."""


def detect() -> dict[str, Any]:
    out = {}
    for name, spec in ADAPTERS.items():
        installed = False
        if spec.get("package"):
            installed = importlib.util.find_spec(spec["package"]) is not None
        elif spec.get("binary"):
            installed = shutil.which(spec["binary"]) is not None
        out[name] = {
            **{k: spec[k] for k in ("name", "version", "license", "scope",
                                    "implemented", "executable")},
            "detected": installed,
            "status": ("implemented" if spec["implemented"] else
                       ("detected_not_validated" if installed else
                        "not_installed")),
            "requires": spec["requires"],
            "calibration": spec["calibration"],
            "limitations": spec["limitations"],
        }
    return {
        "adapters": out,
        "runnable": [k for k, v in out.items() if v["executable"]],
        "note": ("detectar una dependencia no la integra: los adaptadores "
                 "externos no están validados en AGROSV"),
    }


class CropSimulationEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.water = CropWaterNutrientEngine()
        self.phenology = CropPhenologyEngine()

    def simulate(self, *, crop_id: str, planting_date: str,
                 awc_mm_per_m: float, root_depth_cm: float,
                 initial_depletion_mm: float = 0.0,
                 kc: dict[str, Any] | None = None,
                 allow_reference_kc: bool = False,
                 irrigation: dict[str, float] | None = None,
                 p_depletion: float = 0.5,
                 potential_yield_t_ha: float | None = None,
                 ky: float | None = None,
                 ky_source: str | None = None,
                 variety: dict[str, Any] | None = None,
                 adapter: str = "agrosv_water_balance") -> dict[str, Any]:
        key = crop_id.strip().lower()
        if key not in CROPS:
            raise KeyError(f"cultivo desconocido: {crop_id}")
        if adapter != "agrosv_water_balance":
            spec = ADAPTERS.get(adapter)
            if spec is None:
                raise SimulationError(f"adaptador desconocido: {adapter}")
            raise AdapterUnavailable(
                f"{adapter}: {spec['name']} no está integrado en Fase 6; "
                f"requisitos: {', '.join(spec['requires'])}")
        if (potential_yield_t_ha is None) != (ky is None):
            raise SimulationError(
                "para estimar rendimiento se requieren potential_yield_t_ha y "
                "ky juntos, con ky_source")
        if ky is not None and not ky_source:
            raise SimulationError("ky_source es obligatorio si se usa Ky")

        balance = self.water.water_balance(
            crop_id=key, planting_date=planting_date,
            awc_mm_per_m=awc_mm_per_m, root_depth_cm=root_depth_cm,
            initial_depletion_mm=initial_depletion_mm, kc=kc,
            allow_reference_kc=allow_reference_kc,
            p_depletion=p_depletion, irrigation=irrigation)

        stages = None
        stage_error = None
        try:
            stages = self.phenology.run(key, planting_date, variety=variety)
        except (PhenologyError, G5.SourceUnavailableError) as exc:
            stage_error = str(exc)

        ratio = balance["result"]["stress"]["eta_etm_ratio"]
        yield_result = {
            "value_t_ha": None, "status": "not_estimated",
            "reason": "sin rendimiento potencial ni Ky aportados",
        }
        if potential_yield_t_ha is not None and ratio is not None:
            if not 0 <= ky <= 2:
                raise SimulationError("Ky debe estar en 0–2")
            value = max(0.0, potential_yield_t_ha * (1 - ky * (1 - ratio)))
            yield_result = {
                "value_t_ha": round(value, 2),
                "status": "model_estimated_uncalibrated",
                "method": "Ya = Ym × (1 − Ky × (1 − ETa/ETm))",
                "potential_yield_t_ha": potential_yield_t_ha,
                "ky": ky,
                "ky_source": ky_source,
                "water_limited_ratio": ratio,
                "is_forecast": False,
            }

        result = {
            "crop_id": key,
            "planting_date": planting_date,
            "adapter": "agrosv_water_balance",
            "model": {
                "name": "AGROSV FAO-56 water balance",
                "version": ENGINE_VERSION,
                "calibration_status": "uncalibrated",
                "validation_status": "not_validated",
                "scope": "agua del suelo y ET; el rendimiento es opcional y "
                         "condicionado a entradas del usuario",
            },
            "inputs": {
                "soil": balance["result"]["soil"],
                "kc": balance["result"]["kc"],
                "irrigation_events": len(irrigation or {}),
                "weather_dataset": WEATHER_DATASET,
                "evidence_classes": {"soil_inputs": "user_supplied",
                                     "weather": "reanalysis",
                                     "kc": balance["result"]["kc"]["status"]},
            },
            "outputs": {
                "water": balance["result"]["totals"],
                "stress": balance["result"]["stress"],
                "yield": yield_result,
                "phenology": stages["result"] if stages else None,
                "phenology_error": stage_error,
            },
            "assumptions": balance["result"]["assumptions"] + [
                "no se simula biomasa ni crecimiento",
                "el rendimiento, si se calcula, usa Ky aportado por el usuario",
            ],
            "uncertainty": {
                "quantified": False,
                "note": ("no hay intervalos de confianza: el balance es "
                         "determinista y sus entradas no tienen distribución "
                         "conocida"),
                "sensitivity": ["Kc", "AWC", "profundidad radicular",
                                "fecha de siembra", "riego"],
            },
            "calibration_status": "uncalibrated",
            "validation_status": "not_validated",
            "is_forecast": False,
        }
        limitations = [
            "simulación no calibrada ni validada para condiciones salvadoreñas",
            "no es un pronóstico de producción",
            "AWC, profundidad radicular y Kc provienen del llamador",
            "clima de un punto de reanálisis",
        ]
        if stages is None:
            limitations.append(f"fenología no calculada: {stage_error}")
        if yield_result["value_t_ha"] is not None:
            limitations.append(
                "el rendimiento es una estimación condicionada a Ym y Ky "
                "aportados; no es una medición")
        return AG.envelope(
            ENGINE, result=result,
            sources=["crop_parameters_catalog", WEATHER_DATASET, "fao_56"],
            limitations=limitations,
            processing=[
                AG.step("detección de adaptador", "detect"),
                AG.step("balance FAO-56", "water_balance"),
                AG.step("fenología térmica", "CropPhenologyEngine.run"),
                AG.step("rendimiento condicional", "simulate"),
            ],
            query={"crop_id": key, "planting_date": planting_date,
                   "adapter": adapter},
            extra={"adapter_status": detect()["adapters"]["agrosv_water_balance"]},
        )

    def compare(self) -> dict[str, Any]:
        rows = []
        for name, spec in ADAPTERS.items():
            rows.append({
                "adapter": name,
                "license": spec["license"],
                "language": spec["language"],
                "implemented": spec["implemented"],
                "executable": spec["executable"],
                "calibration": spec["calibration"],
            })
        return {
            "adapters": rows,
            "recommendation": (
                "mantener el balance AGROSV como línea base reproducible; "
                "evaluar AquaCrop-OSPy primero por licencia permisiva y API "
                "Python, pero solo después de obtener parámetros locales"),
            "not_integrated": ["aquacrop_ospy", "pcse_wofost", "dssat_csm"],
        }


__all__ = ["CropSimulationEngine", "ADAPTERS", "detect", "SimulationError",
           "AdapterUnavailable"]
