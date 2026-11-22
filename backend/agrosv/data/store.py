"""AGROSV — capa de almacenamiento y consulta (Fase 4, §13 y §14).

Elección: **SQLite** para lo que debe consultarse por clave (catálogo,
observaciones normalizadas, ocurrencias, territorios) y **archivos** para
rásteres y vectores completos. No se introduce PostgreSQL/PostGIS: el volumen
integrado actual es de decenas de miles de filas, el proyecto se ejecuta local y
PostGIS añadiría un servicio que nadie consulta todavía. La migración futura es
directa porque el esquema es SQL explícito y las geometrías se guardan como
GeoJSON, no como tipos propietarios.

Lo que **no** va en SQLite: rásteres (COG/GeoTIFF), capas vectoriales completas
(GeoPackage) y archivos crudos. La base solo guarda metadatos, índices de
consulta y series normalizadas; los binarios viven en `data/` y se referencian
por ruta y hash.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = 4

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    state TEXT NOT NULL,
    institution TEXT,
    license TEXT,
    geographic_coverage TEXT,
    temporal_coverage TEXT,
    spatial_resolution TEXT,
    temporal_resolution TEXT,
    integration_scope TEXT,
    evidence_level TEXT,
    variables_json TEXT,
    units_json TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    dataset_version TEXT,
    source_id TEXT,
    variable TEXT NOT NULL,
    unit TEXT NOT NULL,
    value REAL NOT NULL,
    time_utc TEXT,
    time_local TEXT,
    period_start TEXT,
    period_end TEXT,
    frequency TEXT,
    aggregation TEXT,
    evidence_class TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    cell_support TEXT,
    territory_id TEXT,
    quality_flag TEXT DEFAULT 'ok'
);

CREATE INDEX IF NOT EXISTS idx_obs_dataset_variable_time
    ON observations (dataset_id, variable, time_utc);
CREATE INDEX IF NOT EXISTS idx_obs_territory ON observations (territory_id);
CREATE INDEX IF NOT EXISTS idx_obs_bbox ON observations (longitude, latitude);

CREATE TABLE IF NOT EXISTS occurrences (
    occurrence_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    taxon TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    event_date TEXT,
    basis_of_record TEXT,
    coordinate_uncertainty_m REAL,
    issues_json TEXT,
    territory_id TEXT,
    quality_flag TEXT DEFAULT 'ok'
);
CREATE INDEX IF NOT EXISTS idx_occ_bbox ON occurrences (longitude, latitude);

CREATE TABLE IF NOT EXISTS territories (
    territory_id TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    name TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    parent_id TEXT,
    source_code TEXT,
    source_id TEXT,
    official INTEGER,
    area_km2 REAL,
    bbox_json TEXT,
    centroid_json TEXT,
    geometry_geojson TEXT,
    geometry_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_territory_level ON territories (level);

CREATE TABLE IF NOT EXISTS assets (
    artifact_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    bytes INTEGER,
    format TEXT,
    state TEXT,
    manifest_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_assets_dataset ON assets (dataset_id);

CREATE TABLE IF NOT EXISTS quality_reports (
    report_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    status TEXT NOT NULL,
    checks_run INTEGER,
    report_json TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_qr_dataset ON quality_reports (dataset_id);
"""


class StoreError(RuntimeError):
    pass


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    filters: dict[str, Any]
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"count": len(self.rows), "total": self.total,
                "limit": self.limit, "offset": self.offset,
                "filters": self.filters, "rows": self.rows,
                "note": self.note}


class DataStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._rtree = False

    # --- conexión ----------------------------------------------------------
    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_schema(self) -> dict[str, Any]:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                         ("schema_version", str(SCHEMA_VERSION)))
            self._rtree = _try_rtree(conn)
            return {"path": str(self.path), "schema_version": SCHEMA_VERSION,
                    "rtree": self._rtree}

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def summary(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"exists": False, "path": str(self.path),
                    "note": "base no construida: ejecute el script de integración"}
        with self.connect() as conn:
            def count(table: str) -> int:
                try:
                    return int(conn.execute(f"SELECT COUNT(*) FROM {table}")
                               .fetchone()[0])
                except sqlite3.OperationalError:
                    return 0
            return {
                "exists": True, "path": str(self.path),
                "schema_version": SCHEMA_VERSION,
                "datasets": count("datasets"),
                "observations": count("observations"),
                "occurrences": count("occurrences"),
                "territories": count("territories"),
                "assets": count("assets"),
                "quality_reports": count("quality_reports"),
                "rtree": self._has_rtree(conn),
            }

    def _has_rtree(self, conn: sqlite3.Connection) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='observations_rtree'"
        ).fetchone()
        return row is not None

    # --- carga -------------------------------------------------------------
    def upsert_datasets(self, records: Iterable[Any]) -> int:
        rows = []
        for r in records:
            payload = r.as_dict() if hasattr(r, "as_dict") else dict(r)
            rows.append((
                payload["dataset_id"], payload["name"], payload["domain"],
                payload["state"], payload.get("institution"),
                payload.get("license"), payload.get("geographic_coverage"),
                payload.get("temporal_coverage"), payload.get("spatial_resolution"),
                payload.get("temporal_resolution"), payload.get("integration_scope"),
                payload.get("evidence_level"),
                json.dumps(payload.get("variables", []), ensure_ascii=False),
                json.dumps(payload.get("units", {}), ensure_ascii=False),
                payload.get("updated_at"),
            ))
        with self.connect() as conn:
            conn.executemany(
                """INSERT INTO datasets (dataset_id, name, domain, state, institution,
                    license, geographic_coverage, temporal_coverage,
                    spatial_resolution, temporal_resolution, integration_scope,
                    evidence_level, variables_json, units_json, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(dataset_id) DO UPDATE SET
                    name=excluded.name, domain=excluded.domain,
                    state=excluded.state, institution=excluded.institution,
                    license=excluded.license,
                    geographic_coverage=excluded.geographic_coverage,
                    temporal_coverage=excluded.temporal_coverage,
                    spatial_resolution=excluded.spatial_resolution,
                    temporal_resolution=excluded.temporal_resolution,
                    integration_scope=excluded.integration_scope,
                    evidence_level=excluded.evidence_level,
                    variables_json=excluded.variables_json,
                    units_json=excluded.units_json,
                    updated_at=excluded.updated_at""",
                rows,
            )
        return len(rows)

    def insert_observations(self, rows: Sequence[dict[str, Any]]) -> int:
        if not rows:
            return 0
        columns = ("dataset_id", "dataset_version", "source_id", "variable", "unit",
                   "value", "time_utc", "time_local", "period_start", "period_end",
                   "frequency", "aggregation", "evidence_class", "latitude",
                   "longitude", "cell_support", "territory_id", "quality_flag")
        payload = [tuple(r.get(c) for c in columns) for r in rows]
        with self.connect() as conn:
            first_id = conn.execute(
                "SELECT COALESCE(MAX(observation_id), 0) + 1 FROM observations"
            ).fetchone()[0]
            conn.executemany(
                f"INSERT INTO observations ({','.join(columns)}) "
                f"VALUES ({','.join('?' * len(columns))})", payload)
            if self._has_rtree(conn) or _try_rtree(conn):
                ids = conn.execute(
                    "SELECT observation_id, longitude, latitude FROM observations "
                    "WHERE observation_id >= ?", (first_id,)).fetchall()
                conn.executemany(
                    "INSERT OR REPLACE INTO observations_rtree "
                    "(id, minlon, maxlon, minlat, maxlat) VALUES (?,?,?,?,?)",
                    [(r[0], r[1], r[1], r[2], r[2]) for r in ids
                     if r[1] is not None and r[2] is not None])
        return len(rows)

    def insert_occurrences(self, rows: Sequence[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """INSERT OR IGNORE INTO occurrences
                   (occurrence_id, dataset_id, taxon, latitude, longitude,
                    event_date, basis_of_record, coordinate_uncertainty_m,
                    issues_json, territory_id, quality_flag)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                [(r["occurrence_id"], r["dataset_id"], r["taxon"],
                  r["latitude"], r["longitude"], r.get("event_date"),
                  r.get("basis_of_record"), r.get("coordinate_uncertainty_m"),
                  json.dumps(r.get("issues", []), ensure_ascii=False),
                  r.get("territory_id"), r.get("quality_flag", "ok"))
                 for r in rows])
        return len(rows)

    def insert_territories(self, entries: Iterable[Any]) -> int:
        rows = []
        for e in entries:
            payload = e.as_dict() if hasattr(e, "as_dict") else dict(e)
            rows.append((
                payload["territory_id"], payload["level"], payload["name"],
                payload["name_norm"], payload.get("parent_id"),
                payload.get("source_code"), payload.get("source_id"),
                1 if payload.get("official") else 0 if payload.get("official") is False else None,
                payload.get("area_km2"),
                json.dumps(payload.get("bbox"), ensure_ascii=False),
                json.dumps(payload.get("centroid"), ensure_ascii=False),
                json.dumps(payload.get("geometry"), ensure_ascii=False)
                if payload.get("geometry") else None,
                payload.get("geometry_ref"),
            ))
        with self.connect() as conn:
            conn.executemany(
                """INSERT INTO territories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(territory_id) DO UPDATE SET
                    name=excluded.name, name_norm=excluded.name_norm,
                    parent_id=excluded.parent_id, area_km2=excluded.area_km2,
                    bbox_json=excluded.bbox_json,
                    centroid_json=excluded.centroid_json,
                    geometry_geojson=excluded.geometry_geojson,
                    geometry_ref=excluded.geometry_ref""",
                rows)
        return len(rows)

    def insert_assets(self, rows: Iterable[dict[str, Any]]) -> int:
        rows = list(rows)
        with self.connect() as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO assets
                   (artifact_id, dataset_id, path, sha256, bytes, format, state,
                    manifest_path) VALUES (?,?,?,?,?,?,?,?)""",
                [(r["artifact_id"], r["dataset_id"], r["path"], r["sha256"],
                  r.get("bytes"), r.get("format"), r.get("state"),
                  r.get("manifest_path")) for r in rows])
        return len(rows)

    def insert_quality_report(self, report: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO quality_reports
                   (report_id, dataset_id, status, checks_run, report_json, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (report["report_id"], report["dataset_id"], report["status"],
                 report.get("checks_run", 0),
                 json.dumps(report, ensure_ascii=False),
                 report.get("generated_at")))

    # --- consultas ---------------------------------------------------------
    def datasets(self, *, domain: str | None = None, state: str | None = None,
                 limit: int = 200, offset: int = 0) -> QueryResult:
        where, params = [], []
        if domain:
            where.append("domain = ?")
            params.append(domain.upper())
        if state:
            where.append("state = ?")
            params.append(state.upper())
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM datasets {clause}",
                                 params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM datasets {clause} ORDER BY dataset_id LIMIT ? OFFSET ?",
                [*params, limit, offset]).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["variables"] = json.loads(item.pop("variables_json") or "[]")
            item["units"] = json.loads(item.pop("units_json") or "{}")
            out.append(item)
        return QueryResult(out, int(total), limit, offset,
                           {"domain": domain, "state": state})

    def observation_query(self, *, dataset_id: str | None = None,
                          variable: str | None = None,
                          bbox: tuple[float, float, float, float] | None = None,
                          territory_id: str | None = None,
                          start: str | None = None, end: str | None = None,
                          limit: int = 500, offset: int = 0) -> QueryResult:
        where: list[str] = []
        params: list[Any] = []
        if not self.path.exists():
            return QueryResult([], 0, limit, offset, {},
                               note="base no construida")
        if dataset_id:
            where.append("o.dataset_id = ?")
            params.append(dataset_id)
        if variable:
            where.append("o.variable = ?")
            params.append(variable)
        if territory_id:
            where.append("o.territory_id = ?")
            params.append(territory_id)
        # El filtro se aplica a la fecha de referencia local, no al instante
        # UTC: una observación del 1 de enero (UTC−6) empieza el 31 de diciembre
        # en UTC y no debe desaparecer de una consulta por el año local.
        # `end` es inclusivo por día calendario.
        if start:
            where.append("o.time_local >= ?")
            params.append(start)
        if end:
            from datetime import date, timedelta

            end_day = date.fromisoformat(end[:10])
            where.append("o.time_local < ?")
            params.append((end_day + timedelta(days=1)).isoformat())
        with self.connect() as conn:
            if bbox:
                west, south, east, north = bbox
                if self._has_rtree(conn):
                    where.append(
                        "o.observation_id IN (SELECT id FROM observations_rtree "
                        "WHERE minlon >= ? AND maxlon <= ? AND minlat >= ? "
                        "AND maxlat <= ?)")
                    params.extend([west, east, south, north])
                else:
                    where.append("o.longitude BETWEEN ? AND ? "
                                 "AND o.latitude BETWEEN ? AND ?")
                    params.extend([west, east, south, north])
            clause = f"WHERE {' AND '.join(where)}" if where else ""
            total = conn.execute(
                f"SELECT COUNT(*) FROM observations o {clause}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"""SELECT o.* FROM observations o {clause}
                    ORDER BY o.dataset_id, o.variable, o.time_utc
                    LIMIT ? OFFSET ?""", [*params, limit, offset]).fetchall()
        return QueryResult([dict(r) for r in rows], int(total), limit, offset,
                           {"dataset_id": dataset_id, "variable": variable,
                            "bbox": list(bbox) if bbox else None,
                            "territory_id": territory_id},
                           note="las observaciones integradas conservan su clase "
                                "de evidencia; no se presentan como medición de "
                                "campo si no lo son")

    def occurrences(self, *, bbox: tuple[float, float, float, float] | None = None,
                    taxon: str | None = None, dataset_id: str | None = None,
                    limit: int = 500, offset: int = 0) -> QueryResult:
        if not self.path.exists():
            return QueryResult([], 0, limit, offset, {}, note="base no construida")
        where, params = [], []
        if bbox:
            west, south, east, north = bbox
            where.append("longitude BETWEEN ? AND ? AND latitude BETWEEN ? AND ?")
            params.extend([west, east, south, north])
        if taxon:
            where.append("taxon LIKE ?")
            params.append(f"%{taxon}%")
        if dataset_id:
            where.append("dataset_id = ?")
            params.append(dataset_id)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM occurrences {clause}",
                                 params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM occurrences {clause} ORDER BY occurrence_id "
                "LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
        return QueryResult([dict(r) for r in rows], int(total), limit, offset,
                           {"bbox": list(bbox) if bbox else None,
                            "taxon": taxon})

    def territory(self, territory_id: str) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM territories WHERE territory_id = ?",
                               (territory_id,)).fetchone()
            if row is None:
                return None
            children = conn.execute(
                "SELECT territory_id, level, name FROM territories "
                "WHERE parent_id = ? ORDER BY name", (territory_id,)).fetchall()
        item = dict(row)
        item["bbox"] = json.loads(item.pop("bbox_json") or "null")
        item["centroid"] = json.loads(item.pop("centroid_json") or "null")
        geometry = item.pop("geometry_geojson")
        item["geometry"] = json.loads(geometry) if geometry else None
        item["official"] = bool(item["official"]) if item["official"] is not None else None
        item["children"] = [dict(c) for c in children]
        return item

    def territories(self, *, level: str | None = None,
                    parent_id: str | None = None,
                    limit: int = 500, offset: int = 0) -> QueryResult:
        if not self.path.exists():
            return QueryResult([], 0, limit, offset, {}, note="base no construida")
        where, params = [], []
        if level:
            where.append("level = ?")
            params.append(level)
        if parent_id:
            where.append("parent_id = ?")
            params.append(parent_id)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM territories {clause}",
                                 params).fetchone()[0]
            rows = conn.execute(
                "SELECT territory_id, level, name, parent_id, area_km2, official "
                f"FROM territories {clause} ORDER BY name LIMIT ? OFFSET ?",
                [*params, limit, offset]).fetchall()
        return QueryResult([dict(r) for r in rows], int(total), limit, offset,
                           {"level": level, "parent_id": parent_id})

    def assets(self, dataset_id: str) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM assets WHERE dataset_id = ? ORDER BY artifact_id",
                (dataset_id,)).fetchall()
        return [dict(r) for r in rows]

    def quality_reports(self, *, dataset_id: str | None = None,
                        limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.connect() as conn:
            if dataset_id:
                rows = conn.execute(
                    "SELECT report_json FROM quality_reports WHERE dataset_id = ? "
                    "ORDER BY created_at DESC LIMIT ?", (dataset_id, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT report_json FROM quality_reports "
                    "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def counts_by_dataset(self) -> dict[str, int]:
        if not self.path.exists():
            return {}
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT dataset_id, COUNT(*) AS n FROM observations "
                "GROUP BY dataset_id ORDER BY dataset_id").fetchall()
        return {r["dataset_id"]: int(r["n"]) for r in rows}


def _try_rtree(conn: sqlite3.Connection) -> bool:
    """Activa índice espacial R-tree si SQLite lo trae compilado."""
    try:
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS observations_rtree "
            "USING rtree(id, minlon, maxlon, minlat, maxlat)")
        if conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]:
            conn.execute(
                """INSERT OR REPLACE INTO observations_rtree
                   (id, minlon, maxlon, minlat, maxlat)
                   SELECT observation_id, longitude, longitude, latitude, latitude
                   FROM observations
                   WHERE longitude IS NOT NULL AND latitude IS NOT NULL""")
        return True
    except sqlite3.OperationalError:
        return False


def build_store(path: Path | str) -> DataStore:
    store = DataStore(path)
    store.init_schema()
    return store
