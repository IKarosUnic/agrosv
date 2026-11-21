#!/usr/bin/env python
"""MÓDULO 4 — SUELOS (SoilGrids 2.0 + registro de fuentes nacionales).

Fuente global: SoilGrids 2.0 (ISRIC), CC BY 4.0, 250 m, predicciones por
modelado (no mediciones de laboratorio). Se accede por WebDAV a los VRT
globales en Interrupted Goode Homolosine y se descargan SOLO las teselas
600×600 que cubren El Salvador: el VRT completo tiene 7.692 teselas por capa.

Profundidad de trabajo: 0–30 cm, media ponderada por espesor de las capas
0–5, 5–15 y 15–30 cm (pesos 5/30, 10/30, 15/30).

Variables: pH (H₂O), carbono orgánico (SOC), nitrógeno total, arcilla, arena,
limo. Unidades convertidas a las convencionales agronómicas y documentadas en
DATA_PROVENANCE.md.

ADVERTENCIA: estas capas son estimaciones de un modelo global. No sustituyen
análisis de laboratorio ni el Mapa Digital de Suelos del CENTA.

Salidas (data/processed/soils/rasters/*.tif, EPSG:32616, 250 m):
  phh2o_0-30cm.tif soc_0-30cm.tif nitrogen_0-30cm.tif
  clay_0-30cm.tif sand_0-30cm.tif silt_0-30cm.tif
  + soils_stats.json y manifiestos de procedencia
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from pyproj import Transformer  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.features import rasterize  # noqa: E402
from rasterio.shutil import copy as rio_copy  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402
from rasterio.warp import reproject  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402

from agrosv import config as C  # noqa: E402
from agrosv.provenance import write_manifest  # noqa: E402

BASE = "https://files.isric.org/soilgrids/latest/data"
RAW = C.RAW / "soilgrids"
RES_M = 250.0
NODATA = -32768

# variable -> (unidad final, factor desde el entero almacenado, rango físico)
PROPS = {
    "phh2o": ("pH", 0.1, (3.0, 10.0)),
    "soc": ("g/kg", 0.1, (0.0, 300.0)),
    "nitrogen": ("g/kg", 0.01, (0.0, 30.0)),
    "clay": ("%", 0.1, (0.0, 100.0)),
    "sand": ("%", 0.1, (0.0, 100.0)),
    "silt": ("%", 0.1, (0.0, 100.0)),
}
DEPTHS = [("0-5cm", 5.0), ("5-15cm", 10.0), ("15-30cm", 15.0)]
TOTAL_W = sum(w for _, w in DEPTHS)


def fetch(url: str, dest: Path, retries: int = 3) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                dest.write_bytes(r.read())
            return
        except Exception:  # noqa: BLE001
            if attempt == retries:
                raise
            time.sleep(2 * attempt)


def vrt_path(prop: str, depth: str) -> Path:
    return RAW / prop / f"{prop}_{depth}_mean.vrt"


def load_vrt(prop: str, depth: str) -> Path:
    """Descarga el VRT maestro (3,5 MB) una sola vez y lo cachea."""
    local = vrt_path(prop, depth)
    fetch(f"{BASE}/{prop}/{local.name}", local)
    return local


def select_sources(vrt: Path, win) -> list[str]:
    """Devuelve las rutas relativas de teselas que intersectan la ventana."""
    root = ET.parse(vrt).getroot()
    out = []
    for src in root.iter("ComplexSource"):
        fn = src.findtext("SourceFilename")
        dst = src.find("DstRect")
        if fn is None or dst is None:
            continue
        # Algunos DstRect vienen con offsets fraccionarios (p. ej. 88106.5).
        x, y = float(dst.get("xOff")), float(dst.get("yOff"))
        w, h = float(dst.get("xSize")), float(dst.get("ySize"))
        if (x + w > win.col_off and x < win.col_off + win.width and
                y + h > win.row_off and y < win.row_off + win.height):
            out.append(fn.removeprefix("./"))
    return out


def download_tiles(vrt: Path, rels: list[str], pool: ThreadPoolExecutor) -> int:
    """Descarga paralela; las rutas son relativas al directorio del VRT."""
    base = f"{BASE}/{vrt.parent.name}"
    jobs = [pool.submit(fetch, f"{base}/{rel}", vrt.parent / rel) for rel in rels]
    for j in jobs:
        j.result()
    return len(jobs)


def metric_grid() -> tuple:
    """Rejilla métrica de 250 m alineada, que cubre el país."""
    tr = Transformer.from_crs(C.CRS_STORAGE, C.CRS_METRIC, always_xy=True)
    xs, ys = tr.transform(
        [C.SV_BOUNDS[0], C.SV_BOUNDS[0], C.SV_BOUNDS[2], C.SV_BOUNDS[2]],
        [C.SV_BOUNDS[1], C.SV_BOUNDS[3], C.SV_BOUNDS[1], C.SV_BOUNDS[3]],
    )
    x0 = np.floor(min(xs) / RES_M) * RES_M
    y0 = np.floor(min(ys) / RES_M) * RES_M
    x1 = np.ceil(max(xs) / RES_M) * RES_M
    y1 = np.ceil(max(ys) / RES_M) * RES_M
    width = int(round((x1 - x0) / RES_M))
    height = int(round((y1 - y0) / RES_M))
    return from_origin(x0, y1, RES_M, RES_M), width, height


def read_depth(prop: str, depth: str, dst_tf, width, height) -> np.ndarray:
    """Lee una capa de profundidad y la reproyecta a la rejilla métrica."""
    vrt = load_vrt(prop, depth)
    with rasterio.open(vrt) as ds:
        w, s, e, n = C.SV_BOUNDS
        x0, y0 = Transformer.from_crs(C.CRS_STORAGE, ds.crs, always_xy=True)\
            .transform(w, s)
        x1, y1 = Transformer.from_crs(C.CRS_STORAGE, ds.crs, always_xy=True)\
            .transform(e, n)
        win = from_bounds(x0, y0, x1, y1, ds.transform).round_offsets().round_lengths()
        src = ds.read(1, window=win).astype(np.float32)
        # La ventana incluye océano (nodata de SoilGrids, que solo modela
        # tierra). Se lee con margen para que la reproyección no corte bordes.
        win = rasterio.windows.Window(win.col_off - 2, win.row_off - 2,
                                      win.width + 4, win.height + 4)
        src = ds.read(1, window=win).astype(np.float32)
        src[src == ds.nodata] = np.nan
        src_tf = ds.window_transform(win)
        src_crs = ds.crs

    dst = np.full((height, width), np.nan, dtype=np.float32)
    reproject(source=src, destination=dst, src_transform=src_tf,
              src_crs=src_crs, dst_transform=dst_tf, dst_crs=C.CRS_METRIC,
              src_nodata=np.nan, dst_nodata=np.nan,
              resampling=Resampling.bilinear)

    # La interpolación bilineal devuelve NaN en la franja costera, donde algún
    # vecino de 250 m cae en océano. Esos huecos se rellenan con el vecino más
    # cercano (dato real, sin inventar valores) para no perder suelo costero.
    gaps = ~np.isfinite(dst)
    if gaps.any():
        near = np.full((height, width), np.nan, dtype=np.float32)
        reproject(source=src, destination=near, src_transform=src_tf,
                  src_crs=src_crs, dst_transform=dst_tf, dst_crs=C.CRS_METRIC,
                  src_nodata=np.nan, dst_nodata=np.nan,
                  resampling=Resampling.nearest)
        dst[gaps] = near[gaps]
    return dst


def write_cog(arr: np.ndarray, path: Path, dst_tf, scale: float) -> None:
    data = np.where(np.isfinite(arr), np.round(arr / scale), NODATA).astype(np.int16)
    tmp = C.INTERIM / (path.stem + "_tmp.tif")
    C.INTERIM.mkdir(parents=True, exist_ok=True)
    profile = dict(driver="GTiff", height=data.shape[0], width=data.shape[1],
                   count=1, dtype="int16", crs=C.CRS_METRIC, transform=dst_tf,
                   nodata=NODATA, tiled=True, blockxsize=512, blockysize=512,
                   compress="DEFLATE", predictor=2, zlevel=6, BIGTIFF="IF_SAFER")
    with rasterio.open(tmp, "w", **profile) as ds:
        ds.write(data, 1)
        ds.scales = (scale,)
    if path.exists():
        path.unlink()
    rio_copy(tmp, path, driver="COG", compress="DEFLATE", predictor=2,
             blocksize=512, overview_resampling="average", RESAMPLING="AVERAGE")
    tmp.unlink(missing_ok=True)


def main() -> int:
    t0 = time.time()
    print("=" * 66)
    print(" MÓDULO 4 — SUELOS (SoilGrids 2.0)")
    print("=" * 66)
    C.SOILS_RASTER_DIR.mkdir(parents=True, exist_ok=True)

    dst_tf, width, height = metric_grid()
    print(f"rejilla: {width} x {height} px @ {RES_M:.0f} m  ({C.CRS_METRIC})")

    depts = gpd.read_file(C.TERRITORY_GPKG, layer="adm1").to_crs(C.CRS_METRIC)
    national = depts.union_all()
    mask = rasterize([(national, 1)], out_shape=(height, width),
                     transform=dst_tf, fill=0, dtype="uint8").astype(bool)
    # SoilGrids solo modela TIERRA: los cuerpos de agua interiores son nodata
    # por diseño (Ilopango, Coatepeque, Cerrón Grande…). La cobertura se mide
    # sobre tierra firme para no penalizar un hueco que no es un error.
    water = gpd.read_file(C.INFRA_GPKG, layer="water_bodies").to_crs(C.CRS_METRIC)
    water_mask = rasterize([(g, 1) for g in water.geometry],
                           out_shape=(height, width), transform=dst_tf,
                           fill=0, dtype="uint8", all_touched=True).astype(bool)
    land_mask = mask & ~water_mask
    print(f"celdas dentro del país: {int(mask.sum()):,} "
          f"({mask.sum()*RES_M**2/1e6:,.0f} km²); de ellas {int(water_mask[mask].sum()):,} "
          f"en cuerpos de agua")
    print(f"tierra firme: {int(land_mask.sum()):,} celdas "
          f"({land_mask.sum()*RES_M**2/1e6:,.0f} km²)")

    # --- Descarga selectiva de teselas --------------------------------------
    print("\n-- teselas SoilGrids (solo las que cubren el país) --")
    total_tiles = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for prop in PROPS:
            for depth, _ in DEPTHS:
                vrt = load_vrt(prop, depth)
                with rasterio.open(vrt) as ds:
                    w, s, e, n = C.SV_BOUNDS
                    tr = Transformer.from_crs(C.CRS_STORAGE, ds.crs, always_xy=True)
                    x0, y0 = tr.transform(w, s)
                    x1, y1 = tr.transform(e, n)
                    win = from_bounds(x0, y0, x1, y1, ds.transform)
                rels = select_sources(vrt, win)
                total_tiles += download_tiles(vrt, rels, pool)
                print(f"  {prop:9s} {depth:7s}: {len(rels)} teselas")
    print(f"  total descargado: {total_tiles} teselas")

    # --- Lectura, media ponderada y escritura -------------------------------
    print("\n-- 0–30 cm (media ponderada por espesor) --")
    rasters: dict[str, np.ndarray] = {}
    depth_coverage: dict[str, float] = {}
    for prop, (unit, scale, _) in PROPS.items():
        acc = np.zeros((height, width), dtype=np.float32)
        wsum = np.zeros((height, width), dtype=np.float32)
        for depth, weight in DEPTHS:
            layer = read_depth(prop, depth, dst_tf, width, height)
            good = np.isfinite(layer) & mask
            acc[good] += layer[good] * weight
            wsum[good] += weight
        out = np.where(wsum > 0, acc / np.maximum(wsum, 1e-6), np.nan)
        out[~mask] = np.nan
        rasters[prop] = out * scale  # de entero almacenado a unidad física
        depth_coverage[prop] = float(np.isfinite(out[land_mask]).mean())
        path = C.SOILS_RASTER_DIR / f"{prop}_0-30cm.tif"
        write_cog(rasters[prop], path, dst_tf, scale)
        vals = rasters[prop][mask & np.isfinite(rasters[prop])]
        print(f"  {prop:9s} {unit:5s} media={vals.mean():8.2f} "
              f"p10={np.percentile(vals,10):7.2f} p90={np.percentile(vals,90):7.2f}")

    # --- Validación ----------------------------------------------------------
    print("\n-- validación --")
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))

    for prop, (unit, _, rng) in PROPS.items():
        vals = rasters[prop][mask & np.isfinite(rasters[prop])]
        check(f"{prop} sin nodata sobre tierra firme",
              depth_coverage[prop] > 0.95,
              f"cobertura={depth_coverage[prop]:.2%} (agua excluida)")
        check(f"{prop} dentro de rango físico ({rng[0]}–{rng[1]} {unit})",
              bool(vals.min() >= rng[0] and vals.max() <= rng[1]),
              f"min={vals.min():.2f} max={vals.max():.2f}")

    texture = rasters["clay"] + rasters["sand"] + rasters["silt"]
    tv = texture[mask & np.isfinite(texture)]
    dev = np.abs(tv - 100.0)
    check("textura arcilla+arena+limo ≈ 100 % (desvío medio < 3)",
          float(dev.mean()) < 3.0,
          f"media={tv.mean():.1f}% desvío medio={dev.mean():.2f}")

    grid_ok = True
    for prop in PROPS:
        with rasterio.open(C.SOILS_RASTER_DIR / f"{prop}_0-30cm.tif") as ds:
            grid_ok &= (ds.crs.to_epsg() == 32616 and
                        abs(ds.res[0] - RES_M) < 1e-6 and
                        ds.width == width and ds.height == height)
    check("las 6 capas comparten rejilla 250 m EPSG:32616", bool(grid_ok))

    sv = rasters["soc"][mask & np.isfinite(rasters["soc"])]
    check("carbono orgánico medio plausible para suelos volcánicos (5–80 g/kg)",
          5 <= float(sv.mean()) <= 80, f"{sv.mean():.1f} g/kg")

    if any(not c["passed"] for c in checks):
        print("\nERROR: validación de suelos fallida.")
        return 1

    # --- Estadística por departamento ---------------------------------------
    print("\n-- medias por departamento --")
    stats: dict[str, dict] = {}
    for _, row in depts.iterrows():
        m = rasterize([(row.geometry, 1)], out_shape=(height, width),
                      transform=dst_tf, fill=0, dtype="uint8").astype(bool)
        n = int(m.sum())
        if n == 0:
            continue
        entry = {"name": row["name"], "pixels": n}
        for prop in ("phh2o", "soc", "clay", "nitrogen"):
            v = rasters[prop][m & np.isfinite(rasters[prop])]
            entry[prop] = round(float(v.mean()), 2) if v.size else None
        stats[row["adm1_code"]] = entry
    print(f"  departamentos: {len(stats)}/14")
    check("medias de suelo para los 14 departamentos", len(stats) == 14)

    out = {
        "source": {
            "name": "SoilGrids 2.0 (ISRIC — World Soil Information)",
            "url": "https://files.isric.org/soilgrids/latest/data/",
            "access": "WebDAV (VRT global en Interrupted Goode Homolosine)",
            "license": "CC BY 4.0",
            "native_resolution_m": 250,
            "depth": "0–30 cm (media ponderada 5/30, 10/30, 15/30)",
        },
        "grid": {"crs": C.CRS_METRIC, "resolution_m": RES_M,
                 "width": width, "height": height},
        "variables": {p: {"unit": u, "scale": s, "range": list(r)}
                      for p, (u, s, r) in PROPS.items()},
        "country_means": {p: round(float(rasters[p][mask & np.isfinite(rasters[p])].mean()), 2)
                          for p in PROPS},
        "depth_coverage": {p: round(v, 4) for p, v in depth_coverage.items()},
        "coverage_note": (
            "Cobertura medida sobre tierra firme: se excluyen los polígonos de "
            "cuerpos de agua de OpenStreetMap porque SoilGrids solo modela "
            "tierra. Las celdas de 250 m que cruzan la costa o un cuerpo de "
            "agua no mapeado pueden seguir siendo nodata."),
        "departments": stats,
        "national_sources": [
            {"name": "Mapa Digital de Suelos de El Salvador (CENTA/MAG/CRS)",
             "url": "https://www.centa.gob.sv/mapa-digital-de-suelos/",
             "status": "identificado, no integrado",
             "reason": ("plataforma ArcGIS Hub sin endpoint estable de descarga "
                        "ni licencia explícita de reutilización; requiere "
                        "contacto institucional")},
            {"name": "Soil in El Salvador (World Bank Data Catalog, 2017)",
             "url": "https://datacatalog.worldbank.org/search/dataset/0039929",
             "license": "CC BY 4.0",
             "status": "identificado, no integrado en esta fase",
             "reason": ("clasificación de suelos (polígonos) descargable; se "
                        "integrará como capa de clases separada de las "
                        "predicciones continuas de SoilGrids")},
        ],
        "caveats": [
            "SoilGrids son PREDICCIONES de un modelo global a 250 m; no son "
            "mediciones de laboratorio ni representan variabilidad intra-parcela.",
            "La textura se deriva de las mismas predicciones: su suma ≈100 % es "
            "una comprobación de coherencia interna, no una validación externa.",
            "El Mapa Digital de Suelos del CENTA (resolución de parcela, ~11.000 "
            "muestras) es la referencia nacional y debe preferirse cuando se "
            "obtenga acceso.",
        ],
        "validation": checks,
        "attribution": C.ATTRIBUTION["soilgrids"],
    }
    (C.SOILS_DIR / "soils_stats.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    for prop, (unit, scale, _) in PROPS.items():
        write_manifest(
            C.SOILS_RASTER_DIR / f"{prop}_0-30cm.tif", layer=f"soil_{prop}",
            source_id="soilgrids2", source_url=out["source"]["url"],
            license="CC-BY-4.0", attribution=C.ATTRIBUTION["soilgrids"],
            native_resolution="250 m (Goode Homolosine)",
            effective_resolution="250 m, remuestreado bilineal a EPSG:32616",
            transform="teselas VRT WebDAV -> ventana SV -> reproyección -> "
                      "media ponderada 0–30 cm -> COG",
            extra={"unit": unit, "stored_scale": scale,
                   "depth": "0-30cm", "prediction_not_measurement": True},
        )

    print(f"\nOK — Módulo 4 completado en {time.time()-t0:.1f} s")
    print(f"  {C.SOILS_RASTER_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
