"""AGROSV — motores de sanidad vegetal (Fase 7, §5).

Cuatro motores que **no** producen un «índice de salud» universal:

* `CropHealthMonitoringEngine` interpreta anomalías relativas a la etapa
  fenológica y devuelve un estado enumerado, no una puntuación;
* `VegetationStressEngine` exige al menos dos indicadores independientes;
* `ThermalStressEngine` distingue temperatura del aire de temperatura de
  superficie terrestre y no convierte una en otra;
* `CropAnomalyDetectionEngine` implementa métodos transparentes y rechaza
  modelos opacos sin línea base evaluada.

Cada salida separa indicador observado, inferencia, causa posible, confianza y
evidencia faltante. Un indicador de estrés no es un diagnóstico.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np

from ..agriculture.catalog import CROPS
from ..agriculture.phenology import accumulate, daily_gdd
from . import governance as G

HEALTH_ENGINE = "crop_health_monitoring"
STRESS_ENGINE = "vegetation_stress"
THERMAL_ENGINE = "thermal_stress"
ANOMALY_ENGINE = "crop_anomaly_detection"
ENGINE_VERSION = G.ENGINE_VERSION

#: Sensibilidad genérica por etapa. **No es específica de cultivo**: el catálogo
#: no publica coeficientes de sensibilidad por etapa para todos los cultivos.
STAGE_SENSITIVITY: dict[str, float] = {
    "emergence": 0.4, "vegetative": 0.6, "flowering": 1.0,
    "grain_fill": 0.9, "maturity": 0.3,
}

HEALTH_STATUSES = ("normal_observed", "possible_vegetation_stress",
                   "unusual_vegetation_decline", "insufficient_evidence",
                   "monitoring_recommended")


def _crop(crop_id: str) -> dict[str, Any]:
    record = CROPS.get(crop_id.lower())
    if record is None:
        raise KeyError(f"cultivo desconocido: {crop_id}")
    return record


class CropHealthMonitoringEngine:
    engine = HEALTH_ENGINE
    version = ENGINE_VERSION

    def profile(self, crop_id: str) -> dict[str, Any]:
        crop = _crop(crop_id)
        water = crop.get("water", {}).get("critical_stages", {})
        return {
            "crop_id": crop_id.lower(),
            "scientific_name": crop.get("scientific_name"),
            "cycle_days": crop.get("cycle_days", {}).get("value"),
            "critical_stages": water.get("value"),
            "stage_sensitivity": dict(STAGE_SENSITIVITY),
            "note": ("la sensibilidad por etapa es genérica y declarada; no "
                     "sustituye coeficientes específicos de variedad"),
        }

    def assess(self, crop_id: str, stage: str, *,
               ndvi_anomaly: float | None = None,
               ndmi_anomaly: float | None = None,
               rainfall_anomaly: float | None = None,
               temperature_anomaly: float | None = None,
               n_observations: int = 0,
               baseline_years: int = 0,
               variety: str | None = None,
               management: str | None = None) -> dict[str, Any]:
        crop = _crop(crop_id)
        missing: list[str] = []
        sensitivity = STAGE_SENSITIVITY.get(stage)
        if sensitivity is None:
            missing.append(f"etapa desconocida: {stage!r}")
        if n_observations < 3:
            missing.append(f"observaciones insuficientes: {n_observations} < 3")
        if baseline_years < 3:
            missing.append(f"línea base insuficiente: {baseline_years} < 3 años")
        if ndvi_anomaly is None:
            missing.append("anomalía de NDVI ausente")
        if missing:
            return {
                "engine": self.engine, "engine_version": self.version,
                "crop_id": crop_id.lower(), "stage": stage,
                "status": "insufficient_evidence",
                "confidence": "none", "observed_indicators": {},
                "inference": None, "possible_causes": [],
                "missing_evidence": missing,
                "monitoring_recommended": True,
                "method": "reglas declaradas sobre anomalía estacional",
                "limitations": self._limitations(),
                "note": "sin evidencia suficiente no se emite un estado de salud",
            }
        z = float(ndvi_anomaly)
        supportive = [name for name, value in (
            ("ndmi", ndmi_anomaly), ("rainfall", rainfall_anomaly),
            ("temperature", temperature_anomaly))
            if G.is_number(value) and float(value) <= -1.5]
        if z <= -3.0:
            status = "unusual_vegetation_decline"
        elif z <= -2.0 and sensitivity >= 0.6:
            status = "possible_vegetation_stress"
        elif z <= -1.0:
            status = "monitoring_recommended"
        else:
            status = "normal_observed"
        evidence_count = 1 + len(supportive)
        confidence = ("low" if evidence_count == 1 else
                      "medium" if evidence_count == 2 else "moderate")
        causes: list[str] = []
        if ndvi_anomaly is not None and ndmi_anomaly is not None \
                and float(ndvi_anomaly) <= -1.5 and float(ndmi_anomaly) <= -1.5:
            causes.append("posible estrés hídrico (verdour y humedad bajos)")
        if temperature_anomaly is not None and float(temperature_anomaly) >= 1.5:
            causes.append("posible estrés térmico (temperatura sobre la media)")
        if rainfall_anomaly is not None and float(rainfall_anomaly) <= -1.5:
            causes.append("posible déficit de lluvia")
        return {
            "engine": self.engine, "engine_version": self.version,
            "crop_id": crop_id.lower(),
            "crop_scientific_name": crop.get("scientific_name"),
            "variety": variety, "management": management, "stage": stage,
            "stage_sensitivity": sensitivity,
            "status": status, "confidence": confidence,
            "observed_indicators": {
                "ndvi_anomaly_z": z,
                "ndmi_anomaly_z": G.finite_or_none(ndmi_anomaly),
                "rainfall_anomaly_z": G.finite_or_none(rainfall_anomaly),
                "temperature_anomaly_z": G.finite_or_none(temperature_anomaly),
                "n_observations": int(n_observations),
                "baseline_years": int(baseline_years),
            },
            "inference": ("vegetation_index_anomaly_in_stage"
                          if status != "normal_observed" else None),
            "possible_causes": causes,
            "supporting_indicators": supportive,
            "missing_evidence": [],
            "monitoring_recommended": status != "normal_observed",
            "method": "anomalía robusta de NDVI relativa a la etapa fenológica",
            "assumptions": ["la anomalía proviene de una línea base estacional "
                            "de al menos 3 años"],
            "limitations": self._limitations() + [
                "no se calcula un índice compuesto de salud",
                "la sensibilidad por etapa es genérica, no por variedad",
            ],
            "note": "estado interpretativo; no es diagnóstico agronómico",
        }

    @staticmethod
    def _limitations() -> list[str]:
        return [
            "el NDVI satura en dosel denso y se mezcla con suelo desnudo",
            "una nube residual puede producir una anomalía negativa",
            "la etapa fenológica debe provenir de fecha de siembra o campo",
        ]


class VegetationStressEngine:
    engine = STRESS_ENGINE
    version = ENGINE_VERSION

    #: Umbral declarado de anomalía negativa (z robusto).
    NEGATIVE_Z = -1.5
    #: Déficit de humedad de suelo (0–1) que cuenta como indicador.
    SOIL_DEFICIT = 0.5

    def assess(self, *, ndvi_z: float | None = None,
               ndmi_z: float | None = None,
               rainfall_z: float | None = None,
               temperature_z: float | None = None,
               soil_moisture_deficit: float | None = None) -> dict[str, Any]:
        indicators = {
            "ndvi_z": ndvi_z, "ndmi_z": ndmi_z, "rainfall_z": rainfall_z,
            "temperature_z": temperature_z,
            "soil_moisture_deficit": soil_moisture_deficit,
        }
        available = {k: v for k, v in indicators.items() if G.is_number(v)}
        if len(available) < 2:
            return {
                "engine": self.engine, "engine_version": self.version,
                "status": "insufficient_evidence",
                "inferred_stress": None, "indicators": indicators,
                "confidence": "none",
                "missing_evidence": ["se requieren al menos dos indicadores"],
                "possible_causes": [],
                "method": "conteo de indicadores negativos independientes",
                "limitations": ["un solo indicador no permite inferir estrés"],
            }
        negative = {
            "ndvi": G.is_number(ndvi_z) and float(ndvi_z) <= self.NEGATIVE_Z,
            "ndmi": G.is_number(ndmi_z) and float(ndmi_z) <= self.NEGATIVE_Z,
            "rainfall": (G.is_number(rainfall_z)
                         and float(rainfall_z) <= self.NEGATIVE_Z),
            "temperature": (G.is_number(temperature_z)
                            and float(temperature_z) >= 1.5),
            "soil_moisture": (G.is_number(soil_moisture_deficit)
                              and float(soil_moisture_deficit) >= self.SOIL_DEFICIT),
        }
        count = sum(1 for v in negative.values() if v)
        share = count / len(available)
        status = ("none_detected" if count == 0 else
                  "possible" if share < 0.6 else "multiple_indicators")
        causes: list[str] = []
        if negative["ndvi"] and (negative["ndmi"] or negative["soil_moisture"]
                                 or negative["rainfall"]):
            causes.append("posible componente hídrico")
        if negative["temperature"] and negative["ndvi"]:
            causes.append("posible componente térmico")
        if count and not causes:
            causes.append("causa no identificable con los indicadores presentes")
        return {
            "engine": self.engine, "engine_version": self.version,
            "status": status, "inferred_stress": status != "none_detected",
            "indicators": indicators, "negative_indicators": negative,
            "negative_count": count, "available_count": len(available),
            "share_negative": round(share, 4),
            "confidence": ("low" if len(available) == 2 else
                           "medium" if len(available) == 3 else "moderate"),
            "possible_causes": causes,
            "missing_evidence": [k for k, v in indicators.items() if v is None],
            "method": "conteo declarado de indicadores con umbral explícito",
            "limitations": [
                "los indicadores no son independientes entre sí",
                "no establece causa ni cuantifica pérdida de rendimiento",
                "un indicador de estrés no es un diagnóstico",
            ],
        }


class ThermalStressEngine:
    engine = THERMAL_ENGINE
    version = ENGINE_VERSION

    @staticmethod
    def heat_exposure(tmax_c: Sequence[float], *, threshold_c: float,
                      threshold_source: str) -> dict[str, Any]:
        """Días sobre umbral, racha máxima y grados-día de exceso."""
        if not threshold_source or len(threshold_source) < 3:
            raise G.MonitoringError(
                "el umbral térmico exige una fuente declarada; no se inventa")
        values = [float(v) for v in tmax_c if G.is_number(v)]
        if not values:
            raise G.InsufficientRecordError("sin temperaturas máximas válidas")
        above = [v > float(threshold_c) for v in values]
        longest = current = 0
        for flag in above:
            current = current + 1 if flag else 0
            longest = max(longest, current)
        excess = [max(0.0, v - float(threshold_c)) for v in values]
        return {
            "threshold_c": float(threshold_c),
            "threshold_source": threshold_source,
            "n_days": len(values),
            "days_above": int(sum(above)),
            "max_consecutive_days": int(longest),
            "heat_wave_3d": bool(longest >= 3),
            "degree_days_above_c": round(float(sum(excess)), 2),
            "method": "conteo diario sobre umbral declarado",
        }

    def assess(self, crop_id: str, stage: str, tmax_c: Sequence[float], *,
               threshold_c: float, threshold_source: str,
               lst_c: float | None = None,
               tmin_c: Sequence[float] | None = None,
               tbase_c: float | None = None) -> dict[str, Any]:
        crop = _crop(crop_id)
        exposure = self.heat_exposure(tmax_c, threshold_c=threshold_c,
                                      threshold_source=threshold_source)
        sensitivity = STAGE_SENSITIVITY.get(stage)
        status = ("heat_wave_detected" if exposure["heat_wave_3d"]
                  else "isolated_heat_days" if exposure["days_above"]
                  else "no_heat_exposure")
        out: dict[str, Any] = {
            "engine": self.engine, "engine_version": self.version,
            "crop_id": crop_id.lower(),
            "crop_scientific_name": crop.get("scientific_name"),
            "stage": stage, "stage_sensitivity": sensitivity,
            "status": status, "exposure": exposure,
            "sensitive_stage": bool(sensitivity is not None and sensitivity >= 0.6),
            "air_temperature": {"used": True,
                                "note": "temperatura del aire, no de dosel"},
            "land_surface_temperature": {
                "value": G.finite_or_none(lst_c),
                "used_for_stress": False,
                "note": ("la LST de satélite no se sustituye por temperatura "
                         "de dosel sin metodología validada"),
            },
            "confidence": "medium" if exposure["n_days"] >= 7 else "low",
            "possible_causes": ["exposición térmica sobre el umbral declarado"],
            "missing_evidence": ([] if lst_c is not None
                                 else ["temperatura de dosel medida"]),
            "method": "exposición diaria sobre umbral de literatura declarado",
            "assumptions": [f"umbral aplicable a {crop_id}: {threshold_source}"],
            "limitations": [
                "el umbral no está calibrado para variedades salvadoreñas",
                "la temperatura del aire en un punto no representa toda la parcela",
                "la LST no equivale a temperatura del dosel",
            ],
        }
        if tmin_c is not None and tbase_c is not None:
            pairs = [(lo, hi) for lo, hi in zip(tmin_c, tmax_c)
                     if G.is_number(lo) and G.is_number(hi)]
            if pairs:
                accum = accumulate([p[0] for p in pairs], [p[1] for p in pairs],
                                   float(tbase_c))
                out["growing_degree_days"] = {
                    "total": accum[-1], "tbase_c": float(tbase_c),
                    "n_days": len(accum),
                    "method": "media diaria menos temperatura base",
                }
        else:
            out["growing_degree_days"] = None
            out["missing_evidence"].append("Tmin y Tbase para grado-día")
        return out


class CropAnomalyDetectionEngine:
    engine = ANOMALY_ENGINE
    version = ENGINE_VERSION

    SUPPORTED = ("zscore", "robust_z", "moving_average_residual",
                 "seasonal_anomaly")

    def detect(self, values: Sequence[float], *, method: str = "robust_z",
               baseline: Sequence[float] | None = None,
               threshold: float = 2.0,
               window: int = 3,
               baseline_period: str | None = None) -> dict[str, Any]:
        key = method.lower()
        if key not in self.SUPPORTED:
            raise G.MonitoringError(
                f"método no implementado: {method}; use {list(self.SUPPORTED)}. "
                "Un modelo opaco sin línea base evaluada no se publica")
        if threshold <= 0:
            raise G.MonitoringError("threshold debe ser > 0")
        series = np.asarray([v for v in values], dtype=float)
        if series.size < 3:
            raise G.InsufficientRecordError("se requieren ≥ 3 observaciones")
        valid = np.isfinite(series)
        if valid.sum() < 3:
            raise G.InsufficientRecordError("menos de 3 valores finitos")
        base = series if baseline is None else np.asarray(baseline, dtype=float)
        base = base[np.isfinite(base)]
        scores = np.full(series.shape, np.nan)
        if key in {"zscore", "seasonal_anomaly"}:
            if base.size < 3:
                raise G.InsufficientRecordError("línea base con < 3 valores")
            mean = float(base.mean())
            sd = float(base.std(ddof=1))
            if sd == 0:
                raise G.InsufficientRecordError("desviación de línea base = 0")
            scores = (series - mean) / sd
            centre, spread = mean, sd
        elif key == "robust_z":
            if base.size < 3:
                raise G.InsufficientRecordError("línea base con < 3 valores")
            med = float(np.median(base))
            mad = float(np.median(np.abs(base - med))) * 1.4826
            if mad == 0:
                raise G.InsufficientRecordError("MAD de línea base = 0")
            scores = (series - med) / mad
            centre, spread = med, mad
        else:
            if window < 2:
                raise G.MonitoringError("window debe ser ≥ 2")
            residuals = np.full(series.shape, np.nan)
            for i in range(len(series)):
                previous = series[max(0, i - window):i]
                previous = previous[np.isfinite(previous)]
                if previous.size >= 2:
                    residuals[i] = series[i] - float(previous.mean())
            sd = float(np.nanstd(residuals, ddof=1))
            if not np.isfinite(sd) or sd == 0:
                raise G.InsufficientRecordError("residuos sin dispersión")
            scores = residuals / sd
            centre, spread = 0.0, sd
        flagged = [int(i) for i, s in enumerate(scores)
                   if np.isfinite(s) and abs(s) >= threshold]
        return {
            "engine": self.engine, "engine_version": self.version,
            "method": key, "threshold": float(threshold),
            "window": int(window) if key == "moving_average_residual" else None,
            "baseline_period": baseline_period,
            "centre": round(float(centre), 6), "spread": round(float(spread), 6),
            "n": int(series.size), "n_flagged": len(flagged),
            "flagged_indices": flagged,
            "scores": [None if not np.isfinite(s) else round(float(s), 4)
                       for s in scores],
            "direction": ("below" if flagged and np.nanmedian(
                scores[flagged]) < 0 else "above" if flagged else None),
            "confidence": ("low" if base.size < 6 else
                           "medium" if base.size < 20 else "moderate"),
            "inputs": {"values": int(series.size), "baseline": int(base.size)},
            "limitations": [
                "detecta una desviación estadística, no una causa",
                "una línea base corta produce umbrales inestables",
                "la estacionalidad debe estar resuelta por la línea base",
            ],
        }

    def multivariable(self, indicators: dict[str, Sequence[float]], *,
                      threshold: float = 2.0) -> dict[str, Any]:
        """Anomalía multivariable transparente: mediana de z por fecha."""
        if len(indicators) < 2:
            raise G.MonitoringError("se requieren al menos dos variables")
        arrays = {k: np.asarray(v, dtype=float) for k, v in indicators.items()}
        lengths = {a.size for a in arrays.values()}
        if len(lengths) != 1:
            raise G.MonitoringError("las variables deben tener igual longitud")
        z = {}
        for name, arr in arrays.items():
            finite = arr[np.isfinite(arr)]
            if finite.size < 3:
                raise G.InsufficientRecordError(f"{name} con < 3 valores")
            med = float(np.median(finite))
            mad = float(np.median(np.abs(finite - med))) * 1.4826
            if mad == 0:
                raise G.InsufficientRecordError(f"{name}: MAD = 0")
            z[name] = (arr - med) / mad
        stacked = np.vstack(list(z.values()))
        combined = np.nanmedian(stacked, axis=0)
        flagged = [int(i) for i, s in enumerate(combined)
                   if np.isfinite(s) and abs(s) >= threshold]
        return {
            "engine": self.engine, "engine_version": self.version,
            "method": "mediana de z robustos multivariables",
            "variables": sorted(arrays), "threshold": float(threshold),
            "n": int(combined.size), "n_flagged": len(flagged),
            "flagged_indices": flagged,
            "combined_scores": [None if not np.isfinite(s) else round(float(s), 4)
                                for s in combined],
            "limitations": [
                "la mediana multivariable reduce el peso de una señal aislada",
                "no es un clasificador ni un diagnóstico",
            ],
        }
