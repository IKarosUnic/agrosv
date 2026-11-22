"""AGROSV — CropChangeDetectionEngine y AgriculturalRemoteSensingEngine.

§4.3 y §4.5. El motor de cambio compara dos fechas **comparables**. Se rechaza
la comparación entre sensores o resoluciones distintas salvo que el llamador
declare una armonización explícita: una diferencia de bandas no es un cambio
agrícola.

El resultado informa «cambio detectado» y una lista de procesos *posibles*.
No atribuye causa: una caída de NDVI puede ser cosecha, senescencia, estrés,
nube residual o un píxel mixto distinto.

`AgriculturalRemoteSensingEngine` conecta la observación con el territorio y
el suelo de Fase 5 **si están disponibles**, y declara qué escala sostiene la
resolución real.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import governance as G

CHANGE_ENGINE = "crop_change_detection"
REMOTE_ENGINE = "agricultural_remote_sensing"
ENGINE_VERSION = G.ENGINE_VERSION

#: Escala mínima de píxel que AGROSV considera suficiente por escala de análisis.
SCALE_REQUIREMENTS_M: dict[str, float] = {
    "national": 250.0,
    "departmental": 100.0,
    "municipal": 30.0,
    "agricultural_zone": 20.0,
    "farm": 5.0,
    "parcel": 2.0,
}


class CropChangeDetectionEngine:
    engine = CHANGE_ENGINE
    version = ENGINE_VERSION

    def compare(self, before: np.ndarray, after: np.ndarray, *,
                threshold: float,
                before_sensor: str | None = None,
                after_sensor: str | None = None,
                before_resolution_m: float | None = None,
                after_resolution_m: float | None = None,
                harmonized: bool = False,
                before_date: str | None = None,
                after_date: str | None = None) -> dict[str, Any]:
        """Diferencia entre dos índices con umbral explícito y declarado."""
        if threshold <= 0:
            raise G.MonitoringError("threshold debe ser positivo y justificado")
        b = np.asarray(before, dtype="float32")
        a = np.asarray(after, dtype="float32")
        if b.shape != a.shape:
            raise G.MonitoringError("las dos fechas no comparten rejilla")
        if (before_sensor and after_sensor and before_sensor != after_sensor
                and not harmonized):
            raise G.MonitoringError(
                f"comparación {before_sensor} vs {after_sensor} sin armonización "
                "declarada: la diferencia incluiría el sensor")
        if (before_resolution_m and after_resolution_m
                and before_resolution_m != after_resolution_m
                and not harmonized):
            raise G.MonitoringError(
                "resoluciones distintas sin remuestreo declarado")
        delta = a - b
        valid = np.isfinite(delta)
        if not valid.any():
            raise G.InsufficientRecordError(
                "ningún píxel válido en las dos fechas")
        changed = valid & (np.abs(delta) >= threshold)
        median = float(np.median(delta[valid]))
        p10, p90 = (float(np.quantile(delta[valid], q)) for q in (0.10, 0.90))
        fraction = float(changed.sum() / valid.sum())
        signal = self._classify(median, threshold)
        confidence = ("low" if valid.mean() < 0.5 else
                      "medium" if valid.mean() < 0.8 else "moderate")
        return {
            "engine": self.engine, "engine_version": self.version,
            "evidence_class": "satellite_derived",
            "method": "diferencia de índices con umbral declarado",
            "threshold": threshold,
            "before_date": before_date, "after_date": after_date,
            "before_sensor": before_sensor, "after_sensor": after_sensor,
            "harmonized": harmonized,
            "valid_pixels": int(valid.sum()),
            "changed_pixels": int(changed.sum()),
            "changed_fraction": round(fraction, 6),
            "decrease_fraction": round(
                float((delta[valid] <= -threshold).mean()), 6),
            "increase_fraction": round(
                float((delta[valid] >= threshold).mean()), 6),
            "median_delta": round(median, 6),
            "p10_delta": round(p10, 6), "p90_delta": round(p90, 6),
            "signal": signal,
            "possible_processes": self._processes(signal),
            "attribution": None,
            "confidence": confidence,
            "limitations": [
                "una caída de índice no identifica cosecha, estrés ni disturbio",
                "nubes residuales y sombras producen deltas espurios",
                "la fenología normal explica parte del cambio estacional",
                "no sustituye la verificación de campo",
            ],
            "note": ("comparar dos fechas no basta para atribuir un proceso; "
                     "se requieren observaciones intermedias y de campo"),
        }

    @staticmethod
    def _classify(median: float, threshold: float) -> str:
        if abs(median) < threshold:
            return "no_change_detected"
        if median <= -2 * threshold:
            return "strong_decline"
        if median <= -threshold:
            return "decline"
        if median >= 2 * threshold:
            return "strong_increase"
        return "increase"

    @staticmethod
    def _processes(signal: str) -> list[str]:
        if signal in {"decline", "strong_decline"}:
            return ["posible cosecha o retiro del cultivo",
                    "posible senescencia fenológica",
                    "posible estrés hídrico o térmico",
                    "posible disturbio o pérdida de cobertura"]
        if signal in {"increase", "strong_increase"}:
            return ["posible establecimiento del cultivo",
                    "posible recuperación tras lluvia",
                    "posible crecimiento de maleza o cobertura no agrícola"]
        return []

    def timeseries_summary(self, deltas: list[float], *, threshold: float
                           ) -> dict[str, Any]:
        """Resumen de deltas sucesivos; informa persistencia, no causa."""
        if not deltas:
            raise G.InsufficientRecordError("sin deltas que resumir")
        arr = np.asarray(deltas, dtype=float)
        negative_runs = 0
        longest = 0
        for value in arr:
            if value <= -threshold:
                negative_runs += 1
                longest = max(longest, negative_runs)
            else:
                negative_runs = 0
        return {
            "n": int(arr.size), "threshold": threshold,
            "median_delta": round(float(np.median(arr)), 6),
            "negative_steps": int((arr <= -threshold).sum()),
            "longest_negative_run": int(longest),
            "persistent_decline": bool(longest >= 2),
            "note": ("dos o más descensos consecutivos sugieren persistencia; "
                     "no prueban causa ni daño económico"),
        }


class AgriculturalRemoteSensingEngine:
    """Contexto agrícola de la observación y declaración de escala."""

    engine = REMOTE_ENGINE
    version = ENGINE_VERSION

    def scale_support(self, resolution_m: float, scale: str) -> dict[str, Any]:
        G.check_scale(scale)
        if not G.is_number(resolution_m) or resolution_m <= 0:
            raise G.MonitoringError("resolution_m debe ser un número positivo")
        required = SCALE_REQUIREMENTS_M[scale]
        supported = float(resolution_m) <= required
        return {
            "scale": scale, "resolution_m": float(resolution_m),
            "required_resolution_m": required, "supported": supported,
            "reason": (
                f"la resolución de {resolution_m:g} m "
                f"{'alcanza' if supported else 'no alcanza'} la escala "
                f"'{scale}' (se exigen ≤ {required:g} m)"),
            "note": ("un píxel de 10 m no equivale a una parcela: si la parcela "
                     "es menor que el píxel, el valor es mixto"),
        }

    def link_context(self, *, lat: float, lon: float,
                     provided: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perfil territorial y de suelo de Fase 5, si está disponible.

        Nunca inventa el contexto: si un motor de Fase 5 no puede responder,
        el campo queda en `None` con el motivo.
        """
        context: dict[str, Any] = {"territory": None, "terrain": None,
                                   "soil": None, "availability": {}}
        if provided:
            context.update(provided)
            context["availability"]["provided"] = True
            return context
        try:
            from ..engines.territorial import TerritorialEngine

            profile = TerritorialEngine().profile(lon, lat)
            context["territory"] = {
                k: profile.get(k) for k in ("department", "municipality",
                                            "adm1_code", "adm2_code")
                if k in profile}
            context["terrain"] = profile.get("terrain")
            context["availability"]["territory"] = True
        except Exception as exc:  # noqa: BLE001 — se declara la ausencia
            context["availability"]["territory"] = False
            context["availability"]["territory_reason"] = (
                f"{type(exc).__name__}: {exc}")
        try:
            from ..engines.soil import SoilEngine

            soil = SoilEngine().profile_at_depth(lon, lat, top_cm=0, bottom_cm=30)
            context["soil"] = soil
            context["availability"]["soil"] = True
        except Exception as exc:  # noqa: BLE001
            context["availability"]["soil"] = False
            context["availability"]["soil_reason"] = (
                f"{type(exc).__name__}: {exc}")
        context["note"] = ("el contexto se consulta a los motores de Fase 5; "
                           "una ausencia se declara y no se rellena")
        return context
