"""Motor hidrológico: pruebas analíticas y sobre el DEM real.

Las pruebas sintéticas tienen resultado conocido (una ladera plana drena hacia
una dirección y su acumulación es predecible). Las pruebas sobre el DEM real
comprueban invariantes que deben cumplirse siempre: acumulación ≥ 1, la cuenca
de la celda de salida coincide con su acumulación, y no se inventa área donde
no hay dato.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv import config as C  # noqa: E402
from agrosv.science import hydrology as H  # noqa: E402
from conftest import require  # noqa: E402


def _plane(rows: int = 6, cols: int = 6) -> np.ndarray:
    """Ladera que desciende hacia el este (cada columna es 10 m más baja)."""
    return np.tile(-10.0 * np.arange(cols), (rows, 1))


def test_relleno_de_sumidero():
    z = np.full((3, 3), 100.0)
    z[1, 1] = 50.0
    filled, info = H.fill_depressions(z)
    assert filled[1, 1] == pytest.approx(100.0)
    assert info["cells_raised"] >= 1


def test_relleno_no_inventa_dato_en_nodata():
    z = np.array([[5.0, 5.0, np.nan], [5.0, 1.0, 5.0], [5.0, 5.0, 5.0]])
    filled, info = H.fill_depressions(z)
    assert np.isnan(filled[0, 2]), "no se rellena una celda sin observación"
    assert filled[1, 1] == pytest.approx(5.0), "el pozo interior se rellena al borde"
    assert info["cells_raised"] == 1


def test_d8_en_ladera_plana_apunta_al_este():
    z = _plane()
    filled, _ = H.fill_depressions(z)
    dirs, info = H.d8_flow_direction(filled, 30.0)
    assert (dirs[:, :-1] == 4).all(), "todas las celdas deben drenar al este (código 4)"
    assert (dirs[:, -1] == H.NO_FLOW).all(), "el borde este no tiene salida"
    assert 0 <= info["flat_or_outlet_pct"] <= 100


def test_acumulacion_crece_aguas_abajo():
    z = _plane()
    filled, _ = H.fill_depressions(z)
    dirs, _ = H.d8_flow_direction(filled, 30.0)
    acc = H.flow_accumulation(dirs, filled)
    for r in range(acc.shape[0]):
        assert np.all(np.diff(acc[r, :]) == 1)
    assert acc[0, -1] == acc.shape[1]
    # conservación: toda el área drena por la columna de salida
    assert acc[:, -1].sum() == acc.size


def test_cuenca_de_la_salida_es_exactamente_su_acumulacion():
    z = _plane()
    filled, _ = H.fill_depressions(z)
    dirs, _ = H.d8_flow_direction(filled, 30.0)
    acc = H.flow_accumulation(dirs, filled)
    outlet = H.outlet_cell(acc)
    mask = H.watershed(dirs, outlet)
    assert mask.sum() == int(acc[outlet])


def test_cuenca_respeta_nodata():
    z = _plane()
    z[:, 3] = np.nan
    filled, _ = H.fill_depressions(z)
    dirs, _ = H.d8_flow_direction(filled, 30.0)
    acc = H.flow_accumulation(dirs, filled)
    mask = H.watershed(dirs, H.outlet_cell(acc), np.isfinite(filled))
    assert not mask[:, 3].any()


def test_red_de_drenaje_por_umbral():
    acc = np.array([[1, 2, 3], [1, 2, 3]])
    assert H.drainage_network(acc, 2).sum() == 4
    with pytest.raises(ValueError):
        H.drainage_network(acc, 0)


def test_ls_factor_positivo_y_monotono():
    slope = np.array([0.0, 5.0, 20.0, 45.0])
    acc = np.array([1, 10, 100, 1000])
    ls = H.ls_factor(slope, acc, 30.0)
    assert np.all(np.isfinite(ls))
    assert np.all(ls > 0)
    assert ls[0] < ls[-1]


def test_compute_aoi_diagnosticos():
    # En una ladera que desciende al este cada fila drena por separado: la
    # acumulación máxima es el ancho (20), no el área total (400).
    out = H.compute_aoi(_plane(20, 20), 30.0, stream_threshold_ratio=0.01)
    assert out["accumulation"].max() == 20
    assert out["diagnostics"]["max_accumulation"] == 20
    assert out["streams"].sum() > 0
    assert out["diagnostics"]["valid_cells"] == 400
    assert out["ls_factor"].shape == (20, 20)


def test_cellsize_invalido():
    with pytest.raises(ValueError):
        H.d8_flow_direction(_plane(3, 3), 0)


def test_dem_real_invariantes():
    """Invariantes sobre el DEM de Fase 1 (ventana, no país completo)."""
    import rasterio

    path = require(C.DEM_WGS84)
    with rasterio.open(path) as ds:
        win = rasterio.windows.Window(3000, 2000, 160, 160)
        z = ds.read(1, window=win).astype(np.float32)
        nodata = ds.nodata
    z[nodata == z] = np.nan
    valid = np.isfinite(z)
    if valid.sum() < 1000:
        pytest.skip("ventana sin datos suficientes del DEM")

    aoi = H.compute_aoi(z, 30.0)
    acc = aoi["accumulation"]
    assert np.nanmin(acc) >= 1.0
    assert int(np.nanmax(acc)) <= int(valid.sum())

    outlet = H.outlet_cell(acc)
    mask = H.watershed(aoi["directions"], outlet, valid)
    assert int(mask.sum()) == int(acc[outlet]), (
        "la cuenca de la salida debe tener exactamente la acumulación de esa celda"
    )
    assert mask.sum() <= valid.sum()
    assert not (mask & ~valid).any()
    assert aoi["diagnostics"]["depressions"]["cells_raised"] >= 0
