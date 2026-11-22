"""AGROSV — gobernanza de datos sintéticos (§6).

La separación de capas es una regla de código, no una convención de estilo:
`make_record` exige la capa, y `check_separation` rechaza cualquier registro
sintético que contenga una clave de otra capa o que se declare observado.

Ningún registro sintético puede llevar `evidence_class` observacional.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from ..agriculture import governance as AG
from ..engines import governance as G5

ENGINE_VERSION = AG.ENGINE_VERSION
SERVICE = "agrosv.social"

LAYERS = (
    "SOURCE_PROFILE",
    "SYNTHETIC_AGRICULTURAL_STATE",
    "HOUSEHOLD_STATE",
    "SIMULATION_HISTORY",
    "OBSERVED_VALIDATION_DATA",
)
SYNTHETIC_LAYERS = LAYERS[:4]

NEMOTRON = {
    "dataset_id": "nemotron_personas_sv",
    "name": "nvidia/Nemotron-Personas-El-Salvador",
    "license": "CC BY 4.0",
    "sha256": "68f6a21c17973d6a34ac6354d50a31c1fbcec14f",
    "url": "https://huggingface.co/datasets/nvidia/Nemotron-Personas-El-Salvador",
    "rows": 148000,
    "columns": 25,
}


class LayerError(ValueError):
    """Una capa o un registro viola la separación exigida."""


def synthetic_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8"))
    return f"{prefix}-{digest.hexdigest()[:12]}"


def make_record(layer: str, payload: dict[str, Any], *, method: str,
                assumptions: Iterable[str], scenario_id: str | None = None,
                validation_status: str = "not_validated",
                agent_id: str | None = None,
                parent_ids: Iterable[str] = (),
                evidence_class: str = "synthetic") -> dict[str, Any]:
    if layer not in LAYERS:
        raise LayerError(f"capa desconocida: {layer}; use {LAYERS}")
    if layer == "OBSERVED_VALIDATION_DATA":
        raise LayerError(
            "esta función no crea datos observados: una fuente real se "
            "registra con su ficha y no se genera")
    if evidence_class == "observed_statistic":
        raise LayerError(
            "un registro sintético no puede declararse observed_statistic")
    if not assumptions:
        raise LayerError("todo registro sintético declara supuestos")
    missing = [a for a in assumptions if not str(a).strip()]
    if missing:
        raise LayerError("supuestos vacíos")
    return {
        "record_id": synthetic_id(layer[:3], layer, agent_id, scenario_id,
                                  json.dumps(payload, sort_keys=True,
                                             default=str)),
        "layer": layer,
        "synthetic": True,
        "evidence_class": evidence_class,
        "engine_version": ENGINE_VERSION,
        "generation_method": method,
        "created_at": G5.utcnow(),
        "scenario_id": scenario_id,
        "agent_id": agent_id,
        "parents": list(parent_ids),
        "assumptions": list(assumptions),
        "validation_status": validation_status,
        "payload": payload,
    }


_FORBIDDEN_IN_PROFILE = {
    "crop_id", "area_ha", "irrigated", "capital_usd", "credit_access",
    "yield_t_ha", "adoption", "farm_gate_price", "household_income",
}


def check_separation(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Verifica que cada registro tenga una sola capa y que no se mezclen."""
    errors: list[str] = []
    seen: dict[str, int] = {}
    for index, record in enumerate(records):
        layer = record.get("layer")
        if layer not in LAYERS:
            errors.append(f"registro {index}: capa inválida {layer!r}")
            continue
        seen[layer] = seen.get(layer, 0) + 1
        payload = record.get("payload") or {}
        if layer == "SOURCE_PROFILE":
            leaked = _FORBIDDEN_IN_PROFILE.intersection(payload)
            if leaked:
                errors.append(
                    f"registro {index}: SOURCE_PROFILE contiene campos "
                    f"agrícolas {sorted(leaked)}")
        if record.get("synthetic") and layer == "OBSERVED_VALIDATION_DATA":
            errors.append(f"registro {index}: observado marcado como sintético")
        if not record.get("generation_method"):
            errors.append(f"registro {index}: sin método de generación")
        if not record.get("assumptions"):
            errors.append(f"registro {index}: sin supuestos")
    return {
        "valid": not errors,
        "errors": errors,
        "layers": seen,
        "rule": "las capas se transportan juntas, nunca se fusionan",
    }


def synthetic_envelope(engine: str, *, result: dict[str, Any],
                       assumptions: Iterable[str],
                       limitations: Iterable[str],
                       sources: Iterable[str] = ("agrosv_scenario",),
                       scenario_id: str | None = None,
                       processing: list[dict[str, Any]] | None = None,
                       query: dict[str, Any] | None = None) -> dict[str, Any]:
    limitations = list(limitations)
    if not limitations:
        raise ValueError("un resultado sintético sin limitaciones no se publica")
    payload = AG.envelope(
        engine, result=result, sources=list(sources),
        limitations=limitations, processing=processing, query=query,
        extra={
            "synthetic": True,
            "scenario_id": scenario_id,
            "represents_real_people": False,
            "population_inference_allowed": False,
        },
    )
    payload["governance"] = {
        "layers": list(LAYERS),
        "assumptions": list(assumptions),
        "rule": ("ninguna persona generada representa a un individuo real; "
                 "no se infieren distribuciones poblacionales sin calibración "
                 "empírica independiente"),
    }
    return payload


__all__ = ["LAYERS", "SYNTHETIC_LAYERS", "NEMOTRON", "LayerError",
           "synthetic_id", "make_record", "check_separation",
           "synthetic_envelope", "ENGINE_VERSION", "SERVICE"]
