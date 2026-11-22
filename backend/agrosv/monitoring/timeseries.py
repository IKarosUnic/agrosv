"""AGROSV — SatelliteTimeSeriesEngine (Fase 7, §4.4).

Serie temporal de observaciones espectrales con línea base estacional.

Reglas que el motor hace ejecutables:

* una **ausencia** de observación no es un descenso: los huecos se informan y
  nunca se interpolan para «completar» la serie;
* la línea base se calcula con la misma ventana de día del año en **otros
  años**; comparar estaciones distintas sin ajustar estacionalidad se rechaza;
* la anomalía es robusta (mediana/MAD) y exige al menos `min_years` años y
  `min_obs` observaciones; si no, se lanza `InsufficientRecordError`;
* la tendencia lineal es descriptiva: no es un pronóstico ni una atribución.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable

import numpy as np

from . import governance as G

ENGINE = "satellite_time_series"
ENGINE_VERSION = G.ENGINE_VERSION


def _doy(day: date) -> int:
    return day.timetuple().tm_yday


def _doy_distance(a: int, b: int) -> int:
    diff = abs(a - b)
    return min(diff, 365 - diff)


class SatelliteTimeSeriesEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    # --- construcción ------------------------------------------------------
    def build(self, records: Iterable[dict[str, Any]], *,
              value_key: str = "value",
              cloud_key: str = "cloud_cover",
              max_cloud_pct: float = 30.0) -> dict[str, Any]:
        """Ordena, valida y marca observaciones; no rellena huecos."""
        validated = G.require_dates(records, minimum=1)
        observations = []
        excluded: list[dict[str, Any]] = []
        for record in validated:
            day = record["_date"]
            raw_value = record.get(value_key)
            value = G.finite_or_none(raw_value)
            cloud = G.finite_or_none(record.get(cloud_key))
            reason = None
            if value is None:
                reason = "valor_ausente"
            elif record.get("valid") is False:
                reason = "marcada_invalida"
            elif cloud is not None and cloud > max_cloud_pct:
                reason = f"nubosidad_{cloud:g}_supera_{max_cloud_pct:g}"
            if reason:
                excluded.append({"date": day.isoformat(), "reason": reason,
                                 "value": value, "cloud_cover": cloud})
                continue
            observations.append({
                "date": day.isoformat(), "value": value,
                "cloud_cover": cloud,
                "sensor": record.get("sensor"),
                "quality": record.get("quality"),
                "source": record.get("source"),
            })
        values = [o["value"] for o in observations]
        return {
            "observations": observations,
            "n_total": len(validated),
            "n_valid": len(observations),
            "n_excluded": len(excluded),
            "excluded": excluded,
            "period": {
                "start": observations[0]["date"] if observations else None,
                "end": observations[-1]["date"] if observations else None,
            },
            "statistics": G.result(
                engine=ENGINE, evidence_class="satellite_derived",
                method="estadística descriptiva de la serie válida",
                value={
                    "n": len(values),
                    "mean": float(np.mean(values)) if values else None,
                    "sd": float(np.std(values, ddof=1)) if len(values) > 1 else None,
                    "min": float(np.min(values)) if values else None,
                    "max": float(np.max(values)) if values else None,
                },
                limitations=[
                    "no interpola observaciones ausentes",
                    "las fechas de compuesto no son observaciones instantáneas",
                ])["value"],
            "note": "una observación ausente no se interpreta como deterioro",
        }

    # --- huecos ------------------------------------------------------------
    def gaps(self, observations: list[dict[str, Any]], *,
             expected_interval_days: int = 10) -> dict[str, Any]:
        """Intervalos mayores que 1,5× el intervalo esperado."""
        if expected_interval_days <= 0:
            raise G.MonitoringError("expected_interval_days debe ser > 0")
        dated = G.require_dates(observations, minimum=2)
        limit = 1.5 * expected_interval_days
        missing = []
        for prev, nxt in zip(dated, dated[1:]):
            delta = (nxt["_date"] - prev["_date"]).days
            if delta > limit:
                missing.append({
                    "after": prev["_date"].isoformat(),
                    "before": nxt["_date"].isoformat(),
                    "days": delta,
                    "estimated_missing_observations":
                        max(0, int(round(delta / expected_interval_days)) - 1),
                })
        return {
            "expected_interval_days": expected_interval_days,
            "gap_count": len(missing),
            "gaps": missing,
            "interpolated": False,
            "note": ("los huecos no se rellenan y no son evidencia de cambio; "
                     "una nube persistente puede ocultar una parcela sana"),
        }

    # --- estadística móvil -------------------------------------------------
    def rolling(self, observations: list[dict[str, Any]], *,
                window: int = 3, min_periods: int | None = None) -> dict[str, Any]:
        if window < 2:
            raise G.MonitoringError("window debe ser ≥ 2")
        dated = G.require_dates(observations, minimum=window)
        minimum = min_periods if min_periods is not None else max(2, window // 2)
        out = []
        for i in range(len(dated)):
            chunk = dated[max(0, i - window + 1): i + 1]
            values = [float(r["value"]) for r in chunk
                      if G.is_number(r.get("value"))]
            out.append({
                "date": dated[i]["_date"].isoformat(),
                "window_n": len(values),
                "mean": round(float(np.mean(values)), 6) if len(values) >= minimum
                else None,
                "min": float(np.min(values)) if len(values) >= minimum else None,
                "max": float(np.max(values)) if len(values) >= minimum else None,
            })
        return {"window": window, "min_periods": minimum, "series": out}

    # --- línea base estacional --------------------------------------------
    def seasonal_baseline(self, observations: list[dict[str, Any]], *,
                          target_date: str, window_days: int = 15,
                          min_years: int = 3, min_obs: int = 6,
                          exclude_target_year: bool = True) -> dict[str, Any]:
        target = G.require_dates([{"date": target_date}], minimum=1)[0]["_date"]
        if window_days < 1:
            raise G.MonitoringError("window_days debe ser ≥ 1")
        dated = G.require_dates(observations, minimum=1)
        target_doy = _doy(target)
        values: list[float] = []
        years: set[int] = set()
        for record in dated:
            day = record["_date"]
            if exclude_target_year and day.year == target.year:
                continue
            value = G.finite_or_none(record.get("value"))
            if value is None:
                continue
            if _doy_distance(_doy(day), target_doy) <= window_days:
                values.append(value)
                years.add(day.year)
        if len(years) < min_years:
            raise G.InsufficientRecordError(
                f"línea base insuficiente: {len(years)} años en la ventana "
                f"{target_doy}±{window_days} d; se exigen {min_years}")
        if len(values) < min_obs:
            raise G.InsufficientRecordError(
                f"línea base insuficiente: {len(values)} observaciones; "
                f"se exigen {min_obs}")
        arr = np.asarray(values, dtype=float)
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med))) * 1.4826
        return {
            "target_date": target.isoformat(),
            "window_days": window_days,
            "years": sorted(years),
            "n_years": len(years),
            "n_observations": int(arr.size),
            "median": med,
            "mad": mad,
            "p10": float(np.quantile(arr, 0.10)),
            "p90": float(np.quantile(arr, 0.90)),
            "values": [float(v) for v in arr],
            "method": "ventana de día del año en años distintos",
            "limitations": [
                "la serie no está corregida por deriva del sensor",
                "ventanas de 15 días pueden mezclar etapas fenológicas",
            ],
        }

    def anomaly(self, observations: list[dict[str, Any]], *,
                target_date: str, window_days: int = 15,
                min_years: int = 3, min_obs: int = 6) -> dict[str, Any]:
        """Anomalía robusta de la observación de `target_date`."""
        target = G.require_dates([{"date": target_date}], minimum=1)[0]["_date"]
        dated = G.require_dates(observations, minimum=1)
        match = [r for r in dated if r["_date"] == target]
        if not match:
            raise G.InsufficientRecordError(
                f"no hay observación en {target_date}")
        value = G.finite_or_none(match[0].get("value"))
        if value is None:
            raise G.InsufficientRecordError(
                f"la observación de {target_date} no tiene valor")
        baseline = self.seasonal_baseline(
            observations, target_date=target_date, window_days=window_days,
            min_years=min_years, min_obs=min_obs)
        if baseline["mad"] == 0:
            z = None
            note = "MAD = 0: la anomalía no es interpretable"
        else:
            z = (float(value) - baseline["median"]) / baseline["mad"]
            note = ""
        return {
            "date": target.isoformat(), "value": value,
            "baseline_median": baseline["median"], "baseline_mad": baseline["mad"],
            "baseline_years": baseline["n_years"],
            "baseline_observations": baseline["n_observations"],
            "robust_z": None if z is None else round(float(z), 4),
            "direction": ("below_baseline" if z is not None and z < 0
                          else "above_baseline" if z is not None and z > 0
                          else None),
            "note": note,
            "method": "z robusto (mediana/MAD), ventana estacional declarada",
            "limitations": ["no establece causa", "no sustituye observación de campo"],
        }

    # --- tendencia ---------------------------------------------------------
    def trajectory(self, observations: list[dict[str, Any]], *,
                   min_obs: int = 5) -> dict[str, Any]:
        dated = [r for r in G.require_dates(observations, minimum=min_obs)
                 if G.is_number(r.get("value"))]
        if len(dated) < min_obs:
            raise G.InsufficientRecordError(
                f"tendencia requiere ≥ {min_obs} observaciones con valor")
        x = np.asarray([r["_date"].toordinal() for r in dated], dtype=float)
        y = np.asarray([float(r["value"]) for r in dated], dtype=float)
        x0 = x - x[0]
        slope, intercept = np.polyfit(x0, y, 1)
        fitted = slope * x0 + intercept
        ss_res = float(((y - fitted) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
        return {
            "n": int(len(y)),
            "slope_per_day": round(float(slope), 8),
            "slope_per_30_days": round(float(slope) * 30.0, 6),
            "intercept": round(float(intercept), 6),
            "r2": None if r2 is None else round(r2, 4),
            "period": {"start": dated[0]["_date"].isoformat(),
                       "end": dated[-1]["_date"].isoformat()},
            "method": "mínimos cuadrados ordinarios sobre la serie válida",
            "interpretation": ("tendencia descriptiva del periodo; no es "
                               "pronóstico ni atribución causal"),
            "limitations": [
                "la estacionalidad no se elimina: use anomalías estacionales",
                "n pequeño produce pendientes inestables",
            ],
        }

    # --- comparación -------------------------------------------------------
    def compare(self, first: list[dict[str, Any]], second: list[dict[str, Any]],
                *, label_first: str = "A", label_second: str = "B") -> dict[str, Any]:
        def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
            values = [float(r["value"]) for r in records
                      if G.is_number(r.get("value"))]
            if not values:
                raise G.InsufficientRecordError("conjunto sin valores")
            return {"n": len(values), "median": float(np.median(values)),
                    "mean": float(np.mean(values)), "sd":
                    float(np.std(values, ddof=1)) if len(values) > 1 else None}

        a, b = _summary(first), _summary(second)
        return {
            label_first: a, label_second: b,
            "median_difference": round(b["median"] - a["median"], 6),
            "note": ("comparación descriptiva; sin ajuste estacional ni "
                     "corrección por sensor no admite atribución"),
            "limitations": ["no es una prueba de significancia"],
        }
