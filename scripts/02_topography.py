#!/usr/bin/env python
"""MÓDULO 2 — TOPOGRAFÍA.

Fuente: Copernicus DEM GLO-30 (COG) desde el bucket público de AWS.
  * Se leen VENTANAS de cada tile por /vsicurl: se descargan solo los bloques
    necesarios, no los 8 tiles completos (~184 MB).
  * Las derivadas se calculan en EPSG:32616 (metros). NUNCA se calcula pendiente
    en grados geográficos: a 13°N la relación metros/grado difiere ~4% entre
    latitud y longitud.
  * Las derivadas se conservan en el CRS métrico y no se remuestrean después.

Salidas (data/processed/topography/):
  dem30_wgs84.tif   elevación, CRS de la fuente, resolución nativa
  slope_deg.tif     pendiente (Int16, escala 100)
  aspect_deg.tif    orientación (Uint16, escala 10)
  hillshade.tif     sombreado (Uint8)
  relief_class.tif  clases de relieve (Uint8)
  topography_stats.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Debe fijarse antes de importar rasterio/GDAL.
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("GDAL_HTTP_MULTIPLEX", "YES")
os.environ.setdefault("GDAL_NUM_THREADS", "ALL_CPUS")
os.environ.setdefault("VSI_CACHE", "TRUE")

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.features import rasterize  # noqa: E402
from rasterio.shutil import copy as rio_copy  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
from rasterio.warp import calculate_default_transform, reproject  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import geopandas as gpd  # noqa: E402
from agrosv import config as C  # noqa: E402
from agrosv.provenance import write_manifest  # noqa: E402

ARCSEC = 1.0 / 3600.0  # resolución nativa de GLO-30
SUN_AZIMUTH = 315.0
SUN_ALTITUDE = 45.0


def tile_url(lat: int, lon: int) -> str:
    return C.DEM_TILE_TEMPLATE.format(
        base=C.DEM_S3_BASE,
        ns="N" if lat >= 0 else "S", lat=abs(lat),
        ew="E" if lon >= 0 else "W", lon=abs(lon),
    )


def build_grid():
    """Rejilla de salida alineada a la malla global de 1 arcsec, recortada a SV."""
    w, s, e, n = C.SV_BOUNDS
    lon0 = np.floor(w / ARCSEC) * ARCSEC
    lon1 = np.ceil(e / ARCSEC) * ARCSEC
    lat0 = np.floor(s / ARCSEC) * ARCSEC
    lat1 = np.ceil(n / ARCSEC) * ARCSEC
    width = int(round((lon1 - lon0) / ARCSEC))
    height = int(round((lat1 - lat0) / ARCSEC))
    return lon0, lat0, lon1, lat1, width, height


def mosaic_dem(lon0, lat0, lon1, lat1, width, height):
    """Lee ventanas de cada tile y las compone en un único array."""
    z = np.full((height, width), np.nan, dtype=np.float32)
    used = []
    for lat in C.DEM_TILE_GRID["lat"]:
        for lon in C.DEM_TILE_GRID["lon"]:
            t_w, t_s, t_e, t_n = lon, lat, lon + 1, lat + 1
            iw, is_, ie, inn = (max(t_w, lon0), max(t_s, lat0),
                                min(t_e, lon1), min(t_n, lat1))
            if iw >= ie or is_ >= inn:
                continue  # tile no intersecta
            # Se prefiere el tile local (data/raw/copdem30) porque /vsicurl
            # genera cientos de peticiones de rango y tarda >4 min. El crudo
            # queda hasheado y auditable; si falta, se cae a la lectura remota.
            local = C.RAW / "copdem30" / (tile_url(lat, lon).rsplit("/", 1)[-1])
            url = str(local) if local.exists() else "/vsicurl/" + tile_url(lat, lon)
            try:
                with rasterio.open(url) as ds:
                    win = from_bounds(iw, is_, ie, inn, ds.transform)
                    data = ds.read(1, window=win).astype(np.float32)
                    nd = ds.nodata
                    if nd is not None:
                        data[data == nd] = np.nan
            except Exception as exc:  # noqa: BLE001
                print(f"  [WARN] tile {lat},{lon}: {exc}")
                continue
            col0 = int(round((iw - lon0) / ARCSEC))
            row0 = int(round((lat1 - inn) / ARCSEC))
            h, w = data.shape
            z[row0:row0 + h, col0:col0 + w] = data
            used.append({"tile": f"N{lat}_W{abs(lon)}", "window": [int(h), int(w)],
                         "url": tile_url(lat, lon)})
            print(f"  leído {lat},{lon}: ventana {h}x{w} px")
    return z, used


def write_cog(arr, path, *, crs, transform, nodata, dtype, scale=None):
    """Escribe un COG con compresión y overviews."""
    tmp = C.INTERIM / (path.stem + "_tmp.tif")
    C.INTERIM.mkdir(parents=True, exist_ok=True)
    profile = dict(driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                   count=1, dtype=dtype, crs=crs, transform=transform,
                   nodata=nodata, tiled=True, blockxsize=512, blockysize=512,
                   compress="DEFLATE", predictor=2, zlevel=6, BIGTIFF="IF_SAFER")
    with rasterio.open(tmp, "w", **profile) as ds:
        ds.write(arr.astype(dtype), 1)
        if scale:
            ds.scales = (scale,)
    if path.exists():
        path.unlink()
    rio_copy(tmp, path, driver="COG", compress="DEFLATE", predictor=2,
             blocksize=512, overview_resampling="average", RESAMPLING="AVERAGE")
    tmp.unlink(missing_ok=True)
    return path


def shift_invalid(valid: np.ndarray) -> np.ndarray:
    """Marca como inválida toda celda cuyo vecindario 3x3 toque un borde/nodata."""
    bad = ~valid
    out = bad.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            sh = np.zeros_like(bad)
            ys = slice(max(dy, 0), bad.shape[0] + min(dy, 0))
            yd = slice(max(-dy, 0), bad.shape[0] + min(-dy, 0))
            xs = slice(max(dx, 0), bad.shape[1] + min(dx, 0))
            xd = slice(max(-dx, 0), bad.shape[1] + min(-dx, 0))
            sh[yd, xd] = bad[ys, xs]
            out |= sh
    return out


def slope_aspect_hillshade(z: np.ndarray, res_m: float):
    valid = np.isfinite(z)
    zf = np.where(valid, z, 0.0)
    gy_row, gx_col = np.gradient(zf, res_m, res_m)
    dz_dy = -gy_row          # filas crecen hacia el sur
    dz_dx = gx_col            # columnas crecen hacia el este

    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))

    # Dirección de máxima pendiente descendente, azimut desde el norte.
    aspect = np.degrees(np.arctan2(-dz_dx, -dz_dy)) % 360.0
    aspect = np.where(slope < 1e-6, np.nan, aspect)

    zen = np.radians(90.0 - SUN_ALTITUDE)
    az = np.radians(SUN_AZIMUTH)
    sl = np.radians(slope)
    asp = np.radians(aspect)
    hs = (np.cos(zen) * np.cos(sl) +
          np.sin(zen) * np.sin(sl) * np.cos(az - asp))
    hillshade = np.clip(hs * 255.0, 0, 255)

    invalid = shift_invalid(valid)
    slope[invalid] = np.nan
    aspect[invalid] = np.nan
    hillshade[invalid] = np.nan
    return slope, aspect, hillshade


def main() -> int:
    print("=" * 66)
    print(" MÓDULO 2 — TOPOGRAFÍA")
    print("=" * 66)
    C.TOPOGRAPHY_DIR.mkdir(parents=True, exist_ok=True)

    terr = gpd.read_file(C.TERRITORY_GPKG, layer="adm0")
    depts = gpd.read_file(C.TERRITORY_GPKG, layer="adm1")
    national = terr.geometry.iloc[0]

    lon0, lat0, lon1, lat1, width, height = build_grid()
    print(f"rejilla: {width} x {height} px  ({width*height/1e6:.1f} Mpx)  "
          f"lon[{lon0:.4f},{lon1:.4f}] lat[{lat0:.4f},{lat1:.4f}]")

    print("\n-- mosaico DEM (ventanas por /vsicurl) --")
    z, used_tiles = mosaic_dem(lon0, lat0, lon1, lat1, width, height)

    transform = from_origin(lon0, lat1, ARCSEC, ARCSEC)
    mask = rasterize([(national, 1)], out_shape=(height, width),
                     transform=transform, fill=0, dtype="uint8").astype(bool)
    z[~mask] = np.nan
    valid_ratio = float(np.isfinite(z).sum()) / float(mask.sum())
    print(f"celdas dentro del país: {int(mask.sum()):,}  con dato: {valid_ratio:.2%}")
    if valid_ratio < 1 - C.MAX_NODATA_RATIO_DEM:
        print("ERROR: exceso de nodata dentro del territorio")
        return 1

    # El nodata se materializa como -32768 (no NaN) para que cualquier lector
    # GIS lo reconozca sin depender de comparaciones con NaN.
    dem_path = write_cog(np.where(np.isfinite(z), z, -32768.0), C.DEM_WGS84,
                         crs=C.CRS_STORAGE, transform=transform,
                         nodata=-32768.0, dtype="float32")

    print("\n-- reproyección a métrico para derivadas --")
    with rasterio.open(dem_path) as src:
        dst_tf, dw, dh = calculate_default_transform(
            src.crs, C.CRS_METRIC, src.width, src.height, *src.bounds, resolution=30)
        zdem = np.full((dh, dw), np.nan, dtype=np.float32)
        reproject(source=rasterio.band(src, 1), destination=zdem,
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=dst_tf, dst_crs=C.CRS_METRIC,
                  resampling=Resampling.bilinear,
                  src_nodata=-32768.0, dst_nodata=np.nan)
    print(f"  rejilla métrica: {dw} x {dh} px @ 30 m")

    # La rejilla métrica cubre el rectángulo envolvente, no el país: para medir
    # cobertura hay que rasterizar el territorio EN EL CRS MÉTRICO.
    depts_m = depts.to_crs(C.CRS_METRIC)
    mask_m = rasterize([(depts_m.union_all(), 1)], out_shape=(dh, dw),
                       transform=dst_tf, fill=0, dtype="uint8").astype(bool)
    metric_coverage = float(mask_m.sum()) * 900.0 / 1e6
    print(f"  celdas dentro del país (métrico): {int(mask_m.sum()):,} "
          f"({metric_coverage:,.1f} km²)")

    print("\n-- derivadas --")
    slope, aspect, hs = slope_aspect_hillshade(zdem, 30.0)
    slope_i = np.where(np.isfinite(slope), np.round(slope * 100), -32768).astype(np.int16)
    # 360.0° y 0.0° son el mismo rumbo: se normaliza tras el redondeo para que
    # el máximo almacenado sea 359.9 y no se confunda con el nodata 65535.
    asp_i = np.where(np.isfinite(aspect),
                     np.mod(np.round(aspect * 10), 3600), 65535).astype(np.uint16)
    hs_i = np.where(np.isfinite(hs), np.round(hs), 0).astype(np.uint8)

    edges = [b[0] for b in C.RELIEF_BREAKS] + [C.RELIEF_BREAKS[-1][1]]
    cls = np.digitize(np.nan_to_num(slope, nan=0.0), edges[1:-1], right=False)
    cls = np.where(np.isfinite(slope), cls, 255).astype(np.uint8)

    write_cog(slope_i, C.SLOPE, crs=C.CRS_METRIC, transform=dst_tf,
              nodata=-32768, dtype="int16", scale=0.01)
    write_cog(asp_i, C.ASPECT, crs=C.CRS_METRIC, transform=dst_tf,
              nodata=65535, dtype="uint16", scale=0.1)
    write_cog(hs_i, C.HILLSHADE, crs=C.CRS_METRIC, transform=dst_tf,
              nodata=0, dtype="uint8")
    write_cog(cls, C.RELIEF_CLASS, crs=C.CRS_METRIC, transform=dst_tf,
              nodata=255, dtype="uint8")

    # --- Validación ----------------------------------------------------------
    print("\n-- validación --")
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))

    with rasterio.open(dem_path) as ds:
        check("DEM conserva resolución nativa 1 arcsec",
              abs(ds.res[0] - ARCSEC) < 1e-12, f"{ds.res[0]:.8f}°")
        arr = ds.read(1, masked=True)
        # El rectángulo envolvente incluye mar y territorio vecino: el nodata
        # solo es relevante DENTRO del polígono nacional.
        nodata_dem_country = float((arr.mask & mask).sum()) / float(mask.sum())
        check("DEM sin nodata dentro del territorio",
              nodata_dem_country < C.MAX_NODATA_RATIO_DEM,
              f"nodata dentro del país={nodata_dem_country:.2%}")
        fv = arr.compressed()
        check("elevación dentro de rango físico de SV (-10..3000 m)",
              bool(fv.min() > -10 and fv.max() < 3000),
              f"min={fv.min():.0f} max={fv.max():.0f} m")
        check("elevación máxima > 2000 m (El Pital ~2730 m)", bool(fv.max() > 2000),
              f"{fv.max():.0f} m")

    with rasterio.open(C.SLOPE) as ds:
        s = ds.read(1, masked=True) * ds.scales[0]
        sv = s.compressed()
        check("pendiente en rango 0..90°", bool(sv.min() >= 0 and sv.max() <= 90),
              f"min={sv.min():.2f} max={sv.max():.2f} media={sv.mean():.2f}")
        check("pendiente media nacional plausible (5..25°)",
              bool(5 <= sv.mean() <= 25), f"{sv.mean():.2f}°")
        nodata_pct_country = float((s.mask & mask_m).sum()) / float(mask_m.sum())
        check("sin nodata excesivo en pendiente dentro del país",
              nodata_pct_country < C.MAX_NODATA_RATIO_SLOPE,
              f"nodata dentro del país={nodata_pct_country:.2%}")

    with rasterio.open(C.ASPECT) as ds:
        a = ds.read(1, masked=True) * ds.scales[0]
        av = a.compressed()
        check("aspecto en rango 0..360°", bool(av.min() >= 0 and av.max() < 360),
              f"min={av.min():.1f} max={av.max():.1f}")

    with rasterio.open(C.HILLSHADE) as ds:
        h = ds.read(1, masked=True)
        check("hillshade en rango 0..255", bool(h.min() >= 0 and h.max() <= 255),
              f"min={h.min()} max={h.max()}")

    # Cobertura departamental: cada departamento debe tener datos.
    print("\n-- estadísticas zonales por departamento --")
    with rasterio.open(C.SLOPE) as ds:
        slope_full = ds.read(1).astype(np.float32) * 0.01
        slope_valid = ds.read(1) != -32768
        tf = ds.transform
        elev_full = None
    with rasterio.open(dem_path) as ds:
        elev_full = ds.read(1)
        elev_valid = elev_full != -32768

    stats = {}
    for _, row in depts_m.iterrows():
        m = rasterize([(row.geometry, 1)], out_shape=slope_full.shape,
                      transform=tf, fill=0, dtype="uint8").astype(bool)
        n = int((m & slope_valid).sum())
        if n == 0:
            check(f"cobertura {row['name']}", False, "sin celdas")
            continue
        sv = slope_full[m & slope_valid]
        pronounced = float((sv >= C.RELIEF_PRONOUNCED_MIN_DEG).sum()) / n
        stats[row["adm1_code"]] = {
            "name": row["name"],
            "area_km2": round(float(row["area_km2"]), 1),
            "pixels": n,
            "slope_mean_deg": round(float(sv.mean()), 2),
            "slope_p90_deg": round(float(np.percentile(sv, 90)), 2),
            "pronounced_relief_pct": round(pronounced * 100, 2),
            "nodata_pct": round(100.0 * (1 - sv.size / n), 3),
        }
    print(f"  departamentos con estadística: {len(stats)}/14")
    check("estadística zonal para los 14 departamentos", len(stats) == 14)

    if any(not c["passed"] for c in checks):
        print("\nERROR: validación topográfica fallida.")
        return 1

    # Elevación por departamento desde el DEM en 4326 (grid independiente).
    with rasterio.open(dem_path) as ds:
        dem4326 = ds.read(1)
        tf4326 = ds.transform
        for code, row in depts.set_index("adm1_code").iterrows():
            m = rasterize([(row.geometry, 1)], out_shape=dem4326.shape,
                          transform=tf4326, fill=0, dtype="uint8").astype(bool)
            vals = dem4326[m & (dem4326 != -32768)]
            if vals.size:
                stats[code]["elev_min_m"] = int(vals.min())
                stats[code]["elev_max_m"] = int(vals.max())
                stats[code]["elev_mean_m"] = int(round(float(vals.mean())))

    out = {
        "grid": {"width": width, "height": height, "arcsec": 1.0,
                 "crs": C.CRS_STORAGE, "bounds": [lon0, lat0, lon1, lat1]},
        "metric_grid": {"width": dw, "height": dh, "resolution_m": 30,
                        "crs": C.CRS_METRIC, "note": C.CRS_METRIC_NOTE},
        "tiles_used": used_tiles,
        "country": {
            "elev_min_m": int(np.nanmin(z)), "elev_max_m": int(np.nanmax(z)),
            "slope_mean_deg": round(float(np.nanmean(slope)), 2),
            "pronounced_relief_pct": round(
                float(np.nansum(slope >= C.RELIEF_PRONOUNCED_MIN_DEG)) /
                float(np.isfinite(slope).sum()) * 100, 2),
        },
        "relief_classes": [{"code": i, "min_deg": a, "max_deg": b, "label": lab}
                           for i, (a, b, lab) in enumerate(C.RELIEF_BREAKS)],
        "hillshade": {"sun_azimuth_deg": SUN_AZIMUTH,
                      "sun_altitude_deg": SUN_ALTITUDE,
                      "note": "convención ESRI; no es un dato, es una visualización"},
        "departments": stats,
        "validation": checks,
        "attribution": C.ATTRIBUTION["copdem"],
    }
    (C.TOPOGRAPHY_DIR / "topography_stats.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    for f, layer, res in (
        (C.DEM_WGS84, "dem30_wgs84", "elevación"),
        (C.SLOPE, "slope_deg", "pendiente en grados"),
        (C.ASPECT, "aspect_deg", "orientación (azimut de máxima pendiente)"),
        (C.HILLSHADE, "hillshade", "sombreado (visualización)"),
        (C.RELIEF_CLASS, "relief_class", "clases de relieve"),
    ):
        write_manifest(
            f, layer=layer, source_id="copdem30",
            source_url=C.DEM_S3_BASE, license="Copernicus-DEM-GLO-30",
            attribution=C.ATTRIBUTION["copdem"],
            native_resolution="1 arcsec (~30 m)",
            effective_resolution=("30 m (DSM: incluye vegetación y edificios)"
                                  if layer != "dem30_wgs84"
                                  else "30 m (DSM)"),
            transform=("ventana /vsicurl + mosaico + máscara nacional"
                       if layer == "dem30_wgs84" else
                       "warp EPSG:4326->EPSG:32616 @30m + gradiente Horn-libre"),
            extra={"quantity": res,
                   "nodata_ratio": round(float((~np.isfinite(slope)).mean()), 5)
                   if layer != "dem30_wgs84" else round(1 - valid_ratio, 5)},
        )

    print(f"\nescrito: {C.TOPOGRAPHY_DIR}")
    print(f"  elevación {np.nanmin(z):.0f}..{np.nanmax(z):.0f} m | "
          f"pendiente media {np.nanmean(slope):.2f}°")
    print("\nOK — Módulo 2 completado\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
