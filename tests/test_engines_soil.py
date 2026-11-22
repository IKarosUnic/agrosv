"""Fase 5 — SoilEngine: textura USDA, materia orgánica, perfil y reglas."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv import config as C  # noqa: E402
from agrosv.engines import governance as G  # noqa: E402
from agrosv.engines import soil as S  # noqa: E402
from conftest import require  # noqa: E402

# Punto con dato verificado de SoilGrids (no urbano ni cuerpo de agua).
SOIL_POINT = (-88.6, 13.4)
# Celda declarada NoData en la máscara (San Salvador urbano/costa a 250 m).
NODATA_POINT = (-89.2, 13.7)


# --- clasificación textural --------------------------------------------------
@pytest.mark.parametrize("sand,silt,clay,expected", [
    (90, 5, 5, "arena"),
    (80, 15, 5, "arena franca"),
    (65, 25, 10, "franco arenoso"),
    (50, 30, 20, "franco"),
    (30, 55, 15, "franco limoso"),
    (5, 90, 5, "limo"),
    (30, 35, 35, "arcilla franca"),
    (20, 50, 30, "franco arcillo-limoso"),
    (55, 15, 30, "franco arcillo-arenoso"),
    (10, 45, 45, "arcilla limosa"),
    (50, 5, 45, "arcilla arenosa"),
    (25, 35, 40, "arcilla"),
])
def test_clases_texturales_usda(sand, silt, clay, expected):
    assert S.usda_texture_class(sand, silt, clay) == expected


def test_textura_sin_clasificar_si_la_suma_no_es_coherente():
    assert S.usda_texture_class(10, 10, 10) == "sin_clasificar"
    assert S.usda_texture_class(80, 80, 80) == "sin_clasificar"


# --- materia orgánica --------------------------------------------------------
def test_materia_organica_usa_factor_declarado():
    result = S.organic_matter(28.37)
    assert result["value"] == pytest.approx(28.37 * 1.724 / 10, abs=0.01)
    assert result["label"] == "derivado"
    assert result["factor"] == 1.724
    assert 1.7 <= result["factor_range"][0] <= result["factor_range"][1] <= 2.0
    assert S.organic_matter(None) is None


# --- modelo de perfil --------------------------------------------------------
def test_modelo_de_perfil_declara_intervalos_ausentes():
    model = S.profile_model()
    assert [0, 30] in model["standard_intervals_cm"]
    available = [iv for iv in model["intervals"] if iv["status"] == "available"]
    assert len(available) == 1
    assert available[0]["top_cm"] == 0 and available[0]["bottom_cm"] == 30
    missing = [iv for iv in model["intervals"] if iv["status"] != "available"]
    assert missing and all(iv["reason"] for iv in missing)


# --- reglas de limitación ----------------------------------------------------
def test_reglas_de_limitacion_no_generan_puntaje():
    values = {"ph": 5.0, "clay": 40.0, "sand": 20.0,
              "soil_organic_carbon": 5.0}
    findings = S.evaluate_limitations(values)
    codes = {f["code"] for f in findings}
    assert {"acidez_fuerte", "arcilla_alta",
            "carbono_organico_bajo"} <= codes
    for finding in findings:
        assert finding["threshold"] is not None
        assert finding["implication"]
        assert finding["rule"]
        assert "score" not in finding and "index" not in finding
    assert not any("valor_total" in f for f in findings)


def test_reglas_no_inventan_hallazgos_sin_dato():
    assert S.evaluate_limitations({"ph": None, "clay": None}) == []


def test_suelo_real_sin_dato_declara_no_disponible():
    require(C.SOILS_RASTER_DIR / "clay_0-30cm.tif")
    payload = S.SoilEngine().sample(*NODATA_POINT)
    clay = payload["result"]["properties"]["clay"]
    assert clay["available"] is False
    assert clay["value"] is None
    assert "NoData" in (clay["cell"].get("reason") or "")
    assert payload["result"]["derived"]["texture_class"] is None


def test_suelo_real_conserva_unidades_procedencia_y_resolucion():
    require(C.SOILS_RASTER_DIR / "clay_0-30cm.tif")
    payload = S.SoilEngine().sample(*SOIL_POINT)
    props = payload["result"]["properties"]
    if not props["clay"]["available"]:
        pytest.skip("la celda de prueba cayó en NoData: no se fuerza un valor")
    assert 0 <= props["clay"]["value"] <= 100
    assert 0 <= props["sand"]["value"] <= 100
    assert 0 <= props["silt"]["value"] <= 100
    total = (props["clay"]["value"] + props["sand"]["value"]
             + props["silt"]["value"])
    assert 95 <= total <= 105, "las fracciones deben sumar ~100 %"
    assert props["clay"]["unit"] == "%"
    assert props["ph"]["unit"] == ""
    assert props["clay"]["evidence_class"] == "modeled_prediction"
    assert props["clay"]["dataset_id"] == "soilgrids_2"
    assert props["clay"]["cell"]["res"] == [250.0, 250.0]

    sources = {s["dataset_id"]: s for s in payload["sources"]}
    assert sources["soilgrids_2"]["spatial_resolution"].startswith("250 m")
    assert sources["soilgrids_2"]["license"] == "CC BY 4.0"
    assert payload["result"]["depth_interval_cm"] == [0, 30]


def test_suelo_declara_lo_que_no_puede_dar():
    require(C.SOILS_RASTER_DIR / "clay_0-30cm.tif")
    payload = S.SoilEngine().sample(*SOIL_POINT)
    missing = payload["result"]["not_available"]
    for key in ("soil_depth", "soil_cec", "soil_awc", "soil_salinity",
                "soil_national_map"):
        assert key in missing
        assert missing[key]["reason"]
    comparison = payload["result"]["comparison"]
    assert comparison["comparison_possible"] is False
    assert comparison["conflicts"] == []
    assert any(source["status"] == "RESTRICTED"
               for source in comparison["unavailable_sources"])


def test_comparacion_no_presenta_centa_como_disponible():
    require(C.SOILS_RASTER_DIR / "clay_0-30cm.tif")
    payload = S.SoilEngine().sample(*SOIL_POINT)
    available = [s["dataset_id"]
                 for s in payload["result"]["comparison"]["available_sources"]]
    assert available == ["soilgrids_2"]
    assert "centa_suelos" not in available


def test_gobernanza_registra_soilgrids_como_prediccion():
    src = G.source("soilgrids_2")
    assert src.data_class == G.DataClass.MODELED_PREDICTION
    assert "no sustituye" in " ".join(src.assumptions).lower() or \
        any("laboratorio" in a for a in src.assumptions)
    assert src.nodata == -32768.0
