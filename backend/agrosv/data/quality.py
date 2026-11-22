"""AGROSV — motor de calidad científico (Fase 4, §9).

Cuatro familias de comprobaciones, con severidad explícita:

    espacial    coordenadas, cobertura, geometría, duplicados, rejilla
    temporal    fechas, huecos, duplicados, frecuencia
    numérica    dominio físico, unidades, centinelas, constantes, escala, extremos
    científica  comparación entre fuentes relacionadas (intercomparación)

Dos límites deliberados:

1. **No se repara nada aquí.** El motor informa; la reparación es una decisión
   del pipeline y queda en la procedencia.
2. **Comparar no es validar.** Dos fuentes modeladas (NASA POWER y Open-Meteo,
   por ejemplo) que coinciden no elevan el nivel de evidencia: son
   intercomparaciones, no validación contra campo. `compare_sources` lo declara
   explícitamente y rechaza contar como V2–V4 si ninguna fuente es observación.

`status` resume: FAIL si hay algún error, PASS_WITH_WARNINGS si solo avisos,
PASS si nada. Un informe `PASS` no significa «dato correcto»: significa «no se
encontró un defecto en las comprobaciones ejecutadas», que se listan.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ..science import validation
from ..science.uncertainty import robust_z
from . import temporal as T
from . import units as U

VALIDATOR_VERSION = "agrosv.data.quality/4.0"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Finding:
    code: str
    severity: str  # error | warning | info
    message: str
    count: int = 0
    examples: list[Any] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity,
                "message": self.message, "count": self.count,
                "examples": self.examples[:10], "detail": self.detail}


@dataclass
class QualityReport:
    dataset_id: str
    artifact: str
    checks_run: int = 0
    findings: list[Finding] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    inputs: list[dict[str, Any]] = field(default_factory=list)
    scope: str = "muestra"
    generated_at: str = field(default_factory=utcnow)

    def add(self, finding: Finding | None) -> None:
        if finding is not None:
            self.findings.append(finding)

    def extend(self, findings: Sequence[Finding]) -> None:
        self.findings.extend(findings)

    @property
    def status(self) -> str:
        if any(f.severity == "error" for f in self.findings):
            return "FAIL"
        if any(f.severity == "warning" for f in self.findings):
            return "PASS_WITH_WARNINGS"
        return "PASS"

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def report_id(self) -> str:
        identity = {
            "dataset_id": self.dataset_id,
            "artifact": self.artifact,
            "checks_run": self.checks_run,
            "findings": [f.as_dict() for f in self.findings],
            "parameters": self.parameters,
            "inputs": self.inputs,
            "validator": VALIDATOR_VERSION,
        }
        blob = json.dumps(identity, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "dataset_id": self.dataset_id,
            "artifact": self.artifact,
            "scope": self.scope,
            "status": self.status,
            "checks_run": self.checks_run,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "findings": [f.as_dict() for f in self.findings],
            "parameters": self.parameters,
            "inputs": self.inputs,
            "validator_version": VALIDATOR_VERSION,
            "generated_at": self.generated_at,
            "note": ("PASS no significa «dato correcto»: significa que las "
                     "comprobaciones ejecutadas no encontraron defectos"),
        }

    def save(self, directory: Path | str) -> Path:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{self.dataset_id}.{self.report_id}.json"
        path.write_text(json.dumps(self.as_dict(), indent=2, ensure_ascii=False),
                        encoding="utf-8")
        return path


# --- utilidades numéricas ----------------------------------------------------
def _finite(values: Sequence[Any]) -> tuple[np.ndarray, int, int]:
    arr: list[float] = []
    missing = 0
    sentinels = 0
    for v in values:
        if v is None:
            missing += 1
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            missing += 1
            continue
        if fv != fv:  # NaN
            missing += 1
            continue
        if fv in T.FILL_SENTINELS:
            sentinels += 1
            continue
        arr.append(fv)
    return np.asarray(arr, dtype=float), missing, sentinels


def check_numeric(values: Sequence[Any], variable: str, *,
                  declared_unit: str | None = None,
                  require_unit: bool = True,
                  expected_unit: str | None = None) -> list[Finding]:
    """Dominio, centinelas, vacíos, constantes, escala y extremos."""
    findings: list[Finding] = []
    spec = U.spec(variable)

    if require_unit:
        unit_check = U.check_unit(variable, declared_unit)
        if not unit_check["ok"]:
            findings.append(Finding(
                code="unidad_incompatible", severity=unit_check["severity"],
                message=unit_check["detail"], detail=unit_check))
        elif expected_unit and declared_unit != expected_unit:
            findings.append(Finding(
                code="unidad_no_canonica", severity="warning",
                message=f"se declaró {declared_unit}; canónica {expected_unit}",
                detail={"declared": declared_unit, "canonical": expected_unit}))

    arr, missing, sentinels = _finite(values)
    if sentinels:
        findings.append(Finding(
            code="centinela_como_dato", severity="error", count=sentinels,
            message=("valores centinela (-999/-9999/32767) presentes: son "
                     "ausencia codificada, no mediciones"),
            detail={"sentinels": list(T.FILL_SENTINELS),
                    "missing_fraction": round(sentinels / max(1, len(values)), 4)}))
    if missing:
        findings.append(Finding(
            code="datos_faltantes", severity="warning", count=missing,
            message=("vacíos explícitos: se conservan como ausencia; nunca se "
                     "sustituyen por 0"),
            detail={"missing": missing, "n": len(values)}))

    if spec is None:
        findings.append(Finding(
            code="variable_sin_registro", severity="warning",
            message=f"'{variable}' no está en el registro de unidades: no se "
                    "comprueba dominio"))
        return findings

    if arr.size == 0:
        findings.append(Finding(
            code="sin_valores_validos", severity="error",
            message=f"{variable}: ningún valor válido tras excluir vacíos"))
        return findings

    below = int(np.count_nonzero(arr < spec.gross_min))
    above = int(np.count_nonzero(arr > spec.gross_max))
    if below or above:
        bad_idx = np.where((arr < spec.gross_min) | (arr > spec.gross_max))[0]
        findings.append(Finding(
            code="fuera_de_dominio", severity="error", count=below + above,
            message=(f"{below + above} valores fuera del dominio físico "
                     f"[{spec.gross_min}, {spec.gross_max}] {spec.canonical_unit}"),
            examples=[float(arr[i]) for i in bad_idx[:5]],
            detail={"below": below, "above": above,
                    "domain": [spec.gross_min, spec.gross_max],
                    "variable": variable}))
    elif spec.typical_min is not None and spec.typical_max is not None:
        outside_typical = int(np.count_nonzero(
            (arr < spec.typical_min) | (arr > spec.typical_max)))
        if outside_typical:
            findings.append(Finding(
                code="fuera_de_rango_tipico", severity="info",
                count=outside_typical,
                message=(f"{outside_typical} valores fuera del rango típico "
                         f"[{spec.typical_min}, {spec.typical_max}]; no es un "
                         "error, requiere revisión"),
                detail={"variable": variable}))

    if arr.size >= 10 and float(arr.min()) == float(arr.max()):
        findings.append(Finding(
            code="serie_constante", severity="warning",
            message=(f"{variable}: todos los valores son {float(arr.min()):g}; "
                     "posible máscara mal aplicada o dato rellenado"),
            count=int(arr.size)))

    scale_lo, scale_hi = spec.gross_min, spec.gross_max
    if arr.max() > 10 * max(abs(scale_hi), 1) and arr.min() >= 0:
        findings.append(Finding(
            code="posible_error_de_escala", severity="warning",
            message=(f"{variable}: máximo {arr.max():g} > 10× el límite "
                     f"{scale_hi:g}; revisar factor de escala (p. ej. g/kg vs %)"),
            detail={"max": float(arr.max()), "domain_max": scale_hi}))
    if (spec.canonical_unit in {"%", "m3 m-3"} and arr.min() >= 0
            and arr.max() <= 1.0 and spec.gross_max == 100.0):
        findings.append(Finding(
            code="posible_fraccion", severity="warning",
            message=(f"{variable}: valores entre 0 y 1 con unidad '%': podría "
                     "estar en fracción; no se convierte sin declaración"),
            detail={"max": float(arr.max())}))
    if arr.size > 5 and spec.canonical_unit == "%":
        s = arr.sum() if variable in {"clay", "sand", "silt"} else None
        if s is not None:
            findings.append(Finding(
                code="suma_de_fracciones", severity="info",
                message=(f"{variable}: suma media por registro no evaluada aquí; "
                         "la comprobación arena+limo+arcilla ≈ 100 se hace con "
                         "check_texture"),
                detail={"mean": float(arr.mean())}))

    if arr.size >= 30:
        baseline = arr
        z = np.abs(robust_z(arr, baseline))
        extreme = int(np.count_nonzero(np.nan_to_num(z) > 6))
        if extreme:
            findings.append(Finding(
                code="valores_extremos", severity="warning", count=extreme,
                message=(f"{extreme} valores con |z robusto| > 6 respecto a la "
                         "propia serie; revisar, no eliminar automáticamente"),
                examples=[float(arr[i]) for i in np.argsort(-np.nan_to_num(z))[:5]]))
        findings.append(Finding(
            code="distribucion", severity="info", count=int(arr.size),
            message="resumen distribucional (no es un criterio de aprobación)",
            detail={
                "mean": round(float(arr.mean()), 6),
                "sd": round(float(arr.std(ddof=1)), 6),
                "p01": round(float(np.percentile(arr, 1)), 6),
                "p50": round(float(np.percentile(arr, 50)), 6),
                "p99": round(float(np.percentile(arr, 99)), 6),
                "skew": round(float(_skew(arr)), 4),
                "n": int(arr.size),
            }))
    return findings


def _skew(arr: np.ndarray) -> float:
    if arr.size < 3:
        return 0.0
    sd = arr.std(ddof=0)
    if sd == 0:
        return 0.0
    return float(np.mean(((arr - arr.mean()) / sd) ** 3))


def check_texture(clay: Sequence[Any], sand: Sequence[Any],
                  silt: Sequence[Any], *, tolerance: float = 5.0) -> list[Finding]:
    """arena+limo+arcilla ≈ 100 %: discrepancia real, no error automático.

    SoilGrids predice cada fracción por separado, así que la suma no cierra
    exactamente. Un desvío > `tolerance` puntos porcentuales se informa; no se
    renormaliza en silencio.
    """
    findings: list[Finding] = []
    if not (len(clay) == len(sand) == len(silt)):
        raise ValueError("las tres fracciones deben tener la misma longitud")
    totals = []
    for c, s, l in zip(clay, sand, silt):
        if None in (c, s, l) or any(isinstance(v, float) and v != v
                                    for v in (c, s, l)):
            continue
        totals.append(float(c) + float(s) + float(l))
    if not totals:
        findings.append(Finding(code="textura_sin_datos", severity="error",
                                message="no hay triplete textural completo"))
        return findings
    arr = np.asarray(totals)
    off = int(np.count_nonzero(np.abs(arr - 100) > tolerance))
    findings.append(Finding(
        code="suma_textural", severity="warning" if off else "info", count=off,
        message=(f"{off} de {arr.size} registros con suma textural fuera de "
                 f"100 ± {tolerance} %"),
        detail={"p05": round(float(np.percentile(arr, 5)), 3),
                "p50": round(float(np.percentile(arr, 50)), 3),
                "p95": round(float(np.percentile(arr, 95)), 3),
                "tolerance": tolerance,
                "note": "no se renormaliza: la discrepancia es información"}))
    return findings


def check_missing_vs_zero(values: Sequence[Any]) -> dict[str, Any]:
    """Separa ausencia de cero. Una celda sin dato no vale 0 mm."""
    zeros = sum(1 for v in values if isinstance(v, (int, float))
                and v is not None and v == 0.0)
    missing, sentinels = 0, 0
    for v in values:
        if v is None:
            missing += 1
        elif isinstance(v, float) and v != v:
            missing += 1
        elif isinstance(v, (int, float)) and v in T.FILL_SENTINELS:
            sentinels += 1
    return {"n": len(values), "zeros": zeros, "missing": missing,
            "sentinels": sentinels,
            "distinct": True,
            "note": ("cero es un valor observado; ausencia es falta de dato. "
                     "La media debe calcularse sobre valores válidos")}


def check_spatial_points(lon: Sequence[Any], lat: Sequence[Any], *,
                         bounds: tuple[float, float, float, float] | None = None,
                         max_uncertainty_m: float | None = None,
                         uncertainty: Sequence[Any] | None = None
                         ) -> list[Finding]:
    """Coordenadas: rango, cobertura, duplicados y precisión declarada."""
    findings: list[Finding] = []
    if len(lon) != len(lat):
        raise ValueError("lon y lat con longitudes distintas")
    bad_range, out_of_area, nulls = [], [], []
    pairs: dict[tuple[float, float], int] = {}
    for i, (x, y) in enumerate(zip(lon, lat)):
        if x is None or y is None:
            nulls.append(i)
            continue
        fx, fy = float(x), float(y)
        if not (-180 <= fx <= 180 and -90 <= fy <= 90):
            bad_range.append(i)
            continue
        if bounds and not (bounds[0] <= fx <= bounds[2]
                           and bounds[1] <= fy <= bounds[3]):
            out_of_area.append(i)
        pairs[(round(fx, 6), round(fy, 6))] = pairs.get((round(fx, 6),
                                                          round(fy, 6)), 0) + 1

    if nulls:
        findings.append(Finding(
            code="coordenadas_ausentes", severity="error", count=len(nulls),
            message="registros sin coordenada", examples=nulls[:5]))
    if bad_range:
        findings.append(Finding(
            code="coordenadas_fuera_de_rango", severity="error",
            count=len(bad_range),
            message="longitud/latitud fuera de [-180,180]/[-90,90]",
            examples=bad_range[:5]))
    if out_of_area:
        findings.append(Finding(
            code="fuera_de_cobertura", severity="error", count=len(out_of_area),
            message="coordenadas fuera de la cobertura declarada",
            examples=out_of_area[:5]))
    dupes = {k: v for k, v in pairs.items() if v > 1}
    if dupes:
        findings.append(Finding(
            code="duplicados_espaciales", severity="warning", count=len(dupes),
            message="misma coordenada redondeada a 1e-6 en varios registros",
            examples=[list(k) for k in list(dupes)[:5]]))
    if uncertainty is not None and max_uncertainty_m is not None:
        vals = []
        for u in uncertainty:
            try:
                if u is not None:
                    vals.append(float(u))
            except (TypeError, ValueError):
                continue
        if vals:
            over = sum(1 for v in vals if v > max_uncertainty_m)
            if over:
                findings.append(Finding(
                    code="incertidumbre_coordenada", severity="warning",
                    count=over,
                    message=(f"{over} registros con incertidumbre > "
                             f"{max_uncertainty_m} m"),
                    detail={"median_m": round(float(np.median(vals)), 1),
                            "max_m": round(max(vals), 1)}))
    return findings


def check_temporal(times: Sequence[Any], values: Sequence[Any],
                   spec: T.TimeSeriesSpec) -> list[Finding]:
    """Envuelve `temporal.validate_series` traduciendo hallazgos a severidad."""
    report = T.validate_series(times, values, spec)
    out = []
    for finding in report.findings:
        out.append(Finding(
            code=finding["code"], severity=finding["severity"],
            message=finding.get("detail", ""), count=finding.get("count", 0),
            examples=finding.get("examples", []),
            detail={k: v for k, v in finding.items()
                    if k not in {"code", "severity", "detail", "count",
                                 "examples"}}))
    return out


def check_raster(path: Path | str, *, expected_crs: str | None = None,
                 bounds: tuple[float, float, float, float] | None = None,
                 max_nodata_ratio: float | None = None,
                 max_res_deg: float | None = None) -> tuple[list[Finding], int]:
    """QC ráster: CRS, rejilla, NoData, centinelas, cobertura y variabilidad.

    Devuelve (hallazgos, comprobaciones ejecutadas). Reutiliza el QC de Fase 2 en
    lugar de reimplementar las comprobaciones de rejilla.
    """
    from ..science import qc as science_qc
    from . import raster as R

    findings: list[Finding] = []
    checks = 0
    profile = R.profile_raster(path)
    checks += 1
    large = profile.width * profile.height > 25_000_000
    if not profile.crs:
        findings.append(Finding("raster_sin_crs", "error",
                                "el ráster no declara CRS"))
    elif expected_crs and profile.crs != expected_crs:
        findings.append(Finding(
            "raster_crs_distinto", "error",
            f"CRS {profile.crs} distinto del esperado {expected_crs}"))
    if profile.nodata is None:
        if large:
            block = _block_nodata_scan(path, profile)
            checks += 1
            findings.append(Finding(
                "nodata_sin_declarar",
                "warning" if block["suspicious"] else "info",
                "análisis por bloques: el ráster no declara NoData",
                detail=block))
        else:
            candidates = R.undeclared_nodata_candidates(path)
            checks += 1
            suspect = [c for c in candidates["suspicious"] if c["pct"] >= 0.1]
            if suspect:
                findings.append(Finding(
                    "nodata_sin_declarar", "warning",
                    "valores centinela presentes sin NoData declarado",
                    detail={"candidates": suspect}))
            else:
                findings.append(Finding(
                    "nodata_sin_declarar", "info",
                    "el ráster no declara NoData",
                    detail={"candidates": candidates["suspicious"]}))
    if large:
        # Evita materializar un ráster nacional: se informa forma, rejilla y
        # cobertura medida por bloques. La cobertura de dato válido se declara
        # sin umbral porque el bbox puede incluir mar.
        checks += 1
        scan = _block_nodata_scan(path, profile)
        findings.append(Finding(
            "cobertura_por_bloques", "info",
            f"{scan['valid_pct']}% de celdas válidas leídas por bloques; "
            "sin umbral porque el rectángulo incluye mar",
            detail=scan))
    else:
        science_report = science_qc.qc_raster(
            Path(path), expected_crs=expected_crs,
            max_nodata_ratio=max_nodata_ratio, max_res_deg=max_res_deg)
        checks += len(science_report.checks)
        for check in science_report.checks:
            if check.passed:
                continue
            findings.append(Finding(
                code=f"raster_{check.name.replace(' ', '_')}",
                severity="warning" if check.severity == "warning" else "error",
                message=check.detail or check.name,
                detail={"check": check.name}))
    if bounds is not None:
        try:
            stats = R.window_stats(path, bounds)
            checks += 1
            findings.append(Finding(
                "ventana_de_cobertura", "info",
                "estadísticas de la ventana solicitada (no del archivo completo)",
                detail=stats))
        except Exception as exc:  # noqa: BLE001 — ventana fuera del ráster
            findings.append(Finding(
                "ventana_de_cobertura", "error",
                f"no se pudo leer la ventana: {exc}"))
    return findings, checks


def _block_nodata_scan(path: Path | str, profile: Any,
                       sentinels: tuple[float, ...] = (-9999.0, -999.0,
                                                      32767.0, 255.0)
                       ) -> dict[str, Any]:
    """Cuenta celdas válidas y centinelas bloque a bloque (memoria acotada)."""
    import rasterio

    total = 0
    valid = 0
    found: dict[float, int] = {}
    with rasterio.open(path) as ds:
        masked_nodata = ds.nodata
        for _, window in ds.block_windows(1):
            data = ds.read(1, window=window)
            total += int(data.size)
            if masked_nodata is not None:
                valid += int(np.count_nonzero(data != masked_nodata))
            else:
                valid += int(data.size)
            for sentinel in sentinels:
                count = int(np.count_nonzero(data == sentinel))
                if count:
                    found[sentinel] = found.get(sentinel, 0) + count
    suspicious = [{"value": k, "cells": v,
                   "pct": round(100 * v / total, 4) if total else 0.0}
                  for k, v in sorted(found.items())]
    return {
        "cells": total,
        "valid_pct": round(100 * valid / total, 3) if total else 0.0,
        "nodata_declared": profile.nodata is not None,
        "sentinels_found": suspicious,
        "suspicious": [s for s in suspicious if s["pct"] >= 0.1],
        "method": "lectura por bloques nativos; no se cargó el ráster completo",
    }


def check_vector(path: Path | str, *, layer: str | None = None,
                 bounds: tuple[float, float, float, float] | None = None,
                 expected_crs: str | None = None,
                 sample_rows: int | None = None) -> tuple[list[Finding], int]:
    """QC vectorial: CRS, geometrías, duplicados y extensión.

    `sample_rows` declara una muestra; el informe lo dice, porque validar 2.000
    de 50.000 entidades no es validar la capa completa.
    """
    import geopandas as gpd

    from . import geo

    findings: list[Finding] = []
    checks = 0
    gdf = gpd.read_file(path, layer=layer)
    if sample_rows and len(gdf) > sample_rows:
        gdf = gdf.iloc[:sample_rows]
    checks += 1
    if gdf.crs is None:
        findings.append(Finding("vector_sin_crs", "error",
                                "la capa no declara CRS"))
        return findings, checks
    report = geo.validate_geometries(gdf, bounds=bounds)
    checks += len(report.checks)
    for name, check in report.checks.items():
        if check["count"] == 0:
            continue
        findings.append(Finding(
            code=f"vector_{name}",
            severity="error" if check["severity"] == "error" else "warning",
            count=int(check["count"]), message=check["detail"],
            detail={"offending": report.offending.get(name, [])[:10]}))
    if expected_crs and str(gdf.crs) != expected_crs:
        findings.append(Finding(
            "vector_crs_distinto", "error",
            f"CRS {gdf.crs} distinto del esperado {expected_crs}"))
        checks += 1
    return findings, checks


def compare_sources(name_a: str, values_a: Sequence[Any],
                    name_b: str, values_b: Sequence[Any], *,
                    variable: str, unit: str,
                    evidence_a: T.EvidenceClass,
                    evidence_b: T.EvidenceClass,
                    tolerance_pct: float | None = None,
                    observation_source: str | None = None,
                    reference_scale: str | None = None,
                    independent: bool = False) -> dict[str, Any]:
    """Intercomparación explícita entre dos fuentes.

    Solo si **una fuente es observación** y se declara la escala de referencia
    se calcula un nivel V2–V4. Si ambas son modeladas, el resultado es una
    intercomparación y no incrementa el nivel de evidencia.
    """
    a = np.asarray([np.nan if v is None else float(v) for v in values_a])
    b = np.asarray([np.nan if v is None else float(v) for v in values_b])
    if a.shape != b.shape:
        raise ValueError(f"series de distinto tamaño: {a.shape} vs {b.shape}")
    mask = np.isfinite(a) & np.isfinite(b)
    a, b = a[mask], b[mask]
    meta = {"variable": variable, "unit": unit,
            "sources": [name_a, name_b],
            "evidence_classes": [evidence_a.value, evidence_b.value],
            "paired_values": int(a.size)}

    if a.size < validation.MIN_PAIRS:
        return {**meta, "comparison_class": "insufficient",
                "evidence": None, "metrics": None,
                "note": f"menos de {validation.MIN_PAIRS} pares válidos"}
    metrics = validation.metrics(a, b)
    any_observed = T.EvidenceClass.OBSERVATION in {evidence_a, evidence_b}
    comparison_class = "intercomparison" if not any_observed else "comparison"
    evidence = None
    if any_observed and observation_source and reference_scale:
        evidence = validation.evidence_level(
            metrics["n"], reference_scale=reference_scale,
            observation_source=observation_source, independent=independent)
    findings: list[Finding] = []
    if tolerance_pct is not None and abs(metrics["pbias_pct"] or 0) > tolerance_pct:
        findings.append(Finding(
            "diferencia_sistematica", "warning",
            f"PBIAS {metrics['pbias_pct']:.1f}% supera la tolerancia "
            f"{tolerance_pct}%", detail={"pbias_pct": metrics["pbias_pct"]}))
    if np.isfinite(metrics["r"]) and metrics["r"] > 0.999 and abs(metrics["bias"]) < 1e-9:
        findings.append(Finding(
            "posible_duplicacion_de_fuente", "warning",
            "las series son casi idénticas: podrían proceder de la misma fuente"))
    return {
        **meta,
        "comparison_class": comparison_class,
        "evidence": evidence,
        "evidence_use": ("incrementa nivel de validación" if evidence else
                         "NO incrementa nivel de validación: intercomparación "
                         "entre fuentes modeladas"),
        "metrics": metrics,
        "findings": [f.as_dict() for f in findings],
        "interpretation": (
            "las diferencias no son errores por sí mismas: distintas escalas de "
            "soporte, métodos y períodos producen diferencias legítimas; deben "
            "documentarse con su explicación"),
        "limitations": [
            "coincidencia entre modelos no equivale a exactitud",
            "la escala de soporte de cada fuente debe compararse explícitamente",
        ],
    }


def compare_variable_to_source(*, variable: str, derived: Sequence[Any],
                               reference: Sequence[Any], reference_name: str,
                               derived_name: str, **kwargs: Any) -> dict[str, Any]:
    """Alias con nombres explícitos para comparaciones derivado-vs-referencia."""
    return compare_sources(derived_name, derived, reference_name, reference,
                           variable=variable, **kwargs)


def report_for_dataset(*, dataset_id: str, artifact: str,
                       numeric: Sequence[tuple[str, Sequence[Any], str | None]] = (),
                       temporal_series: tuple[Sequence[Any], Sequence[Any],
                                              T.TimeSeriesSpec] | None = None,
                       points: tuple[Sequence[Any], Sequence[Any]] | None = None,
                       bounds: tuple[float, float, float, float] | None = None,
                       soil_texture: tuple[Sequence[Any], Sequence[Any],
                                          Sequence[Any]] | None = None,
                       comparisons: Sequence[dict[str, Any]] = (),
                       scope: str = "muestra") -> QualityReport:
    """Construye un informe completo a partir de los datos disponibles."""
    report = QualityReport(dataset_id=dataset_id, artifact=artifact, scope=scope)
    for variable, values, unit in numeric:
        report.extend(check_numeric(values, variable, declared_unit=unit))
        report.checks_run += 1
    if temporal_series is not None:
        times, values, spec = temporal_series
        report.extend(check_temporal(times, values, spec))
        report.extend(check_numeric(values, spec.variable, declared_unit=spec.unit))
        report.checks_run += 2
    if points is not None:
        lon, lat = points
        report.extend(check_spatial_points(lon, lat, bounds=bounds))
        report.checks_run += 1
    if soil_texture is not None:
        report.extend(check_texture(*soil_texture))
        report.checks_run += 1
    for comparison in comparisons:
        report.checks_run += 1
        for finding in comparison.get("findings", []):
            report.add(Finding(**finding))
        if comparison.get("evidence"):
            report.add(Finding(
                "nivel_de_evidencia", "info",
                f"nivel {comparison['evidence']['level']}: "
                f"{comparison['evidence']['reason']}",
                detail=comparison["evidence"]))
    return report
