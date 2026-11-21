"""AGROSV — procedencia y trazabilidad.

Regla de Fase 0 (`DATA_PIPELINE.md` §9): una cifra sin manifiesto no es
publicable. Este módulo materializa esa regla: cada capa procesada escribe un
sidecar `.provenance.json` y la API lo expone junto al dato.
"""
from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rasterio


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def software_versions() -> dict[str, str]:
    import geopandas
    import pyproj
    import shapely

    return {
        "python": platform.python_version(),
        "gdal": rasterio.__gdal_version__,
        "rasterio": rasterio.__version__,
        "geopandas": geopandas.__version__,
        "shapely": shapely.__version__,
        "pyproj": pyproj.__version__,
    }


def raster_info(path: Path) -> dict[str, Any]:
    """Resolución y CRS reales leídos del archivo, no de lo que creemos haber escrito."""
    with rasterio.open(path) as ds:
        return {
            "crs": str(ds.crs),
            "width": ds.width,
            "height": ds.height,
            "count": ds.count,
            "dtype": ds.dtypes[0],
            "nodata": ds.nodata,
            "res": [abs(v) for v in ds.res],
            "bounds": list(ds.bounds),
        }


def write_manifest(
    path: Path,
    *,
    layer: str,
    source_id: str,
    source_url: str | None,
    license: str,
    attribution: str,
    native_resolution: str,
    effective_resolution: str,
    transform: str,
    extra: dict[str, Any] | None = None,
    provenance_id: str | None = None,
) -> dict[str, Any]:
    """Escribe `<path>.provenance.json` y devuelve el registro."""
    payload: dict[str, Any] = {
        "provenance_id": provenance_id or f"{layer}@{utcnow()}",
        "layer": layer,
        "artifact": str(path.relative_to(Path(path).parents[len(Path(path).parents) - 1]))
        if path.is_absolute()
        else str(path),
        "source_id": source_id,
        "source_url": source_url,
        "license": license,
        "attribution": attribution,
        "native_resolution": native_resolution,
        "effective_resolution": effective_resolution,
        "transform": transform,
        "generated_at": utcnow(),
        "software": software_versions(),
    }
    if path.suffix.lower() in {".tif", ".tiff"}:
        payload["raster"] = raster_info(path)
    if extra:
        payload["extra"] = extra
    payload["artifact_sha256"] = sha256_file(path)

    sidecar = path.with_suffix(path.suffix + ".provenance.json")
    sidecar.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def read_manifest(path: Path) -> dict[str, Any] | None:
    sidecar = path.with_suffix(path.suffix + ".provenance.json")
    if not sidecar.exists():
        return None
    return json.loads(sidecar.read_text(encoding="utf-8"))
