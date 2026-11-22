"""AGROSV — estructuras normalizadas por dominio (Fase 4, §12).

Esta fase **no implementa los modelos científicos** de territorio, suelos,
hidrología, clima, agricultura, economía, fitosanidad y biodiversidad. Prepara y
valida sus estructuras: claves naturales, tipos, unidades, niveles territoriales
y clases de evidencia, para que un motor futuro no vuelva a resolver formatos,
coordenadas ni unidades.

Cada campo declara su unidad mediante una variable del registro
`agrosv.data.units`, de modo que la validación de unidades es la misma en todo
el sistema. `validate_record` comprueba tipos, unidades, enumeraciones y rangos;
`validate_records` añade unicidad de la clave natural y duplicados.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from . import units as U

DTYPES = {"str", "float", "int", "date", "datetime", "bool"}


@dataclass(frozen=True)
class FieldSpec:
    name: str
    dtype: str
    required: bool
    description: str
    unit_variable: str | None = None
    enumerated: tuple[str, ...] | None = None
    latitude: bool = False
    longitude: bool = False

    def __post_init__(self) -> None:
        if self.dtype not in DTYPES:
            raise ValueError(f"{self.name}: dtype desconocido {self.dtype}")
        if self.latitude and self.longitude:
            raise ValueError(f"{self.name}: no puede ser latitud y longitud")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "required": self.required,
            "unit_variable": self.unit_variable,
            "canonical_unit": (U.spec(self.unit_variable).canonical_unit
                               if self.unit_variable and U.spec(self.unit_variable)
                               else None),
            "enumerated": list(self.enumerated) if self.enumerated else None,
            "description": self.description,
        }


@dataclass(frozen=True)
class DomainSpec:
    code: str
    domain: str
    name: str
    description: str
    natural_key: tuple[str, ...]
    fields: tuple[FieldSpec, ...]
    temporal: str
    territory_levels: tuple[str, ...]
    evidence_default: str
    prepared: str
    not_implemented: str
    notes: tuple[str, ...] = ()

    def field(self, name: str) -> FieldSpec:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "domain": self.domain,
            "name": self.name,
            "description": self.description,
            "natural_key": list(self.natural_key),
            "temporal": self.temporal,
            "territory_levels": list(self.territory_levels),
            "evidence_default": self.evidence_default,
            "prepared": self.prepared,
            "not_implemented": self.not_implemented,
            "fields": [f.as_dict() for f in self.fields],
            "notes": list(self.notes),
        }


_EVIDENCE = ("observation", "reanalysis", "forecast", "climate_projection",
             "simulation", "aggregate")

_TERRITORY = DomainSpec(
    code="A", domain="TERRITORY", name="Territorio",
    description="Límites, topografía, elevación, pendiente, geomorfología y "
                "cobertura terrestre.",
    natural_key=("territory_id",),
    temporal="static",
    territory_levels=("country", "department", "municipality_2023",
                      "municipality_historic", "district", "basin", "subbasin",
                      "microbasin", "protected_area"),
    evidence_default="derived",
    prepared=("ADM0/ADM1 verificados; elevación, pendiente, aspecto y clases de "
              "relieve derivadas del Copernicus DEM 30 m"),
    not_implemented="límites municipales 2023, distritos, cuencas y geomorfología "
                    "detallada (sin capa verificada)",
    fields=(
        FieldSpec("territory_id", "str", True,
                  "identificador estable; nunca el nombre"),
        FieldSpec("level", "str", True, "nivel territorial",
                  enumerated=("country", "department", "municipality_2023",
                              "municipality_historic", "district", "basin",
                              "subbasin", "microbasin", "protected_area",
                              "agricultural_unit", "parcel")),
        FieldSpec("name", "str", True, "nombre canónico del límite"),
        FieldSpec("parent_id", "str", False, "territorio padre"),
        FieldSpec("area_km2", "float", False, "superficie calculada en EPSG:6933",
                  unit_variable="area"),
        FieldSpec("elevation_mean_m", "float", False, "elevación media",
                  unit_variable="elevation"),
        FieldSpec("slope_mean_deg", "float", False, "pendiente media",
                  unit_variable="slope"),
        FieldSpec("land_cover_class", "int", False, "clase de cobertura dominante",
                  unit_variable="land_cover_class"),
        FieldSpec("source_id", "str", True, "fuente del límite o variable"),
        FieldSpec("crs", "str", True, "CRS declarado; EPSG:4326 para intercambio"),
    ),
    notes=("una cuenca no coincide con un municipio; el nivel se declara siempre",),
)

_SOILS = DomainSpec(
    code="B", domain="SOILS", name="Suelos",
    description="Textura, profundidad, pH, materia orgánica, nutrientes, drenaje "
                "y propiedades hidráulicas.",
    natural_key=("sample_id", "depth_top_cm", "depth_bottom_cm", "variable"),
    temporal="static",
    territory_levels=("department", "municipality_2023", "district",
                      "agricultural_unit", "parcel"),
    evidence_default="observation",
    prepared=("esquema por variable y profundidad; SoilGrids 0–30 cm integrado "
              "como predicción con incertidumbre declarada"),
    not_implemented=("pedotransferencia para capacidad de campo y punto de "
                     "marchitez; Mapa Digital de Suelos del CENTA (sin acceso)"),
    fields=(
        FieldSpec("sample_id", "str", True, "identificador de muestra o celda"),
        FieldSpec("variable", "str", True, "propiedad del suelo",
                  enumerated=("clay", "sand", "silt", "ph", "soil_organic_carbon",
                              "soil_nitrogen", "nutrient", "soil_depth",
                              "soil_moisture")),
        FieldSpec("value", "float", True, "valor de la propiedad"),
        FieldSpec("unit", "str", True, "unidad declarada; se valida contra el registro"),
        FieldSpec("depth_top_cm", "float", True, "límite superior del intervalo",
                  unit_variable="soil_depth"),
        FieldSpec("depth_bottom_cm", "float", True, "límite inferior del intervalo",
                  unit_variable="soil_depth"),
        FieldSpec("longitude", "float", False, "longitud EPSG:4326",
                  longitude=True),
        FieldSpec("latitude", "float", False, "latitud EPSG:4326", latitude=True),
        FieldSpec("territory_id", "str", False, "unidad territorial si aplica"),
        FieldSpec("analysis_method", "str", True,
                  "método de laboratorio o de predicción (Olsen, KCl, DTPA, ML)"),
        FieldSpec("evidence_class", "str", True, "observación o predicción",
                  enumerated=("observation", "reanalysis", "simulation")),
        FieldSpec("source_id", "str", True, "fuente"),
        FieldSpec("uncertainty", "float", False, "incertidumbre estándar en la "
                                                 "unidad del valor"),
    ),
    notes=("SoilGrids es una predicción global a 250 m: no se mezcla con "
           "mediciones CENTA en la misma columna sin declararlo",),
)

_HYDROLOGY = DomainSpec(
    code="C", domain="HYDROLOGY", name="Hidrografía",
    description="Ríos, lagos, cuencas, acuíferos, pozos, estaciones y recursos "
                "hídricos.",
    natural_key=("station_id", "variable", "time"),
    temporal="series",
    territory_levels=("basin", "subbasin", "microbasin", "department"),
    evidence_default="observation",
    prepared="esquema de estaciones, caudal, nivel y geometría de cuencas",
    not_implemented=("series de aforo (SNET/MARN sin acceso); acuíferos; "
                     "calibración de modelos hidrológicos"),
    fields=(
        FieldSpec("station_id", "str", True, "identificador de estación o punto"),
        FieldSpec("variable", "str", True, "variable hidrológica",
                  enumerated=("discharge", "water_level", "precipitation")),
        FieldSpec("time", "datetime", True, "instante en UTC"),
        FieldSpec("value", "float", True, "valor medido"),
        FieldSpec("unit", "str", True, "unidad declarada"),
        FieldSpec("longitude", "float", True, "longitud EPSG:4326",
                  longitude=True),
        FieldSpec("latitude", "float", True, "latitud EPSG:4326", latitude=True),
        FieldSpec("basin_id", "str", False, "cuenca (territory_id nivel basin)"),
        FieldSpec("measurement_method", "str", True, "aforo, limnímetro, radar…"),
        FieldSpec("evidence_class", "str", True, "clase de evidencia",
                  enumerated=_EVIDENCE),
        FieldSpec("quality_flag", "str", False, "ok | suspect | estimated"),
        FieldSpec("source_id", "str", True, "fuente"),
    ),
    notes=("caudal derivado de un DEM no es caudal observado; se etiqueta "
           "simulado y no se calibra sin aforos",),
)

_CLIMATE = DomainSpec(
    code="D", domain="CLIMATE", name="Clima",
    description="Precipitación, temperatura, radiación, viento, humedad y "
                "evapotranspiración.",
    natural_key=("dataset_id", "longitude", "latitude", "variable", "time"),
    temporal="series",
    territory_levels=("country", "department", "municipality_2023", "agricultural_unit"),
    evidence_default="reanalysis",
    prepared=("series diarias de punto normalizadas (NASA POWER, Open-Meteo) con "
              "base temporal y clase de evidencia declaradas"),
    not_implemented="series de estaciones SNET; AgERA5 (requiere token CDS)",
    fields=(
        FieldSpec("dataset_id", "str", True, "dataset de origen"),
        FieldSpec("variable", "str", True, "variable climática",
                  enumerated=("precipitation", "temperature", "relative_humidity",
                              "et0", "radiation", "wind_speed")),
        FieldSpec("time", "datetime", True, "fecha/hora del período, base declarada"),
        FieldSpec("value", "float", True, "valor"),
        FieldSpec("unit", "str", True, "unidad declarada"),
        FieldSpec("longitude", "float", True, "longitud de la celda o punto",
                  longitude=True),
        FieldSpec("latitude", "float", True, "latitud de la celda o punto",
                  latitude=True),
        FieldSpec("cell_support", "str", False,
                  "tamaño de celda o soporte del valor (p. ej. 0,05° o punto)"),
        FieldSpec("evidence_class", "str", True,
                  "observation | reanalysis | forecast | climate_projection",
                  enumerated=("observation", "reanalysis", "forecast",
                              "climate_projection")),
        FieldSpec("aggregation", "str", True, "sum | mean | max | min | instant",
                  enumerated=("sum", "mean", "max", "min", "instant")),
        FieldSpec("time_basis", "str", True, "UTC | local",
                  enumerated=("UTC", "local")),
        FieldSpec("source_id", "str", True, "fuente"),
    ),
    notes=("un pronóstico nunca se almacena en la misma serie que una "
           "observación; el período y la fuente se conservan por registro",),
)

_AGRICULTURE = DomainSpec(
    code="E", domain="AGRICULTURE", name="Agricultura",
    description="Cultivos, variedades, producción, calendarios y sistemas "
                "productivos.",
    natural_key=("crop", "variety", "territory_id", "season", "year", "system"),
    temporal="aggregate",
    territory_levels=("country", "department", "municipality_2023", "district",
                      "agricultural_unit"),
    evidence_default="aggregate",
    prepared="esquema de superficie, producción y rendimiento por unidad territorial",
    not_implemented=("microdatos del CAP 2025 (no públicos); parámetros locales "
                     "calibrados por variedad"),
    fields=(
        FieldSpec("crop", "str", True, "cultivo (nombre común y código si existe)"),
        FieldSpec("variety", "str", False, "variedad; vacío si el agregado no la distingue"),
        FieldSpec("territory_id", "str", True, "unidad territorial"),
        FieldSpec("season", "str", False, "primera | postrera | apante | anual",
                  enumerated=("primera", "postrera", "apante", "anual")),
        FieldSpec("year", "int", True, "año agrícola declarado"),
        FieldSpec("system", "str", False, "secano | riego | mixto",
                  enumerated=("secano", "riego", "mixto")),
        FieldSpec("area_ha", "float", False, "superficie sembrada o cosechada",
                  unit_variable="area"),
        FieldSpec("production_t", "float", False, "producción",
                  unit_variable="production"),
        FieldSpec("yield_t_ha", "float", False, "rendimiento",
                  unit_variable="yield"),
        FieldSpec("evidence_class", "str", True, "observación censal o estimación",
                  enumerated=("observation", "aggregate", "simulation")),
        FieldSpec("source_id", "str", True, "fuente (CAP, anuario, MAG)"),
    ),
    notes=("la superficie cosechada y la sembrada no son intercambiables; se "
           "declara cuál es",),
)

_ECONOMY = DomainSpec(
    code="F", domain="ECONOMY", name="Economía",
    description="Precios, costos, mercados, transporte y estadísticas "
                "agropecuarias.",
    natural_key=("product", "market", "price_date", "presentation"),
    temporal="series",
    territory_levels=("country", "department", "municipality_2023"),
    evidence_default="aggregate",
    prepared="esquema de precios con plaza, presentación y moneda explícitas",
    not_implemented="series históricas tabuladas completas (los boletines son PDF)",
    fields=(
        FieldSpec("product", "str", True, "producto"),
        FieldSpec("market", "str", True, "plaza o mercado"),
        FieldSpec("price_date", "date", True, "fecha del precio"),
        FieldSpec("price_usd", "float", True, "precio",
                  unit_variable="price"),
        FieldSpec("presentation", "str", True,
                  "unidad de venta (quintal, caja, libra, docena)"),
        FieldSpec("product_class", "str", False, "mayorista | consumidor | insumo",
                  enumerated=("mayorista", "consumidor", "insumo")),
        FieldSpec("territory_id", "str", False, "unidad territorial de la plaza"),
        FieldSpec("evidence_class", "str", True, "clase de evidencia",
                  enumerated=("observation", "aggregate")),
        FieldSpec("source_id", "str", True, "fuente"),
    ),
    notes=("un precio sin presentación ni plaza no es comparable",),
)

_PHYTOSANITARY = DomainSpec(
    code="G", domain="PHYTOSANITARY", name="Fitosanidad",
    description="Plagas, enfermedades, reportes y vigilancia.",
    natural_key=("report_id",),
    temporal="event",
    territory_levels=("country", "department", "municipality_2023", "district",
                      "parcel"),
    evidence_default="observation",
    prepared="esquema de reportes con método de detección y severidad declarada",
    not_implemented=("modelo de riesgo; series de vigilancia (ISC/IPPC sin datos "
                     "crudos verificados)"),
    fields=(
        FieldSpec("report_id", "str", True, "identificador del reporte"),
        FieldSpec("pest", "str", True, "plaga o enfermedad (nombre científico si existe)"),
        FieldSpec("crop", "str", False, "cultivo afectado"),
        FieldSpec("territory_id", "str", False, "unidad territorial del reporte"),
        FieldSpec("date", "date", True, "fecha del reporte o de detección"),
        FieldSpec("severity", "str", False, "baja | media | alta",
                  enumerated=("baja", "media", "alta")),
        FieldSpec("detection_method", "str", True,
                  "trampa, inspección, laboratorio, reporte de productor"),
        FieldSpec("evidence_class", "str", True, "observación o modelado",
                  enumerated=("observation", "simulation")),
        FieldSpec("source_id", "str", True, "fuente"),
    ),
    notes=("un reporte de productor no equivale a confirmación de laboratorio",),
)

_BIODIVERSITY = DomainSpec(
    code="H", domain="BIODIVERSITY", name="Biodiversidad",
    description="Cobertura natural, ecosistemas, especies y restricciones "
                "ambientales.",
    natural_key=("occurrence_id",),
    temporal="event",
    territory_levels=("country", "department", "protected_area"),
    evidence_default="observation",
    prepared="esquema de ocurrencias con incertidumbre de coordenada e issues",
    not_implemented="listas rojas nacionales; vacíos de muestreo corregidos",
    fields=(
        FieldSpec("occurrence_id", "str", True, "identificador de la ocurrencia"),
        FieldSpec("taxon", "str", True, "nombre científico"),
        FieldSpec("longitude", "float", True, "longitud EPSG:4326",
                  longitude=True),
        FieldSpec("latitude", "float", True, "latitud EPSG:4326", latitude=True),
        FieldSpec("event_date", "datetime", False, "fecha de observación"),
        FieldSpec("basis_of_record", "str", False,
                  "HUMAN_OBSERVATION | MACHINE_OBSERVATION | PRESERVED_SPECIMEN…"),
        FieldSpec("coordinate_uncertainty_m", "float", False,
                  "incertidumbre declarada de la coordenada"),
        FieldSpec("protected_area_id", "str", False, "área protegida si aplica"),
        FieldSpec("dataset_id", "str", True, "dataset de origen"),
        FieldSpec("source_id", "str", True, "fuente"),
    ),
    notes=("GBIF agrega fuentes heterogéneas: el sesgo de muestreo no se corrige "
           "por agregación",),
)

DOMAINS: dict[str, DomainSpec] = {
    d.domain: d for d in (_TERRITORY, _SOILS, _HYDROLOGY, _CLIMATE,
                          _AGRICULTURE, _ECONOMY, _PHYTOSANITARY, _BIODIVERSITY)
}


def domain(key: str) -> DomainSpec:
    k = key.upper()
    if k not in DOMAINS:
        raise KeyError(f"dominio desconocido: {key}; use {sorted(DOMAINS)}")
    return DOMAINS[k]


def _coerce(value: Any, spec: FieldSpec) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    try:
        if spec.dtype == "float":
            f = float(value)
            if not math.isfinite(f):
                return None, "no finito"
            return f, None
        if spec.dtype == "int":
            return int(value), None
        if spec.dtype == "bool":
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "si", "sí"}, None
            return bool(value), None
        if spec.dtype == "date":
            if isinstance(value, datetime):
                return value.date(), None
            if isinstance(value, date):
                return value, None
            return date.fromisoformat(str(value)[:10]), None
        if spec.dtype == "datetime":
            if isinstance(value, datetime):
                return value, None
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")), None
        return str(value), None
    except (TypeError, ValueError) as exc:
        return None, str(exc)


def validate_record(domain_key: str, record: Mapping[str, Any]
                    ) -> dict[str, Any]:
    """Valida un registro contra el contrato del dominio."""
    spec = domain(domain_key)
    errors: list[str] = []
    warnings: list[str] = []
    coerced: dict[str, Any] = {}

    known = {f.name for f in spec.fields}
    unknown = set(record) - known
    if unknown:
        warnings.append(f"campos no declarados en el contrato: {sorted(unknown)}")

    for f in spec.fields:
        if f.required and (f.name not in record or record[f.name] in (None, "")):
            errors.append(f"falta campo obligatorio: {f.name}")
            continue
        if f.name not in record:
            continue
        value, problem = _coerce(record[f.name], f)
        if problem:
            errors.append(f"{f.name}: no convertible a {f.dtype} ({problem})")
            continue
        coerced[f.name] = value
        if value is None:
            continue
        if f.enumerated and str(value) not in f.enumerated:
            errors.append(
                f"{f.name}: valor '{value}' fuera de {list(f.enumerated)}")
        if f.latitude and not -90 <= float(value) <= 90:
            errors.append(f"{f.name}: latitud fuera de rango ({value})")
        if f.longitude and not -180 <= float(value) <= 180:
            errors.append(f"{f.name}: longitud fuera de rango ({value})")

    unit = record.get("unit")
    variable = record.get("variable")
    if variable and unit and not U.check_unit(str(variable), str(unit))["ok"]:
        errors.append(
            f"unidad '{unit}' incompatible con la variable '{variable}'")

    if spec.domain == "SOILS" and {"depth_top_cm", "depth_bottom_cm"} <= set(coerced):
        top = coerced.get("depth_top_cm")
        bottom = coerced.get("depth_bottom_cm")
        if top is not None and bottom is not None and bottom <= top:
            errors.append("depth_bottom_cm debe ser mayor que depth_top_cm")

    if spec.domain == "ECONOMY" and not record.get("presentation"):
        warnings.append("precio sin presentación: no es comparable")

    return {"domain": spec.domain, "ok": not errors, "errors": errors,
            "warnings": warnings, "record": coerced}


def validate_records(domain_key: str, records: Iterable[Mapping[str, Any]]
                     ) -> dict[str, Any]:
    """Valida un lote y comprueba unicidad de la clave natural."""
    spec = domain(domain_key)
    results = [validate_record(domain_key, r) for r in records]
    seen: dict[tuple[Any, ...], int] = {}
    duplicates: list[tuple[int, int]] = []
    for i, record in enumerate(records):
        key = tuple(record.get(k) for k in spec.natural_key)
        if all(v is None for v in key):
            continue
        if key in seen:
            duplicates.append((seen[key], i))
        else:
            seen[key] = i
    errors = sum(len(r["errors"]) for r in results)
    return {
        "domain": spec.domain,
        "records": len(results),
        "invalid": sum(1 for r in results if not r["ok"]),
        "errors": errors,
        "duplicate_keys": duplicates,
        "ok": errors == 0 and not duplicates,
        "natural_key": list(spec.natural_key),
        "note": "la clave natural no sustituye a un id de origen; evita "
                "duplicados en la tabla normalizada",
    }


def table_contract(domain_key: str) -> dict[str, Any]:
    """Contrato de tabla listo para crear un esquema SQL o Arrow."""
    spec = domain(domain_key)
    return {
        "table": spec.domain.lower(),
        "columns": [
            {"name": f.name,
             "sql_type": {"float": "REAL", "int": "INTEGER", "bool": "INTEGER",
                          "date": "TEXT", "datetime": "TEXT", "str": "TEXT"}[f.dtype],
             "required": f.required,
             "unit": (U.spec(f.unit_variable).canonical_unit
                      if f.unit_variable and U.spec(f.unit_variable) else None),
             "description": f.description}
            for f in spec.fields
        ],
        "primary_key": list(spec.natural_key),
        "temporal": spec.temporal,
        "territory_levels": list(spec.territory_levels),
        "evidence_default": spec.evidence_default,
    }


def all_domains() -> dict[str, Any]:
    return {
        "count": len(DOMAINS),
        "domains": [d.as_dict() for d in DOMAINS.values()],
        "status": {d.domain: {"prepared": d.prepared,
                             "not_implemented": d.not_implemented}
                   for d in DOMAINS.values()},
        "note": ("estructuras preparadas y validadas; los modelos científicos "
                 "de cada dominio no forman parte de esta fase"),
    }


def integration_matrix() -> dict[str, Any]:
    """Qué dominio tiene estructura, datos integrados y qué falta."""
    return {
        "domains": {
            d.domain: {
                "code": d.code,
                "structure": "prepared",
                "temporal": d.temporal,
                "territory_levels": list(d.territory_levels),
                "prepared": d.prepared,
                "not_implemented": d.not_implemented,
            } for d in DOMAINS.values()
        },
        "rule": ("una estructura preparada no implica datos disponibles: el "
                 "estado real de cada dataset está en el catálogo"),
    }
