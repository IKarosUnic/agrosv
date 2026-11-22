"""Índices espectrales: aritmética verificable y límites declarados.

No hay escenas satelitales en este repositorio, así que no se prueba adquisición
(sería una prueba ficticia). Se prueba lo que sí existe: que la fórmula sea la
publicada, que la ausencia de dato no se convierta en cero y que la resolución
efectiva declarada no se confunda con la de visualización.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.science import indices as I  # noqa: E402


def test_ndvi_valor_analitico():
    out = I.ndvi(np.array([0.5], dtype="f4"), np.array([0.1], dtype="f4"))
    assert out[0] == pytest.approx(0.4 / 0.6, rel=1e-6)


def test_ndvi_agua_negativo_y_vegetacion_positivo():
    veg = I.ndvi(np.array([0.45]), np.array([0.08]))
    agua = I.ndvi(np.array([0.05]), np.array([0.12]))
    assert veg[0] > 0.5
    assert agua[0] < 0


def test_ndvi_denominador_nulo_es_nan_no_cero():
    out = I.ndvi(np.array([0.2]), np.array([-0.2]))
    assert np.isnan(out[0]), "un denominador nulo no puede publicarse como 0"


def test_indices_recortados_a_rango_fisico():
    out = I.ndvi(np.array([5.0, -5.0]), np.array([0.1, 0.1]))
    assert np.all(out >= -1.0) and np.all(out <= 1.0)


def test_evi_formula_publicada():
    nir, red, blue = 0.5, 0.2, 0.1
    esperado = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)
    out = I.evi(np.array([nir]), np.array([red]), np.array([blue]))
    assert out[0] == pytest.approx(esperado, rel=1e-6)


def test_ndwi_y_ndmi_y_nbr():
    assert I.ndwi(np.array([0.3]), np.array([0.1]))[0] == pytest.approx(0.5)
    assert I.ndmi(np.array([0.3]), np.array([0.1]))[0] == pytest.approx(0.5)
    # NBR: (0.4 - 0.2) / (0.4 + 0.2) = 0.333, no 0.5
    assert I.nbr(np.array([0.4]), np.array([0.2]))[0] == pytest.approx(0.2 / 0.6)


def test_compute_exige_bandas_declaradas():
    with pytest.raises(KeyError):
        I.compute("ndvi", {"nir": np.array([0.3])})
    with pytest.raises(KeyError):
        I.compute("inexistente", {})


def test_compute_despacha_correctamente():
    bands = {"nir": np.array([0.5]), "red": np.array([0.1]),
             "blue": np.array([0.05]), "green": np.array([0.2]),
             "swir1": np.array([0.2]), "swir2": np.array([0.15])}
    for name in ("ndvi", "evi", "ndwi", "ndmi", "nbr"):
        assert I.compute(name, bands).shape == (1,)


def test_reflectancia_escala_y_offset():
    out = I.to_reflectance(np.array([5000], dtype="int32"), scale=1e-4)
    assert out[0] == pytest.approx(0.5, rel=1e-6)
    con_offset = I.to_reflectance(np.array([5000], dtype="int32"), scale=1e-4,
                                  offset=-1000)
    assert con_offset[0] == pytest.approx(0.4, rel=1e-6)


def test_bandas_de_distinta_forma_fallan():
    with pytest.raises(ValueError):
        I.ndvi(np.zeros((2, 2)), np.zeros((3, 3)))


def test_cambio_requiere_umbral_justificado():
    with pytest.raises(ValueError):
        I.change_mask(np.zeros((2, 2)), np.zeros((2, 2)), threshold=0)


def test_mascara_de_cambio_cuenta_bien():
    before = np.array([[0.2, 0.2], [0.8, np.nan]])
    after = np.array([[0.5, 0.21], [0.5, 0.5]])
    out = I.change_mask(before, after, threshold=0.2)
    assert out["changed_pixels"] == 2  # (0,0) sube 0.3; (1,0) baja 0.3
    assert out["decrease"].sum() == 1
    assert out["increase"].sum() == 1
    assert out["valid_pixels"] == 3


def test_anomalia_robusta_de_la_serie():
    baseline = np.arange(1, 10, dtype=float)
    series = np.array([5.0, 100.0])
    z = I.series_anomaly(series, baseline)
    assert z[0] == pytest.approx(0.0)
    assert z[1] > 10


def test_resolucion_efectiva_declarada():
    specs = I.specs()
    assert specs["ndvi"]["resolution_m"] == 10
    assert specs["ndmi"]["resolution_m"] == 20
    assert any("20 m" in s for s in specs["ndmi"]["limitations"])
    for name, spec in specs.items():
        assert spec["limitations"], f"{name} sin limitaciones declaradas"
        assert spec["formula"]
