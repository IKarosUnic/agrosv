"""AGROSV — API de datos integrados `/api/data` (Fase 4, §14).

Publica solo lo que existe. Si el catálogo no se ha construido, responde 503 con
la instrucción; si un dataset no está `INTEGRATED`, no sirve observaciones. No
hay endpoints de demostración con datos inventados.

Consultas implementadas y probadas en `tests/test_data_api.py`:

    GET /api/data/catalog
    GET /api/data/datasets/{dataset_id}
    GET /api/data/datasets/{dataset_id}/lineage
    GET /api/data/territories
    GET /api/data/territory/{territory_id}
    GET /api/data/observations
    GET /api/data/occurrences
    GET /api/data/raster/metadata
    GET /api/data/quality/reports
    GET /api/data/quality/reports/{dataset_id}
    GET /api/data/domains
    GET /api/data/storage
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from .. import config as C
from . import domains as dom
from . import storage as S
from .catalog import Catalog, DatasetNotFound, DatasetState
from .lineage import LineageGraph
from .store import DataStore

router = APIRouter(prefix="/api/data", tags=["data"])

SERVICE_VERSION = "4.0.0"
DEFAULT_CATALOG = C.DATA / "metadata" / "datasets.json"
DEFAULT_RASTER_CATALOG = C.DATA / "metadata" / "raster_catalog.json"
DEFAULT_LINEAGE = C.DATA / "manifests" / "lineage.json"


def _header_text(value: str) -> str:
    """Los encabezados HTTP son latin-1: se transliteran sin perder el sentido."""
    import unicodedata

    text = unicodedata.normalize("NFKD", value)
    text = text.encode("ascii", "ignore").decode("ascii")
    return " ".join(text.split())


def _headers(*, provenance: str = "", license_: str = "") -> dict[str, str]:
    from datetime import datetime, timezone

    headers = {
        "X-AGROSV-Version": SERVICE_VERSION,
        "X-AGROSV-Data-Date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    if provenance:
        headers["X-AGROSV-Provenance"] = _header_text(provenance)
    if license_:
        headers["X-AGROSV-License"] = _header_text(license_)
    return headers


def _catalog() -> Catalog:
    if not DEFAULT_CATALOG.exists():
        raise HTTPException(
            503,
            "catálogo no construido: ejecute "
            "`python scripts/08_build_phase4_integration.py`")
    return Catalog.load(DEFAULT_CATALOG)


def _store() -> DataStore:
    return DataStore(S.layout().store_path)


def _report_stamp(report: dict[str, Any]) -> str:
    return str(report.get("generated_at") or report.get("created_at") or "")


def _report_key(report: dict[str, Any]) -> tuple[Any, Any]:
    """Un informe describe un artefacto concreto de un dataset."""
    return report.get("dataset_id"), report.get("artifact")


def _current_reports(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Descarta informes superados por una revisión posterior del mismo artefacto.

    El mismo artefacto revalidado produce un informe nuevo que reemplaza al
    anterior: si el anterior era `FAIL`, ya no es evidencia vigente y no debe
    publicarse. Artefactos distintos del mismo dataset son evidencia separada y
    se conservan. Los empates de fecha se conservan todos: no se elige uno al
    azar entre dos revisiones simultáneas.
    """
    latest: dict[tuple[Any, Any], str] = {}
    for report in reports:
        key, stamp = _report_key(report), _report_stamp(report)
        if key not in latest or stamp > latest[key]:
            latest[key] = stamp
    return [r for r in reports if _report_stamp(r) == latest[_report_key(r)]]


def _directory_reports(directory: Path, pattern: str) -> list[dict[str, Any]]:
    """Respaldo sin base SQLite: JSON del directorio, solo los vigentes."""
    reports = _current_reports([json.loads(p.read_text(encoding="utf-8"))
                                for p in sorted(directory.glob(pattern))])
    reports.sort(key=lambda r: (_report_stamp(r), str(r.get("report_id") or "")),
                 reverse=True)
    return reports


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    parts = bbox.split(",")
    if len(parts) != 4:
        raise HTTPException(400, "bbox debe ser 'oeste,sur,este,norte'")
    try:
        west, south, east, north = (float(p) for p in parts)
    except ValueError:
        raise HTTPException(400, "bbox con valores no numéricos") from None
    if not (west < east and south < north):
        raise HTTPException(400, "bbox inválido: se exige oeste<este y sur<norte")
    if not (-180 <= west <= 180 and -180 <= east <= 180
            and -90 <= south <= 90 and -90 <= north <= 90):
        raise HTTPException(400, "bbox fuera de rango geográfico")
    return west, south, east, north


# --- catálogo ----------------------------------------------------------------
@router.get("/catalog", summary="Catálogo nacional de datasets con estado y evidencia")
def catalog(domain: str | None = None,
            state: str | None = None,
            institution: str | None = None,
            redistributable: bool | None = None,
            include_transitions: bool = False):
    cat = _catalog()
    try:
        records = cat.select(domain=domain, state=state, institution=institution,
                             redistributable=redistributable)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    payload = [r.as_dict() if include_transitions else
               {k: v for k, v in r.as_dict().items() if k != "transitions"}
               for r in records]
    return JSONResponse(
        content={
            "service_version": SERVICE_VERSION,
            "summary": cat.summary(),
            "audit": cat.audit(),
            "filters": {"domain": domain, "state": state,
                        "institution": institution,
                        "redistributable": redistributable},
            "count": len(payload),
            "datasets": payload,
            "states": [s.value for s in DatasetState],
            "note": ("state ≠ calidad científica; evidence_level es independiente "
                     "y el catálogo no eleva niveles por importar"),
        },
        headers=_headers(),
    )


@router.get("/datasets/{dataset_id}", summary="Ficha completa de un dataset")
def dataset(dataset_id: str):
    cat = _catalog()
    try:
        record = cat.get(dataset_id)
    except DatasetNotFound:
        raise HTTPException(404, f"dataset desconocido: {dataset_id}") from None
    store = _store()
    assets = store.assets(dataset_id) if store.exists else []
    reports = store.quality_reports(dataset_id=dataset_id, limit=10) if store.exists else []
    return JSONResponse(
        content={
            "dataset": record.as_dict(),
            "assets": assets,
            "quality_reports": [
                {"report_id": r["report_id"], "status": r["status"],
                 "checks_run": r["checks_run"], "generated_at": r["generated_at"]}
                for r in reports],
            "served": record.state is DatasetState.INTEGRATED,
            "note": ("si state != INTEGRATED no se sirven observaciones de este "
                     "dataset, aunque sus metadatos sí son públicos"),
        },
        headers=_headers(license_=record.license),
    )


@router.get("/datasets/{dataset_id}/lineage", summary="Cadena de derivación de un dataset")
def dataset_lineage(dataset_id: str):
    cat = _catalog()
    try:
        cat.get(dataset_id)
    except DatasetNotFound:
        raise HTTPException(404, f"dataset desconocido: {dataset_id}") from None
    if not DEFAULT_LINEAGE.exists():
        raise HTTPException(503, "grafo de linaje no construido")
    graph = LineageGraph.load(DEFAULT_LINEAGE)
    records = [r.as_dict() for r in graph.records if r.dataset_id == dataset_id]
    if not records:
        return JSONResponse(
            content={"dataset_id": dataset_id, "derivations": [],
                     "note": "el dataset no tiene productos derivados registrados; "
                             "no se inventa una cadena"},
            headers=_headers())
    return JSONResponse(content={"dataset_id": dataset_id,
                                 "derivations": records,
                                 "summary": graph.summary()},
                        headers=_headers())


# --- territorio --------------------------------------------------------------
@router.get("/territories", summary="Unidades territoriales por nivel")
def territories(level: str | None = None, parent_id: str | None = None,
                limit: int = Query(500, ge=1, le=5000), offset: int = 0):
    store = _store()
    if not store.exists:
        raise HTTPException(503, "base de datos no construida")
    result = store.territories(level=level, parent_id=parent_id,
                               limit=limit, offset=offset)
    if result.total == 0 and level and level not in {
            "country", "department", "municipality_historic"}:
        return JSONResponse(
            content={**result.as_dict(),
                     "note": (f"el nivel '{level}' no tiene capa verificada en "
                              "este repositorio; no se sintetizan límites")},
            headers=_headers())
    return JSONResponse(content=result.as_dict(), headers=_headers())


@router.get("/territory/{territory_id}", summary="Unidad territorial y sus hijos")
def territory(territory_id: str):
    store = _store()
    if not store.exists:
        raise HTTPException(503, "base de datos no construida")
    item = store.territory(territory_id)
    if item is None:
        raise HTTPException(404, f"territorio no encontrado: {territory_id}")
    return JSONResponse(
        content={"territory": item,
                 "note": ("territory_id es la clave estable; el nombre es un "
                          "atributo de búsqueda")},
        headers=_headers())


# --- observaciones -----------------------------------------------------------
@router.get("/observations", summary="Series normalizadas por dataset, variable y área")
def observations(dataset_id: str | None = None, variable: str | None = None,
                 bbox: str | None = None, territory_id: str | None = None,
                 start: str | None = None, end: str | None = None,
                 limit: int = Query(500, ge=1, le=5000), offset: int = 0):
    cat = _catalog()
    if dataset_id:
        try:
            record = cat.get(dataset_id)
        except DatasetNotFound:
            raise HTTPException(404, f"dataset desconocido: {dataset_id}") from None
        if record.state is not DatasetState.INTEGRATED:
            raise HTTPException(
                409,
                f"{dataset_id} está en {record.state.value}: no hay observaciones "
                "integradas que servir")
    else:
        integrated = [r.dataset_id for r in cat
                      if r.state is DatasetState.INTEGRATED]
        if not integrated:
            return JSONResponse(
                content={"count": 0, "total": 0, "rows": [],
                         "note": "ningún dataset está INTEGRATED todavía"},
                headers=_headers())
    store = _store()
    if not store.exists:
        raise HTTPException(503, "base de datos no construida")
    result = store.observation_query(
        dataset_id=dataset_id, variable=variable, bbox=_parse_bbox(bbox),
        territory_id=territory_id, start=start, end=end, limit=limit, offset=offset)
    return JSONResponse(content=result.as_dict(), headers=_headers())


@router.get("/occurrences", summary="Ocurrencias biológicas normalizadas")
def occurrences(bbox: str | None = None, taxon: str | None = None,
                dataset_id: str | None = None,
                limit: int = Query(500, ge=1, le=5000), offset: int = 0):
    store = _store()
    if not store.exists:
        raise HTTPException(503, "base de datos no construida")
    result = store.occurrences(bbox=_parse_bbox(bbox), taxon=taxon,
                               dataset_id=dataset_id, limit=limit, offset=offset)
    return JSONResponse(
        content={**result.as_dict(),
                 "note": ("ocurrencias agregadas de terceros: el sesgo de muestreo "
                          "no se corrige agregando registros")},
        headers=_headers())


# --- ráster y calidad -------------------------------------------------------
@router.get("/raster/metadata", summary="Perfil de los rásteres gestionados")
def raster_metadata(zone: str | None = None):
    path = DEFAULT_RASTER_CATALOG
    if not path.exists():
        raise HTTPException(
            503, "catálogo ráster no construido: ejecute el script de integración")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rasters = payload.get("rasters", [])
    if zone:
        rasters = [r for r in rasters if r.get("zone") == zone]
    return JSONResponse(
        content={"count": len(rasters), "rasters": rasters,
                 "generated_at": payload.get("generated_at"),
                 "note": ("resolución nativa y efectiva declaradas por separado; "
                          "un remuestreo no se presenta como resolución original")},
        headers=_headers())


@router.get("/quality/reports", summary="Informes de calidad por dataset")
def quality_reports(status: str | None = None, limit: int = Query(100, ge=1, le=500)):
    store = _store()
    if store.exists:
        reports = store.quality_reports(limit=limit)
    else:
        directory = S.layout().quality_dir
        reports = (_directory_reports(directory, "*.json")[:limit]
                   if directory.exists() else [])
    if status:
        reports = [r for r in reports if r.get("status") == status.upper()]
    summaries = [{"report_id": r["report_id"], "dataset_id": r["dataset_id"],
                  "status": r["status"], "checks_run": r["checks_run"],
                  "errors": r.get("errors", 0), "warnings": r.get("warnings", 0),
                  "generated_at": r.get("generated_at")} for r in reports]
    return JSONResponse(
        content={"count": len(summaries), "reports": summaries,
                 "note": ("PASS no significa «dato correcto»: enumera las "
                          "comprobaciones ejecutadas")},
        headers=_headers())


@router.get("/quality/reports/{dataset_id}", summary="Informe completo de calidad")
def quality_report(dataset_id: str):
    store = _store()
    if store.exists:
        reports = store.quality_reports(dataset_id=dataset_id, limit=20)
    else:
        directory = S.layout().quality_dir
        reports = (_directory_reports(directory, f"{dataset_id}.*.json")[:20]
                   if directory.exists() else [])
    if not reports:
        raise HTTPException(404, f"sin informes de calidad para {dataset_id}")
    return JSONResponse(content={"dataset_id": dataset_id, "count": len(reports),
                                 "reports": reports}, headers=_headers())


# --- estructuras y almacenamiento -------------------------------------------
@router.get("/domains", summary="Contratos de datos por dominio (A–H)")
def domain_contracts(code: str | None = None):
    if code:
        matching = [d for d in dom.DOMAINS.values() if d.code.upper() == code.upper()
                    or d.domain == code.upper()]
        if not matching:
            raise HTTPException(404, f"dominio no encontrado: {code}")
        return JSONResponse(content={"domain": matching[0].as_dict(),
                                     "table_contract": dom.table_contract(
                                         matching[0].domain)},
                            headers=_headers())
    return JSONResponse(content=dom.all_domains(), headers=_headers())


@router.get("/storage", summary="Zonas de almacenamiento, política Git y contenido")
def storage_summary():
    lay = S.layout()
    store = DataStore(lay.store_path)
    return JSONResponse(
        content={"layout": S.zone_manifest(lay), "store": store.summary(),
                 "note": ("los binarios grandes no se versionan; la base guarda "
                          "metadatos, series normalizadas e índices")},
        headers=_headers())
