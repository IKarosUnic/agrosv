"""Dataset versioning y procedencia, derivados de los manifiestos existentes.

No duplica información: la fuente de verdad son los sidecar
`<artefacto>.provenance.json` que escriben los scripts de Fase 1
(`agrosv.provenance.write_manifest`). Este módulo los indexa, les asigna un
identificador de versión estable por contenido y verifica que el hash siga
correspondiendo al archivo.

`dataset_version` = `<capa>@<sha256[:12]>`; el identificador depende del
contenido, no de la fecha, de modo que reproducir una capa con los mismos
insumos produce la misma versión.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .. import config as C

MANIFEST_SUFFIX = ".provenance.json"


def _sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class DatasetVersion:
    dataset_version: str
    layer: str
    artifact: Path
    provenance_id: str
    license: str
    source_id: str
    source_url: str | None
    native_resolution: str
    effective_resolution: str
    generated_at: str
    sha256: str
    manifest: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "layer": self.layer,
            "artifact": str(self.artifact.relative_to(C.ROOT)),
            "provenance_id": self.provenance_id,
            "license": self.license,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "native_resolution": self.native_resolution,
            "effective_resolution": self.effective_resolution,
            "generated_at": self.generated_at,
            "sha256": self.sha256,
        }


def _manifests(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    yield from sorted(root.rglob(f"*{MANIFEST_SUFFIX}"))


def catalog(root: Path | None = None) -> list[DatasetVersion]:
    """Indexa todos los manifiestos bajo `data/processed` (o `root`)."""
    root = root or C.PROCESSED
    out: list[DatasetVersion] = []
    for manifest_path in _manifests(root):
        artifact = Path(str(manifest_path)[: -len(MANIFEST_SUFFIX)])
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sha = str(manifest.get("artifact_sha256", ""))
        if not sha:
            # Un manifiesto sin hash no permite versionar: se omite en lugar de
            # inventar una versión que no se puede verificar.
            continue
        layer = str(manifest.get("layer", artifact.stem))
        out.append(
            DatasetVersion(
                dataset_version=f"{layer}@{sha[:12]}",
                layer=layer,
                artifact=artifact,
                provenance_id=str(manifest.get("provenance_id", "")),
                license=str(manifest.get("license", "")),
                source_id=str(manifest.get("source_id", "")),
                source_url=manifest.get("source_url"),
                native_resolution=str(manifest.get("native_resolution", "")),
                effective_resolution=str(manifest.get("effective_resolution", "")),
                generated_at=str(manifest.get("generated_at", "")),
                sha256=sha,
                manifest=manifest,
            )
        )
    return out


def find(provenance_id: str, root: Path | None = None) -> DatasetVersion | None:
    for ds in catalog(root):
        if ds.provenance_id == provenance_id or ds.dataset_version == provenance_id:
            return ds
    return None


def verify(dataset: DatasetVersion) -> dict[str, Any]:
    """Recalcula el hash del artefacto y decide si la versión es válida."""
    if not dataset.artifact.exists():
        return {"dataset_version": dataset.dataset_version,
                "artifact_present": False, "hash_matches": False,
                "detail": "artefacto ausente"}
    actual = _sha256(dataset.artifact)
    return {
        "dataset_version": dataset.dataset_version,
        "artifact_present": True,
        "hash_matches": actual == dataset.sha256,
        "actual_sha256": actual,
    }


def verify_all(root: Path | None = None) -> dict[str, Any]:
    results = [verify(ds) for ds in catalog(root)]
    ok = [r for r in results if r.get("hash_matches")]
    return {
        "checked": len(results),
        "verified": len(ok),
        "failed": [r for r in results if not r.get("hash_matches")],
        "all_verified": bool(results) and len(ok) == len(results),
    }


def ledger(root: Path | None = None, out: Path | None = None) -> dict[str, Any]:
    """Libro de versiones: una entrada por dataset, ordenado por capa."""
    entries = [ds.as_dict() for ds in catalog(root)]
    payload = {
        "generated_by": "agrosv.science.registry",
        "note": (
            "Identificadores derivados del hash del artefacto, no de la fecha. "
            "Un cambio de contenido cambia la versión; un cambio de fecha no."
        ),
        "count": len(entries),
        "datasets": entries,
    }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                       encoding="utf-8")
    return payload


def licenses(root: Path | None = None) -> dict[str, list[str]]:
    """Agrupa capas por licencia para que la API no publique lo que no puede."""
    out: dict[str, list[str]] = {}
    for ds in catalog(root):
        out.setdefault(ds.license or "sin declarar", []).append(ds.layer)
    return {k: sorted(v) for k, v in sorted(out.items())}
