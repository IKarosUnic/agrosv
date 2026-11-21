"""Módulo 2 — resolución, rangos físicos y ausencia de valores espurios."""
from __future__ import annotations

import numpy as np
import pytest
import rasterio

from agrosv import config as C
from conftest import require


def _read(path, masked=True):
    with rasterio.open(require(path)) as ds:
        return ds.read(1, masked=masked), ds


def test_dem_resolucion_nativa():
    _, ds = _read(C.DEM_WGS84, masked=False)
    assert ds.crs.to_string() == C.CRS_STORAGE
    assert ds.res[0] == pytest.approx(1 / 3600, abs=1e-12)
    assert ds.res[1] == pytest.approx(1 / 3600, abs=1e-12)


def test_derivadas_en_crs_metrico_y_30m():
    for path in (C.SLOPE, C.ASPECT, C.HILLSHADE, C.RELIEF_CLASS):
        with rasterio.open(require(path)) as ds:
            assert ds.crs.to_string() == C.CRS_METRIC
            assert ds.res[0] == pytest.approx(30.0, abs=1e-6)


def test_dem_sin_nodata_excesivo(topo_stats):
    # El rectángulo envolvente incluye mar, por lo que el nodata global supera
    # el 50 %. Lo relevante es la cobertura DENTRO del país, que el módulo
    # verificó y registró: se comprueba ese resultado, no el mar.
    checks = {c["check"]: c for c in topo_stats["validation"]}
    assert checks["DEM sin nodata dentro del territorio"]["passed"]
    assert topo_stats["country"]["elev_max_m"] > 2000


def test_rango_de_elevacion():
    arr, _ = _read(C.DEM_WGS84)
    vals = arr.compressed()
    assert vals.min() > -20
    assert vals.max() < 3000


def test_pendiente_en_grados_fisicos():
    with rasterio.open(require(C.SLOPE)) as ds:
        arr = ds.read(1, masked=True) * ds.scales[0]
    vals = arr.compressed()
    assert vals.min() >= 0.0
    assert vals.max() <= 90.0
    assert 5.0 <= float(vals.mean()) <= 25.0


def test_aspecto_no_alcanza_360():
    with rasterio.open(require(C.ASPECT)) as ds:
        arr = ds.read(1, masked=True) * ds.scales[0]
    vals = arr.compressed()
    assert vals.min() >= 0.0
    assert vals.max() < 360.0


def test_hillshade_uint8_y_nodata_declarado():
    with rasterio.open(require(C.HILLSHADE)) as ds:
        assert ds.dtypes[0] == "uint8"
        assert ds.nodata == 0


def test_clases_de_relieve_solo_0_a_5():
    with rasterio.open(require(C.RELIEF_CLASS)) as ds:
        arr = ds.read(1)
        mask = ds.read_masks(1) > 0
    codes = np.unique(arr[mask])
    assert set(codes.tolist()).issubset({0, 1, 2, 3, 4, 5})


def test_nodata_de_derivadas_bajo_el_umbral(topo_stats):
    for layer in topo_stats["validation"]:
        assert layer["passed"], layer["check"]
    for path in (C.SLOPE, C.ASPECT):
        with rasterio.open(require(path)) as ds:
            nodata = 1 - float(ds.read_masks(1).mean())
        assert nodata < 0.60  # rectángulo envolvente: ~54 % fuera del país
    with rasterio.open(require(C.SLOPE)) as ds:
        m = ds.dataset_mask()
    assert m.mean() > 0.3


def test_estadistica_por_departamento_completa(topo_stats):
    assert len(topo_stats["departments"]) == 14
    for code, d in topo_stats["departments"].items():
        assert code.startswith("SV-")
        assert d["pixels"] > 0
        assert 0 <= d["slope_mean_deg"] <= 90
        assert d["elev_max_m"] >= d["elev_min_m"]


def test_transformacion_de_coordenadas_ida_y_vuelta():
    from rasterio.warp import transform as warp_transform

    lon, lat = -89.2, 13.7
    x, y = warp_transform(C.CRS_STORAGE, C.CRS_METRIC, [lon], [lat])
    lon2, lat2 = warp_transform(C.CRS_METRIC, C.CRS_STORAGE, x, y)
    # ida y vuelta en un par de milímetros
    assert abs(lon2[0] - lon) < 1e-8
    assert abs(lat2[0] - lat) < 1e-8
    # UTM 16N tiene su meridiano central en -87°: al oeste del país el este
    # cae por debajo de 500 km.
    assert 200_000 < x[0] < 600_000
    assert 1_400_000 < y[0] < 1_650_000


def test_manifiesto_topografia():
    from agrosv.provenance import read_manifest

    m = read_manifest(C.SLOPE)
    assert m is not None
    assert m["transform"].startswith("warp")
    assert "copernicus" in m["attribution"].lower()
