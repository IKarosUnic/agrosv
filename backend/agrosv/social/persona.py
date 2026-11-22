"""AGROSV — AgriculturalPersonaEngine (§5.3).

Usa el **esquema** de Nemotron-Personas-El-Salvador como base contextual. Dos
orígenes distintos, nunca confundidos:

    nemotron_sample              fila real de la muestra descargada (3 filas)
    schema_compatible_synthetic  perfil generado por AGROSV con el mismo esquema

La muestra de 3 filas no contiene ocupaciones agrícolas. Por eso el motor
**no** reasigna la ocupación de esas filas: si se intenta adjuntar un estado
agrícola a un perfil no agrícola, se rechaza salvo autorización explícita y se
marca `role_consistent_with_source: false`.

No se generan nombres, direcciones ni identidades. El estado agrícola viaja en
su propia capa y no se fusiona con el perfil de origen.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ..engines import governance as G5
from . import governance as SG

ENGINE = "agricultural_persona"
ENGINE_VERSION = SG.ENGINE_VERSION

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PATH = ROOT / "data/samples/phase3/nemotron_rows/nemotron_rows_sample.json"

EDUCATION = ("primaria", "bachillerato", "universitario")
HOUSEHOLD_TYPES = ("unipersonal", "nuclear", "monoparental", "extendida")

_AGRICULTURAL_WORDS = (
    "agricultura", "agricola", "agrícola", "cultivo", "cereales", "café",
    "cafe", "maíz", "maiz", "frijol", "hortaliza", "fruta", "ganader",
    "pecuar", "silvicultura", "pesca", "riego",
)

_OCCUPATION_BY_SYSTEM = {
    "rainfed_subsistence": "Cultivo de cereales y legumbres (subsistencia)",
    "rainfed_smallholder": "Cultivo de cereales y legumbres",
    "agroforestry_smallholder": "Cultivo de café bajo sombra",
    "irrigated_horticulture": "Cultivo de hortalizas y melones",
    "rainfed_or_irrigated_orchard": "Cultivo de frutales",
    "diversified_smallholder": "Cultivo mixto de cereales, legumbres y hortalizas",
    "urban_small_space": "Producción agrícola urbana en pequeño espacio",
    "cooperative": "Cultivo de café en cooperativa",
    "commercial_technified": "Cultivo de caña de azúcar y granos",
}


class PersonaError(ValueError):
    pass


def occupation_is_agricultural(occupation: str | None) -> bool:
    if not occupation:
        return False
    text = occupation.lower()
    return any(word in text for word in _AGRICULTURAL_WORDS)


def _load_sample(limit: int | None) -> list[dict[str, Any]]:
    if not SAMPLE_PATH.exists():
        raise G5.SourceUnavailableError(
            "nemotron_personas_sv", [str(SAMPLE_PATH)],
            "ejecute scripts/07_fetch_phase3_samples.py")
    raw = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    rows = raw.get("rows", [])
    if limit is not None:
        rows = rows[:limit]
    profiles = []
    for item in rows:
        row = item.get("row", item)
        if isinstance(row, str):
            row = json.loads(row)
        profiles.append(row)
    return profiles


class AgriculturalPersonaEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    # --- perfiles de origen ------------------------------------------------
    def sample_profiles(self, limit: int | None = None) -> dict[str, Any]:
        rows = _load_sample(limit)
        profiles, records = [], []
        for row in rows:
            profile = {
                "uuid": row.get("uuid"),
                "age": row.get("age"),
                "education_level": row.get("education_level"),
                "occupation": row.get("occupation"),
                "area": row.get("area"),
                "department": row.get("department"),
                "municipality": row.get("municipality"),
                "household_type": row.get("household_type"),
                "marital_status": row.get("marital_status"),
                "agricultural_occupation": occupation_is_agricultural(
                    row.get("occupation")),
                "origin": "nemotron_sample",
                "not_a_real_person": True,
            }
            records.append(SG.make_record(
                "SOURCE_PROFILE", profile,
                method="lectura directa de la muestra Nemotron (sin alterar)",
                assumptions=[
                    "la fila es una persona sintética del dataset, no una "
                    "persona real",
                    "CC BY 4.0 permite reutilización con atribución",
                ],
                agent_id=profile["uuid"],
                validation_status="source_verified"))
            profiles.append({"profile": profile,
                             "provenance": {"dataset": SG.NEMOTRON,
                                            "license": "CC BY 4.0"}})
        agricultural = sum(1 for p in profiles
                           if p["profile"]["agricultural_occupation"])
        return {
            "count": len(profiles),
            "agricultural_count": agricultural,
            "profiles": profiles,
            "records": records,
            "note": ("la muestra descargada no contiene ocupaciones "
                     "agrícolas" if agricultural == 0 else
                     "algunas filas declaran ocupación agrícola"),
        }

    def nemotron_agricultural_profiles(
        self,
        *,
        department: str | None = None,
        municipality: str | None = None,
        area: str | None = None,
        archetype: str | None = None,
        occupation_query: str | None = None,
        limit: int = 20,
        live: bool = False,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Obtiene perfiles reales con ocupación agrícola desde Nemotron SV."""
        from .nemotron import NemotronDatasetClient

        return NemotronDatasetClient().query_profiles(
            department=department,
            municipality=municipality,
            area=area,
            archetype=archetype,
            occupation_query=occupation_query,
            agricultural_only=True,
            limit=limit,
            live=live,
            offset=offset,
        )

    def synthetic_source_profile(self, agent: dict[str, Any], *,
                                 seed: int = 42) -> dict[str, Any]:
        state = agent.get("state", {}).get("payload", {})
        index = int(agent.get("index", 0))
        rng = np.random.default_rng(seed * 1_000_003 + index)
        system = state.get("production_system", "rainfed_smallholder")
        age = int(rng.integers(18, 81))
        education = str(rng.choice(EDUCATION, p=[0.55, 0.32, 0.13]))
        household = str(rng.choice(HOUSEHOLD_TYPES, p=[0.10, 0.55, 0.15, 0.20]))
        profile = {
            "uuid": None,
            "age": age,
            "education_level": education,
            "occupation": _OCCUPATION_BY_SYSTEM.get(
                system, "Cultivo de cereales y legumbres"),
            "area": state.get("area_type", "rural"),
            "department": state.get("department"),
            "municipality": None,
            "household_type": household,
            "agricultural_occupation": True,
            "origin": "schema_compatible_synthetic",
            "from_nemotron_dataset": False,
            "sex": None,
            "sex_omitted": "minimización de atributos sensibles",
            "not_a_real_person": True,
            "nemotron_schema_used": True,
        }
        record = SG.make_record(
            "SOURCE_PROFILE", profile,
            method=("perfil compatible con el esquema Nemotron generado por "
                    "AGROSV; no proviene del dataset"),
            assumptions=[
                "el perfil imita el esquema, no una fila de Nemotron",
                "educación y tipo de hogar son sorteos sintéticos",
                "no se genera nombre ni identidad",
                "el sexo se omite por minimización",
            ],
            agent_id=agent.get("agent_id"),
            scenario_id=(agent.get("state") or {}).get("scenario_id"),
            validation_status="not_validated")
        return {"profile": profile, "record": record,
                "provenance": {"schema": SG.NEMOTRON,
                               "rows_used": 0,
                               "license": "CC BY 4.0 (esquema y atribución)"}}

    # --- composición -------------------------------------------------------
    def compose(self, agent: dict[str, Any], *,
                source_profile: dict[str, Any] | None = None,
                seed: int = 42,
                allow_role_extension: bool = False,
                use_nemotron_corpus: bool = False) -> dict[str, Any]:
        if "state" not in agent:
            raise PersonaError("el agente no tiene capa SYNTHETIC_AGRICULTURAL_STATE")
        if source_profile is None and "source_profile" in agent:
            source_profile = agent["source_profile"]
        if source_profile is None and use_nemotron_corpus:
            state_payload = agent["state"].get("payload", {})
            matches = self.nemotron_agricultural_profiles(
                department=state_payload.get("department"),
                archetype=agent.get("archetype"),
                limit=5,
            )
            if not matches["profiles"]:
                matches = self.nemotron_agricultural_profiles(limit=5)
            if matches["profiles"]:
                idx = int(agent.get("index", 0)) % len(matches["profiles"])
                picked = matches["profiles"][idx]
                source_profile = {
                    "profile": picked["profile"],
                    "record": matches["records"][idx],
                    "provenance": picked["provenance"],
                }
        origin = source_profile or self.synthetic_source_profile(agent, seed=seed)
        profile = origin["profile"]
        if not profile.get("origin"):
            raise PersonaError("el perfil de origen no declara procedencia")
        consistent = bool(profile.get("agricultural_occupation"))
        if not consistent and not allow_role_extension:
            return {
                "attachable": False,
                "reason": ("el perfil de origen no declara ocupación agrícola; "
                           "AGROSV no reasigna roles sin autorización explícita"),
                "source_profile": profile,
                "source_record": origin.get("record"),
                "synthetic_agricultural_state": agent["state"],
                "layer_separation": ("SOURCE_PROFILE y "
                                     "SYNTHETIC_AGRICULTURAL_STATE se "
                                     "transportan por separado"),
            }
        card = {
            "display_label": (f"Productor sintético {agent['agent_id']} · "
                              f"arquetipo {agent['archetype']}"),
            "is_person": False,
            "source_profile": profile,
            "agricultural_state": agent["state"]["payload"],
            "role_consistent_with_source": consistent,
            "role_assigned_by_agrosv": not consistent,
            "language": "es-SV",
            "warnings": [
                "persona sintética; no corresponde a una persona real",
                "el estado agrícola es una capa AGROSV separada",
            ],
        }
        if not consistent:
            card["warnings"].append(
                "la ocupación del perfil de origen no es agrícola: el rol fue "
                "asignado por AGROSV con autorización")
        return {
            "attachable": True,
            "persona": card,
            "source_profile": profile,
            "source_record": origin.get("record"),
            "synthetic_agricultural_state": agent["state"],
            "record": SG.make_record(
                "SIMULATION_HISTORY",
                {"persona_card": card},
                method="composición de perfil de origen y estado agrícola",
                assumptions=["las capas permanecen separadas en el resultado"],
                agent_id=agent["agent_id"],
                parent_ids=[r for r in (origin.get("record", {}).get("record_id"),
                                        agent["state"].get("record_id")) if r],
                validation_status="not_validated"),
        }

    def validate(self, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
        return SG.check_separation(records)


__all__ = ["AgriculturalPersonaEngine", "PersonaError", "SAMPLE_PATH",
           "occupation_is_agricultural", "EDUCATION", "HOUSEHOLD_TYPES"]
