"""AGROSV — catálogo nacional de datos (Fase 4, §3).

El catálogo no es una lista de enlaces: es una máquina de estados con evidencia.
Un dataset solo avanza si existe un artefacto con hash, un informe de validación
aprobado o un registro de integración consultable. No hay forma de marcar algo
como `VALIDATED` o `INTEGRATED` «porque se importó»: las puertas de transición
lo impiden y cada intento fallido explica qué falta.

Separación de conceptos que el catálogo mantiene deliberadamente distinta:

    state          dónde está el dataset en el ciclo de vida (9 estados)
    evidence_level nivel de evidencia científica V0–V4 (ver science.validation)
    scope          a qué escala se descargó/validó/integró (nacional, muestra…)

`INTEGRATED` significa que el dato es consultable por la capa de datos; **no**
significa que sea exacto. Un dataset integrado con evidencia V0 sigue siendo V0.

Estados y transiciones permitidas (todo lo demás es un error):

    DISCOVERED ─┬─> ACCESS_PENDING ─> DOWNLOADED ─> PARSED ─> VALIDATED ─> INTEGRATED
                ├─> RESTRICTED ─────────────────────────────┘
                ├─> UNAVAILABLE
                └─> REJECTED

`REJECTED` es terminal. Un dataset rechazado se reconsidera creando un registro
nuevo con otro `dataset_id`, para que el historial no se reescriba.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, Field, field_validator, model_validator

from .storage import sha256_file


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path: str | Path) -> Path:
    """Ruta existente: absoluta si existe, o relativa a la raíz del proyecto.

    El catálogo guarda rutas relativas (portables); la comprobación de
    existencia no depende del directorio de trabajo.
    """
    from .. import config as C

    p = Path(path)
    if p.exists():
        return p
    return C.ROOT / p


class DatasetState(str, Enum):
    DISCOVERED = "DISCOVERED"
    ACCESS_PENDING = "ACCESS_PENDING"
    DOWNLOADED = "DOWNLOADED"
    PARSED = "PARSED"
    VALIDATED = "VALIDATED"
    INTEGRATED = "INTEGRATED"
    RESTRICTED = "RESTRICTED"
    UNAVAILABLE = "UNAVAILABLE"
    REJECTED = "REJECTED"


ALLOWED_TRANSITIONS: dict[DatasetState, frozenset[DatasetState]] = {
    DatasetState.DISCOVERED: frozenset({
        DatasetState.ACCESS_PENDING, DatasetState.DOWNLOADED,
        DatasetState.RESTRICTED, DatasetState.UNAVAILABLE, DatasetState.REJECTED,
    }),
    DatasetState.ACCESS_PENDING: frozenset({
        DatasetState.DOWNLOADED, DatasetState.RESTRICTED,
        DatasetState.UNAVAILABLE, DatasetState.REJECTED,
    }),
    DatasetState.DOWNLOADED: frozenset({
        DatasetState.PARSED, DatasetState.REJECTED, DatasetState.UNAVAILABLE,
    }),
    DatasetState.PARSED: frozenset({
        DatasetState.VALIDATED, DatasetState.REJECTED,
    }),
    DatasetState.VALIDATED: frozenset({
        DatasetState.INTEGRATED, DatasetState.REJECTED,
        # Revalidación fallida: se degrada y se documenta; no se borra historia.
        DatasetState.DOWNLOADED,
    }),
    DatasetState.INTEGRATED: frozenset({
        DatasetState.VALIDATED, DatasetState.REJECTED,
    }),
    DatasetState.RESTRICTED: frozenset({
        DatasetState.ACCESS_PENDING, DatasetState.REJECTED, DatasetState.UNAVAILABLE,
    }),
    DatasetState.UNAVAILABLE: frozenset({
        DatasetState.ACCESS_PENDING, DatasetState.DISCOVERED, DatasetState.REJECTED,
    }),
    DatasetState.REJECTED: frozenset(),
}

TERMINAL_STATES = frozenset({DatasetState.REJECTED})


class EvidenceType(str, Enum):
    URL_PROBE = "url_probe"
    FILE_HASH = "file_hash"
    PARSE_RESULT = "parse_result"
    VALIDATION_REPORT = "validation_report"
    INTEGRATION_RECORD = "integration_record"
    LICENSE_CHECK = "license_check"
    INSTITUTIONAL_RESPONSE = "institutional_response"
    MANUAL_REVIEW = "manual_review"
    RECONCILIATION = "reconciliation"


class Evidence(BaseModel):
    """Prueba de una transición. Sin `reference` verificable no es evidencia."""

    evidence_type: EvidenceType
    reference: str = Field(min_length=3)
    captured_at: str = Field(default_factory=utcnow)
    note: str = ""
    passed: bool | None = None
    sha256: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path | str, evidence_type: EvidenceType, *,
                  note: str = "", passed: bool | None = None,
                  payload: dict[str, Any] | None = None) -> "Evidence":
        p = _resolve(path)
        exists = p.exists() and p.is_file()
        return cls(
            evidence_type=evidence_type,
            reference=str(path),
            note=note or (f"archivo existente ({p.stat().st_size} B)" if exists
                          else "archivo ausente al registrar la evidencia"),
            passed=passed if passed is not None else exists,
            sha256=sha256_file(p) if exists else None,
            payload=payload or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class Transition(BaseModel):
    dataset_id: str
    state_from: DatasetState
    state_to: DatasetState
    at: str = Field(default_factory=utcnow)
    actor: str = "agrosv.pipeline"
    note: str = ""
    evidence: list[Evidence] = Field(min_length=1)

    @model_validator(mode="after")
    def _evidence_is_not_decorative(self) -> "Transition":
        for ev in self.evidence:
            if not ev.reference.strip():
                raise ValueError("evidencia sin referencia")
        return self


class DatasetRecord(BaseModel):
    """Ficha completa exigida por §3. Los campos pueden ser `None` (desconocido),
    pero nunca inventados: `missing_fields()` los enumera y algunas transiciones
    los exigen."""

    dataset_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,63}$")
    name: str = Field(min_length=3)
    description: str = Field(min_length=10)
    institution: str
    source_url: str
    publication_date: str | None = None
    download_date: str | None = None
    version: str | None = None
    license: str
    redistribution_allowed: bool | None = None
    derived_use_allowed: bool | None = None
    geographic_coverage: str
    temporal_coverage: str
    crs: str | None = None
    spatial_resolution: str | None = None
    temporal_resolution: str | None = None
    variables: list[str] = Field(default_factory=list)
    units: dict[str, str] = Field(default_factory=dict)
    format: str
    size: str | None = None
    methodology: str
    limitations: list[str] = Field(default_factory=list)
    uncertainty: str
    usage_restrictions: str = ""
    domain: str = "TERRITORY"
    state: DatasetState = DatasetState.DISCOVERED
    evidence_level: str = "V0"
    validation_scope: str | None = None
    integration_scope: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    notes: str = ""
    updated_at: str = Field(default_factory=utcnow)

    @field_validator("domain")
    @classmethod
    def _known_domain(cls, value: str) -> str:
        allowed = {"TERRITORY", "SOILS", "HYDROLOGY", "CLIMATE", "AGRICULTURE",
                   "ECONOMY", "PHYTOSANITARY", "BIODIVERSITY"}
        if value.upper() not in allowed:
            raise ValueError(f"dominio desconocido: {value}; use {sorted(allowed)}")
        return value.upper()

    @field_validator("evidence_level")
    @classmethod
    def _known_level(cls, value: str) -> str:
        if value not in {"V0", "V1", "V2", "V3", "V4"}:
            raise ValueError("evidence_level debe ser V0–V4")
        return value

    # Campos que no pueden faltar para afirmar que un dataset está validado.
    CRITICAL_FIELDS: tuple[str, ...] = (
        "license", "geographic_coverage", "temporal_coverage",
        "spatial_resolution", "temporal_resolution", "methodology",
        "uncertainty", "format", "institution", "source_url",
    )

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        for name in self.CRITICAL_FIELDS:
            value = getattr(self, name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(name)
        if not self.limitations:
            missing.append("limitations")
        if not self.variables:
            missing.append("variables")
        # CRS solo es crítico si el dataset es espacial.
        if self.crs is None and any(
            token in self.format.lower()
            for token in ("geojson", "shapefile", "gpkg", "geopackage", "tif",
                          "geotiff", "cog", "raster", "netcdf", "zarr")
        ):
            missing.append("crs")
        # Unidades: toda variable física necesita unidad declarada. Una variable
        # cuya unidad canónica es adimensional (pH, NDVI) puede declarar "".
        from .units import UNITLESS_VARIABLES, spec

        for var in self.variables:
            if var.lower() in UNITLESS_VARIABLES:
                continue
            if var not in self.units:
                missing.append(f"units[{var}]")
                continue
            declared = self.units[var]
            spec_ = spec(var)
            if not declared and not (spec_ and spec_.canonical_unit == ""):
                missing.append(f"units[{var}]")
        return missing

    def as_dict(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["missing_fields"] = self.missing_fields()
        payload["terminal"] = self.state in TERMINAL_STATES
        return payload


class CatalogError(ValueError):
    """Transición rechazada: incluye el motivo y lo que falta."""

    def __init__(self, message: str, *, missing: Iterable[str] = ()) -> None:
        super().__init__(message)
        self.missing = list(missing)


class DatasetNotFound(KeyError):
    pass


def _as_state(value: DatasetState | str) -> DatasetState:
    """Acepta el enum o su valor; `str(enum)` no es el valor en Python 3.11+."""
    if isinstance(value, DatasetState):
        return value
    return DatasetState(str(value))


def _require_evidence(state: DatasetState, evidence: list[Evidence],
                     previous: DatasetRecord) -> None:
    """Puertas de transición. Devuelve nada o lanza CatalogError."""
    if not evidence:
        raise CatalogError(
            f"transición a {state.value} sin evidencia: toda transición debe "
            "poder auditarse"
        )
    kinds = {ev.evidence_type for ev in evidence}
    passed = [ev for ev in evidence if ev.passed is True]

    if state is DatasetState.DOWNLOADED:
        if EvidenceType.FILE_HASH not in kinds:
            raise CatalogError("DOWNLOADED exige evidencia de tipo file_hash")
        if not previous.artifacts:
            raise CatalogError(
                "DOWNLOADED exige al menos un artefacto registrado en `artifacts`"
            )
        missing = [p for p in previous.artifacts if not _resolve(p).exists()]
        if missing:
            raise CatalogError(
                "DOWNLOADED con artefactos ausentes en disco", missing=missing
            )
        if not previous.download_date:
            raise CatalogError("DOWNLOADED exige `download_date`")

    elif state is DatasetState.PARSED:
        if EvidenceType.PARSE_RESULT not in kinds or not passed:
            raise CatalogError(
                "PARSED exige un parse_result con passed=true"
            )
        if not previous.variables:
            raise CatalogError("PARSED exige declarar las variables parseadas")

    elif state is DatasetState.VALIDATED:
        missing = previous.missing_fields()
        if missing:
            raise CatalogError(
                "VALIDATED exige completar los campos críticos", missing=missing
            )
        reports = [ev for ev in evidence
                   if ev.evidence_type is EvidenceType.VALIDATION_REPORT]
        if not reports or not any(ev.passed is True for ev in reports):
            raise CatalogError(
                "VALIDATED exige un validation_report con passed=true"
            )
        checks = max((int(ev.payload.get("checks_run", 0)) for ev in reports),
                     default=0)
        if checks < 3:
            raise CatalogError(
                "VALIDATED exige al menos 3 comprobaciones ejecutadas en el "
                f"informe (declaradas: {checks})"
            )
        if any(ev.payload.get("status") == "FAIL" for ev in reports):
            raise CatalogError("VALIDATED no admite un informe de calidad FAIL")
        if not previous.validation_scope:
            raise CatalogError(
                "VALIDATED exige `validation_scope` (qué se validó y a qué escala)"
            )

    elif state is DatasetState.INTEGRATED:
        if previous.state not in {DatasetState.VALIDATED, DatasetState.INTEGRATED}:
            raise CatalogError(
                "INTEGRATED exige pasar primero por VALIDATED"
            )
        if not previous.validation_scope:
            raise CatalogError("INTEGRATED exige `validation_scope` declarado")
        if not previous.integration_scope:
            raise CatalogError(
                "INTEGRATED exige `integration_scope` (nacional, muestra, punto…)"
            )
        records = [ev for ev in evidence
                   if ev.evidence_type is EvidenceType.INTEGRATION_RECORD]
        if not records or not any(ev.payload.get("queryable") is True for ev in records):
            raise CatalogError(
                "INTEGRATED exige un integration_record con queryable=true"
            )

    elif state is DatasetState.RESTRICTED:
        if EvidenceType.LICENSE_CHECK not in kinds:
            raise CatalogError(
                "RESTRICTED exige evidencia de tipo license_check"
            )

    elif state in {DatasetState.UNAVAILABLE, DatasetState.REJECTED}:
        if not any(ev.passed is False for ev in evidence):
            raise CatalogError(
                f"{state.value} exige evidencia con passed=false que documente "
                "el fallo o el rechazo"
            )
        if state is DatasetState.REJECTED and not previous.limitations:
            raise CatalogError(
                "REJECTED exige declarar al menos una limitación o motivo"
            )


class Catalog:
    """Catálogo persistido en JSON. Una sola fuente de verdad por proyecto."""

    SCHEMA_VERSION = 4

    def __init__(self, path: Path | str,
                 records: dict[str, DatasetRecord] | None = None) -> None:
        self.path = Path(path)
        self._records: dict[str, DatasetRecord] = records or {}

    # --- persistencia ------------------------------------------------------
    @classmethod
    def load(cls, path: Path | str) -> "Catalog":
        p = Path(path)
        if not p.exists():
            return cls(p)
        payload = json.loads(p.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) > cls.SCHEMA_VERSION:
            raise ValueError(
                f"catálogo con esquema {payload.get('schema_version')} más nuevo "
                f"que este código ({cls.SCHEMA_VERSION})"
            )
        records = {}
        for raw in payload.get("datasets", []):
            record = DatasetRecord.model_validate(raw)
            records[record.dataset_id] = record
        return cls(p, records)

    def save(self) -> Path:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": utcnow(),
            "count": len(self._records),
            "states": self.summary()["by_state"],
            "datasets": [r.as_dict() for r in sorted(
                self._records.values(), key=lambda r: r.dataset_id)],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        return self.path

    # --- consulta ----------------------------------------------------------
    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(sorted(self._records.values(), key=lambda r: r.dataset_id))

    def ids(self) -> list[str]:
        return sorted(self._records)

    def get(self, dataset_id: str) -> DatasetRecord:
        try:
            return self._records[dataset_id]
        except KeyError:
            raise DatasetNotFound(dataset_id) from None

    def select(self, *, domain: str | None = None, state: DatasetState | str | None = None,
               institution: str | None = None,
               redistributable: bool | None = None) -> list[DatasetRecord]:
        wanted = _as_state(state) if state else None
        out = []
        for record in self:
            if domain and record.domain != domain.upper():
                continue
            if wanted and record.state is not wanted:
                continue
            if institution and institution.lower() not in record.institution.lower():
                continue
            if redistributable is not None and record.redistribution_allowed is not redistributable:
                continue
            out.append(record)
        return out

    def transitions(self) -> list[Transition]:
        return [t for r in self for t in r.transitions]

    # --- mutación ----------------------------------------------------------
    def add(self, record: DatasetRecord, evidence: list[Evidence],
            *, actor: str = "agrosv.pipeline", note: str = "alta en catálogo") -> DatasetRecord:
        if record.dataset_id in self._records:
            raise CatalogError(f"dataset_id duplicado: {record.dataset_id}")
        if record.state is not DatasetState.DISCOVERED:
            raise CatalogError(
                "un registro nuevo entra como DISCOVERED; use transition() para "
                "avanzarlo con evidencia"
            )
        if not evidence:
            raise CatalogError(
                "el alta en catálogo exige evidencia de descubrimiento"
            )
        transition = Transition(
            dataset_id=record.dataset_id,
            state_from=DatasetState.DISCOVERED,
            state_to=DatasetState.DISCOVERED,
            actor=actor, note=note, evidence=evidence,
        )
        record = record.model_copy(update={"transitions": [transition],
                                           "updated_at": utcnow()})
        self._records[record.dataset_id] = record
        return record

    def patch(self, dataset_id: str, **fields: Any) -> DatasetRecord:
        """Actualiza metadatos concretos sin tocar estado ni historial.

        Es la vía para completar `artifacts`, `download_date` o
        `integration_scope` **antes** de una transición, sin fingir que el
        dataset ya cambió de estado.
        """
        forbidden = {"state", "transitions", "dataset_id"} & set(fields)
        if forbidden:
            raise CatalogError(
                f"patch() no modifica {sorted(forbidden)}: use transition()")
        record = self.get(dataset_id)
        updated = record.model_copy(update={**fields, "updated_at": utcnow()})
        self._records[dataset_id] = updated
        return updated

    def upsert(self, record: DatasetRecord) -> DatasetRecord:
        """Reemplaza metadatos **sin** tocar estado ni historial.

        Se usa al refrescar fichas (por ejemplo, completar la licencia) sin
        fingir una transición. El estado y las transiciones se conservan.
        """
        if record.dataset_id not in self._records:
            raise DatasetNotFound(record.dataset_id)
        current = self._records[record.dataset_id]
        merged = record.model_copy(update={
            "state": current.state,
            "transitions": current.transitions,
            "updated_at": utcnow(),
        })
        self._records[record.dataset_id] = merged
        return merged

    def transition(self, dataset_id: str, to_state: DatasetState | str,
                   evidence: list[Evidence], *, actor: str = "agrosv.pipeline",
                   note: str = "") -> DatasetRecord:
        record = self.get(dataset_id)
        target = _as_state(to_state)
        allowed = ALLOWED_TRANSITIONS[record.state]
        if target not in allowed:
            raise CatalogError(
                f"transición no permitida {record.state.value} -> {target.value}; "
                f"desde {record.state.value} solo se admite "
                f"{sorted(s.value for s in allowed) or 'nada (estado terminal)'}"
            )
        _require_evidence(target, evidence, record)
        transition = Transition(
            dataset_id=dataset_id, state_from=record.state, state_to=target,
            actor=actor, note=note, evidence=evidence,
        )
        updated = record.model_copy(update={
            "state": target,
            "transitions": [*record.transitions, transition],
            "updated_at": utcnow(),
        })
        if target is DatasetState.VALIDATED:
            report = next(ev for ev in evidence
                          if ev.evidence_type is EvidenceType.VALIDATION_REPORT
                          and ev.passed is True)
            updated = updated.model_copy(update={
                "validation_scope": updated.validation_scope or
                str(report.payload.get("scope", "muestra descargada")),
            })
        self._records[dataset_id] = updated
        return updated

    # --- resúmenes ---------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        by_state = {s.value: 0 for s in DatasetState}
        by_domain: dict[str, int] = {}
        for record in self._records.values():
            by_state[record.state.value] += 1
            by_domain[record.domain] = by_domain.get(record.domain, 0) + 1
        return {
            "count": len(self._records),
            "by_state": by_state,
            "by_domain": dict(sorted(by_domain.items())),
            "integrated": sorted(r.dataset_id for r in self
                                 if r.state is DatasetState.INTEGRATED),
            "restricted_or_unavailable": sorted(
                r.dataset_id for r in self
                if r.state in {DatasetState.RESTRICTED, DatasetState.UNAVAILABLE}),
            "note": ("state ≠ calidad: un dataset INTEGRATED puede tener "
                     "evidence_level V0"),
        }

    def audit(self) -> dict[str, Any]:
        """Comprueba coherencia interna del catálogo completo."""
        problems: list[str] = []
        for record in self:
            if record.state is not DatasetState.DISCOVERED and not record.transitions:
                problems.append(f"{record.dataset_id}: sin historial de transiciones")
            states = [t.state_to for t in record.transitions]
            if states and states[-1] is not record.state:
                problems.append(
                    f"{record.dataset_id}: el último estado del historial "
                    f"({states[-1].value}) no coincide con el estado actual "
                    f"({record.state.value})"
                )
            for prev, curr in zip(states, states[1:]):
                if curr not in ALLOWED_TRANSITIONS[prev]:
                    problems.append(
                        f"{record.dataset_id}: historial con transición inválida "
                        f"{prev.value}->{curr.value}"
                    )
            if record.state is DatasetState.VALIDATED and not record.validation_scope:
                problems.append(f"{record.dataset_id}: VALIDATED sin validation_scope")
            if record.state is DatasetState.INTEGRATED and not record.integration_scope:
                problems.append(f"{record.dataset_id}: INTEGRATED sin integration_scope")
        return {
            "checked": len(self._records),
            "ok": not problems,
            "problems": problems,
            "transitions": len(self.transitions()),
            "note": "auditoría estructural, no científica: no reevalúa la calidad",
        }
