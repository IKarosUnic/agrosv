"""Reproducibilidad: manifiestos de ejecución verificables por hash.

Un resultado de AGROSV es reproducible si otra persona puede reconstruirlo con
los mismos datos, versiones y parámetros y obtener el mismo hash de salida.
Este módulo registra ese conjunto y permite verificarlo después.

`run_id` es un hash del contenido de entradas + parámetros + seed, no un
timestamp. Dos ejecuciones idénticas comparten `run_id`; un cambio de parámetro
o de archivo de entrada lo cambia. Eso es lo que permite afirmar «misma
corrida» sin comparar fechas.
"""
from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..provenance import software_versions


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode("utf-8")


def environment_fingerprint() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "software": software_versions(),
    }


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return dict(self.payload)

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.payload, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        return path


def build_manifest(
    *,
    name: str,
    inputs: Iterable[str | Path],
    params: dict[str, Any],
    seed: int | None,
    outputs: Iterable[str | Path] = (),
    notes: str = "",
) -> RunManifest:
    """Construye un manifiesto; exige seed si hay cualquier componente aleatorio."""
    input_records = []
    for item in inputs:
        p = Path(item)
        input_records.append({
            "path": str(p),
            "sha256": file_sha256(p) if p.exists() else None,
            "exists": p.exists(),
        })
    output_records = []
    for item in outputs:
        p = Path(item)
        output_records.append({
            "path": str(p),
            "sha256": file_sha256(p) if p.exists() else None,
            "exists": p.exists(),
        })

    identity = {"name": name, "params": params, "seed": seed,
                "inputs": [(r["path"], r["sha256"]) for r in input_records]}
    run_id = hashlib.sha256(_canonical(identity)).hexdigest()[:16]

    payload = {
        "run_id": run_id,
        "name": name,
        "created_at": utcnow(),
        "seed": seed,
        "params": params,
        "identity_note": (
            "run_id = sha256(nombre, parámetros, seed, hashes de entrada); "
            "no depende de la fecha de ejecución"
        ),
        "inputs": input_records,
        "outputs": output_records,
        "environment": environment_fingerprint(),
        "notes": notes,
    }
    return RunManifest(run_id=run_id, payload=payload)


def verify_manifest(path: Path) -> dict[str, Any]:
    """Recalcula los hashes de entradas y salidas y comprueba el `run_id`."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    problems: list[str] = []

    for group in ("inputs", "outputs"):
        for record in payload.get(group, []):
            p = Path(record["path"])
            if not p.exists():
                problems.append(f"{group}: falta {p}")
                continue
            if record.get("sha256") and file_sha256(p) != record["sha256"]:
                problems.append(f"{group}: hash distinto en {p}")

    identity = {
        "name": payload.get("name"),
        "params": payload.get("params"),
        "seed": payload.get("seed"),
        "inputs": [(r["path"], r["sha256"]) for r in payload.get("inputs", [])],
    }
    recomputed = hashlib.sha256(_canonical(identity)).hexdigest()[:16]
    if recomputed != payload.get("run_id"):
        problems.append(
            f"run_id no corresponde al contenido: {payload.get('run_id')} != {recomputed}"
        )
    return {"run_id": payload.get("run_id"), "reproducible": not problems,
            "problems": problems}
