"""AGROSV — API geoespacial (Fase 1).

Un solo proceso sirve la API y la interfaz compilada, de modo que el mapa, los
tiles de hillshade y los GeoJSON comparten origen (sin CORS ni claves).

Decisiones:
  * No hay base de datos de servidor: las capas son GeoPackage y COG en disco,
    abiertos por ventana. PostGIS no aporta nada en Fase 1 (ver ADR-001).
  * Todos los datos salen de archivos con manifiesto `.provenance.json`; cada
    respuesta incluye `provenance` cuando corresponde.
  * Los tiles se generan al vuelo desde el COG de hillshade (sin teselado
    previo): un solo archivo fuente, sin caché que pueda quedar obsoleta.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from shapely.geometry import Point, box

from . import config as C
from .provenance import read_manifest

app = FastAPI(
    title="AGROSV Geospatial Foundation API",
    version="1.0.0",
    description=(
        "API de la fundación geoespacial de AGROSV: territorio, topografía, "
        "infraestructura (OpenStreetMap) y suelos (SoilGrids). "
        "Cada capa declara resolución, licencia y procedencia."
    ),
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Rango de zoom servido para hillshade. El DEM nativo es de 30 m; más allá de
# z13 no hay información nueva, solo interpolación.
HILLSHADE_MINZOOM, HILLSHADE_MAXZOOM = 7, 14
TILE_SIZE = 256


# --- Utilidades ---------------------------------------------------------------
def _departments() -> gpd.GeoDataFrame:
    return _departments_cached()


@lru_cache(maxsize=1)
def _departments_cached() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(C.TERRITORY_GPKG, layer="adm1")
    return gdf.set_crs(C.CRS_STORAGE, allow_override=True)


@lru_cache(maxsize=1)
def _metadata() -> dict:
    topo = json.loads((C.TOPOGRAPHY_DIR / "topography_stats.json").read_text())
    infra = json.loads((C.INFRA_DIR / "infrastructure_stats.json").read_text())
    soils = json.loads((C.SOILS_DIR / "soils_stats.json").read_text())
    terr_meta = json.loads((C.TERRITORY_DIR / "territory_meta.json").read_text())
    return {"territory": terr_meta, "topography": topo,
            "infrastructure": infra, "soils": soils}


def _sample(raster_path: Path, lon: float, lat: float, scale: float = 1.0):
    """Valor puntual (vecino más cercano) de un raster en EPSG:4326."""
    if not raster_path.exists():
        raise HTTPException(503, f"capa no disponible: {raster_path.name}")
    with rasterio.open(raster_path) as ds:
        x, y = rasterio.warp.transform(C.CRS_STORAGE, ds.crs, [lon], [lat])
        try:
            row, col = ds.index(x[0], y[0])
            win = ((row, row + 1), (col, col + 1))
            val = ds.read(1, window=win, masked=True).astype("float64") * scale
        except Exception:
            return None
        if val.size == 0 or np.ma.is_masked(val[0, 0]):
            return None
        v = float(val[0, 0])
        if not math.isfinite(v) or v == ds.nodata:
            return None
        return v


def _check_lonlat(lon: float, lat: float) -> None:
    w, s, e, n = C.SV_BOUNDS
    if not (w <= lon <= e and s <= lat <= n):
        raise HTTPException(400, "coordenada fuera del rectángulo de El Salvador")


# --- Sistema -------------------------------------------------------------------
@app.get("/api/health", summary="Estado del servicio y de cada capa")
def health():
    layers = {
        "territory": C.TERRITORY_GPKG,
        "dem": C.DEM_WGS84, "slope": C.SLOPE, "aspect": C.ASPECT,
        "hillshade": C.HILLSHADE, "relief_class": C.RELIEF_CLASS,
        "infrastructure": C.INFRA_GPKG,
    }
    missing = [k for k, p in layers.items() if not p.exists()]
    return {"status": "ok" if not missing else "degraded", "missing": missing,
            "version": app.version}


@app.get("/api/meta", summary="Resoluciones, licencias y procedencia de cada capa")
def meta():
    m = _metadata()
    return {
        "crs": {"storage": C.CRS_STORAGE, "metric": C.CRS_METRIC,
                "equal_area": C.CRS_EQUAL_AREA},
        "metric_note": C.CRS_METRIC_NOTE,
        "attribution": C.ATTRIBUTION,
        "datasets": {
            "territory": {
                "source": "geoBoundaries gbOpen",
                "license": "CC BY-SA 2.0",
                "adm1_count": m["territory"].get("adm1_count"),
                "adm2_count": m["territory"].get("adm2_count"),
                "adm2_official": False,
                "note": "ADM2 = 262 municipios pre-reforma 2023 (histórico).",
            },
            "topography": {
                "source": "Copernicus DEM GLO-30",
                "license": "Copernicus DEM (DLR/Airbus) — uso libre con atribución",
                "native_resolution": "1 arcsec (~30 m)",
                "derivatives_crs": C.CRS_METRIC,
                "grid": m["topography"]["grid"],
                "metric_grid": m["topography"]["metric_grid"],
            },
            "infrastructure": {
                "source": "OpenStreetMap (extracto Geofabrik)",
                "license": "ODbL 1.0",
                "osm_timestamp": m["infrastructure"]["source"]["osm_timestamp"],
                "features": m["infrastructure"]["layers"],
            },
            "soils": {
                "source": "SoilGrids 2.0 (ISRIC)",
                "license": "CC BY 4.0",
                "resolution_m": 250,
                "depth": "0–30 cm",
                "warning": "predicción de modelo global, no medición de laboratorio",
            },
        },
        "limitations_url": "/api/limitations",
    }


@app.get("/api/limitations", summary="Limitaciones conocidas, en texto plano")
def limitations():
    path = C.ROOT / "docs" / "LIMITATIONS.md"
    if not path.exists():
        raise HTTPException(404, "LIMITATIONS.md no encontrado")
    return Response(path.read_text(encoding="utf-8"), media_type="text/markdown")


# --- Territorio ----------------------------------------------------------------
@app.get("/api/territory/departments", summary="Departamentos (GeoJSON)")
def departments(simplify: float = Query(0.001, ge=0, le=0.02,
                                       description="tolerancia de simplificación en grados")):
    gdf = _departments()
    if simplify:
        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.simplify(simplify, preserve_topology=True)
    keep = [c for c in ("adm1_code", "name", "area_km2", "geometry") if c in gdf.columns]
    return JSONResponse(content=json.loads(gdf[keep].to_json()),
                        headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/territory/departments/{code}", summary="Un departamento y sus indicadores")
def department(code: str):
    gdf = _departments()
    row = gdf[gdf["adm1_code"].str.upper() == code.upper()]
    if row.empty:
        raise HTTPException(404, f"departamento {code} no existe")
    r = row.iloc[0]
    topo = _metadata()["topography"]["departments"].get(r["adm1_code"], {})
    soil = _metadata()["soils"]["departments"].get(r["adm1_code"], {})
    return {
        "code": r["adm1_code"], "name": r["name"],
        "area_km2": round(float(r["area_km2"]), 1),
        "topography": topo, "soils": soil,
        "geometry": json.loads(gpd.GeoSeries([r.geometry], crs=gdf.crs).to_json())
        ["features"][0]["geometry"],
    }


@app.get("/api/territory/municipalities", summary="Municipios históricos (pre-2023)")
def municipalities(department: str | None = None):
    gdf = gpd.read_file(C.TERRITORY_GPKG, layer="adm2")
    if department:
        gdf = gdf[gdf["adm1_code"].str.upper() == department.upper()]
    cols = [c for c in ("adm2_code", "name", "adm1_code", "quality") if c in gdf]
    payload = json.loads(gdf[cols + ["geometry"]].to_json())
    payload["metadata"] = {
        "official": False,
        "note": ("Límites municipales ANTERIORES a la reforma de 2023 "
                 "(262 municipios). No representan los 44 municipios vigentes."),
    }
    return JSONResponse(content=payload)


# --- Topografía ----------------------------------------------------------------
@app.get("/api/topography/elevation", summary="Elevación, pendiente y aspecto en un punto")
def elevation(lat: float, lon: float):
    _check_lonlat(lon, lat)
    return {
        "lat": lat, "lon": lon,
        "elevation_m": _sample(C.DEM_WGS84, lon, lat),
        "slope_deg": _sample(C.SLOPE, lon, lat, scale=0.01),
        "aspect_deg": _sample(C.ASPECT, lon, lat, scale=0.1),
        "relief_class": _sample(C.RELIEF_CLASS, lon, lat),
        "source": {"dem": "Copernicus DEM GLO-30 (DSM, ~30 m)",
                   "derivatives_crs": C.CRS_METRIC},
    }


@app.get("/api/topography/stats", summary="Estadísticas nacionales y por departamento")
def topography_stats():
    return _metadata()["topography"]["departments"] | {
        "country": _metadata()["topography"]["country"],
        "relief_classes": _metadata()["topography"]["relief_classes"],
    }


# --- Infraestructura -----------------------------------------------------------
@app.get("/api/infrastructure/summary", summary="Conteos y longitudes por capa")
def infrastructure_summary():
    infra = _metadata()["infrastructure"]
    return {"source": infra["source"], "layers": infra["layers"],
            "road_km_by_class": infra.get("road_km_by_class"),
            "road_km_main_network": infra.get("road_km_main_network"),
            "road_km_total": infra.get("road_km_total"),
            "coverage_notes": infra["coverage_notes"]}


@app.get("/api/infrastructure/{layer}", summary="Capa OSM como GeoJSON (recortada a un bbox)")
def infrastructure_layer(
    layer: str,
    west: float | None = None, south: float | None = None,
    east: float | None = None, north: float | None = None,
    limit: int = Query(8000, le=50000),
):
    allowed = {"roads", "waterways", "water_bodies", "settlements",
               "infrastructure", "power_lines"}
    if layer not in allowed:
        raise HTTPException(404, f"capa '{layer}' no existe; use {sorted(allowed)}")
    bbox = None
    if None not in (west, south, east, north):
        bbox = box(west, south, east, north)
    gdf = gpd.read_file(C.INFRA_GPKG, layer=layer, bbox=bbox, rows=limit)
    if len(gdf) >= limit:
        headers = {"X-Truncated": "true"}
    else:
        headers = {}
    payload = json.loads(gdf.to_json())
    payload["metadata"] = {"layer": layer, "features": len(gdf),
                           "license": "ODbL 1.0",
                           "attribution": C.ATTRIBUTION["osm"]}
    return JSONResponse(content=payload, headers=headers)


# --- Suelos --------------------------------------------------------------------
SOIL_RASTERS = {
    "phh2o": ("pH (H₂O)", 0.1, "pH"),
    "soc": ("carbono orgánico", 0.1, "g/kg"),
    "nitrogen": ("nitrógeno total", 0.01, "g/kg"),
    "clay": ("arcilla", 0.1, "%"),
    "sand": ("arena", 0.1, "%"),
    "silt": ("limo", 0.1, "%"),
}


@app.get("/api/soils/summary", summary="Medias nacionales y por departamento")
def soils_summary():
    soils = _metadata()["soils"]
    return {
        "source": soils["source"],
        "variables": soils["variables"],
        "country_means": soils["country_means"],
        "national_sources": soils["national_sources"],
        "caveats": soils["caveats"],
    }


@app.get("/api/soils/point", summary="Propiedades del suelo 0–30 cm en un punto")
def soils_point(lat: float, lon: float):
    _check_lonlat(lon, lat)
    out = {"lat": lat, "lon": lon, "depth": "0-30cm"}
    for key, (_, scale, unit) in SOIL_RASTERS.items():
        v = _sample(C.SOILS_RASTER_DIR / f"{key}_0-30cm.tif", lon, lat, scale=scale)
        out[key] = None if v is None else round(v, 2)
    out["unit"] = {k: u[2] for k, u in SOIL_RASTERS.items()}
    out["disclaimer"] = ("Predicciones SoilGrids 2.0 a 250 m; no son análisis "
                         "de laboratorio.")
    return out


# --- Tiles de hillshade ---------------------------------------------------------
# Rampas discretas documentadas en docs/LIMITATIONS.md.
RELIEF_RGB = {
    0: (232, 240, 226), 1: (203, 222, 175), 2: (166, 199, 122),
    3: (222, 190, 95), 4: (196, 130, 74), 5: (150, 78, 55),
}
SLOPE_BINS = [(0, 2), (2, 5), (5, 12), (12, 25), (25, 45), (45, 91)]


@app.get("/api/tiles/{kind}/{z}/{x}/{y}.png",
         summary="Teselas PNG (hillshade, pendiente, clases de relieve)")
def raster_tile(kind: str, z: int, x: int, y: int):
    if kind not in {"hillshade", "slope", "relief"}:
        raise HTTPException(404, "tipo de tesela desconocido")
    if not (HILLSHADE_MINZOOM <= z <= HILLSHADE_MAXZOOM):
        raise HTTPException(400, f"zoom fuera de rango {HILLSHADE_MINZOOM}–{HILLSHADE_MAXZOOM}")
    src_path = {"hillshade": C.HILLSHADE, "slope": C.SLOPE,
                "relief": C.RELIEF_CLASS}[kind]
    if not src_path.exists():
        raise HTTPException(503, f"{kind} no generado")

    n = 2 ** z
    lon0, lon1 = x / n * 360.0 - 180.0, (x + 1) / n * 360.0 - 180.0

    def _lat(yy: int) -> float:
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))

    lat0, lat1 = _lat(y + 1), _lat(y)
    west, south, east, north = lon0, lat0, lon1, lat1

    with rasterio.open(src_path) as ds:
        b = transform_bounds(C.CRS_STORAGE, ds.crs, west, south, east, north)
        win = from_bounds(*b, transform=ds.transform)
        data = ds.read(1, window=win, out_shape=(TILE_SIZE, TILE_SIZE),
                       resampling=Resampling.nearest if kind != "hillshade"
                       else Resampling.bilinear, boundless=True, fill_value=0)
        # `read_masks` no acepta out_shape/boundless en rasterio 1.5; la
        # validez se deriva del propio centinela de nodata de cada capa.
        mask = np.where(data == ds.nodata, 0, 255).astype(np.uint8)
    rgb = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    if kind == "hillshade":
        shade = data.astype(np.uint8)
        rgb[..., 0] = (shade * 0.94).astype(np.uint8) + 14
        rgb[..., 1] = (shade * 0.96).astype(np.uint8) + 9
        rgb[..., 2] = (shade * 0.90).astype(np.uint8) + 4
        rgb[..., 3] = np.where(mask > 0, 255, 0).astype(np.uint8)
    elif kind == "slope":
        deg = data.astype(np.float32) * 0.01
        codes = np.digitize(deg, [b[1] for b in SLOPE_BINS[:-1]], right=False)
        for code, color in RELIEF_RGB.items():
            sel = codes == code
            rgb[sel, 0], rgb[sel, 1], rgb[sel, 2] = color
        rgb[..., 3] = np.where((mask > 0) & (data != -32768), 190, 0).astype(np.uint8)
    else:
        for code, color in RELIEF_RGB.items():
            sel = data == code
            rgb[sel, 0], rgb[sel, 1], rgb[sel, 2] = color
        rgb[..., 3] = np.where((mask > 0) & (data != 255), 200, 0).astype(np.uint8)

    from PIL import Image

    buf = __import__("io").BytesIO()
    Image.fromarray(rgb, mode="RGBA").save(buf, format="PNG", optimize=True)
    return Response(buf.getvalue(), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


# --- Interfaz compilada ---------------------------------------------------------
DIST = C.ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="ui")
