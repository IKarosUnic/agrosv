"""Módulo 4 — suelos: rejilla común, rangos y naturaleza predictiva."""
from __future__ import annotations

import numpy as np
import pytest
import rasterio

from agrosv import config as C
from conftest import require

RASTERS = ["phh2o", "soc", "nitrogen", "clay", "sand", "silt"]
RANGES = {
    "phh2o": (3.0, 10.0), "soc": (0.0, 300.0), "nitrogen": (0.0, 30.0),
    "clay": (0.0, 100.0), "sand": (0.0, 100.0), "silt": (0.0, 100.0),
}


def _path(prop: str):
    return C.SOILS_RASTER_DIR / f"{prop}_0-30cm.tif"


@pytest.mark.parametrize("prop", RASTERS)
def test_rejilla_comun(prop, soil_stats):
    with rasterio.open(require(_path(prop))) as ds:
        assert ds.crs.to_string() == C.CRS_METRIC
        assert ds.res[0] == pytest.approx(250.0, abs=1e-6)
        assert ds.width == soil_stats["grid"]["width"]
        assert ds.height == soil_stats["grid"]["height"]


@pytest.mark.parametrize("prop", RASTERS)
def test_rangos_fisicos(prop):
    with rasterio.open(require(_path(prop))) as ds:
        arr = ds.read(1, masked=True) * ds.scales[0]
    vals = arr.compressed()
    lo, hi = RANGES[prop]
    assert vals.size > 0
    assert vals.min() >= lo
    assert vals.max() <= hi


def test_textura_suma_cien():
    arrays = []
    for prop in ("clay", "sand", "silt"):
        with rasterio.open(require(_path(prop))) as ds:
            arrays.append(ds.read(1, masked=True) * ds.scales[0])
    total = (arrays[0] + arrays[1] + arrays[2]).compressed()
    assert abs(float(total.mean()) - 100.0) < 1.0


def test_cobertura_sobre_tierra(soil_stats):
    for prop, cov in soil_stats["depth_coverage"].items():
        assert cov > 0.95, f"{prop}: {cov}"
    assert "agua" in soil_stats["coverage_note"]


def test_no_se_presenta_como_medicion(soil_stats):
    text = " ".join(soil_stats["caveats"]).lower()
    assert "predicci" in text
    assert "laboratorio" in text
    assert any(s["status"].startswith("identificado")
               for s in soil_stats["national_sources"])


def test_manifiesto_suelos():
    from agrosv.provenance import read_manifest

    m = read_manifest(_path("phh2o"))
    assert m is not None
    assert m["license"] == "CC-BY-4.0"
    assert m["extra"]["prediction_not_measurement"] is True
    assert m["extra"]["depth"] == "0-30cm"


def test_medias_nacionales_plausibles(soil_stats):
    means = soil_stats["country_means"]
    assert 4.5 <= means["phh2o"] <= 8.5
    assert 5 <= means["soc"] <= 80
    assert 20 <= means["clay"] <= 60


def test_nitrogeno_es_menor_que_carbono(soil_stats):
    means = soil_stats["country_means"]
    assert means["nitrogen"] < means["soc"]
