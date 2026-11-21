"""Módulo 7 — rendimiento de las consultas expuestas.

Los umbrales son deliberadamente holgados (hardware variable) pero suficientes
para detectar regresiones graves: lectura de rasters completos por petición,
GeoJSON sin comprimir o capas OSM sin filtro espacial.
"""
from __future__ import annotations

import math
import time


def _timed(fn, *, repeat=3):
    best = float("inf")
    for _ in range(repeat):
        t = time.perf_counter()
        out = fn()
        best = min(best, time.perf_counter() - t)
    return best, out


def test_consulta_puntual_rapida(client):
    # calienta cachés de sistema de archivos
    client.get("/api/topography/elevation", params={"lat": 13.69, "lon": -89.22})
    dt, r = _timed(lambda: client.get("/api/topography/elevation",
                                      params={"lat": 13.69, "lon": -89.22}))
    assert r.status_code == 200
    assert dt < 0.08, f"elevación tardó {dt*1000:.1f} ms"


def test_suelo_puntual_rapido(client):
    client.get("/api/soils/point", params={"lat": 13.69, "lon": -89.22})
    dt, r = _timed(lambda: client.get("/api/soils/point",
                                      params={"lat": 13.69, "lon": -89.22}))
    assert r.status_code == 200
    assert dt < 0.20, f"suelo tardó {dt*1000:.1f} ms"


def test_payload_de_departamentos_ligero(client):
    # `simplify` es el valor por defecto del endpoint: el mapa no necesita
    # vértices sub-métricos y un dispositivo de gama baja agradece 90 KB.
    dt, r = _timed(lambda: client.get("/api/territory/departments"), repeat=2)
    assert r.status_code == 200
    assert dt < 1.0
    assert len(r.content) < 400_000, f"{len(r.content)/1024:.0f} KB"


def test_tesela_generada_rapido(client):
    z = 9
    n = 2 ** z
    x = int((-89.22 + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(13.69))) / math.pi) / 2.0 * n)
    client.get(f"/api/tiles/hillshade/{z}/{x}/{y}.png")  # calienta
    dt, r = _timed(lambda: client.get(f"/api/tiles/hillshade/{z}/{x}/{y}.png"))
    assert r.status_code == 200
    assert dt < 1.5, f"tesela tardó {dt*1000:.0f} ms"


def test_capa_osm_acotada_por_bbox(client):
    params = {"west": -89.3, "south": 13.6, "east": -89.0, "north": 13.9, "limit": 500}
    dt, r = _timed(lambda: client.get("/api/infrastructure/roads", params=params), repeat=2)
    assert r.status_code == 200
    assert dt < 3.0
    assert len(r.json()["features"]) <= 500
