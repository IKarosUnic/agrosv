"""Fase 5 — integración de motores, API y cobertura geográfica.

Cubre lo que los módulos por motor no cubren:

* perfil ambiental en cuatro regiones distintas de El Salvador;
* consistencia de unidades, CRS y procedencia en la respuesta final;
* reglas de interacción, incluidas las que declaran una ausencia;
* endpoints `/api/engines` con sus códigos de error;
* caché derivado sin escribir en el repositorio;
* umbrales de rendimiento medidos (holgados, para no ser frágiles).

Las pruebas se OMITEN si falta el artefacto correspondiente (`require`), nunca
pasan en falso.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv import config as C  # noqa: E402
from agrosv.engines import cache as CACHE  # noqa: E402
from agrosv.engines import climate as CL  # noqa: E402
from agrosv.engines import environmental as EN  # noqa: E402
from agrosv.engines import governance as G  # noqa: E402
from agrosv.engines import hydrology as HY  # noqa: E402
from agrosv.engines import soil as SL  # noqa: E402
from agrosv.engines import terrain as TM  # noqa: E402
from agrosv.engines import territorial as TR  # noqa: E402
from conftest import require  # noqa: E402

#: Cuatro regiones: extremo occidental, valle central, nororiente y oriente.
REGIONS: dict[str, tuple[float, float]] = {
    "occidental": (-89.85, 13.85),   # Ahuachapán
    "central": (-89.20, 13.70),      # San Salvador
    "nororiental": (-88.95, 14.20),  # Chalatenango
    "oriental": (-87.90, 13.35),     # La Unión
}


def _require_stack() -> None:
    require(C.DEM_WGS84)
    require(C.SLOPE)
    require(C.ASPECT)
    require(C.RELIEF_CLASS)
    require(C.TERRITORY_GPKG)
    require(C.INFRA_GPKG)
    for spec in SL.SOIL_VARIABLES.values():
        require(C.SOILS_RASTER_DIR / spec["file"])
    require(CL.DB_PATH)


@pytest.fixture(scope="module")
def profiles() -> dict[str, dict]:
    _require_stack()
    engine = EN.EnvironmentalInteractionEngine()
    return {name: engine.profile(lon, lat, size_m=3000, use_cache=False)
            for name, (lon, lat) in REGIONS.items()}


# --- perfil ambiental ---------------------------------------------------------
def test_perfil_ambiental_cubre_cuatro_regiones(profiles):
    assert set(profiles) == set(REGIONS)
    for name, payload in profiles.items():
        assert payload["engine"] == "environmental"
        assert payload["engine_version"] == G.ENGINE_VERSION
        for key in ("result", "sources", "coverage", "limitations",
                    "processing_history", "conventions"):
            assert key in payload, f"{name}: falta {key}"
        assert payload["limitations"], "un resultado sin limitaciones no se publica"


def test_perfil_ambiental_no_inventa_errores_de_componente(profiles):
    for name, payload in profiles.items():
        errors = payload["result"]["component_errors"]
        assert errors == {}, f"{name}: componentes fallidos {errors}"
        assert payload["result"]["terrain"]["available"] is True
        assert payload["result"]["identification"]["department"]


def test_perfil_ambiental_no_publica_puntuacion(profiles):
    for payload in profiles.values():
        result = payload["result"]
        for forbidden in ("score", "index", "suitability", "environmental_index"):
            assert forbidden not in result
        assert "no produce una" in result["environmental_profile_rule"]


def test_perfil_ambiental_declara_ausencias(profiles):
    for payload in profiles.values():
        result = payload["result"]
        assert result["hydrology"]["groundwater"]["available"] is False
        assert result["climate"]["result"]["stations"]["available"] is False
        coverage = result["data_coverage"]
        assert coverage["groundwater"]["available"] is False
        codes = {c["code"] for c in result["environmental_constraints"]}
        # La profundidad de suelo no existe: la regla de ausencia debe ejecutarse.
        assert "sin_dato_de_profundidad" in codes


def test_perfil_ambiental_conserva_procedencia(profiles):
    for payload in profiles.values():
        assert payload["sources"]
        classes = set()
        for source in payload["sources"]:
            for key in ("dataset_id", "source_url", "license", "data_class",
                        "spatial_resolution", "temporal_coverage", "version"):
                assert key in source, f"falta {key} en {source.get('dataset_id')}"
            assert source["source_url"].startswith("http")
            classes.add(source["data_class"])
        assert "reanalysis" in classes
        assert "modeled_prediction" in classes


def test_perfil_ambiental_conserva_incertidumbre(profiles):
    for payload in profiles.values():
        uncertainty = payload["result"]["uncertainty"]
        assert uncertainty["aggregate"]["quantified"] is False
        for component in ("terrain", "soil", "climate", "hydrology"):
            assert uncertainty[component]["evidence_class"]
            assert uncertainty[component]["confidence"] == "baja"


def test_perfil_ambiental_es_reproducible_en_lo_fisico(profiles):
    """Dos regiones distintas no pueden producir el mismo terreno."""
    elevations = {name: p["result"]["terrain"]["elevation_m"]
                  for name, p in profiles.items()}
    assert len(set(elevations.values())) == len(elevations), elevations


# --- unidades y CRS ----------------------------------------------------------
def test_unidades_del_terreno_son_coherentes(profiles):
    for payload in profiles.values():
        terrain = payload["result"]["terrain"]
        if terrain.get("slope_deg") is not None:
            assert terrain["slope_pct"] == pytest.approx(
                math.tan(math.radians(terrain["slope_deg"])) * 100, abs=0.05)
        assert terrain["elevation_m"] is not None
        assert payload["conventions"]["crs_query"] == C.CRS_STORAGE


def test_unidades_del_suelo_suman_cien(profiles):
    for payload in profiles.values():
        props = payload["result"]["soil"]["properties"]
        if not props["clay"]["available"]:
            continue
        total = (props["clay"]["value"] + props["sand"]["value"]
                 + props["silt"]["value"])
        assert 95 <= total <= 105
        assert props["clay"]["unit"] == "%"
        assert props["soil_organic_carbon"]["unit"] == "g kg-1"


def test_areas_hidrologicas_no_exceden_la_ventana(profiles):
    for payload in profiles.values():
        basin = payload["result"]["hydrology"]["watershed"]
        if basin is None:
            continue
        window_km2 = (basin["window"]["size_m"] ** 2) / 1e6
        assert 0 <= basin["upstream_area_km2"] <= window_km2 + 1e-6
        assert basin["window"]["res_m"] == 30.0


def test_crs_ida_y_vuelta_es_estable():
    from pyproj import Transformer

    forward = Transformer.from_crs(C.CRS_STORAGE, C.CRS_METRIC, always_xy=True)
    back = Transformer.from_crs(C.CRS_METRIC, C.CRS_STORAGE, always_xy=True)
    lon, lat = -89.2, 13.7
    x, y = forward.transform(lon, lat)
    lon2, lat2 = back.transform(x, y)
    assert abs(lon2 - lon) < 1e-9 and abs(lat2 - lat) < 1e-9


def test_area_de_el_salvador_coincide_con_la_referencia():
    require(C.TERRITORY_GPKG)
    location = TR.locate(-89.2, 13.7)
    country = location.country
    assert country is not None
    error = abs(country["area_km2"] - C.SV_AREA_KM2_REF) / C.SV_AREA_KM2_REF
    assert error <= C.SV_AREA_TOLERANCE


# --- reglas de interacción ---------------------------------------------------
def test_reglas_de_interaccion_cruzan_dominios():
    values = {"slope_deg": 30.0, "clay": 10.0}
    codes = {c["code"] for c in EN.apply_interaction_rules(values)}
    assert "erosion_pendiente_textura" in codes
    for finding in EN.apply_interaction_rules(values):
        assert finding["domains"] and finding["implication"]
        assert finding["validated"] is False


def test_reglas_no_inventan_si_falta_un_insumo():
    # Las reglas numéricas no se ejecutan sin sus entradas; solo pueden
    # aparecer hallazgos que declaran una ausencia del repositorio.
    for values in ({}, {"slope_deg": 30.0}, {"clay": 40.0}):
        findings = EN.apply_interaction_rules(values)
        assert [f for f in findings if not f["declares_absence"]] == []


def test_regla_de_ausencia_se_ejecuta_con_none():
    findings = EN.apply_interaction_rules({"soil_depth_cm": None})
    codes = {f["code"] for f in findings}
    assert "sin_dato_de_profundidad" in codes
    assert all(f["declares_absence"] for f in findings)


def test_indice_compuesto_se_rechaza():
    with pytest.raises(EN.CompositeIndicatorError):
        EN.EnvironmentalInteractionEngine().composite_indicator()


# --- consultas territoriales -------------------------------------------------
def test_perfil_por_identificador_oficial_usa_punto_interior():
    require(C.TERRITORY_GPKG)
    require(C.DEM_WGS84)
    payload = TR.TerritorialEngine().profile_by_territory(
        "SV-AH", level="department", radius_cells=1, size_m=3000)
    selection = payload["result"]["territory_selection"]
    assert selection["official"] is True
    assert selection["source_code"] == "SV-AH"
    assert payload["query"]["territory_query"] == "SV-AH"
    assert "no es un agregado areal" in payload["limitations"][-1]
    lon = selection["evaluation_point"]["lon"]
    lat = selection["evaluation_point"]["lat"]
    assert payload["result"]["location"]["department"]["source_code"] == "SV-AH"


def test_identificador_inexistente_no_se_inventa():
    require(C.TERRITORY_GPKG)
    payload = TR.TerritorialEngine().profile_by_territory("Atlantida")
    assert payload["resolved"] is False


def test_interseccion_y_contencion_de_rectangulo():
    require(C.TERRITORY_GPKG)
    # Rectángulo de ~2×2 km dentro de San Salvador: un solo departamento lo
    # contiene por completo.
    payload = TR.territories_in_bbox(-89.168, 13.760, -89.148, 13.780,
                                     level="department")
    assert payload["count"] >= 1
    containing = [t for t in payload["territories"] if t["contains_query_bbox"]]
    assert len(containing) == 1
    assert containing[0]["source_code"] == "SV-SS"
    assert payload["limitations"]


def test_rectangulo_invalido_falla():
    with pytest.raises(TR.CoverageError):
        TR.territories_in_bbox(-89.0, 13.7, -89.2, 13.6)


def test_oceano_dentro_del_bbox_se_declara_fuera_de_tierra():
    # Al sur de la costa, dentro del rectángulo nacional.
    location = TR.locate(-89.50, 12.99)
    assert location.inside_bbox is True
    assert location.inside_land is False


def test_consulta_por_profundidad_declara_lo_ausente():
    require(C.SOILS_RASTER_DIR / "clay_0-30cm.tif")
    engine = SL.SoilEngine()
    available = engine.profile_at_depth(-88.6, 13.4, top_cm=0, bottom_cm=30)
    assert available["available"] is True
    assert available["interval_cm"] == [0, 30]
    missing = engine.profile_at_depth(-88.6, 13.4, top_cm=0, bottom_cm=15)
    assert missing["available"] is False
    assert missing["nearest_available_interval_cm"] == [0, 30]
    with pytest.raises(ValueError):
        engine.profile_at_depth(-88.6, 13.4, top_cm=40, bottom_cm=10)


# --- caché derivado ----------------------------------------------------------
def test_cache_es_direccionado_por_contenido(tmp_path):
    cache = CACHE.DerivedCache(tmp_path)
    calls = {"n": 0}

    def build() -> dict:
        calls["n"] += 1
        return {"value": calls["n"]}

    first, info1 = cache.get_or_compute(engine="demo", version="1",
                                        params={"a": 1}, paths=[],
                                        build=build)
    second, info2 = cache.get_or_compute(engine="demo", version="1",
                                         params={"a": 1}, paths=[],
                                         build=build)
    other, info3 = cache.get_or_compute(engine="demo", version="1",
                                        params={"a": 2}, paths=[],
                                        build=build)
    assert first["value"] == 1 and second["value"] == 1
    assert info1.hit is False and info2.hit is True
    assert other["value"] == 2 and info3.hit is False
    assert info1.key != info3.key
    assert calls["n"] == 2


def test_cache_corrupto_se_recalcula(tmp_path):
    cache = CACHE.DerivedCache(tmp_path)
    payload, info = cache.get_or_compute(engine="demo", version="1",
                                         params={}, paths=[],
                                         build=lambda: {"ok": True})
    Path(info.path).write_text("{no es json", encoding="utf-8")
    payload2, info2 = cache.get_or_compute(engine="demo", version="1",
                                           params={}, paths=[],
                                           build=lambda: {"ok": True})
    assert payload2 == {"ok": True} and info2.hit is False


def test_motor_respeta_use_cache_false():
    require(C.DEM_WGS84)
    engine = HY.HydrologyEngine()
    first = engine.profile(*REGIONS["central"], size_m=3000, use_cache=False)
    second = engine.profile(*REGIONS["central"], size_m=3000, use_cache=False)
    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is False
    assert first["cache"]["key"] == second["cache"]["key"]
    assert first["result"]["watershed"]["upstream_area_km2"] == \
        second["result"]["watershed"]["upstream_area_km2"]


# --- API ---------------------------------------------------------------------
def test_api_meta_y_cobertura(client):
    meta = client.get("/api/engines/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert body["service_version"] == G.ENGINE_VERSION
    assert "no_composite_index" in body["policies"]
    assert meta.headers["X-AGROSV-Engine"] == "agrosv"

    coverage = client.get("/api/engines/coverage")
    assert coverage.status_code == 200
    assert coverage.json()["climate"]["points"]
    assert coverage.json()["hydrology"]["groundwater"] == "no disponible"


def test_api_datasets_y_ficha(client):
    listing = client.get("/api/engines/datasets").json()
    assert listing["count"] >= 6
    assert "copdem30" in listing["available"]
    assert "groundwater_levels" in listing["unavailable_variables"]

    ficha = client.get("/api/engines/datasets/soilgrids_2")
    assert ficha.status_code == 200
    assert ficha.json()["license"] == "CC BY 4.0"
    assert ficha.json()["data_class"] == "modeled_prediction"

    assert client.get("/api/engines/datasets/inexistente").status_code == 404


def test_api_terreno_valido_y_fuera_de_cobertura(client):
    ok = client.get("/api/engines/terrain", params={"lat": 13.7, "lon": -89.2})
    assert ok.status_code == 200
    assert ok.json()["result"]["terrain"]["available"] is True

    bad = client.get("/api/engines/terrain", params={"lat": 40.4, "lon": -3.7})
    assert bad.status_code == 400
    assert "El Salvador" in bad.json()["detail"]


def test_api_perfiles_principales(client):
    for endpoint in ("territorial", "soil", "hydrology", "climate",
                     "environmental"):
        response = client.get(f"/api/engines/{endpoint}",
                              params={"lat": 13.7, "lon": -89.2,
                                      "size_m": 3000} if endpoint in
                              ("hydrology", "environmental") else
                              {"lat": 13.7, "lon": -89.2})
        assert response.status_code == 200, (endpoint, response.text[:200])
        body = response.json()
        assert body["engine"] == endpoint
        assert body["sources"]
        assert body["limitations"]


def test_api_suelo_por_profundidad(client):
    ok = client.get("/api/engines/soil/profile",
                    params={"lat": 13.4, "lon": -88.6, "top_cm": 0,
                            "bottom_cm": 30})
    assert ok.status_code == 200
    assert ok.json()["available"] is True

    absent = client.get("/api/engines/soil/profile",
                        params={"lat": 13.4, "lon": -88.6, "top_cm": 0,
                                "bottom_cm": 15})
    assert absent.status_code == 200
    assert absent.json()["available"] is False


def test_api_busqueda_y_perfil_territorial(client):
    search = client.get("/api/engines/territory/search",
                        params={"q": "ahuachapan", "level": "department"})
    assert search.status_code == 200
    assert search.json()["territory"]["source_code"] == "SV-AH"

    profile = client.get("/api/engines/territory/profile",
                         params={"q": "SV-SS", "radius_cells": 1,
                                 "size_m": 3000})
    assert profile.status_code == 200
    assert profile.json()["result"]["territory_selection"]["source_code"] == "SV-SS"

    missing = client.get("/api/engines/territory/search",
                         params={"q": "Atlantida"})
    assert missing.status_code == 200
    assert missing.json()["resolved"] is False


def test_api_interseccion_territorial(client):
    response = client.get("/api/engines/territory/intersect",
                          params={"west": -89.168, "south": 13.760,
                                  "east": -89.148, "north": 13.780,
                                  "level": "department"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert any(t["contains_query_bbox"] for t in body["territories"])

    invalid = client.get("/api/engines/territory/intersect",
                         params={"west": -89.0, "south": 13.7,
                                 "east": -89.2, "north": 13.6})
    assert invalid.status_code == 400


def test_api_cache(client):
    response = client.get("/api/engines/cache")
    assert response.status_code == 200
    body = response.json()
    assert "path" in body and "entries" in body


# --- rendimiento -------------------------------------------------------------
def test_rendimiento_de_un_perfil_completo(profiles):
    """Umbral holgado: detecta una regresión grave, no mide la máquina."""
    engine = EN.EnvironmentalInteractionEngine()
    start = time.perf_counter()
    engine.profile(*REGIONS["central"], size_m=3000, use_cache=False)
    elapsed = time.perf_counter() - start
    assert elapsed < 20.0, f"perfil ambiental demasiado lento: {elapsed:.2f}s"


def test_rendimiento_de_interseccion_nacional():
    require(C.TERRITORY_GPKG)
    start = time.perf_counter()
    payload = TR.territories_in_bbox(*C.SV_BOUNDS)
    elapsed = time.perf_counter() - start
    assert payload["count"] == 287, payload["count"]
    assert elapsed < 10.0, f"intersección nacional demasiado lenta: {elapsed:.2f}s"


def test_extraccion_por_ventana_no_carga_el_pais():
    """Una ventana de 3 km debe leer pocas celdas, no el ráster nacional."""
    require(C.DEM_WGS84)
    window = HY.dem_window_metric(*REGIONS["central"], size_m=3000)
    assert window.shape == (100, 100)
    assert window.nodata_share == 0.0
