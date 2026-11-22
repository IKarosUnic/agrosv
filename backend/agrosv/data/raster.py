"""AGROSV — gestión de datos ráster (Fase 4, §7).

Reglas:

* Un ráster se lee **por ventanas o por bloques**; nunca se carga el país entero
  en memoria si se puede evitar (`iter_blocks`, `read_window`).
* Si se remuestrea a una resolución más gruesa, la operación queda registrada y
  el producto declara `effective_resolution` distinta de la nativa. Si se
  remuestrea a una resolución **más fina**, se lanza `ResolutionInflationError`:
  interpolar no crea información.
* El NoData se declara y se comprueba. Un ráster sin NoData declarado pero con
  un centinela (p. ej. -9999) es un defecto que el QC reporta.
* La elección de contenedor (COG, NetCDF, Zarr) se justifica por patrón de
  acceso, no por preferencia.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject, transform_bounds
from rasterio.windows import Window, from_bounds

from .. import config as C

#: Nombres de remuestreo aceptados, con su efecto declarado.
RESAMPLING_METHODS: dict[str, str] = {
    "nearest": "conserva valores originales; adecuado para clases y máscaras",
    "bilinear": "interpola 2x2; suaviza; no válido para clases",
    "cubic": "interpola 4x4; puede sobrepasar el rango original",
    "average": "media de celdas de origen; correcto al agregar resolución",
    "mode": "clase dominante; adecuado para cobertura terrestre",
    "max": "máximo; conserva extremos (p. ej. profundidad de inundación)",
    "min": "mínimo; conserva extremos negativos",
}

COG_BLOCK_SIZES = {256, 512, 1024}


def safe_block(size: int) -> int:
    """Bloque teselado válido para un ráster de ancho/alto `size`.

    GTiff exige bloques múltiplos de 16 y no mayores que la imagen; usar 512 en
    un recorte de 50 píxeles produce un archivo inválido.
    """
    if size >= 512:
        return 512
    if size >= 256:
        return 256
    return max(16, (int(size) // 16) * 16)


class ResolutionInflationError(ValueError):
    """Se intentó aumentar la resolución declarada de una fuente."""


class RasterGridError(ValueError):
    """Dos rásteres que debían compartir rejilla no la comparten."""


@dataclass
class RasterProfile:
    path: str
    driver: str
    crs: str | None
    width: int
    height: int
    count: int
    dtype: str
    nodata: float | None
    res: tuple[float, float]
    bounds: tuple[float, float, float, float]
    tiled: bool
    block_shape: tuple[int, int] | None
    compress: str | None
    overviews: list[int]
    pixel_area_m2: float | None
    cog_heuristic: bool
    cog_notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "driver": self.driver,
            "crs": self.crs,
            "width": self.width,
            "height": self.height,
            "count": self.count,
            "dtype": self.dtype,
            "nodata": self.nodata,
            "nodata_declared": self.nodata is not None,
            "res": list(self.res),
            "bounds": list(self.bounds),
            "tiled": self.tiled,
            "block_shape": list(self.block_shape) if self.block_shape else None,
            "compress": self.compress,
            "overviews": self.overviews,
            "pixel_area_m2": self.pixel_area_m2,
            "cog_heuristic": self.cog_heuristic,
            "cog_notes": self.cog_notes,
            "note": ("cog_heuristic es una comprobación estructural, no una "
                     "certificación de Cloud Optimized GeoTIFF"),
        }


def _pixel_area_m2(crs: str | None, res: tuple[float, float],
                   bounds: tuple[float, float, float, float]) -> float | None:
    """Área aproximada de píxel en m² en el centro de la imagen."""
    if not crs:
        return None
    import pyproj

    parsed = pyproj.CRS.from_user_input(crs)
    if parsed.is_projected:
        unit = parsed.axis_info[0].unit_conversion_factor if parsed.axis_info else 1.0
        return abs(res[0] * res[1]) * float(unit) ** 2
    lat = (bounds[1] + bounds[3]) / 2
    m_per_deg_lat = 111_132.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
    return abs(res[0] * m_per_deg_lon * res[1] * m_per_deg_lat)


def profile_raster(path: Path | str) -> RasterProfile:
    """Lee solo la cabecera y un bloque de metadatos; no carga el ráster."""
    p = Path(path)
    with rasterio.open(p) as ds:
        notes: list[str] = []
        block = ds.block_shapes[0] if ds.block_shapes else None
        overviews = [int(o) for o in ds.overviews(1)] if ds.count else []
        compress = ds.profile.get("compress")
        cog = True
        if ds.driver != "GTiff":
            cog = False
            notes.append(f"driver {ds.driver} (COG exige GTiff)")
        if not ds.profile.get("tiled"):
            cog = False
            notes.append("no está teselado: la lectura por ventana degrada")
        if block and block[0] not in COG_BLOCK_SIZES:
            notes.append(f"bloque {block} distinto de 256/512/1024")
        if not overviews:
            cog = False
            notes.append("sin overviews: zoom-out obliga a leer resolución completa")
        if not compress:
            notes.append("sin compresión declarada")
        if ds.nodata is None:
            notes.append("NoData no declarado")
        return RasterProfile(
            path=str(p), driver=ds.driver, crs=str(ds.crs) if ds.crs else None,
            width=ds.width, height=ds.height, count=ds.count,
            dtype=ds.dtypes[0], nodata=ds.nodata,
            res=(abs(ds.res[0]), abs(ds.res[1])),
            bounds=tuple(ds.bounds),  # type: ignore[arg-type]
            tiled=bool(ds.profile.get("tiled")),
            block_shape=(int(block[0]), int(block[1])) if block else None,
            compress=str(compress) if compress else None,
            overviews=overviews,
            pixel_area_m2=_pixel_area_m2(str(ds.crs) if ds.crs else None,
                                         (abs(ds.res[0]), abs(ds.res[1])),
                                         tuple(ds.bounds)),  # type: ignore[arg-type]
            cog_heuristic=cog, cog_notes=notes,
        )


def iter_blocks(path: Path | str, *, band: int = 1,
                masked: bool = True) -> Iterator[tuple[Window, np.ndarray]]:
    """Itera los bloques nativos del archivo (no todo el ráster a la vez)."""
    with rasterio.open(path) as ds:
        for _, window in ds.block_windows(band):
            data = ds.read(band, window=window, masked=masked)
            yield window, data


def read_window(path: Path | str, bounds: tuple[float, float, float, float],
                *, band: int = 1, bounds_crs: str = "EPSG:4326",
                masked: bool = True) -> tuple[np.ndarray, Any]:
    """Ventana por extensión, reproyectando el bbox al CRS del ráster."""
    with rasterio.open(path) as ds:
        if ds.crs is None:
            raise RasterGridError("el ráster no declara CRS")
        b = transform_bounds(bounds_crs, ds.crs, *bounds)
        win = from_bounds(*b, transform=ds.transform)
        data = ds.read(band, window=win, masked=masked)
        return data, rasterio.windows.transform(win, ds.transform)


def window_stats(path: Path | str, bounds: tuple[float, float, float, float],
                 *, band: int = 1) -> dict[str, Any]:
    """Estadísticas de una ventana sin cargar el archivo completo."""
    data, _ = read_window(path, bounds, band=band, masked=True)
    arr = np.asarray(data, dtype="float64")
    valid = arr[~np.ma.getmaskarray(data)] if np.ma.isMaskedArray(data) else arr
    valid = valid[np.isfinite(valid)]
    if valid.size == 0:
        return {"cells": 0, "note": "ventana sin celdas válidas"}
    return {
        "cells": int(valid.size),
        "min": float(valid.min()), "max": float(valid.max()),
        "mean": float(valid.mean()), "median": float(np.median(valid)),
        "p10": float(np.percentile(valid, 10)),
        "p90": float(np.percentile(valid, 90)),
        "masked_cells": int(np.size(arr) - valid.size),
    }


@dataclass
class ResampleOperation:
    source: str
    source_crs: str
    target_crs: str
    source_res: tuple[float, float]
    target_res: tuple[float, float]
    method: str
    degraded: bool
    reason: str
    native_resolution: str
    effective_resolution: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_crs": self.source_crs,
            "target_crs": self.target_crs,
            "source_res": list(self.source_res),
            "target_res": list(self.target_res),
            "method": self.method,
            "degraded": self.degraded,
            "reason": self.reason,
            "native_resolution": self.native_resolution,
            "effective_resolution": self.effective_resolution,
            "rule": ("un producto remuestreado nunca declara la resolución "
                     "nativa de la fuente"),
        }


def plan_reproject(path: Path | str, target_crs: str, *,
                   target_res: float | None = None,
                   method: str = "nearest",
                   reason: str = "") -> ResampleOperation:
    """Calcula la operación y rechaza el aumento de resolución declarado."""
    if method not in RESAMPLING_METHODS:
        raise ValueError(f"método no soportado: {method}; use {sorted(RESAMPLING_METHODS)}")
    profile = profile_raster(path)
    if not profile.crs:
        raise RasterGridError("el ráster no declara CRS")
    source_res = max(profile.res)
    target = target_res if target_res is not None else source_res
    if target < source_res * 0.999:
        raise ResolutionInflationError(
            f"resolución destino {target} < origen {source_res}: interpolar no "
            "crea información. Use target_res >= resolución nativa y documente "
            "la incertidumbre."
        )
    degraded = target > source_res * 1.001
    return ResampleOperation(
        source=profile.path, source_crs=profile.crs, target_crs=str(target_crs),
        source_res=profile.res, target_res=(target, target), method=method,
        degraded=degraded, reason=reason,
        native_resolution=f"{source_res:g}",
        effective_resolution=(f"{target:g} (remuestreado desde {source_res:g})"
                              if degraded else f"{source_res:g} (nativo)"),
    )


def reproject_to_file(path: Path | str, out_path: Path | str, target_crs: str, *,
                      target_res: float | None = None, method: str = "nearest",
                      reason: str = "", nodata: float | None = None) -> dict[str, Any]:
    """Reproyecta por bloques declarados y escribe un GeoTIFF teselado."""
    op = plan_reproject(path, target_crs, target_res=target_res,
                        method=method, reason=reason)
    p, out = Path(path), Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(p) as src:
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds,
            resolution=(op.target_res[0], op.target_res[1])
            if target_res else None,
        )
        profile = src.profile.copy()
        profile.update({
            "crs": target_crs, "transform": transform,
            "width": width, "height": height,
            "driver": "GTiff", "tiled": True,
            "blockxsize": safe_block(width), "blockysize": safe_block(height),
            "compress": "deflate",
            "nodata": nodata if nodata is not None else src.nodata,
            "BIGTIFF": "IF_SAFER",
        })
        with rasterio.open(out, "w", **profile) as dst:
            # `reproject` escribe por bloques de destino: no materializa el
            # ráster completo en memoria.
            reproject(
                source=rasterio.band(src, 1), destination=rasterio.band(dst, 1),
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=transform, dst_crs=target_crs,
                resampling=getattr(Resampling, method),
                src_nodata=src.nodata,
                dst_nodata=profile["nodata"],
            )
    op_payload = op.as_dict()
    op_payload["output"] = str(out)
    op_payload["output_profile"] = profile_raster(out).as_dict()
    return op_payload


def clip_to_file(path: Path | str, out_path: Path | str,
                 bounds: tuple[float, float, float, float], *,
                 bounds_crs: str = "EPSG:4326") -> dict[str, Any]:
    """Recorta por extensión conservando la rejilla nativa (sin remuestreo)."""
    src_p = Path(path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(src_p) as src:
        b = transform_bounds(bounds_crs, src.crs, *bounds)
        win = from_bounds(*b, transform=src.transform)
        # Alinear a la rejilla entera evita media celda desplazada.
        win = win.round_offsets().round_lengths()
        profile = src.profile.copy()
        profile.update({
            "height": int(win.height), "width": int(win.width),
            "transform": rasterio.windows.transform(win, src.transform),
            "driver": "GTiff", "tiled": True,
            "blockxsize": safe_block(int(win.width)),
            "blockysize": safe_block(int(win.height)),
            "compress": "deflate", "BIGTIFF": "IF_SAFER",
        })
        with rasterio.open(out, "w", **profile) as dst:
            data = src.read(window=win)
            dst.write(data)
            if profile.get("nodata") is None:
                profile["nodata"] = None
    return {
        "source": str(src_p),
        "output": str(out),
        "bounds": list(bounds),
        "window": [int(win.col_off), int(win.row_off),
                   int(win.width), int(win.height)],
        "resampling": "none",
        "native_resolution": profile_raster(src_p).res,
        "profile": profile_raster(out).as_dict(),
    }


def assert_same_grid(paths: list[Path | str], *,
                     tolerance: float = 1e-9) -> dict[str, Any]:
    """Comprueba que varios rásteres comparten CRS, rejilla y extensión."""
    profiles = [profile_raster(p) for p in paths]
    if not profiles:
        return {"ok": False, "detail": "sin rásteres"}
    base = profiles[0]
    problems: list[str] = []
    for other in profiles[1:]:
        if other.crs != base.crs:
            problems.append(f"{other.path}: CRS {other.crs} != {base.crs}")
        if (abs(other.res[0] - base.res[0]) > tolerance
                or abs(other.res[1] - base.res[1]) > tolerance):
            problems.append(f"{other.path}: resolución {other.res} != {base.res}")
        if (other.width, other.height) != (base.width, base.height):
            problems.append(
                f"{other.path}: forma {other.width}x{other.height} != "
                f"{base.width}x{base.height}")
        if any(abs(a - b) > tolerance for a, b in zip(other.bounds, base.bounds)):
            problems.append(f"{other.path}: extensión distinta")
    return {"ok": not problems, "checked": len(profiles),
            "problems": problems,
            "reference": base.path,
            "note": "rejilla idéntica ≠ precisión idéntica"}


CONTAINER_GUIDE: dict[str, Any] = {
    "cog": {
        "use_when": ("un ráster por variable, lecturas por ventana o teselas, "
                     "tamaño nacional o menor"),
        "why": "lectura por rango HTTP y por bloque; un solo archivo por producto",
        "limits": "no representa series multivariable ni cubos temporales",
    },
    "netcdf": {
        "use_when": ("varias variables y dimensión temporal con convenciones CF, "
                     "series climáticas"),
        "why": "metadatos CF completos y compatibilidad con xarray/ERA5/CHIRPS",
        "limits": "lectura por bloque menos eficiente que COG en HTTP simple",
    },
    "zarr": {
        "use_when": ("cubos temporales grandes, escritura paralela, acceso "
                     "por chunks desde varios procesos"),
        "why": "chunks independientes y almacenamiento fragmentado",
        "limits": "requiere gestor de chunks y no es un archivo único",
    },
}


def choose_container(*, temporal: bool, variables: int,
                     access: str = "window") -> dict[str, Any]:
    """Recomienda contenedor con criterio explícito (no por preferencia)."""
    if temporal and variables >= 2:
        choice = "zarr" if access in {"parallel", "chunk"} else "netcdf"
    elif temporal and access in {"parallel", "chunk"}:
        choice = "zarr"
    else:
        choice = "cog"
    return {"container": choice, **CONTAINER_GUIDE[choice],
            "decided_by": {"temporal": temporal, "variables": variables,
                           "access": access}}


def sample_points(path: Path | str, lon: list[float], lat: list[float], *,
                  source_crs: str = "EPSG:4326",
                  band: int = 1) -> list[float | None]:
    """Muestreo puntual por ventana de 1 píxel; no lee el ráster completo."""
    import pyproj

    with rasterio.open(path) as ds:
        if ds.crs is None:
            raise RasterGridError("el ráster no declara CRS")
        tr = pyproj.Transformer.from_crs(source_crs, ds.crs, always_xy=True)
        xs, ys = tr.transform(lon, lat)
        out: list[float | None] = []
        for x, y in zip(xs, ys):
            try:
                row, col = ds.index(x, y)
                win = Window(col, row, 1, 1)
                val = ds.read(band, window=win, masked=True)
                if not val.size or np.ma.is_masked(val[0, 0]):
                    out.append(None)
                    continue
                v = float(val[0, 0])
            except Exception:  # noqa: BLE001 — fuera de extensión
                v = None
            if v is None or not np.isfinite(v) or v == ds.nodata:
                out.append(None)
            else:
                out.append(v)
        return out


def undeclared_nodata_candidates(path: Path | str, *, band: int = 1,
                                 sentinels: tuple[float, ...] = (-9999.0, -999.0,
                                                                32767.0, 255.0)
                                 ) -> dict[str, Any]:
    """Busca centinelas de NoData en un ráster que no los declara."""
    profile = profile_raster(path)
    if profile.nodata is not None:
        return {"declared": True, "nodata": profile.nodata,
                "suspicious": [], "note": "NoData declarado"}
    with rasterio.open(path) as ds:
        data = ds.read(band)
    found = []
    for sentinel in sentinels:
        count = int(np.count_nonzero(data == sentinel))
        if count:
            found.append({"value": sentinel, "cells": count,
                          "pct": round(100 * count / data.size, 3)})
    return {"declared": False, "nodata": None, "suspicious": found,
            "note": ("un centinela frecuente sin NoData declarado es un defecto "
                     "de metadatos: el motor de calidad no debe interpretarlo "
                     "como valor observado")}
