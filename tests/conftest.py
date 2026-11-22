"""Configuración común de la suite de pruebas de AGROSV Fase 1.

Las pruebas se ejecutan contra los artefactos procesados reales: si un módulo
no se ha generado, la prueba se OMITE explícitamente (nunca pasa en falso).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv import config as C  # noqa: E402


def require(path: Path) -> Path:
    """Devuelve la ruta existente o salta la prueba declarándolo.

    Acepta rutas relativas (algunas pruebas de Fase 4 las usan) y las resuelve
    contra la raíz del proyecto antes de informar del salto.
    """
    candidate = Path(path)
    resolved = candidate if candidate.is_absolute() else ROOT / candidate
    if not resolved.exists():
        try:
            label = resolved.relative_to(ROOT).as_posix()
        except ValueError:
            label = str(resolved)
        pytest.skip(f"artefacto no generado: {label}")
    return resolved


def load_stats(name: str) -> dict:
    paths = {
        "territory": C.TERRITORY_DIR / "territory_meta.json",
        "topography": C.TOPOGRAPHY_DIR / "topography_stats.json",
        "infrastructure": C.INFRA_DIR / "infrastructure_stats.json",
        "soils": C.SOILS_DIR / "soils_stats.json",
    }
    path = require(paths[name])
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def territory():
    require(C.TERRITORY_GPKG)
    import geopandas as gpd

    return gpd.read_file(C.TERRITORY_GPKG, layer="adm1")


@pytest.fixture(scope="session")
def territory_meta():
    return load_stats("territory")


@pytest.fixture(scope="session")
def topo_stats():
    return load_stats("topography")


@pytest.fixture(scope="session")
def infra_stats():
    return load_stats("infrastructure")


@pytest.fixture(scope="session")
def soil_stats():
    return load_stats("soils")


@pytest.fixture(scope="session")
def client():
    require(C.TERRITORY_GPKG)
    require(C.HILLSHADE)
    from fastapi.testclient import TestClient

    from agrosv.api import app

    return TestClient(app)
