"""AGROSV — normalización temporal (Fase 4, §8).

Un instante, un período y un pronóstico no son la misma cosa. Este módulo fija:

* **Base temporal explícita**: `UTC` o `local`. El Salvador usa UTC−6 todo el
  año (no aplica horario de verano); aun así, la base se declara por serie y no
  se deduce del archivo. NASA POWER entrega sus días en hora solar local (`LST`)
  y Open-Meteo en `America/El_Salvador`; tratarlos como UTC desplaza la serie
  seis horas, que en precipitación diaria es un error de un día.
* **Clase de evidencia**: observación, reanálisis, pronóstico, proyección
  climática, simulación. `assert_comparable` impide mezclarlas en una misma
  serie sin declararlo.
* **Frecuencia y agregación**: una suma mensual calculada con 12 de 31 días es
  un mínimo, no un total; se devuelve con cobertura declarada.
* **Año hidrológico y temporada agrícola**: convenciones configurables. La
  temporada por defecto es una referencia regional marcada como *pendiente de
  confirmación oficial*, no una norma del MAG.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable, Sequence

try:  # En Windows sin tzdata, ZoneInfo puede no encontrar la zona.
    from zoneinfo import ZoneInfo

    LOCAL_TZ = ZoneInfo("America/El_Salvador")
    LOCAL_TZ_SOURCE = "IANA America/El_Salvador (zoneinfo)"
except Exception:  # noqa: BLE001
    LOCAL_TZ = timezone(timedelta(hours=-6), name="UTC-06")
    LOCAL_TZ_SOURCE = "offset fijo UTC-06 (tzdata no disponible en este equipo)"

LOCAL_UTC_OFFSET_HOURS = -6


class TemporalError(ValueError):
    pass


class MixedEvidenceError(TemporalError):
    """Se intentaron combinar clases de evidencia incompatibles."""


class EvidenceClass(str, Enum):
    OBSERVATION = "observation"          # medido o registrado
    REANALYSIS = "reanalysis"            # modelo asimilado con observaciones
    FORECAST = "forecast"                # pronóstico con horizonte
    CLIMATE_PROJECTION = "climate_projection"
    SIMULATION = "simulation"            # modelo de proceso bajo supuestos
    AGGREGATE = "aggregate"              # estadística derivada (censo, anuario)


NON_OBSERVATIONAL = frozenset({EvidenceClass.FORECAST,
                               EvidenceClass.CLIMATE_PROJECTION,
                               EvidenceClass.SIMULATION})


class Frequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    DEKADAL = "dekadal"
    PENTADAL = "pentadal"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class Aggregation(str, Enum):
    INSTANT = "instant"
    SUM = "sum"
    MEAN = "mean"
    MAX = "max"
    MIN = "min"
    ACCUMULATION = "accumulation"


@dataclass(frozen=True)
class TimeSeriesSpec:
    """Contrato temporal de una serie. Sin esto, una serie no se normaliza."""

    variable: str
    unit: str
    evidence_class: EvidenceClass
    frequency: Frequency
    time_basis: str  # "UTC" | "local"
    aggregation: Aggregation
    dataset_id: str
    source_id: str
    period_start: str | None = None
    period_end: str | None = None
    temporal_resolution: str | None = None
    uncertainty_note: str = ""

    def __post_init__(self) -> None:
        if self.time_basis not in {"UTC", "local"}:
            raise TemporalError("time_basis debe ser 'UTC' o 'local'")
        if self.evidence_class in NON_OBSERVATIONAL and not self.uncertainty_note:
            raise TemporalError(
                f"{self.evidence_class.value} exige declarar incertidumbre: no es "
                "una observación y no puede presentarse como tal"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "unit": self.unit,
            "evidence_class": self.evidence_class.value,
            "frequency": self.frequency.value,
            "time_basis": self.time_basis,
            "aggregation": self.aggregation.value,
            "dataset_id": self.dataset_id,
            "source_id": self.source_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "temporal_resolution": self.temporal_resolution,
            "uncertainty_note": self.uncertainty_note,
        }


# --- conversión de base temporal --------------------------------------------
def parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = str(value).strip()
    if len(text) == 4 and text.isdigit():  # año (p. ej. World Bank)
        return datetime(int(text), 1, 1)
    if len(text) == 7 and text[4] == "-":  # YYYY-MM
        return datetime.strptime(text, "%Y-%m")
    if len(text) == 8 and text.isdigit():  # NASA POWER: YYYYMMDD
        return datetime.strptime(text, "%Y%m%d")
    if len(text) == 10:
        return datetime.strptime(text, "%Y-%m-%d")
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def to_utc(moment: Any, *, time_basis: str = "local") -> datetime:
    """Lee una marca como base declarada y la devuelve en UTC.

    Una marca sin zona se interpreta en la base declarada. Una marca con zona
    se respeta: no se reetiqueta.
    """
    dt = parse_time(moment)
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    if time_basis == "UTC":
        return dt.replace(tzinfo=timezone.utc)
    return dt.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)


def to_local(moment: Any, *, time_basis: str = "UTC") -> datetime:
    dt = parse_time(moment)
    if dt.tzinfo is None:
        dt = (dt.replace(tzinfo=timezone.utc) if time_basis == "UTC"
              else dt.replace(tzinfo=LOCAL_TZ))
    return dt.astimezone(LOCAL_TZ)


def time_basis_report() -> dict[str, Any]:
    return {
        "local_timezone": str(LOCAL_TZ),
        "local_timezone_source": LOCAL_TZ_SOURCE,
        "utc_offset_hours": LOCAL_UTC_OFFSET_HOURS,
        "dst": False,
        "note": ("El Salvador no aplica horario de verano; la base de cada serie "
                 "se declara y no se deduce del archivo"),
    }


# --- etiquetas de período ----------------------------------------------------
def period_label(moment: Any, frequency: Frequency) -> str:
    dt = parse_time(moment)
    if frequency is Frequency.ANNUAL:
        return f"{dt.year}"
    if frequency is Frequency.MONTHLY:
        return f"{dt.year}-{dt.month:02d}"
    if frequency is Frequency.DEKADAL:
        dekad = 1 if dt.day <= 10 else 2 if dt.day <= 20 else 3
        return f"{dt.year}-{dt.month:02d}-D{dekad}"
    if frequency is Frequency.PENTADAL:
        pentad = min(73, (dt.timetuple().tm_yday - 1) // 5 + 1)
        return f"{dt.year}-P{pentad:02d}"
    if frequency is Frequency.WEEKLY:
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if frequency is Frequency.HOURLY:
        return dt.strftime("%Y-%m-%dT%H:00")
    return dt.strftime("%Y-%m-%d")


def _expected_periods(start: date, end: date, frequency: Frequency) -> list[str]:
    out: list[str] = []
    if frequency is Frequency.DAILY:
        cur = start
        while cur <= end:
            out.append(cur.isoformat())
            cur += timedelta(days=1)
    elif frequency is Frequency.WEEKLY:
        cur = start
        while cur <= end:
            out.append(period_label(cur, frequency))
            cur += timedelta(days=7)
    elif frequency is Frequency.MONTHLY:
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            out.append(f"{y}-{m:02d}")
            m += 1
            if m == 13:
                y, m = y + 1, 1
    elif frequency is Frequency.ANNUAL:
        out = [str(y) for y in range(start.year, end.year + 1)]
    elif frequency is Frequency.HOURLY:
        cur = datetime.combine(start, datetime.min.time())
        stop = datetime.combine(end, datetime.max.time())
        while cur <= stop:
            out.append(cur.strftime("%Y-%m-%dT%H:00"))
            cur += timedelta(hours=1)
    elif frequency in {Frequency.DEKADAL, Frequency.PENTADAL}:
        # Frecuencia intra-mensual: se validan huecos por periodo etiquetado.
        cur = start
        while cur <= end:
            out.append(period_label(cur, frequency))
            cur += timedelta(days=10 if frequency is Frequency.DEKADAL else 5)
    return out


@dataclass
class TemporalReport:
    n: int
    frequency: str
    period: dict[str, Any]
    findings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f["severity"] == "error" for f in self.findings)

    def as_dict(self) -> dict[str, Any]:
        return {"n": self.n, "frequency": self.frequency, "period": self.period,
                "ok": self.ok, "findings": self.findings,
                "note": "hueco ≠ cero: los períodos faltantes se enumeran, no "
                        "se rellenan"}


FILL_SENTINELS = (-999.0, -9999.0, -99999.0, 32767.0, 9999.0)


def validate_series(times: Sequence[Any], values: Sequence[Any],
                    spec: TimeSeriesSpec) -> TemporalReport:
    """Valida fechas, duplicados, orden, frecuencia, huecos y centinelas."""
    if len(times) != len(values):
        raise TemporalError(
            f"longitud distinta: {len(times)} fechas vs {len(values)} valores")
    findings: list[dict[str, Any]] = []

    parsed: list[datetime] = []
    invalid: list[Any] = []
    for t in times:
        try:
            parsed.append(parse_time(t))
        except Exception:  # noqa: BLE001
            parsed.append(datetime.min)
            invalid.append(t)
    if invalid:
        findings.append({"code": "fechas_invalidas", "severity": "error",
                         "count": len(invalid), "examples": invalid[:5],
                         "detail": "fechas no interpretables"})

    valid_dt = [t for t in parsed if t is not datetime.min]
    labels = [period_label(t, spec.frequency) for t in valid_dt]
    dupes = sorted({lab for lab in labels if labels.count(lab) > 1})
    if dupes:
        findings.append({"code": "periodos_duplicados", "severity": "error",
                         "count": len(dupes), "examples": dupes[:5],
                         "detail": "más de un registro para el mismo período"})
    if valid_dt != sorted(valid_dt):
        findings.append({"code": "orden_temporal", "severity": "warning",
                         "detail": "la serie no está ordenada cronológicamente"})

    missing_values = sum(1 for v in values if v is None
                         or (isinstance(v, float) and v != v))
    sentinels = sum(1 for v in values if isinstance(v, (int, float))
                    and v in FILL_SENTINELS)
    if sentinels:
        findings.append({
            "code": "centinela_como_dato", "severity": "error", "count": sentinels,
            "detail": ("valores -999/-9999/32767 presentes: son centinelas de "
                       "falta, no mediciones; hay que enmascararlos"),
        })
    if missing_values:
        findings.append({
            "code": "datos_faltantes", "severity": "warning",
            "count": missing_values,
            "detail": "vacíos explícitos; se conservan como ausencia, no como 0",
        })

    expected: list[str] = []
    if valid_dt:
        start = min(valid_dt).date()
        end = max(valid_dt).date()
        expected = _expected_periods(start, end, spec.frequency)
    present = set(labels)
    gaps = [p for p in expected if p not in present]
    if gaps:
        findings.append({
            "code": "periodos_faltantes", "severity": "warning",
            "count": len(gaps), "examples": gaps[:10],
            "detail": (f"{len(gaps)} de {len(expected)} períodos esperados "
                       f"({spec.frequency.value}) sin registro"),
        })

    observed_freq = _infer_frequency(labels, spec.frequency)
    if observed_freq != spec.frequency.value:
        findings.append({
            "code": "frecuencia_inconsistente", "severity": "error",
            "declared": spec.frequency.value, "observed": observed_freq,
            "detail": "la separación real entre registros no coincide con la "
                      "frecuencia declarada",
        })

    if spec.evidence_class in NON_OBSERVATIONAL:
        findings.append({
            "code": "clase_no_observacional", "severity": "info",
            "evidence_class": spec.evidence_class.value,
            "detail": "la serie no es una observación y no debe compararse como "
                      "medición de campo",
        })

    period = {
        "start": min(valid_dt).isoformat() if valid_dt else None,
        "end": max(valid_dt).isoformat() if valid_dt else None,
        "n_periods": len(labels),
        "expected_periods": len(expected),
        "coverage": round(len(present) / len(expected), 4) if expected else None,
        "time_basis": spec.time_basis,
    }
    return TemporalReport(n=len(times), frequency=spec.frequency.value,
                          period=period, findings=findings)


def _infer_frequency(labels: list[str], declared: Frequency) -> str:
    if len(labels) < 3:
        return declared.value
    try:
        dates = sorted({parse_time(lab) for lab in labels})
    except Exception:  # noqa: BLE001 — etiquetas no parseables: no se infiere
        return declared.value
    if len(dates) < 3:
        return declared.value
    deltas = [(b - a).total_seconds() for a, b in zip(dates, dates[1:])]
    deltas = [d for d in deltas if d > 0]
    if not deltas:
        return declared.value
    median = sorted(deltas)[len(deltas) // 2]
    for freq, seconds in ((Frequency.HOURLY, 3600), (Frequency.DAILY, 86400),
                          (Frequency.WEEKLY, 7 * 86400)):
        if abs(median - seconds) <= seconds * 0.25:
            return freq.value
    if 26 <= median / 86400 <= 32:
        return Frequency.MONTHLY.value
    if 300 <= median / 86400 <= 400:
        return Frequency.ANNUAL.value
    return declared.value


def assert_comparable(classes: Iterable[EvidenceClass]) -> None:
    """Impide mezclar observación y pronóstico/proyección en una sola serie."""
    kinds = {c if isinstance(c, EvidenceClass) else EvidenceClass(c) for c in classes}
    non_obs = kinds & NON_OBSERVATIONAL
    if EvidenceClass.OBSERVATION in kinds and non_obs:
        raise MixedEvidenceError(
            "no se combinan observaciones con "
            f"{sorted(k.value for k in non_obs)}: son clases de evidencia distintas"
        )
    if len(non_obs) > 1:
        raise MixedEvidenceError(
            f"no se combinan {sorted(k.value for k in non_obs)} en una serie: "
            "pronóstico, proyección y simulación no son intercambiables"
        )


def aggregate_periods(times: Sequence[Any], values: Sequence[Any],
                      *, spec: TimeSeriesSpec,
                      target: Frequency = Frequency.MONTHLY,
                      min_coverage: float = 0.9) -> dict[str, list[dict[str, Any]]]:
    """Agrega con cobertura declarada; no publica un total incompleto como total."""
    if target not in {Frequency.MONTHLY, Frequency.ANNUAL}:
        raise TemporalError("agregación soportada: mensual y anual")
    buckets: dict[str, list[float]] = {}
    for t, v in zip(times, values):
        if v is None or (isinstance(v, float) and v != v):
            continue
        key = period_label(t, target)
        buckets.setdefault(key, []).append(float(v))
    expected_per = {Frequency.MONTHLY: 30.4, Frequency.ANNUAL: 365.25}[target]
    freq_expected = {Frequency.DAILY: 1.0, Frequency.HOURLY: 1 / 24}.get(
        spec.frequency, None)
    out = []
    for key in sorted(buckets):
        vals = buckets[key]
        n_expected = (expected_per / freq_expected
                      if freq_expected else None)
        coverage = (len(vals) / n_expected) if n_expected else None
        if spec.aggregation is Aggregation.SUM:
            value = sum(vals)
        elif spec.aggregation is Aggregation.MEAN:
            value = sum(vals) / len(vals)
        elif spec.aggregation is Aggregation.MAX:
            value = max(vals)
        elif spec.aggregation is Aggregation.MIN:
            value = min(vals)
        else:
            raise TemporalError(
                f"no se agrega una serie de tipo {spec.aggregation.value}")
        complete = coverage is None or coverage >= min_coverage
        out.append({
            "period": key,
            "value": value,
            "n": len(vals),
            "coverage": round(coverage, 4) if coverage is not None else None,
            "complete": bool(complete),
            "quality_flag": "ok" if complete else "incomplete_period",
        })
    return {"aggregation": target.value, "method": spec.aggregation.value,
            "min_coverage": min_coverage, "periods": out}


# --- calendarios -------------------------------------------------------------
def hydrological_year(moment: Any, *, start_month: int = 5) -> str:
    """Etiqueta de año hidrológico (por defecto mayo–abril, convención regional).

    El inicio es configurable y **debe declararse**: no es una norma nacional
    verificada en este repositorio.
    """
    if not 1 <= start_month <= 12:
        raise ValueError("start_month debe estar entre 1 y 12")
    dt = parse_time(moment)
    start_year = dt.year if dt.month >= start_month else dt.year - 1
    end_year = start_year + 1
    return f"HY{start_year}/{end_year}"


@dataclass(frozen=True)
class Season:
    season_id: str
    name: str
    start_month: int
    end_month: int
    note: str = ""

    def contains(self, moment: Any) -> bool:
        month = parse_time(moment).month
        if self.start_month <= self.end_month:
            return self.start_month <= month <= self.end_month
        return month >= self.start_month or month <= self.end_month


#: Referencia regional, NO norma oficial de El Salvador. Se exige confirmación
#: con los calendarios del MAG/CENTA por cultivo y zona antes de usarla para
#: decisiones. Se mantiene aquí para que el desacuerdo sea visible y no quede
#: enterrado en cada módulo.
REGIONAL_SEASON_REFERENCE: tuple[Season, ...] = (
    Season("primera", "Primera", 5, 8,
           "referencia agronómica regional; pendiente de confirmación oficial"),
    Season("postrera", "Postrera", 9, 11,
           "referencia agronómica regional; pendiente de confirmación oficial"),
    Season("apante", "Apante", 12, 2,
           "usada en algunas zonas; NO es un ciclo nacional uniforme"),
)


def season_of(moment: Any, seasons: Sequence[Season] = REGIONAL_SEASON_REFERENCE
              ) -> list[str]:
    """Temporadas que contienen la fecha. Puede ser más de una en transición."""
    return [s.season_id for s in seasons if s.contains(moment)]


def season_calendar_report(
    seasons: Sequence[Season] = REGIONAL_SEASON_REFERENCE
) -> dict[str, Any]:
    return {
        "seasons": [{"season_id": s.season_id, "name": s.name,
                     "start_month": s.start_month, "end_month": s.end_month,
                     "note": s.note} for s in seasons],
        "status": "REFERENCE_ONLY",
        "limitation": ("no es un calendario oficial verificado: debe sustituirse "
                       "por los calendarios del MAG/CENTA por cultivo y zona"),
        "hydrological_year_default_start_month": 5,
        "hydrological_year_status": ("convención regional configurable; "
                                     "pendiente de confirmación con SNET/MARN"),
    }
