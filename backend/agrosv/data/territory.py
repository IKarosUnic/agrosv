"""AGROSV — sistema de referencia territorial nacional (Fase 4, §6).

Objetivo: que ninguna unión dependa del nombre de un lugar. Cada unidad tiene un
identificador estable, un nivel explícito y una procedencia. Los nombres son
atributos de búsqueda, no claves.

Qué cubre hoy, con evidencia:

    country              ADM0 del GeoPackage de Fase 1 (derivado de ADM1)
    department           ADM1, 14 unidades, códigos ISO 3166-2:SV
    municipality_historic ADM2, 272 polígonos pre-reforma 2023 (NO oficiales)
    municipality_2023    44 municipios vigentes — SIN capa en este repositorio
    district             262 distritos — SIN capa y SIN lista oficial verificada
    basin/subbasin/microbasin   sin delimitación propia verificada
    protected_area       sin capa integrada
    agricultural_unit    unidad de análisis AGROSV (derivada, no administrativa)
    parcel               solo con acceso legal; nunca se inventa

Este módulo **no crea límites**. Declara los niveles ausentes como ausentes y
bloquea las uniones que los necesiten (`CrosswalkTable.incomplete`). La
diferencia entre división administrativa, hidrográfica y agrícola se documenta
en `docs/phase4/TERRITORIAL_REFERENCE_SYSTEM.md`: una cuenca no respeta
municipios y una unidad agrícola no es una parcela.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

LEVELS: dict[str, dict[str, Any]] = {
    "country": {"id_prefix": "SV", "parent": None, "official_required": True,
                "description": "El Salvador (ADM0 derivado de ADM1)"},
    "department": {"id_prefix": "SV-ADM1", "parent": "country",
                   "official_required": True,
                   "description": "14 departamentos, ISO 3166-2:SV"},
    "municipality_2023": {"id_prefix": "SV-ADM2", "parent": "department",
                          "official_required": True,
                          "description": "44 municipios vigentes desde 2023"},
    "municipality_historic": {"id_prefix": "SV-ADM2H", "parent": "department",
                              "official_required": False,
                              "description": "272 municipios pre-reforma 2023"},
    "district": {"id_prefix": "SV-DIS", "parent": "municipality_2023",
                 "official_required": True,
                 "description": "262 distritos (unidad censal)"},
    "basin": {"id_prefix": "SV-BAS", "parent": "country",
              "official_required": False,
              "description": "cuenca hidrográfica; no coincide con ADM"},
    "subbasin": {"id_prefix": "SV-SUB", "parent": "basin",
                 "official_required": False,
                 "description": "subcuenca (p. ej. Pfafstetter > 10 km²)"},
    "microbasin": {"id_prefix": "SV-MIC", "parent": "subbasin",
                   "official_required": False,
                   "description": "microcuenca; delimitación local"},
    "protected_area": {"id_prefix": "SV-AP", "parent": "country",
                       "official_required": False,
                       "description": "área natural protegida"},
    "agricultural_unit": {"id_prefix": "SV-AGU", "parent": "department",
                          "official_required": False,
                          "description": "unidad de análisis agrícola AGROSV "
                                         "(derivada; no es división oficial)"},
    "parcel": {"id_prefix": "SV-PAR", "parent": "district",
               "official_required": False,
               "description": "parcela; requiere información legalmente accesible"},
}


class TerritoryError(ValueError):
    pass


class AmbiguousTerritoryError(TerritoryError):
    def __init__(self, query: str, candidates: list[str]) -> None:
        super().__init__(
            f"'{query}' es ambiguo: {len(candidates)} candidatos {candidates[:10]}"
        )
        self.candidates = candidates


class CrosswalkIncompleteError(TerritoryError):
    def __init__(self, message: str, *, unmapped: Iterable[str] = ()) -> None:
        super().__init__(message)
        self.unmapped = list(unmapped)


def normalize_name(name: str) -> str:
    """Normaliza para búsqueda; nunca sustituye al nombre canónico.

    Elimina acentos y diacríticos, por lo que «Cañas» y «Canas» colisionan. Eso
    es aceptable para *buscar* y peligroso para *identificar*: la identidad la
    da `territory_id`.
    """
    if not name:
        return ""
    norm = unicodedata.normalize("NFKD", str(name))
    norm = "".join(ch for ch in norm if not unicodedata.combining(ch))
    norm = norm.lower().replace("ñ", "n")
    norm = re.sub(r"[^a-z0-9]+", " ", norm)
    return re.sub(r"\s+", " ", norm).strip()


def _slug(text: str) -> str:
    norm = normalize_name(text).replace(" ", "-")
    return re.sub(r"-{2,}", "-", norm).strip("-")


@dataclass
class TerritoryEntry:
    territory_id: str
    level: str
    name: str
    source_code: str
    source_id: str
    parent_id: str | None = None
    official: bool | None = None
    area_km2: float | None = None
    bbox: list[float] | None = None
    centroid: list[float] | None = None
    geometry_ref: str | None = None
    geometry: dict[str, Any] | None = None
    id_basis: str = "source_code"
    stability: str = "stable"
    aliases: list[str] = field(default_factory=list)

    @property
    def name_norm(self) -> str:
        return normalize_name(self.name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "territory_id": self.territory_id,
            "level": self.level,
            "name": self.name,
            "name_norm": self.name_norm,
            "source_code": self.source_code,
            "source_id": self.source_id,
            "parent_id": self.parent_id,
            "official": self.official,
            "area_km2": self.area_km2,
            "bbox": self.bbox,
            "centroid": self.centroid,
            "geometry_ref": self.geometry_ref,
            "geometry": self.geometry,
            "id_basis": self.id_basis,
            "stability": self.stability,
            "aliases": self.aliases,
        }


def make_territory_id(level: str, source_code: str, name: str) -> tuple[str, str, str]:
    """Devuelve (territory_id, id_basis, stability).

    Se prefiere el código oficial. Si no existe, se usa un hash del nombre, que
    es estable frente a variantes ortográficas pero **no** frente a cambios de
    nombre; en ese caso `stability="conditional"`.
    """
    if level not in LEVELS:
        raise TerritoryError(f"nivel desconocido: {level}; use {sorted(LEVELS)}")
    prefix = LEVELS[level]["id_prefix"]
    code = (source_code or "").strip()
    if level == "country":
        return "SV", "official_code", "stable"
    if code:
        core = code
        if core.upper().startswith("SV-"):
            core = core[3:]
        if level in {"department"}:
            return f"{prefix}-{core.upper()}", "official_code", "stable"
        return f"{prefix}-{_slug(core)}", "source_code", "stable"
    digest = hashlib.sha256(f"{level}:{normalize_name(name)}".encode()).hexdigest()[:8]
    return f"{prefix}-X{digest.upper()}", "name_hash", "conditional"


class TerritorialIndex:
    """Índice de unidades con identificadores estables y búsqueda sin ambigüedad."""

    def __init__(self, entries: Iterable[TerritoryEntry] = ()) -> None:
        self._entries: dict[str, TerritoryEntry] = {}
        for entry in entries:
            if entry.territory_id in self._entries:
                raise TerritoryError(f"territory_id duplicado: {entry.territory_id}")
            self._entries[entry.territory_id] = entry
        self._by_name: dict[str, list[str]] = {}
        for entry in self._entries.values():
            for label in {entry.name_norm, *map(normalize_name, entry.aliases)}:
                if label:
                    self._by_name.setdefault(label, []).append(entry.territory_id)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(sorted(self._entries.values(),
                           key=lambda e: (e.level, e.territory_id)))

    def get(self, territory_id: str) -> TerritoryEntry:
        try:
            return self._entries[territory_id]
        except KeyError:
            raise TerritoryError(f"territorio no encontrado: {territory_id}") from None

    def by_level(self, level: str) -> list[TerritoryEntry]:
        return [e for e in self if e.level == level]

    def children(self, territory_id: str) -> list[TerritoryEntry]:
        return [e for e in self if e.parent_id == territory_id]

    def ancestors(self, territory_id: str) -> list[TerritoryEntry]:
        chain: list[TerritoryEntry] = []
        current = self.get(territory_id)
        while current.parent_id:
            current = self.get(current.parent_id)
            chain.append(current)
        return chain

    def resolve(self, query: str, *, level: str | None = None) -> TerritoryEntry:
        """Busca por id, código fuente o nombre normalizado. Nunca adivina."""
        q = query.strip()
        if q in self._entries:
            entry = self._entries[q]
            if level and entry.level != level:
                raise TerritoryError(
                    f"{q} es nivel {entry.level}, no {level}"
                )
            return entry
        by_code = [e for e in self
                   if e.source_code.lower() == q.lower()
                   and (level is None or e.level == level)]
        if len(by_code) == 1:
            return by_code[0]
        hits = [self._entries[tid] for tid in self._by_name.get(normalize_name(q), [])
                if level is None or self._entries[tid].level == level]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise AmbiguousTerritoryError(q, [e.territory_id for e in hits])
        raise TerritoryError(f"territorio no encontrado: {query!r} (nivel={level})")

    # --- construcción ------------------------------------------------------
    @classmethod
    def from_geopackage(cls, path: Path | str, *, geometry: bool = True,
                        levels: dict[str, str] | None = None) -> "TerritorialIndex":
        """Carga ADM0/ADM1/ADM2 del GeoPackage territorial de Fase 1."""
        import geopandas as gpd

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        layers = levels or {"adm0": "country", "adm1": "department",
                            "adm2": "municipality_historic"}
        entries: list[TerritoryEntry] = []
        parent_by_code: dict[str, str] = {}
        for layer, level in layers.items():
            try:
                gdf = gpd.read_file(path, layer=layer)
            except Exception:  # noqa: BLE001 — capa opcional ausente
                continue
            code_col = next((c for c in gdf.columns if c.endswith("_code")), None)
            for _, row in gdf.iterrows():
                source_code = str(row[code_col]) if code_col else ""
                tid, basis, stability = make_territory_id(
                    level, source_code, str(row.get("name", "")))
                parent_id = None
                if level == "department":
                    parent_id = "SV"
                elif level == "municipality_historic":
                    parent_code = str(row.get("adm1_code", ""))
                    parent_id = parent_by_code.get(parent_code)
                geom_json = None
                bbox = centroid = None
                g = row.geometry
                if g is not None and not g.is_empty:
                    bbox = [round(v, 6) for v in g.bounds]
                    c = g.centroid
                    centroid = [round(c.x, 6), round(c.y, 6)]
                    if geometry and level != "municipality_historic":
                        geom_json = json.loads(gpd.GeoSeries([g]).to_json())[
                            "features"][0]["geometry"]
                area = row.get("area_km2")
                entry = TerritoryEntry(
                    territory_id=tid, level=level, name=str(row.get("name", "")),
                    source_code=source_code, source_id=str(row.get("source_id", "")),
                    parent_id=parent_id,
                    official=bool(row["official"]) if "official" in gdf.columns
                    and row["official"] is not None else None,
                    area_km2=round(float(area), 4) if area is not None else None,
                    bbox=bbox, centroid=centroid,
                    geometry_ref=(f"{path.as_posix()}#{layer}={source_code}"
                                  if level == "municipality_historic" else None),
                    geometry=geom_json, id_basis=basis, stability=stability,
                )
                entries.append(entry)
                if level == "department":
                    parent_by_code[source_code] = tid
        return cls(entries)

    # --- cobertura ---------------------------------------------------------
    def coverage(self) -> dict[str, Any]:
        present = {e.level for e in self}
        report = {}
        for level, spec in LEVELS.items():
            units = [e for e in self if e.level == level]
            report[level] = {
                "present": level in present,
                "count": len(units),
                "official": (all(e.official for e in units)
                             if units else None),
                "id_prefix": spec["id_prefix"],
                "description": spec["description"],
                "geometry_embedded": sum(1 for e in units if e.geometry),
            }
        missing = [lv for lv, r in report.items() if not r["present"]]
        return {
            "levels": report,
            "missing_levels": missing,
            "note": ("un nivel ausente no se sintetiza: las uniones que lo "
                     "requieran quedan bloqueadas"),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 4,
            "levels": {k: v for k, v in LEVELS.items()},
            "coverage": self.coverage(),
            "territories": [e.as_dict() for e in self],
            "rule": ("territory_id es la clave; el nombre es solo un atributo "
                     "de búsqueda"),
        }

    def save(self, path: Path | str) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.as_dict(), indent=2, ensure_ascii=False),
                     encoding="utf-8")
        return p


class CrosswalkTable:
    """Correspondencia entre dos niveles (p. ej. 272 históricos ↔ 44 vigentes).

    Mientras `status != COMPLETE`, `map()` lanza `CrosswalkIncompleteError`. Así
    es imposible unir el censo con la capa vieja «casi bien».
    """

    REQUIRED = ("source_level", "target_level", "status", "entries", "source_id")

    def __init__(self, payload: dict[str, Any]) -> None:
        missing = [k for k in self.REQUIRED if k not in payload]
        if missing:
            raise TerritoryError(f"tabla de correspondencia incompleta: faltan {missing}")
        self.payload = payload
        self.entries: list[dict[str, Any]] = payload.get("entries", [])
        self.status = str(payload.get("status", "INCOMPLETE")).upper()
        self._map: dict[str, str] = {}
        for entry in self.entries:
            if not entry.get("source") or not entry.get("target"):
                raise TerritoryError("entrada de correspondencia sin source/target")
            if entry["source"] in self._map:
                raise TerritoryError(
                    f"origen duplicado en correspondencia: {entry['source']}")
            self._map[entry["source"]] = entry["target"]

    @classmethod
    def load(cls, path: Path | str) -> "CrosswalkTable":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @property
    def complete(self) -> bool:
        return self.status == "COMPLETE"

    def map(self, source_id: str) -> str:
        if not self.complete:
            raise CrosswalkIncompleteError(
                f"correspondencia {self.payload['source_level']} -> "
                f"{self.payload['target_level']} en estado {self.status}: "
                "no se permite unir datos con una tabla incompleta"
            )
        try:
            return self._map[source_id]
        except KeyError:
            raise CrosswalkIncompleteError(
                f"sin correspondencia para {source_id}", unmapped=[source_id]
            ) from None

    def coverage(self, source_ids: Iterable[str]) -> dict[str, Any]:
        ids = list(source_ids)
        mapped = [i for i in ids if i in self._map]
        return {
            "source_level": self.payload["source_level"],
            "target_level": self.payload["target_level"],
            "status": self.status,
            "source_units": len(ids),
            "mapped": len(mapped),
            "unmapped": len(ids) - len(mapped),
            "unmapped_ids": [i for i in ids if i not in self._map][:50],
            "complete": self.complete,
            "usable_for_joins": self.complete and len(mapped) == len(ids),
        }


def assert_no_synthetic_boundaries(index: TerritorialIndex, *,
                                   required_levels: Iterable[str] = ()) -> None:
    """Falla si se intenta usar un nivel sin datos oficiales verificados."""
    coverage = index.coverage()["levels"]
    blocked = [lv for lv in required_levels if not coverage.get(lv, {}).get("present")]
    if blocked:
        raise TerritoryError(
            "niveles territoriales sin capa verificada: "
            f"{blocked}. No se generan límites por interpolación ni por nombre."
        )
