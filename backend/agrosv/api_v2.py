"""AGROSV — API científica versionada (Fase 2).

Capa `/api/v1` sobre los endpoints de Fase 1, que **no se modifican**. Esta capa
solo publica lo que puede sostener: catálogo de datasets con hash y licencia,
resolución de procedencia, control de calidad, hidrología D8 derivada del DEM y
paquetes territoriales offline.

Dos reglas se aplican en cada respuesta:

1. Toda cifra sale envuelta por `agrosv.science.schemas.wrap`, que exige
   etiqueta (observado/derivado/estimado/predicho/simulado), resolución real,
   incertidumbre, limitaciones y `provenance_id`.
2. Nada se sirve de una fuente cuya licencia prohíba la redistribución. Los
   paquetes offline excluyen OSM (ODbL con *share-alike* sobre bases derivadas)
   y cualquier capa restringida.
"""
from __future__ import annotations

import io
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse, StreamingResponse
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

from . import config as C
from .provenance import read_manifest
from .science import hydrology, indices, qc, registry
from .science.schemas import Uncertainty, wrap

router = APIRouter(prefix="/api/v1", tags=["science-v1"])

SERVICE_VERSION = "2.0.0"
PUBLIC_LICENSE = "CC-BY-4.0"
RES_30M = "30 m (DEM Copernicus GLO-30, DSM: incluye vegetación y edificios)"
HYDRO_LIMITATIONS = [
    "modelo no calibrado: no hay aforos ni series de caudal para El Salvador",
    "el DEM de 30 m no resuelve cauces menores ni obras hidráulicas",
    "D8 no representa flujo difuso ni zonas planas; las celdas planas se informan",
    "produce agua físicamente presente, no agua autorizada ni comprometida",
    "ventana de análisis acotada: una cuenca mayor que la ventana aparece truncada",
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dem_provenance() -> str:
    for ds in registry.catalog():
        if ds.layer == "dem30_wgs84":
            return ds.provenance_id or ds.dataset_version
    raise HTTPException(503, "DEM sin manifiesto de procedencia")


def _headers(provenance_id: str = "", license_: str = PUBLIC_LICENSE) -> dict[str, str]:
    return {
        "X-AGROSV-Version": SERVICE_VERSION,
        "X-AGROSV-Provenance": provenance_id,
        "X-AGROSV-License": license_,
        "X-AGROSV-Data-Date": _utcnow()[:10],
    }


# --- Metadatos ----------------------------------------------------------------
@router.get("/meta", summary="Versión, datasets versionados y fichas de índices")
def meta():
    catalog = [ds.as_dict() for ds in registry.catalog()]
    return JSONResponse(
        content={
            "service_version": SERVICE_VERSION,
            "generated_at": _utcnow(),
            "inherits": "/api (Fase 1): territorio, topografía, infraestructura, suelos",
            "datasets": catalog,
            "licenses": registry.licenses(),
            "indices": indices.specs(),
            "publication_policy": {
                "redistributable": ["CC-BY-4.0", "CC-BY-SA-2.0",
                                    "Copernicus-DEM-GLO-30", "ODbL-1.0"],
                "derived_only": ["propietaria FAO (AquaCrop)",
                                 "no comercial (WorldClim, GAEZ)"],
                "note": "las fuentes derivadas-only nunca se sirven como archivo",
            },
            "notes": [
                "dataset_version depende del hash del contenido, no de la fecha",
                "la resolución publicada es la del insumo más grueso, nunca la de visualización",
            ],
        },
        headers=_headers(),
    )


@router.get("/sources", summary="Catálogo de versiones de dataset con licencia")
def sources(verify: bool = Query(False, description="recalcular hashes (lento)")):
    payload: dict[str, Any] = {
        "count": len(registry.catalog()),
        "datasets": [ds.as_dict() for ds in registry.catalog()],
        "licenses": registry.licenses(),
    }
    if verify:
        payload["verification"] = registry.verify_all()
    return JSONResponse(content=payload, headers=_headers())


@router.get("/provenance/{provenance_id}", summary="Manifiesto completo de una cifra")
def provenance(provenance_id: str):
    dataset = registry.find(provenance_id)
    if dataset is None:
        raise HTTPException(404, f"provenance_id desconocido: {provenance_id}")
    return JSONResponse(
        content={"dataset_version": dataset.dataset_version,
                 "manifest": dataset.manifest},
        headers=_headers(dataset.provenance_id, dataset.license),
    )


# --- Control de calidad -------------------------------------------------------
@router.get("/qc", summary="Control de calidad geoespacial de los artefactos")
def qc_summary(include_rasters: bool = Query(False,
                                             description="leer rasters completos (lento)")):
    targets: list[tuple[Path, str | None]] = [
        (C.TERRITORY_GPKG, "adm1"),
        (C.TERRITORY_GPKG, "adm2"),
        (C.INFRA_GPKG, "roads"),
        (C.INFRA_GPKG, "waterways"),
    ]
    targets = [(p, l) for p, l in targets if p.exists()]
    reports = [qc.qc_vector(p, layer=l, expected_crs=C.CRS_STORAGE,
                            bounds=C.SV_BOUNDS).as_dict() for p, l in targets]
    if include_rasters:
        rasters = [C.DEM_WGS84, C.SLOPE, C.RELIEF_CLASS,
                   C.SOILS_RASTER_DIR / "phh2o_0-30cm.tif"]
        reports += [qc.qc_raster(p).as_dict() for p in rasters if p.exists()]
    ok = all(r["ok"] for r in reports)
    return JSONResponse(
        content={
            "ok": ok,
            "checked": len(reports),
            "failed": [r["artifact"] for r in reports if not r["ok"]],
            "reports": reports,
            "note": ("QC de propiedades geométricas y de cobertura; no valida la "
                     "exactitud temática ni la validez científica del dato"),
            "generated_at": _utcnow(),
        },
        headers=_headers(),
    )


# --- Hidrología ---------------------------------------------------------------
def _dem_window(lon: float, lat: float, size_m: float
                ) -> tuple[np.ndarray, Any, str]:
    """Ventana del DEM reproyectada a UTM 16N a 30 m (no se carga el país)."""
    if not C.DEM_WGS84.exists():
        raise HTTPException(503, "DEM no generado")
    dlat = size_m / 111_320.0
    dlon = size_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.1))
    west, east = lon - dlon / 2, lon + dlon / 2
    south, north = lat - dlat / 2, lat + dlat / 2

    with rasterio.open(C.DEM_WGS84) as ds:
        win = rasterio.windows.from_bounds(west, south, east, north, ds.transform)
        arr = ds.read(1, window=win, boundless=True, fill_value=-32768.0)
        src_tf = rasterio.windows.transform(win, ds.transform)
        src_crs = ds.crs
        src_nodata = ds.nodata

    m_w, m_s, m_e, m_n = transform_bounds(src_crs, C.CRS_METRIC, west, south, east, north)
    res = 30.0
    width = max(16, int(math.ceil((m_e - m_w) / res)))
    height = max(16, int(math.ceil((m_n - m_s) / res)))
    dst_tf = from_origin(m_w, m_n, res, res)

    src = arr.astype(np.float32)
    if src_nodata is not None:
        src[src == src_nodata] = np.nan
    dst = np.full((height, width), np.nan, dtype=np.float32)
    rasterio.warp.reproject(
        source=src, destination=dst,
        src_transform=src_tf, src_crs=src_crs,
        dst_transform=dst_tf, dst_crs=C.CRS_METRIC,
        resampling=Resampling.bilinear,
        src_nodata=np.nan, dst_nodata=np.nan,
    )
    return dst, dst_tf, C.CRS_METRIC


@router.get("/hydro/watershed", summary="Cuenca aguas arriba (D8) desde un punto")
def watershed(
    lat: float = Query(..., ge=C.SV_BOUNDS[1], le=C.SV_BOUNDS[3]),
    lon: float = Query(..., ge=C.SV_BOUNDS[0], le=C.SV_BOUNDS[2]),
    size_m: float = Query(3_000, ge=900, le=12_000,
                          description="lado de la ventana de análisis, en metros"),
    geometry: bool = Query(True, description="incluir polígono GeoJSON"),
):
    elev, transform, crs = _dem_window(lon, lat, size_m)
    valid = np.isfinite(elev)
    if valid.sum() < 100:
        raise HTTPException(422, "la ventana no contiene celdas con dato del DEM")

    aoi = hydrology.compute_aoi(elev, 30.0, stream_threshold_ratio=0.01)
    outlet = hydrology.outlet_cell(aoi["accumulation"])
    mask = hydrology.watershed(aoi["directions"], outlet, valid)

    touches_edge = bool(mask[0, :].any() or mask[-1, :].any()
                        or mask[:, 0].any() or mask[:, -1].any())
    area_km2 = round(float(mask.sum()) * 900.0 / 1e6, 4)
    acc_at_outlet = int(aoi["accumulation"][outlet])

    value: dict[str, Any] = {
        "outlet_rowcol": list(outlet),
        "area_km2": area_km2,
        "cells": int(mask.sum()),
        "accumulation_at_outlet": acc_at_outlet,
        "truncated": touches_edge,
        "diagnostics": {**aoi["diagnostics"],
                        "window_size_m": size_m,
                        "window_cells": [int(elev.shape[1]), int(elev.shape[0])]},
    }
    if geometry:
        gj = hydrology.mask_to_geojson(mask, transform, crs)
        value["geometry"] = gj["features"][0]["geometry"] if gj["features"] else None
        value["geometry_features"] = len(gj["features"])

    limitations = list(HYDRO_LIMITATIONS)
    if touches_edge:
        limitations.append(
            "la cuenca alcanza el borde de la ventana de análisis: el área "
            "reportada es un mínimo, no el área total de la cuenca"
        )
    return JSONResponse(
        content=wrap(
            value,
            label="derivado",
            method="priority-flood + D8 + acumulación + cuenca aguas arriba",
            resolution="30 m (DEM GLO-30 reproyectado a UTM 16N)",
            confidence="baja" if touches_edge else "media",
            provenance_id=_dem_provenance(),
            uncertainty=Uncertainty(
                method="sensibilidad no cuantificada en esta ejecución",
                note=("el área depende del relleno de sumideros y del borde de "
                      "la ventana; sin aforos no hay calibración"),
            ),
            limitations=limitations,
            unit="km²",
            sources=["copdem30"],
            model_version="agrosv.science.hydrology/1",
            extra={"truncated": touches_edge},
        ),
        headers=_headers(_dem_provenance()),
    )


@router.get("/hydro/aoi", summary="Diagnósticos hidrológicos de un área de interés")
def hydro_aoi(
    lat: float = Query(..., ge=C.SV_BOUNDS[1], le=C.SV_BOUNDS[3]),
    lon: float = Query(..., ge=C.SV_BOUNDS[0], le=C.SV_BOUNDS[2]),
    size_m: float = Query(3_000, ge=900, le=6_000),
):
    elev, _, _ = _dem_window(lon, lat, size_m)
    aoi = hydrology.compute_aoi(elev, 30.0)
    lsv = aoi["ls_factor"][np.isfinite(aoi["ls_factor"])]
    sv = aoi["slope_deg"][np.isfinite(aoi["slope_deg"])]
    if sv.size == 0:
        raise HTTPException(422, "ventana sin pendiente válida")
    value = {
        "diagnostics": aoi["diagnostics"],
        "slope_deg": {"mean": round(float(sv.mean()), 2),
                      "p90": round(float(np.percentile(sv, 90)), 2)},
        "ls_factor": {"mean": round(float(lsv.mean()), 3) if lsv.size else None,
                      "p90": round(float(np.percentile(lsv, 90)), 3) if lsv.size else None},
        "stream_cells": int(aoi["streams"].sum()),
    }
    return JSONResponse(
        content=wrap(
            value,
            label="derivado",
            method="D8 + acumulación + LS de RUSLE (factor topográfico)",
            resolution="30 m (DEM GLO-30)",
            confidence="baja",
            provenance_id=_dem_provenance(),
            uncertainty=Uncertainty(method="no cuantificada; ver limitaciones"),
            limitations=HYDRO_LIMITATIONS + [
                "LS es solo el factor topográfico de RUSLE: sin R, K, C y P no "
                "hay tasa de erosión",
            ],
            sources=["copdem30"],
            model_version="agrosv.science.hydrology/1",
        ),
        headers=_headers(_dem_provenance()),
    )


# --- Índices espectrales ------------------------------------------------------
@router.get("/indices", summary="Fichas de índices, resolución nativa y límites")
def index_specs():
    return JSONResponse(
        content={
            "indices": indices.specs(),
            "implemented": "aritmética de bandas y máscaras de cambio",
            "not_implemented": [
                "adquisición STAC/CDSE",
                "enmascarado de nubes por banda SCL",
                "compuestos temporales por mediana",
                "detección de candidatos agrícolas",
            ],
            "note": ("no se sirve ninguna serie satelital: sin escenas archivadas "
                     "no hay nada que publicar"),
        },
        headers=_headers(),
    )


# --- Paquetes offline ---------------------------------------------------------
PACKAGE_EXCLUDED = {
    "osm": "ODbL 1.0 share-alike: no se incluye para no licenciar el paquete completo",
    "private": "datos de parcelas y reportes comunitarios no son públicos",
}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@router.get("/offline/{department}.zip", summary="Paquete territorial offline")
def offline_package(department: str):
    import geopandas as gpd

    if not C.TERRITORY_GPKG.exists():
        raise HTTPException(503, "territorio no generado")
    adm1 = gpd.read_file(C.TERRITORY_GPKG, layer="adm1")
    row = adm1[adm1["adm1_code"].str.upper() == department.upper()]
    if row.empty:
        raise HTTPException(404, f"departamento {department} no existe")
    row = row.iloc[0]
    code = str(row["adm1_code"])

    topo = _read_json(C.TOPOGRAPHY_DIR / "topography_stats.json").get(
        "departments", {}).get(code, {})
    soils = _read_json(C.SOILS_DIR / "soils_stats.json").get(
        "departments", {}).get(code, {})

    municipality_note = {
        "official": False,
        "note": ("límites municipales anteriores a la reforma de 2023; no son "
                 "los 44 municipios vigentes"),
    }
    try:
        adm2 = gpd.read_file(C.TERRITORY_GPKG, layer="adm2")
        adm2 = adm2[adm2["adm1_code"].str.upper() == code.upper()]
        adm2_payload = json.loads(adm2[["adm2_code", "name", "geometry"]].to_json()) \
            if len(adm2) else {"type": "FeatureCollection", "features": []}
    except Exception:  # noqa: BLE001 — capa opcional
        adm2_payload = {"type": "FeatureCollection", "features": []}
    adm2_payload["metadata"] = municipality_note

    members: dict[str, bytes] = {
        "territory/department.geojson": json.dumps(
            json.loads(gpd.GeoDataFrame([row], crs=adm1.crs).to_json()),
            ensure_ascii=False).encode("utf-8"),
        "territory/municipalities_historic.geojson": json.dumps(
            adm2_payload, ensure_ascii=False).encode("utf-8"),
        "terrain_stats.json": json.dumps(topo, indent=2, ensure_ascii=False).encode("utf-8"),
        "soils_summary.json": json.dumps(soils, indent=2, ensure_ascii=False).encode("utf-8"),
    }

    versions = [ds.as_dict() for ds in registry.catalog()
                if ds.layer in {"adm1", "adm2", "territory", "dem30_wgs84"}]
    metadata = {
        "package": f"agrosv-package-{code}",
        "department": {"code": code, "name": str(row["name"]),
                       "area_km2": round(float(row["area_km2"]), 1)},
        "generated_at": _utcnow(),
        "service_version": SERVICE_VERSION,
        "dataset_versions": versions,
        "licenses": {
            "territory": (
                "geoBoundaries gbOpen, CC BY-SA 2.0. Base derivada sujeta a "
                "la misma licencia."
            ),
            "topography": C.ATTRIBUTION["copdem"],
            "soils": C.ATTRIBUTION["soilgrids"],
        },
        "excluded": PACKAGE_EXCLUDED,
        "limitations": [
            "los datos tienen la fecha de corte de los artefactos listados",
            "no incluye rásteres: solo vectores y resúmenes estadísticos",
            "no sustituye los portales oficiales de MAG, CENTA, MARN o BCR",
        ],
    }
    members["metadata.json"] = json.dumps(
        metadata, indent=2, ensure_ascii=False).encode("utf-8")
    members["README.txt"] = (
        "AGROSV — paquete territorial offline\n"
        f"Departamento: {row['name']} ({code})\n"
        f"Generado: {metadata['generated_at']}\n\n"
        "Contenido: límite departamental, municipios históricos, resumen "
        "topográfico y de suelos.\n\n"
        "Atribución obligatoria:\n"
        f"  {C.ATTRIBUTION['geoboundaries']}\n"
        f"  {C.ATTRIBUTION['copdem']}\n"
        f"  {C.ATTRIBUTION['soilgrids']}\n\n"
        "Este paquete NO contiene datos privados ni capas OSM.\n"
    ).encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(members.items()):
            zf.writestr(name, data)
    buf.seek(0)
    headers = _headers()
    headers["Content-Disposition"] = (
        f'attachment; filename="agrosv-package-{code}.zip"'
    )
    headers["X-AGROSV-License"] = "CC-BY-SA-2.0;CC-BY-4.0"
    return StreamingResponse(buf, media_type="application/zip", headers=headers)


@router.get("/validation/policy", summary="Niveles de evidencia y estado real")
def validation_policy():
    return JSONResponse(
        content={
            "levels": {
                "V0": "sin validación externa",
                "V1": "consistencia interna",
                "V2": "referencia agregada (≥10 pares)",
                "V3": "referencia puntual (≥30 pares)",
                "V4": "validación independiente de campo",
            },
            "current_status": {
                "territory": "V1 (integridad geométrica verificada en pruebas)",
                "topography": "V1 (rangos físicos; sin MDT de referencia)",
                "soils": "V0 en El Salvador (SoilGrids es predicción global)",
                "hydrology_module": "V0 (sin aforos; no calibrado)",
                "satellite_indices": "V0 (sin escenas procesadas ni campo)",
            },
            "rule": ("ningún módulo se etiqueta V2 o superior sin métricas "
                     "registradas contra observaciones declaradas"),
        },
        headers=_headers(),
    )
