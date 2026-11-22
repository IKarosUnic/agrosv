"""Rendimiento y memoria acotada: lo que debe poder hacerse sin cargar el país.

Los umbrales son deliberadamente holgados (máquina de desarrollo, Windows). Su
función es detectar un cambio de orden de magnitud —por ejemplo, que una consulta
pase de ventana a lectura completa—, no medir un benchmark reproducible.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv import config as C  # noqa: E402
from agrosv.data import raster as R  # noqa: E402
from agrosv.data import storage as S  # noqa: E402
from agrosv.data.catalog import Catalog  # noqa: E402
from agrosv.data.store import DataStore  # noqa: E402
from conftest import require  # noqa: E402


def test_ventana_del_dem_no_materializa_el_pais():
    require(C.DEM_WGS84)
    bounds = (-89.30, 13.65, -89.24, 13.71)
    start = time.perf_counter()
    data, _ = R.read_window(C.DEM_WGS84, bounds)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"ventana DEM tardó {elapsed:.2f}s"
    assert data.size < C.DEM_WGS84.stat().st_size / 4, (
        "la ventana devolvió más celdas que un recorte razonable")


def test_bloques_de_chirps_no_cargan_el_mundo():
    sample = (Path("data/samples/phase3/chirps3_day")
              / "chirps-v3.0.rnl.2026.01.15.tif")
    require(sample)
    profile = R.profile_raster(sample)
    total_cells = profile.width * profile.height
    largest = 0
    blocks = 0
    for window, data in R.iter_blocks(sample):
        blocks += 1
        largest = max(largest, data.size)
        if blocks >= 3:
            break
    assert blocks >= 1
    assert largest < total_cells / 10


def test_consulta_de_observaciones_es_rapida():
    require(S.layout().store_path)
    store = DataStore(S.layout().store_path)
    start = time.perf_counter()
    result = store.observation_query(dataset_id="open_meteo_point",
                                     variable="temperature", limit=100)
    elapsed = time.perf_counter() - start
    assert result.total > 0
    assert elapsed < 1.0, f"consulta tardó {elapsed:.2f}s"
    start = time.perf_counter()
    store.observation_query(bbox=(-89.30, 13.60, -89.10, 13.80), limit=100)
    assert time.perf_counter() - start < 1.0


def test_carga_de_catalogo_es_rapida():
    require(S.layout().catalog_path)
    start = time.perf_counter()
    catalog = Catalog.load(S.layout().catalog_path)
    elapsed = time.perf_counter() - start
    assert len(catalog) >= 20
    assert elapsed < 2.0, f"catálogo tardó {elapsed:.2f}s"


def test_perfil_de_rasters_gestionados_por_cabecera():
    catalog_path = S.layout().raster_catalog
    require(catalog_path)
    import json

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    start = time.perf_counter()
    for entry in payload["rasters"][:5]:
        R.profile_raster(Path(entry["path"]))
    elapsed = time.perf_counter() - start
    assert elapsed < 3.0, f"5 perfiles tardaron {elapsed:.2f}s"
