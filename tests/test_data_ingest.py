"""Motor de ingesta: formatos, integridad, deduplicación y reanudación."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.data import ingest as ING  # noqa: E402
from agrosv.data import storage as S  # noqa: E402


@pytest.fixture()
def engine(tmp_path):
    lay = S.DataLayout(root=tmp_path / "data")
    S.ensure_layout(lay)
    return ING.IngestEngine(lay), lay


def write_geojson(path: Path) -> Path:
    path.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "properties": {"name": "prueba"},
            "geometry": {"type": "Point", "coordinates": [-89.2, 13.7]},
        }],
    }), encoding="utf-8")
    return path


def write_csv(path: Path) -> Path:
    path.write_text("variable,valor\ntemperatura,25.4\n", encoding="utf-8")
    return path


def write_raster(path: Path, *, nodata: float | None = None) -> Path:
    data = np.arange(100, dtype="float32").reshape(10, 10)
    profile = {
        "driver": "GTiff", "width": 10, "height": 10, "count": 1,
        "dtype": "float32", "crs": "EPSG:4326",
        "transform": from_origin(-89.5, 14.0, 0.01, 0.01),
        "nodata": nodata, "tiled": False, "compress": "lzw",
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)
    return path


def test_detecta_formatos_por_contenido(tmp_path):
    assert ING.detect_format(write_geojson(tmp_path / "a.json")).format is ING.Format.GEOJSON
    assert ING.detect_format(write_csv(tmp_path / "a.csv")).format is ING.Format.CSV
    assert ING.detect_format(write_raster(tmp_path / "a.tif")).format is ING.Format.GEOTIFF
    plain = tmp_path / "plain.json"
    plain.write_text('{"a": 1}', encoding="utf-8")
    assert ING.detect_format(plain).format is ING.Format.JSON


def test_extension_incoherente_se_reporta(tmp_path):
    csv = write_csv(tmp_path / "datos.json")  # texto delimitado con .json
    detection = ING.detect_format(csv)
    assert detection.format is ING.Format.CSV
    assert not detection.matches_extension


def test_ingesta_guarda_hash_manifiesto_y_objeto(engine, tmp_path):
    eng, lay = engine
    source = write_geojson(tmp_path / "muestra.geojson")
    record = eng.ingest_local(source, dataset_id="ds", source_id="src",
                              license="CC BY 4.0")
    assert record.status is ING.IngestStatus.INGESTED
    assert record.sha256 == S.sha256_file(source)
    assert Path(record.stored_path).exists()
    assert Path(record.manifest_path).exists()
    manifest = json.loads(Path(record.manifest_path).read_text(encoding="utf-8"))
    assert manifest["integrity"]["ok"] is True
    assert manifest["metadata"]["geojson"]["features"] == 1
    assert record.artifact_id.startswith("ds.")
    assert (lay.objects / record.sha256[:2]).exists()


def test_segunda_ingesta_identica_no_duplica(engine, tmp_path):
    eng, lay = engine
    a = write_geojson(tmp_path / "a.geojson")
    b = write_geojson(tmp_path / "b.geojson")  # mismo contenido, otro nombre
    first = eng.ingest_local(a, dataset_id="ds", source_id="src")
    second = eng.ingest_local(b, dataset_id="ds", source_id="src")
    assert second.status is ING.IngestStatus.DUPLICATE
    assert second.stored_path == first.stored_path
    objects = list((lay.objects).rglob("*"))
    blobs = [p for p in objects if p.is_file()]
    assert len(blobs) == 1, "el almacén direccionado por contenido duplicó el blob"


def test_hash_esperado_distinto_falla(engine, tmp_path):
    eng, _ = engine
    source = write_geojson(tmp_path / "a.geojson")
    with pytest.raises(ING.IntegrityError):
        eng.ingest_local(source, dataset_id="ds", source_id="src",
                         expected_sha256="0" * 64)


def test_archivo_vacio_falla(engine, tmp_path):
    eng, _ = engine
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ING.IntegrityError):
        eng.ingest_local(empty, dataset_id="ds", source_id="src")


def test_lote_se_reanuda_sin_repetir(engine, tmp_path):
    eng, lay = engine
    good = write_csv(tmp_path / "good.csv")
    missing = tmp_path / "missing.csv"
    items = [
        {"item_id": "good", "path": str(good), "dataset_id": "ds",
         "source_id": "src"},
        {"item_id": "missing", "path": str(missing), "dataset_id": "ds",
         "source_id": "src"},
    ]
    first = eng.ingest_batch(items, job_name="lote", resume=True)
    assert first["ok"] == 1 and first["failed"] == 1
    state = json.loads(Path(first["state_path"]).read_text(encoding="utf-8"))
    assert state["items"]["good"]["status"] == "ok"

    missing.write_text("variable,valor\nph,6.4\n", encoding="utf-8")
    second = eng.ingest_batch(items, job_name="lote", resume=True)
    assert second["all_ok"]
    state = json.loads(Path(second["state_path"]).read_text(encoding="utf-8"))
    assert state["items"]["good"].get("resumed") is True


def test_host_no_autorizado_se_rechaza(engine):
    eng, _ = engine
    with pytest.raises(ING.HostNotAllowed):
        eng.download("https://no-autorizado.example/x.tif", eng.lay.raw,
                     allow_hosts=["data.chc.ucsb.edu"])


class _FakeResponse:
    headers = {"etag": '"abc"', "content-length": "11"}

    def raise_for_status(self) -> None:
        return None


class _FakeStream:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self):
        yield self.payload


class _FakeClient:
    def head(self, url):
        return _FakeResponse()

    def stream(self, method, url):
        return _FakeStream(b"contenido-ok")

    def close(self):
        return None


def test_descarga_omite_contenido_identico(engine):
    eng, _ = engine
    client = _FakeClient()
    first = eng.download("https://data.chc.ucsb.edu/a.tif", eng.lay.raw,
                         allow_hosts=["data.chc.ucsb.edu"], client=client)
    assert first["status"] == "DOWNLOADED"
    second = eng.download("https://data.chc.ucsb.edu/a.tif", eng.lay.raw,
                          allow_hosts=["data.chc.ucsb.edu"], client=client)
    assert second["status"] == "SKIPPED"
    assert (eng.lay.manifests / "download_ledger.json").exists()


def test_raster_se_inspecciona_sin_cargarlo(engine, tmp_path):
    eng, _ = engine
    raster = write_raster(tmp_path / "r.tif", nodata=-9999.0)
    record = eng.ingest_local(raster, dataset_id="ds", source_id="src")
    assert record.format == "geotiff"
    meta = record.metadata["raster"]
    assert meta["width"] == 10 and meta["nodata"] == -9999.0
    assert "bounds" in meta
