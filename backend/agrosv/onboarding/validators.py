"""Validadores estrictos para datos externos.

Ningún validador imputa, corrige ni completa valores. Si falta un campo
obligatorio o una unidad no coincide, el archivo se rechaza y se dice por qué.
Los errores se limitan a 200 por respuesta para no devolver archivos completos.

Formatos:

* `station_series` — CSV largo estación-día-variable
* `centa_samples` — CSV largo muestra-variable
* `basins` — GeoJSON FeatureCollection
* `gauging` — CSV largo estación-día-caudal
* `crosswalk` — CSV departamento-municipio-distrito
* `gnss` — CSV punto con altitud ortométrica o elipsoidal + ondulación
"""
from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .. import config as C

MAX_ERRORS = 200

STATION_VARIABLES: dict[str, tuple[str, float | None, float | None]] = {
    "precipitation": ("mm", 0.0, None),
    "temperature_max": ("degC", -10.0, 55.0),
    "temperature_min": ("degC", -10.0, 55.0),
    "temperature_mean": ("degC", -10.0, 55.0),
    "relative_humidity": ("%", 0.0, 100.0),
    "wind_speed": ("m/s", 0.0, 60.0),
    "et0": ("mm", 0.0, None),
}

CENTA_VARIABLES: dict[str, tuple[str, float | None, float | None]] = {
    "ph": ("pH", 2.5, 10.5),
    "organic_matter_pct": ("%", 0.0, 40.0),
    "n_total_pct": ("%", 0.0, 2.0),
    "p_available_mgkg": ("mg/kg", 0.0, 500.0),
    "k_exchangeable_cmolkkg": ("cmol(+)/kg", 0.0, 10.0),
    "ca_exchangeable_cmolkkg": ("cmol(+)/kg", 0.0, 60.0),
    "mg_exchangeable_cmolkkg": ("cmol(+)/kg", 0.0, 30.0),
    "cec_cmolkkg": ("cmol(+)/kg", 0.0, 100.0),
    "clay_pct": ("%", 0.0, 100.0),
    "sand_pct": ("%", 0.0, 100.0),
    "silt_pct": ("%", 0.0, 100.0),
    "ec_ds_m": ("dS/m", 0.0, 30.0),
}

CROSSWALK_EXPECTED = {"departments": 14, "municipalities": 44, "districts": 262}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _report(kind: str, path: str | Path, rows: Iterable[dict[str, Any]],
            errors: list[str], warnings: list[str],
            summary: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = list(rows)
    return {
        "kind": kind,
        "path": str(path),
        "valid": not errors,
        "n_rows": len(rows),
        "error_count": len(errors),
        "errors": errors[:MAX_ERRORS],
        "warning_count": len(warnings),
        "warnings": warnings[:MAX_ERRORS],
        "summary": summary or {},
        "checked_at": _now(),
        "rule": "no se imputa ni se corrige ningún valor",
    }


def _read_csv(path: str | Path, required: Iterable[str]
              ) -> tuple[list[str], list[dict[str, str]], list[str]]:
    target = Path(path)
    if not target.exists():
        return [], [], [f"archivo no encontrado: {target}"]
    if not target.is_file():
        return [], [], [f"no es un archivo: {target}"]
    with target.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = [h.strip() for h in (reader.fieldnames or []) if h]
        missing = [field for field in required if field not in headers]
        if missing:
            return headers, [], [f"faltan columnas obligatorias: {missing}"]
        rows = []
        for raw in reader:
            rows.append({(k or "").strip(): (v.strip() if isinstance(v, str)
                                            else v)
                         for k, v in raw.items() if k is not None})
    return headers, rows, []


def _date(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _coord_ok(lon: float, lat: float) -> bool:
    west, south, east, north = C.SV_BOUNDS
    return west <= lon <= east and south <= lat <= north


# --- estaciones -------------------------------------------------------------
def validate_station_series(path: str | Path) -> dict[str, Any]:
    required = ("station_id", "date", "variable", "value", "unit",
                "latitude", "longitude", "source")
    _, rows, errors = _read_csv(path, required)
    if errors:
        return _report("station_series", path, rows, errors, [])
    warnings: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    stations: set[str] = set()
    variables: dict[str, int] = {}
    dates: list[str] = []
    for index, row in enumerate(rows, start=2):
        station = row["station_id"]
        variable = row["variable"]
        if not station:
            errors.append(f"fila {index}: station_id vacío")
            continue
        if not row["source"]:
            errors.append(f"fila {index}: source vacío")
        if variable not in STATION_VARIABLES:
            errors.append(f"fila {index}: variable no admitida {variable!r}")
            continue
        unit, low, high = STATION_VARIABLES[variable]
        if row["unit"] != unit:
            errors.append(
                f"fila {index}: unidad {row['unit']!r} != {unit!r} para "
                f"{variable}")
        day = _date(row["date"])
        if day is None:
            errors.append(f"fila {index}: fecha inválida {row['date']!r}")
        else:
            dates.append(day.isoformat())
        value = _num(row["value"])
        if value is None:
            errors.append(f"fila {index}: value no numérico")
        else:
            if low is not None and value < low:
                errors.append(f"fila {index}: {variable}={value} < {low}")
            if high is not None and value > high:
                warnings.append(f"fila {index}: {variable}={value} > {high}")
        lon, lat = _num(row["longitude"]), _num(row["latitude"])
        if lon is None or lat is None:
            errors.append(f"fila {index}: coordenada no numérica")
        elif not _coord_ok(lon, lat):
            errors.append(f"fila {index}: coordenada fuera del rectángulo "
                          f"nacional ({lon}, {lat})")
        key = (station, row["date"], variable)
        if key in seen:
            errors.append(f"fila {index}: duplicado {key}")
        seen.add(key)
        stations.add(station)
        variables[variable] = variables.get(variable, 0) + 1
    summary = {
        "stations": len(stations),
        "variables": variables,
        "start": min(dates) if dates else None,
        "end": max(dates) if dates else None,
        "coverage_note": ("el validador no exige continuidad diaria: un "
                          "hueco se conserva como hueco"),
    }
    return _report("station_series", path, rows, errors, warnings, summary)


# --- laboratorio CENTA ------------------------------------------------------
def validate_centa_samples(path: str | Path) -> dict[str, Any]:
    required = ("sample_id", "date", "latitude", "longitude", "depth_cm",
                "variable", "value", "unit", "lab_method", "source")
    _, rows, errors = _read_csv(path, required)
    if errors:
        return _report("centa_samples", path, rows, errors, [])
    warnings: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    samples: set[str] = set()
    variables: dict[str, int] = {}
    labs: set[str] = set()
    for index, row in enumerate(rows, start=2):
        if not row["sample_id"]:
            errors.append(f"fila {index}: sample_id vacío")
            continue
        if not row["lab_method"] or not row["source"]:
            errors.append(f"fila {index}: lab_method o source vacío")
        day = _date(row["date"])
        if day is None:
            errors.append(f"fila {index}: fecha inválida {row['date']!r}")
        lon, lat = _num(row["longitude"]), _num(row["latitude"])
        if lon is None or lat is None:
            errors.append(f"fila {index}: coordenada no numérica")
        elif not _coord_ok(lon, lat):
            errors.append(f"fila {index}: coordenada fuera de El Salvador")
        depth = _num(row["depth_cm"])
        if depth is None or depth < 0 or depth > 300:
            errors.append(f"fila {index}: depth_cm inválido {row['depth_cm']!r}")
        variable = row["variable"]
        if variable not in CENTA_VARIABLES:
            errors.append(f"fila {index}: variable no admitida {variable!r}")
            continue
        unit, low, high = CENTA_VARIABLES[variable]
        if row["unit"] != unit:
            errors.append(f"fila {index}: unidad {row['unit']!r} != {unit!r} "
                          f"para {variable}")
        value = _num(row["value"])
        if value is None:
            errors.append(f"fila {index}: value no numérico")
        else:
            if low is not None and value < low:
                errors.append(f"fila {index}: {variable}={value} < {low}")
            if high is not None and value > high:
                errors.append(f"fila {index}: {variable}={value} > {high}")
        key = (row["sample_id"], variable, str(depth))
        if key in seen:
            errors.append(f"fila {index}: duplicado {key}")
        seen.add(key)
        samples.add(row["sample_id"])
        labs.add(row["source"])
        variables[variable] = variables.get(variable, 0) + 1
    summary = {
        "samples": len(samples),
        "variables": variables,
        "sources": sorted(labs),
        "note": ("profundidad y método son obligatorios; el validador no "
                 "convierte unidades ni compara con SoilGrids"),
    }
    return _report("centa_samples", path, rows, errors, warnings, summary)


# --- cuencas ----------------------------------------------------------------
def validate_basins(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return _report("basins", path, [], [f"archivo no encontrado: {target}"],
                       [])
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _report("basins", path, [], [f"GeoJSON inválido: {exc}"], [])
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        return _report("basins", path, [],
                       ["se requiere un FeatureCollection GeoJSON"], [])
    features = payload.get("features") or []
    if not isinstance(features, list):
        return _report("basins", path, [],
                       ["'features' debe ser una lista"], [])
    errors: list[str] = []
    warnings: list[str] = []
    codes: set[str] = set()
    total_area = 0.0
    try:
        from pyproj import Geod
        from shapely.geometry import shape
        from shapely.validation import explain_validity
    except ImportError:
        return _report("basins", path, features,
                       ["shapely/pyproj no disponibles para validar geometría"],
                       [])
    geod = Geod(ellps="WGS84")
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            errors.append(f"feature {index}: no es un objeto GeoJSON")
            continue
        props = feature.get("properties") or {}
        if not isinstance(props, dict):
            errors.append(f"feature {index}: 'properties' no es un objeto")
            continue
        code = str(props.get("basin_code") or "").strip()
        name = str(props.get("name") or "").strip()
        area = _num(props.get("area_km2"))
        if not code or not name:
            errors.append(f"feature {index}: basin_code o name vacío")
        if not code:
            continue
        if code in codes:
            errors.append(f"feature {index}: basin_code duplicado {code}")
        codes.add(code)
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in {"Polygon",
                                                        "MultiPolygon"}:
            errors.append(f"feature {index}: geometría ausente o no poligonal")
            continue
        try:
            geom = shape(geometry)
        except Exception as exc:  # geometría malformada
            errors.append(f"feature {index}: geometría inválida ({exc})")
            continue
        if not geom.is_valid:
            errors.append(f"feature {index}: geometría inválida: "
                          f"{explain_validity(geom)}")
            continue
        if geom.is_empty:
            errors.append(f"feature {index}: geometría vacía")
            continue
        area_m2, _ = geod.geometry_area_perimeter(geom)
        computed = abs(area_m2) / 1e6
        total_area += computed
        if area is None:
            warnings.append(f"feature {index}: area_km2 ausente; calculada "
                            f"{computed:.1f} km²")
        elif area > 0 and abs(computed - area) / area > 0.10:
            warnings.append(
                f"feature {index}: area declarada {area} km² difiere >10 % de "
                f"la calculada {computed:.1f} km²")
        west, south, east, north = geom.bounds
        if west < -92.5 or east > -86.5 or south < 12.5 or north > 15.0:
            warnings.append(f"feature {index}: extensión fuera del entorno "
                            f"salvadoreño {geom.bounds}")
    summary = {
        "features": len(features),
        "unique_codes": len(codes),
        "total_area_km2": round(total_area, 2),
        "area_method": "geodésica WGS84 sobre la geometría declarada",
    }
    return _report("basins", path, features, errors, warnings, summary)


# --- caudales ---------------------------------------------------------------
def validate_gauging(path: str | Path) -> dict[str, Any]:
    required = ("station_id", "date", "discharge_m3s", "basin_code", "source")
    _, rows, errors = _read_csv(path, required)
    if errors:
        return _report("gauging", path, rows, errors, [])
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()
    stations: set[str] = set()
    basins: set[str] = set()
    dates: list[str] = []
    zero = 0
    for index, row in enumerate(rows, start=2):
        if not row["station_id"] or not row["basin_code"]:
            errors.append(f"fila {index}: station_id o basin_code vacío")
            continue
        if not row["source"]:
            errors.append(f"fila {index}: source vacío")
        day = _date(row["date"])
        if day is None:
            errors.append(f"fila {index}: fecha inválida {row['date']!r}")
        else:
            dates.append(day.isoformat())
        discharge = _num(row["discharge_m3s"])
        if discharge is None:
            errors.append(f"fila {index}: discharge_m3s no numérico")
        elif discharge < 0:
            errors.append(f"fila {index}: caudal negativo {discharge}")
        elif discharge == 0:
            zero += 1
        key = (row["station_id"], row["date"])
        if key in seen:
            errors.append(f"fila {index}: duplicado {key}")
        seen.add(key)
        stations.add(row["station_id"])
        basins.add(row["basin_code"])
    summary = {
        "stations": len(stations),
        "basins": len(basins),
        "start": min(dates) if dates else None,
        "end": max(dates) if dates else None,
        "zero_flow_rows": zero,
        "note": "no se rellena ningún día sin registro",
    }
    return _report("gauging", path, rows, errors, warnings, summary)


# --- correspondencia municipal ---------------------------------------------
def validate_crosswalk(path: str | Path) -> dict[str, Any]:
    required = ("department", "municipality", "district", "legal_instrument",
                "effective_date", "source")
    _, rows, errors = _read_csv(path, required)
    if errors:
        return _report("crosswalk", path, rows, errors, [])
    warnings: list[str] = []
    district_owner: dict[tuple[str, str], str] = {}
    municipality_dept: dict[str, str] = {}
    departments: set[str] = set()
    municipalities: set[str] = set()
    dates: set[str] = set()
    ids: set[str] = set()
    for index, row in enumerate(rows, start=2):
        department = row["department"]
        municipality = row["municipality"]
        district = row["district"]
        if not department or not municipality or not district:
            errors.append(f"fila {index}: departamento, municipio o distrito "
                          "vacío")
            continue
        if not row["legal_instrument"] or not row["source"]:
            errors.append(f"fila {index}: instrumento legal o fuente vacío")
        day = _date(row["effective_date"])
        if day is None:
            errors.append(f"fila {index}: effective_date inválido")
        else:
            dates.add(day.isoformat())
        key = (department, district)
        if key in district_owner:
            errors.append(f"fila {index}: distrito duplicado en el "
                          f"departamento: {district}")
        district_owner[key] = municipality
        previous = municipality_dept.get(municipality)
        if previous and previous != department:
            errors.append(f"fila {index}: municipio {municipality} aparece en "
                          f"{previous} y {department}")
        municipality_dept[municipality] = department
        if row.get("district_id"):
            if row["district_id"] in ids:
                errors.append(f"fila {index}: district_id duplicado")
            ids.add(row["district_id"])
        departments.add(department)
        municipalities.add(municipality)
    counts = {
        "departments": len(departments),
        "municipalities": len(municipalities),
        "districts": len(rows),
    }
    for key, expected in CROSSWALK_EXPECTED.items():
        if counts[key] > expected:
            errors.append(f"{key}={counts[key]} supera el total oficial "
                          f"{expected}")
        elif counts[key] < expected:
            warnings.append(f"{key}={counts[key]} < {expected}: posible "
                            "subconjunto")
    if len(dates) > 1:
        warnings.append(f"varias fechas de vigencia: {sorted(dates)}")
    summary = {**counts, "effective_dates": sorted(dates),
               "legal_instruments": sorted({r["legal_instrument"]
                                            for r in rows}),
               "ids_note": "district_id/municipality_id son AGROSV, no "
                           "códigos oficiales"}
    return _report("crosswalk", path, rows, errors, warnings, summary)


# --- GNSS -------------------------------------------------------------------
def _orthometric(row: dict[str, str]) -> tuple[float | None, str | None]:
    h = _num(row.get("orthometric_height_m"))
    if h is not None:
        return h, "orthometric"
    ellipsoidal = _num(row.get("ellipsoidal_height_m"))
    undulation = _num(row.get("geoid_undulation_m"))
    if ellipsoidal is not None and undulation is not None:
        return ellipsoidal - undulation, "ellipsoidal_minus_geoid"
    return None, None


def validate_gnss(path: str | Path) -> dict[str, Any]:
    required = ("point_id", "latitude", "longitude", "date", "source",
                "horizontal_accuracy_m", "vertical_accuracy_m")
    _, rows, errors = _read_csv(path, required)
    if errors:
        return _report("gnss", path, rows, errors, [])
    warnings: list[str] = []
    seen: set[str] = set()
    methods: dict[str, int] = {}
    vertical_acc: list[float] = []
    for index, row in enumerate(rows, start=2):
        point = row["point_id"]
        if not point:
            errors.append(f"fila {index}: point_id vacío")
            continue
        if point in seen:
            errors.append(f"fila {index}: point_id duplicado {point}")
        seen.add(point)
        if not row["source"]:
            errors.append(f"fila {index}: source vacío")
        day = _date(row["date"])
        if day is None:
            errors.append(f"fila {index}: fecha inválida {row['date']!r}")
        lon, lat = _num(row["longitude"]), _num(row["latitude"])
        if lon is None or lat is None:
            errors.append(f"fila {index}: coordenada no numérica")
        elif not _coord_ok(lon, lat):
            errors.append(f"fila {index}: coordenada fuera de El Salvador")
        height, method = _orthometric(row)
        if height is None:
            errors.append(
                f"fila {index}: falta orthometric_height_m o "
                "(ellipsoidal_height_m + geoid_undulation_m)")
        elif not -100 <= height <= 3000:
            errors.append(f"fila {index}: altura fuera de rango {height}")
        else:
            methods[method or "unknown"] = methods.get(method or "unknown", 0) + 1
        for field in ("horizontal_accuracy_m", "vertical_accuracy_m"):
            value = _num(row.get(field))
            if value is None or value <= 0:
                errors.append(f"fila {index}: {field} inválido")
            elif field == "vertical_accuracy_m":
                vertical_acc.append(value)
    summary = {
        "points": len(seen),
        "height_methods": methods,
        "mean_vertical_accuracy_m": (round(sum(vertical_acc) / len(vertical_acc),
                                           3) if vertical_acc else None),
        "note": ("se exige altura ortométrica o elipsoidal + ondulación; no "
                 "se convierte con un geoide no declarado"),
    }
    return _report("gnss", path, rows, errors, warnings, summary)


VALIDATORS = {
    "station_series": validate_station_series,
    "centa_samples": validate_centa_samples,
    "basins": validate_basins,
    "gauging": validate_gauging,
    "crosswalk": validate_crosswalk,
    "gnss": validate_gnss,
}


def validate(kind: str, path: str | Path) -> dict[str, Any]:
    if kind not in VALIDATORS:
        raise KeyError(f"tipo de archivo desconocido: {kind}; "
                       f"disponibles {sorted(VALIDATORS)}")
    return VALIDATORS[kind](path)


__all__ = ["VALIDATORS", "validate", "validate_station_series",
           "validate_centa_samples", "validate_basins", "validate_gauging",
           "validate_crosswalk", "validate_gnss", "STATION_VARIABLES",
           "CENTA_VARIABLES", "CROSSWALK_EXPECTED"]
