"""AGROSV — caché de resultados derivados (Fase 5, §9).

El caché es **direccionado por contenido de entrada**, no por hora:

    clave = sha256(motor + versión + parámetros + huella de cada artefacto fuente)

La huella de un artefacto es su ruta, tamaño y mtime. Si un ráster se regenera,
la clave cambia y el resultado viejo no se reutiliza: no hay caché obsoleto
silencioso. Se guarda en `data/derived/cache/`, fuera de Git, y se puede
deshabilitar con `use_cache=False`.

No se cachea nada que contenga datos personales ni resultados de una consulta
con `fresh=true`.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .. import config as C


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class CacheInfo:
    key: str
    hit: bool
    path: str
    created_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"key": self.key, "hit": self.hit, "path": self.path,
                "created_at": self.created_at}


def artifact_fingerprint(paths: Iterable[Path | str]) -> list[dict[str, Any]]:
    """Ruta relativa, tamaño y mtime de cada artefacto; ausente se declara."""
    out = []
    for p in paths:
        path = Path(p)
        try:
            rel = str(path.relative_to(C.ROOT))
        except ValueError:
            rel = str(path)
        if path.exists():
            stat = path.stat()
            out.append({"path": rel, "bytes": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns})
        else:
            out.append({"path": rel, "missing": True})
    return sorted(out, key=lambda d: d["path"])


class DerivedCache:
    def __init__(self, directory: Path | str | None = None) -> None:
        self.directory = Path(directory) if directory else C.DATA / "derived" / "cache"

    @staticmethod
    def make_key(engine: str, version: str, params: dict[str, Any],
                 fingerprints: list[dict[str, Any]]) -> str:
        payload = json.dumps({"engine": engine, "version": version,
                              "params": params, "inputs": fingerprints},
                             sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    def get_or_compute(
        self,
        *,
        engine: str,
        version: str,
        params: dict[str, Any],
        paths: Iterable[Path | str],
        build: Callable[[], dict[str, Any]],
        use_cache: bool = True,
    ) -> tuple[dict[str, Any], CacheInfo]:
        key = self.make_key(engine, version, params, artifact_fingerprint(paths))
        path = self.directory / f"{engine}.{key}.json"
        if use_cache and path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                info = CacheInfo(key=key, hit=True, path=str(path),
                                 created_at=payload.get("_cache", {}).get("created_at"))
                payload.pop("_cache", None)
                return payload, info
            except (OSError, json.JSONDecodeError):
                # Un caché corrupto no se sirve: se recalcula y se sobrescribe.
                pass
        payload = build()
        if use_cache:
            try:
                self.directory.mkdir(parents=True, exist_ok=True)
                stored = dict(payload)
                stored["_cache"] = {"key": key, "created_at": _utcnow()}
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(stored, indent=2, ensure_ascii=False),
                               encoding="utf-8")
                os.replace(tmp, path)
            except OSError:
                # Sin permiso de escritura el motor sigue funcionando: el caché
                # es una optimización, no un requisito científico.
                pass
        return payload, CacheInfo(key=key, hit=False, path=str(path))

    def stats(self) -> dict[str, Any]:
        if not self.directory.exists():
            return {"exists": False, "path": str(self.directory), "entries": 0}
        files = sorted(self.directory.glob("*.json"))
        return {"exists": True, "path": str(self.directory),
                "entries": len(files),
                "bytes": sum(f.stat().st_size for f in files),
                "note": ("clave = motor + versión + parámetros + huella de "
                         "artefactos; un cambio de fuente invalida el caché")}
