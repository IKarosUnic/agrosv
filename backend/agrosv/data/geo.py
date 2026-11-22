"""AGROSV — normalización geoespacial (Fase 4, §5).

Reglas que este módulo implementa y que no se pueden saltar:

* El CRS de origen **se conserva**: toda transformación devuelve un registro con
  el CRS original y el de destino, y no se sobrescribe el archivo de entrada.
* El área y la distancia se calculan en un CRS proyectado. Pedir `area_km2` de
  una capa en EPSG:4326 lanza `GeographicMetricError` en lugar de devolver un
  número en grados² que parezca kilómetros.
* La zona UTM se elige por extensión y se documenta el factor de escala. Para
  áreas grandes o comparaciones entre zonas se usa un CRS de área equivalente.
* Las geometrías se diagnostican y, si se reparan, se registra la operación
  completa (hash original, método, área antes/después). Nunca en silencio.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pyproj
from shapely import make_valid, normalize
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

from .. import config as C

EPSG_WGS84 = "EPSG:4326"
EPSG_EQUAL_AREA = C.CRS_EQUAL_AREA       # EPSG:6933 (igual área global)
EPSG_METRIC_DEFAULT = C.CRS_METRIC       # EPSG:32616 (UTM 16N)


class GeographicMetricError(ValueError):
    """Se pidió una métrica en un CRS geográfico."""


class CRSConversionError(ValueError):
    """El CRS no se puede interpretar o no se puede transformar."""


# --- CRS ---------------------------------------------------------------------
def crs_info(crs: Any) -> dict[str, Any]:
    """Describe un CRS sin transformar nada."""
    try:
        parsed = pyproj.CRS.from_user_input(crs)
    except Exception as exc:  # noqa: BLE001 — se traduce a un error propio
        raise CRSConversionError(f"CRS no interpretable: {crs!r}: {exc}") from exc
    return {
        "input": str(crs),
        "epsg": parsed.to_epsg(),
        "name": parsed.name,
        "is_geographic": parsed.is_geographic,
        "is_projected": parsed.is_projected,
        "axis_units": parsed.axis_info[0].unit_name if parsed.axis_info else None,
        "area_of_use": (list(parsed.area_of_use.bounds)
                        if parsed.area_of_use else None),
    }


def utm_epsg(lon: float, lat: float) -> int:
    """EPSG de la zona UTM que contiene el punto (WGS84)."""
    if not (-180 <= lon <= 180 and -80 <= lat <= 84):
        raise ValueError(f"punto fuera del dominio UTM: lon={lon}, lat={lat}")
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def choose_metric_crs(bounds: tuple[float, float, float, float]) -> dict[str, Any]:
    """Elige CRS métrico para un área y documenta por qué.

    `bounds` = (oeste, sur, este, norte) en EPSG:4326.
    """
    west, south, east, north = bounds
    lon_center = (west + east) / 2
    lat_center = (south + north) / 2
    zones = {utm_epsg(lon, lat_center) for lon in (west, east)}
    epsg = utm_epsg(lon_center, lat_center)
    span_deg = east - west
    if len(zones) > 1 or span_deg > 6:
        return {
            "epsg": int(EPSG_EQUAL_AREA.split(":")[1]),
            "crs": EPSG_EQUAL_AREA,
            "reason": ("el área cruza más de una zona UTM o supera 6° de "
                       "longitud: se usa un CRS de área equivalente"),
            "equal_area": True,
            "scale_note": ("EPSG:6933 conserva área; no es adecuado para "
                           "distancias ni orientaciones"),
            "zones_considered": sorted(zones),
        }
    factor = _utm_scale_factor(epsg, lon_center, lat_center)
    return {
        "epsg": epsg,
        "crs": f"EPSG:{epsg}",
        "reason": f"área dentro de la zona UTM {epsg}",
        "equal_area": False,
        "scale_note": (
            f"factor de escala en el centro del área ≈ {factor:.4f}; "
            "las distancias se corrigen por este factor si se requiere precisión "
            "sub-porcentual"
        ),
        "zones_considered": [epsg],
    }


def _utm_scale_factor(epsg: int, lon: float, lat: float) -> float:
    """Factor de escala de la proyección UTM en un punto (mapa/geodesia)."""
    proj = pyproj.Proj(f"EPSG:{epsg}")
    geod = pyproj.Geod(ellps="WGS84")
    d = 1e-3  # grados; suficientemente pequeño para una derivada local
    x1, y1 = proj(lon, lat)
    x2, y2 = proj(lon + d, lat)
    map_meters = float(np.hypot(x2 - x1, y2 - y1))
    _, _, true_meters = geod.inv(lon, lat, lon + d, lat)
    if true_meters == 0:
        return 1.0
    return map_meters / true_meters


# --- transformación ----------------------------------------------------------
@dataclass(frozen=True)
class TransformRecord:
    source_crs: str
    target_crs: str
    reason: str
    features: int
    preserved_original: bool
    geographic_to_projected: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_crs": self.source_crs,
            "target_crs": self.target_crs,
            "reason": self.reason,
            "features": self.features,
            "preserved_original": self.preserved_original,
            "geographic_to_projected": self.geographic_to_projected,
            "note": ("el CRS de origen queda declarado en la columna "
                     "_crs_source; el archivo de entrada no se modifica"),
        }


def transform_vector(gdf, target_crs: str, *, reason: str,
                     purpose: str = "exchange"):
    """Reproyecta y conserva constancia del CRS original.

    `purpose` ∈ {exchange, area, distance, slope}. Para `area`/`distance` se
    rechaza un destino geográfico.
    """
    if gdf.crs is None:
        raise CRSConversionError(
            "la capa no declara CRS: no se reproyecta a ciegas; asígnelo con "
            "`set_crs` tras verificar la fuente"
        )
    target = pyproj.CRS.from_user_input(target_crs)
    if purpose in {"area", "distance", "slope"} and target.is_geographic:
        raise GeographicMetricError(
            f"'{purpose}' requiere CRS proyectado; se pidió {target_crs}"
        )
    out = gdf.to_crs(target_crs)
    out = out.copy()
    out["_crs_source"] = str(gdf.crs)
    out.attrs.update(getattr(gdf, "attrs", {}))
    out.attrs["crs_original"] = str(gdf.crs)
    out.attrs["transform_record"] = TransformRecord(
        source_crs=str(gdf.crs), target_crs=str(target_crs), reason=reason,
        features=len(out),
        preserved_original=True,
        geographic_to_projected=(pyproj.CRS.from_user_input(gdf.crs).is_geographic
                                 and target.is_projected),
    ).as_dict()
    return out


def transform_geometry(geom: BaseGeometry, source_crs: str,
                       target_crs: str) -> BaseGeometry:
    transformer = pyproj.Transformer.from_crs(source_crs, target_crs,
                                              always_xy=True)
    return shapely_transform(transformer.transform, geom)


def area_km2(gdf, *, equal_area_crs: str = EPSG_EQUAL_AREA):
    """Área por entidad en km². Exige destino proyectado de área equivalente."""
    target = pyproj.CRS.from_user_input(equal_area_crs)
    if target.is_geographic:
        raise GeographicMetricError(
            "no se calcula superficie en un CRS geográfico: EPSG:4326 no tiene "
            "unidades métricas. Use EPSG:6933 o una proyección de área equivalente."
        )
    if gdf.crs is None:
        raise CRSConversionError("la capa no declara CRS; no se puede calcular área")
    projected = gdf.to_crs(equal_area_crs)
    return projected.geometry.area / 1e6


def distance_m(geom_a: BaseGeometry, geom_b: BaseGeometry, *, crs: str) -> float:
    """Distancia en metros. Rechaza CRS geográfico."""
    parsed = pyproj.CRS.from_user_input(crs)
    if parsed.is_geographic:
        raise GeographicMetricError(
            "distancia en grados ≠ distancia en metros; use un CRS proyectado"
        )
    return float(geom_a.distance(geom_b))


# --- diagnóstico de geometrías ----------------------------------------------
@dataclass
class GeometryReport:
    features: int
    checks: dict[str, Any] = field(default_factory=dict)
    offending: dict[str, list[Any]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(c["count"] == 0 for c in self.checks.values()
                   if c["severity"] == "error")

    def as_dict(self) -> dict[str, Any]:
        return {
            "features": self.features,
            "ok": self.ok,
            "checks": self.checks,
            "offending": {k: v[:50] for k, v in self.offending.items()},
            "note": ("diagnóstico sin reparación: las geometrías inválidas se "
                     "informan, no se corrigen aquí"),
        }


def _self_intersection_count(geom: BaseGeometry) -> int:
    """Número de puntos de autointersección (0 si es válida)."""
    if geom.is_valid or geom.is_empty:
        return 0
    try:
        from shapely.validation import explain_validity

        detail = explain_validity(geom)
        return 1 if detail else 0
    except Exception:  # noqa: BLE001
        return 1


def validate_geometries(gdf, *, bounds: tuple[float, float, float, float] | None = None,
                        min_area_m2: float = 0.0) -> GeometryReport:
    """Diagnostica invalidez, vacíos, duplicados, fuera de rango y solapamientos."""
    report = GeometryReport(features=len(gdf))
    if len(gdf) == 0:
        report.checks["capa_vacia"] = {"count": 1, "severity": "error",
                                       "detail": "sin entidades"}
        return report

    geoms = gdf.geometry
    null_idx = [int(i) for i, g in enumerate(geoms) if g is None]
    empty_idx = [int(i) for i, g in enumerate(geoms)
                 if g is not None and g.is_empty]
    invalid_idx = [int(i) for i, g in enumerate(geoms)
                   if g is not None and not g.is_empty and not g.is_valid]
    selfint_idx = [i for i in invalid_idx
                   if _self_intersection_count(geoms.iloc[i]) > 0]

    hashes: dict[str, list[int]] = {}
    for i, g in enumerate(geoms):
        if g is None or g.is_empty:
            continue
        digest = hashlib.sha256(normalize(g).wkb).hexdigest()
        hashes.setdefault(digest, []).append(i)
    dup_groups = [idx for idx in hashes.values() if len(idx) > 1]

    report.checks["geometrias_nulas"] = {
        "count": len(null_idx), "severity": "error", "detail": "geometría ausente"}
    report.checks["geometrias_vacias"] = {
        "count": len(empty_idx), "severity": "error", "detail": "geometría vacía"}
    report.checks["geometrias_invalidas"] = {
        "count": len(invalid_idx), "severity": "error",
        "detail": "topología inválida (anillos cruzados, agujeros fuera, etc.)"}
    report.checks["autointersecciones"] = {
        "count": len(selfint_idx), "severity": "error",
        "detail": "polígonos autointersectados"}
    report.checks["duplicados_geometricos"] = {
        "count": len(dup_groups), "severity": "warning",
        "detail": "misma geometría normalizada en varias entidades"}
    report.offending.update({
        "nulas": null_idx, "vacias": empty_idx, "invalidas": invalid_idx,
        "autointersecciones": selfint_idx, "duplicados": dup_groups,
    })

    if bounds is not None:
        west, south, east, north = bounds
        wgs = gdf if str(gdf.crs) == EPSG_WGS84 else gdf.to_crs(EPSG_WGS84)
        out_idx = []
        for i, g in enumerate(wgs.geometry):
            if g is None or g.is_empty:
                continue
            minx, miny, maxx, maxy = g.bounds
            if (minx < west - 0.01 or miny < south - 0.01
                    or maxx > east + 0.01 or maxy > north + 0.01):
                out_idx.append(i)
        report.checks["fuera_de_cobertura"] = {
            "count": len(out_idx), "severity": "error",
            "detail": f"fuera del rectángulo {bounds}"}
        report.offending["fuera_de_cobertura"] = out_idx

    if min_area_m2 > 0 and gdf.crs is not None:
        areas = area_km2(gdf) * 1e6
        slivers = [int(i) for i, a in enumerate(areas) if 0 < a < min_area_m2]
        report.checks["poligonos_minusculos"] = {
            "count": len(slivers), "severity": "warning",
            "detail": f"área < {min_area_m2} m² (posibles esquirlas)"}
        report.offending["poligonos_minusculos"] = slivers

    # Solapamientos entre entidades del mismo nivel (error topológico real:
    # dos municipios no pueden ocupar el mismo terreno).
    overlaps: list[tuple[int, int, float]] = []
    if gdf.crs is not None and len(gdf) > 1:
        # Se proyecta una sola vez: el área de intersección en grados² no es
        # una superficie y comparar ratios en grados sería engañoso.
        projected = gdf.to_crs(EPSG_EQUAL_AREA)
        proj_geoms = projected.geometry
        tree = gdf.sindex
        for i, geom in enumerate(geoms):
            if geom is None or geom.is_empty:
                continue
            for j in tree.query(geom, predicate="intersects"):
                j = int(j)
                if j <= i:
                    continue
                other = geoms.iloc[j]
                if other is None or other.is_empty:
                    continue
                gi, gj = proj_geoms.iloc[i], proj_geoms.iloc[j]
                inter_area = float(gi.intersection(gj).area)
                smaller = min(float(gi.area), float(gj.area))
                ratio = inter_area / smaller if smaller > 0 else 0.0
                if ratio > 0.01:
                    overlaps.append((i, j, round(ratio, 4)))
    report.checks["solapamientos_topologicos"] = {
        "count": len(overlaps), "severity": "warning",
        "detail": "pares con intersección > 1% del polígono menor; revisar "
                  "límites administrativos"}
    report.offending["solapamientos"] = overlaps
    return report


# --- reparación registrada ---------------------------------------------------
@dataclass
class RepairLog:
    method: str
    operations: list[dict[str, Any]] = field(default_factory=list)
    original_sha256: str | None = None
    original_backup: str | None = None

    @property
    def repaired_count(self) -> int:
        return len(self.operations)

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "repaired_count": self.repaired_count,
            "operations": self.operations,
            "original_sha256": self.original_sha256,
            "original_backup": self.original_backup,
            "note": ("reparación explícita y registrada; el dato original se "
                     "conserva y no se sobrescribe"),
        }


def repair_geometries(gdf, *, method: str = "make_valid",
                      backup_path: Path | None = None,
                      original_file: Path | None = None):
    """Repara geometrías inválidas devolviendo (gdf_reparado, RepairLog).

    Métodos: `make_valid` (por defecto) o `buffer0`. No se repara nada que no
    esté inválido y cada operación queda con hash y área antes/después.
    """
    if method not in {"make_valid", "buffer0"}:
        raise ValueError("método de reparación no soportado: use make_valid o buffer0")
    if gdf.crs is None:
        raise CRSConversionError(
            "no se repara una capa sin CRS: el área antes/después no sería "
            "comparable"
        )
    out = gdf.copy()
    log = RepairLog(method=method)
    if original_file and Path(original_file).exists():
        from .storage import sha256_file

        log.original_sha256 = sha256_file(Path(original_file))
    if backup_path and original_file:
        import shutil

        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original_file, backup_path)
        log.original_backup = str(backup_path)

    areas_before = area_km2(gdf)
    repaired_flags = np.zeros(len(out), dtype=bool)
    for i, geom in enumerate(out.geometry):
        if geom is None or geom.is_empty or geom.is_valid:
            continue
        fixed = make_valid(geom) if method == "make_valid" else geom.buffer(0)
        log.operations.append({
            "index": int(i),
            "geometry_hash_before": hashlib.sha256(geom.wkb).hexdigest(),
            "geometry_hash_after": hashlib.sha256(fixed.wkb).hexdigest(),
            "method": method,
            "geometry_type_before": geom.geom_type,
            "geometry_type_after": fixed.geom_type,
            "valid_after": bool(fixed.is_valid),
        })
        out.iloc[i, out.columns.get_loc(out.geometry.name)] = fixed
        repaired_flags[i] = True

    areas_after = area_km2(out)
    for op in log.operations:
        i = op["index"]
        op["area_km2_before"] = round(float(areas_before.iloc[i]), 6)
        op["area_km2_after"] = round(float(areas_after.iloc[i]), 6)
        op["area_change_pct"] = (
            round(100 * (op["area_km2_after"] - op["area_km2_before"])
                  / op["area_km2_before"], 4)
            if op["area_km2_before"] else None
        )
    out["geom_repaired"] = repaired_flags
    out["geom_repair_method"] = np.where(repaired_flags, method, "")
    out.attrs.update(getattr(gdf, "attrs", {}))
    out.attrs["repair_log"] = log.as_dict()
    return out, log


def assert_crs_declared(gdf, *, what: str = "capa") -> dict[str, Any]:
    if gdf.crs is None:
        raise CRSConversionError(
            f"{what} sin CRS declarado: no se puede publicar ni medir"
        )
    return crs_info(gdf.crs)


def transform_points(lon: np.ndarray, lat: np.ndarray,
                     source_crs: str, target_crs: str
                     ) -> tuple[np.ndarray, np.ndarray]:
    transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return np.asarray(x), np.asarray(y)


def coverage_union(gdf, *, crs: str = EPSG_EQUAL_AREA) -> dict[str, Any]:
    """Área de la unión y solapamiento acumulado de un conjunto de polígonos."""
    if gdf.crs is None:
        raise CRSConversionError("capa sin CRS")
    proj = gdf.to_crs(crs)
    union_area = float(proj.geometry.union_all().area)
    sum_area = float(proj.geometry.area.sum())
    return {
        "crs": crs,
        "sum_area_km2": round(sum_area / 1e6, 4),
        "union_area_km2": round(union_area / 1e6, 4),
        "overlap_area_km2": round((sum_area - union_area) / 1e6, 4),
        "overlap_pct": round(100 * (sum_area - union_area) / sum_area, 4)
        if sum_area else 0.0,
    }
