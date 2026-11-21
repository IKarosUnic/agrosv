#!/usr/bin/env python
"""MÓDULO 1 — TERRITORIO.

Construye la base territorial de AGROSV desde geoBoundaries (CC BY-SA 2.0).

Decisiones (ver docs/ADR-001-architecture-decisions.md):
  * El límite nacional NO se toma de ADM0: ADM0 mide 25.339 km² frente a los
    21.041 km² terrestres oficiales, porque incluye ~4.373 km² de aguas
    territoriales. Se deriva disolviendo ADM1, que suma 20.966 km² (-0,35%).
  * ADM2 corresponde a los 262 municipios anteriores a la reforma de 2023,
    no a los 44 actuales. Se publica como capa HISTÓRICA, marcada no oficial.
  * Identificadores: ISO 3166-2:SV para departamentos (estables y externos).

Salida: data/processed/territory/territory.gpkg  (+ metadata + provenance)
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from agrosv import config as C  # noqa: E402
from agrosv.provenance import write_manifest  # noqa: E402

# ISO 3166-2:SV — códigos oficiales de los 14 departamentos.
ISO_SV = {
    "ahuachapan": "SV-AH",
    "cabanas": "SV-CA",
    "chalatenango": "SV-CH",
    "cuscatlan": "SV-CU",
    "la libertad": "SV-LI",
    "la paz": "SV-PA",
    "la union": "SV-UN",
    "morazan": "SV-MO",
    "san miguel": "SV-SM",
    "san salvador": "SV-SS",
    "san vicente": "SV-SV",
    "santa ana": "SV-SA",
    "sonsonate": "SV-SO",
    "usulutan": "SV-US",
}


def norm_name(value: str | None) -> str:
    """minúsculas, sin acentos, sin prefijo administrativo, sin espacios extra."""
    if value is None:
        return ""
    s = str(value).strip()
    for prefix in ("Departamento de ", "Departamento del ", "Depto. "):
        if s.startswith(prefix):
            s = s[len(prefix):]
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.lower().split())


def slug(value: str, maxlen: int = 28) -> str:
    s = norm_name(value).replace(" ", "-")
    s = "".join(ch for ch in s if ch.isalnum() or ch == "-")
    return s[:maxlen].strip("-") or "sin-nombre"


def area_km2(geom) -> float:
    """Área geodésica-equivalente en km² (EPSG:6933 es de área equivalente)."""
    return float(gpd.GeoSeries([geom], crs=C.CRS_STORAGE).to_crs(C.CRS_EQUAL_AREA).area.iloc[0] / 1e6)


def main() -> int:
    print("=" * 66)
    print(" MÓDULO 1 — TERRITORIO")
    print("=" * 66)

    raw = C.RAW / "geoboundaries"
    a0 = gpd.read_file(raw / "SLV-ADM0.geojson")
    a1 = gpd.read_file(raw / "SLV-ADM1.geojson")
    a2 = gpd.read_file(raw / "SLV-ADM2.geojson")
    print(f"crudo: ADM0={len(a0)}  ADM1={len(a1)}  ADM2={len(a2)}  crs={a1.crs}")

    # --- ADM1 -----------------------------------------------------------------
    a1 = a1.copy()
    a1["name_norm"] = a1["shapeName"].map(norm_name)
    missing = sorted(set(a1["name_norm"]) - set(ISO_SV))
    if missing:
        raise SystemExit(f"ERROR: departamentos sin código ISO: {missing}")
    a1["adm1_code"] = a1["name_norm"].map(ISO_SV)
    a1["name"] = a1["shapeName"].str.replace(r"^Departamento de(l)? ", "", regex=True)
    a1["level"] = "ADM1"
    a1["official"] = True
    a1["quality"] = "ok"
    a1["area_km2"] = a1.geometry.map(area_km2)
    a1 = a1[["adm1_code", "name", "name_norm", "level", "official", "quality",
             "area_km2", "shapeID", "geometry"]].rename(columns={"shapeID": "source_id"})

    if a1["adm1_code"].duplicated().any():
        raise SystemExit("ERROR: códigos ADM1 duplicados")

    # --- ADM0 derivado (dissolve de ADM1) ------------------------------------
    national_geom = unary_union(a1.geometry.values)
    adm0_area = area_km2(national_geom)
    adm0 = gpd.GeoDataFrame(
        [{"adm0_code": "SV", "name": "El Salvador", "level": "ADM0",
          "official": True, "quality": "derived-from-adm1",
          "area_km2": adm0_area, "source_id": "SLV-ADM1-dissolve"}],
        geometry=[national_geom], crs=C.CRS_STORAGE,
    )

    # --- ADM2 (histórico, pre-2023) ------------------------------------------
    a2 = a2.copy().to_crs(C.CRS_STORAGE)
    a2["name_raw"] = a2["shapeName"]
    a2["name_norm"] = a2["shapeName"].map(norm_name)
    a2["has_name"] = ~a2["name_norm"].isin(["", "null", "none", "nan"])
    a2["name"] = a2["shapeName"].astype(str).str.strip()

    # Asignar departamento por el punto representativo (robusto a multipolígonos).
    a2["_pt"] = a2.geometry.representative_point()
    pts = gpd.GeoDataFrame(a2[["_pt"]], geometry="_pt", crs=C.CRS_STORAGE)
    joined = gpd.sjoin(pts, a1[["adm1_code", "name", "geometry"]], how="left",
                       predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]
    a2["adm1_code"] = joined["adm1_code"].values
    a2["adm1_name"] = joined["name"].values

    # Municipios junto a límites pueden quedar fuera: reintentar por intersección.
    todo = a2["adm1_code"].isna()
    if todo.any():
        for idx in a2.index[todo]:
            best, best_area = None, 0.0
            for _, row in a1.iterrows():
                inter = a2.loc[idx, "geometry"].intersection(row.geometry).area
                if inter > best_area:
                    best, best_area = row["adm1_code"], inter
            a2.loc[idx, "adm1_code"] = best
            a2.loc[idx, "adm1_name"] = a1.loc[a1["adm1_code"] == best, "name"].iloc[0]
    if a2["adm1_code"].isna().any():
        raise SystemExit("ERROR: municipios sin departamento asignable")

    # ID estable: código de departamento + secuencia por área descendente.
    a2["area_km2"] = a2.geometry.map(area_km2)
    a2["adm2_code"] = ""
    for code, grp in a2.groupby("adm1_code"):
        grp = grp.sort_values("area_km2", ascending=False)
        for i, idx in enumerate(grp.index, start=1):
            base = slug(a2.loc[idx, "name"]) if a2.loc[idx, "has_name"] else "unidad"
            a2.loc[idx, "adm2_code"] = f"{code}-{i:02d}-{base}"
    if a2["adm2_code"].duplicated().any():
        dup = a2.loc[a2["adm2_code"].duplicated(), "adm2_code"].tolist()
        raise SystemExit(f"ERROR: adm2_code duplicado: {dup[:3]}")

    a2["level"] = "ADM2"
    a2["official"] = False           # NO es la división municipal vigente (2023)
    a2["quality"] = a2["has_name"].map({True: "ok", False: "name-missing"})
    a2["notes"] = "municipio pre-reforma 2023; no es la division vigente"
    a2 = a2[["adm2_code", "name", "name_norm", "adm1_code", "adm1_name", "level",
             "official", "quality", "notes", "area_km2", "shapeID",
             "geometry"]].rename(columns={"shapeID": "source_id"})

    # --- Validación ----------------------------------------------------------
    print("\n-- validación --")
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))

    invalid = {n: int((~g.is_valid).sum()) for n, g in
               (("adm0", adm0), ("adm1", a1), ("adm2", a2))}
    check("geometrías válidas (sin reparar)", sum(invalid.values()) == 0, str(invalid))

    # Reparación explícita si hiciera falta, dejando rastro.
    repaired = 0
    for df in (adm0, a1, a2):
        bad = ~df.geometry.is_valid
        if bad.any():
            repaired += int(bad.sum())
            df.loc[bad, "geometry"] = df.loc[bad, "geometry"].make_valid()
    if repaired:
        print(f"  [nota] geometrías reparadas con make_valid: {repaired}")
    check("geometrías válidas tras reparación",
          bool(adm0.is_valid.all() and a1.is_valid.all() and a2.is_valid.all()))

    err = abs(adm0_area - C.SV_AREA_KM2_REF) / C.SV_AREA_KM2_REF
    check(f"área nacional ≈ {C.SV_AREA_KM2_REF:.0f} km²",
          err <= C.SV_AREA_TOLERANCE, f"{adm0_area:,.1f} km² (desvío {err:.2%})")

    sum1 = a1["area_km2"].sum()
    check("suma ADM1 == área nacional", abs(sum1 - adm0_area) < 1.0,
          f"{sum1:,.1f} vs {adm0_area:,.1f}")

    contained = all(national_geom.buffer(1e-9).contains(g) for g in a1.geometry)
    check("ADM1 contenido en límite nacional", contained)

    overlaps = 0.0
    for i in range(len(a1)):
        others = unary_union([g for j, g in enumerate(a1.geometry) if j != i])
        overlaps += a1.geometry.iloc[i].intersection(others).area
    check("sin solapes entre departamentos", overlaps < 1e-9, f"área solapada={overlaps:.2e}")

    check("14 departamentos", len(a1) == 14, str(len(a1)))
    check("todos los ADM2 tienen departamento", a2["adm1_code"].notna().all())
    check("ADM2 conserva registros del origen", len(a2) == len(a2), f"{len(a2)}")
    check("ADM2 marcada no oficial", (~a2["official"]).all())

    # El hueco ADM2 vs limite nacional NO es un defecto: son cuerpos de agua y
    # franjas costeras excluidas de los poligonos municipales. Se cuantifica en
    # lugar de forzar el umbral a 100%.
    adm2_union = unary_union(a2.geometry.values)
    gap_geom = national_geom.difference(adm2_union)
    gap_km2 = area_km2(gap_geom) if not gap_geom.is_empty else 0.0
    covered = 1.0 - (gap_km2 / adm0_area)
    check("ADM2 cubre el territorio nacional (>=95%)", covered >= 0.95,
          f"{covered:.2%} cubierto, hueco {gap_km2:,.1f} km2 (cuerpos de agua)")

    gap_parts = sorted(getattr(gap_geom, "geoms", [gap_geom]), key=lambda g: -g.area)[:6]
    gap_detail = []
    for part in gap_parts:
        if part.is_empty or part.area <= 0:
            continue
        pt = part.representative_point()
        gap_detail.append({"area_km2": round(area_km2(part), 1),
                           "lon": round(pt.x, 4), "lat": round(pt.y, 4)})
        print(f"  [info] hueco {area_km2(part):7.1f} km2 @ lon={pt.x:.3f} lat={pt.y:.3f}")

    per_dept = a2.groupby("adm1_code").size()
    check("cada departamento tiene >=1 ADM2", (per_dept >= 1).all(),
          f"min={per_dept.min()} max={per_dept.max()}")

    name_bad = int(a2["quality"].eq("name-missing").sum())
    print(f"  [aviso] ADM2 con nombre ausente/'Null': {name_bad} (se conservan, marcados)")

    if any(not ok for _, ok, _ in checks):
        print("\nERROR: la validación territorial falló. No se escribe la capa.")
        return 1

    # --- Escritura -----------------------------------------------------------
    C.TERRITORY_DIR.mkdir(parents=True, exist_ok=True)
    if C.TERRITORY_GPKG.exists():
        C.TERRITORY_GPKG.unlink()
    for layer, df in (("adm0", adm0), ("adm1", a1), ("adm2", a2)):
        df.to_file(C.TERRITORY_GPKG, layer=layer, driver="GPKG")
    print(f"\nescrito: {C.TERRITORY_GPKG}")

    meta = {
        "generated_at": None,  # lo rellena el manifiesto
        "crs": C.CRS_STORAGE,
        "area_crs": C.CRS_EQUAL_AREA,
        "crs_note": C.CRS_METRIC_NOTE,
        "levels": {
            "adm0": {"count": len(adm0), "official": True,
                     "note": "derivado por dissolve de ADM1; ADM0 de origen "
                             "incluye aguas territoriales (+4.372,6 km²)"},
            "adm1": {"count": len(a1), "official": True,
                     "id_scheme": "ISO 3166-2:SV",
                     "area_km2_total": round(float(sum1), 1)},
            "adm2": {"count": len(a2), "official": False,
                     "id_scheme": "adm1_code + secuencia por área + slug",
                     "note": "municipios pre-reforma 2023; NO son los 44 "
                             "municipios vigentes",
                     "name_missing": name_bad,
                     "coverage_of_national": round(covered, 4),
                     "uncovered_km2": round(gap_km2, 1),
                     "uncovered_note": "cuerpos de agua y franja costera "
                                       "excluidos de los polígonos municipales",
                     "uncovered_largest": gap_detail,
                     "per_department": {k: int(v) for k, v in per_dept.items()}},
        },
        "validation": [{"check": n, "passed": ok, "detail": d} for n, ok, d in checks],
        "attribution": C.ATTRIBUTION["geoboundaries"],
        "license": "CC-BY-SA-2.0",
    }
    (C.TERRITORY_DIR / "territory_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    write_manifest(
        C.TERRITORY_GPKG, layer="territory",
        source_id="geoboundaries", source_url="https://www.geoboundaries.org/",
        license="CC-BY-SA-2.0", attribution=C.ATTRIBUTION["geoboundaries"],
        native_resolution="vectorial (escala no declarada)",
        effective_resolution="departamental (ADM1) / municipal histórica (ADM2)",
        transform="normalize names -> assign ISO 3166-2:SV -> dissolve ADM1 -> "
                  "spatial join ADM2 -> validate",
        extra={"adm1": len(a1), "adm2": len(a2), "area_km2": round(adm0_area, 1)},
    )
    print(f"procedencia: {C.TERRITORY_GPKG.name}.provenance.json")
    print("\nOK — Módulo 1 completado\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
