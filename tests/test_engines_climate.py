"""Fase 5 — ClimateEngine: agregación temporal, rachas, extremos y sequía."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv.engines import climate as CL  # noqa: E402
from conftest import require  # noqa: E402

DB = ROOT / "data" / "validated" / "agrosv_data.sqlite"
POINT = (-89.2, 13.7)


def _engine() -> CL.ClimateEngine:
    require(DB)
    return CL.ClimateEngine()


# --- utilidades temporales ---------------------------------------------------
def test_haversine_es_cero_en_el_mismo_punto_y_simetrica():
    assert CL.haversine_km(-89.2, 13.7, -89.2, 13.7) == 0.0
    a = CL.haversine_km(-89.2, 13.7, -88.2, 13.7)
    b = CL.haversine_km(-88.2, 13.7, -89.2, 13.7)
    assert a == pytest.approx(b)
    assert 100 < a < 120, "1° de longitud a 13,7° N ≈ 108 km"


def test_agregacion_anual_marca_periodos_incompletos():
    series = [(f"2020-01-{d:02d}", 1.0) for d in range(1, 11)]
    result = CL._aggregate_annual(series, "sum")
    assert result[2020]["value"] == pytest.approx(10.0)
    assert result[2020]["complete"] is False
    assert result[2020]["quality_flag"] == "incomplete_period"
    assert result[2020]["coverage"] < 0.9


def test_rachas_seca_y_humeda_conocidas():
    series = [
        ("2020-01-01", 0.0), ("2020-01-02", 0.0), ("2020-01-03", 0.0),
        ("2020-01-04", 5.0), ("2020-01-05", 0.0),
    ]
    dry = CL._runs(series, wet=False)
    wet = CL._runs(series, wet=True)
    assert dry["length"] == 3 and dry["start"] == "2020-01-01"
    assert wet["length"] == 1 and wet["start"] == "2020-01-04"


# --- datos reales ------------------------------------------------------------
def test_series_disponibles_y_agregaciones_declaradas():
    engine = _engine()
    precip = engine.series("open_meteo_point", "precipitation")
    assert precip["aggregation"] == "sum"
    assert precip["unit"] == "mm"
    assert precip["evidence_class"] == "reanalysis"
    assert precip["n"] > 2000
    assert precip["start"].startswith("2019-01-01")
    with pytest.raises(CL.ClimateDataError):
        engine.series("open_meteo_point", "temperature")  # dos agregaciones
    tmax = engine.series("open_meteo_point", "temperature", "max")
    assert tmax["unit"] == "degC"


def test_variable_inexistente_no_se_inventa():
    engine = _engine()
    with pytest.raises(CL.ClimateDataError):
        engine.series("open_meteo_point", "solar_radiation")


def test_punto_mas_cercano_declara_distancia():
    engine = _engine()
    same = engine.nearest_point(*POINT)
    assert same["distance_km"] == 0.0
    assert same["representative"] is True
    far = engine.nearest_point(-90.0, 14.2)
    assert far["distance_km"] > 0
    assert far["distance_note"]


def test_precipitacion_anual_suma_los_dias_y_cubre_el_periodo():
    engine = _engine()
    annual = engine.annual_series("open_meteo_point", "precipitation")
    assert sorted(annual) == list(range(2019, 2026))
    for year, payload in annual.items():
        assert payload["value"] > 0
        assert 300 <= payload["n_days"] <= 366
        assert payload["complete"] is True
        assert payload["coverage"] >= 0.9


def test_climatologia_mensual_tiene_doce_meses_y_unidades():
    engine = _engine()
    climatology = engine.monthly_climatology("open_meteo_point", "precipitation")
    assert len(climatology["months"]) == 12
    assert [m["month"] for m in climatology["months"]] == list(range(1, 13))
    assert climatology["unit"] == "mm"
    assert climatology["not_a_normal"]


def test_extremos_etccdi_son_coherentes():
    engine = _engine()
    extremes = engine.extremes()
    years = extremes["years"]
    assert years
    for row in years:
        assert row["rx5day_mm"] >= row["rx1day_mm"] - 0.01
        assert row["r95p_mm"] <= row["prcptot_mm"] + 0.01
        assert 0 <= row["cdd_days"] <= 366
        assert 0 <= row["cwd_days"] <= 366
    assert extremes["r95p_threshold_mm"] > 0
    assert "ETCCDI" in extremes["reference"]


def test_rachas_secas_tienen_umbral_declarado():
    engine = _engine()
    spells = engine.dry_spells()
    assert spells["threshold_mm"] == 1.0
    assert spells["series_max_dry_days"] >= 1
    for row in spells["years"]:
        assert row["spells_ge_20d"] <= row["spells_ge_15d"] <= row["spells_ge_10d"]


def test_anomalias_se_centran_en_el_periodo():
    engine = _engine()
    anomalies = engine.anomalies()
    values = [row["anomaly_c"] for row in anomalies["years"]]
    assert all(-5 < v < 5 for v in values)
    assert abs(sum(values) / len(values)) < 1.0
    assert anomalies["thresholds"]["tmax_p95_c"] > anomalies["thresholds"]["tmin_p5_c"]


def test_sequia_es_percentil_y_no_se_presenta_como_spi():
    engine = _engine()
    drought = engine.drought_indicator()
    assert 0 <= drought["percentile"] <= 100
    assert drought["category"] in {
        "extremadamente_seco", "muy_seco", "seco", "normal",
        "humedo", "muy_humedo", "extremadamente_humedo"}
    assert "NO es el SPI" in drought["not_spi"]
    assert drought["n_windows"] > 12


def test_normales_declaran_registro_insuficiente():
    engine = _engine()
    normals = engine.normals()
    assert normals["status"] == "insufficient_record"
    assert normals["years"] < normals["wmo_requirement_years"]
    assert "no se publica una normal" in normals["note"]


def test_estacionalidad_usa_walter_lieth_y_no_inventa_temporada():
    engine = _engine()
    season = engine.seasonality()
    assert len(season["months"]) == 12
    assert season["humid_months_walter_lieth"]
    assert "MAG" in season["note"]
    assert season["top3_months_share_pct"] is not None


def test_perfil_climatico_no_interpola_ni_presenta_estaciones():
    engine = _engine()
    payload = engine.profile(*POINT)
    result = payload["result"]
    assert result["stations"]["available"] is False
    assert result["spatial_interpolation"]["applied"] is False
    assert result["forecasts"]["available"] is False
    assert result["evidence_classes_present"] == ["reanalysis"]
    assert all("reanálisis" in lim or "estación" in lim
               for lim in payload["limitations"][:2])
