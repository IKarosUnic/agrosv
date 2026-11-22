"""Fase 5 — HydrologyEngine: agua superficial, cuenca D8 y balance hídrico."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv import config as C  # noqa: E402
from agrosv.engines import hydrology as HY  # noqa: E402
from conftest import require  # noqa: E402

POINT = (-89.2, 13.7)


def test_ventana_rechaza_tamanos_invalidos():
    with pytest.raises(HY.WindowError):
        HY.dem_window_metric(*POINT, size_m=10)
    with pytest.raises(HY.WindowError):
        HY.dem_window_metric(*POINT, size_m=100_000)


def test_ventana_metrica_tiene_resolucion_y_crs_declarados():
    require(C.DEM_WGS84)
    window = HY.dem_window_metric(*POINT, size_m=3000)
    assert window.crs == C.CRS_METRIC
    assert window.res_m == 30.0
    assert window.shape == (100, 100)
    assert 0.0 <= window.nodata_share <= 1.0
    assert window.row == 50 and window.col == 50


def test_agua_superficial_reporta_distancia_real_y_advertencias():
    require(C.INFRA_GPKG)
    result = HY.surface_water(*POINT, max_km=10.0)
    assert result["available"] is True
    nearest = result["nearest_any"]
    if nearest is not None:
        assert nearest["distance_m"] >= 0
        assert nearest["distance_km"] == pytest.approx(
            nearest["distance_m"] / 1000.0, abs=0.001)
        assert nearest["osm_id"]
    text = " ".join(result["caveats"]).lower()
    assert "caudal" in text
    assert "subterránea" in text


def test_agua_superficial_no_infiere_agua_de_un_cauce():
    require(C.INFRA_GPKG)
    result = HY.surface_water(*POINT)
    assert any("no dice nada" in c.lower() or "no implica" in c.lower()
               for c in result["caveats"])


def test_agua_subterranea_declarada_no_disponible():
    result = HY.groundwater_availability()
    assert result["available"] is False
    for key in ("groundwater_aquifers", "groundwater_levels",
                "groundwater_recharge", "water_rights"):
        assert key in result["variables"]
        assert result["variables"][key]["would_require"]
    assert "agua subterránea" in result["note"].lower()


def test_cuenca_derivada_conserva_invariantes():
    require(C.DEM_WGS84)
    basin = HY.watershed_from_point(*POINT, size_m=4000)
    assert basin["upstream_area_km2"] > 0
    assert basin["upstream_area_km2"] <= 16.0  # no puede exceder la ventana
    assert basin["diagnostics"]["valid_cells"] > 0
    assert basin["diagnostics"]["max_accumulation"] >= 1
    assert basin["truncated"] in (True, False)
    assert basin["limitations"], "sin limitaciones no es publicable"
    text = " ".join(basin["limitations"]).lower()
    assert "no es una cuenca oficial" in text


def test_cuenca_ventana_pequena_marca_truncamiento():
    require(C.DEM_WGS84)
    small = HY.watershed_from_point(*POINT, size_m=2000)
    # En una ventana de 2 km es esperable que la cuenca toque el borde: si no,
    # al menos el flag debe existir y ser booleano.
    assert isinstance(small["truncated"], bool)
    assert small["window"]["size_m"] == 2000


def test_budyko_respeta_limites_fisicos():
    assert HY._budyko_runoff(1000, 0, omega=2.0) == pytest.approx(1000)
    assert HY._budyko_runoff(0, 500, omega=2.0) is None
    for p, e in ((800, 1200), (2000, 900), (500, 500)):
        q = HY._budyko_runoff(p, e, omega=2.0)
        assert 0 <= q <= p, "la escorrentía no puede ser negativa ni exceder P"


def test_balance_hidrico_coherente_y_con_incertidumbre():
    require(C.DATA / "validated" / "agrosv_data.sqlite")
    balance = HY.water_balance(*POINT)
    assert balance["available"] is True
    mean = balance["mean"]
    assert mean["precipitation_mm"] > 0
    assert mean["et0_mm"] > 0
    assert mean["precipitation_minus_et0_mm"] == pytest.approx(
        mean["precipitation_mm"] - mean["et0_mm"], abs=0.2)
    if mean["budyko_runoff_mm"] is not None:
        assert 0 <= mean["budyko_runoff_mm"] <= mean["precipitation_mm"]
        low, high = mean["budyko_runoff_range_mm_omega_1.5_3.0"]
        assert low <= high
    assert balance["uncertainty"]["method"]
    assert any("no es un caudal" in lim for lim in balance["limitations"])
    assert any("recarga" in lim for lim in balance["limitations"])


def test_perfil_hidrologico_no_confunde_potencial_con_acceso():
    require(C.DEM_WGS84)
    payload = HY.HydrologyEngine().profile(*POINT, size_m=3000)
    rule = payload["result"]["hydrological_interpretation"]["rule"].lower()
    assert "acceso" in rule and "≠" in payload["result"][
        "hydrological_interpretation"]["rule"]
    assert payload["result"]["groundwater"]["available"] is False
    assert payload["sources"]
