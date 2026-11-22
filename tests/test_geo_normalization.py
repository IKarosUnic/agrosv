"""Normalización geoespacial: CRS, métricas y geometrías."""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.data import geo  # noqa: E402


def gdf(polygons, crs="EPSG:4326") -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"name": [f"u{i}" for i in range(len(polygons))]},
                            geometry=polygons, crs=crs)


def test_crs_info_describe_sin_transformar():
    info = geo.crs_info("EPSG:4326")
    assert info["is_geographic"] is True
    assert info["epsg"] == 4326
    assert geo.crs_info("EPSG:32616")["is_projected"] is True


def test_transformacion_conserva_crs_original():
    source = gdf([box(-89.2, 13.6, -89.1, 13.7)])
    out = geo.transform_vector(source, "EPSG:32616",
                               reason="cálculo métrico", purpose="distance")
    assert str(out.crs) == "EPSG:32616"
    assert out["_crs_source"].iloc[0] == "EPSG:4326"
    assert out.attrs["crs_original"] == "EPSG:4326"
    assert out.attrs["transform_record"]["preserved_original"] is True
    assert str(source.crs) == "EPSG:4326", "la entrada no se modifica"


def test_area_en_grados_se_rechaza():
    source = gdf([box(-89.2, 13.6, -89.1, 13.7)])
    with pytest.raises(geo.GeographicMetricError):
        geo.area_km2(source, equal_area_crs="EPSG:4326")
    with pytest.raises(geo.GeographicMetricError):
        geo.transform_vector(source, "EPSG:4326", reason="x", purpose="area")


def test_area_equivalente_tiene_sentido_fisico():
    source = gdf([box(0, 0, 1, 1)])
    area = float(geo.area_km2(source).iloc[0])
    assert 11_000 < area < 13_500, f"un grado² en el ecuador ≈ 12.364 km², no {area}"
    assert geo.area_km2(source).iloc[0] != pytest.approx(
        float(source.geometry.area.iloc[0]))


def test_distancia_geografica_se_rechaza():
    with pytest.raises(geo.GeographicMetricError):
        geo.distance_m(Point(0, 0), Point(1, 0), crs="EPSG:4326")
    assert geo.distance_m(Point(500_000, 1_000_000),
                          Point(500_030, 1_000_000),
                          crs="EPSG:32616") == pytest.approx(30.0)


def test_geometria_autointersectada_se_detecta():
    bowtie = box(0, 0, 1, 1).union(Point(0.5, 0.5)).buffer(0)
    invalid = gpd.GeoSeries.from_wkt(
        ["POLYGON ((0 0, 1 1, 1 0, 0 1, 0 0))"], crs="EPSG:4326")
    frame = gpd.GeoDataFrame({"name": ["bowtie"]}, geometry=invalid)
    report = geo.validate_geometries(frame)
    assert report.ok is False
    assert report.checks["geometrias_invalidas"]["count"] == 1
    assert report.checks["autointersecciones"]["count"] == 1
    assert bowtie.is_valid  # el control no tocó la geometría original


def test_duplicados_y_fuera_de_cobertura():
    same = box(-89.2, 13.6, -89.1, 13.7)
    far = box(-70.0, 5.0, -69.9, 5.1)
    frame = gdf([same, same, far])
    report = geo.validate_geometries(frame, bounds=(-90.2, 12.9, -87.6, 14.5))
    assert report.checks["duplicados_geometricos"]["count"] == 1
    assert report.checks["fuera_de_cobertura"]["count"] == 1


def test_solapamiento_entre_unidades_se_informa():
    frame = gdf([box(0, 0, 1, 1), box(0.5, 0, 1.5, 1)])
    report = geo.validate_geometries(frame)
    assert report.checks["solapamientos_topologicos"]["count"] == 1
    assert report.checks["solapamientos_topologicos"]["severity"] == "warning"


def test_reparacion_registrada_conserva_hash_y_area(tmp_path):
    invalid = gpd.GeoSeries.from_wkt(
        ["POLYGON ((0 0, 1 1, 1 0, 0 1, 0 0))"], crs="EPSG:4326")
    frame = gpd.GeoDataFrame({"name": ["bowtie"]}, geometry=invalid)
    original = tmp_path / "original.geojson"
    frame.to_file(original, driver="GeoJSON")
    repaired, log = geo.repair_geometries(
        frame, method="make_valid", original_file=original,
        backup_path=tmp_path / "backup.geojson")
    assert repaired.geometry.iloc[0].is_valid
    assert log.repaired_count == 1
    assert log.original_sha256
    op = log.operations[0]
    assert op["geometry_hash_before"] != op["geometry_hash_after"]
    assert "area_change_pct" in op
    assert repaired["geom_repaired"].iloc[0]
    assert (tmp_path / "backup.geojson").exists()
    assert not frame.geometry.iloc[0].is_valid, "el original no se modifica"


def test_reparacion_sin_crs_se_rechaza():
    frame = gpd.GeoDataFrame({"name": ["x"]}, geometry=[
        gpd.GeoSeries.from_wkt(["POLYGON ((0 0, 1 1, 1 0, 0 1, 0 0))"]).iloc[0]])
    with pytest.raises(geo.CRSConversionError):
        geo.repair_geometries(frame)


def test_eleccion_de_crs_metrico_documentada():
    local = geo.choose_metric_crs((-89.3, 13.6, -89.1, 13.8))
    assert local["equal_area"] is False
    assert local["epsg"] in (32615, 32616)
    national = geo.choose_metric_crs((-90.18, 12.98, -87.64, 14.45))
    assert national["epsg"] == 6933
    assert national["equal_area"] is True
    assert "área" in national["scale_note"]


def test_union_y_solapamiento_agregado():
    frame = gdf([box(0, 0, 1, 1), box(0.5, 0, 1.5, 1)])
    coverage = geo.coverage_union(frame)
    assert coverage["sum_area_km2"] > coverage["union_area_km2"]
    assert coverage["overlap_area_km2"] > 0


def test_capa_sin_crs_no_se_reproyecta():
    frame = gpd.GeoDataFrame({"name": ["x"]}, geometry=[box(0, 0, 1, 1)])
    with pytest.raises(geo.CRSConversionError):
        geo.transform_vector(frame, "EPSG:32616", reason="x")
