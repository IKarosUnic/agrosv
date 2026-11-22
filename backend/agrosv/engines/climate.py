"""AGROSV — ClimateEngine (Fase 5, §6).

Trabaja con lo que existe: **dos coordenadas de reanálisis** con serie diaria
2019-01-01 a 2025-12-31 (NASA POWER y Open-Meteo). Nada más. En particular:

* No hay estaciones SNET/MARN: no se presenta reanálisis como observación.
* No hay cobertura espacial: **no se interpola** el clima entre puntos ni se
  genera un mapa. Se informa la distancia al punto climático usado.
* No hay 30 años: se publica una *climatología del período disponible*, no una
  normal climatológica de la OMM.
* No hay pronóstico ni proyección: no se sirven.

Indicadores implementados (definiciones declaradas, no «índices» inventados):

    Rx1day, Rx5day, R95p, CDD, CWD, PRCPTOT, SDII   (ETCCDI, días con P ≥ 1 mm)
    rachas secas (P < 1 mm) y húmedas (P ≥ 1 mm)
    meses húmedos Walter–Lieth (P_mes > 2·T_mes)
    anomalías anuales y días extremos por percentiles del período
    indicador de sequía por percentil de precipitación acumulada a 3 meses
      (NO es SPI: el registro es corto y la serie tiene ceros, lo que exige una
      distribución mixta que aquí no se ajusta)

Toda cifra conserva su clase de evidencia: `reanalysis`.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any, Iterable

import numpy as np

from .. import config as C
from . import governance as G

ENGINE = "climate"
ENGINE_VERSION = G.ENGINE_VERSION
DB_PATH = C.DATA / "validated" / "agrosv_data.sqlite"

#: Día húmedo para índices ETCCDI y rachas.
WET_DAY_MM = 1.0

#: Umbrales de categoría del indicador por percentil (declarados, no SPI).
DROUGHT_PERCENTILE_CATEGORIES: tuple[tuple[float, str, str], ...] = (
    (5.0, "extremadamente_seco", "percentil ≤ 5"),
    (10.0, "muy_seco", "percentil 5–10"),
    (20.0, "seco", "percentil 10–20"),
    (80.0, "normal", "percentil 20–80"),
    (90.0, "humedo", "percentil 80–90"),
    (95.0, "muy_humedo", "percentil 90–95"),
    (100.0, "extremadamente_humedo", "percentil > 95"),
)

#: Variables y agregaciones disponibles por dataset, tal como están integradas.
DATASET_VARIABLES: dict[str, dict[str, tuple[str, ...]]] = {
    "nasa_power_point": {
        "precipitation": ("sum",),
        "temperature": ("max", "min"),
    },
    "open_meteo_point": {
        "precipitation": ("sum",),
        "et0": ("sum",),
        "relative_humidity": ("mean",),
        "temperature": ("max", "min"),
    },
}


class ClimateDataError(RuntimeError):
    """No hay serie suficiente para la consulta."""


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise G.SourceUnavailableError(
            "nasa_power_point", [str(DB_PATH)],
            "ejecute scripts/08_build_phase4_integration.py")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@lru_cache(maxsize=1)
def points() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT dataset_id, latitude, longitude, cell_support, "
            "dataset_version, MIN(time_local) AS start, MAX(time_local) AS end, "
            "COUNT(*) AS n FROM observations GROUP BY dataset_id, latitude, longitude"
        ).fetchall()
    return [dict(r) for r in rows]


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_point(lon: float, lat: float, *,
                  dataset_id: str | None = None) -> dict[str, Any]:
    """Punto climático más cercano. Si está lejos, se dice; no se interpola."""
    candidates = points()
    if dataset_id:
        candidates = [p for p in candidates if p["dataset_id"] == dataset_id]
    if not candidates:
        raise ClimateDataError(
            f"no hay puntos climáticos para dataset={dataset_id}")
    best = min(candidates, key=lambda p: haversine_km(lon, lat, p["longitude"],
                                                      p["latitude"]))
    distance = haversine_km(lon, lat, best["longitude"], best["latitude"])
    return {
        "dataset_id": best["dataset_id"],
        "latitude": best["latitude"],
        "longitude": best["longitude"],
        "cell_support": best["cell_support"],
        "dataset_version": best["dataset_version"],
        "period": {"start": best["start"], "end": best["end"]},
        "distance_km": round(distance, 2),
        "representative": distance <= 25.0,
        "distance_note": (
            "el valor es del punto de reanálisis, no del lugar consultado; no "
            "se interpola entre puntos"
            if distance > 0 else "el punto consultado coincide con la celda"),
    }


@lru_cache(maxsize=64)
def _rows(dataset_id: str, variable: str,
          aggregation: str) -> tuple[tuple[str, float], ...]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT time_local, value FROM observations "
            "WHERE dataset_id = ? AND variable = ? AND aggregation = ? "
            "AND value IS NOT NULL AND quality_flag = 'ok' "
            "ORDER BY time_local",
            (dataset_id, variable, aggregation)).fetchall()
    out = []
    for row in rows:
        try:
            day = str(row["time_local"])[:10]
            date.fromisoformat(day)
        except (TypeError, ValueError):
            continue
        value = float(row["value"])
        if not math.isfinite(value):
            continue
        out.append((day, value))
    return tuple(out)


def _aggregation_for(dataset_id: str, variable: str,
                     aggregation: str | None = None) -> str:
    spec = DATASET_VARIABLES.get(dataset_id, {})
    if variable not in spec:
        raise ClimateDataError(
            f"{dataset_id} no tiene '{variable}'; variables disponibles: "
            f"{sorted(spec)}")
    options = spec[variable]
    if aggregation is None:
        if len(options) != 1:
            raise ClimateDataError(
                f"'{variable}' en {dataset_id} tiene varias agregaciones "+
                f"{list(options)}: declare cuál se usa")
        return options[0]
    if aggregation not in options:
        raise ClimateDataError(
            f"agregación '{aggregation}' no declarada para {variable} en "
            f"{dataset_id}; disponibles {list(options)}")
    return aggregation


def _series(dataset_id: str, variable: str,
            aggregation: str | None = None) -> list[tuple[str, float]]:
    return list(_rows(dataset_id, variable,
                      _aggregation_for(dataset_id, variable, aggregation)))


def _aggregate_annual(series: Iterable[tuple[str, float]],
                      method: str) -> dict[int, dict[str, Any]]:
    buckets: dict[int, list[float]] = {}
    for day, value in series:
        year = int(day[:4])
        buckets.setdefault(year, []).append(value)
    out: dict[int, dict[str, Any]] = {}
    for year, values in sorted(buckets.items()):
        expected = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
        coverage = len(values) / expected
        if method == "sum":
            value = float(sum(values))
        elif method == "mean":
            value = float(np.mean(values))
        elif method == "max":
            value = float(max(values))
        elif method == "min":
            value = float(min(values))
        else:
            raise ValueError(f"agregación desconocida: {method}")
        out[year] = {
            "value": round(value, 2),
            "n_days": len(values),
            "coverage": round(coverage, 4),
            "complete": coverage >= 0.9,
            "quality_flag": "ok" if coverage >= 0.9 else "incomplete_period",
        }
    return out


def _monthly(series: Iterable[tuple[str, float]], method: str
             ) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[float]] = {}
    for day, value in series:
        key = day[:7]
        buckets.setdefault(key, []).append(value)
    out = {}
    for key, values in sorted(buckets.items()):
        year, month = int(key[:4]), int(key[5:7])
        expected = 31 if month in (1, 3, 5, 7, 8, 10, 12) else (
            30 if month in (4, 6, 9, 11) else
            (29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28))
        coverage = len(values) / expected
        if method == "sum":
            value = float(sum(values))
        elif method == "mean":
            value = float(np.mean(values))
        elif method == "max":
            value = float(max(values))
        elif method == "min":
            value = float(min(values))
        else:
            raise ValueError(method)
        out[key] = {"value": round(value, 2), "n_days": len(values),
                    "coverage": round(coverage, 4),
                    "complete": coverage >= 0.9}
    return out


def _runs(series: list[tuple[str, float]], *, wet: bool) -> dict[str, Any]:
    best = {"length": 0, "start": None, "end": None}
    current = 0
    start = None
    for day, value in series:
        is_wet = value >= WET_DAY_MM
        condition = is_wet if wet else not is_wet
        if condition:
            current += 1
            start = start or day
            if current > best["length"]:
                best = {"length": current, "start": start, "end": day}
        else:
            current = 0
            start = None
    return best


class ClimateEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def points(self) -> list[dict[str, Any]]:
        return points()

    def nearest_point(self, lon: float, lat: float) -> dict[str, Any]:
        return nearest_point(lon, lat)

    def series(self, dataset_id: str, variable: str,
               aggregation: str | None = None) -> dict[str, Any]:
        data = _series(dataset_id, variable, aggregation)
        spec = _aggregation_for(dataset_id, variable, aggregation)
        return {
            "dataset_id": dataset_id,
            "variable": variable,
            "aggregation": spec,
            "unit": {"precipitation": "mm", "et0": "mm",
                     "relative_humidity": "%"}.get(variable, "degC"),
            "evidence_class": "reanalysis",
            "n": len(data),
            "start": data[0][0] if data else None,
            "end": data[-1][0] if data else None,
            "series": [{"date": d, "value": v} for d, v in data],
            "note": "serie diaria de reanálisis; no es una estación",
        }

    def annual_series(self, dataset_id: str, variable: str,
                      aggregation: str | None = None
                      ) -> dict[int, dict[str, Any]]:
        agg = _aggregation_for(dataset_id, variable, aggregation)
        method = "sum" if agg == "sum" else "mean"
        return _aggregate_annual(_series(dataset_id, variable, agg), method)

    # --- agregaciones -------------------------------------------------------
    def monthly_climatology(self, dataset_id: str, variable: str,
                            aggregation: str | None = None) -> dict[str, Any]:
        method = _aggregation_for(dataset_id, variable, aggregation)
        monthly = _monthly(_series(dataset_id, variable, method),
                           "sum" if method == "sum" else "mean")
        by_month: dict[int, list[float]] = {}
        for key, payload in monthly.items():
            by_month.setdefault(int(key[5:7]), []).append(payload["value"])
        table = []
        for month in range(1, 13):
            values = by_month.get(month, [])
            table.append({
                "month": month,
                "mean": round(float(np.mean(values)), 2) if values else None,
                "min": round(float(np.min(values)), 2) if values else None,
                "max": round(float(np.max(values)), 2) if values else None,
                "n_years": len(values),
            })
        return {
            "dataset_id": dataset_id,
            "variable": variable,
            "aggregation": "sum" if method == "sum" else "mean",
            "unit": "mm" if variable in {"precipitation", "et0"} else
                    ("%" if variable == "relative_humidity" else "degC"),
            "months": table,
            "method": ("media de los totales/prodmedios mensuales del período "
                       "disponible (2019–2025)"),
            "evidence_class": "reanalysis",
            "not_a_normal": (
                "con 7 años no se calcula una normal climatológica de la OMM; "
                "es una climatología del período"),
        }

    def normals(self) -> dict[str, Any]:
        years = sorted(self.annual_series("open_meteo_point", "precipitation"))
        return {
            "status": "insufficient_record",
            "period": {"start": years[0] if years else None,
                       "end": years[-1] if years else None},
            "years": len(years),
            "wmo_requirement_years": 30,
            "published_as": "climatología del período disponible",
            "note": (
                "no se publica una normal de 30 años: exigiría una serie "
                "homogénea de 1991–2020 o 1981–2010 con control de calidad"),
            "evidence_class": "reanalysis",
        }

    def dry_spells(self) -> dict[str, Any]:
        data = _series("open_meteo_point", "precipitation", "sum")
        by_year: dict[int, list[tuple[str, float]]] = {}
        for day, value in data:
            by_year.setdefault(int(day[:4]), []).append((day, value))
        rows = []
        for year, series in sorted(by_year.items()):
            longest = _runs(series, wet=False)
            spells = []
            current = 0
            for _, value in series:
                if value < WET_DAY_MM:
                    current += 1
                elif current:
                    spells.append(current)
                    current = 0
            if current:
                spells.append(current)
            rows.append({
                "year": year,
                "max_consecutive_dry_days": longest["length"],
                "start": longest["start"],
                "end": longest["end"],
                "spells_ge_5d": sum(1 for s in spells if s >= 5),
                "spells_ge_10d": sum(1 for s in spells if s >= 10),
                "spells_ge_15d": sum(1 for s in spells if s >= 15),
                "spells_ge_20d": sum(1 for s in spells if s >= 20),
            })
        return {
            "dataset_id": "open_meteo_point",
            "threshold_mm": WET_DAY_MM,
            "definition": "día seco = precipitación diaria < 1,0 mm",
            "years": rows,
            "series_max_dry_days": max((r["max_consecutive_dry_days"] for r in rows),
                                       default=None),
            "evidence_class": "reanalysis",
            "note": ("una racha seca de reanálisis no es una sequía agrícola: "
                     "no incorpora suelo ni demanda hídrica"),
        }

    def extremes(self) -> dict[str, Any]:
        data = _series("open_meteo_point", "precipitation", "sum")
        values = np.array([v for _, v in data], dtype="float64")
        wet = values[values >= WET_DAY_MM]
        p95 = float(np.percentile(wet, 95)) if wet.size else None
        by_year: dict[int, list[float]] = {}
        dates: dict[int, list[str]] = {}
        for day, value in data:
            by_year.setdefault(int(day[:4]), []).append(value)
            dates.setdefault(int(day[:4]), []).append(day)
        rows = []
        for year, vals in sorted(by_year.items()):
            arr = np.asarray(vals, dtype="float64")
            order = np.argsort(dates[year])
            arr = arr[order]
            rx1 = float(arr.max()) if arr.size else None
            roll5 = (np.convolve(arr, np.ones(5), mode="valid")
                     if arr.size >= 5 else np.array([]))
            rx5 = float(roll5.max()) if roll5.size else None
            r95 = (float(arr[arr > p95].sum()) if p95 is not None else None)
            year_data = list(zip(dates[year], vals))
            cdd = _runs(year_data, wet=False)["length"]
            cwd = _runs(year_data, wet=True)["length"]
            wet_days = arr[arr >= WET_DAY_MM]
            rows.append({
                "year": year,
                "prcptot_mm": round(float(arr.sum()), 1),
                "rx1day_mm": round(rx1, 1) if rx1 is not None else None,
                "rx5day_mm": round(rx5, 1) if rx5 is not None else None,
                "r95p_mm": round(r95, 1) if r95 is not None else None,
                "cdd_days": cdd,
                "cwd_days": cwd,
                "sdii_mm_per_wet_day": (round(float(wet_days.mean()), 2)
                                        if wet_days.size else None),
                "wet_days": int(wet_days.size),
            })
        return {
            "dataset_id": "open_meteo_point",
            "base_period": {"start": data[0][0], "end": data[-1][0]},
            "r95p_threshold_mm": round(p95, 2) if p95 is not None else None,
            "definitions": {
                "prcptot": "suma anual de precipitación diaria",
                "rx1day": "máxima precipitación de 1 día",
                "rx5day": "máxima suma de 5 días consecutivos",
                "r95p": ("suma anual de días con P > percentil 95 de días "
                         "húmedos del período base"),
                "cdd": "máxima racha de días con P < 1 mm",
                "cwd": "máxima racha de días con P ≥ 1 mm",
                "sdii": "precipitación total / días húmedos",
            },
            "reference": "definiciones ETCCDI (Zhang et al., 2011)",
            "years": rows,
            "evidence_class": "reanalysis",
            "note": ("los índices se calculan sobre un producto de reanálisis de "
                     "~9 km: subestiman la intensidad de lluvias convectivas "
                     "locales"),
        }

    def anomalies(self) -> dict[str, Any]:
        tmax = _series("nasa_power_point", "temperature", "max")
        tmin = _series("nasa_power_point", "temperature", "min")
        tmax_map = dict(tmax)
        pairs = [(day, (tmax_map[day] + value) / 2.0)
                 for day, value in tmin if day in tmax_map]
        tmean_daily = np.array([v for _, v in pairs], dtype="float64")
        if tmean_daily.size == 0:
            raise ClimateDataError("sin temperatura máxima y mínima emparejadas")
        p95 = float(np.percentile([v for _, v in tmax], 95))
        p5 = float(np.percentile([v for _, v in tmin], 5))
        period_mean = float(tmean_daily.mean())
        by_year: dict[int, list[tuple[str, float, float, float]]] = {}
        tmin_map = dict(tmin)
        for day, tmax_v in tmax:
            if day not in tmin_map:
                continue
            by_year.setdefault(int(day[:4]), []).append(
                (day, tmax_v, tmin_map[day], (tmax_v + tmin_map[day]) / 2.0))
        rows = []
        for year, entries in sorted(by_year.items()):
            if year == min(by_year) or year == max(by_year):
                complete = len(entries) >= 330
            else:
                complete = len(entries) >= 330
            annual_mean = float(np.mean([e[3] for e in entries]))
            rows.append({
                "year": year,
                "mean_temperature_c": round(annual_mean, 2),
                "anomaly_c": round(annual_mean - period_mean, 2),
                "days_tmax_gt_p95": sum(1 for e in entries if e[1] > p95),
                "days_tmin_lt_p5": sum(1 for e in entries if e[2] < p5),
                "n_days": len(entries),
                "complete": complete,
            })
        return {
            "dataset_id": "nasa_power_point",
            "method": ("temperatura media diaria = (Tmax + Tmin)/2; anomalía "
                       "anual respecto de la media del período 2019–2025; "
                       "extremos por percentiles p95/p5 del período"),
            "period_mean_c": round(period_mean, 2),
            "thresholds": {"tmax_p95_c": round(p95, 2),
                           "tmin_p5_c": round(p5, 2)},
            "years": rows,
            "evidence_class": "reanalysis",
            "note": ("una anomalía térmica de reanálisis no es un evento "
                     "extremo observado; la celda es de ~55 × 69 km"),
        }

    def drought_indicator(self) -> dict[str, Any]:
        monthly = _monthly(
            _series("open_meteo_point", "precipitation", "sum"), "sum")
        keys = sorted(monthly)
        totals = [monthly[k]["value"] for k in keys]
        windows = []
        for i in range(len(totals) - 2):
            windows.append((keys[i + 2], sum(totals[i:i + 3])))
        if not windows:
            raise ClimateDataError("serie mensual insuficiente para 3 meses")
        values = np.array([w[1] for w in windows], dtype="float64")
        latest_key, latest = windows[-1]
        percentile = float((values <= latest).mean() * 100.0)
        category = next(
            (name for limit, name, _ in DROUGHT_PERCENTILE_CATEGORIES
             if percentile <= limit), "normal")
        return {
            "dataset_id": "open_meteo_point",
            "window_months": 3,
            "latest_window_end": latest_key,
            "precipitation_3m_mm": round(latest, 1),
            "percentile": round(percentile, 1),
            "category": category,
            "categories": [{"max_percentile": limit, "category": name,
                            "definition": definition}
                           for limit, name, definition in
                           DROUGHT_PERCENTILE_CATEGORIES],
            "n_windows": len(windows),
            "method": (
                "percentil empírico de la precipitación acumulada a 3 meses "
                "respecto de todas las ventanas del período"),
            "not_spi": (
                "NO es el SPI: el SPI requiere ajustar una distribución "
                "(gamma mixta con ceros) sobre ≥30 años; con 7 años y muchos "
                "ceros de precipitación el ajuste no sería defendible"),
            "evidence_class": "reanalysis",
            "limitations": [
                "un percentil de 7 años es una referencia débil",
                "precipitación baja no equivale a sequía agrícola sin demanda "
                "hídrica y suelo",
            ],
        }

    def seasonality(self) -> dict[str, Any]:
        precip = self.monthly_climatology("open_meteo_point", "precipitation")
        tmax = self.monthly_climatology("nasa_power_point", "temperature", "max")
        tmin = self.monthly_climatology("nasa_power_point", "temperature", "min")
        tmax_by = {m["month"]: m["mean"] for m in tmax["months"]}
        tmin_by = {m["month"]: m["mean"] for m in tmin["months"]}
        rows = []
        for entry in precip["months"]:
            month = entry["month"]
            t_mean = (None if tmax_by.get(month) is None
                      or tmin_by.get(month) is None
                      else round((tmax_by[month] + tmin_by[month]) / 2.0, 2))
            humid = (None if entry["mean"] is None or t_mean is None
                     else entry["mean"] > 2.0 * t_mean)
            rows.append({
                "month": month,
                "precipitation_mm": entry["mean"],
                "temperature_mean_c": t_mean,
                "walter_lieth_humid": humid,
            })
        wet = [r for r in rows if r["precipitation_mm"] is not None]
        total = sum(r["precipitation_mm"] for r in wet) or None
        wettest = max(wet, key=lambda r: r["precipitation_mm"]) if wet else None
        driest = min(wet, key=lambda r: r["precipitation_mm"]) if wet else None
        top3 = sorted((r["precipitation_mm"] for r in wet), reverse=True)[:3]
        return {
            "months": rows,
            "humid_months_walter_lieth": [r["month"] for r in rows
                                          if r["walter_lieth_humid"]],
            "wettest_month": wettest,
            "driest_month": driest,
            "top3_months_share_pct": (round(100.0 * sum(top3) / total, 1)
                                      if total else None),
            "method": ("climatología mensual; mes húmedo según Walter–Lieth "
                       "(P_mes > 2·T_mes, P en mm y T en °C)"),
            "evidence_class": "reanalysis",
            "note": ("la temporada agrícola (primera/postrera) NO se deriva de "
                     "esta tabla: requiere calendarios del MAG/CENTA"),
        }

    # --- perfil -------------------------------------------------------------
    def profile(self, lon: float, lat: float) -> dict[str, Any]:
        point = nearest_point(lon, lat)
        dataset = point["dataset_id"]
        result: dict[str, Any] = {
            "point": point,
            "stations": {
                "available": False,
                "reason": G.UNAVAILABLE["station_observations"]["reason"],
            },
            "period": point["period"],
            "annual_precipitation": self.annual_series(dataset, "precipitation"),
            "annual_et0": self.annual_series("open_meteo_point", "et0"),
            "monthly_precipitation": self.monthly_climatology(
                dataset, "precipitation"),
            "seasonality": self.seasonality(),
            "dry_spells": self.dry_spells(),
            "extremes": self.extremes(),
            "anomalies": self.anomalies(),
            "drought": self.drought_indicator(),
            "normals": self.normals(),
            "forecasts": {
                "available": False,
                "reason": G.UNAVAILABLE["climate_forecast"]["reason"],
            },
            "spatial_interpolation": {
                "applied": False,
                "reason": ("con dos puntos no se interpola clima: un mapa "
                           "interpolado sería una invención con apariencia de dato"),
            },
            "evidence_classes_present": ["reanalysis"],
        }
        return G.envelope(
            ENGINE,
            result=result,
            sources=["nasa_power_point", "open_meteo_point"],
            limitations=[
                "solo dos puntos de reanálisis: no hay cobertura nacional",
                "reanálisis ≠ observación de estación",
                "7 años no son una normal climatológica de la OMM",
                "no hay pronóstico ni proyección climática",
                "el indicador de sequía es por percentiles, no SPI",
                "no se interpola espacialmente el clima",
            ],
            processing=[
                G.step("selección del punto climático más cercano",
                       "nearest_point"),
                G.step("agregaciones diarias/mensuales/anuales",
                       "agrosv.engines.climate"),
                G.step("índices ETCCDI y rachas", "extremes / dry_spells"),
            ],
            query={"lon": lon, "lat": lat},
            coverage=G.coverage_statement()["climate"],
        )


__all__ = [
    "ClimateEngine", "points", "nearest_point", "haversine_km",
    "ClimateDataError", "DATASET_VARIABLES", "WET_DAY_MM",
    "DROUGHT_PERCENTILE_CATEGORIES",
]
