"""Módulo 3 — capas OSM: integridad, licencia y coherencia espacial."""
from __future__ import annotations

import geopandas as gpd
import pytest

from agrosv import config as C
from conftest import require

LAYERS = ["roads", "waterways", "water_bodies", "settlements",
          "infrastructure", "power_lines"]


@pytest.mark.parametrize("layer", LAYERS)
def test_capa_existe_y_tiene_datos(layer, infra_stats):
    require(C.INFRA_GPKG)
    gdf = gpd.read_file(C.INFRA_GPKG, layer=layer, rows=5)
    assert len(gdf) > 0
    assert gdf.crs.to_string() == C.CRS_STORAGE
    assert infra_stats["layers"][layer]["features"] > 0


@pytest.mark.parametrize("layer", LAYERS)
def test_sin_ids_duplicados(layer):
    require(C.INFRA_GPKG)
    gdf = gpd.read_file(C.INFRA_GPKG, layer=layer, columns=["osm_id"])
    assert gdf["osm_id"].notna().all()
    assert gdf["osm_id"].is_unique


def test_geometrias_validas_y_no_vacias():
    require(C.INFRA_GPKG)
    for layer in ("roads", "waterways", "water_bodies"):
        gdf = gpd.read_file(C.INFRA_GPKG, layer=layer)
        assert gdf.geometry.is_valid.all(), layer
        assert (~gdf.geometry.is_empty).all(), layer


def test_todo_dentro_del_pais():
    require(C.INFRA_GPKG)
    terr = gpd.read_file(C.TERRITORY_GPKG, layer="adm1")
    national = terr.union_all().buffer(1e-6)
    for layer in ("roads", "waterways", "water_bodies", "settlements"):
        gdf = gpd.read_file(C.INFRA_GPKG, layer=layer, rows=3000)
        assert gdf.geometry.intersects(national).all(), layer


def test_longitudes_plausibles(infra_stats):
    km = infra_stats["road_km_by_class"]
    assert infra_stats["road_km_total"] > 10_000
    assert km["arterial"] < km["local"]
    assert 5_000 <= infra_stats["road_km_main_network"] <= 15_000
    assert 2_000 <= infra_stats["layers"]["waterways"]["length_km"] <= 40_000


def test_cuerpos_de_agua_plausibles(infra_stats):
    area = infra_stats["layers"]["water_bodies"]["area_km2"]
    assert 100 <= area <= 2000
    types = infra_stats["water_types"]
    assert sum(types.values()) == infra_stats["layers"]["water_bodies"]["features"]
    assert any(types.get(k, 0) > 0 for k in ("lake", "reservoir", "lagoon", "river"))


def test_asentamientos_suficientes(infra_stats):
    assert infra_stats["layers"]["settlements"]["features"] >= 200
    assert infra_stats["settlement_types"].get("city", 0) >= 10


def test_licencia_odbl_documentada():
    from agrosv.provenance import read_manifest

    m = read_manifest(C.INFRA_GPKG)
    assert m is not None
    assert m["license"] == "ODbL-1.0"
    assert "OpenStreetMap" in m["attribution"]
    assert len(m["extra"]["pbf_sha256"]) == 64


def test_estadisticas_coherentes_con_el_archivo(infra_stats):
    gdf = gpd.read_file(C.INFRA_GPKG, layer="settlements", columns=["osm_id"])
    assert len(gdf) == infra_stats["layers"]["settlements"]["features"]
