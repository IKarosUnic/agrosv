"""AGROSV — Conector real para nvidia/Nemotron-Personas-El-Salvador.

Permite consumir filas reales del dataset `nvidia/Nemotron-Personas-El-Salvador`
(tanto desde el corpus agrícola descargado localmente como en vivo mediante
Hugging Face Datasets Server) respetando la separación estricta de capas:

- `SOURCE_PROFILE`: campos originales de Nemotron (`origin="nemotron_dataset"`,
  `from_nemotron_dataset=True`). Nunca contiene variables agrícolas inventadas.
- `SYNTHETIC_AGRICULTURAL_STATE`: estado agrícola generado por AGROSV y
  anclado a la ocupación, departamento, municipio y área de la fila Nemotron.
"""
from __future__ import annotations

import json
import time
import unicodedata
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import requests

from .. import config as C
from ..engines import governance as G5
from . import governance as SG

DATASET_ID = "nvidia/Nemotron-Personas-El-Salvador"
HF_ROWS_URL = "https://datasets-server.huggingface.co/rows"
CORPUS_PATH = (
    C.DATA / "samples" / "phase3" / "nemotron_rows"
    / "nemotron_agricultural_corpus.json"
)
SAMPLE_PATH = (
    C.DATA / "samples" / "phase3" / "nemotron_rows"
    / "nemotron_rows_sample.json"
)

AGRICULTURAL_KEYWORDS = (
    "agricultura",
    "agricola",
    "agrícola",
    "agropecuar",
    "cultivo de ",
    "cultivos ",
    "cereales",
    "hortalizas",
    "café",
    "cafe",
    "plantas con las que se preparan bebidas",
    "caña de azúcar",
    "cana de azucar",
    "frutas tropicales",
    "frutas de pepita",
    "frutos oleaginosos",
    "cría de ganado",
    "cria de ganado",
    "cría de aves",
    "cria de aves",
    "cría de cerdos",
    "cria de cerdos",
    "cría de otros animales",
    "cria de otros animales",
    "apicultura",
    "silvicultura",
    "explotación forestal",
    "explotacion forestal",
    "pesca ",
    "acuicultura",
    "apoyo a la agricultura",
    "maíz",
    "maiz",
    "frijol",
)

_NON_FARM_EXCLUSIONS = (
    "venta al por",
    "comercio",
    "elaboracion de bebidas",
    "elaboracion de productos",
    "restaurantes",
    "transporte",
)


def _norm(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.strip().lower()


def is_agricultural_occupation(occupation: str | None) -> bool:
    """Devuelve True si la ocupación de Nemotron corresponde al sector agro/rural."""
    normed = _norm(occupation)
    if not normed:
        return False
    if any(excl in normed for excl in _NON_FARM_EXCLUSIONS):
        return False
    return any(_norm(word) in normed for word in AGRICULTURAL_KEYWORDS)


def map_occupation_to_archetype(
    occupation: str | None,
    *,
    area: str | None = None,
    education_level: str | None = None,
) -> str:
    """Mapea una ocupación real de Nemotron al arquetipo agrícola más coherente."""
    occ = _norm(occupation)
    area_n = _norm(area)
    edu_n = _norm(education_level)

    if "preparan bebidas" in occ or "cafe" in occ:
        return "coffee_smallholder"
    if "cana de azucar" in occ:
        return "commercial_technified"
    if "hortalizas" in occ or "melones" in occ or "tuberculos" in occ:
        if "urban" in area_n:
            return "urban_farmer"
        return "vegetable_producer"
    if "cereales" in occ or "legumbres" in occ or "arroz" in occ or "maiz" in occ or "frijol" in occ:
        if any(k in edu_n for k in ("primaria", "ningun", "sin estudios", "basica")):
            return "subsistence_maize"
        return "smallholder_basic_grains"
    if "frutas" in occ or "frutos" in occ or "nueces" in occ:
        return "fruit_producer"
    if "urban" in area_n and "cultivo" in occ:
        return "urban_farmer"
    return "mixed_crop"


def row_to_source_profile(
    row: dict[str, Any],
    *,
    row_idx: int | None = None,
) -> dict[str, Any]:
    """Normaliza una fila real de Nemotron al contrato SOURCE_PROFILE."""
    occ = row.get("occupation")
    profile = {
        "uuid": row.get("uuid"),
        "age": row.get("age"),
        "sex": row.get("sex"),
        "education_level": row.get("education_level"),
        "occupation": occ,
        "area": row.get("area"),
        "department": row.get("department"),
        "municipality": row.get("municipality"),
        "household_type": row.get("household_type"),
        "marital_status": row.get("marital_status"),
        "languages_spoken": row.get("languages_spoken"),
        "country": row.get("country", "El Salvador"),
        "agricultural_occupation": is_agricultural_occupation(occ),
        "origin": "nemotron_dataset",
        "from_nemotron_dataset": True,
        "nemotron_schema_used": True,
        "not_a_real_person": True,
    }
    if row_idx is not None:
        profile["nemotron_row_idx"] = int(row_idx)
    return profile


def _extract_row_dict(item: dict[str, Any]) -> tuple[int | None, dict[str, Any]]:
    row_idx = item.get("row_idx")
    row = item.get("row", item)
    if isinstance(row, str):
        row = json.loads(row)
    return row_idx, row


class NemotronDatasetClient:
    """Cliente de lectura local y en vivo para nvidia/Nemotron-Personas-El-Salvador."""

    def __init__(self, corpus_path: Path | None = None) -> None:
        self.corpus_path = corpus_path or CORPUS_PATH

    def corpus_available(self) -> bool:
        return self.corpus_path.exists()

    def fetch_live_rows(
        self,
        *,
        offset: int = 0,
        length: int = 100,
        agricultural_only: bool = False,
        timeout: int = 30,
        retries: int = 3,
    ) -> dict[str, Any]:
        """Consulta en vivo Hugging Face Datasets Server para Nemotron SV."""
        if length <= 0 or length > 100:
            raise ValueError("length debe estar entre 1 y 100")
        last_exc: Exception | None = None
        payload: dict[str, Any] | None = None
        for attempt in range(max(1, retries)):
            try:
                resp = requests.get(
                    HF_ROWS_URL,
                    params={
                        "dataset": DATASET_ID,
                        "config": "default",
                        "split": "train",
                        "offset": int(offset),
                        "length": int(length),
                    },
                    timeout=timeout,
                )
                if resp.status_code in {429, 500, 502, 503, 504} and attempt + 1 < retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                resp.raise_for_status()
                payload = resp.json()
                break
            except requests.RequestException as exc:
                last_exc = exc
                if attempt + 1 < retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise
        if payload is None:
            raise RuntimeError(f"Error consultando Nemotron: {last_exc}")
        raw_items = payload.get("rows", [])
        rows: list[dict[str, Any]] = []
        for item in raw_items:
            idx, row = _extract_row_dict(item)
            if agricultural_only and not is_agricultural_occupation(row.get("occupation")):
                continue
            rows.append({"row_idx": idx, "row": row})
        return {
            "source": "huggingface_datasets_server",
            "dataset": DATASET_ID,
            "offset": offset,
            "length": length,
            "num_rows_total": payload.get("num_rows_total"),
            "returned": len(rows),
            "rows": rows,
        }

    def load_corpus_items(self) -> dict[str, Any]:
        """Carga el corpus agrícola descargado localmente de Nemotron."""
        if not self.corpus_path.exists():
            raise G5.SourceUnavailableError(
                "nemotron_personas_sv",
                [str(self.corpus_path)],
                "ejecute scripts/14_fetch_nemotron_agricultural.py",
            )
        raw = json.loads(self.corpus_path.read_text(encoding="utf-8"))
        items = raw.get("rows", [])
        normalized: list[dict[str, Any]] = []
        for item in items:
            idx, row = _extract_row_dict(item)
            normalized.append({"row_idx": idx, "row": row})
        return {
            "metadata": raw.get("metadata", {}),
            "rows": normalized,
        }

    def query_profiles(
        self,
        *,
        department: str | None = None,
        municipality: str | None = None,
        area: str | None = None,
        archetype: str | None = None,
        occupation_query: str | None = None,
        agricultural_only: bool = True,
        limit: int = 20,
        live: bool = False,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Obtiene perfiles reales de Nemotron normalizados como SOURCE_PROFILE."""
        if limit <= 0 or limit > 500:
            raise ValueError("limit debe estar entre 1 y 500")

        if live:
            fetched = self.fetch_live_rows(
                offset=offset,
                length=min(100, max(limit, 20)),
                agricultural_only=agricultural_only,
            )
            items = fetched["rows"]
            origin_mode = "huggingface_live"
            corpus_meta: dict[str, Any] = {
                "num_rows_total": fetched.get("num_rows_total"),
                "offset": offset,
            }
        else:
            loaded = self.load_corpus_items()
            items = loaded["rows"]
            origin_mode = "local_nemotron_corpus"
            corpus_meta = loaded.get("metadata", {})

        dept_n = _norm(department)
        muni_n = _norm(municipality)
        area_n = _norm(area)
        occ_n = _norm(occupation_query)
        arch_n = _norm(archetype)

        profiles: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []

        for item in items:
            idx, row = item.get("row_idx"), item.get("row", item)
            occ = row.get("occupation")
            if agricultural_only and not is_agricultural_occupation(occ):
                continue
            if dept_n and dept_n not in _norm(row.get("department")):
                continue
            if muni_n and muni_n not in _norm(row.get("municipality")):
                continue
            if area_n and area_n != _norm(row.get("area")):
                continue
            if occ_n and occ_n not in _norm(occ):
                continue
            mapped_arch = map_occupation_to_archetype(
                occ, area=row.get("area"), education_level=row.get("education_level")
            )
            if arch_n and arch_n != _norm(mapped_arch):
                continue

            profile = row_to_source_profile(row, row_idx=idx)
            record = SG.make_record(
                "SOURCE_PROFILE",
                profile,
                method="lectura directa de fila real de Nemotron-Personas-El-Salvador",
                assumptions=[
                    "la fila proviene del dataset sintético oficial nvidia/Nemotron-Personas-El-Salvador",
                    "CC BY 4.0 permite reutilización con atribución",
                    "no representa una persona real",
                ],
                agent_id=profile["uuid"],
                validation_status="source_verified",
            )
            skills_raw = row.get("skills_and_expertise_list")
            try:
                skills = json.loads(skills_raw) if isinstance(skills_raw, str) else (skills_raw or [])
            except Exception:
                skills = []
            profiles.append({
                "profile": profile,
                "mapped_archetype": mapped_arch,
                "context": {
                    "skills_and_expertise_list": skills,
                    "career_goals_and_ambitions": row.get("career_goals_and_ambitions"),
                    "persona": row.get("persona"),
                },
                "provenance": {
                    "dataset": SG.NEMOTRON,
                    "license": "CC BY 4.0",
                    "retrieval_mode": origin_mode,
                },
            })
            records.append(record)
            if len(profiles) >= limit:
                break

        return {
            "count": len(profiles),
            "agricultural_count": sum(
                1 for p in profiles if p["profile"]["agricultural_occupation"]
            ),
            "retrieval_mode": origin_mode,
            "corpus_metadata": corpus_meta,
            "profiles": profiles,
            "records": records,
        }

    def build_agents_from_rows(
        self,
        items: Iterable[dict[str, Any]],
        *,
        seed: int = 42,
        scenario_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Construye agentes agrícolas AGROSV anclados a filas reales de Nemotron."""
        from .population import ARCHETYPES, BOUNDS_BASIS, _uniform

        rng = np.random.default_rng(seed)
        agents: list[dict[str, Any]] = []

        for index, item in enumerate(items):
            if "profile" in item:
                profile = dict(item["profile"])
                context = item.get("context", {})
                row_idx = profile.get("nemotron_row_idx")
            else:
                row_idx, row = _extract_row_dict(item)
                profile = row_to_source_profile(row, row_idx=row_idx)
                context = {
                    "persona": row.get("persona"),
                    "career_goals_and_ambitions": row.get("career_goals_and_ambitions"),
                }

            archetype = map_occupation_to_archetype(
                profile.get("occupation"),
                area=profile.get("area"),
                education_level=profile.get("education_level"),
            )
            spec = ARCHETYPES[archetype]
            agent_id = f"AGSV-NEM-{archetype}-{index:06d}"

            area_ha = round(_uniform(rng, spec["area_ha"]), 3)
            irrigated = bool(rng.random() < float(np.mean(spec["irrigated"])))
            capital_usd = round(_uniform(rng, spec["capital_usd"]), 2)
            credit_access = round(_uniform(rng, spec["credit_access"]), 3)
            market_access = round(_uniform(rng, spec["market_access"]), 3)
            household_labor = int(
                rng.integers(spec["household_labor"][0], spec["household_labor"][1] + 1)
            )
            hired_labor = int(
                rng.integers(spec["hired_labor"][0], spec["hired_labor"][1] + 1)
            )
            tenure = str(rng.choice(spec["tenure"]))
            risk_aversion = round(_uniform(rng, spec["risk_aversion"]), 3)
            info_access = round(_uniform(rng, spec["info_access"]), 3)
            experience_years = int(
                rng.integers(spec["experience_years"][0], spec["experience_years"][1] + 1)
            )
            digital_literacy = round(_uniform(rng, spec["digital_literacy"]), 3)
            cooperative = bool(rng.random() < float(np.mean(spec["cooperative"])))
            off_farm_income = round(_uniform(rng, spec["off_farm_income"]), 3)

            department = profile.get("department") or "San Salvador"
            municipality = profile.get("municipality")
            area_type = profile.get("area") or spec["area_type"]

            source_record = SG.make_record(
                "SOURCE_PROFILE",
                profile,
                method="lectura directa de fila real de Nemotron-Personas-El-Salvador",
                assumptions=[
                    "la fila proviene de nvidia/Nemotron-Personas-El-Salvador (CC BY 4.0)",
                    "no representa a una persona real",
                ],
                agent_id=agent_id,
                scenario_id=scenario_id,
                validation_status="source_verified",
            )

            state = SG.make_record(
                "SYNTHETIC_AGRICULTURAL_STATE",
                {
                    "archetype": archetype,
                    "archetype_label": spec["label"],
                    "production_system": spec["production_system"],
                    "primary_crop": spec["primary_crop"],
                    "crops": list(spec["crops"]),
                    "area_ha": area_ha,
                    "irrigated": irrigated,
                    "capital_usd": capital_usd,
                    "credit_access": credit_access,
                    "market_access": market_access,
                    "household_labor": household_labor,
                    "hired_labor": hired_labor,
                    "tenure": tenure,
                    "risk_aversion": risk_aversion,
                    "info_access": info_access,
                    "experience_years": experience_years,
                    "digital_literacy": digital_literacy,
                    "cooperative": cooperative,
                    "off_farm_income": off_farm_income,
                    "department": department,
                    "municipality": municipality,
                    "area_type": area_type,
                    "nemotron_uuid": profile.get("uuid"),
                    "nemotron_row_idx": row_idx,
                    "parameter_basis": f"{BOUNDS_BASIS} + nemotron_source_anchor",
                },
                method=(
                    "dotación agrícola sintética de AGROSV anclada a ocupación, "
                    "departamento y municipio reales de Nemotron"
                ),
                assumptions=[
                    "el perfil demográfico y ocupación provienen de Nemotron-Personas-El-Salvador",
                    "las variables productivas (área, capital, riego, crédito) son rangos sintéticos de AGROSV porque Nemotron no las incluye",
                    "no sustituye al CAP 2025",
                ],
                scenario_id=scenario_id,
                agent_id=agent_id,
                parent_ids=[source_record["record_id"]],
            )

            agents.append({
                "agent_id": agent_id,
                "archetype": archetype,
                "seed": seed,
                "index": index,
                "nemotron_uuid": profile.get("uuid"),
                "source_profile": {
                    "profile": profile,
                    "record": source_record,
                    "context": context,
                    "provenance": {
                        "dataset": SG.NEMOTRON,
                        "license": "CC BY 4.0",
                    },
                },
                "state": state,
            })
        return agents


__all__ = [
    "AGRICULTURAL_KEYWORDS",
    "CORPUS_PATH",
    "DATASET_ID",
    "HF_ROWS_URL",
    "NemotronDatasetClient",
    "SAMPLE_PATH",
    "is_agricultural_occupation",
    "map_occupation_to_archetype",
    "row_to_source_profile",
]
