"""AGROSV — linaje y versionado de productos derivados (Fase 4, §11).

No duplica el motor de reproducibilidad de Fase 2: cada derivación se registra
con `agrosv.science.reproducibility.build_manifest`, que ya calcula un `run_id`
dependiente del contenido (entradas + parámetros + seed) y verifica hashes.
Este módulo añade lo que faltaba para responder «¿de dónde salió este mapa?»:

* un **grafo** de artefactos (nodo = sha256 de archivo; arista = derivación);
* la receta ordenada de pasos con herramienta, versión y parámetros;
* la consulta inversa: dado un producto, qué datasets y archivos lo produjeron;
* detección de ciclos y verificación de integridad de toda la cadena.

Regla: un derivado sin registro no es publicable. `assert_traceable` lo exige.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..science.reproducibility import (build_manifest, file_sha256,
                                       verify_manifest)
from .storage import sha256_file

DATABASE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


def is_database(path: Path | str) -> bool:
    return Path(path).suffix.lower() in DATABASE_SUFFIXES


def logical_database_digest(path: Path | str) -> str:
    """Hash del *contenido lógico* de una base SQLite.

    El archivo físico cambia con WAL, checkpoints y reorganización de páginas
    aunque el contenido sea idéntico. Para trazabilidad científica se hashea el
    esquema y las filas ordenadas, no los bytes del archivo. Un ráster o un CSV
    se siguen verificando byte a byte; esta excepción se declara en el registro
    con `digest: sqlite-logical`.
    """
    p = Path(path)
    h = hashlib.sha256()
    con = sqlite3.connect(p)
    try:
        tables = con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        for name, ddl in tables:
            h.update(name.encode("utf-8"))
            h.update((ddl or "").encode("utf-8"))
            rows = con.execute(f'SELECT * FROM "{name}"').fetchall()
            canonical = sorted(
                json.dumps(row, sort_keys=True, default=str, ensure_ascii=False)
                for row in rows)
            for row in canonical:
                h.update(row.encode("utf-8"))
    finally:
        con.close()
    return h.hexdigest()


def artifact_digest(path: Path | str) -> str:
    """Hash verificable de un artefacto (lógico para bases, físico si no)."""
    p = Path(path)
    return logical_database_digest(p) if is_database(p) else sha256_file(p)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LineageError(ValueError):
    pass


class UntraceableArtifact(LineageError):
    pass


@dataclass
class Step:
    name: str
    tool: str
    tool_version: str
    params: dict[str, Any] = field(default_factory=dict)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "tool": self.tool,
                "tool_version": self.tool_version, "params": self.params,
                "note": self.note}


@dataclass
class DerivationRecord:
    dataset_id: str
    name: str
    version: str
    steps: list[Step]
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]
    seed: int | None = None
    validation_state: str = "UNVALIDATED"
    manifest_path: str | None = None
    created_at: str = field(default_factory=utcnow)
    notes: str = ""
    run_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dataset_id": self.dataset_id,
            "name": self.name,
            "version": self.version,
            "seed": self.seed,
            "steps": [s.as_dict() for s in self.steps],
            "inputs": self.inputs,
            "outputs": self.outputs,
            "validation_state": self.validation_state,
            "manifest_path": self.manifest_path,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @property
    def output_hashes(self) -> list[str]:
        return [o["sha256"] for o in self.outputs if o.get("sha256")]

    @property
    def input_hashes(self) -> list[str]:
        return [i["sha256"] for i in self.inputs if i.get("sha256")]


def record_derivation(*, dataset_id: str, name: str, version: str,
                      steps: Iterable[Step | dict[str, Any]],
                      input_paths: Iterable[str | Path],
                      output_paths: Iterable[str | Path],
                      manifests_dir: Path | str,
                      seed: int | None = None,
                      params: dict[str, Any] | None = None,
                      validation_state: str = "UNVALIDATED",
                      notes: str = "") -> DerivationRecord:
    """Registra una derivación y escribe su manifiesto verificable."""
    step_objs = [s if isinstance(s, Step) else Step(**s) for s in steps]
    if not step_objs:
        raise LineageError("una derivación sin pasos no es reconstruible")
    input_paths = [Path(p) for p in input_paths]
    output_paths = [Path(p) for p in output_paths]
    if not output_paths:
        raise LineageError("una derivación sin salidas no registra nada")
    missing = [str(p) for p in [*input_paths, *output_paths] if not p.exists()]
    if missing:
        raise LineageError(f"archivos de linaje ausentes: {missing}")

    # Las bases SQLite se excluyen del manifiesto físico: su archivo cambia con
    # WAL/checkpoint aunque el contenido no. Se registran con hash lógico abajo.
    physical_outputs = [p for p in output_paths if not is_database(p)]
    manifest = build_manifest(
        name=name,
        inputs=input_paths,
        outputs=physical_outputs,
        params={"version": version, "steps": [s.as_dict() for s in step_objs],
                "database_outputs": [str(p) for p in output_paths
                                     if is_database(p)],
                **(params or {})},
        seed=seed,
        notes=notes,
    )
    manifests = Path(manifests_dir)
    path = manifests / "derivations" / f"{manifest.run_id}.json"
    manifest.write(path)

    record = DerivationRecord(
        dataset_id=dataset_id, name=name, version=version,
        steps=step_objs,
        inputs=[{"path": str(p), "sha256": file_sha256(p),
                 "digest": "sha256"} for p in input_paths],
        outputs=[{"path": str(p), "sha256": artifact_digest(p),
                  "digest": "sqlite-logical" if is_database(p) else "sha256",
                  "bytes": p.stat().st_size} for p in output_paths],
        seed=seed, validation_state=validation_state,
        manifest_path=str(path), notes=notes, run_id=manifest.run_id,
    )
    return record


class LineageGraph:
    """Grafo de derivaciones persistido en un JSON pequeño."""

    SCHEMA_VERSION = 4

    def __init__(self, path: Path | str,
                 records: list[DerivationRecord] | None = None) -> None:
        self.path = Path(path)
        self.records: list[DerivationRecord] = records or []

    @classmethod
    def load(cls, path: Path | str) -> "LineageGraph":
        p = Path(path)
        if not p.exists():
            return cls(p)
        payload = json.loads(p.read_text(encoding="utf-8"))
        records = []
        for raw in payload.get("derivations", []):
            records.append(DerivationRecord(
                run_id=raw.get("run_id"), dataset_id=raw["dataset_id"],
                name=raw["name"], version=raw["version"],
                steps=[Step(**s) for s in raw.get("steps", [])],
                inputs=raw.get("inputs", []), outputs=raw.get("outputs", []),
                seed=raw.get("seed"),
                validation_state=raw.get("validation_state", "UNVALIDATED"),
                manifest_path=raw.get("manifest_path"),
                created_at=raw.get("created_at", utcnow()),
                notes=raw.get("notes", ""),
            ))
        return cls(p, records)

    def save(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path else self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": utcnow(),
            "count": len(self.records),
            "derivations": [r.as_dict() for r in self.records],
            "note": ("nodo = sha256 de archivo; arista = derivación registrada "
                     "con pasos y parámetros"),
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    # --- grafo -------------------------------------------------------------
    def add(self, record: DerivationRecord) -> None:
        if record.run_id and any(r.run_id == record.run_id for r in self.records):
            return  # idempotente: misma receta, misma entrada
        known = {h for r in self.records for h in r.output_hashes}
        for h in record.input_hashes:
            # Un input puede ser un archivo crudo sin derivación previa: es raíz.
            if h not in known:
                continue
        self.records.append(record)
        self._assert_acyclic()

    def _edges(self) -> dict[str, list[str]]:
        edges: dict[str, list[str]] = {}
        for record in self.records:
            for out in record.output_hashes:
                # Una copia idéntica (mismo hash de entrada y salida) no es un
                # ciclo: es una derivación sin cambio de contenido.
                edges.setdefault(out, []).extend(
                    h for h in record.input_hashes if h != out)
        return edges

    def _assert_acyclic(self) -> None:
        graph = self._edges()
        state: dict[str, int] = {}

        def visit(node: str, trail: tuple[str, ...]) -> None:
            if state.get(node) == 2:
                return
            if state.get(node) == 1:
                raise LineageError(
                    "ciclo de linaje: " + " -> ".join(trail + (node,)))
            state[node] = 1
            for parent in graph.get(node, []):
                visit(parent, trail + (node,))
            state[node] = 2

        for node in graph:
            visit(node, ())

    def explain(self, artifact: str | Path) -> dict[str, Any]:
        """Cadena completa de un producto: derivaciones, entradas y pasos."""
        p = Path(artifact)
        digest = artifact_digest(p) if p.exists() else str(artifact)
        chain = [r for r in self.records if digest in r.output_hashes]
        if not chain:
            raise UntraceableArtifact(
                f"{artifact} no tiene derivación registrada: no es publicable "
                "hasta registrar su linaje")
        all_inputs: list[dict[str, Any]] = []
        visited: set[str] = set()
        stack = list(chain)
        while stack:
            record = stack.pop()
            for inp in record.inputs:
                if inp["sha256"] in visited:
                    continue
                visited.add(inp["sha256"])
                all_inputs.append(inp)
                stack.extend(r for r in self.records
                             if inp["sha256"] in r.output_hashes)
        return {
            "artifact": str(artifact),
            "sha256": digest,
            "derivations": [r.as_dict() for r in chain],
            "root_inputs": all_inputs,
            "reconstructable": all(r.manifest_path for r in chain),
            "note": ("el linaje se reconstruye desde los manifiestos de "
                     "ejecución; no se dedujo de fechas"),
        }

    def datasets_for(self, artifact: str | Path) -> list[str]:
        try:
            return sorted({d["dataset_id"] for d in self.explain(artifact)["derivations"]})
        except UntraceableArtifact:
            return []

    def verify(self) -> dict[str, Any]:
        """Verifica hashes de entradas/salidas y `run_id` de cada manifiesto."""
        results = []
        for record in self.records:
            problems: list[str] = []
            for group in ("inputs", "outputs"):
                for item in getattr(record, group):
                    path = Path(item["path"])
                    if not path.exists():
                        problems.append(f"{group}: falta {path}")
                    elif item.get("sha256") and (artifact_digest(path)
                                                  != item["sha256"]):
                        problems.append(f"{group}: hash distinto en {path}")
            if record.manifest_path and Path(record.manifest_path).exists():
                check = verify_manifest(Path(record.manifest_path))
                problems.extend(check["problems"])
            results.append({"run_id": record.run_id, "ok": not problems,
                            "problems": problems})
        return {"checked": len(results),
                "verified": sum(1 for r in results if r["ok"]),
                "ok": all(r["ok"] for r in results),
                "results": results}

    def assert_traceable(self, artifact: str | Path) -> dict[str, Any]:
        info = self.explain(artifact)
        if not info["reconstructable"]:
            raise UntraceableArtifact(
                "hay derivaciones sin manifiesto: no se puede reconstruir")
        return info

    def summary(self) -> dict[str, Any]:
        nodes = {h for r in self.records for h in r.output_hashes}
        roots = {h for r in self.records for h in r.input_hashes} - nodes
        return {
            "derivations": len(self.records),
            "outputs": len(nodes),
            "root_inputs": len(roots),
            "datasets": sorted({r.dataset_id for r in self.records}),
            "unvalidated": sum(1 for r in self.records
                               if r.validation_state != "VALIDATED"),
        }
