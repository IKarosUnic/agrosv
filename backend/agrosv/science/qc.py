"""Control de calidad geoespacial.

Comprueba propiedades que, si fallan, invalidan cualquier estadística derivada:
CRS declarado, resolución positiva, cobertura de dato válido, geometrías
válidas, duplicados y alineación de rejilla. No «limpia» datos: informa. La
decisión de corregir es del pipeline, y queda registrada en la procedencia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""
    severity: str = "error"  # "error" invalida la capa; "warning" solo informa

    def as_dict(self) -> dict[str, Any]:
        return {"check": self.name, "passed": self.passed,
                "detail": self.detail, "severity": self.severity}


@dataclass
class QCReport:
    artifact: str
    kind: str
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str = "",
            severity: str = "error") -> None:
        self.checks.append(Check(name, bool(passed), detail, severity))

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "error")

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact": self.artifact,
            "kind": self.kind,
            "ok": self.ok,
            "failed": [c.as_dict() for c in self.checks
                       if not c.passed and c.severity == "error"],
            "warnings": [c.as_dict() for c in self.checks
                         if not c.passed and c.severity == "warning"],
            "checks": [c.as_dict() for c in self.checks],
        }


def qc_raster(path: Path, *, expected_crs: str | None = None,
              max_nodata_ratio: float | None = None,
              max_res_deg: float | None = None) -> QCReport:
    """QC de un ráster: CRS, rejilla, nodata y rango físico.

    `max_nodata_ratio` es opcional a propósito: en una capa nacional el
    rectángulo envolvente incluye mar y territorio vecino, de modo que un
    umbral fijo marcaría como defecto una cobertura correcta. Sin umbral, la
    cobertura se informa como advertencia medida, no como fallo; la capa que
    exija un umbral lo declara y entonces sí falla.
    """
    report = QCReport(artifact=str(path), kind="raster")
    if not path.exists():
        report.add("artefacto presente", False, "no existe")
        return report
    with rasterio.open(path) as ds:
        report.add("CRS declarado", ds.crs is not None, str(ds.crs))
        if expected_crs:
            report.add("CRS esperado", str(ds.crs) == expected_crs,
                       f"esperado {expected_crs}, leído {ds.crs}")
        report.add("resolución positiva", all(r > 0 for r in ds.res),
                   f"{ds.res[0]:.8g} x {ds.res[1]:.8g}")
        report.add("rejilla sin rotación",
                   ds.transform.b == 0 and ds.transform.d == 0,
                   f"b={ds.transform.b} d={ds.transform.d}")
        if max_res_deg is not None:
            report.add(
                "resolución no más fina que la fuente",
                max(abs(r) for r in ds.res) >= max_res_deg - 1e-12,
                f"res={max(abs(r) for r in ds.res):.8g} >= {max_res_deg}",
            )
        data = ds.read(1, masked=True)
        valid = int(data.count())
        total = int(ds.width * ds.height)
        ratio = 1.0 - valid / total if total else 1.0
        if max_nodata_ratio is None:
            report.add("cobertura de dato válido", True,
                       f"nodata={ratio:.2%} (sin umbral declarado)",
                       severity="warning")
        else:
            report.add("cobertura de dato válido", ratio <= max_nodata_ratio,
                       f"nodata={ratio:.2%} (máx {max_nodata_ratio:.0%})")
        report.add("hay celdas válidas", valid > 0, f"{valid:,} celdas")

        # Un ráster con un único valor repetido no aporta información: es el
        # síntoma típico de una máscara mal aplicada o de una descarga vacía.
        if valid:
            arr = data.compressed()
            report.add("variabilidad no nula",
                       float(arr.min()) != float(arr.max()),
                       f"min={float(arr.min()):.4g} max={float(arr.max()):.4g}")
            report.add("sin NaN dentro de la máscara",
                       not bool(np.isnan(arr).any()),
                       "valores finitos", severity="warning")
    return report


def qc_vector(path: Path, layer: str | None = None, *,
              expected_crs: str | None = None,
              bounds: tuple[float, float, float, float] | None = None) -> QCReport:
    """QC vectorial: CRS, validez, vacíos, duplicados y cobertura de bbox."""
    import geopandas as gpd
    from shapely import normalize

    report = QCReport(artifact=f"{path}:{layer or ''}".rstrip(":"), kind="vector")
    if not path.exists():
        report.add("artefacto presente", False, "no existe")
        return report
    gdf = gpd.read_file(path, layer=layer)
    report.add("capa no vacía", len(gdf) > 0, f"{len(gdf)} entidades")
    report.add("CRS declarado", gdf.crs is not None, str(gdf.crs))
    if expected_crs and gdf.crs is not None:
        report.add("CRS esperado", str(gdf.crs) == expected_crs,
                   f"esperado {expected_crs}, leído {gdf.crs}")
    if len(gdf) == 0:
        return report

    geoms = gdf.geometry
    report.add("sin geometrías nulas", int(geoms.isna().sum()) == 0,
               f"{int(geoms.isna().sum())} nulas")
    report.add("sin geometrías vacías", int(geoms.is_empty.sum()) == 0,
               f"{int(geoms.is_empty.sum())} vacías")
    valid = geoms[geoms.notna() & ~geoms.is_empty]
    invalid = int((~valid.is_valid).sum())
    report.add("geometrías válidas", invalid == 0, f"{invalid} inválidas")

    # Duplicados por geometría normalizada: dos polígonos idénticos con
    # coordenadas en orden distinto siguen siendo el mismo registro.
    hashes = [hash(normalize(g).wkb) for g in valid]
    dupes = len(hashes) - len(set(hashes))
    report.add("sin geometrías duplicadas", dupes == 0, f"{dupes} duplicadas",
               severity="warning")

    if bounds and gdf.crs is not None:
        west, south, east, north = bounds
        minx, miny, maxx, maxy = gdf.to_crs("EPSG:4326").total_bounds
        inside = (minx >= west - 0.01 and miny >= south - 0.01
                  and maxx <= east + 0.01 and maxy <= north + 0.01)
        report.add("extensión dentro del área declarada", inside,
                   f"bounds={minx:.4f},{miny:.4f},{maxx:.4f},{maxy:.4f}")
    return report


def qc_summary(paths: list[Path], *, layer: str | None = None) -> dict[str, Any]:
    """Ejecuta QC sobre una lista de artefactos y resume el resultado."""
    reports = []
    for path in paths:
        is_raster = path.suffix.lower() in {".tif", ".tiff"}
        reports.append((qc_raster(path) if is_raster
                        else qc_vector(path, layer=layer)).as_dict())
    return {
        "artifacts": len(reports),
        "ok": all(r["ok"] for r in reports),
        "failed_artifacts": [r["artifact"] for r in reports if not r["ok"]],
        "reports": reports,
    }
