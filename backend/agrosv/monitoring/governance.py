"""AGROSV — gobernanza científica de la monitorización (Fase 7, §11–§13).

Vocabulario único para toda la fase. Tres reglas ejecutables:

1. **Una clase de evidencia no se convierte en otra.** Una escena satelital, un
   índice derivado, un umbral de literatura, una observación de campo y una
   alerta generada por reglas son cosas distintas y viajan etiquetadas.
2. **La ausencia de dato es un resultado.** Una serie corta, una banda ausente
   o un umbral sin fuente se publican como `null` + motivo; nunca se rellenan.
3. **Ninguna cifra se publica sin método, periodo y límites.** Los motores
   devuelven `method`, `assumptions` y `limitations` junto al valor.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable

ENGINE_VERSION = "7.0.0"
SERVICE = "agrosv.monitoring"

EVIDENCE_CLASSES = (
    "satellite_observation",   # reflectancia o temperatura de una escena
    "satellite_derived",       # índice o producto calculado de bandas
    "observed",                # medición de estación, pluviómetro o sensor
    "reanalysis",              # modelo asimilado (ERA5, AgERA5)
    "model_estimate",          # modelo de proceso o estadístico de AGROSV
    "reference_threshold",     # umbral publicado en literatura o guía técnica
    "field_observation",       # aportada por una persona; sin verificar
    "official_notice",         # comunicado de una institución competente
    "community_report",        # reporte comunitario no revisado
    "synthetic_fixture",       # dato construido para pruebas
)

SCALES = ("national", "departmental", "municipal", "agricultural_zone",
          "farm", "parcel")

ALERT_STATUSES = ("DETECTED", "PRELIMINARY", "NEEDS_VERIFICATION",
                  "VERIFIED", "DISMISSED", "EXPIRED")

#: Transiciones permitidas. Una alerta VERIFIED no vuelve a PRELIMINARY.
ALERT_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "DETECTED": ("PRELIMINARY", "NEEDS_VERIFICATION", "DISMISSED", "EXPIRED"),
    "PRELIMINARY": ("NEEDS_VERIFICATION", "VERIFIED", "DISMISSED", "EXPIRED"),
    "NEEDS_VERIFICATION": ("VERIFIED", "DISMISSED", "EXPIRED"),
    "VERIFIED": ("EXPIRED",),
    "DISMISSED": (),
    "EXPIRED": (),
}

ALERT_CATEGORIES = (
    "drought", "excess_rainfall", "flood_exposure", "extreme_heat",
    "vegetation_anomaly", "water_stress", "pest_risk", "disease_risk",
    "soil_degradation", "crop_monitoring_required",
)

#: Verificadores que por sí solos pueden sostener VERIFIED.
STRONG_VERIFIERS = ("official_institution", "field_inspection",
                    "independent_dataset")
#: Verificadores que exigen revisión o un segundo verificador.
WEAK_VERIFIERS = ("extension_report", "community_report", "photograph")


class MonitoringError(ValueError):
    """Entrada inválida para un motor de monitorización."""


class InsufficientRecordError(MonitoringError):
    """La serie o el conjunto de observaciones no permite el cálculo pedido."""


class UnsupportedScaleError(MonitoringError):
    """Se pidió una escala que los datos no sostienen."""


class EvidenceError(MonitoringError):
    """Se intentó publicar un valor con una clase de evidencia no admitida."""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_evidence(evidence_class: str) -> str:
    if evidence_class not in EVIDENCE_CLASSES:
        raise EvidenceError(
            f"clase de evidencia no admitida: {evidence_class!r}; "
            f"use una de {list(EVIDENCE_CLASSES)}")
    return evidence_class


def check_scale(scale: str) -> str:
    if scale not in SCALES:
        raise UnsupportedScaleError(
            f"escala no admitida: {scale!r}; use una de {list(SCALES)}")
    return scale


def is_number(value: Any) -> bool:
    """True solo para un número real finito (bool excluido)."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(float(value)))


def finite_or_none(value: Any) -> float | None:
    return float(value) if is_number(value) else None


def clamp01(value: float) -> float:
    if not is_number(value):
        raise MonitoringError(f"se esperaba un número finito, no {value!r}")
    return min(1.0, max(0.0, float(value)))


def scale_between(value: float, low: float, high: float) -> float:
    """Normalización lineal declarada a [0, 1]."""
    if not (is_number(value) and is_number(low) and is_number(high)):
        raise MonitoringError("scale_between exige tres números finitos")
    if high == low:
        raise MonitoringError("low y high no pueden ser iguales")
    return clamp01((float(value) - float(low)) / (float(high) - float(low)))


def weighted_score(components: dict[str, float | None],
                   weights: dict[str, float], *,
                   require_all: bool = False) -> dict[str, Any]:
    """Media ponderada que **no imputa** componentes ausentes.

    Si falta un componente con peso y `require_all`, devuelve `value=None`.
    Si no, renormaliza sobre los pesos presentes y lo declara en `missing`.
    """
    if not components:
        raise MonitoringError("sin componentes que combinar")
    unknown = set(components) - set(weights)
    if unknown:
        raise MonitoringError(f"componentes sin peso declarado: {sorted(unknown)}")
    total = 0.0
    used = 0.0
    missing: list[str] = []
    for name, weight in weights.items():
        if weight < 0:
            raise MonitoringError(f"peso negativo en {name}")
        value = components.get(name)
        if value is None:
            if weight > 0:
                missing.append(name)
            continue
        total += clamp01(value) * float(weight)
        used += float(weight)
    if used == 0:
        return {"value": None, "weight_used": 0.0, "missing": missing,
                "renormalized": False,
                "note": "ningún componente con dato y peso"}
    if missing and require_all:
        return {"value": None, "weight_used": 0.0, "missing": missing,
                "renormalized": False, "note": "faltan componentes exigidos"}
    return {"value": round(total / used, 6), "weight_used": round(used, 6),
            "missing": missing, "renormalized": bool(missing)}


def require_dates(records: Iterable[dict[str, Any]], *, key: str = "date",
                  minimum: int = 1) -> list[dict[str, Any]]:
    """Ordena registros por fecha ISO y exige un mínimo de observaciones."""
    from datetime import date

    out = []
    for record in records:
        raw = record.get(key)
        if raw is None:
            raise InsufficientRecordError(f"registro sin '{key}': {record}")
        try:
            parsed = date.fromisoformat(str(raw)[:10])
        except ValueError:
            raise MonitoringError(f"fecha inválida: {raw!r}; use YYYY-MM-DD") from None
        out.append({**record, "_date": parsed})
    if len(out) < minimum:
        raise InsufficientRecordError(
            f"se requieren al menos {minimum} observaciones; hay {len(out)}")
    out.sort(key=lambda r: r["_date"])
    return out


def result(*, engine: str, evidence_class: str, method: str,
           value: Any = None, assumptions: list[str] | None = None,
           limitations: list[str] | None = None,
           uncertainty: Any = None, **extra: Any) -> dict[str, Any]:
    """Sobre común de toda respuesta de la fase."""
    return {
        "engine": engine,
        "engine_version": ENGINE_VERSION,
        "evidence_class": check_evidence(evidence_class),
        "method": method,
        "value": value,
        "assumptions": assumptions or [],
        "limitations": limitations or [],
        "uncertainty": uncertainty,
        "generated_at": utcnow(),
        **extra,
    }
