"""AGROSV — arquitectura de almacenamiento (Fase 4).

Extiende la estructura de Fase 3 **sin renombrar nada**: añade `staging/` (zona
de escritura temporal) y `validated/` (datos normalizados y aprobados por el
motor de calidad). `processed/` y `derived/` conservan su significado anterior.

Principios que este módulo hace ejecutables:

1. Lo crudo es inmutable y no se versiona; lo derivado es reproducible y sí.
2. Ningún binario grande entra en Git (límite por tamaño, verificado).
3. Un artefacto se promueve de `staging/` a `validated/` solo si su hash
   coincide con el registrado; si ya existe un archivo con el mismo hash en el
   destino, no se duplica.
4. Los nombres de archivo son ASCII, sin espacios y con la resolución y la
   versión declaradas, para que dos artefactos distintos nunca colisionen.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .. import config as C

ZONES = ("raw", "staging", "validated", "processed", "derived",
         "metadata", "manifests", "samples")

#: Política de versionado por zona. `max_bytes` es el umbral por archivo para
#: que Git sea una opción razonable; por encima, solo manifiesto y receta.
ZONE_POLICY: dict[str, dict[str, object]] = {
    "raw": {"git": False, "max_bytes": None,
            "reason": "descargas originales voluminosas y regenerables"},
    "staging": {"git": False, "max_bytes": None,
                "reason": "zona de escritura temporal; nunca es entregable"},
    "validated": {"git": True, "max_bytes": 25 * 1024 * 1024,
                  "reason": "datos normalizados que superaron el motor de calidad"},
    "processed": {"git": True, "max_bytes": 25 * 1024 * 1024,
                  "reason": "capas listas para API (Fase 1)"},
    "derived": {"git": True, "max_bytes": 10 * 1024 * 1024,
                "reason": "resultados de modelo pequeños y reproducibles"},
    "metadata": {"git": True, "max_bytes": 5 * 1024 * 1024,
                 "reason": "catálogo, correspondencias y contratos"},
    "manifests": {"git": True, "max_bytes": 5 * 1024 * 1024,
                  "reason": "trazabilidad: sin manifiesto no hay dato publicable"},
    "samples": {"git": True, "max_bytes": 5 * 1024 * 1024,
                "reason": "evidencia ligera; los rásteres quedan fuera de Git"},
}

_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class DataLayout:
    """Rutas de todas las zonas. Ninguna ruta se escribe a mano en otro módulo."""

    root: Path

    def zone(self, name: str) -> Path:
        if name not in ZONES:
            raise ValueError(f"zona desconocida: {name}; use {ZONES}")
        return self.root / name

    @property
    def raw(self) -> Path:
        return self.zone("raw")

    @property
    def staging(self) -> Path:
        return self.zone("staging")

    @property
    def validated(self) -> Path:
        return self.zone("validated")

    @property
    def processed(self) -> Path:
        return self.zone("processed")

    @property
    def derived(self) -> Path:
        return self.zone("derived")

    @property
    def metadata(self) -> Path:
        return self.zone("metadata")

    @property
    def manifests(self) -> Path:
        return self.zone("manifests")

    @property
    def samples(self) -> Path:
        return self.zone("samples")

    @property
    def objects(self) -> Path:
        """Almacén direccionado por contenido (deduplicación por sha256)."""
        return self.raw / "_objects"

    @property
    def catalog_path(self) -> Path:
        return self.metadata / "datasets.json"

    @property
    def store_path(self) -> Path:
        return self.validated / "agrosv_data.sqlite"

    @property
    def lineage_path(self) -> Path:
        return self.manifests / "lineage.json"

    @property
    def ingest_log(self) -> Path:
        return self.manifests / "ingest_log.jsonl"

    @property
    def quality_dir(self) -> Path:
        return self.metadata / "quality_reports"

    @property
    def raster_catalog(self) -> Path:
        return self.metadata / "raster_catalog.json"

    @property
    def territory_index(self) -> Path:
        return self.metadata / "territory_index.json"


def layout(root: Path | None = None) -> DataLayout:
    return DataLayout(root=Path(root) if root else C.DATA)


def ensure_layout(lay: DataLayout | None = None) -> list[Path]:
    """Crea las zonas ausentes. Solo añade directorios, no toca los existentes."""
    lay = lay or layout()
    created = []
    for name in ZONES:
        path = lay.zone(name)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)
    return created


# --- Nombres -----------------------------------------------------------------
def slug(text: str, *, field: str = "valor") -> str:
    """ASCII, minúsculas, sin espacios. Falla en lugar de «arreglar» en silencio."""
    if not text:
        raise ValueError(f"{field} vacío")
    norm = unicodedata.normalize("NFKD", str(text))
    norm = "".join(ch for ch in norm if not unicodedata.combining(ch))
    norm = norm.lower().replace("ñ", "n").replace(" ", "-")
    norm = re.sub(r"[^a-z0-9._-]+", "-", norm).strip("-")
    norm = re.sub(r"-{2,}", "-", norm)
    if not norm or not _SLUG.match(norm):
        raise ValueError(f"{field} no produce un slug válido: {text!r}")
    return norm


def encode_resolution(resolution: str) -> str:
    """`0.05 deg` -> `0p05deg`; `250 m` -> `250m`; `30 m` -> `30m`."""
    raw = resolution.strip().lower().replace(" ", "")
    raw = raw.replace("°", "deg").replace("º", "deg")
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(deg|m|km|arcsec|arc-sec)", raw)
    if not m:
        raise ValueError(
            f"resolución no codificable: {resolution!r}; formatos aceptados: "
            "'0.05 deg', '250 m', '1 km', '30 arcsec'"
        )
    number, unit = m.groups()
    number = number.rstrip("0").rstrip(".") if "." in number else number
    return f"{number.replace('.', 'p')}{unit.replace('arc-sec', 'arcsec')}"


def artifact_name(*, source_id: str, variable: str, resolution: str,
                  version: str, date: str, ext: str) -> str:
    """`{source}_{variable}_{res}_{fecha}_{version}.{ext}` (Fase 3, §3)."""
    ext = ext.lstrip(".").lower()
    if not re.fullmatch(r"[a-z0-9]+", ext):
        raise ValueError(f"extensión inválida: {ext!r}")
    date_part = date.strip()
    if not re.fullmatch(r"[0-9]{4}(-[0-9]{2}){0,2}(_[0-9]{4}(-[0-9]{2}){0,2})?", date_part):
        raise ValueError(f"fecha no ISO 8601: {date!r}")
    return (f"{slug(source_id, field='source_id')}_"
            f"{slug(variable, field='variable')}_"
            f"{encode_resolution(resolution)}_"
            f"{date_part}_"
            f"{slug(version, field='version')}.{ext}")


# --- Integridad --------------------------------------------------------------
def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def object_store_path(lay: DataLayout, digest: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("sha256 inválido")
    return lay.objects / digest[:2] / digest[2:4] / digest


def store_object(lay: DataLayout, source: Path) -> tuple[Path, str, bool]:
    """Guarda una copia direccionada por contenido. Devuelve (ruta, sha, nuevo).

    `nuevo=False` significa que el objeto ya existía: no se duplica el archivo,
    aunque el nombre original fuera distinto.
    """
    digest = sha256_file(source)
    target = object_store_path(lay, digest)
    if target.exists():
        return target, digest, False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target, digest, True


def git_tracking_decision(path: Path, lay: DataLayout | None = None) -> dict[str, object]:
    """¿Debe este archivo entrar en Git? Responde con motivo, no con un booleano."""
    lay = lay or layout()
    rel = Path(path).resolve()
    zone = None
    for name in ZONES:
        try:
            rel.relative_to(lay.zone(name).resolve())
            zone = name
            break
        except ValueError:
            continue
    if zone is None:
        return {"track": False, "zone": None,
                "reason": "fuera de las zonas de datos de AGROSV"}
    policy = ZONE_POLICY[zone]
    if not policy["git"]:
        return {"track": False, "zone": zone, "reason": str(policy["reason"])}
    size = Path(path).stat().st_size if Path(path).exists() else 0
    limit = policy["max_bytes"]
    if limit is not None and size > int(limit):
        return {"track": False, "zone": zone, "bytes": size, "limit": int(limit),
                "reason": f"excede el límite de {int(limit)} B para {zone}; "
                          "deje el archivo y versione solo su manifiesto"}
    return {"track": True, "zone": zone, "bytes": size,
            "reason": str(policy["reason"])}


def promote(lay: DataLayout, staged: Path, *, dataset_id: str,
            filename: str | None = None) -> dict[str, object]:
    """Promueve `staging/` -> `validated/` verificando hash y evitando duplicados."""
    if not staged.exists():
        raise FileNotFoundError(staged)
    digest = sha256_file(staged)
    target_dir = lay.validated / slug(dataset_id, field="dataset_id")
    target = target_dir / (filename or staged.name)
    if target.exists():
        if sha256_file(target) == digest:
            return {"promoted": False, "duplicate": True, "path": str(target),
                    "sha256": digest,
                    "reason": "idéntico al ya validado: no se duplica"}
        raise FileExistsError(
            f"{target} existe con otro contenido; incremente la versión en el "
            "nombre del artefacto en lugar de sobrescribir"
        )
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staged, target)
    return {"promoted": True, "duplicate": False, "path": str(target),
            "sha256": digest, "bytes": target.stat().st_size}


def zone_manifest(lay: DataLayout | None = None) -> dict[str, object]:
    lay = lay or layout()
    return {
        "root": str(lay.root),
        "zones": {name: {"path": str(lay.zone(name)),
                         "exists": lay.zone(name).exists(),
                         **ZONE_POLICY[name]} for name in ZONES},
        "note": ("raw y staging no se versionan; validated/processed/derived "
                 "solo bajo el umbral declarado por archivo"),
    }
