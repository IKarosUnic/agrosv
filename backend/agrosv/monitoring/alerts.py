"""AGROSV — alertas y aviso temprano (Fase 7, §8).

Cinco motores:

* `AgriculturalAlertEngine` — crea alertas estructuradas, suprime duplicados y
  gobierna el ciclo de vida. La alerta original es inmutable; los cambios de
  estado y las verificaciones se guardan como eventos.
* `AgriculturalEarlyWarningEngine` — aviso basado en pronóstico, separado de la
  observación y sin afirmaciones deterministas.
* `AlertPrioritizationEngine` — prioriza con pesos declarados y una regla
  explícita: un evento confirmado de severidad alta no queda por debajo de una
  señal algorítmica de confianza baja.
* `AlertVerificationEngine` — exige evidencia fuerte (institución, inspección o
  dataset independiente) o dos verificadores débiles para VERIFIED.
* `AgriculturalNotificationEngine` — cola local, sin servicios de pago ni datos
  personales.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from . import governance as G

ALERT_ENGINE = "agricultural_alert"
WARNING_ENGINE = "agricultural_early_warning"
PRIORITY_ENGINE = "alert_prioritization"
VERIFICATION_ENGINE = "alert_verification"
NOTIFICATION_ENGINE = "agricultural_notification"
ENGINE_VERSION = G.ENGINE_VERSION

SEVERITY_LEVELS = ("low", "moderate", "high", "very_high")
VERIFICATION_OUTCOMES = ("confirmed", "not_confirmed", "inconclusive")


def _today() -> date:
    return datetime.now(timezone.utc).date()


class AgriculturalAlertEngine:
    engine = ALERT_ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self._alerts: dict[str, dict[str, Any]] = {}
        self._by_fingerprint: dict[str, str] = {}

    # --- creación ----------------------------------------------------------
    def create(self, *, category: str, geographic_scope: dict[str, Any],
               observation_period: dict[str, str], detection_method: str,
               risk_level: str, evidence: list[dict[str, Any]],
               confidence: str, source_datasets: list[str],
               crop_id: str | None = None,
               recommended_verification: str | None = None,
               review_days: int = 14,
               evidence_class: str = "model_estimate",
               uncertainty: str | None = None,
               model_version: str = ENGINE_VERSION) -> dict[str, Any]:
        if category not in G.ALERT_CATEGORIES:
            raise G.MonitoringError(
                f"categoría no admitida: {category}; use {list(G.ALERT_CATEGORIES)}")
        if risk_level not in SEVERITY_LEVELS:
            raise G.MonitoringError(f"nivel no admitido: {risk_level}")
        if not evidence:
            raise G.MonitoringError("una alerta exige evidencia; no se crea vacía")
        if not source_datasets:
            raise G.MonitoringError("una alerta exige datasets de origen")
        if not geographic_scope:
            raise G.MonitoringError("una alerta exige ámbito geográfico")
        if review_days < 1:
            raise G.MonitoringError("review_days debe ser ≥ 1")
        G.check_evidence(evidence_class)
        G.check_scale(str(geographic_scope.get("scale", "municipal")))
        fingerprint = self._fingerprint(category, geographic_scope, crop_id,
                                        observation_period)
        existing_id = self._by_fingerprint.get(fingerprint)
        if existing_id:
            existing = self._alerts[existing_id]
            if existing["status"] not in {"DISMISSED", "EXPIRED"}:
                return {"alert": dict(existing), "duplicate": True,
                        "suppressed_reason":
                        "existe una alerta activa con la misma huella"}
        alert_id = f"ALR-{fingerprint[:12]}"
        now = G.utcnow()
        alert = {
            "alert_id": alert_id,
            "fingerprint": fingerprint,
            "category": category,
            "geographic_scope": dict(geographic_scope),
            "crop_id": crop_id.lower() if crop_id else None,
            "detected_at": now,
            "observation_period": dict(observation_period),
            "source_datasets": list(source_datasets),
            "detection_method": detection_method,
            "risk_level": risk_level,
            "evidence": list(evidence),
            "evidence_class": evidence_class,
            "confidence": confidence,
            "uncertainty": uncertainty,
            "recommended_verification": recommended_verification or
            "inspección de campo o confirmación institucional",
            "expires_at": (_today() + timedelta(days=int(review_days))).isoformat(),
            "status": "DETECTED",
            "model_version": model_version,
            "updated_at": now,
            "history": [{"status": "DETECTED", "at": now,
                         "reason": "creación"}],
            "verification_events": [],
        }
        alert["original"] = {k: v for k, v in alert.items()
                             if k not in {"updated_at", "history",
                                          "verification_events", "original"}}
        self._alerts[alert_id] = alert
        self._by_fingerprint[fingerprint] = alert_id
        return {"alert": dict(alert), "duplicate": False,
                "suppressed_reason": None}

    @staticmethod
    def _fingerprint(category: str, scope: dict[str, Any], crop_id: str | None,
                     period: dict[str, str]) -> str:
        payload = json.dumps({"category": category, "scope": scope,
                              "crop": (crop_id or "").lower(),
                              "period": period}, sort_keys=True,
                             ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def from_risk(self, *, risk_value: float | None, category: str, **kwargs: Any
                  ) -> dict[str, Any] | None:
        """Crea alerta solo si el riesgo alcanza el umbral operativo (0,25)."""
        if risk_value is None:
            return None
        if not 0 <= float(risk_value) <= 1:
            raise G.MonitoringError("risk_value debe estar en [0, 1]")
        if float(risk_value) < 0.25:
            return None
        level = ("very_high" if risk_value >= 0.75 else
                 "high" if risk_value >= 0.50 else
                 "moderate" if risk_value >= 0.35 else "low")
        return self.create(category=category, risk_level=level,
                           evidence=kwargs.pop("evidence", None) or [],
                           **kwargs)

    # --- consulta ----------------------------------------------------------
    def get(self, alert_id: str) -> dict[str, Any]:
        if alert_id not in self._alerts:
            raise KeyError(f"alerta desconocida: {alert_id}")
        return dict(self._alerts[alert_id])

    def list(self, *, status: str | None = None,
             category: str | None = None,
             include_expired: bool = False) -> dict[str, Any]:
        items = []
        for alert in self._alerts.values():
            if status and alert["status"] != status:
                continue
            if category and alert["category"] != category:
                continue
            if not include_expired and alert["status"] == "EXPIRED":
                continue
            items.append(dict(alert))
        items.sort(key=lambda a: a["detected_at"], reverse=True)
        return {"count": len(items), "alerts": items,
                "by_status": self._count_by("status"),
                "by_category": self._count_by("category")}

    def _count_by(self, key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for alert in self._alerts.values():
            out[alert[key]] = out.get(alert[key], 0) + 1
        return out

    # --- ciclo de vida -----------------------------------------------------
    def transition(self, alert_id: str, status: str, *,
                   reason: str = "",
                   verification_events: list[dict[str, Any]] | None = None
                   ) -> dict[str, Any]:
        alert = self._alerts.get(alert_id)
        if alert is None:
            raise KeyError(f"alerta desconocida: {alert_id}")
        if status not in G.ALERT_STATUSES:
            raise G.MonitoringError(f"estado no admitido: {status}")
        if status not in G.ALERT_TRANSITIONS[alert["status"]]:
            raise G.MonitoringError(
                f"transición no permitida: {alert['status']} → {status}")
        if status == "VERIFIED":
            ok, why = self._verification_sufficient(
                verification_events or alert["verification_events"])
            if not ok:
                raise G.MonitoringError(
                    f"no se puede marcar VERIFIED: {why}")
        now = G.utcnow()
        alert["status"] = status
        alert["updated_at"] = now
        alert["history"].append({"status": status, "at": now,
                                 "reason": reason or "cambio de estado"})
        if verification_events:
            alert["verification_events"].extend(verification_events)
        return dict(alert)

    @staticmethod
    def _verification_sufficient(events: Iterable[dict[str, Any]]
                                 ) -> tuple[bool, str]:
        confirmed = [e for e in events
                     if e.get("outcome") == "confirmed"
                     and float(e.get("confidence", 0) or 0) >= 0.5]
        strong = [e for e in confirmed
                  if e.get("verifier_type") in G.STRONG_VERIFIERS]
        if strong:
            return True, "verificador fuerte confirmado"
        weak_types = {e.get("verifier_type") for e in confirmed
                      if e.get("verifier_type") in G.WEAK_VERIFIERS}
        if len(weak_types) >= 2:
            return True, "dos verificadores débiles independientes"
        return False, ("se requiere un verificador fuerte (institución, "
                       "inspección de campo o dataset independiente) o dos "
                       "verificadores débiles de tipo distinto")

    def expire(self, *, on: str | None = None) -> dict[str, Any]:
        reference = date.fromisoformat(on) if on else _today()
        expired = []
        for alert in self._alerts.values():
            if alert["status"] in {"DISMISSED", "EXPIRED", "VERIFIED"}:
                continue
            if date.fromisoformat(alert["expires_at"]) <= reference:
                now = G.utcnow()
                alert["status"] = "EXPIRED"
                alert["updated_at"] = now
                alert["history"].append({"status": "EXPIRED", "at": now,
                                         "reason": f"revisión vencida {reference}"})
                expired.append(alert["alert_id"])
        return {"expired": expired, "count": len(expired), "on": reference.isoformat()}


class AlertPrioritizationEngine:
    engine = PRIORITY_ENGINE
    version = ENGINE_VERSION

    WEIGHTS = {"severity": 0.35, "exposure": 0.15, "crop_sensitivity": 0.15,
               "confidence": 0.15, "evidence_quality": 0.10, "time": 0.10}
    _SEVERITY = {"low": 0.25, "moderate": 0.50, "high": 0.75, "very_high": 1.0}
    _CONFIDENCE = {"none": 0.0, "low": 0.3, "medium": 0.6, "moderate": 0.8,
                   "high": 1.0}
    _EVIDENCE = {"low": 0.3, "moderate": 0.6, "high": 1.0}

    def prioritize(self, alerts: list[dict[str, Any]], *,
                   crop_sensitivity: dict[str, float] | None = None,
                   exposure_area_km2: dict[str, float] | None = None,
                   evidence_quality: dict[str, float] | None = None,
                   on: str | None = None) -> dict[str, Any]:
        if not alerts:
            raise G.InsufficientRecordError("sin alertas que priorizar")
        crop_sensitivity = crop_sensitivity or {}
        exposure_area_km2 = exposure_area_km2 or {}
        evidence_quality = evidence_quality or {}
        reference = date.fromisoformat(on) if on else _today()
        ranked = []
        for alert in alerts:
            components = {
                "severity": self._SEVERITY.get(alert.get("risk_level"), 0.0),
                "exposure": self._exposure(
                    exposure_area_km2.get(alert["alert_id"])),
                "crop_sensitivity": G.clamp01(
                    crop_sensitivity.get(alert.get("crop_id") or "", 0.5)),
                "confidence": self._CONFIDENCE.get(alert.get("confidence"), 0.3),
                "evidence_quality": self._EVIDENCE.get(
                    evidence_quality.get(alert["alert_id"], "moderate"), 0.6),
                "time": self._time_factor(alert.get("expires_at"), reference),
            }
            score = G.weighted_score(components, self.WEIGHTS)
            reasons = self._reasons(alert, components, score)
            verified_high = (alert.get("status") == "VERIFIED"
                             and components["severity"] >= 0.75)
            ranked.append({
                "alert_id": alert["alert_id"], "category": alert["category"],
                "status": alert.get("status"),
                "risk_level": alert.get("risk_level"),
                "priority_score": score["value"],
                "components": components,
                "verified_high_severity": verified_high,
                "reasons": reasons,
            })
        ranked.sort(key=lambda r: (r["verified_high_severity"],
                                   r["priority_score"] or 0.0), reverse=True)
        for i, item in enumerate(ranked, start=1):
            item["rank"] = i
        return {
            "engine": self.engine, "engine_version": self.version,
            "count": len(ranked), "ranking": ranked,
            "weights": dict(self.WEIGHTS),
            "policy": ("un evento verificado de severidad alta se ordena antes "
                       "que una señal algorítmica de confianza baja; el resto "
                       "se ordena por puntuación"),
            "limitations": [
                "la puntuación no es una probabilidad",
                "los pesos son una decisión metodológica",
                "la prioridad no sustituye la verificación",
            ],
        }

    @staticmethod
    def _exposure(area_km2: float | None) -> float | None:
        if not G.is_number(area_km2):
            return None
        import math

        return G.scale_between(math.log10(max(0.0, float(area_km2)) + 1.0), 0, 4)

    @staticmethod
    def _time_factor(expires_at: str | None, reference: date) -> float:
        if not expires_at:
            return 0.3
        try:
            days = (date.fromisoformat(expires_at) - reference).days
        except ValueError:
            return 0.3
        return 1.0 if days <= 7 else 0.6 if days <= 14 else 0.3

    @staticmethod
    def _reasons(alert: dict[str, Any], components: dict[str, float],
                 score: dict[str, Any]) -> list[str]:
        reasons = [f"severidad {alert.get('risk_level')}"]
        if alert.get("status") == "VERIFIED":
            reasons.append("alerta verificada")
        if components["confidence"] < 0.4:
            reasons.append("confianza baja: no debe superar un evento confirmado")
        if score.get("missing"):
            reasons.append(f"componentes sin dato: {score['missing']}")
        return reasons


class AlertVerificationEngine:
    engine = VERIFICATION_ENGINE
    version = ENGINE_VERSION

    def __init__(self, alerts: AgriculturalAlertEngine) -> None:
        self.alerts = alerts
        self._events: dict[str, list[dict[str, Any]]] = {}

    def submit(self, alert_id: str, *, verifier_type: str, outcome: str,
               evidence: list[dict[str, Any]], observed_on: str,
               confidence: float, notes: str = "",
               geographic_reference: str | None = None
               ) -> dict[str, Any]:
        alert = self.alerts.get(alert_id)
        if verifier_type not in G.STRONG_VERIFIERS + G.WEAK_VERIFIERS:
            raise G.MonitoringError(
                f"verificador no admitido: {verifier_type}")
        if outcome not in VERIFICATION_OUTCOMES:
            raise G.MonitoringError(f"resultado no admitido: {outcome}")
        if not evidence:
            raise G.MonitoringError("una verificación exige evidencia")
        try:
            date.fromisoformat(observed_on[:10])
        except ValueError:
            raise G.MonitoringError("observed_on debe ser YYYY-MM-DD") from None
        event = {
            "verification_id": hashlib.sha256(
                f"{alert_id}|{verifier_type}|{observed_on}|{outcome}|"
                f"{len(evidence)}".encode("utf-8")).hexdigest()[:16],
            "alert_id": alert_id,
            "verifier_type": verifier_type,
            "outcome": outcome,
            "evidence": evidence,
            "observed_on": observed_on,
            "recorded_at": G.utcnow(),
            "confidence": G.clamp01(confidence),
            "notes": notes,
            "geographic_reference": geographic_reference,
            "community_observation": verifier_type == "community_report",
        }
        self._events.setdefault(alert_id, []).append(event)
        return dict(event)

    def evaluate(self, alert_id: str) -> dict[str, Any]:
        self.alerts.get(alert_id)
        events = self._events.get(alert_id, [])
        if not events:
            return {"alert_id": alert_id, "evaluated": False,
                    "recommended_status": None,
                    "reason": "sin eventos de verificación"}
        confirmed = [e for e in events if e["outcome"] == "confirmed"]
        rejected = [e for e in events if e["outcome"] == "not_confirmed"]
        ok, why = AgriculturalAlertEngine._verification_sufficient(events)
        if ok:
            status = "VERIFIED"
        elif rejected and not confirmed:
            status = "DISMISSED"
        else:
            status = "NEEDS_VERIFICATION"
        return {
            "alert_id": alert_id, "evaluated": True, "events": events,
            "recommended_status": status, "reason": why,
            "community_only": all(e["community_observation"] for e in events),
            "note": ("un reporte comunitario no verifica por sí solo una alerta"),
        }

    def apply(self, alert_id: str) -> dict[str, Any]:
        evaluation = self.evaluate(alert_id)
        if not evaluation["evaluated"]:
            raise G.MonitoringError("no hay verificaciones que aplicar")
        events = self._events[alert_id]
        status = evaluation["recommended_status"]
        current = self.alerts.get(alert_id)["status"]
        if status not in G.ALERT_TRANSITIONS[current]:
            self.alerts.transition(alert_id, "NEEDS_VERIFICATION",
                                   reason="verificación recibida")
            current = "NEEDS_VERIFICATION"
        alert = self.alerts.transition(
            alert_id, status,
            reason="verificación: " + evaluation["reason"],
            verification_events=events)
        evaluation["alert"] = alert
        return evaluation


class AgriculturalNotificationEngine:
    engine = NOTIFICATION_ENGINE
    version = ENGINE_VERSION

    CHANNELS = ("api", "ui", "report", "offline_sync")

    def __init__(self) -> None:
        self._queue: list[dict[str, Any]] = []

    def enqueue(self, alert: dict[str, Any], *, preferences: dict[str, Any],
                redact: bool = False) -> dict[str, Any]:
        prefs = self._preferences(preferences)
        if not self._matches(alert, prefs):
            return {"queued": False, "reason": "no cumple las preferencias",
                    "alert_id": alert["alert_id"]}
        item = {
            "notification_id": f"NTF-{alert['alert_id']}-{len(self._queue) + 1}",
            "alert_id": alert["alert_id"],
            "category": alert["category"],
            "risk_level": alert["risk_level"],
            "crop_id": alert.get("crop_id"),
            "geographic_scope": self._redact_scope(alert["geographic_scope"])
            if redact else dict(alert["geographic_scope"]),
            "created_at": G.utcnow(),
            "channels": [c for c in self.CHANNELS if c in prefs["channels"]],
            "delivered_at": None,
            "external_service_used": False,
            "personal_data_included": False,
        }
        self._queue.append(item)
        return {"queued": True, "item": dict(item), "reason": None}

    def _preferences(self, preferences: dict[str, Any]) -> dict[str, Any]:
        channels = preferences.get("channels") or ["api", "ui"]
        unknown = set(channels) - set(self.CHANNELS)
        if unknown:
            raise G.MonitoringError(
                f"canales no admitidos: {sorted(unknown)}; use {list(self.CHANNELS)}")
        severity = preferences.get("min_severity", "low")
        if severity not in SEVERITY_LEVELS:
            raise G.MonitoringError(f"min_severity no admitido: {severity}")
        return {
            "channels": list(channels),
            "areas": [str(a).lower() for a in preferences.get("areas") or []],
            "crops": [str(c).lower() for c in preferences.get("crops") or []],
            "categories": list(preferences.get("categories") or []),
            "min_severity": severity,
        }

    def _matches(self, alert: dict[str, Any], prefs: dict[str, Any]) -> bool:
        order = {level: i for i, level in enumerate(SEVERITY_LEVELS)}
        if order[alert["risk_level"]] < order[prefs["min_severity"]]:
            return False
        if prefs["areas"]:
            haystack = json.dumps(alert["geographic_scope"],
                                  ensure_ascii=False).lower()
            if not any(area in haystack for area in prefs["areas"]):
                return False
        if prefs["crops"] and (alert.get("crop_id") or "").lower() not in prefs["crops"]:
            return False
        if prefs["categories"] and alert["category"] not in prefs["categories"]:
            return False
        return True

    @staticmethod
    def _redact_scope(scope: dict[str, Any]) -> dict[str, Any]:
        out = dict(scope)
        for key in ("latitude", "longitude", "lat", "lon"):
            if key in out:
                out[key] = None
        out["redacted"] = True
        return out

    def pending(self, *, channel: str | None = None) -> dict[str, Any]:
        items = [dict(i) for i in self._queue
                 if i["delivered_at"] is None
                 and (channel is None or channel in i["channels"])]
        return {"count": len(items), "items": items,
                "note": "cola local; no se usa ningún servicio de mensajería"}

    def sync(self, *, channel: str = "offline_sync") -> dict[str, Any]:
        if channel not in self.CHANNELS:
            raise G.MonitoringError(f"canal no admitido: {channel}")
        now = G.utcnow()
        delivered = 0
        for item in self._queue:
            if item["delivered_at"] is None and channel in item["channels"]:
                item["delivered_at"] = now
                delivered += 1
        return {"channel": channel, "delivered": delivered, "at": now}


class AgriculturalEarlyWarningEngine:
    engine = WARNING_ENGINE
    version = ENGINE_VERSION

    def forecast_warning(self, forecast: dict[str, Any], *,
                         crop_id: str | None = None,
                         threshold_c: float,
                         threshold_source: str,
                         stage: str | None = None) -> dict[str, Any]:
        """Aviso por pronóstico; nunca una afirmación determinista."""
        if not threshold_source:
            raise G.MonitoringError(
                "un aviso por pronóstico exige umbral con fuente")
        block = HeatAndClimateRiskEngineProxy.validate_forecast(forecast)
        values = forecast.get("values") or []
        tmax = []
        for value in values:
            if isinstance(value, dict):
                candidate = value.get("tmax_c")
            else:
                candidate = value
            if G.is_number(candidate):
                tmax.append(float(candidate))
        if not tmax:
            raise G.InsufficientRecordError("pronóstico sin temperaturas válidas")
        from .crop_health import ThermalStressEngine

        exposure = ThermalStressEngine.heat_exposure(
            tmax, threshold_c=threshold_c, threshold_source=threshold_source)
        status = ("possible_heat_warning" if exposure["days_above"] else
                  "no_warning")
        return {
            "engine": self.engine, "engine_version": self.version,
            "warning_type": "forecast_based",
            "status": status,
            "deterministic": False,
            "statement": ("posible exposición a calor por encima del umbral "
                          "en el horizonte pronosticado"
                          if exposure["days_above"] else
                          "sin exposición prevista sobre el umbral"),
            "exposure": exposure,
            "forecast": block,
            "crop_id": crop_id.lower() if crop_id else None,
            "stage": stage,
            "lead_time_days": block["horizon_days"],
            "uncertainty": block["uncertainty"],
            "evidence_class": "forecast",
            "limitations": [
                "un pronóstico no es una observación",
                "no se emite una afirmación determinista sobre el futuro",
                "la incertidumbre del proveedor debe conservarse",
            ],
        }

    def observation_warning(self, *, category: str, observed_value: float,
                            threshold: float, threshold_source: str,
                            geographic_scope: dict[str, Any],
                            evidence: list[dict[str, Any]]) -> dict[str, Any]:
        if category not in G.ALERT_CATEGORIES:
            raise G.MonitoringError(f"categoría no admitida: {category}")
        if not threshold_source:
            raise G.MonitoringError("el umbral observado exige fuente")
        triggered = float(observed_value) >= float(threshold)
        return {
            "engine": self.engine, "engine_version": self.version,
            "warning_type": "observation_based",
            "category": category, "status": "triggered" if triggered else "not_triggered",
            "observed_value": float(observed_value),
            "threshold": float(threshold), "threshold_source": threshold_source,
            "geographic_scope": geographic_scope, "evidence": evidence,
            "deterministic": True,
            "note": "describe una observación; no predice el futuro",
        }

    def official_warning(self, *, institution: str, notice_id: str,
                         statement: str, valid_from: str) -> dict[str, Any]:
        if not institution or not notice_id:
            raise G.MonitoringError("un aviso oficial exige institución e identificador")
        return {
            "engine": self.engine, "engine_version": self.version,
            "warning_type": "official_institutional",
            "institution": institution, "notice_id": notice_id,
            "statement": statement, "valid_from": valid_from,
            "evidence_class": "official_notice",
            "note": "se reproduce la institución; AGROSV no la reclasifica",
        }


class HeatAndClimateRiskEngineProxy:
    """Evita un import circular: reutiliza la validación de pronóstico."""

    @staticmethod
    def validate_forecast(forecast: dict[str, Any]) -> dict[str, Any]:
        from .risks import HeatAndClimateRiskEngine

        return HeatAndClimateRiskEngine._validate_forecast(forecast)
