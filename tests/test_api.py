"""Módulo 5 — endpoints: contrato, errores y contenido."""
from __future__ import annotations

import math

import pytest


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok", body
    assert body["missing"] == []


def test_meta_declara_fuentes_y_licencias(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    m = r.json()
    for key in ("territory", "topography", "infrastructure", "soils"):
        assert key in m["datasets"]
    assert m["datasets"]["infrastructure"]["license"] == "ODbL 1.0"
    assert m["datasets"]["soils"]["license"] == "CC BY 4.0"
    assert m["datasets"]["territory"]["adm2_official"] is False


def test_departamentos_geojson(client):
    r = client.get("/api/territory/departments")
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 14
    props = fc["features"][0]["properties"]
    assert {"adm1_code", "name", "area_km2"} <= set(props)
    # la respuesta por defecto se simplifica para gama baja
    assert len(r.content) < 400_000


def test_un_departamento(client):
    r = client.get("/api/territory/departments/SV-SS")
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == "SV-SS"
    assert d["name"].lower().startswith("san salvador")
    assert d["area_km2"] > 0
    assert "elev_max_m" in d["topography"]
    assert d["soils"]["phh2o"] is not None


def test_departamento_inexistente(client):
    assert client.get("/api/territory/departments/SV-ZZ").status_code == 404


def test_municipios_marcados_como_historicos(client):
    r = client.get("/api/territory/municipalities", params={"department": "SV-SS"})
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["official"] is False
    assert len(body["features"]) > 0


def test_elevacion_en_san_salvador(client):
    r = client.get("/api/topography/elevation",
                   params={"lat": 13.6929, "lon": -89.2182})
    assert r.status_code == 200
    d = r.json()
    assert 400 <= d["elevation_m"] <= 1500
    assert 0 <= d["slope_deg"] <= 90
    assert d["aspect_deg"] is None or 0 <= d["aspect_deg"] < 360


def test_coordenada_fuera_del_pais(client):
    r = client.get("/api/topography/elevation",
                   params={"lat": 40.4, "lon": -3.7})
    assert r.status_code == 400


def test_suelo_puntual(client):
    r = client.get("/api/soils/point", params={"lat": 13.85, "lon": -89.35})
    assert r.status_code == 200
    d = r.json()
    assert 3 <= d["phh2o"] <= 10
    assert d["clay"] + d["sand"] + d["silt"] == pytest.approx(100, abs=3)
    assert "laboratorio" in d["disclaimer"]


def test_resumen_de_infraestructura(client):
    r = client.get("/api/infrastructure/summary")
    assert r.status_code == 200
    d = r.json()
    assert d["layers"]["roads"]["features"] > 1000
    assert d["source"]["osm_timestamp"]


def test_capa_osm_por_bbox(client):
    r = client.get("/api/infrastructure/water_bodies",
                   params={"west": -89.3, "south": 13.6, "east": -89.0, "north": 13.9,
                           "limit": 500})
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert body["metadata"]["license"] == "ODbL 1.0"


def test_capa_osm_invalida(client):
    assert client.get("/api/infrastructure/buildings").status_code == 404


def _tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


@pytest.mark.parametrize("kind", ["hillshade", "slope", "relief"])
def test_teselas_png(client, kind):
    x, y = _tile(13.69, -89.22, 9)
    r = client.get(f"/api/tiles/{kind}/9/{x}/{y}.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(r.content) > 500


def test_zoom_fuera_de_rango(client):
    x, y = _tile(13.69, -89.22, 9)
    assert client.get(f"/api/tiles/hillshade/3/{x}/{y}.png").status_code == 400
    assert client.get("/api/tiles/bogus/9/1/1.png").status_code == 404


def test_limitaciones_legibles(client):
    r = client.get("/api/limitations")
    assert r.status_code == 200
    assert "Limitaciones" in r.text
