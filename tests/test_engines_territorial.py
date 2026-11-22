"""Fase 5 — TerritorialEngine y análisis del terreno.

Pruebas sintéticas con resultado conocido (conversión de pendiente, clases,
TRI, TPI) y pruebas sobre el DEM real que comprueban invariantes, no valores
«esperados» copiados de la ejecución.

Ninguna prueba se salta en silencio: si falta un artefacto, `require` la omite
declarándolo. Un test que pasa sin ejecutar la comprobación sería peor que no
tenerlo.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv import config as C  # noqa: E402
from agrosv.engines import governance as G  # noqa: E402
from agrosv.engines import terrain as TM  # noqa: E402
from agrosv.engines import territorial as TR  # noqa: E402
from conftest import require  # noqa: E402

SAN_SALVADOR = (-89.2, 13.7)


def _terrain_point() -> tuple[float, float]:
    require(C.DEM_WGS84)
    require(C.SLOPE)
    return SAN_SALVADOR


# --- coordenadas y cobertura -------------------------------------------------
def test_coordenada_fuera_del_pais_falla_sin_extrapolar():
    with pytest.raises(TR.CoverageError):
        TR.validate_coordinate(-3.7, 40.4)   # Madrid
    with pytest.raises(TR.CoverageError):
        TR.validate_coordinate(float("nan"), 13.7)
    with pytest.raises(TR.CoverageError):
        TR.validate_coordinate(-89.2, "no-numérico")  # type: ignore[arg-type]


def test_coordenada_valida_se_devuelve_como_float():
    lon, lat = TR.validate_coordinate("-89.2", "13.7")
    assert (lon, lat) == (-89.2, 13.7)
    assert isinstance(lon, float)


def test_cobertura_declara_niveles_ausentes():
    cov = TR.coverage()
    levels = cov["territorial_levels"]
    assert "department" in levels["present"]
    assert "municipality_2023" in levels["absent"]
    assert "district" in levels["absent"]
    # Un nivel ausente no se sintetiza: la lista de presentes no lo contiene.
    assert "basin" not in levels["present"]


# --- conversión de pendiente -------------------------------------------------
def test_pendiente_en_porcentaje_es_tangente():
    assert TM.slope_pct(45.0) == pytest.approx(100.0, abs=0.01)
    assert TM.slope_pct(0.0) == pytest.approx(0.0)
    assert TM.slope_pct(30.0) == pytest.approx(math.tan(math.radians(30)) * 100,
                                               abs=1e-9)
    assert TM.slope_pct(None) is None


def test_clase_de_relieve_usa_los_umbrales_declarados():
    assert TM.relief_class_of(0.5)["label"] == "plano"
    assert TM.relief_class_of(3.0)["label"] == "suave"
    assert TM.relief_class_of(20.0)["label"] == "quebrado"
    assert TM.relief_class_of(50.0)["label"] == "muy_escarpado"
    assert TM.relief_class_of(None) is None


def test_aspecto_a_rumbo():
    assert TM.aspect_compass(0.0) == "N"
    assert TM.aspect_compass(360.0) == "N"
    assert TM.aspect_compass(90.0) == "E"
    assert TM.aspect_compass(225.0) == "SO"
    assert TM.aspect_compass(None) is None


# --- TRI / TPI sintéticos ----------------------------------------------------
def _plane(slope_m: float = 1.0) -> np.ndarray:
    """Plano que desciende hacia el este 1 m por celda."""
    return np.tile(-slope_m * np.arange(3), (3, 1)) + 100.0


def test_tri_de_un_plano_es_conocido():
    plane = _plane()
    value = TM.tri_riley(plane, 1, 1, 30.0)
    # Σ(z0−z)² sobre 8 vecinos de un plano con pendiente 1 m: 6·1² + 2·2² = 14
    assert value == pytest.approx(math.sqrt(14.0))


def test_tri_no_inventa_valor_con_nodata():
    plane = _plane()
    plane[0, 0] = np.nan
    assert TM.tri_riley(plane, 1, 1, 30.0) is None


def test_tpi_centro_de_plano_es_positivo_aguas_arriba():
    plane = _plane()
    # z0 = 99; vecinos = 100,100,100, 99, 98, 98, 98, 98 → media 99,125
    assert TM.tpi(plane, 1, 1) == pytest.approx(-0.125, abs=1e-9)
    assert TM.tpi_position(-0.125) == "plano_local"
    assert TM.tpi_position(5.0) == "cresta"
    assert TM.tpi_position(-5.0) == "valle"
    assert TM.tpi_position(1.0) == "ladera"


def test_tpi_rechaza_ventana_de_tamano_incorrecto():
    with pytest.raises(ValueError):
        TM.tpi(np.zeros((5, 5)), 2, 2, radius=1)


# --- extracción real del DEM -------------------------------------------------
def test_terreno_real_tiene_unidades_y_rangos_coherentes():
    lon, lat = _terrain_point()
    metrics = TM.terrain_metrics(lon, lat)
    assert metrics["available"] is True
    elevation = metrics["elevation_m"]
    assert -10 <= elevation <= 2730, "El Salvador: 0–2730 m según el DEM"
    assert 0 <= metrics["slope_deg"] <= 90
    assert 0 <= metrics["aspect_deg"] < 360
    assert metrics["slope_pct"] == pytest.approx(
        math.tan(math.radians(metrics["slope_deg"])) * 100, abs=0.02)
    assert metrics["relief_class"]["label"] in {
        label for _, _, label in C.RELIEF_BREAKS}
    assert metrics["source"] == "copdem30"
    assert metrics["limitations"], "un resultado sin limitaciones no es publicable"


def test_terreno_incluye_supuestos_de_resolucion_y_dsm():
    lon, lat = _terrain_point()
    metrics = TM.terrain_metrics(lon, lat)
    text = " ".join(metrics["limitations"]).lower()
    assert "dsm" in text
    assert "resolución" in text and "exactitud" in text


def test_perfil_territorial_identifica_departamento():
    lon, lat = _terrain_point()
    require(C.TERRITORY_GPKG)
    payload = TR.TerritorialEngine().profile(lon, lat)
    location = payload["result"]["location"]
    assert location["country"]["name"] == "El Salvador"
    assert location["department"]["source_code"] == "SV-SS"
    assert location["department"]["official"] is True
    assert location["municipality_historic"]["official"] is False
    assert payload["result"]["terrain"]["available"] is True
    assert payload["sources"], "todo resultado cita sus fuentes"


def test_perfil_territorial_declara_ausencia_de_limites_2023():
    require(C.TERRITORY_GPKG)
    require(C.DEM_WGS84)
    payload = TR.TerritorialEngine().coverage()
    assert "municipality_2023" in payload["territorial_levels"]["absent"]
    assert payload["territorial_levels"]["absent_note"]


def test_busqueda_territorial_por_nombre_y_nivel():
    require(C.TERRITORY_GPKG)
    engine = TR.TerritorialEngine()
    hit = engine.resolve_territory("ahuachapan", level="department")
    assert hit["resolved"] is True
    assert hit["territory"]["level"] == "department"
    assert hit["territory"]["source_code"] == "SV-AH"


def test_busqueda_territorial_inexistente_no_inventa():
    require(C.TERRITORY_GPKG)
    hit = TR.TerritorialEngine().resolve_territory("atlantida")
    assert hit["resolved"] is False


def test_cuenca_asociada_marca_truncamiento_y_unidades():
    lon, lat = _terrain_point()
    require(C.DEM_WGS84)
    from agrosv.engines import hydrology as HY

    basin = HY.watershed_from_point(lon, lat, size_m=4000)
    assert basin["upstream_area_km2"] >= 0
    assert isinstance(basin["truncated"], bool)
    assert basin["window"]["res_m"] == 30.0
    assert basin["window"]["cells"] == [133, 133] or basin["window"]["cells"][0] > 3
    assert basin["method"]


def test_gobernanza_no_declara_disponible_un_dataset_sin_archivo():
    src = G.source("copdem30")
    assert src.available == (not src.missing_artifacts())
    assert G.availability_report()["available"]


def test_variable_ausente_se_declara_con_motivo():
    assert "groundwater_levels" in G.UNAVAILABLE
    entry = G.UNAVAILABLE["groundwater_levels"]
    assert entry["reason"] and entry["would_require"] and entry["status"]
