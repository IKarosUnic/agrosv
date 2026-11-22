"""AGROSV — motor de ingesta reproducible (Fase 4, §4).

Qué hace y qué no:

* Descarga **solo de fuentes autorizadas**: hay una lista explícita de hosts. No
  hay rastreo ni scraping de portales que no lo permitan.
* No descarga dos veces el mismo contenido: compara ETag/Content-Length del
  registro de descargas y, para archivos locales, el hash del almacén
  direccionado por contenido.
* Verifica integridad (hash, tamaño, cabecera de formato) antes de aceptar un
  archivo, y guarda el original inmutable en `data/raw/_objects/<sha>`.
* Procesa por lotes con estado en disco: un lote interrumpido se reanuda sin
  repetir lo ya ingestado.
* Los rásteres se inspeccionan por cabecera (`rasterio.open`), nunca cargando el
  archivo completo; los CSV se cuentan por streaming.

Formatos soportados: GeoJSON, Shapefile, GeoPackage, GeoTIFF/COG, CSV, Parquet,
NetCDF, Zarr, JSON. Donde falta una dependencia (pyarrow, xarray) se registra la
limitación en el manifiesto en lugar de fingir que se extrajo metadata.
"""
from __future__ import annotations

import json
import os
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import urlparse

from . import storage as S


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class IngestError(ValueError):
    pass


class HostNotAllowed(IngestError):
    pass


class IntegrityError(IngestError):
    pass


class Format(str, Enum):
    GEOJSON = "geojson"
    SHAPEFILE = "shapefile"
    GEOPACKAGE = "geopackage"
    GEOTIFF = "geotiff"
    COG = "cog"
    CSV = "csv"
    PARQUET = "parquet"
    NETCDF = "netcdf"
    ZARR = "zarr"
    JSON = "json"
    UNKNOWN = "unknown"


class IngestStatus(str, Enum):
    INGESTED = "INGESTED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


_EXT_MAP = {
    ".geojson": Format.GEOJSON, ".json": Format.JSON,
    ".shp": Format.SHAPEFILE, ".zip": Format.SHAPEFILE,
    ".gpkg": Format.GEOPACKAGE,
    ".tif": Format.GEOTIFF, ".tiff": Format.GEOTIFF,
    ".csv": Format.CSV, ".tsv": Format.CSV,
    ".parquet": Format.PARQUET, ".pq": Format.PARQUET,
    ".nc": Format.NETCDF, ".nc4": Format.NETCDF, ".cdf": Format.NETCDF,
    ".zarr": Format.ZARR,
}


@dataclass
class FormatDetection:
    format: Format
    evidence: str
    matches_extension: bool

    def as_dict(self) -> dict[str, Any]:
        return {"format": self.format.value, "evidence": self.evidence,
                "matches_extension": self.matches_extension}


def detect_format(path: Path | str) -> FormatDetection:
    p = Path(path)
    if p.is_dir():
        if (p / ".zgroup").exists() or (p / ".zattrs").exists() or any(
                c.suffix in {".zarray", ".zgroup"} for c in p.glob("*")):
            return FormatDetection(Format.ZARR, "directorio con metadatos Zarr", True)
        raise IngestError(f"directorio no reconocido como Zarr: {p}")
    ext_format = _EXT_MAP.get(p.suffix.lower())
    with open(p, "rb") as fh:
        head = fh.read(8)
    fmt, evidence = Format.UNKNOWN, "sin firma reconocida"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        fmt, evidence = Format.GEOTIFF, "firma TIFF en cabecera"
    elif head[:4] == b"PAR1":
        fmt, evidence = Format.PARQUET, "firma PAR1"
    elif head[:3] in (b"CDF",) or head == b"\x89HDF\r\n\x1a\n":
        fmt, evidence = Format.NETCDF, "firma NetCDF/HDF5"
    elif head[:16].startswith(b"SQLite format 3"):
        fmt, evidence = Format.GEOPACKAGE, "contenedor SQLite (GeoPackage)"
    elif head[:4] == b"\x00\x00\x27\x0a":
        fmt, evidence = Format.SHAPEFILE, "firma Shapefile (9994 big-endian)"
    elif head[:1] in (b"{", b"["):
        text = p.read_text(encoding="utf-8", errors="replace")[:4000]
        stripped = text.lstrip()
        if '"FeatureCollection"' in stripped or '"Feature"' in stripped:
            fmt, evidence = Format.GEOJSON, "JSON con objeto Feature/FC"
        else:
            fmt, evidence = Format.JSON, "JSON sin estructura geoespacial"
    elif head[:1] not in (b"",):
        try:
            sample = p.read_text(encoding="utf-8", errors="strict")[:4000]
            first = sample.splitlines()[0] if sample.splitlines() else ""
            if "," in first or ";" in first or "\t" in first:
                fmt, evidence = Format.CSV, "texto delimitado con cabecera"
        except UnicodeDecodeError:
            fmt = Format.UNKNOWN
    # JSON y GeoJSON comparten extensión `.json` con frecuencia: el contenido
    # (Feature/FeatureCollection) manda, y no es una incoherencia.
    json_family = {Format.JSON, Format.GEOJSON}
    matches = (ext_format is None or ext_format == fmt
               or (ext_format in json_family and fmt in json_family))
    if fmt is Format.UNKNOWN and ext_format is not None:
        fmt, evidence = ext_format, "solo por extensión (no verificable)"
        matches = False
    return FormatDetection(fmt, evidence, matches)


@dataclass
class IntegrityCheck:
    checks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c["passed"] for c in self.checks if c["severity"] == "error")

    def add(self, name: str, passed: bool, detail: str = "",
            severity: str = "error") -> None:
        self.checks.append({"check": name, "passed": bool(passed),
                            "detail": detail, "severity": severity})

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "checks": self.checks}


def _extract_metadata(path: Path, fmt: Format) -> dict[str, Any]:
    """Extrae solo metadatos (cabeceras). Nunca carga un ráster nacional."""
    meta: dict[str, Any] = {"format": fmt.value, "bytes": path.stat().st_size}
    notes: list[str] = []
    try:
        if fmt in {Format.GEOTIFF, Format.COG}:
            from .raster import profile_raster

            meta["raster"] = profile_raster(path).as_dict()
        elif fmt in {Format.GEOPACKAGE, Format.SHAPEFILE}:
            import pyogrio

            layers = pyogrio.list_layers(path)
            meta["layers"] = [str(name) for name in layers[:, 0]]
            infos = {}
            for layer in meta["layers"]:
                info = pyogrio.read_info(path, layer=layer)
                infos[layer] = {
                    "features": int(info.get("features", 0)),
                    "crs": str(info.get("crs")) if info.get("crs") else None,
                    "geometry_type": info.get("geometry_type"),
                    "fields": list(info.get("fields", [])),
                    "total_bounds": [float(v) for v in info.get("total_bounds", [])],
                }
            meta["vector"] = infos
        elif fmt is Format.GEOJSON:
            payload = json.loads(path.read_text(encoding="utf-8"))
            features = payload.get("features", [])
            meta["geojson"] = {
                "type": payload.get("type"),
                "features": len(features),
                "crs": (payload.get("crs") or {}).get("properties", {}).get("name"),
                "property_keys": sorted({k for f in features[:50]
                                         for k in (f.get("properties") or {})}),
            }
            if not meta["geojson"]["crs"]:
                notes.append("GeoJSON sin CRS declarado: RFC 7946 asume EPSG:4326, "
                             "pero se debe verificar contra la fuente")
        elif fmt is Format.JSON:
            payload = json.loads(path.read_text(encoding="utf-8"))
            meta["json"] = {
                "type": type(payload).__name__,
                "keys": sorted(payload)[:40] if isinstance(payload, dict) else None,
                "records": len(payload) if isinstance(payload, list) else None,
            }
        elif fmt is Format.CSV:
            delimiter = ","
            with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
                first = fh.readline()
                delimiter = "\t" if first.count("\t") > first.count(",") else (
                    ";" if first.count(";") > first.count(",") else ",")
                rows = 0
                for _ in fh:
                    rows += 1
            meta["tabular"] = {
                "delimiter": delimiter,
                "header": [h.strip() for h in first.rstrip("\n").split(delimiter)],
                "rows": rows,
            }
        elif fmt is Format.PARQUET:
            try:
                import pyarrow.parquet as pq  # type: ignore

                schema = pq.read_schema(path)
                meta["parquet"] = {"columns": schema.names,
                                   "schema": str(schema)}
            except ImportError:
                notes.append("pyarrow no instalado: no se extrajo el esquema "
                             "Parquet (limitación de entorno, no del archivo)")
        elif fmt is Format.NETCDF:
            try:
                import xarray as xr  # type: ignore

                with xr.open_dataset(path) as ds:
                    meta["netcdf"] = {"dims": dict(ds.sizes),
                                      "variables": list(ds.data_vars),
                                      "crs": str(ds.attrs.get("crs", ""))}
            except ImportError:
                notes.append("xarray/netCDF4 no instalado: no se extrajo la "
                             "estructura NetCDF (limitación de entorno)")
        elif fmt is Format.ZARR:
            meta["zarr"] = {"entries": sorted(p.name for p in path.iterdir())[:40]}
        else:
            raise IngestError(f"formato no soportado: {fmt.value}")
    except IngestError:
        raise
    except Exception as exc:  # noqa: BLE001 — un header ilegible es un hallazgo
        raise IntegrityError(f"cabecera ilegible ({fmt.value}): {exc}") from exc
    if notes:
        meta["limitations"] = notes
    return meta


@dataclass
class IngestRecord:
    artifact_id: str
    dataset_id: str
    source_id: str
    original_path: str
    stored_path: str
    sha256: str
    bytes: int
    format: str
    format_evidence: str
    metadata: dict[str, Any]
    integrity: dict[str, Any]
    status: IngestStatus
    retrieved_at: str = field(default_factory=utcnow)
    license: str = ""
    source_url: str | None = None
    version: str | None = None
    error: str | None = None
    manifest_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "dataset_id": self.dataset_id,
            "source_id": self.source_id,
            "original_path": self.original_path,
            "stored_path": self.stored_path,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "format": self.format,
            "format_evidence": self.format_evidence,
            "metadata": self.metadata,
            "integrity": self.integrity,
            "status": self.status.value,
            "retrieved_at": self.retrieved_at,
            "license": self.license,
            "source_url": self.source_url,
            "version": self.version,
            "error": self.error,
            "manifest_path": self.manifest_path,
        }


class IngestEngine:
    """Ingesta local verificable, con deduplicación y manifiesto por artefacto."""

    def __init__(self, lay: S.DataLayout | None = None) -> None:
        self.lay = lay or S.layout()
        S.ensure_layout(self.lay)

    # --- registro ----------------------------------------------------------
    def _log(self, record: IngestRecord) -> None:
        self.lay.ingest_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lay.ingest_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"artifact_id": record.artifact_id,
                                 "dataset_id": record.dataset_id,
                                 "sha256": record.sha256,
                                 "status": record.status.value,
                                 "retrieved_at": record.retrieved_at,
                                 "path": record.stored_path},
                                ensure_ascii=False) + "\n")

    def _log_entries(self) -> list[dict[str, Any]]:
        if not self.lay.ingest_log.exists():
            return []
        out = []
        for line in self.lay.ingest_log.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def find_duplicate(self, sha256: str) -> dict[str, Any] | None:
        for entry in reversed(self._log_entries()):
            if entry.get("sha256") == sha256 and entry.get("status") == "INGESTED":
                return entry
        return None

    # --- ingesta -----------------------------------------------------------
    def ingest_local(self, path: Path | str, *, dataset_id: str, source_id: str,
                     license: str = "", source_url: str | None = None,
                     version: str | None = None,
                     expected_sha256: str | None = None,
                     force: bool = False) -> IngestRecord:
        p = Path(path)
        if not p.exists():
            raise IngestError(f"archivo inexistente: {p}")
        if p.stat().st_size == 0:
            raise IntegrityError(f"archivo vacío: {p}")

        digest = S.sha256_file(p)
        artifact_id = f"{dataset_id}.{digest[:12]}"
        integrity = IntegrityCheck()
        integrity.add("archivo no vacío", p.stat().st_size > 0)
        if expected_sha256:
            integrity.add("hash coincide con el esperado", digest == expected_sha256,
                          f"esperado {expected_sha256[:12]}…, leído {digest[:12]}…")

        detection = detect_format(p)
        integrity.add("formato reconocido", detection.format is not Format.UNKNOWN,
                      detection.format.value)
        integrity.add("extensión coherente con el contenido",
                      detection.matches_extension,
                      f"extensión {p.suffix}, contenido {detection.format.value}")

        duplicate = None if force else self.find_duplicate(digest)
        if duplicate:
            # El contenido ya está en el almacén, pero el manifiesto se reescribe
            # con metadatos frescos: sin manifiesto verifiable no hay reanudación.
            record = IngestRecord(
                artifact_id=artifact_id, dataset_id=dataset_id,
                source_id=source_id, original_path=str(p),
                stored_path=duplicate.get("path", ""), sha256=digest,
                bytes=p.stat().st_size, format=detection.format.value,
                format_evidence=detection.evidence,
                metadata=_extract_metadata(p, detection.format),
                integrity=integrity.as_dict(), status=IngestStatus.DUPLICATE,
                license=license, source_url=source_url, version=version,
                error=None,
            )
            record.manifest_path = str(self._write_manifest(record))
            return record

        if not integrity.ok:
            failure = IntegrityCheck_error(integrity)
            record = IngestRecord(
                artifact_id=artifact_id, dataset_id=dataset_id,
                source_id=source_id, original_path=str(p), stored_path="",
                sha256=digest, bytes=p.stat().st_size,
                format=detection.format.value,
                format_evidence=detection.evidence, metadata={},
                integrity=integrity.as_dict(), status=IngestStatus.FAILED,
                license=license, source_url=source_url, version=version,
                error=failure,
            )
            self._write_manifest(record)
            self._log(record)
            raise IntegrityError(failure)

        stored, _, _created = S.store_object(self.lay, p)
        metadata = _extract_metadata(p, detection.format)
        record = IngestRecord(
            artifact_id=artifact_id, dataset_id=dataset_id, source_id=source_id,
            original_path=str(p), stored_path=str(stored), sha256=digest,
            bytes=p.stat().st_size, format=detection.format.value,
            format_evidence=detection.evidence, metadata=metadata,
            integrity=integrity.as_dict(), status=IngestStatus.INGESTED,
            license=license, source_url=source_url, version=version,
        )
        manifest = self._write_manifest(record)
        record.manifest_path = str(manifest)
        self._log(record)
        return record

    def _write_manifest(self, record: IngestRecord) -> Path:
        directory = self.lay.manifests / "ingest"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{record.artifact_id}.json"
        path.write_text(json.dumps(record.as_dict(), indent=2,
                                   ensure_ascii=False), encoding="utf-8")
        return path

    # --- descarga ----------------------------------------------------------
    def download(self, url: str, dest_dir: Path | str, *, allow_hosts: Sequence[str],
                 client: Any | None = None, max_bytes: int = 2_000_000_000,
                 timeout: float = 60.0) -> dict[str, Any]:
        """Descarga con lista blanca de hosts y omisión de contenido idéntico."""
        host = urlparse(url).netloc.split(":")[0].lower()
        allowed = {h.lower() for h in allow_hosts}
        if host not in allowed:
            raise HostNotAllowed(
                f"host '{host}' no está en la lista de fuentes autorizadas "
                f"{sorted(allowed)}")
        ledger = self._load_download_ledger()
        previous = ledger.get(url)

        own_client = client is None
        if own_client:
            import httpx

            client = httpx.Client(follow_redirects=True, timeout=timeout)
        try:
            head = client.head(url)
            etag = head.headers.get("etag")
            length = head.headers.get("content-length")
            if (previous and previous.get("etag") == etag
                    and str(previous.get("content_length")) == str(length)
                    and Path(previous.get("path", "")).exists()):
                return {"status": "SKIPPED", "reason": "ETag y tamaño idénticos "
                        "al registro previo", **previous}
            dest = Path(dest_dir)
            dest.mkdir(parents=True, exist_ok=True)
            name = Path(urlparse(url).path).name or "download.bin"
            target = dest / name
            part = target.with_suffix(target.suffix + ".part")
            digest = __import__("hashlib").sha256()
            size = 0
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(part, "wb") as fh:
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            raise IngestError(
                                f"descarga excede el límite de {max_bytes} B")
                        digest.update(chunk)
                        fh.write(chunk)
            os.replace(part, target)
            sha = digest.hexdigest()
            stored, _, _ = S.store_object(self.lay, target)
            entry = {"url": url, "etag": etag, "content_length": length,
                     "sha256": sha, "bytes": size, "path": str(stored),
                     "retrieved_at": utcnow()}
            ledger[url] = entry
            self._save_download_ledger(ledger)
            return {"status": "DOWNLOADED", **entry}
        finally:
            if own_client:
                client.close()

    def _load_download_ledger(self) -> dict[str, Any]:
        path = self.lay.manifests / "download_ledger.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save_download_ledger(self, ledger: dict[str, Any]) -> None:
        path = self.lay.manifests / "download_ledger.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    # --- lotes -------------------------------------------------------------
    def ingest_batch(self, items: Sequence[dict[str, Any]], *,
                     job_name: str, resume: bool = True) -> dict[str, Any]:
        """Lote con estado: reanuda sin repetir items ya completados."""
        state_path = self.lay.manifests / "ingest_jobs" / f"{job_name}.json"
        state = {"job": job_name, "updated_at": utcnow(), "items": {}}
        if resume and state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        def persist() -> None:
            state["updated_at"] = utcnow()
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                                  encoding="utf-8")

        for item in items:
            item_id = str(item.get("item_id") or item.get("path"))
            prior = state["items"].get(item_id, {})
            if resume and prior.get("status") in {"ok", "DUPLICATE"}:
                prior["resumed"] = True
                continue
            try:
                record = self.ingest_local(
                    item["path"], dataset_id=item["dataset_id"],
                    source_id=item["source_id"],
                    license=item.get("license", ""),
                    source_url=item.get("source_url"),
                    version=item.get("version"),
                    expected_sha256=item.get("expected_sha256"),
                )
                state["items"][item_id] = {
                    "status": "ok" if record.status is IngestStatus.INGESTED
                    else record.status.value,
                    "artifact_id": record.artifact_id,
                    "manifest": record.manifest_path,
                    "bytes": record.bytes,
                }
            except Exception as exc:  # noqa: BLE001 — el lote continúa
                state["items"][item_id] = {
                    "status": "FAILED", "error": str(exc),
                    "traceback": traceback.format_exc(limit=4),
                }
                self.log_error(job=job_name, item=item_id, error=str(exc))
            persist()
        persist()

        statuses = [v.get("status") for v in state["items"].values()]
        return {
            "job": job_name, "items": len(state["items"]),
            "ok": statuses.count("ok"),
            "duplicates": statuses.count("DUPLICATE"),
            "failed": statuses.count("FAILED"),
            "skipped": statuses.count("SKIPPED"),
            "all_ok": all(s in {"ok", "DUPLICATE"} for s in statuses),
            "state_path": str(state_path),
            "items_detail": state["items"],
        }

    def log_error(self, *, job: str, item: str, error: str) -> None:
        path = self.lay.manifests / "pipeline_errors.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": utcnow(), "job": job, "item": item,
                                 "error": error}, ensure_ascii=False) + "\n")


def IntegrityCheck_error(check: IntegrityCheck) -> str:
    failed = [c for c in check.checks if not c["passed"]]
    return "; ".join(f"{c['check']}: {c['detail']}" for c in failed) or "integridad"
