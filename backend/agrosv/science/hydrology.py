"""Motor hidrológico determinista sobre un DEM (Módulo J, núcleo D8).

Implementa, sin dependencias externas de modelado:

  * relleno de sumideros por priority-flood (Barnes et al., 2014);
  * dirección de flujo D8 (O'Callaghan & Mark, 1984);
  * acumulación de flujo;
  * delimitación de cuenca aguas arriba desde una salida;
  * red de drenaje por umbral de área;
  * factor LS de RUSLE (Wischmeier & Smith, 1978; exposición de flujo).

Todo se calcula sobre una **ventana métrica**: la unidad de proceso es el área
de interés, no el país completo (SYSTEM_ARCHITECTURE.md §12.4). Un resultado
obtenido en una ventana truncada se declara truncado; el módulo no extrapola.

Advertencia científica: la proximidad a un cauce no implica disponibilidad de
agua. Este módulo produce agua **físicamente presente** (escorrentía potencial,
área aportante), nunca agua autorizada ni comprometida.
"""
from __future__ import annotations

import heapq
from typing import Any

import numpy as np

# Orden: NO, N, NE, O, E, SO, S, SE (fila, columna). El índice es el código D8.
DIRS: tuple[tuple[int, int], ...] = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)
NO_FLOW = 8
_DELTAS = np.array([d[0] * 100000 + d[1] for d in DIRS])  # solo para referencia


def fill_depressions(elevation: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Rellena sumideros con priority-flood.

    Las celdas sin dato (NaN) se tratan como borde: el relleno no inventa
    elevación donde no hay observación.
    """
    z = np.asarray(elevation, dtype=float)
    if z.ndim != 2:
        raise ValueError("se esperaba un array 2-D de elevación")
    h, w = z.shape
    valid = np.isfinite(z)
    out = z.copy()
    visited = ~valid
    heap: list[tuple[float, int, int]] = []

    def push(r: int, c: int) -> None:
        if visited[r, c]:
            return
        visited[r, c] = True
        heapq.heappush(heap, (float(out[r, c]), r, c))

    for c in range(w):
        push(0, c)
        push(h - 1, c)
    for r in range(h):
        push(r, 0)
        push(r, w - 1)

    raised = 0
    while heap:
        z0, r, c = heapq.heappop(heap)
        for dr, dc in DIRS:
            rr, cc = r + dr, c + dc
            if rr < 0 or rr >= h or cc < 0 or cc >= w or visited[rr, cc]:
                continue
            visited[rr, cc] = True
            if z[rr, cc] < z0:
                out[rr, cc] = z0
                raised += 1
            heapq.heappush(heap, (float(out[rr, cc]), rr, cc))

    return out, {"cells_raised": int(raised),
                 "raised_pct": round(100.0 * raised / max(int(valid.sum()), 1), 3)}


def d8_flow_direction(filled: np.ndarray, cellsize_m: float) -> tuple[np.ndarray, dict[str, Any]]:
    """Dirección de máxima pendiente descendente (código 0–7; 8 = sin salida)."""
    z = np.asarray(filled, dtype=float)
    if cellsize_m <= 0:
        raise ValueError("cellsize_m debe ser positivo")
    h, w = z.shape
    valid = np.isfinite(z)
    zf = np.where(valid, z, np.inf)
    best = np.full((h, w), -np.inf, dtype=float)
    code = np.full((h, w), NO_FLOW, dtype=np.uint8)

    for i, (dr, dc) in enumerate(DIRS):
        dist = cellsize_m * (2 ** 0.5 if dr and dc else 1.0)
        nb = np.full((h, w), np.inf, dtype=float)
        dst_r = slice(max(-dr, 0), h + min(-dr, 0))
        src_r = slice(max(dr, 0), h + min(dr, 0))
        dst_c = slice(max(-dc, 0), w + min(-dc, 0))
        src_c = slice(max(dc, 0), w + min(dc, 0))
        nb[dst_r, dst_c] = zf[src_r, src_c]
        with np.errstate(invalid="ignore", divide="ignore"):
            drop = (zf - nb) / dist
        better = np.isfinite(drop) & (drop > best) & (drop > 0)
        best = np.where(better, drop, best)
        code = np.where(better, i, code).astype(np.uint8)

    flat = valid & (code == NO_FLOW)
    return code, {"flat_or_outlet_cells": int(flat.sum()),
                  "flat_or_outlet_pct": round(100.0 * flat.sum() /
                                              max(int(valid.sum()), 1), 3)}


def flow_accumulation(directions: np.ndarray, filled: np.ndarray) -> np.ndarray:
    """Número de celdas que drenan por cada celda (incluida ella misma).

    Se procesa en orden descendente de elevación: en un DEM sin sumideros cada
    celda entrega su acumulación a una celda estrictamente más baja. En
    superficies planas creadas por el relleno el orden es arbitrario; el número
    de celdas planas se informa como diagnóstico y no se corrige en silencio.
    """
    z = np.asarray(filled, dtype=float)
    dirs = np.asarray(directions)
    valid = np.isfinite(z)
    h, w = z.shape
    acc = valid.astype(np.float64).ravel()
    dirs_flat = dirs.ravel()
    z_flat = z.ravel()
    deltas = np.array([d[0] * w + d[1] for d in DIRS])

    for idx in np.argsort(-z_flat, kind="stable"):
        code = int(dirs_flat[idx])
        if code >= NO_FLOW:
            continue
        target = int(idx) + int(deltas[code])
        if target < 0 or target >= acc.size:
            continue
        # Evita el «salto de fila»: un vecino en diagonal/este-oeste no puede
        # estar en otra fila tras el desplazamiento lineal de la rejilla.
        if abs((target % w) - (int(idx) % w)) > 1:
            continue
        acc[target] += acc[idx]
    return acc.reshape(h, w)


def watershed(directions: np.ndarray, seed: tuple[int, int],
              valid: np.ndarray | None = None) -> np.ndarray:
    """Cuenca aguas arriba desde una celda de salida (recorrido inverso D8)."""
    dirs = np.asarray(directions)
    h, w = dirs.shape
    valid = np.isfinite(dirs) if valid is None else np.asarray(valid)
    mask = np.zeros((h, w), dtype=bool)
    r0, c0 = seed
    if not (0 <= r0 < h and 0 <= c0 < w) or not valid[r0, c0]:
        return mask

    mask[r0, c0] = True
    stack = [(r0, c0)]
    while stack:
        r, c = stack.pop()
        for dr, dc in DIRS:
            rr, cc = r + dr, c + dc
            if rr < 0 or rr >= h or cc < 0 or cc >= w or mask[rr, cc] or not valid[rr, cc]:
                continue
            code = int(dirs[rr, cc])
            if code < NO_FLOW:
                tr, tc = DIRS[code]
                if rr + tr == r and cc + tc == c:
                    mask[rr, cc] = True
                    stack.append((rr, cc))
    return mask


def drainage_network(accumulation: np.ndarray, threshold_cells: int) -> np.ndarray:
    """Celdas de cauce: acumulación ≥ umbral declarado (no es un cauce oficial)."""
    if threshold_cells < 1:
        raise ValueError("threshold_cells debe ser ≥ 1")
    return np.asarray(accumulation) >= threshold_cells


def ls_factor(slope_deg: np.ndarray, accumulation: np.ndarray,
              cellsize_m: float) -> np.ndarray:
    """Factor LS de RUSLE.

    Pendiente: `65.41·sin²θ + 4.56·sinθ + 0.065` (Wischmeier & Smith, 1978).
    Longitud: longitud de flujo `λ = acumulación · celdas` con exponente m
    escalonado según la pendiente. Es una aproximación; RUSLE exige además
    R, K, C y P, que este módulo no calcula.
    """
    theta = np.radians(np.clip(np.asarray(slope_deg, dtype=float), 0.0, 90.0))
    s_fin = np.where(np.isfinite(theta), theta, 0.0)
    s_factor = 65.41 * np.sin(s_fin) ** 2 + 4.56 * np.sin(s_fin) + 0.065

    slope_frac = np.tan(s_fin)
    m = np.select(
        [slope_frac >= 0.05, slope_frac >= 0.035, slope_frac >= 0.01],
        [0.5, 0.4, 0.3],
        default=0.2,
    )
    lam = np.maximum(np.asarray(accumulation, dtype=float) * cellsize_m, cellsize_m)
    ls = (lam / 22.13) ** m * s_factor
    ls = np.where(np.isfinite(theta), ls, np.nan)
    return ls


def slope_degrees(filled: np.ndarray, cellsize_m: float) -> np.ndarray:
    """Pendiente en grados por diferencias finitas centrales (celdas métricas)."""
    z = np.asarray(filled, dtype=float)
    gy, gx = np.gradient(z, cellsize_m, cellsize_m)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def compute_aoi(
    elevation: np.ndarray,
    cellsize_m: float,
    *,
    stream_threshold_ratio: float = 0.01,
) -> dict[str, Any]:
    """Cadena completa sobre un área de interés y sus diagnósticos."""
    if not 0 < stream_threshold_ratio <= 1:
        raise ValueError("stream_threshold_ratio debe estar en (0, 1]")
    filled, fill_info = fill_depressions(elevation)
    dirs, dir_info = d8_flow_direction(filled, cellsize_m)
    acc = flow_accumulation(dirs, filled)
    valid = np.isfinite(filled)
    slopes = slope_degrees(np.where(valid, filled, 0.0), cellsize_m)
    slopes = np.where(valid, slopes, np.nan)
    ls = ls_factor(slopes, acc, cellsize_m)
    threshold = max(2, int(round(stream_threshold_ratio * max(int(valid.sum()), 1))))
    streams = drainage_network(acc, threshold)
    return {
        "filled": filled,
        "directions": dirs,
        "accumulation": acc,
        "slope_deg": slopes,
        "ls_factor": ls,
        "streams": streams,
        "diagnostics": {
            "cells": int(elevation.size),
            "valid_cells": int(valid.sum()),
            "cellsize_m": cellsize_m,
            "depressions": fill_info,
            "flow": dir_info,
            "stream_threshold_cells": threshold,
            "stream_threshold_ratio": stream_threshold_ratio,
            "max_accumulation": int(np.nanmax(acc)) if valid.any() else 0,
        },
    }


def outlet_cell(accumulation: np.ndarray) -> tuple[int, int]:
    """Celda con mayor acumulación (salida principal del área analizada)."""
    acc = np.nan_to_num(np.asarray(accumulation, dtype=float), nan=-1.0)
    r, c = np.unravel_index(int(np.argmax(acc)), acc.shape)
    return int(r), int(c)


def mask_to_geojson(mask: np.ndarray, transform: Any, crs: str) -> dict[str, Any]:
    """Poligoniza una máscara booleana a GeoJSON (RFC 7946)."""
    from rasterio.features import shapes

    feats = []
    for geom, value in shapes(mask.astype(np.uint8), mask=mask.astype(bool),
                              transform=transform):
        if int(value) != 1:
            continue
        feats.append({"type": "Feature", "properties": {"value": int(value)},
                      "geometry": geom})
    return {"type": "FeatureCollection", "crs": {"type": "name",
            "properties": {"name": crs}}, "features": feats}
