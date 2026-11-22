"""AGROSV — monitorización integrada (Fase 7, §9).

`AgriculturalMonitoringEngine` reúne capas heterogéneas **sin inventar** las que
faltan: cada capa declara si está disponible y con qué clase de evidencia.
`CropMonitoringTimelineEngine` ordena eventos y no rellena periodos vacíos.
`AgriculturalRiskMappingEngine` exporta GeoJSON con metadatos de capa.
`AgriculturalMonitoringAnalysisEngine` separa estadística descriptiva,
tendencia e inferencia; ninguna conclusión causal se emite sin diseño.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

import numpy as np

from .. import config as C
from . import governance as G
from .change import AgriculturalRemoteSensingEngine
from .timeseries import SatelliteTimeSeriesEngine

MONITORING_ENGINE = "agricultural_monitoring"
TIMELINE_ENGINE = "crop_monitoring_timeline"
MAPPING_ENGINE = "agricultural_risk_mapping"
ANALYSIS_ENGINE = "agricultural_monitoring_analysis"
ENGINE_VERSION = G.ENGINE_VERSION

TIMELINE_EVENT_TYPES = ("planting", "growth_stage", "satellite_observation",
                        "climate_event", "anomaly", "risk_change", "alert",
                        "field_verification", "harvest", "management")


class AgriculturalMonitoringEngine:
    engine = MONITORING_ENGINE
    version = ENGINE_VERSION

    def status(self, *, lat: float, lon: float,
               crop_id: str | None = None, scale: str = "municipal",
               resolution_m: float | None = None,
               satellite_index: dict[str, Any] | None = None,
               anomalies: dict[str, Any] | None = None,
               risks: dict[str, Any] | None = None,
               alert_summary: dict[str, Any] | None = None,
               include_context: bool = False) -> dict[str, Any]:
        from ..engines.territorial import CoverageError, validate_coordinate

        try:
            lon_v, lat_v = validate_coordinate(lon, lat)
        except CoverageError as exc:
            raise G.MonitoringError(str(exc)) from None
        G.check_scale(scale)
        layers: dict[str, Any] = {}

        def _layer(name: str, payload: Any, evidence: str,
                   required: bool = True) -> None:
            if payload is None:
                layers[name] = {"available": False, "value": None,
                                "reason": "no aportado en la consulta"}
                return
            layers[name] = {"available": True, "value": payload,
                            "evidence_class": G.check_evidence(evidence)}

        _layer("satellite_index", satellite_index, "satellite_derived")
        _layer("anomalies", anomalies, "model_estimate")
        _layer("risks", risks, "model_estimate")
        _layer("alerts", alert_summary, "model_estimate", required=False)
        scale_support = None
        if resolution_m is not None:
            scale_support = AgriculturalRemoteSensingEngine().scale_support(
                resolution_m, scale)
        context = None
        if include_context:
            context = AgriculturalRemoteSensingEngine().link_context(
                lat=lat_v, lon=lon_v)
        available = sum(1 for layer in layers.values() if layer["available"])
        return {
            "engine": self.engine, "engine_version": self.version,
            "latitude": lat_v, "longitude": lon_v, "crop_id": crop_id,
            "scale": scale, "layers": layers,
            "available_layers": available, "total_layers": len(layers),
            "scale_support": scale_support,
            "context": context,
            "missing_layers": [k for k, v in layers.items()
                               if not v["available"]],
            "method": "agregación declarativa de capas ya calculadas",
            "limitations": [
                "no calcula capas ausentes",
                "la agregación no crea un índice compuesto",
                "la escala soportada depende de la resolución real del dato",
            ],
            "note": "cada capa conserva su clase de evidencia; no se promedia "
                    "entre observaciones y modelos",
        }


class CropMonitoringTimelineEngine:
    engine = TIMELINE_ENGINE
    version = ENGINE_VERSION

    def build(self, events: Iterable[dict[str, Any]], *,
              expected_interval_days: int | None = None) -> dict[str, Any]:
        validated = G.require_dates(events, minimum=1)
        out = []
        duplicates: list[list[str]] = []
        seen: dict[tuple[str, str, str], str] = {}
        for index, event in enumerate(validated, start=1):
            event_type = event.get("type")
            if event_type not in TIMELINE_EVENT_TYPES:
                raise G.MonitoringError(
                    f"tipo de evento no admitido: {event_type!r}; "
                    f"use {list(TIMELINE_EVENT_TYPES)}")
            evidence = event.get("evidence_class") or "observed"
            G.check_evidence(str(evidence))
            key = (event["_date"].isoformat(), str(event_type),
                   str(event.get("source") or ""))
            sequence = index
            event_id = str(event.get("event_id") or
                           f"EVT-{event['_date'].isoformat()}-{index}")
            if key in seen:
                duplicates.append([seen[key], event_id])
            else:
                seen[key] = event_id
            out.append({
                "sequence": sequence, "event_id": event_id,
                "date": event["_date"].isoformat(), "type": event_type,
                "description": event.get("description"),
                "value": G.finite_or_none(event.get("value")),
                "unit": event.get("unit"),
                "evidence_class": evidence,
                "source": event.get("source"),
                "provenance": event.get("provenance"),
                "duplicate_suspected": key in seen and seen[key] != event_id,
            })
        periods = []
        if expected_interval_days:
            for prev, nxt in zip(validated, validated[1:]):
                gap = (nxt["_date"] - prev["_date"]).days
                if gap > 1.5 * expected_interval_days:
                    periods.append({"after": prev["_date"].isoformat(),
                                    "before": nxt["_date"].isoformat(),
                                    "days": gap})
        return {
            "engine": self.engine, "engine_version": self.version,
            "event_count": len(out), "events": out,
            "period": {"start": out[0]["date"], "end": out[-1]["date"]},
            "duplicates_suspected": duplicates,
            "missing_periods": periods,
            "interpolated": False,
            "note": ("los eventos se ordenan por fecha; los periodos sin evento "
                     "no se rellenan"),
            "limitations": [
                "una fecha de evento no prueba que el proceso ocurriera ese día",
                "los eventos de fuentes distintas pueden solaparse",
            ],
        }


class AgriculturalRiskMappingEngine:
    engine = MAPPING_ENGINE
    version = ENGINE_VERSION

    def to_feature_collection(self, points: Iterable[dict[str, Any]], *,
                              indicator: str, source: str,
                              observation_date: str,
                              resolution_m: float,
                              methodology: str,
                              confidence: str,
                              limitations: list[str],
                              modeled: bool = True,
                              crs: str = "EPSG:4326") -> dict[str, Any]:
        if not source or not methodology:
            raise G.MonitoringError(
                "toda capa exige fuente y metodología")
        west, south, east, north = C.SV_BOUNDS
        features = []
        for point in points:
            lat = G.finite_or_none(point.get("latitude", point.get("lat")))
            lon = G.finite_or_none(point.get("longitude", point.get("lon")))
            value = G.finite_or_none(point.get("value"))
            if lat is None or lon is None:
                raise G.MonitoringError("punto sin coordenada válida")
            if not (west <= lon <= east and south <= lat <= north):
                raise G.MonitoringError("punto fuera de El Salvador")
            if value is None:
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "value": value,
                    "indicator": indicator,
                    "unit": point.get("unit"),
                    "modeled": bool(modeled),
                    "evidence_class": "model_estimate" if modeled
                    else "satellite_derived",
                    "source": source,
                    "observation_date": observation_date,
                    "confidence": confidence,
                },
            })
        if not features:
            raise G.InsufficientRecordError("ningún punto con valor para mapear")
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "indicator": indicator,
                "source": source,
                "date": observation_date,
                "resolution_m": float(resolution_m),
                "crs": crs,
                "methodology": methodology,
                "confidence": confidence,
                "limitations": list(limitations),
                "modeled": bool(modeled),
                "interpolated": False,
                "feature_count": len(features),
                "note": ("los valores modelados no son mediciones directas; "
                         "no se interpola entre puntos"),
            },
        }


class AgriculturalMonitoringAnalysisEngine:
    engine = ANALYSIS_ENGINE
    version = ENGINE_VERSION

    def analyze(self, records: Iterable[dict[str, Any]], *,
                alerts: Iterable[dict[str, Any]] | None = None,
                verification_events: Iterable[dict[str, Any]] | None = None
                ) -> dict[str, Any]:
        validated = G.require_dates(records, minimum=2)
        values = [float(r["value"]) for r in validated
                  if G.is_number(r.get("value"))]
        if len(values) < 2:
            raise G.InsufficientRecordError("se requieren ≥ 2 valores")
        arr = np.asarray(values, dtype=float)
        descriptive = {
            "n": int(arr.size), "mean": round(float(arr.mean()), 6),
            "median": round(float(np.median(arr)), 6),
            "sd": round(float(arr.std(ddof=1)), 6) if arr.size > 1 else None,
            "min": round(float(arr.min()), 6),
            "max": round(float(arr.max()), 6),
            "p10": round(float(np.quantile(arr, 0.10)), 6),
            "p90": round(float(np.quantile(arr, 0.90)), 6),
            "period": {"start": validated[0]["_date"].isoformat(),
                       "end": validated[-1]["_date"].isoformat()},
        }
        trend = None
        if arr.size >= 5:
            try:
                trend = SatelliteTimeSeriesEngine().trajectory(
                    [{"date": r["_date"].isoformat(), "value": r.get("value")}
                     for r in validated], min_obs=5)
            except G.InsufficientRecordError:
                trend = None
        alert_list = list(alerts or [])
        by_category: dict[str, int] = {}
        by_month: dict[str, int] = {}
        for alert in alert_list:
            category = alert.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1
            month = str(alert.get("detected_at", ""))[:7]
            if month:
                by_month[month] = by_month.get(month, 0) + 1
        outcomes: dict[str, int] = {}
        for event in verification_events or []:
            outcome = event.get("outcome", "unknown")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        return {
            "engine": self.engine, "engine_version": self.version,
            "descriptive": descriptive,
            "trend": trend,
            "alerts": {"count": alert_list, "by_category": by_category,
                       "by_month": by_month},
            "verification_outcomes": outcomes,
            "inference": {
                "causal_claim": False,
                "note": ("la comparación y la tendencia son descriptivas; no "
                         "se infiere que un factor ambiental causó la anomalía"),
            },
            "limitations": [
                "n pequeño reduce la estabilidad de la tendencia",
                "la muestra no es un diseño experimental",
                "la frecuencia de alertas depende de los umbrales configurados",
            ],
        }
