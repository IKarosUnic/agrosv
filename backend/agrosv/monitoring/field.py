"""AGROSV — AgriculturalFieldVerificationEngine (Fase 7, §9.4).

Observaciones de campo aportadas por personas. No son registros científicos
confirmados: entran como `field_observation`, con controles de calidad,
detección de duplicados, requisitos de evidencia, flujo de revisión e historial.

Privacidad: la coordenada exacta no se publica salvo consentimiento explícito;
en la vista pública se redondea a 2 decimales (~1 km).
"""
from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timezone
from typing import Any

from .. import config as C
from . import governance as G

ENGINE = "agricultural_field_verification"
ENGINE_VERSION = G.ENGINE_VERSION

OBSERVATION_TYPES = ("crop_observation", "pest_suspected", "disease_symptoms",
                     "water_stress", "flood_damage", "heat_damage",
                     "crop_loss", "management_practice")

PHOTO_REQUIRED = frozenset({"pest_suspected", "disease_symptoms", "crop_loss"})
STATUSES = ("received", "needs_evidence", "in_review", "accepted", "rejected")


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * radius * math.asin(math.sqrt(a))


class AgriculturalFieldVerificationEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self._observations: dict[str, dict[str, Any]] = {}

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = ("observation_type", "latitude", "longitude",
                    "observed_on", "contributor_id")
        missing = [k for k in required if payload.get(k) is None]
        if missing:
            raise G.MonitoringError(f"faltan campos: {missing}")
        obs_type = payload["observation_type"]
        if obs_type not in OBSERVATION_TYPES:
            raise G.MonitoringError(
                f"tipo no admitido: {obs_type}; use {list(OBSERVATION_TYPES)}")
        lat, lon = float(payload["latitude"]), float(payload["longitude"])
        west, south, east, north = C.SV_BOUNDS
        if not (west <= lon <= east and south <= lat <= north):
            raise G.MonitoringError("la observación cae fuera de El Salvador")
        try:
            observed = date.fromisoformat(str(payload["observed_on"])[:10])
        except ValueError:
            raise G.MonitoringError("observed_on debe ser YYYY-MM-DD") from None
        if observed > date.today():
            raise G.MonitoringError("la fecha de observación no puede ser futura")
        photos = list(payload.get("photos") or [])
        warnings: list[str] = []
        if abs(lat - round(lat, 2)) < 1e-9 and abs(lon - round(lon, 2)) < 1e-9:
            warnings.append("coordenada con precisión de ~1 km: puede no "
                            "identificar la parcela")
        duplicate_of = self._find_duplicate(obs_type, lat, lon, observed,
                                            payload.get("crop_id"))
        if duplicate_of:
            warnings.append(f"posible duplicado de {duplicate_of}")
        status = "received"
        if obs_type in PHOTO_REQUIRED and not photos:
            status = "needs_evidence"
            warnings.append("el tipo de observación exige fotografía georreferenciada")
        identifier = "FLD-" + hashlib.sha256(
            f"{obs_type}|{lat:.5f}|{lon:.5f}|{observed}|"
            f"{payload['contributor_id']}".encode("utf-8")).hexdigest()[:12]
        now = G.utcnow()
        record = {
            "observation_id": identifier,
            "observation_type": obs_type,
            "latitude": lat, "longitude": lon,
            "observed_on": observed.isoformat(),
            "crop_id": (payload.get("crop_id") or "").lower() or None,
            "crop_stage": payload.get("crop_stage"),
            "severity": payload.get("severity"),
            "notes": payload.get("notes"),
            "photos": photos,
            "management": payload.get("management"),
            "contributor_id": payload["contributor_id"],
            "contributor_type": payload.get("contributor_type", "community"),
            "publish_coordinates": bool(payload.get("publish_coordinates", False)),
            "status": status,
            "quality_checks": {
                "inside_country": True,
                "date_not_future": True,
                "photo_supplied": bool(photos),
                "photo_required": obs_type in PHOTO_REQUIRED,
                "duplicate_of": duplicate_of,
                "coordinate_precision_warning": any(
                    "precisión" in w for w in warnings),
            },
            "warnings": warnings,
            "evidence_class": "field_observation",
            "verified_scientific_record": False,
            "submitted_at": now,
            "audit": [{"at": now, "action": "submitted",
                       "actor": payload["contributor_id"],
                       "status": status}],
        }
        self._observations[identifier] = record
        return dict(record)

    def _find_duplicate(self, obs_type: str, lat: float, lon: float,
                        observed: date, crop_id: str | None) -> str | None:
        for other in self._observations.values():
            if other["observation_type"] != obs_type:
                continue
            if (other.get("crop_id") or "") != (crop_id or "").lower():
                continue
            try:
                other_date = date.fromisoformat(other["observed_on"])
            except ValueError:
                continue
            if abs((other_date - observed).days) > 7:
                continue
            if _haversine_m(lat, lon, other["latitude"],
                            other["longitude"]) <= 500:
                return other["observation_id"]
        return None

    def list(self, *, status: str | None = None,
             obs_type: str | None = None,
             crop_id: str | None = None) -> dict[str, Any]:
        items = [dict(r) for r in self._observations.values()
                 if (status is None or r["status"] == status)
                 and (obs_type is None or r["observation_type"] == obs_type)
                 and (crop_id is None or r.get("crop_id") == crop_id.lower())]
        items.sort(key=lambda r: r["observed_on"], reverse=True)
        return {"count": len(items), "observations": items,
                "by_status": self._count("status"), "by_type": self._count("observation_type"),
                "note": "ninguna observación es un registro confirmado por envío"}

    def _count(self, key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for record in self._observations.values():
            out[record[key]] = out.get(record[key], 0) + 1
        return out

    def get(self, observation_id: str) -> dict[str, Any]:
        if observation_id not in self._observations:
            raise KeyError(f"observación desconocida: {observation_id}")
        return dict(self._observations[observation_id])

    def review(self, observation_id: str, *, reviewer_id: str,
               decision: str, notes: str = "") -> dict[str, Any]:
        if decision not in {"accept", "reject", "request_evidence"}:
            raise G.MonitoringError("decisión no admitida")
        record = self._observations.get(observation_id)
        if record is None:
            raise KeyError(f"observación desconocida: {observation_id}")
        now = G.utcnow()
        if decision == "accept":
            record["status"] = "accepted"
        elif decision == "reject":
            record["status"] = "rejected"
        else:
            record["status"] = "needs_evidence"
        record["audit"].append({"at": now, "action": "review",
                                "actor": reviewer_id, "decision": decision,
                                "notes": notes, "status": record["status"]})
        record["verified_scientific_record"] = False
        return dict(record)

    def public_view(self, observation_id: str) -> dict[str, Any]:
        record = self.get(observation_id)
        lat, lon = record["latitude"], record["longitude"]
        if not record["publish_coordinates"]:
            lat, lon = round(lat, 2), round(lon, 2)
        return {
            "observation_id": record["observation_id"],
            "observation_type": record["observation_type"],
            "latitude": lat, "longitude": lon,
            "coordinate_precision": ("exacta" if record["publish_coordinates"]
                                     else "redondeada ~1 km"),
            "observed_on": record["observed_on"], "crop_id": record["crop_id"],
            "status": record["status"],
            "evidence_class": "field_observation",
            "verified_scientific_record": False,
            "photos": len(record["photos"]),
            "note": "observación aportada por una persona; no es un registro "
                    "oficial ni una confirmación científica",
        }

    def summary(self) -> dict[str, Any]:
        return {
            "engine": self.engine, "engine_version": self.version,
            "total": len(self._observations), "by_status": self._count("status"),
            "by_type": self._count("observation_type"),
            "accepted_not_verified": sum(
                1 for r in self._observations.values()
                if r["status"] == "accepted" and not r["verified_scientific_record"]),
            "note": ("la aceptación en revisión no convierte la observación en "
                     "un registro científico verificado"),
        }
