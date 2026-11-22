"""Correspondencia municipal 2023 (Decreto 762) — consulta y agregación.

El CSV se deriva de la distribución oficial publicada por la Asamblea
Legislativa. Los identificadores `SV-MUN-*` y `SV-DIS-*` son de AGROSV, **no**
códigos oficiales. La fuente no publica códigos, así que no se inventan.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from .. import config as C
from . import validators

CROSSWALK_PATH = C.DATA / "reference" / "municipality_crosswalk_2023.csv"
PROVENANCE_PATH = (C.DATA / "reference" /
                   "municipality_crosswalk_2023.provenance.json")


class CrosswalkError(RuntimeError):
    pass


def normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text).lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


@lru_cache(maxsize=2)
def _load(path_str: str) -> tuple[dict[str, str], ...]:
    path = Path(path_str)
    if not path.exists():
        raise CrosswalkError(
            f"no existe {path}; ejecute "
            "scripts/12_build_municipality_crosswalk.py")
    report = validators.validate_crosswalk(path)
    if not report["valid"]:
        raise CrosswalkError(f"correspondencia inválida: {report['errors']}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        import csv

        return tuple(dict(row) for row in csv.DictReader(handle))


def load_crosswalk(path: str | Path | None = None) -> list[dict[str, str]]:
    return [dict(row) for row in _load(str(path or CROSSWALK_PATH))]


def provenance() -> dict[str, Any]:
    if not PROVENANCE_PATH.exists():
        raise CrosswalkError(f"no existe {PROVENANCE_PATH}")
    return json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))


def summary() -> dict[str, Any]:
    rows = load_crosswalk()
    departments: dict[str, int] = {}
    municipalities: dict[str, int] = {}
    for row in rows:
        departments[row["department"]] = departments.get(
            row["department"], 0) + 1
        municipalities[row["municipality"]] = municipalities.get(
            row["municipality"], 0) + 1
    meta = provenance() if PROVENANCE_PATH.exists() else {}
    return {
        "dataset_id": "municipality_crosswalk_2023",
        "counts": {"departments": len(departments),
                   "municipalities": len(municipalities),
                   "districts": len(rows)},
        "departments": dict(sorted(departments.items())),
        "municipalities": dict(sorted(municipalities.items())),
        "effective_date": meta.get("effective_date"),
        "legal_instrument": meta.get("legal_instrument"),
        "source": meta.get("source"),
        "validation_status": meta.get("validation_status"),
        "ids_are_official": False,
        "note": ("los distritos son los 262 municipios históricos; los "
                 "municipios son los 44 vigentes desde 2024-05-01"),
    }


def lookup_district(name: str, department: str | None = None
                    ) -> list[dict[str, str]]:
    needle = normalize(name)
    dept = normalize(department) if department else None
    return [row for row in load_crosswalk()
            if normalize(row["district"]) == needle
            and (dept is None or normalize(row["department"]) == dept)]


def municipality_of(district: str, department: str | None = None
                    ) -> dict[str, Any]:
    matches = lookup_district(district, department)
    if not matches:
        return {"found": False, "district": district,
                "reason": "distrito no encontrado"}
    if len(matches) > 1:
        return {"found": False, "district": district,
                "ambiguous": True,
                "candidates": [{"department": m["department"],
                                "municipality": m["municipality"]}
                               for m in matches],
                "reason": "nombre repetido en varios departamentos; indique "
                          "department"}
    row = matches[0]
    return {"found": True, "district": row["district"],
            "department": row["department"],
            "municipality": row["municipality"],
            "municipality_id": row["municipality_id"],
            "district_id": row["district_id"],
            "source": row["source"]}


def districts_of(municipality: str, department: str | None = None
                 ) -> dict[str, Any]:
    needle = normalize(municipality)
    dept = normalize(department) if department else None
    rows = [row for row in load_crosswalk()
            if normalize(row["municipality"]) == needle
            and (dept is None or normalize(row["department"]) == dept)]
    if not rows:
        return {"found": False, "municipality": municipality,
                "reason": "municipio no encontrado"}
    return {"found": True, "municipality": rows[0]["municipality"],
            "department": rows[0]["department"],
            "districts": [{"district": r["district"],
                           "district_id": r["district_id"]} for r in rows]}


def aggregate_rows(rows: list[dict[str, Any]], *,
                   district_key: str = "district",
                   department_key: str = "department"
                   ) -> dict[str, Any]:
    """Agrega filas con nombre de distrito a los 44 municipios vigentes.

    Un nombre de distrito repetido (p. ej. El Rosario) exige `department` en
    la fila; si no, la fila queda en `unmapped` con la razón, no se elige una
    arbitrariamente.
    """
    mapping: dict[str, list[dict[str, str]]] = {}
    for item in load_crosswalk():
        mapping.setdefault(normalize(item["district"]), []).append(item)
    out: dict[str, list[dict[str, Any]]] = {}
    unmapped: list[dict[str, Any]] = []
    for row in rows:
        name = row.get(district_key)
        if not name:
            unmapped.append({"row": row, "reason": "sin nombre de distrito"})
            continue
        candidates = mapping.get(normalize(str(name)), [])
        if not candidates:
            unmapped.append({"district": str(name),
                             "reason": "distrito no encontrado"})
            continue
        if len(candidates) > 1:
            department = row.get(department_key)
            filtered = [c for c in candidates
                        if department and normalize(c["department"])
                        == normalize(str(department))]
            if not filtered:
                unmapped.append({
                    "district": str(name),
                    "reason": "nombre ambiguo; indique department",
                    "candidates": [c["department"] for c in candidates],
                })
                continue
            candidates = filtered
        target = candidates[0]
        out.setdefault(target["municipality"], []).append(row)
    return {"municipalities": out, "unmapped": unmapped,
            "rule": ("agregación por nombre de distrito; los nombres "
                     "repetidos requieren department")}


__all__ = ["CROSSWALK_PATH", "PROVENANCE_PATH", "CrosswalkError", "normalize",
           "load_crosswalk", "provenance", "summary", "lookup_district",
           "municipality_of", "districts_of", "aggregate_rows"]
