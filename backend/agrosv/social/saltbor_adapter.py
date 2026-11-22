"""AGROSV — Adaptador de interoperabilidad E7 con IKarosUnic/sv-people (Saltbor).

Implementa la frontera HTTP/JSON entre AGROSV y `IKarosUnic/sv-people` sin
importar el paquete `saltbor` ni compartir base de datos SQLite:

1. **AGROSV / Nemotron → Saltbor (`sv-people`)**:
   - `to_saltbor_profiles`: traduce perfiles `SOURCE_PROFILE` (de Nemotron o
     sintéticos) al formato exacto de `PopulationFactory.create_from_profiles()`.
   - `to_saltbor_farm_plots`: traduce `SYNTHETIC_AGRICULTURAL_STATE` al
     esquema `FarmPlot` de `saltbor.domain.agriculture` (convirtiendo hectáreas
     a manzanas: 1 mz ≈ 0.70 ha).
   - `to_saltbor_bundle`: empaqueta perfiles, parcelas y eventos de simulación
     con trazabilidad y verificación de separación de capas.

2. **Saltbor (`sv-people`) → AGROSV**:
   - `from_saltbor_payload`: ingiere perfiles, humanos sintéticos o `FarmPlot`
     exportados por `sv-people`, los separa en `SOURCE_PROFILE` +
     `SYNTHETIC_AGRICULTURAL_STATE` y valida con `check_separation`.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from . import governance as SG
from .nemotron import is_agricultural_occupation, map_occupation_to_archetype

CONTRACT_VERSION = "1.0.0"
TARGET_REPO = "https://github.com/IKarosUnic/sv-people"
MANZANA_TO_HA = 0.70

_CROP_TO_SALTBOR = {
    "maize": "maiz",
    "beans": "frijol",
    "tomato": "hortalizas",
    "sweet_pepper": "hortalizas",
    "cucumber": "hortalizas",
    "onion": "hortalizas",
    "lettuce_urban": "hortalizas",
    "radish_urban": "hortalizas",
    "cilantro_urban": "hortalizas",
    "coffee": "cafe",
    "sorghum": "maicillo",
    "sugarcane": "cana",
}

_SALTBOR_TO_CROP = {
    "maiz": "maize",
    "maíz": "maize",
    "frijol": "beans",
    "hortalizas": "tomato",
    "cafe": "coffee",
    "café": "coffee",
    "maicillo": "sorghum",
    "cana": "sugarcane",
    "caña": "sugarcane",
}

_DEFAULT_YIELD_QQ_MZ = {
    "maiz": 45.0,
    "frijol": 16.0,
    "hortalizas": 120.0,
    "cafe": 18.0,
    "maicillo": 32.0,
    "cana": 110.0,
}

_GIVEN_NAME_RE = re.compile(r"^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)")


def _slug(value: str | None, fallback: str = "sv") -> str:
    if not value:
        return fallback
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return cleaned or fallback


def _map_gender_to_saltbor(sex_or_gender: str | None) -> str:
    val = str(sex_or_gender or "").strip().lower()
    if val in {"masculino", "male", "m", "hombre"}:
        return "male"
    if val in {"femenino", "female", "f", "mujer"}:
        return "female"
    return "non_binary"


def _map_sex_from_saltbor(gender: str | None) -> str | None:
    val = str(gender or "").strip().lower()
    if val in {"male", "masculino", "m"}:
        return "Masculino"
    if val in {"female", "femenino", "f"}:
        return "Femenino"
    return None


def _extract_given_name(
    profile: dict[str, Any],
    context: dict[str, Any],
    index: int,
) -> str:
    if profile.get("given_name"):
        return str(profile["given_name"])
    persona_txt = str(context.get("persona") or "").strip()
    if persona_txt:
        match = _GIVEN_NAME_RE.match(persona_txt)
        if match and match.group(1).lower() not in {"en", "con", "el", "la", "los", "las", "su"}:
            return match.group(1)
    return f"Productor_{index + 1}"


def _income_level_from_state(state_payload: dict[str, Any]) -> float:
    capital = float(state_payload.get("capital_usd", 500.0))
    # Escala acotada [0.10, 0.95] coherente con PopulationFactory de Saltbor
    normalized = min(0.95, max(0.10, (capital / 10_000.0) * 0.7 + 0.15))
    return round(normalized, 3)


def to_saltbor_profiles(
    items: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convierte agentes AGROSV o perfiles Nemotron al formato de Saltbor."""
    profiles: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if "state" in item:
            state_payload = item.get("state", {}).get("payload", {})
            src_block = item.get("source_profile") or {}
            src_profile = src_block.get("profile") if "profile" in src_block else src_block
            context = src_block.get("context", {})
            agent_id = item.get("agent_id")
        else:
            state_payload = {}
            src_profile = item.get("profile", item)
            context = item.get("context", {})
            agent_id = item.get("agent_id") or src_profile.get("uuid")

        src_profile = src_profile or {}
        dept = src_profile.get("department") or state_payload.get("department") or "San Salvador"
        dept_slug = _slug(dept)
        from_nemotron = bool(
            src_profile.get("from_nemotron_dataset")
            or src_profile.get("origin") in {"nemotron_dataset", "nemotron_sample"}
        )

        profiles.append({
            "serial": index + 1,
            "given_name": _extract_given_name(src_profile, context, index),
            "family_name": str(src_profile.get("family_name") or dept),
            "nickname": src_profile.get("nickname"),
            "age": int(src_profile.get("age") or 35),
            "gender": _map_gender_to_saltbor(src_profile.get("sex") or src_profile.get("gender")),
            "occupation": str(
                src_profile.get("occupation")
                or state_payload.get("archetype_label")
                or "Agricultor"
            ),
            "education_level": str(src_profile.get("education_level") or "primaria"),
            "income_level": _income_level_from_state(state_payload),
            "home_id": f"hogar_{dept_slug}_{index + 1}",
            "work_id": f"parcela_{dept_slug}_{index + 1}",
            "data_source": "nemotron_dataset" if from_nemotron else "mock_generated",
            "agrosv_agent_id": agent_id,
            "nemotron_uuid": src_profile.get("uuid"),
            "department": dept,
            "municipality": src_profile.get("municipality") or state_payload.get("municipality"),
            "area": src_profile.get("area") or state_payload.get("area_type") or "rural",
            "archetype": state_payload.get("archetype"),
        })
    return profiles


def to_saltbor_farm_plots(
    agents: Iterable[dict[str, Any]],
    *,
    soil_moisture_level: float = 0.75,
    current_growth_stage: str = "vegetative",
) -> list[dict[str, Any]]:
    """Convierte agentes agrícolas AGROSV al esquema FarmPlot de Saltbor."""
    plots: list[dict[str, Any]] = []
    for index, agent in enumerate(agents):
        payload = agent.get("state", {}).get("payload", {})
        primary = str(payload.get("primary_crop") or "maize").lower()
        crop_sb = _CROP_TO_SALTBOR.get(primary, "maiz")
        area_ha = float(payload.get("area_ha") or 1.0)
        area_mz = round(area_ha / MANZANA_TO_HA, 3)
        dept = str(payload.get("department") or "San Salvador")
        plots.append({
            "plot_id": f"parcela_agsv_{_slug(dept)}_{index + 1}",
            "owner_id": agent.get("agent_id") or f"human_agsv_{index + 1}",
            "department": dept,
            "municipality": payload.get("municipality"),
            "crop_type": crop_sb,
            "agrosv_crop_id": primary,
            "area_manzanas": area_mz,
            "area_ha": round(area_ha, 3),
            "expected_yield_per_manzana": _DEFAULT_YIELD_QQ_MZ.get(crop_sb, 35.0),
            "soil_moisture_level": round(float(soil_moisture_level), 3),
            "fertilizer_applied": float(payload.get("capital_usd", 0.0)) >= 300.0,
            "current_growth_stage": current_growth_stage,
            "harvested_quintales": 0.0,
            "irrigated": bool(payload.get("irrigated")),
        })
    return plots


def to_saltbor_bundle(
    agents: Iterable[dict[str, Any]],
    *,
    scenario_id: str | None = None,
    soil_moisture_level: float = 0.75,
    current_growth_stage: str = "vegetative",
) -> dict[str, Any]:
    """Genera un paquete completo AGROSV → Saltbor (sv-people) con eventos y trazabilidad."""
    agent_list = list(agents)
    profiles = to_saltbor_profiles(agent_list)
    plots = to_saltbor_farm_plots(
        agent_list,
        soil_moisture_level=soil_moisture_level,
        current_growth_stage=current_growth_stage,
    )

    records_to_check: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for index, agent in enumerate(agent_list):
        src_record = (agent.get("source_profile") or {}).get("record")
        if src_record:
            records_to_check.append(src_record)
        state_record = agent.get("state")
        if state_record:
            records_to_check.append(state_record)
        events.append({
            "event_type": "agrosv_saltbor_sync",
            "contract_version": CONTRACT_VERSION,
            "scenario_id": scenario_id,
            "agent_id": agent.get("agent_id"),
            "nemotron_uuid": agent.get("nemotron_uuid"),
            "saltbor_profile": profiles[index],
            "saltbor_farm_plot": plots[index],
            "source_record_id": src_record.get("record_id") if src_record else None,
            "state_record_id": state_record.get("record_id") if state_record else None,
        })

    layer_check = SG.check_separation(records_to_check) if records_to_check else {
        "valid": True, "errors": [], "layers": {},
    }

    return {
        "contract_version": CONTRACT_VERSION,
        "direction": "agrosv_to_saltbor",
        "target_repo": TARGET_REPO,
        "coupling": "http_json_only (sin importar saltbor ni compartir SQLite)",
        "count": len(agent_list),
        "nemotron_backed_count": sum(
            1 for p in profiles if p["data_source"] == "nemotron_dataset"
        ),
        "profiles": profiles,
        "farm_plots": plots,
        "events": events,
        "layer_check": layer_check,
        "provenance": {
            "source_dataset": SG.NEMOTRON,
            "target_compatible_methods": [
                "saltbor.population.factory.PopulationFactory.create_from_profiles",
                "saltbor.domain.agriculture.AgricultureActivityDomain.register_plot",
            ],
        },
    }


def from_saltbor_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Importa perfiles/humanos/parcelas de sv-people hacia capas separadas de AGROSV."""
    from .population import ARCHETYPES

    raw_profiles = list(
        payload.get("profiles") or payload.get("humans") or payload.get("agents") or []
    )
    raw_plots = list(payload.get("farm_plots") or payload.get("plots") or [])
    if not raw_profiles and not raw_plots:
        raise ValueError("el payload debe incluir 'profiles', 'humans', 'agents' o 'farm_plots'")

    plots_by_owner: dict[str, dict[str, Any]] = {}
    for plot in raw_plots:
        owner = str(plot.get("owner_id") or "")
        if owner:
            plots_by_owner[owner] = plot

    # Si solo se enviaron parcelas, sintetiza perfiles mínimos por propietario
    if not raw_profiles and raw_plots:
        for idx, plot in enumerate(raw_plots):
            raw_profiles.append({
                "owner_id": plot.get("owner_id") or f"saltbor_owner_{idx + 1}",
                "department": plot.get("department") or "San Salvador",
                "occupation": f"Cultivo de {plot.get('crop_type', 'maiz')}",
                "data_source": "simulation_generated",
            })

    imported_agents: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []

    for index, item in enumerate(raw_profiles):
        # Soporta estructura plana (create_from_profiles) o anidada (SyntheticHuman export)
        ident = item.get("identity") if isinstance(item.get("identity"), dict) else {}
        demo = item.get("demographics") if isinstance(item.get("demographics"), dict) else {}

        owner_key = str(
            item.get("agrosv_agent_id")
            or item.get("owner_id")
            or ident.get("uid")
            or item.get("uid")
            or ""
        )
        plot = plots_by_owner.get(owner_key) or (
            raw_plots[index] if index < len(raw_plots) else {}
        )

        occ = str(
            demo.get("occupation") or item.get("occupation") or "Agricultor"
        )
        edu = str(
            demo.get("education_level") or item.get("education_level") or "primaria"
        )
        dept = str(
            item.get("department") or plot.get("department") or "San Salvador"
        )
        area_str = str(item.get("area") or "rural")
        data_source = str(
            demo.get("data_source")
            or ident.get("data_source")
            or item.get("data_source")
            or "mock_generated"
        )
        from_nemotron = "nemotron" in data_source.lower()

        source_profile = {
            "uuid": item.get("nemotron_uuid") or ident.get("uid") or item.get("uuid"),
            "age": int(demo.get("age") or item.get("age") or 35),
            "sex": _map_sex_from_saltbor(demo.get("gender") or item.get("gender")),
            "education_level": edu,
            "occupation": occ,
            "area": area_str,
            "department": dept,
            "municipality": item.get("municipality"),
            "household_type": item.get("household_type") or "nuclear",
            "agricultural_occupation": is_agricultural_occupation(occ) or bool(plot),
            "origin": "saltbor_adapter",
            "saltbor_data_source": data_source,
            "from_nemotron_dataset": from_nemotron,
            "nemotron_schema_used": True,
            "not_a_real_person": True,
        }

        archetype = item.get("archetype")
        if not archetype or archetype not in ARCHETYPES:
            crop_hint = str(plot.get("crop_type") or "").lower()
            if crop_hint in {"hortalizas"}:
                archetype = "vegetable_producer"
            elif crop_hint in {"cafe", "café"}:
                archetype = "coffee_smallholder"
            elif crop_hint in {"frijol"}:
                archetype = "bean_producer"
            elif crop_hint in {"cana", "caña"}:
                archetype = "commercial_technified"
            else:
                archetype = map_occupation_to_archetype(
                    occ, area=area_str, education_level=edu
                )

        spec = ARCHETYPES[archetype]
        agent_id = str(
            item.get("agrosv_agent_id")
            or f"AGSV-SB-{archetype}-{index:06d}"
        )

        primary_crop = _SALTBOR_TO_CROP.get(
            str(plot.get("crop_type") or "").lower(),
            spec["primary_crop"],
        )
        crops = [primary_crop] + [c for c in spec["crops"] if c != primary_crop]
        area_ha = (
            round(float(plot["area_manzanas"]) * MANZANA_TO_HA, 3)
            if plot.get("area_manzanas") is not None
            else round(float(sum(spec["area_ha"]) / 2.0), 3)
        )
        income_lvl = float(demo.get("income_level") or item.get("income_level") or 0.4)
        capital_usd = round(max(100.0, income_lvl * 5000.0), 2)

        source_record = SG.make_record(
            "SOURCE_PROFILE",
            source_profile,
            method="importación controlada desde IKarosUnic/sv-people (Saltbor)",
            assumptions=[
                "el perfil proviene de Saltbor y se mantiene separado del estado agrícola",
                "no representa una persona real",
            ],
            agent_id=agent_id,
            validation_status="source_verified" if from_nemotron else "not_validated",
        )
        state_record = SG.make_record(
            "SYNTHETIC_AGRICULTURAL_STATE",
            {
                "archetype": archetype,
                "archetype_label": spec["label"],
                "production_system": spec["production_system"],
                "primary_crop": primary_crop,
                "crops": crops,
                "area_ha": area_ha,
                "irrigated": bool(plot.get("irrigated", False)),
                "capital_usd": capital_usd,
                "credit_access": round(float(sum(spec["credit_access"]) / 2.0), 3),
                "market_access": round(float(sum(spec["market_access"]) / 2.0), 3),
                "household_labor": int(sum(spec["household_labor"]) // 2),
                "hired_labor": int(sum(spec["hired_labor"]) // 2),
                "tenure": spec["tenure"][0],
                "risk_aversion": round(float(sum(spec["risk_aversion"]) / 2.0), 3),
                "info_access": round(float(sum(spec["info_access"]) / 2.0), 3),
                "experience_years": 10,
                "digital_literacy": round(float(sum(spec["digital_literacy"]) / 2.0), 3),
                "cooperative": archetype == "cooperative_member",
                "off_farm_income": round(float(sum(spec["off_farm_income"]) / 2.0), 3),
                "department": dept,
                "municipality": item.get("municipality"),
                "area_type": area_str,
                "saltbor_plot_id": plot.get("plot_id"),
                "parameter_basis": "saltbor_adapter_import",
            },
            method="traducción de perfil/parcela Saltbor a estado agrícola AGROSV",
            assumptions=[
                "1 manzana = 0.70 ha cuando proviene de FarmPlot de Saltbor",
                "variables agronómicas faltantes usan valores medios de arquetipo",
            ],
            agent_id=agent_id,
            parent_ids=[source_record["record_id"]],
        )
        all_records.extend([source_record, state_record])
        imported_agents.append({
            "agent_id": agent_id,
            "archetype": archetype,
            "seed": 42,
            "index": index,
            "source_profile": {
                "profile": source_profile,
                "record": source_record,
            },
            "state": state_record,
        })

    layer_check = SG.check_separation(all_records)
    return {
        "contract_version": CONTRACT_VERSION,
        "direction": "saltbor_to_agrosv",
        "source_repo": TARGET_REPO,
        "count": len(imported_agents),
        "nemotron_backed_count": sum(
            1 for a in imported_agents
            if a["source_profile"]["profile"]["from_nemotron_dataset"]
        ),
        "agents": imported_agents,
        "layer_check": layer_check,
    }


__all__ = [
    "CONTRACT_VERSION",
    "MANZANA_TO_HA",
    "TARGET_REPO",
    "from_saltbor_payload",
    "to_saltbor_bundle",
    "to_saltbor_farm_plots",
    "to_saltbor_profiles",
]
