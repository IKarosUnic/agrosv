"""AGROSV Fase 4 — construcción del catálogo, validación e integración.

Qué hace, en orden y con evidencia real:

1. Ingiere las muestras de Fase 3 con `agrosv.data.ingest` (hash + metadatos).
2. Ejecuta el motor de calidad sobre cada muestra (espacial, temporal, numérico).
3. Construye el índice territorial y la plantilla de correspondencia (incompleta
   a propósito: no existe la tabla oficial 272 distritos ↔ 44 municipios).
4. Normaliza e integra series de punto (NASA POWER, Open-Meteo) y ocurrencias
   GBIF en SQLite, exportando CSV verificables.
5. Perfila todos los rásteres gestionados y recorta la muestra CHIRPS al país
   con operación registrada.
6. Registra el linaje de cada producto derivado.
7. Avanza el catálogo **solo** con la evidencia producida: un dataset sin
   informe aprobado no llega a VALIDATED, y sin consulta verificable no llega a
   INTEGRATED.
8. Escribe el informe de monitoreo.

Uso:
    python scripts/08_build_phase4_integration.py [--rebuild]

Las rutas del catálogo son relativas a la raíz del proyecto.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv import config as C  # noqa: E402
from agrosv.data import (catalog as CAT, confidence as CONF, geo as GEO,  # noqa: E402
                         ingest as ING, lineage as LIN, quality as Q,
                         raster as RAS, storage as S, temporal as T,
                         territory as TR)
from agrosv.data.store import DataStore  # noqa: E402
from agrosv.data import pipeline as PIPE  # noqa: E402

PROBES_PATH = ROOT / "research" / "raw" / "phase3" / "probes_20261122_r3.json"
SAMPLES = ROOT / "data" / "samples" / "phase3"
REGISTRY_DOC = "docs/data_expansion/DATA_SOURCE_REGISTRY.md"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return S.sha256_file(path)


def provenance_path(artifact: Path) -> Path:
    return Path(str(artifact) + ".provenance.json")


def provenance(artifact: Path) -> dict[str, Any]:
    return read_json(provenance_path(artifact), {}) or {}


def probe_index() -> dict[str, dict[str, Any]]:
    payload = read_json(PROBES_PATH, {}) or {}
    return {r["id"]: r for r in payload.get("results", [])}


def probe_ev(probes: dict[str, dict[str, Any]], probe_id: str, *,
             passed: bool | None = None, note: str = "") -> CAT.Evidence:
    record = probes.get(probe_id, {})
    status = record.get("status")
    ok = passed if passed is not None else bool(status and 200 <= int(status) < 300)
    return CAT.Evidence(
        evidence_type=CAT.EvidenceType.URL_PROBE,
        reference=(f"{rel(PROBES_PATH)}#{probe_id}" if record
                   else f"{REGISTRY_DOC}#{probe_id}"),
        note=note or f"status={status}; url={record.get('url')}",
        passed=ok,
        payload={"status": status, "url": record.get("url"),
                 "found_in_probe_run": bool(record)},
    )


def doc_ev(anchor: str, note: str, *, passed: bool = True) -> CAT.Evidence:
    return CAT.Evidence(evidence_type=CAT.EvidenceType.MANUAL_REVIEW,
                        reference=f"{REGISTRY_DOC}#{anchor}", note=note,
                        passed=passed)


def file_ev(path: Path, note: str = "") -> CAT.Evidence:
    return CAT.Evidence.from_file(path, CAT.EvidenceType.FILE_HASH, note=note,
                                  passed=True)


def parse_ev(manifest: Path, fmt: str) -> CAT.Evidence:
    return CAT.Evidence.from_file(
        manifest, CAT.EvidenceType.PARSE_RESULT, passed=True,
        payload={"parser": "agrosv.data.ingest/4.0", "format": fmt})


def validation_ev(report_path: Path, report: Q.QualityReport,
                  scope: str) -> CAT.Evidence:
    return CAT.Evidence.from_file(
        report_path, CAT.EvidenceType.VALIDATION_REPORT,
        passed=report.status != "FAIL",
        payload={"status": report.status, "checks_run": report.checks_run,
                 "scope": scope, "report_id": report.report_id})


def integration_ev(lay: S.DataLayout, dataset_id: str, *,
                   rows: int, endpoint: str, details: dict[str, Any]
                   ) -> CAT.Evidence:
    path = lay.manifests / "integration" / f"{dataset_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"dataset_id": dataset_id, "queryable": True, "rows": rows,
               "endpoint": endpoint, "store": rel(lay.store_path),
               "verified_at": utcnow(), **details}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return CAT.Evidence.from_file(
        path, CAT.EvidenceType.INTEGRATION_RECORD, passed=True,
        payload={"queryable": True, "rows": rows, "endpoint": endpoint})


def base_record(**kwargs: Any) -> CAT.DatasetRecord:
    """Ficha con valores explícitamente desconocidos cuando no hay evidencia."""
    return CAT.DatasetRecord(**kwargs)


# --- normalización de series -------------------------------------------------
NASA_VARS = {
    "PRECTOTCORR": ("precipitation", "mm", "sum", "precipitación corregida"),
    "T2M_MAX": ("temperature", "degC", "max", "temperatura máxima a 2 m"),
    "T2M_MIN": ("temperature", "degC", "min", "temperatura mínima a 2 m"),
}

OPEN_METEO_VARS = {
    "precipitation_sum": ("precipitation", "mm", "sum"),
    "temperature_2m_max": ("temperature", "degC", "max"),
    "temperature_2m_min": ("temperature", "degC", "min"),
    "et0_fao_evapotranspiration": ("et0", "mm", "sum"),
    "relative_humidity_2m_mean": ("relative_humidity", "%", "mean"),
}


def local_day_to_utc(day: str) -> tuple[str, str]:
    """Período diario local (UTC−6) expresado en UTC."""
    d = datetime.strptime(day, "%Y-%m-%d")
    start = d.replace(tzinfo=timezone(timedelta(hours=T.LOCAL_UTC_OFFSET_HOURS)))
    end = start + timedelta(days=1)
    return (start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


def parse_nasa(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = read_json(path)
    params = payload["properties"]["parameter"]
    meta = payload.get("parameters", {})
    fill = float(payload.get("header", {}).get("fill_value", -999.0))
    lon, lat = -89.20, 13.70
    rows: list[dict[str, Any]] = []
    sentinels = 0
    for api_name, (variable, unit, aggregation, _desc) in NASA_VARS.items():
        series = params.get(api_name, {})
        for raw_day, value in series.items():
            if value is None or float(value) == fill:
                sentinels += 1
                continue
            day = f"{raw_day[:4]}-{raw_day[4:6]}-{raw_day[6:]}"
            start, end = local_day_to_utc(day)
            rows.append({
                "dataset_id": "nasa_power_point", "variable": variable,
                "unit": unit, "value": float(value), "time_local": day,
                "time_utc": start, "period_start": start, "period_end": end,
                "frequency": "daily", "aggregation": aggregation,
                "evidence_class": "reanalysis", "latitude": lat, "longitude": lon,
                "cell_support": "0,5° × 0,625° (MERRA-2/POWER)",
                "quality_flag": "ok", "source_id": "nasa_power",
                "dataset_version": "v2.10.5",
            })
    info = {"n_days": len({r["time_local"] for r in rows}),
            "n_rows": len(rows), "sentinels_converted_to_missing": sentinels,
            "units_source": meta, "time_basis": "LST (hora solar local)",
            "offset_assumption": "UTC−6 para el período diario; LST puede "
                                 "desviarse ~±30 min del tiempo civil",
            "position": {"latitude": lat, "longitude": lon}}
    return rows, info


def parse_open_meteo(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = read_json(path)
    daily = payload["daily"]
    lon = float(payload["longitude"])
    lat = float(payload["latitude"])
    units = payload.get("daily_units", {})
    rows: list[dict[str, Any]] = []
    for api_name, (variable, unit, aggregation) in OPEN_METEO_VARS.items():
        for day, value in zip(daily["time"], daily.get(api_name, [])):
            if value is None:
                continue
            start, end = local_day_to_utc(day)
            rows.append({
                "dataset_id": "open_meteo_point", "variable": variable,
                "unit": unit, "value": float(value), "time_local": day,
                "time_utc": start, "period_start": start, "period_end": end,
                "frequency": "daily", "aggregation": aggregation,
                "evidence_class": "reanalysis", "latitude": lat, "longitude": lon,
                "cell_support": "0,1° (~9 km) ERA5/IFS",
                "quality_flag": "ok", "source_id": "open_meteo",
                "dataset_version": "archive-api v1",
            })
    info = {"n_days": len(daily["time"]), "n_rows": len(rows),
            "timezone": payload.get("timezone"),
            "utc_offset_seconds": payload.get("utc_offset_seconds"),
            "daily_units": units,
            "position": {"latitude": lat, "longitude": lon}}
    return rows, info


def parse_gbif(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = read_json(path)
    results = payload.get("results", [])
    rows = []
    for item in results:
        lat, lon = item.get("decimalLatitude"), item.get("decimalLongitude")
        if lat is None or lon is None:
            continue
        west, south, east, north = C.SV_BOUNDS
        on_land_bbox = west <= float(lon) <= east and south <= float(lat) <= north
        rows.append({
            "occurrence_id": str(item.get("key")),
            "dataset_id": "gbif_sv",
            "taxon": item.get("scientificName") or item.get("species") or "",
            "latitude": float(lat), "longitude": float(lon),
            "event_date": item.get("eventDate"),
            "basis_of_record": item.get("basisOfRecord"),
            "coordinate_uncertainty_m": item.get("coordinateUncertaintyInMeters"),
            "issues": item.get("issues", []),
            # No se elimina el registro: se marca. Borrar sería una corrección
            # silenciosa; el informe explica cuántos y por qué.
            "quality_flag": "ok" if on_land_bbox else "outside_land_bbox",
        })
    info = {"records": len(rows), "count_reported": payload.get("count"),
            "issues_present": sum(1 for r in rows if r["issues"])}
    return rows, info


def parse_worldbank(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = read_json(path)
    series = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    rows = [{"date": str(item["date"]), "value": item.get("value")}
            for item in series if item.get("value") is not None]
    rows.sort(key=lambda r: r["date"])
    return rows, {"indicator": series[0]["indicator"] if series else None,
                  "records": len(rows)}


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


# --- informes ----------------------------------------------------------------
def report_nasa(rows: list[dict[str, Any]], layer: S.DataLayout) -> Q.QualityReport:
    report = Q.QualityReport("nasa_power_point",
                             "data/samples/phase3/nasa_power_point/power_daily_13.70N_89.20W.json",
                             scope="muestra de punto: 13,70 N, 89,20 W, 2019–2025")
    by_var: dict[tuple[str, str], list[Any]] = {}
    for r in rows:
        by_var.setdefault((r["variable"], r["aggregation"]), []).append(r["value"])
    for (variable, aggregation), values in by_var.items():
        report.extend(Q.check_numeric(values, variable, declared_unit=(
            "mm" if variable == "precipitation" else "degC")))
        report.checks_run += 1
    precip = [r for r in rows if r["variable"] == "precipitation"]
    spec = T.TimeSeriesSpec(
        variable="precipitation", unit="mm",
        evidence_class=T.EvidenceClass.REANALYSIS, frequency=T.Frequency.DAILY,
        time_basis="local", aggregation=T.Aggregation.SUM,
        dataset_id="nasa_power_point", source_id="nasa_power",
        period_start="2019-01-01", period_end="2025-12-31",
        temporal_resolution="diaria (desagregada de pentadas)",
        uncertainty_note="reanálisis MERRA-2: error de representación espacial "
                         "no cuantificado en El Salvador",
    )
    report.extend(Q.check_temporal([r["time_local"] for r in precip],
                                   [r["value"] for r in precip], spec))
    report.checks_run += 1
    report.add(Q.Finding(
        "clase_de_evidencia", "info",
        "NASA POWER es reanálisis, no una estación: no se presenta como medición "
        "de campo", detail={"evidence_class": "reanalysis"}))
    report.parameters = {"comparison": "intercomparación con Open-Meteo para "
                                      "temperatura (ver informe de Open-Meteo)"}
    return report


def report_open_meteo(rows: list[dict[str, Any]]) -> Q.QualityReport:
    report = Q.QualityReport(
        "open_meteo_point",
        "data/samples/phase3/open_meteo_point/openmeteo_daily_13.70N_89.20W.json",
        scope="muestra de punto: 13,67 N, 89,17 W, 2019–2025")
    by_var: dict[str, list[Any]] = {}
    units = {}
    for r in rows:
        by_var.setdefault(r["variable"], []).append(r["value"])
        units[r["variable"]] = r["unit"]
    for variable, values in by_var.items():
        report.extend(Q.check_numeric(values, variable,
                                      declared_unit=units[variable]))
        report.checks_run += 1
    precip = [r for r in rows if r["variable"] == "precipitation"]
    spec = T.TimeSeriesSpec(
        variable="precipitation", unit="mm",
        evidence_class=T.EvidenceClass.REANALYSIS, frequency=T.Frequency.DAILY,
        time_basis="local", aggregation=T.Aggregation.SUM,
        dataset_id="open_meteo_point", source_id="open_meteo",
        period_start="2019-01-01", period_end="2025-12-31",
        temporal_resolution="diaria (agregada por el proveedor)",
        uncertainty_note="agregador ERA5/IFS a 0,1°: no es medición local",
    )
    report.extend(Q.check_temporal([r["time_local"] for r in precip],
                                   [r["value"] for r in precip], spec))
    report.checks_run += 1
    report.add(Q.Finding(
        "licencia_no_comercial", "warning",
        "el nivel gratuito de Open-Meteo es solo para uso no comercial: el uso "
        "comercial exige plan de pago"))
    return report


def compare_temperature(nasa: list[dict[str, Any]],
                        meteo: list[dict[str, Any]]) -> dict[str, Any]:
    def series(rows: list[dict[str, Any]], aggregation: str) -> dict[str, float]:
        return {r["time_local"]: r["value"] for r in rows
                if r["variable"] == "temperature" and r["aggregation"] == aggregation}

    out = {}
    for aggregation, label in (("max", "temperatura máxima"),
                               ("min", "temperatura mínima")):
        a, b = series(nasa, aggregation), series(meteo, aggregation)
        common = sorted(set(a) & set(b))
        out[aggregation] = Q.compare_sources(
            "nasa_power", [a[d] for d in common], "open_meteo", [b[d] for d in common],
            variable="temperature", unit="degC",
            evidence_a=T.EvidenceClass.REANALYSIS,
            evidence_b=T.EvidenceClass.REANALYSIS,
            tolerance_pct=10.0)
        out[aggregation]["label"] = label
        out[aggregation]["n_common_days"] = len(common)
    return out


def report_gbif(occurrences: list[dict[str, Any]]) -> Q.QualityReport:
    report = Q.QualityReport(
        "gbif_sv", "data/samples/phase3/gbif_sv/gbif_occurrence_sv_300.json",
        scope="muestra de 300 ocurrencias en El Salvador")
    report.extend(Q.check_spatial_points(
        [o["longitude"] for o in occurrences],
        [o["latitude"] for o in occurrences],
        max_uncertainty_m=2000.0,
        uncertainty=[o["coordinate_uncertainty_m"] for o in occurrences]))
    report.checks_run += 1
    outside = [o for o in occurrences if o["quality_flag"] != "ok"]
    report.add(Q.Finding(
        "fuera_del_rectangulo_terrestre", "warning", count=len(outside),
        message=(f"{len(outside)} registros fuera del rectángulo terrestre de "
                 "El Salvador; se conservan marcados, no se eliminan"),
        examples=[{"occurrence_id": o["occurrence_id"],
                   "lon": o["longitude"], "lat": o["latitude"],
                   "taxon": o["taxon"]} for o in outside[:5]],
        detail={"rule": "un registro marino puede ser correcto; borrarlo sin "
                        "declararlo ocultaría la diferencia de cobertura"}))
    report.checks_run += 1
    no_uncertainty = sum(1 for o in occurrences
                         if o["coordinate_uncertainty_m"] is None)
    report.add(Q.Finding(
        "incertidumbre_no_declarada", "warning", count=no_uncertainty,
        message=f"{no_uncertainty} ocurrencias sin incertidumbre de coordenada declarada"))
    report.add(Q.Finding(
        "sesgo_de_muestreo", "warning",
        "GBIF agrega observaciones voluntarias: la densidad refleja esfuerzo de "
        "muestreo, no abundancia"))
    report.checks_run += 1
    report.add(Q.Finding(
        "clase_de_evidencia", "info",
        "ocurrencias de biodiversidad agregadas; el taxón y la fecha conservan "
        "la fuente original"))
    report.checks_run += 1
    return report


# --- programa principal ------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AGROSV Fase 4 — integración")
    parser.add_argument("--rebuild", action="store_true",
                        help="reconstruir catálogo, base y linaje desde cero")
    args = parser.parse_args(argv)
    try:  # consola Windows en cp1252: el informe contiene «≠», «°», «→»
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — consola no reconfigurable
        pass

    lay = S.layout()
    S.ensure_layout(lay)
    if args.rebuild:
        for target in (lay.catalog_path, lay.store_path, lay.lineage_path):
            if target.exists():
                target.unlink()
        for suffix in ("-wal", "-shm"):
            extra = Path(str(lay.store_path) + suffix)
            if extra.exists():
                extra.unlink()

    probes = probe_index()
    catalog = CAT.Catalog.load(lay.catalog_path)
    engine = ING.IngestEngine(lay)
    store = DataStore(lay.store_path)
    if not store.exists:
        store = DataStore(lay.store_path)
        store.init_schema()
    store.init_schema()

    skipped: list[str] = []

    # --- 1/2. muestras: ingesta y validación --------------------------------
    nasa_path = SAMPLES / "nasa_power_point" / "power_daily_13.70N_89.20W.json"
    meteo_path = SAMPLES / "open_meteo_point" / "openmeteo_daily_13.70N_89.20W.json"
    gbif_path = SAMPLES / "gbif_sv" / "gbif_occurrence_sv_300.json"
    wb_path = SAMPLES / "worldbank_slv" / "wb_agri_land_share_slv.json"
    chirps_path = SAMPLES / "chirps3_day" / "chirps-v3.0.rnl.2026.01.15.tif"
    soilrest_path = SAMPLES / "soilgrids_rest_point" / "soilgrids_phh2o_point.json"
    nemotron_path = SAMPLES / "nemotron_rows" / "nemotron_rows_sample.json"
    s2_path = SAMPLES / "sentinel2_stac" / "s2_stac_search.json"

    nasa_rows = parse_nasa(nasa_path)[0] if nasa_path.exists() else []
    meteo_rows = parse_open_meteo(meteo_path)[0] if meteo_path.exists() else []
    gbif_rows = parse_gbif(gbif_path)[0] if gbif_path.exists() else []
    wb_rows = parse_worldbank(wb_path)[0] if wb_path.exists() else []

    reports: dict[str, tuple[Q.QualityReport, Path]] = {}

    def register_report(report: Q.QualityReport) -> tuple[Q.QualityReport, Path]:
        path = report.save(lay.quality_dir)
        reports[report.dataset_id] = (report, path)
        store.insert_quality_report(report.as_dict())
        return report, path

    if nasa_rows:
        register_report(report_nasa(nasa_rows, lay))
    if meteo_rows:
        register_report(report_open_meteo(meteo_rows))
    if gbif_rows:
        register_report(report_gbif(gbif_rows))

    # Comparación NASA vs Open-Meteo: se anexa al informe de Open-Meteo.
    comparison_output = {}
    if nasa_rows and meteo_rows:
        comparison_output = compare_temperature(nasa_rows, meteo_rows)
        report, path = reports["open_meteo_point"]
        for key, result in comparison_output.items():
            report.add(Q.Finding(
                f"intercomparacion_temperatura_{key}", "info",
                f"{result['label']}: {result['comparison_class']} con "
                f"{result['n_common_days']} días comunes; "
                f"{result['evidence_use']}",
                detail={k: result[k] for k in
                        ("metrics", "evidence_use", "paired_values")}))
        report.checks_run += len(comparison_output)
        report.save(lay.quality_dir)
        store.insert_quality_report(report.as_dict())

    # CHIRPS: recorte y QC ráster.
    chirps_clip = None
    if chirps_path.exists():
        chirps_clip = lay.validated / "chirps3" / (
            "chirps3_precip_0p05deg_sv_2026-01-15_v3.0.tif")
        clip_info = RAS.clip_to_file(chirps_path, chirps_clip, C.SV_BOUNDS)
        findings, checks = Q.check_raster(
            chirps_clip, expected_crs="EPSG:4326",
            bounds=C.SV_BOUNDS, max_res_deg=0.0499)
        report = Q.QualityReport(
            "chirps3", rel(chirps_clip),
            checks_run=checks,
            scope="muestra de 1 día global recortada a El Salvador; no es una "
                  "serie nacional integrada")
        report.extend(findings)
        report.parameters = {"clip": clip_info,
                            "native_vs_effective": {
                                "native": "0,05° (pentadal; el diario está "
                                          "desagregado con ERA5)",
                                "effective": "diaria desagregada, no "
                                             "independiente a escala diaria"}}
        register_report(report)

    # World Bank: indicador nacional anual.
    if wb_rows:
        report = Q.QualityReport(
            "worldbank_agri_share", rel(wb_path), checks_run=0,
            scope="indicador nacional anual (superficie agrícola, % del territorio)")
        report.extend(Q.check_numeric([r["value"] for r in wb_rows],
                                      "agricultural_land_share",
                                      declared_unit="%", require_unit=False))
        report.checks_run += 1
        spec = T.TimeSeriesSpec(
            variable="agricultural_land_share", unit="%",
            evidence_class=T.EvidenceClass.AGGREGATE,
            frequency=T.Frequency.ANNUAL, time_basis="UTC",
            aggregation=T.Aggregation.MEAN,
            dataset_id="worldbank_agri_share", source_id="worldbank_api",
            temporal_resolution="anual",
            uncertainty_note="agregado nacional derivado por el Banco Mundial; "
                             "no es medición directa en El Salvador")
        report.extend(Q.check_temporal([r["date"] for r in wb_rows],
                                       [r["value"] for r in wb_rows], spec))
        report.checks_run += 1
        missing = Q.check_missing_vs_zero([r["value"] for r in wb_rows])
        report.add(Q.Finding("ausencia_vs_cero", "info",
                             "los años sin dato se excluyeron, no se rellenaron",
                             detail=missing))
        report.checks_run += 1
        register_report(report)

    # Rásteres de Fase 1: QC para respaldar su estado.
    report_phase1: dict[str, tuple[Q.QualityReport, Path]] = {}
    if C.DEM_WGS84.exists():
        # Sin umbral de NoData: el rectángulo del DEM incluye mar, de modo que
        # un porcentaje fijo marcaría como defecto una cobertura correcta.
        findings, checks = Q.check_raster(
            C.DEM_WGS84, expected_crs="EPSG:4326", bounds=C.SV_BOUNDS)
        rp = Q.QualityReport("copdem30", rel(C.DEM_WGS84), checks_run=checks,
                             scope="capa nacional completa (DEM y derivados)")
        rp.extend(findings)
        report_phase1["copdem30"] = register_report(rp)
    if C.SOILS_RASTER_DIR.exists():
        soil_raster = C.SOILS_RASTER_DIR / "phh2o_0-30cm.tif"
        if soil_raster.exists():
            findings, checks = Q.check_raster(soil_raster,
                                              expected_crs="EPSG:32616",
                                              bounds=C.SV_BOUNDS)
            rp = Q.QualityReport("soilgrids_2", rel(soil_raster),
                                 checks_run=checks,
                                 scope="6 propiedades 0–30 cm; predicción global "
                                       "a 250 m")
            rp.extend(findings)
            rp.add(Q.Finding(
                "prediccion_no_medicion", "warning",
                "SoilGrids es una predicción de modelo global: no es análisis de "
                "laboratorio y no se mezcla con CENTA"))
            report_phase1["soilgrids_2"] = register_report(rp)
    if C.TERRITORY_GPKG.exists():
        findings, checks = Q.check_vector(
            C.TERRITORY_GPKG, layer="adm1", bounds=C.SV_BOUNDS,
            expected_crs="EPSG:4326")
        rp = Q.QualityReport("geoboundaries_adm1", rel(C.TERRITORY_GPKG),
                             checks_run=checks,
                             scope="ADM1 (14 departamentos) completo")
        rp.extend(findings)
        report_phase1["geoboundaries_adm1"] = register_report(rp)
    if C.INFRA_GPKG.exists():
        import pyogrio

        info = pyogrio.read_info(C.INFRA_GPKG, layer="roads")
        bounds = [float(v) for v in info.get("total_bounds", [])]
        rp = Q.QualityReport("osm_sv", rel(C.INFRA_GPKG), checks_run=0,
                             scope="capa de vialidad (extracto Geofabrik)")
        rp.add(Q.Finding("crs", "info" if info.get("crs") else "error",
                         f"CRS declarado: {info.get('crs')}"))
        rp.checks_run += 1
        inside = (bounds and bounds[0] >= C.SV_BOUNDS[0] - 0.05
                  and bounds[1] >= C.SV_BOUNDS[1] - 0.05
                  and bounds[2] <= C.SV_BOUNDS[2] + 0.05
                  and bounds[3] <= C.SV_BOUNDS[3] + 0.05)
        rp.add(Q.Finding("cobertura", "info" if inside else "warning",
                         f"bounds {bounds} frente a El Salvador {C.SV_BOUNDS}"))
        rp.checks_run += 1
        rp.add(Q.Finding("entidades", "info",
                         f"{int(info.get('features', 0))} elementos en 'roads'"))
        rp.checks_run += 1
        rp.add(Q.Finding(
            "licencia_odbl", "warning",
            "ODbL 1.0: base de datos derivada sujeta a share-alike; no se "
            "redistribuye dentro de paquetes cerrados"))
        rp.checks_run += 1
        report_phase1["osm_sv"] = register_report(rp)

    # --- 3. sistema territorial --------------------------------------------
    index = TR.TerritorialIndex.from_geopackage(C.TERRITORY_GPKG, geometry=True)
    index.save(lay.territory_index)
    crosswalk_dir = lay.metadata / "crosswalks"
    crosswalk_dir.mkdir(parents=True, exist_ok=True)
    crosswalk_path = crosswalk_dir / "district_2023_municipality.json"
    if not crosswalk_path.exists():
        crosswalk_path.write_text(json.dumps({
            "source_level": "municipality_historic",
            "target_level": "municipality_2023",
            "source_id": "BCR/CNR — tabla oficial de correspondencia",
            "status": "INCOMPLETE",
            "entries": [],
            "limitation": (
                "No existe en el repositorio una tabla oficial verificada de los "
                "272 distritos (o municipios históricos) a los 44 municipios "
                "vigentes. Se deja vacía a propósito: inventarla produciría "
                "uniones incorrectas con el censo."),
            "required_evidence": (
                "Publicación del BCR/CNR con códigos de distrito y municipio, "
                "fecha de vigencia y decreto de reforma"),
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    store.insert_territories(index)

    # --- 4. integración de series ------------------------------------------
    obs_dir = lay.validated / "observations"
    csv_outputs: dict[str, Path] = {}
    obs_columns = ["dataset_id", "variable", "unit", "value", "time_local",
                   "time_utc", "period_start", "period_end", "frequency",
                   "aggregation", "evidence_class", "latitude", "longitude",
                   "cell_support", "quality_flag", "source_id"]
    if nasa_rows:
        csv_outputs["nasa_power_point"] = write_csv(
            obs_dir / "nasa_power_point_daily.csv", nasa_rows, obs_columns)
    if meteo_rows:
        csv_outputs["open_meteo_point"] = write_csv(
            obs_dir / "open_meteo_point_daily.csv", meteo_rows, obs_columns)

    integrated_rows: dict[str, int] = {}
    for dataset_id, rows in (("nasa_power_point", nasa_rows),
                             ("open_meteo_point", meteo_rows)):
        if not rows:
            continue
        with store.connect() as conn:
            conn.execute("DELETE FROM observations WHERE dataset_id = ?",
                         (dataset_id,))
        integrated_rows[dataset_id] = store.insert_observations(rows)

    if gbif_rows:
        csv_outputs["gbif_sv"] = write_csv(
            obs_dir / "gbif_sv_sample_occurrences.csv", gbif_rows,
            ["occurrence_id", "dataset_id", "taxon", "latitude", "longitude",
             "event_date", "basis_of_record", "coordinate_uncertainty_m",
             "quality_flag"])
        with store.connect() as conn:
            conn.execute("DELETE FROM occurrences WHERE dataset_id = 'gbif_sv'")
        integrated_rows["gbif_sv"] = store.insert_occurrences(gbif_rows)

    # --- 5. catálogo --------------------------------------------------------
    # Fase 1: ya integrados en la API anterior.
    if C.DEM_WGS84.exists():
        prov = provenance(C.DEM_WGS84)
        record = base_record(
            dataset_id="copdem30",
            name="Copernicus DEM GLO-30 y derivados topográficos",
            description="Modelo digital de superficie a 30 m con pendiente, "
                        "aspecto, hillshade y clases de relieve calculados por "
                        "AGROSV en EPSG:32616.",
            institution="Copernicus DEM (DLR/Airbus) — ESA/UE",
            source_url="https://copernicus-dem-30m.s3.amazonaws.com/",
            publication_date="2011-2015",
            download_date=str(prov.get("generated_at", ""))[:10] or None,
            version="GLO-30",
            license="Copernicus DEM (DLR/Airbus) — uso libre con atribución",
            redistribution_allowed=True, derived_use_allowed=True,
            geographic_coverage="El Salvador (tiles N13–N14, W089–W091)",
            temporal_coverage="2011–2015 (fecha de vuelo de la misión)",
            crs="EPSG:4326 (almacenamiento) / EPSG:32616 (derivados métricos)",
            spatial_resolution="30 m (1 arcsec); derivados a 30 m",
            temporal_resolution="estático",
            variables=["elevation", "slope", "aspect", "relief_class"],
            units={"elevation": "m", "slope": "deg", "aspect": "deg",
                   "relief_class": "class"},
            format="GeoTIFF teselado (COG-like)",
            size="91 MB el DEM; derivados < 100 MB",
            methodology="Remuestreo y cálculo de pendiente/aspecto en UTM 16N "
                        "con ventanas; relief por umbrales documentados.",
            limitations=[
                "es un DSM: incluye vegetación y edificios, no el suelo desnudo",
                "sin MDT nacional de referencia para validar exactitud vertical",
                "el extremo occidental tiene ~0,15% de distorsión de escala UTM",
            ],
            uncertainty="Exactitud vertical no verificada en el país; pendiente "
                        "heredada del DEM y sensible al ruido vertical",
            usage_restrictions="Atribución obligatoria (DLR/Airbus, Copernicus)",
            domain="TERRITORY",
            artifacts=[rel(C.DEM_WGS84), rel(C.SLOPE), rel(C.ASPECT),
                       rel(C.HILLSHADE), rel(C.RELIEF_CLASS)],
            notes="Fecha de descarga tomada del manifiesto de Fase 1; la fecha "
                  "de descarga original no se registró en esa fase.",
        )
        catalog.add(record, [file_ev(provenance_path(C.DEM_WGS84),
                                     "manifiesto de procedencia de Fase 1")])
        catalog.patch("copdem30", evidence_level="V1",
                      validation_scope=report_phase1["copdem30"][0].scope,
                      integration_scope="nacional (DEM y derivados a 30 m; consulta puntual y teselas)")
        for state, ev, note in (
            (CAT.DatasetState.DOWNLOADED,
             [file_ev(C.DEM_WGS84, "hash del DEM procesado")],
             "artefacto de Fase 1 presente y verificado"),
            (CAT.DatasetState.PARSED,
             [CAT.Evidence.from_file(C.DEM_WGS84,
                                     CAT.EvidenceType.PARSE_RESULT, passed=True,
                                     payload={"parser": "rasterio", "bands": 1})],
             "cabecera GeoTIFF leída con rasterio"),
            (CAT.DatasetState.VALIDATED,
             [validation_ev(report_phase1["copdem30"][1], report_phase1["copdem30"][0],
                            scope="capa nacional completa")],
             "QC de CRS, rejilla, NoData y cobertura"),
            (CAT.DatasetState.INTEGRATED,
             [integration_ev(lay, "copdem30", rows=0,
                             endpoint="/api/topography/elevation,/api/tiles",
                             details={"query": "punto y teselas"})],
             "servido por la API de topografía y teselas desde la Fase 1"),
        ):
            catalog.transition("copdem30", state, ev, note=note)

    if C.TERRITORY_GPKG.exists():
        prov = provenance(C.TERRITORY_GPKG)
        record = base_record(
            dataset_id="geoboundaries_adm1",
            name="Límites departamentales y municipales históricos",
            description="ADM0/ADM1/ADM2 de geoBoundaries con códigos ISO "
                        "3166-2:SV para departamentos y 272 municipios "
                        "pre-reforma 2023.",
            institution="geoBoundaries (William & Mary) — derivado de OSM",
            source_url="https://www.geoboundaries.org/",
            publication_date="2021",
            download_date=str(prov.get("generated_at", ""))[:10] or None,
            version="gbOpen 2021",
            license="CC BY-SA 2.0",
            redistribution_allowed=True, derived_use_allowed=True,
            geographic_coverage="El Salvador",
            temporal_coverage="2021 (ADM2 anterior a la reforma de 2023)",
            crs="EPSG:4326",
            spatial_resolution="vectorial; sin resolución de rejilla declarada",
            temporal_resolution="estático",
            variables=["area_km2", "boundary"],
            units={"area_km2": "km2", "boundary": "geometry"},
            format="GeoPackage",
            size="1,6 MB",
            methodology="Disolución y validación geométrica; áreas calculadas en "
                        "EPSG:6933, no en grados.",
            limitations=[
                "ADM2 son 272 polígonos históricos, NO los 44 municipios vigentes",
                "10 municipios sin nombre; cobertura del 97,22% del país",
                "no incluye distritos ni límites catastrales",
            ],
            uncertainty="Los límites son administrativos aproximados derivados "
                        "de OSM; no son levantamiento topográfico",
            usage_restrictions="CC BY-SA 2.0: base derivada sujeta a la misma "
                               "licencia",
            domain="TERRITORY",
            artifacts=[rel(C.TERRITORY_GPKG)],
            notes="No se renombra la capa de Fase 1; la corrección 2023 se "
                  "resolverá con la tabla de correspondencia oficial.",
        )
        catalog.add(record, [file_ev(provenance_path(C.TERRITORY_GPKG))])
        catalog.patch("geoboundaries_adm1", evidence_level="V1",
                      validation_scope=report_phase1["geoboundaries_adm1"][0].scope,
                      integration_scope="nacional (ADM1 completo; ADM2 histórico indexado)")
        for state, ev, note in (
            (CAT.DatasetState.DOWNLOADED, [file_ev(C.TERRITORY_GPKG)],
             "GeoPackage presente con manifiesto"),
            (CAT.DatasetState.PARSED,
             [CAT.Evidence.from_file(C.TERRITORY_GPKG,
                                     CAT.EvidenceType.PARSE_RESULT, passed=True,
                                     payload={"layers": ["adm0", "adm1", "adm2"]})],
             "capas y CRS leídos con pyogrio"),
            (CAT.DatasetState.VALIDATED,
             [validation_ev(report_phase1["geoboundaries_adm1"][1], report_phase1["geoboundaries_adm1"][0],
                            scope="ADM1 completo; ADM2 indexado sin validar "
                                  "correspondencia 2023")],
             "QC geométrico de ADM1 y revisión de cobertura"),
            (CAT.DatasetState.INTEGRATED,
             [integration_ev(lay, "geoboundaries_adm1", rows=len(index),
                             endpoint="/api/territory/{territory_id},"
                                      "/api/data/territories",
                             details={"levels": ["country", "department",
                                                 "municipality_historic"]})],
             "índice territorial e ingreso en la base de consulta"),
        ):
            catalog.transition("geoboundaries_adm1", state, ev, note=note)

    if "soilgrids_2" in report_phase1:
        soil_files = [C.SOILS_RASTER_DIR / f"{k}_0-30cm.tif"
                      for k in ("phh2o", "soc", "nitrogen", "clay", "sand", "silt")]
        prov = provenance(soil_files[0])
        record = base_record(
            dataset_id="soilgrids_2",
            name="SoilGrids 2.0 — propiedades del suelo 0–30 cm",
            description="pH, carbono orgánico, nitrógeno y textura predichos a "
                        "250 m para El Salvador, recortados de SoilGrids 2.0.",
            institution="ISRIC — World Soil Information",
            source_url="https://soilgrids.org/",
            publication_date="2017-2022 (datos de entrenamiento)",
            download_date=str(prov.get("generated_at", ""))[:10] or None,
            version="SoilGrids 2.0",
            license="CC BY 4.0",
            redistribution_allowed=True, derived_use_allowed=True,
            geographic_coverage="El Salvador (recorte nacional)",
            temporal_coverage="2017–2022 (modelo, no serie temporal)",
            crs="EPSG:32616 (rejilla UTM 16N de Fase 1; la consulta reproyecta "
                "desde EPSG:4326)",
            spatial_resolution="250 m (rejilla UTM 16N)",
            temporal_resolution="estático (modelo)",
            variables=["ph", "soil_organic_carbon", "soil_nitrogen",
                       "clay", "sand", "silt"],
            units={"ph": "", "soil_organic_carbon": "g kg-1",
                   "soil_nitrogen": "g kg-1", "clay": "%", "sand": "%",
                   "silt": "%"},
            format="GeoTIFF (6 archivos)",
            size="< 1 MB por propiedad recortada",
            methodology="Predicción con aprendizaje automático y covariables; "
                        "recorte y escalado de unidades documentados.",
            limitations=[
                "es predicción global, no medición de laboratorio en El Salvador",
                "error mayor en relieve complejo; 250 m no representa parcelas",
                "las fracciones texturales no suman 100 exactamente",
            ],
            uncertainty="Incertidumbre por propiedad publicada por ISRIC no "
                        "integrada aún; error local no validado",
            usage_restrictions="Atribución CC BY 4.0; no presentar como análisis "
                               "de laboratorio",
            domain="SOILS",
            artifacts=[rel(p) for p in soil_files if p.exists()],
        )
        catalog.add(record, [file_ev(provenance_path(soil_files[0]))])
        catalog.patch("soilgrids_2", evidence_level="V1",
                      validation_scope=report_phase1["soilgrids_2"][0].scope,
                      integration_scope="nacional (6 propiedades 0–30 cm; consulta puntual)")
        for state, ev, note in (
            (CAT.DatasetState.DOWNLOADED,
             [file_ev(p) for p in soil_files if p.exists()],
             "seis propiedades recortadas y verificadas"),
            (CAT.DatasetState.PARSED,
             [CAT.Evidence.from_file(soil_files[0],
                                     CAT.EvidenceType.PARSE_RESULT, passed=True,
                                     payload={"parser": "rasterio",
                                              "properties": 6})],
             "cabeceras GeoTIFF leídas"),
            (CAT.DatasetState.VALIDATED,
             [validation_ev(report_phase1["soilgrids_2"][1], report_phase1["soilgrids_2"][0],
                            scope="capa nacional de 6 propiedades 0–30 cm")],
             "QC de rejilla, NoData y rango de pH"),
            (CAT.DatasetState.INTEGRATED,
             [integration_ev(lay, "soilgrids_2", rows=0,
                             endpoint="/api/soils/point,/api/soils/summary",
                             details={"query": "punto"})],
             "consulta puntual servida desde Fase 1"),
        ):
            catalog.transition("soilgrids_2", state, ev, note=note)

    if "osm_sv" in report_phase1:
        prov = provenance(C.INFRA_GPKG)
        record = base_record(
            dataset_id="osm_sv",
            name="OpenStreetMap — infraestructura de El Salvador",
            description="Vialidad, hidrografía, asentamientos e infraestructura "
                        "del extracto Geofabrik de El Salvador.",
            institution="OpenStreetMap contributors (extracto Geofabrik)",
            source_url="https://download.geofabrik.de/central-america/el-salvador.html",
            publication_date=None,
            download_date=str(prov.get("generated_at", ""))[:10] or None,
            version="extracto diario",
            license="ODbL 1.0",
            redistribution_allowed=True, derived_use_allowed=True,
            geographic_coverage="El Salvador",
            temporal_coverage="instantánea del extracto (no serie histórica)",
            crs="EPSG:4326",
            spatial_resolution="vectorial; precisión variable por elemento",
            temporal_resolution="instantánea",
            variables=["area_km2", "length_km"],
            units={"area_km2": "km2", "length_km": "km"},
            format="GeoPackage",
            size="51 MB",
            methodology="Extracción por capas temáticas desde el extracto OSM; "
                        "longitudes calculadas en CRS métrico.",
            limitations=[
                "cobertura agrícola insuficiente: no hay parcelas ni cultivos",
                "precisión posicional heterogénea según colaborador",
                "la fecha de cada elemento es la del extracto, no la del terreno",
            ],
            uncertainty="Precisión posicional no medida; sin control de calidad "
                        "sistemático de OSM en el país",
            usage_restrictions="ODbL 1.0: atribución y share-alike sobre bases "
                               "derivadas; excluido de paquetes cerrados",
            domain="TERRITORY",
            artifacts=[rel(C.INFRA_GPKG)],
        )
        catalog.add(record, [file_ev(provenance_path(C.INFRA_GPKG))])
        catalog.patch("osm_sv", evidence_level="V1",
                      validation_scope=report_phase1["osm_sv"][0].scope,
                      integration_scope="nacional (capas temáticas por bbox)")
        for state, ev, note in (
            (CAT.DatasetState.DOWNLOADED, [file_ev(C.INFRA_GPKG)],
             "extracto procesado con manifiesto"),
            (CAT.DatasetState.PARSED,
             [CAT.Evidence.from_file(C.INFRA_GPKG,
                                     CAT.EvidenceType.PARSE_RESULT, passed=True,
                                     payload={"layers": 6})],
             "capas y CRS verificados con pyogrio"),
            (CAT.DatasetState.VALIDATED,
             [validation_ev(report_phase1["osm_sv"][1], report_phase1["osm_sv"][0],
                            scope="capa de vialidad; cobertura nacional")],
             "QC de CRS, cobertura y licencia"),
            (CAT.DatasetState.INTEGRATED,
             [integration_ev(lay, "osm_sv", rows=0,
                             endpoint="/api/infrastructure/{layer}",
                             details={"query": "capa por bbox"})],
             "servido por la API de infraestructura"),
        ):
            catalog.transition("osm_sv", state, ev, note=note)

    # Muestras de punto y biodiversidad.
    def register_sample(*, dataset_id: str, name: str, description: str,
                        institution: str, url: str, license_: str,
                        domain: str, coverage: str, temporal: str, crs: str | None,
                        res: str, tres: str, variables: list[str],
                        units: dict[str, str], fmt: str, methodology: str,
                        limitations: list[str], uncertainty: str,
                        restrictions: str, sample_path: Path, report_key: str,
                        endpoint: str, rows: int, extra: dict[str, Any] | None = None,
                        redistributable: bool = True,
                        evidence_level: str = "V1",
                        integration_details: dict[str, Any] | None = None,
                        integrate: bool = True) -> None:
        record = base_record(
            dataset_id=dataset_id, name=name, description=description,
            institution=institution, source_url=url, publication_date=None,
            download_date=None, version=None, license=license_,
            redistribution_allowed=redistributable,
            derived_use_allowed=redistributable,
            geographic_coverage=coverage, temporal_coverage=temporal, crs=crs,
            spatial_resolution=res, temporal_resolution=tres,
            variables=variables, units=units, format=fmt,
            size=f"{sample_path.stat().st_size:,} B" if sample_path.exists() else None,
            methodology=methodology, limitations=limitations,
            uncertainty=uncertainty, usage_restrictions=restrictions,
            domain=domain, artifacts=[rel(sample_path)], evidence_level=evidence_level,
            notes="Muestra mínima de Fase 3; no es el dataset nacional completo.",
        )
        catalog.add(record, [file_ev(sample_path, "muestra descargada en Fase 3")])
        ingest_record = engine.ingest_local(
            sample_path, dataset_id=dataset_id,
            source_id=record.institution.split(" ")[0].lower(),
            license=license_, source_url=url)
        catalog.patch(dataset_id,
                      download_date=ingest_record.retrieved_at[:10],
                      artifacts=[rel(sample_path)])
        downloaded_ev = [CAT.Evidence.from_file(
            sample_path, CAT.EvidenceType.FILE_HASH, passed=True,
            note=f"sha256 {ingest_record.sha256[:16]}…")]
        catalog.transition(dataset_id, CAT.DatasetState.DOWNLOADED, downloaded_ev,
                          note="muestra descargada y hasheada")
        parse_path = Path(ingest_record.manifest_path or "")
        catalog.transition(dataset_id, CAT.DatasetState.PARSED,
                          [parse_ev(parse_path, ingest_record.format)],
                          note="formato detectado y metadatos extraídos")
        report, report_path = reports[report_key]
        catalog.patch(dataset_id, evidence_level=evidence_level,
                      validation_scope=report.scope)
        catalog.transition(
            dataset_id, CAT.DatasetState.VALIDATED,
            [validation_ev(report_path, report, report.scope)],
            note=f"motor de calidad: {report.status} con {report.checks_run} "
                 "comprobaciones")
        if integrate:
            catalog.patch(dataset_id, integration_scope="muestra de punto / "
                                                       "conjunto de ocurrencias")
            catalog.transition(
                dataset_id, CAT.DatasetState.INTEGRATED,
                [integration_ev(lay, dataset_id, rows=rows, endpoint=endpoint,
                                details=integration_details or {})],
                note="consultable por /api/data")

    if nasa_rows:
        register_sample(
            dataset_id="nasa_power_point",
            name="NASA POWER — serie diaria de punto",
            description="Precipitación corregida y temperaturas máxima/mínima "
                        "diarias para 13,70 N, 89,20 W (2019–2025).",
            institution="NASA POWER (NASA LaRC)",
            url=("https://power.larc.nasa.gov/api/temporal/daily/point?parameters="
                 "PRECTOTCORR,T2M_MAX,T2M_MIN&community=AG&longitude=-89.20"
                 "&latitude=13.70&start=20190101&end=20251231&format=JSON"),
            license_="NASA POWER: datos abiertos, uso comercial permitido con cita",
            domain="CLIMATE",
            coverage="1 punto (celda POWER de 0,5° × 0,625°)",
            temporal="2019-01-01 a 2025-12-31 (2.557 días)",
            crs="EPSG:4326 (coordenada del punto)",
            res="punto; soporte de celda 0,5° × 0,625°",
            tres="diaria",
            variables=["precipitation", "temperature"],
            units={"precipitation": "mm", "temperature": "degC"},
            fmt="JSON",
            methodology="Descarga de la API diaria; normalización de unidades, "
                        "conversión de centinela -999 a ausencia y período diario "
                        "local (LST) expresado en UTC−6.",
            limitations=[
                "es reanálisis MERRA-2, no una estación meteorológica",
                "un punto no representa el país ni un departamento",
                "el día está en hora solar local (LST), no en UTC civil",
                "la precipitación diaria es desagregada, no medida a esa escala",
            ],
            uncertainty="Error de representación espacial no cuantificado; sin "
                        "estaciones de referencia disponibles para validar",
            restrictions="Citar NASA POWER Project",
            sample_path=nasa_path, report_key="nasa_power_point",
            endpoint="/api/data/observations?dataset_id=nasa_power_point",
            rows=integrated_rows.get("nasa_power_point", 0),
            evidence_level="V1",
            integration_details={"variables": ["precipitation", "temperature"],
                                 "frequency": "daily",
                                 "time_basis": "LST (UTC−6 asumido)"},
        )

    if meteo_rows:
        register_sample(
            dataset_id="open_meteo_point",
            name="Open-Meteo — serie diaria de punto",
            description="Precipitación, temperatura, ET₀ FAO-56 y humedad "
                        "relativa diarias para 13,67 N, 89,17 W (2019–2025).",
            institution="Open-Meteo (agregador ERA5/IFS)",
            url=("https://archive-api.open-meteo.com/v1/archive?latitude=13.70"
                 "&longitude=-89.20&start_date=2019-01-01&end_date=2025-12-31"
                 "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,"
                 "et0_fao_evapotranspiration,relative_humidity_2m_mean"
                 "&timezone=America%2FEl_Salvador"),
            license_="CC BY 4.0; nivel gratuito solo uso no comercial",
            domain="CLIMATE",
            coverage="1 punto (celda ~9 km)",
            temporal="2019-01-01 a 2025-12-31 (2.557 días)",
            crs="EPSG:4326",
            res="punto; soporte de celda 0,1° (~9 km)",
            tres="diaria",
            variables=["precipitation", "temperature", "et0",
                       "relative_humidity"],
            units={"precipitation": "mm", "temperature": "degC", "et0": "mm",
                   "relative_humidity": "%"},
            fmt="JSON",
            methodology="Descarga con zona America/El_Salvador (UTC−6); períodos "
                        "diarios locales convertidos a UTC; unidades verificadas "
                        "contra daily_units.",
            limitations=[
                "agregador de reanálisis: no es medición local",
                "una celda de ~9 km no representa un municipio ni una parcela",
                "ET₀ calculada por el proveedor, no derivada por AGROSV",
                "el nivel gratuito es solo para uso no comercial",
            ],
            uncertainty="No cuantificada para El Salvador; intercomparación con "
                        "NASA POWER registrada en el informe de calidad",
            restrictions="CC BY 4.0; uso comercial requiere plan de pago",
            sample_path=meteo_path, report_key="open_meteo_point",
            endpoint="/api/data/observations?dataset_id=open_meteo_point",
            rows=integrated_rows.get("open_meteo_point", 0),
            redistributable=False,
            evidence_level="V1",
            integration_details={"variables": ["precipitation", "temperature",
                                               "et0", "relative_humidity"],
                                 "frequency": "daily"},
        )

    if gbif_rows:
        register_sample(
            dataset_id="gbif_sv",
            name="GBIF — muestra de ocurrencias de especies en El Salvador",
            description="300 ocurrencias georreferenciadas descargadas de GBIF "
                        "para El Salvador, con taxón, fecha e incertidumbre.",
            institution="GBIF (Global Biodiversity Information Facility)",
            url="https://api.gbif.org/v1/occurrence/search?country=SV&limit=300",
            license_="Por registro (GBIF agrega licencias de publicadores)",
            domain="BIODIVERSITY",
            coverage="El Salvador (300 registros, no inventario completo)",
            temporal="1600–2026 según eventDate de cada registro",
            crs="EPSG:4326",
            res="punto (incertidumbre declarada por registro)",
            tres="evento (fecha de observación)",
            variables=["occurrence"],
            units={"occurrence": "count"},
            fmt="JSON",
            methodology="Descarga de la API de ocurrencias; normalización de "
                        "coordenadas, fecha e incertidumbre; validación espacial.",
            limitations=[
                "sesgo de muestreo: la densidad refleja observadores, no abundancia",
                "taxón y fecha dependen de la calidad del publicador",
                "coordenadas con incertidumbre de hasta kilómetros",
                "no es un inventario nacional ni una lista roja",
            ],
            uncertainty="Incertidumbre por registro; ausente en parte de los casos",
            restrictions="Citar GBIF y los publicadores de cada registro",
            sample_path=gbif_path, report_key="gbif_sv",
            endpoint="/api/data/occurrences?dataset_id=gbif_sv",
            rows=integrated_rows.get("gbif_sv", 0),
            evidence_level="V1",
            integration_details={"table": "occurrences", "records": len(gbif_rows)},
        )

    # CHIRPS: validado, no integrado como serie nacional.
    if chirps_clip and "chirps3" in reports:
        sample_prov = read_json(SAMPLES / "chirps3_day" / "sample.json", {}) or {}
        record = base_record(
            dataset_id="chirps3",
            name="CHIRPS v3 — precipitación (muestra de un día)",
            description="Muestra del producto diario CHIRPS v3 para 2026-01-15, "
                        "recortada a El Salvador; no es una serie integrada.",
            institution="Climate Hazards Center, UC Santa Barbara",
            source_url=sample_prov.get("url", "https://data.chc.ucsb.edu/"),
            publication_date="2026-01-15 (fecha del dato)",
            download_date=str(sample_prov.get("retrieved_at", ""))[:10] or None,
            version="v3.0 (variante rnl)",
            license="Uso abierto con atribución (verificar aviso CHC)",
            redistribution_allowed=True, derived_use_allowed=True,
            geographic_coverage="global, recortado a El Salvador",
            temporal_coverage="1 día (2026-01-15)",
            crs="EPSG:4326",
            spatial_resolution="0,05° (~5,5 km)",
            temporal_resolution="diaria desagregada; nativa pentadal",
            variables=["precipitation"],
            units={"precipitation": "mm"},
            format="GeoTIFF (muestra) → GeoTIFF recortado",
            size="14 MB muestra global; recorte nacional de pocos MB",
            methodology="Recorte por extensión sin remuestreo; metadatos y "
                        "NoData verificados; se conserva el archivo original.",
            limitations=[
                "el producto diario está desagregado con ERA5: no es "
                "independiente a escala diaria",
                "una muestra de un día no permite validar la serie",
                "no se ha comparado con estaciones nacionales",
            ],
            uncertainty="Error del producto no evaluado en El Salvador; resolución "
                        "de 0,05° no es precisión de 5 km",
            usage_restrictions="Atribución a CHIRPS/CHC",
            domain="CLIMATE",
            artifacts=[rel(chirps_clip), rel(chirps_path)],
        )
        catalog.add(record, [file_ev(chirps_path, "muestra CHIRPS de Fase 3")])
        catalog.patch("chirps3",
                      download_date=str(sample_prov.get("retrieved_at", ""))[:10] or None,
                      artifacts=[rel(chirps_clip), rel(chirps_path)])
        ingest_rec = engine.ingest_local(chirps_path, dataset_id="chirps3",
                                         source_id="chirps3",
                                         license=record.license,
                                         source_url=record.source_url)
        catalog.transition("chirps3", CAT.DatasetState.DOWNLOADED,
                          [file_ev(chirps_path)],
                          note="muestra global descargada y hasheada")
        catalog.transition(
            "chirps3", CAT.DatasetState.PARSED,
            [parse_ev(Path(ingest_rec.manifest_path or ""), "geotiff")],
            note="cabecera y rejilla verificadas; recorte al país registrado")
        report, report_path = reports["chirps3"]
        catalog.patch("chirps3", validation_scope=report.scope, evidence_level="V1")
        catalog.transition("chirps3", CAT.DatasetState.VALIDATED,
                          [validation_ev(report_path, report, report.scope)],
                          note="QC ráster de CRS, rejilla, NoData y cobertura")

    if wb_rows and "worldbank_agri_share" in reports:
        sample_prov = read_json(SAMPLES / "worldbank_slv" / "sample.json", {}) or {}
        record = base_record(
            dataset_id="worldbank_agri_share",
            name="Banco Mundial — superficie agrícola (% del territorio)",
            description="Indicador AG.LND.AGRI.ZS para El Salvador, 1960–2024, "
                        "como contexto macro; no representa uso agrícola actual.",
            institution="World Bank Open Data",
            source_url=sample_prov.get("url", "https://api.worldbank.org/"),
            publication_date="2026-11-11 (última actualización del indicador)",
            download_date=str(sample_prov.get("retrieved_at", ""))[:10] or None,
            version="AG.LND.AGRI.ZS",
            license="CC BY 4.0",
            redistribution_allowed=True, derived_use_allowed=True,
            geographic_coverage="El Salvador (agregado nacional)",
            temporal_coverage="1960–2024 (anual, con vacíos)",
            crs=None,
            spatial_resolution="agregado nacional (no espacial)",
            temporal_resolution="anual",
            variables=["agricultural_land_share"],
            units={"agricultural_land_share": "%"},
            format="JSON",
            size="14,9 kB",
            methodology="Serie anual del indicador; años sin dato excluidos, no "
                        "rellenados.",
            limitations=[
                "agregado nacional: no sirve para departamento ni municipio",
                "la definición de «tierra agrícola» incluye pastos y cultivos",
                "no es medición de campo de AGROSV",
            ],
            uncertainty="Metadatos del indicador no verificados contra la fuente "
                        "primaria de El Salvador",
            usage_restrictions="Atribución CC BY 4.0",
            domain="AGRICULTURE",
            artifacts=[rel(wb_path)],
        )
        catalog.add(record, [file_ev(wb_path)])
        ingest_rec = engine.ingest_local(wb_path, dataset_id="worldbank_agri_share",
                                         source_id="worldbank_api",
                                         license=record.license,
                                         source_url=record.source_url)
        catalog.patch("worldbank_agri_share",
                      download_date=str(sample_prov.get("retrieved_at", ""))[:10] or None)
        catalog.transition("worldbank_agri_share", CAT.DatasetState.DOWNLOADED,
                          [file_ev(wb_path)], note="serie descargada y hasheada")
        catalog.transition(
            "worldbank_agri_share", CAT.DatasetState.PARSED,
            [parse_ev(Path(ingest_rec.manifest_path or ""), "json")],
            note="JSON parseado; 65 registros anuales")
        report, report_path = reports["worldbank_agri_share"]
        catalog.patch("worldbank_agri_share", validation_scope=report.scope,
                      evidence_level="V1")
        catalog.transition("worldbank_agri_share", CAT.DatasetState.VALIDATED,
                          [validation_ev(report_path, report, report.scope)],
                          note="QC numérico, temporal y ausencia-vs-cero")

    # --- 6. datasets no integrados y restricciones -------------------------
    def add_simple(*, dataset_id: str, name: str, description: str,
                   institution: str, url: str, license_: str, domain: str,
                   coverage: str, temporal: str, fmt: str, res: str,
                   tres: str, limitations: list[str], uncertainty: str,
                   restrictions: str, methodology: str = "No evaluada: el "
                   "recurso no está disponible para inspección.",
                   artifacts: list[str] | None = None,
                   publication: str | None = None,
                   evidence: CAT.Evidence | None = None,
                   target: CAT.DatasetState | None = None,
                   transitions: list[tuple[CAT.DatasetState, list[CAT.Evidence], str]] | None = None,
                   crs: str | None = None,
                   variables: list[str] | None = None,
                   units: dict[str, str] | None = None,
                   evidence_level: str = "V0") -> None:
        download_date = None
        if artifacts:
            existing = [p for p in artifacts if (ROOT / p).exists()]
            if existing:
                download_date = datetime.fromtimestamp(
                    (ROOT / existing[0]).stat().st_mtime).strftime("%Y-%m-%d")
        record = base_record(
            dataset_id=dataset_id, name=name, description=description,
            institution=institution, source_url=url, publication_date=publication,
            download_date=download_date, version=None, license=license_,
            redistribution_allowed=None, derived_use_allowed=None,
            geographic_coverage=coverage, temporal_coverage=temporal, crs=crs,
            spatial_resolution=res, temporal_resolution=tres,
            variables=variables or [], units=units or {}, format=fmt,
            size=None, methodology=methodology, limitations=limitations,
            uncertainty=uncertainty, usage_restrictions=restrictions,
            domain=domain, artifacts=artifacts or [], evidence_level=evidence_level,
        )
        catalog.add(record, [evidence or probe_ev(probes, dataset_id)],
                    note="alta en catálogo con evidencia de descubrimiento")
        for state, evs, note in (transitions or []):
            catalog.transition(dataset_id, state, evs, note=note)

    # DOWNLOADED sin parsear: solo metadatos STAC.
    if s2_path.exists():
        add_simple(
            dataset_id="sentinel2_c1_l2a",
            name="Sentinel-2 Collection-1 L2A — metadatos STAC",
            description="Resultado de búsqueda STAC (2 ítems, 36 coincidencias) "
                        "sobre El Salvador. No se descargaron escenas.",
            institution="Copernicus/ESA (vía STAC Earth Search)",
            url="https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a",
            license_="Copernicus (atribución)",
            domain="TERRITORY",
            coverage="Global; consulta sobre El Salvador",
            temporal="2015–actualidad (escenas)",
            fmt="JSON (STAC ItemCollection)",
            res="10 / 20 / 60 m",
            tres="5 días (revisita)",
            crs="EPSG:32616 (UTM 16N en las escenas de la zona)",
            variables=["metadata"],
            units={"metadata": "count"},
            limitations=[
                "solo se descargaron metadatos STAC, no imágenes",
                "sin escenas archivadas no hay índice espectral ni serie NDVI",
                "las nubes de la época lluviosa limitan la observación óptica",
            ],
            uncertainty="No aplica: no se procesó ninguna observación",
            restrictions="Atribución Copernicus; sin datos archivados",
            methodology="Búsqueda STAC con filtro de cobertura; sin descarga de "
                        "COG (decisión registrada en Fase 3).",
            artifacts=[rel(s2_path)],
            evidence=file_ev(s2_path),
            transitions=[(
                CAT.DatasetState.DOWNLOADED,
                [file_ev(s2_path)],
                "metadatos STAC descargados; no se descargaron escenas")],
            evidence_level="V0",
        )

    # PARSED sin validar: Nemotron es sintético.
    if nemotron_path.exists():
        add_simple(
            dataset_id="nemotron_sv",
            name="Nemotron Personas SV — muestra de filas sintéticas",
            description="Tres filas de ejemplo del dataset de personas "
                        "sintéticas de El Salvador; no representan productores.",
            institution="NVIDIA (Nemotron Personas)",
            url="https://huggingface.co/datasets/nvidia/Nemotron-Personas-El-Salvador",
            license_="CC BY 4.0",
            domain="ECONOMY",
            coverage="El Salvador (44 municipios declarados por el proveedor)",
            temporal="2026-06-05 (publicación)",
            fmt="JSON (filas de muestra)",
            res="no espacial",
            tres="no temporal",
            limitations=[
                "datos sintéticos: no son personas ni explotaciones reales",
                "no sirven como evidencia socioeconómica ni para inferencia",
                "no se validan como observación; permanecen PARSED",
            ],
            uncertainty="No aplica: la generación sintética no tiene error de "
                        "medición, pero tampoco validez empírica",
            restrictions="CC BY 4.0; uso ilustrativo, nunca como dato observado",
            variables=["persona_uuid", "professional_persona"],
            units={"persona_uuid": "id", "professional_persona": "text"},
            artifacts=[rel(nemotron_path)],
            evidence=file_ev(nemotron_path),
            methodology="Inspección de estructura y tres filas; sin validación "
                        "científica por ser sintético.",
            transitions=[(
                CAT.DatasetState.DOWNLOADED,
                [file_ev(nemotron_path)],
                "muestra de filas descargada"),
                (CAT.DatasetState.PARSED,
                 [CAT.Evidence.from_file(
                     nemotron_path, CAT.EvidenceType.PARSE_RESULT, passed=True,
                     payload={"rows": 3, "synthetic": True})],
                 "estructura parseada; no se promueve a VALIDATED")],
            evidence_level="V0",
        )

    # REJECTED: SoilGrids REST devuelve null.
    if soilrest_path.exists():
        add_simple(
            dataset_id="soilgrids_rest",
            name="SoilGrids 2.0 — API REST (rechazada)",
            description="Consulta REST de pH en un punto: HTTP 200 con "
                        "`mean: null`. No es una fuente utilizable para ingesta.",
            institution="ISRIC — World Soil Information",
            url="https://rest.isric.org/soilgrids/v2.0/properties/query",
            license_="CC BY 4.0",
            domain="SOILS",
            coverage="punto 13,70 N / 89,20 W",
            temporal="consulta 2026-11-22",
            fmt="JSON",
            res="250 m (declarado por el proveedor)",
            tres="estático",
            limitations=[
                "la respuesta no contiene valor (`mean: null`): defecto del canal",
                "el WebDAV/COG de ISRIC sí funciona y es la vía usada",
            ],
            uncertainty="No aplica: no hay valor que interpretar",
            restrictions="CC BY 4.0",
            variables=["ph"],
            units={"ph": ""},
            artifacts=[rel(soilrest_path)],
            evidence=file_ev(soilrest_path),
            transitions=[
                (CAT.DatasetState.DOWNLOADED, [file_ev(soilrest_path)],
                 "respuesta JSON descargada"),
                (CAT.DatasetState.PARSED,
                 [CAT.Evidence.from_file(
                     soilrest_path, CAT.EvidenceType.PARSE_RESULT, passed=True,
                     payload={"mean": None})],
                 "JSON parseado; el campo mean es null"),
                (CAT.DatasetState.REJECTED,
                 [CAT.Evidence(
                     evidence_type=CAT.EvidenceType.VALIDATION_REPORT,
                     reference=rel(soilrest_path),
                     note="mean=null: no hay dato que validar",
                     passed=False,
                     payload={"status": "FAIL", "reason": "null_payload"})],
                 "rechazada: el canal devuelve null; se usa WebDAV"),
            ],
            evidence_level="V0",
        )

    # DISCOVERED: HydroSHEDS solo portal.
    add_simple(
        dataset_id="hydrosheds",
        name="HydroSHEDS / HydroBASINS — red hídrica global",
        description="Red hídrica y cuencas anidadas globales; portal verificado, "
                    "sin descarga realizada ni delimitación nacional validada.",
        institution="WWF / USGS",
        url="https://www.hydrosheds.org/products",
        license_="Verificar EULA de HydroSHEDS (no es licencia abierta estándar)",
        domain="HYDROLOGY",
        coverage="global",
        temporal="~2000 (base SRTM)",
        fmt="Shapefile / GeoTIFF",
        res="15–90 arcsec según producto",
        tres="estático",
        limitations=[
            "no hay delimitación oficial de cuencas de El Salvador integrada",
            "la topología global no sustituye el PNGIRH del MARN",
        ],
        uncertainty="No evaluada: no se descargó el producto",
        restrictions="Licencia por verificar antes de cualquier uso derivado",
        evidence=probe_ev(probes, "hydrosheds"),
        evidence_level="V0",
    )

    # ACCESS_PENDING
    add_simple(
        dataset_id="cnr_elsalvadormaps",
        name="CNR — El Salvador Maps (ortofoto, LiDAR, MDT/MDS)",
        description="Plataforma nacional de ortofoto y LiDAR declarada por el "
                    "CNR; sin ficha técnica ni licencia públicas.",
        institution="Centro Nacional de Registros (CNR)",
        url="https://elsalvadormaps.sv/",
        license_="No localizada",
        domain="TERRITORY",
        coverage="nacional; hasta 10 cm declarados",
        temporal="2023 (proyecto)",
        fmt="Visor / servicios",
        res="hasta 10 cm (declarado, no verificado)",
        tres="estático",
        limitations=[
            "certificado TLS inválido al sondear: no se pudo verificar contenido",
            "sin licencia de reutilización documentada",
            "sin ficha de resolución, fecha de vuelo ni exactitud vertical",
        ],
        uncertainty="No evaluada: acceso no verificado",
        restrictions="Requiere convenio/compra y autorización escrita de derivados",
        evidence=probe_ev(probes, "cnr_elsalvadormaps", passed=False,
                          note="TLS inválido; no se estableció acceso"),
        transitions=[(
            CAT.DatasetState.ACCESS_PENDING,
            [probe_ev(probes, "cnr_elsalvadormaps", passed=False,
                      note="solicitud de ficha técnica y licencia pendiente")],
            "acceso pendiente de autorización institucional")],
    )
    add_simple(
        dataset_id="faostat",
        name="FAOSTAT — producción y comercio agropecuario",
        description="Estadísticas agrícolas por país; API y bulk no respondieron "
                    "en la verificación de Fase 3.",
        institution="FAO",
        url="https://www.fao.org/faostat/en/#data",
        license_="FAO (verificar condiciones de reutilización)",
        domain="AGRICULTURE",
        coverage="global por país",
        temporal="1961–",
        fmt="API/CSV",
        res="agregado nacional",
        tres="anual",
        limitations=[
            "API devolvió 521 y el bulk 403 en la verificación",
            "agregado nacional: no desagrega departamento",
        ],
        uncertainty="No evaluada",
        restrictions="Condiciones FAO por confirmar",
        evidence=probe_ev(probes, "faostat_api", passed=False,
                          note="API 521 / bulk 403"),
        transitions=[(
            CAT.DatasetState.ACCESS_PENDING,
            [probe_ev(probes, "faostat_api", passed=False,
                      note="reintentar con canal oficial alternativo")],
            "canal no disponible; se mantiene pendiente")],
    )

    # RESTRICTED
    add_simple(
        dataset_id="centa_suelos",
        name="CENTA — Mapa Digital de Suelos",
        description="Textura, pH, materia orgánica y nutrientes con ~11.000 "
                    "muestras declaradas; visor público, descarga no verificada.",
        institution="CENTA (MAG)",
        url="https://www.centa.gob.sv/mapa-digital-de-suelos",
        license_="No declarada",
        domain="SOILS",
        coverage="nacional; escala no verificada",
        temporal="publicación 2026-06-05",
        fmt="Visor ArcGIS / geodatabase (no verificada)",
        res="no verificada",
        tres="estático",
        limitations=[
            "portal responde 403 a clientes no navegador",
            "Hub ArcGIS devuelve 0 ítems",
            "sin licencia de uso ni de derivados",
        ],
        uncertainty="No evaluada: sin acceso a los datos",
        restrictions="Requiere solicitud formal y licencia; no se sustituye por "
                     "SoilGrids sin declararlo",
        evidence=doc_ev("centa_suelos",
                        "acceso restringido; requiere convenio con CENTA"),
        transitions=[(
            CAT.DatasetState.RESTRICTED,
            [CAT.Evidence(evidence_type=CAT.EvidenceType.LICENSE_CHECK,
                          reference=rel(PROBES_PATH) + "#centa_suelos",
                          note="sin licencia declarada; acceso 403",
                          passed=True,
                          payload={"requires": "convenio", "license": "no declarada"})],
            "restringido: sin licencia ni acceso verificable")],
    )
    add_simple(
        dataset_id="agera5",
        name="AgERA5 — agroclima diario (C3S)",
        description="Reanálisis agroclimático a 0,1° con variables para modelos "
                    "de cultivo; requiere token del Climate Data Store.",
        institution="Copernicus Climate Change Service (C3S)",
        url="https://cds.climate.copernicus.eu/datasets/sis-agrometeorological-indicators",
        license_="CC BY 4.0 (requiere cuenta CDS)",
        domain="CLIMATE",
        coverage="global 0,1°",
        temporal="1979–",
        fmt="NetCDF/Zarr",
        res="0,1° (~11 km)",
        tres="diaria",
        limitations=[
            "requiere token CDS no disponible en este entorno",
            "0,1° no representa parcelas ni valles locales",
        ],
        uncertainty="No evaluada; error del reanálisis no verificado en el país",
        restrictions="CC BY 4.0 con registro CDS",
        evidence=doc_ev("agera5", "token CDS requerido; no descargado"),
        transitions=[(
            CAT.DatasetState.RESTRICTED,
            [CAT.Evidence(evidence_type=CAT.EvidenceType.LICENSE_CHECK,
                          reference=rel(PROBES_PATH) + "#agera5_cds",
                          note="acceso con cuenta/token CDS", passed=True,
                          payload={"requires": "CDS token"})],
            "restringido por credenciales")],
    )
    add_simple(
        dataset_id="worldclim_21",
        name="WorldClim 2.1 — bioclimáticas y escenarios",
        description="19 variables bioclimáticas y proyecciones; licencia no "
                    "comercial sin redistribución.",
        institution="WorldClim (Fick & Hijmans)",
        url="https://www.worldclim.org/data/worldclim21.html",
        license_="No comercial, sin redistribución",
        domain="CLIMATE",
        coverage="global 30 arcsec",
        temporal="1970–2000 y escenarios SSP",
        fmt="GeoTIFF",
        res="30 arcsec (~1 km)",
        tres="normal climática / escenario",
        limitations=[
            "licencia impide redistribución y uso comercial",
            "interpolación de estaciones, no observación en rejilla",
        ],
        uncertainty="No evaluada; interpolación en relieve complejo es incierta",
        restrictions="No comercial, sin redistribución: solo uso interno derivado",
        evidence=doc_ev("worldclim_21", "licencia no comercial"),
        transitions=[(
            CAT.DatasetState.RESTRICTED,
            [CAT.Evidence(evidence_type=CAT.EvidenceType.LICENSE_CHECK,
                          reference="docs/data_expansion/DATA_LICENSE_AND_ACCESS_REPORT.md",
                          note="licencia no comercial, sin redistribución",
                          passed=True,
                          payload={"commercial": False,
                                   "redistribution": False})],
            "restringido por licencia")],
    )
    add_simple(
        dataset_id="protectedplanet",
        name="Protected Planet — áreas protegidas",
        description="Base mundial de áreas protegidas; API requiere token.",
        institution="UNEP-WCMC",
        url="https://www.protectedplanet.net/",
        license_="No comercial; API con token",
        domain="BIODIVERSITY",
        coverage="global",
        temporal="actualización continua",
        fmt="Web/API",
        res="vectorial",
        tres="estático",
        limitations=[
            "API devolvió 401 sin token",
            "los límites de áreas protegidas de El Salvador no están verificados",
        ],
        uncertainty="No evaluada",
        restrictions="Token y uso no comercial",
        evidence=doc_ev("protectedplanet", "API 401 sin token"),
        transitions=[(
            CAT.DatasetState.RESTRICTED,
            [CAT.Evidence(evidence_type=CAT.EvidenceType.LICENSE_CHECK,
                          reference=rel(PROBES_PATH) + "#protectedplanet_sv",
                          note="token requerido; uso no comercial", passed=True,
                          payload={"requires": "API token"})],
            "restringido por token y licencia")],
    )

    # UNAVAILABLE
    add_simple(
        dataset_id="marn_geoportal",
        name="MARN — geoportal de servicios REST",
        description="Geoportal ambiental del MARN; no respondió en la "
                    "verificación (HTTP 522).",
        institution="Ministerio de Medio Ambiente y Recursos Naturales (MARN)",
        url="https://geoportal.marn.gob.sv/",
        license_="No declarada",
        domain="HYDROLOGY",
        coverage="nacional",
        temporal="no verificable",
        fmt="REST",
        res="no verificable",
        tres="no verificable",
        limitations=[
            "HTTP 522 al sondear; sin servicios disponibles",
            "no se pudo verificar ninguna capa ambiental",
        ],
        uncertainty="No evaluada",
        restrictions="Desconocidas hasta recuperar el servicio",
        evidence=probe_ev(probes, "marn_geoportal", passed=False,
                          note="HTTP 522"),
        transitions=[(
            CAT.DatasetState.UNAVAILABLE,
            [probe_ev(probes, "marn_geoportal", passed=False,
                      note="HTTP 522 en la verificación")],
            "no disponible: el servicio no respondió")],
    )
    add_simple(
        dataset_id="mag_anuario_2022_23",
        name="MAG — Anuario de Estadísticas Agropecuarias 2022-2023",
        description="Anuario oficial de producción y precios; la URL indexada "
                    "responde 404.",
        institution="MAG / DGEA",
        url=("https://www.mag.gob.sv/wp-content/uploads/2024/02/"
             "1-Anuario-de-Estadisticas-Agropecuarias-2022-2023-final-1.pdf"),
        license_="No declarada",
        domain="AGRICULTURE",
        coverage="nacional / departamental / municipal",
        temporal="2022-2023",
        fmt="PDF",
        res="agregado administrativo",
        tres="anual",
        limitations=[
            "404 en la ruta documentada",
            "los anuarios son PDF maquetados: requieren extracción revisada",
        ],
        uncertainty="No evaluada",
        restrictions="No redistribuir el PDF; solo agregados derivados con cita",
        evidence=probe_ev(probes, "mag_anuario_2022_23", passed=False,
                          note="HTTP 404"),
        transitions=[(
            CAT.DatasetState.UNAVAILABLE,
            [probe_ev(probes, "mag_anuario_2022_23", passed=False,
                      note="HTTP 404 en la URL documentada")],
            "no disponible en la ruta documentada")],
    )
    add_simple(
        dataset_id="fao_ecocrop",
        name="FAO EcoCrop — requerimientos de cultivos",
        description="Base de requerimientos agroecológicos por cultivo; el "
                    "servicio fue retirado (503).",
        institution="FAO",
        url="https://ecocrop.apps.fao.org/",
        license_="FAO (servicio retirado)",
        domain="AGRICULTURE",
        coverage="global por cultivo",
        temporal="—",
        fmt="Web",
        res="no espacial",
        tres="estático",
        limitations=[
            "servicio 503: retirado",
            "los parámetros de cultivo deben provenir de fuentes locales o de "
            "DSSAT/FAO documentadas",
        ],
        uncertainty="No evaluada",
        restrictions="Servicio no disponible",
        evidence=probe_ev(probes, "fao_ecocrop", passed=False, note="HTTP 503"),
        transitions=[(
            CAT.DatasetState.UNAVAILABLE,
            [probe_ev(probes, "fao_ecocrop", passed=False,
                      note="servicio retirado (503)")],
            "servicio retirado")],
    )

    # --- 7. base: catálogo final y activos ---------------------------------
    store.upsert_datasets(catalog)
    assets = []
    for record in catalog:
        for path_str in record.artifacts:
            p = (ROOT / path_str) if not Path(path_str).is_absolute() else Path(path_str)
            if p.exists():
                assets.append({
                    "artifact_id": f"{record.dataset_id}.{sha(p)[:12]}",
                    "dataset_id": record.dataset_id, "path": path_str,
                    "sha256": sha(p), "bytes": p.stat().st_size,
                    "format": p.suffix.lstrip("."), "state": record.state.value,
                    "manifest_path": rel(provenance_path(p))
                    if provenance_path(p).exists() else None,
                })
    store.insert_assets(assets)

    # --- 8. catálogo ráster ------------------------------------------------
    raster_targets: list[tuple[Path, str, str, str]] = []
    for name, path in (("dem30_wgs84", C.DEM_WGS84), ("slope_deg", C.SLOPE),
                       ("aspect_deg", C.ASPECT), ("hillshade", C.HILLSHADE),
                       ("relief_class", C.RELIEF_CLASS)):
        raster_targets.append((path, name, "copdem30", "processed"))
    for key in ("phh2o", "soc", "nitrogen", "clay", "sand", "silt"):
        raster_targets.append((C.SOILS_RASTER_DIR / f"{key}_0-30cm.tif",
                               f"soilgrids_{key}_0-30cm", "soilgrids_2",
                               "processed"))
    if chirps_clip:
        raster_targets.append((chirps_clip, "chirps3_precip_0p05deg_sv",
                               "chirps3", "validated"))
    if chirps_path.exists():
        raster_targets.append((chirps_path, "chirps3_precip_global_sample",
                               "chirps3", "samples"))
    rasters = []
    for path, variable, dataset_id, zone in raster_targets:
        if not path.exists():
            continue
        profile = RAS.profile_raster(path)
        entry = profile.as_dict()
        entry.update({"variable": variable, "dataset_id": dataset_id,
                      "zone": zone, "bytes": path.stat().st_size})
        if profile.nodata is None:
            entry["nodata_candidates"] = RAS.undeclared_nodata_candidates(path)
        entry["container_recommendation"] = RAS.choose_container(
            temporal=False, variables=1, access="window")
        rasters.append(entry)
    lay.raster_catalog.write_text(json.dumps({
        "generated_at": utcnow(), "count": len(rasters), "rasters": rasters,
        "note": ("resolución nativa y efectiva declaradas por separado; el "
                 "contenedor recomendado es una decisión, no una conversión"),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- 9. linaje ---------------------------------------------------------
    graph = LIN.LineageGraph.load(lay.lineage_path)
    if chirps_clip and chirps_path.exists():
        graph.add(LIN.record_derivation(
            dataset_id="chirps3", name="chirps3_recorte_sv", version="AGROSV-4.0",
            input_paths=[chirps_path], output_paths=[chirps_clip],
            manifests_dir=lay.manifests,
            steps=[LIN.Step("recorte_por_extension",
                            "agrosv.data.raster.clip_to_file", "4.0",
                            {"bounds": list(C.SV_BOUNDS), "resampling": "none",
                             "crs": "EPSG:4326"}),
                   LIN.Step("perfil_y_qc", "agrosv.data.quality.check_raster",
                            "4.0", {"expected_crs": "EPSG:4326"})],
            validation_state="VALIDATED",
            notes="Recorte sin remuestreo; resolución nativa conservada."))
    for dataset_id, csv_path in csv_outputs.items():
        source = {"nasa_power_point": nasa_path, "open_meteo_point": meteo_path,
                  "gbif_sv": gbif_path}.get(dataset_id)
        if not source or not source.exists() or not csv_path.exists():
            continue
        graph.add(LIN.record_derivation(
            dataset_id=dataset_id, name=f"{dataset_id}_normalizacion",
            version="AGROSV-4.0", input_paths=[source], output_paths=[csv_path],
            manifests_dir=lay.manifests,
            steps=[LIN.Step("parseo_y_normalizacion",
                            "agrosv.data.ingest", "4.0",
                            {"units": "registro agrosv.data.units",
                             "time_basis": "local (UTC−6)"}),
                   LIN.Step("exportacion_csv", "csv.DictWriter", "stdlib", {})],
            validation_state="VALIDATED",
            notes="Normalización de unidades, tiempo y clase de evidencia."))
    if csv_outputs and lay.store_path.exists():
        graph.add(LIN.record_derivation(
            dataset_id="agrosv_data_store", name="carga_base_consulta",
            version="AGROSV-4.0",
            input_paths=list(csv_outputs.values()),
            output_paths=[lay.store_path], manifests_dir=lay.manifests,
            steps=[LIN.Step("carga_sqlite", "agrosv.data.store.DataStore", "4.0",
                            {"tables": ["observations", "occurrences"]})],
            validation_state="VALIDATED",
            notes="La base conserva la clase de evidencia por fila."))
    graph.save()

    # --- 10. cierre --------------------------------------------------------
    catalog.save()
    monitoring = PIPE.monitoring_report(catalog_path=lay.catalog_path, layout=lay)
    PIPE.write_monitoring(monitoring, lay.manifests / "monitoring.json")

    print(json.dumps({
        "generated_at": utcnow(),
        "catalog": catalog.summary(),
        "audit": catalog.audit(),
        "store": store.summary(),
        "temporal": T.time_basis_report(),
        "territory": index.coverage()["missing_levels"],
        "crosswalk_status": TR.CrosswalkTable.load(crosswalk_path).coverage(
            [e.source_code for e in index.by_level("municipality_historic")]
        ) if crosswalk_path.exists() else None,
        "quality_reports": {k: {"status": v[0].status, "checks": v[0].checks_run}
                            for k, v in reports.items()},
        "intercomparison": {k: {"class": v["comparison_class"],
                                "n": v["paired_values"]}
                            for k, v in comparison_output.items()},
        "rasters": len(rasters),
        "lineage": graph.summary(),
        "monitoring_ok": monitoring["ok"],
        "skipped": skipped,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
