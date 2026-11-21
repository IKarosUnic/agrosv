"""Módulo 1 — integridad, cobertura y geometrías del territorio."""
from __future__ import annotations

import pytest

from agrosv import config as C

ISO_CODES = {
    "SV-AH", "SV-CA", "SV-CH", "SV-CU", "SV-LI", "SV-MO", "SV-PA",
    "SV-SA", "SV-SM", "SV-SO", "SV-SS", "SV-SV", "SV-UN", "SV-US",
}


def test_departamentos_completos(territory):
    assert len(territory) == 14
    assert set(territory["adm1_code"]) == ISO_CODES
    assert territory["adm1_code"].is_unique


def test_crs_documentado(territory, territory_meta):
    assert territory.crs.to_string() == C.CRS_STORAGE
    assert territory_meta["crs"] == C.CRS_STORAGE
    assert territory_meta["area_crs"] == C.CRS_EQUAL_AREA


def test_geometrias_validas_y_no_vacias(territory):
    assert territory.geometry.is_valid.all()
    assert (~territory.geometry.is_empty).all()
    assert territory.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all()


def test_area_nacional_dentro_de_tolerancia(territory):
    import geopandas as gpd

    area = float(gpd.GeoSeries([territory.union_all()], crs=C.CRS_STORAGE)
                 .to_crs(C.CRS_EQUAL_AREA).area.sum()) / 1e6
    rel = abs(area - C.SV_AREA_KM2_REF) / C.SV_AREA_KM2_REF
    assert rel < C.SV_AREA_TOLERANCE, f"área {area:,.1f} km² (desvío {rel:.2%})"
    # El ADM0 original incluye aguas territoriales; el derivado no.
    assert area < 22000


def test_sin_solapes_entre_departamentos(territory):
    geoms = list(territory.geometry)
    for i in range(len(geoms)):
        for j in range(i + 1, len(geoms)):
            inter = geoms[i].intersection(geoms[j])
            assert inter.area < 1e-8, f"solape {i}-{j}: {inter.area}"


def test_adm2_es_historico_y_etiquetado(territory_meta):
    adm2 = territory_meta["levels"]["adm2"]
    assert adm2["official"] is False
    assert 260 <= adm2["count"] <= 280


def test_adm2_sin_huecos_de_departamento(territory_meta):
    adm2 = territory_meta["levels"]["adm2"]
    assert adm2["coverage_of_national"] >= 0.95
    assert adm2["uncovered_note"]


def test_identificadores_estables(territory):
    for _, row in territory.iterrows():
        assert row["adm1_code"].startswith("SV-")
        assert len(row["adm1_code"]) == 5
        slug = row.get("slug")
        if slug is not None:
            assert slug == slug.strip() and " " not in slug


def test_manifiesto_de_procedencia():
    from agrosv.provenance import read_manifest

    m = read_manifest(C.TERRITORY_GPKG)
    assert m is not None
    assert m["license"] == "CC-BY-SA-2.0"
    assert len(m["artifact_sha256"]) == 64
    assert m["software"]["gdal"]
