"""Error vertical del DEM a partir de puntos de control GNSS.

El DEM Copernicus GLO-30 es un **DSM** (superficie) con altitudes
ortométricas EGM2008. Un punto GNSS puede aportar altura ortométrica o altura
elipsoidal más ondulación del geoide; en el segundo caso se convierte
`H = h − N`. No se usa un geoide implícito: el modelo debe declararse.

No se declara una exactitud que no se haya medido: si no hay puntos, el
resultado es `available: false`.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from ..engines import governance as G5
from . import validators

DEM_DATASET = "copdem30"
DEM_VERTICAL_DATUM = "EGM2008"
DEM_CELL_SUPPORT = "30 m (GLO-30)"


def _rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return [{(k or "").strip(): (v.strip() if isinstance(v, str) else v)
                 for k, v in row.items() if k is not None}
                for row in csv.DictReader(handle)]


def dem_error(path: str | Path) -> dict[str, Any]:
    report = validators.validate_gnss(path)
    if not report["valid"]:
        raise ValueError(f"GNSS inválido: {report['errors'][:5]}")
    rows = _rows(path)
    from ..engines.terrain import sample_elevation

    points: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in rows:
        lon = float(row["longitude"])
        lat = float(row["latitude"])
        height, method = validators._orthometric(row)
        try:
            dem = sample_elevation(lon, lat)
        except (G5.SourceUnavailableError, FileNotFoundError, OSError) as exc:
            return {
                "available": False,
                "reason": f"DEM no disponible: {exc}",
                "dem_dataset": DEM_DATASET,
                "n_points": len(rows),
            }
        if dem is None:
            skipped.append({"point_id": row["point_id"],
                            "reason": "celda NoData o fuera de cobertura"})
            continue
        diff = float(dem) - float(height)
        points.append({
            "point_id": row["point_id"],
            "longitude": lon,
            "latitude": lat,
            "height_method": method,
            "gnss_height_m": round(float(height), 3),
            "dem_height_m": round(float(dem), 3),
            "difference_m": round(diff, 3),
            "vertical_accuracy_m": float(row["vertical_accuracy_m"]),
            "within_vertical_accuracy": abs(diff) <= float(
                row["vertical_accuracy_m"]),
        })
    if not points:
        return {
            "available": False,
            "reason": "ningún punto tiene dato en el DEM",
            "dem_dataset": DEM_DATASET,
            "skipped": skipped,
        }
    diffs = np.array([p["difference_m"] for p in points], dtype=float)
    abs_diff = np.abs(diffs)
    n = len(diffs)
    metrics = {
        "n": n,
        "bias_m": round(float(diffs.mean()), 3),
        "mae_m": round(float(abs_diff.mean()), 3),
        "rmse_m": round(float(np.sqrt(np.mean(diffs ** 2))), 3),
        "std_m": round(float(diffs.std(ddof=1)) if n > 1 else 0.0, 3),
        "p95_abs_m": round(float(np.percentile(abs_diff, 95)), 3),
        "min_m": round(float(diffs.min()), 3),
        "max_m": round(float(diffs.max()), 3),
        "within_vertical_accuracy_fraction": round(
            sum(1 for p in points if p["within_vertical_accuracy"]) / n, 3),
    }
    return {
        "available": True,
        "dem_dataset": DEM_DATASET,
        "dem_vertical_datum": DEM_VERTICAL_DATUM,
        "dem_cell_support": DEM_CELL_SUPPORT,
        "metrics": metrics,
        "points": points,
        "skipped": skipped,
        "height_methods": report["summary"].get("height_methods"),
        "assumptions": [
            "el DEM es un DSM: incluye dosel y edificaciones",
            "la altura GNSS se tomó como ortométrica o se convirtió con la "
            "ondulación declarada",
            "la comparación es puntual contra una celda de 30 m",
            "no se corrige por cambios de uso o de superficie entre fechas",
        ],
        "limitations": [
            "una muestra pequeña no representa el error nacional del DEM",
            "el DSM sobreestima la altura del terreno con vegetación o edificios",
            "la exactitud depende del levantamiento GNSS y su época",
            "no se evalúa el error horizontal",
        ],
        "synthetic": False,
        "is_official_dem_accuracy": False,
    }


__all__ = ["dem_error", "DEM_DATASET", "DEM_VERTICAL_DATUM",
           "DEM_CELL_SUPPORT"]
