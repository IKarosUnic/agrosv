"""AGROSV — motores de riesgo agrícola (Fase 7, §7).

Seis motores con un marco transparente:

    riesgo = peligro × exposición × vulnerabilidad

Cada factor es un valor [0, 1] con procedencia declarada. Si falta un factor y
se exige completo, el riesgo es `None`: no se rellena. Las clases
(`negligible`…`very_high`) son una escala operativa de AGROSV, **no** una
clasificación oficial.

Reglas transversales:

* una susceptibilidad modelada no es un evento observado;
* una exposición potencial no es una pérdida;
* no se calculan tasas de erosión ni caudales sin modelo calibrado;
* el pronóstico se informa aparte de la observación y nunca se mezcla.
"""
from __future__ import annotations

from datetime import date
from statistics import NormalDist
from typing import Any, Sequence

import numpy as np

from ..agriculture.catalog import CROPS
from . import governance as G
from .crop_health import STAGE_SENSITIVITY, ThermalStressEngine

RISK_ENGINE = "agricultural_risk"
DROUGHT_ENGINE = "drought_monitoring"
FLOOD_ENGINE = "flood_excess_water_risk"
HEAT_ENGINE = "heat_climate_risk"
SOIL_ENGINE = "soil_degradation_risk"
LOSS_ENGINE = "crop_loss_risk"
ENGINE_VERSION = G.ENGINE_VERSION

#: Escala operativa de AGROSV (declarada, no oficial).
RISK_CLASSES: tuple[tuple[float, str], ...] = (
    (0.10, "negligible"), (0.25, "low"), (0.50, "moderate"),
    (0.75, "high"), (1.01, "very_high"),
)

DROUGHT_TYPES = ("meteorological", "agricultural", "hydrological",
                 "soil_moisture", "vegetation")


def classify_risk(value: float | None) -> str | None:
    if value is None:
        return None
    for limit, label in RISK_CLASSES:
        if value < limit:
            return label
    return "very_high"


class AgriculturalRiskEngine:
    engine = RISK_ENGINE
    version = ENGINE_VERSION

    def assess(self, *, hazard: float | None, exposure: float | None,
               vulnerability: float | None,
               require_all: bool = True,
               detail: dict[str, Any] | None = None) -> dict[str, Any]:
        components = {"hazard": hazard, "exposure": exposure,
                      "vulnerability": vulnerability}
        missing = [k for k, v in components.items() if v is None]
        for name, value in components.items():
            if value is not None:
                G.clamp01(value)
        if missing and require_all:
            value = None
        elif missing:
            present = [G.clamp01(v) for v in components.values() if v is not None]
            value = float(np.prod(present)) if present else None
        else:
            value = float(np.prod([G.clamp01(v) for v in components.values()]))
        return {
            "engine": self.engine, "engine_version": self.version,
            "framework": "Risk = Hazard × Exposure × Vulnerability",
            "components": components,
            "risk_value": None if value is None else round(value, 6),
            "risk_class": classify_risk(value),
            "missing": missing,
            "detail": detail or {},
            "method": ("producto de tres factores normalizados a [0, 1]; "
                       "clases operativas AGROSV"),
            "assumptions": ["los tres factores son independientes; la "
                            "multiplicación no modela correlación"],
            "limitations": [
                "las clases no son una clasificación oficial",
                "la escala no está validada contra daños observados",
                "un riesgo alto no es un evento confirmado",
            ],
        }

    def integrate(self, indicators: dict[str, float | None], *,
                  weights: dict[str, float] | None = None,
                  require_all: bool = False) -> dict[str, Any]:
        weights = weights or {k: 1.0 for k in indicators}
        score = G.weighted_score(indicators, weights, require_all=require_all)
        return {
            "engine": self.engine, "engine_version": self.version,
            "indicators": indicators, "weights": weights,
            "risk_value": score["value"],
            "risk_class": classify_risk(score["value"]),
            "missing": score["missing"],
            "renormalized": score["renormalized"],
            "method": "media ponderada declarada de sub-riesgos",
            "limitations": [
                "no se combinan escalas incompatibles",
                "los pesos son una decisión metodológica, no un resultado",
            ],
        }


class DroughtMonitoringEngine:
    engine = DROUGHT_ENGINE
    version = ENGINE_VERSION
    #: OMM: se requieren ≥ 30 años para un índice estandarizado.
    MIN_YEARS = 30

    @staticmethod
    def consecutive_dry_days(precipitation_mm: Sequence[float], *,
                             wet_threshold_mm: float = 1.0) -> dict[str, Any]:
        values = [float(v) if G.is_number(v) else None
                  for v in precipitation_mm]
        if not values:
            raise G.InsufficientRecordError("sin precipitación")
        longest = current = 0
        dry_days = 0
        for value in values:
            if value is not None and value < wet_threshold_mm:
                dry_days += 1
                current += 1
                longest = max(longest, current)
            elif value is not None:
                current = 0
        return {"n_days": len(values), "wet_threshold_mm": wet_threshold_mm,
                "dry_days": dry_days, "max_consecutive_dry_days": longest,
                "current_run": current,
                "method": "racha de días con P < umbral",
                "limitations": ["no incorpora agua del suelo ni demanda"]}

    @staticmethod
    def accumulate_monthly(values: Sequence[float | None], *, scale: int
                           ) -> list[float | None]:
        if scale < 1:
            raise G.MonitoringError("scale debe ser ≥ 1")
        out: list[float | None] = []
        for i in range(len(values)):
            if i + 1 < scale:
                out.append(None)
                continue
            window = values[i - scale + 1:i + 1]
            if len(window) < scale or any(v is None for v in window):
                out.append(None)
            else:
                out.append(round(float(sum(window)), 3))
        return out

    def standardized_precipitation_index(
            self, monthly_mm: Sequence[float | None], *,
            scale: int = 3, min_years: int = MIN_YEARS) -> dict[str, Any]:
        """Índice estandarizado **empírico** (no el SPI gamma oficial).

        Se agrupa la precipitación acumulada por mes calendario, se asigna una
        probabilidad empírica (Gringorten) y se transforma a z normal. Exige
        al menos `min_years` valores por grupo; si no, no se calcula.
        """
        if len(monthly_mm) < min_years * 12:
            raise G.InsufficientRecordError(
                f"índice estandarizado requiere ≥ {min_years} años "
                f"({min_years * 12} meses); hay {len(monthly_mm)}")
        accumulated = self.accumulate_monthly(monthly_mm, scale=scale)
        groups: dict[int, list[float]] = {}
        for index, value in enumerate(accumulated):
            if value is None:
                continue
            groups.setdefault(index % 12, []).append(value)
        if not accumulated or accumulated[-1] is None:
            raise G.InsufficientRecordError("la última ventana está incompleta")
        last = accumulated[-1]
        month = (len(accumulated) - 1) % 12
        sample = sorted(groups.get(month, []))
        if len(sample) < min_years:
            raise G.InsufficientRecordError(
                f"grupo de mes con {len(sample)} valores; se exigen {min_years}")
        rank = sum(1 for v in sample if v < last)
        p = (rank + 0.44) / (len(sample) + 0.12)
        p = min(max(p, 1e-6), 1 - 1e-6)
        z = NormalDist().inv_cdf(p)
        return {
            "scale_months": scale, "min_years": min_years,
            "n_years_in_group": len(sample),
            "accumulated_mm": last,
            "plotting_position": round(p, 6),
            "z": round(float(z), 4),
            "class": ("extremadamente_seco" if z <= -1.645 else
                      "muy_seco" if z <= -1.282 else
                      "seco" if z <= -0.842 else
                      "extremadamente_humedo" if z >= 1.645 else
                      "muy_humedo" if z >= 1.282 else
                      "humedo" if z >= 0.842 else "normal"),
            "method": ("estandarización empírica por mes calendario "
                       "(Gringorten → normal); no es el SPI gamma oficial"),
            "limitations": [
                "no ajusta una distribución gamma como el SPI estándar",
                "los ceros y la estacionalidad marcada afectan la cola",
                "requiere un registro homogéneo y completo",
            ],
        }

    def assess(self, *, precip_3m_mm: float | None = None,
               precip_percentile: float | None = None,
               et0_3m_mm: float | None = None,
               soil_deficit_fraction: float | None = None,
               cdd_days: int | None = None,
               ndvi_anomaly: float | None = None) -> dict[str, Any]:
        meteorological = None
        if G.is_number(precip_percentile):
            p = float(precip_percentile)
            if not 0 <= p <= 100:
                raise G.MonitoringError("el percentil debe estar en [0, 100]")
            meteorological = {
                "class": ("extremadamente_seco" if p <= 5 else
                          "muy_seco" if p <= 10 else
                          "seco" if p <= 20 else
                          "normal" if p < 80 else
                          "humedo" if p < 90 else "muy_humedo"),
                "percentile": p,
                "method": "percentil de precipitación acumulada del periodo",
                "limitations": ["percentil ≠ SPI", "depende del periodo de referencia"],
            }
        elif (G.is_number(precip_3m_mm) and G.is_number(et0_3m_mm)
              and float(et0_3m_mm) > 0):
            ratio = float(precip_3m_mm) / float(et0_3m_mm)
            meteorological = {
                "class": ("severe_deficit" if ratio < 0.5
                          else "moderate_deficit" if ratio < 0.75
                          else "no_deficit"),
                "ratio_p_et0": round(ratio, 4),
                "method": "P/ET0 del trimestre",
                "limitations": ["ratio climático, no índice estandarizado"],
            }
        agricultural = None
        if G.is_number(soil_deficit_fraction):
            d = G.clamp01(soil_deficit_fraction)
            agricultural = {
                "class": ("sin_deficit" if d < 0.5 else
                          "deficit_moderado" if d < 0.75 else "deficit_severo"),
                "deficit_fraction": d,
                "method": "fracción de agua disponible agotada",
                "limitations": ["requiere TAW y profundidad radicular verificadas"],
            }
        hydrological = {"class": None, "status": "not_evaluated",
                        "reason": "sin caudales ni aforos integrados"}
        vegetation = None
        if G.is_number(ndvi_anomaly):
            vegetation = {
                "robust_z": float(ndvi_anomaly),
                "class": ("anomalía_negativa" if float(ndvi_anomaly) <= -1.5
                          else "sin_anomalía_negativa"),
                "note": "señal de vegetación, no tipo de sequía",
            }
        return {
            "engine": self.engine, "engine_version": self.version,
            "drought_types": {
                "meteorological": meteorological,
                "agricultural": agricultural,
                "soil_moisture": agricultural,
                "hydrological": hydrological,
                "vegetation": vegetation,
            },
            "cdd": cdd_days,
            "statement": self._statement(meteorological, agricultural,
                                         hydrological),
            "method": "evaluación separada de cinco categorías de sequía",
            "limitations": [
                "no se calcula un índice único",
                "un déficit meteorológico no implica sequía agrícola",
                "sin aforos no se evalúa sequía hidrológica",
            ],
        }

    @staticmethod
    def _statement(meteorological: dict | None, agricultural: dict | None,
                   hydrological: dict) -> str:
        if agricultural and agricultural["class"] != "sin_deficit":
            return "déficit de agua del suelo compatible con sequía agrícola"
        if meteorological and meteorological["class"] in {
                "seco", "muy_seco", "extremadamente_seco",
                "moderate_deficit", "severe_deficit"}:
            return ("déficit meteorológico; no se infiere estrés del cultivo "
                    "sin agua del suelo")
        if hydrological["status"] == "not_evaluated":
            return "sin evidencia suficiente para una categoría de sequía"
        return "sin déficit detectado en los indicadores disponibles"


class FloodAndExcessWaterRiskEngine:
    engine = FLOOD_ENGINE
    version = ENGINE_VERSION

    def assess(self, *, rainfall_24h_mm: float | None = None,
               rainfall_72h_mm: float | None = None,
               slope_deg: float | None = None,
               soil_infiltration_mm_h: float | None = None,
               drainage_distance_m: float | None = None,
               official_flood_zone: bool | None = None) -> dict[str, Any]:
        components: dict[str, float | None] = {}
        detail: dict[str, Any] = {}
        if G.is_number(rainfall_24h_mm):
            components["intensity_24h"] = G.scale_between(rainfall_24h_mm, 20, 100)
            detail["intensity_24h"] = {
                "value_mm": float(rainfall_24h_mm), "scale": [20, 100],
                "note": "rangos operativos AGROSV, no umbrales oficiales"}
        if G.is_number(rainfall_72h_mm):
            components["antecedent_72h"] = G.scale_between(rainfall_72h_mm, 40, 200)
            detail["antecedent_72h"] = {
                "value_mm": float(rainfall_72h_mm), "scale": [40, 200]}
        if G.is_number(slope_deg):
            components["runoff_slope"] = G.scale_between(slope_deg, 0, 25)
            detail["runoff_slope"] = {"value_deg": float(slope_deg),
                                      "scale": [0, 25]}
        if G.is_number(soil_infiltration_mm_h):
            components["low_infiltration"] = (
                1.0 - G.scale_between(soil_infiltration_mm_h, 2, 50))
            detail["low_infiltration"] = {
                "value_mm_h": float(soil_infiltration_mm_h), "scale": [2, 50]}
        if G.is_number(drainage_distance_m):
            components["drainage_proximity"] = (
                1.0 - G.scale_between(drainage_distance_m, 100, 5000))
            detail["drainage_proximity"] = {
                "distance_m": float(drainage_distance_m), "scale": [100, 5000]}
        if official_flood_zone is not None:
            components["official_zone"] = 1.0 if official_flood_zone else 0.0
        if not components:
            raise G.InsufficientRecordError(
                "sin variables para estimar exposición a exceso de agua")
        weights = {"intensity_24h": 0.30, "antecedent_72h": 0.25,
                   "runoff_slope": 0.15, "low_infiltration": 0.15,
                   "drainage_proximity": 0.10, "official_zone": 0.05}
        weights = {k: w for k, w in weights.items() if k in components}
        score = G.weighted_score(components, weights)
        processes = self._processes(rainfall_24h_mm, rainfall_72h_mm, slope_deg,
                                    soil_infiltration_mm_h, drainage_distance_m)
        return {
            "engine": self.engine, "engine_version": self.version,
            "evidence_class": "model_estimate",
            "exposure_score": score["value"],
            "exposure_class": classify_risk(score["value"]),
            "components": components, "weights": weights,
            "detail": detail, "missing": score["missing"],
            "process_flags": processes,
            "prediction": False,
            "method": "índice ponderado declarado de exposición potencial",
            "assumptions": ["los rangos operativos no son umbrales oficiales"],
            "limitations": [
                "no es una predicción hidrológica ni hidráulica",
                "no hay modelo de cuenca calibrado ni batimetría",
                "la exposición potencial no es un daño observado",
            ],
            "note": "requiere verificación de campo y fuentes oficiales de inundación",
        }

    @staticmethod
    def _processes(r24: float | None, r72: float | None, slope: float | None,
                   infiltration: float | None,
                   drainage: float | None) -> dict[str, bool | None]:
        intense = G.is_number(r24) and float(r24) >= 50
        wet = G.is_number(r72) and float(r72) >= 100
        flat = G.is_number(slope) and float(slope) < 2
        steep = G.is_number(slope) and float(slope) > 8
        low_inf = G.is_number(infiltration) and float(infiltration) < 10
        near = G.is_number(drainage) and float(drainage) < 1000
        return {
            "surface_water_accumulation": (flat and wet) if flat and wet else None,
            "waterlogging": (flat and (wet or low_inf)) if flat else None,
            "river_flood_exposure": (near and wet) if near else None,
            "flash_flood_exposure": (steep and intense) if steep else None,
            "soil_saturation": wet if G.is_number(r72) else None,
        }


class HeatAndClimateRiskEngine:
    engine = HEAT_ENGINE
    version = ENGINE_VERSION

    def assess(self, *, tmax_c: Sequence[float] | None = None,
               threshold_c: float, threshold_source: str,
               rainfall_mm: float | None = None,
               et0_mm: float | None = None,
               crop_id: str | None = None,
               stage: str | None = None,
               forecast: dict[str, Any] | None = None) -> dict[str, Any]:
        observed = None
        if tmax_c:
            observed = ThermalStressEngine.heat_exposure(
                tmax_c, threshold_c=threshold_c,
                threshold_source=threshold_source)
            observed["share_days_above"] = round(
                observed["days_above"] / observed["n_days"], 4)
        rainfall_deficit = None
        if G.is_number(rainfall_mm) and G.is_number(et0_mm) and float(et0_mm) > 0:
            ratio = float(rainfall_mm) / float(et0_mm)
            rainfall_deficit = {"ratio_p_et0": round(ratio, 4),
                                "class": ("deficit" if ratio < 0.75
                                          else "no_deficit")}
        components: dict[str, float | None] = {}
        if observed:
            components["heat_exposure"] = min(1.0, observed["share_days_above"])
        if rainfall_deficit:
            components["rainfall_deficit"] = (
                1.0 - min(1.0, rainfall_deficit["ratio_p_et0"]))
        score = None
        if components:
            score = G.weighted_score(
                components, {k: 1.0 for k in components})
        crop_note = None
        if crop_id:
            if crop_id.lower() not in CROPS:
                raise KeyError(f"cultivo desconocido: {crop_id}")
            crop_note = {"crop_id": crop_id.lower(),
                         "stage": stage,
                         "stage_sensitivity": STAGE_SENSITIVITY.get(stage)
                         if stage else None}
        forecast_block = None
        if forecast is not None:
            forecast_block = self._validate_forecast(forecast)
        return {
            "engine": self.engine, "engine_version": self.version,
            "observed_heat": observed,
            "rainfall_deficit": rainfall_deficit,
            "risk_score": None if score is None else score["value"],
            "risk_class": classify_risk(None if score is None else score["value"]),
            "crop": crop_note,
            "forecast": forecast_block,
            "mixed_with_observed": False,
            "method": "exposición observada sobre umbral declarado + déficit P/ET0",
            "limitations": [
                "el umbral debe provenir de una fuente explícita",
                "la temperatura del aire no es la del dosel",
                "el pronóstico se informa por separado y no se suma al riesgo observado",
                "ENSO y variabilidad climática no se evalúan sin datos",
            ],
        }

    @staticmethod
    def _validate_forecast(forecast: dict[str, Any]) -> dict[str, Any]:
        required = ("provider", "issued_at", "valid_from", "valid_to",
                    "horizon_days", "uncertainty", "values")
        missing = [k for k in required if k not in forecast]
        if missing:
            raise G.MonitoringError(f"pronóstico incompleto: faltan {missing}")
        for key in ("issued_at", "valid_from", "valid_to"):
            try:
                date.fromisoformat(str(forecast[key])[:10])
            except ValueError:
                raise G.MonitoringError(f"{key} debe ser YYYY-MM-DD") from None
        if int(forecast["horizon_days"]) < 0:
            raise G.MonitoringError("horizon_days no puede ser negativo")
        return {
            "provider": forecast["provider"],
            "issued_at": forecast["issued_at"],
            "valid_from": forecast["valid_from"], "valid_to": forecast["valid_to"],
            "horizon_days": int(forecast["horizon_days"]),
            "uncertainty": forecast["uncertainty"],
            "values": forecast["values"],
            "evidence_class": "forecast",
            "status": "valid" if forecast.get("valid", True) else "stale",
            "note": "pronóstico probabilístico: no genera una afirmación determinista",
        }


class SoilDegradationRiskEngine:
    engine = SOIL_ENGINE
    version = ENGINE_VERSION

    def assess(self, *, slope_deg: float, vegetation_cover: float,
               rainfall_erosivity: float | None = None,
               soil_erodibility: float | None = None,
               land_cover_change: float | None = None,
               salinity: float | None = None,
               organic_matter_g_kg: float | None = None) -> dict[str, Any]:
        if not G.is_number(slope_deg):
            raise G.MonitoringError("slope_deg es obligatorio")
        cover = G.clamp01(vegetation_cover)
        slope_factor = G.scale_between(slope_deg, 0, 30)
        cover_factor = 1.0 - cover
        components: dict[str, float | None] = {
            "slope": slope_factor, "low_cover": cover_factor}
        if G.is_number(land_cover_change):
            components["cover_loss"] = G.clamp01(land_cover_change)
        score = G.weighted_score(
            components, {"slope": 0.45, "low_cover": 0.40, "cover_loss": 0.15})
        relative_index = None
        rusle_complete = False
        if G.is_number(rainfall_erosivity) and G.is_number(soil_erodibility):
            ls = (0.065 + 4.56 * np.sin(np.radians(float(slope_deg))) + 65.41
                  * np.sin(np.radians(float(slope_deg))) ** 2)
            c_factor = max(0.01, 1.0 - cover)
            relative_index = round(float(rainfall_erosivity)
                                   * float(soil_erodibility) * float(ls)
                                   * c_factor, 4)
            rusle_complete = True
        return {
            "engine": self.engine, "engine_version": self.version,
            "evidence_class": "model_estimate",
            "susceptibility_score": score["value"],
            "susceptibility_class": classify_risk(score["value"]),
            "components": components,
            "relative_erosion_index": relative_index,
            "relative_erosion_index_units": "adimensional (R·K·LS·C)",
            "erosion_rate": None,
            "erosion_rate_reason": ("no se declaran tasas (t/ha/año) sin "
                                    "calibración y datos de pérdida de suelo"),
            "rusle_inputs_complete": rusle_complete,
            "salinity": {"value": G.finite_or_none(salinity),
                         "evaluated": False,
                         "reason": "sin umbral local con fuente declarada"},
            "organic_matter": {"value_g_kg": G.finite_or_none(organic_matter_g_kg),
                               "evaluated": False,
                               "reason": "sin umbral local con fuente declarada"},
            "method": "susceptibilidad por pendiente, cobertura y cambio de cobertura",
            "limitations": [
                "susceptibilidad modelada ≠ degradación observada",
                "LS es una aproximación y no un factor calculado con DEM local",
                "no se calculan tasas de erosión",
            ],
        }


class CropLossRiskEngine:
    engine = LOSS_ENGINE
    version = ENGINE_VERSION

    HAZARD_WEIGHTS = {"drought": 0.25, "flood": 0.15, "heat": 0.20,
                      "pest": 0.15, "disease": 0.15, "excess_rainfall": 0.05,
                      "soil_degradation": 0.05}

    def exposure(self, crop_id: str, *, stage: str | None = None,
                 hazards: dict[str, float | None] | None = None,
                 management_factor: float | None = None,
                 observed_damage_fraction: float | None = None,
                 potential_yield_t_ha: float | None = None,
                 expected_yield_t_ha: float | None = None) -> dict[str, Any]:
        if crop_id.lower() not in CROPS:
            raise KeyError(f"cultivo desconocido: {crop_id}")
        hazards = {k: v for k, v in (hazards or {}).items()
                   if k in self.HAZARD_WEIGHTS}
        if not hazards:
            raise G.InsufficientRecordError("sin peligros declarados")
        weights = {k: self.HAZARD_WEIGHTS[k] for k in hazards}
        score = G.weighted_score(hazards, weights)
        sensitivity = STAGE_SENSITIVITY.get(stage, 0.5) if stage else 0.5
        base = score["value"]
        potential = None
        if base is not None:
            potential = base * (0.4 + 0.6 * sensitivity)
            if management_factor is not None:
                potential *= float(management_factor)
            potential = round(min(1.0, max(0.0, potential)), 6)
        modeled_loss = None
        if G.is_number(potential_yield_t_ha) and G.is_number(expected_yield_t_ha):
            if float(potential_yield_t_ha) <= 0:
                raise G.MonitoringError("el rendimiento potencial debe ser > 0")
            modeled_loss = {
                "fraction": round(max(0.0, 1.0 - float(expected_yield_t_ha)
                                      / float(potential_yield_t_ha)), 6),
                "method": "1 − rendimiento esperado / potencial",
                "label": "pérdida modelada, no observada",
            }
        return {
            "engine": self.engine, "engine_version": self.version,
            "crop_id": crop_id.lower(), "stage": stage,
            "hazards": hazards, "weights": weights,
            "potential_impact": potential,
            "potential_impact_class": classify_risk(potential),
            "stage_sensitivity": sensitivity,
            "management_factor": management_factor,
            "observed_damage": {
                "fraction": G.finite_or_none(observed_damage_fraction),
                "label": "daño observado en campo" if observed_damage_fraction
                is not None else None,
            },
            "modeled_loss": modeled_loss,
            "is_actual_yield_loss": False,
            "method": ("combinación ponderada de peligros × sensibilidad de "
                       "etapa × ajuste de manejo declarado"),
            "limitations": [
                "no es una pérdida de rendimiento observada",
                "los pesos son metodológicos y no están calibrados",
                "la etapa fenológica debe estar verificada",
                "no se usa una salida de simulación como pérdida real",
            ],
            "note": "impacto potencial, daño observado y pérdida modelada son "
                    "campos distintos y no se suman",
        }
