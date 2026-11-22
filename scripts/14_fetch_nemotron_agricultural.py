"""AGROSV — Descarga de corpus agrícola real desde nvidia/Nemotron-Personas-El-Salvador.

Escanea lotes distribuidos a lo largo de las 148.000 filas mediante
Hugging Face Datasets Server (sin requerir pyarrow/datasets) y guarda las filas
con ocupación agrícola/pecuaria/forestal en:
    data/samples/phase3/nemotron_rows/nemotron_agricultural_corpus.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.social.nemotron import (  # noqa: E402
    CORPUS_PATH,
    DATASET_ID,
    NemotronDatasetClient,
    is_agricultural_occupation,
    map_occupation_to_archetype,
)

TOTAL_ROWS = 148_000
BATCH_LENGTH = 100
DEFAULT_OFFSETS = [i * 3200 for i in range(45)]


def fetch_corpus(
    offsets: list[int] | None = None,
    *,
    length: int = BATCH_LENGTH,
    output_path: Path = CORPUS_PATH,
) -> dict:
    client = NemotronDatasetClient(output_path)
    scan_offsets = offsets or DEFAULT_OFFSETS
    seen_uuids: set[str] = set()
    collected: list[dict] = []
    dept_counts: dict[str, int] = {}
    arch_counts: dict[str, int] = {}
    scanned = 0

    for offset in scan_offsets:
        try:
            batch = client.fetch_live_rows(
                offset=offset, length=length, agricultural_only=False, timeout=30, retries=4
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] offset {offset} omitido: {exc}", file=sys.stderr)
            continue
        scanned += length
        time.sleep(0.5)
        for item in batch["rows"]:
            row = item["row"]
            occ = row.get("occupation")
            if not is_agricultural_occupation(occ):
                continue
            uid = str(row.get("uuid") or f"idx-{item.get('row_idx')}")
            if uid in seen_uuids:
                continue
            seen_uuids.add(uid)
            collected.append(item)
            dept = str(row.get("department") or "Desconocido")
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
            arch = map_occupation_to_archetype(
                occ, area=row.get("area"), education_level=row.get("education_level")
            )
            arch_counts[arch] = arch_counts.get(arch, 0) + 1

    payload = {
        "metadata": {
            "dataset_id": DATASET_ID,
            "license": "CC BY 4.0",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "rows_scanned": scanned,
            "agricultural_rows_collected": len(collected),
            "departments_covered": len(dept_counts),
            "department_counts": dict(sorted(dept_counts.items())),
            "mapped_archetype_counts": dict(sorted(arch_counts.items())),
            "offsets_scanned": scan_offsets,
            "note": (
                "Subconjunto real de filas agrícolas de "
                "nvidia/Nemotron-Personas-El-Salvador (personas sintéticas; "
                "no sustituye censos ni microdatos observados)."
            ),
        },
        "rows": collected,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    output_path.write_bytes(raw_bytes)
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    meta_path = output_path.with_suffix(".provenance.json")
    meta_path.write_text(
        json.dumps(
            {
                "file": str(output_path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256,
                "bytes": len(raw_bytes),
                **payload["metadata"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "output": str(output_path),
        "rows_scanned": scanned,
        "agricultural_rows": len(collected),
        "departments": len(dept_counts),
        "sha256": sha256,
    }


def clean_local_corpus(output_path: Path = CORPUS_PATH) -> dict:
    """Refiltra el corpus local existente usando is_agricultural_occupation."""
    raw = json.loads(output_path.read_text(encoding="utf-8"))
    collected: list[dict] = []
    dept_counts: dict[str, int] = {}
    arch_counts: dict[str, int] = {}
    seen_uuids: set[str] = set()
    for item in raw.get("rows", []):
        row = item.get("row", item)
        occ = row.get("occupation")
        if not is_agricultural_occupation(occ):
            continue
        uid = str(row.get("uuid") or f"idx-{item.get('row_idx')}")
        if uid in seen_uuids:
            continue
        seen_uuids.add(uid)
        collected.append(item)
        dept = str(row.get("department") or "Desconocido")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
        arch = map_occupation_to_archetype(
            occ, area=row.get("area"), education_level=row.get("education_level")
        )
        arch_counts[arch] = arch_counts.get(arch, 0) + 1

    meta = dict(raw.get("metadata", {}))
    meta.update({
        "agricultural_rows_collected": len(collected),
        "departments_covered": len(dept_counts),
        "department_counts": dict(sorted(dept_counts.items())),
        "mapped_archetype_counts": dict(sorted(arch_counts.items())),
    })
    payload = {"metadata": meta, "rows": collected}
    raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    output_path.write_bytes(raw_bytes)
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    meta_path = output_path.with_suffix(".provenance.json")
    meta_path.write_text(
        json.dumps(
            {
                "file": str(output_path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256,
                "bytes": len(raw_bytes),
                **meta,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "output": str(output_path),
        "agricultural_rows": len(collected),
        "departments": len(dept_counts),
        "archetypes": arch_counts,
        "sha256": sha256,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-local", action="store_true")
    args = parser.parse_args()
    summary = clean_local_corpus() if args.clean_local else fetch_corpus()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
