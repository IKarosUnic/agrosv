#!/usr/bin/env python
"""MÓDULO 3 — INFRAESTRUCTURA GEOGRÁFICA (OpenStreetMap).

Fuente: extracto de Geofabrik `el-salvador-latest.osm.pbf` (ODbL 1.0).
No se usa la API Overpass en tiempo de ejecución: el extracto se descarga una
vez, se hashea y queda auditado. `scripts/download_data.sh` reproduce la bajada.

Capas (data/processed/infrastructure/infrastructure.gpkg):
  roads                vías, clasificadas por jerarquía
  waterways            ríos, arroyos, canales, drenajes
  water_bodies         cuerpos de agua (polígonos)
  settlements          asentamientos (puntos `place`)
  infrastructure       puntos relevantes (salud, educación, energía, puertos…)
  power_lines          líneas eléctricas y ductos

Todas las capas se recortan al territorio nacional derivado de ADM1 en el
Módulo 1 (no al rectángulo envolvente): una vía que cruza la frontera no debe
atribuirse completa a El Salvador.

Licencia: la base derivada está sujeta a ODbL 1.0. Cualquier publicación debe
mantener la atribución «© OpenStreetMap contributors» y ofrecer la base
derivada bajo la misma licencia.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import geopandas as gpd  # noqa: E402
import osmium  # noqa: E402
import pandas as pd  # noqa: E402
import pyogrio  # noqa: E402
import shapely  # noqa: E402

from agrosv import config as C  # noqa: E402
from agrosv.provenance import sha256_file, write_manifest  # noqa: E402

PBF = C.RAW / "osm" / "el-salvador-latest.osm.pbf"

# Jerarquía vial. El orden importa: la primera coincidencia gana.
ROAD_CLASSES = {
    "motorway": "arterial", "trunk": "arterial", "primary": "arterial",
    "motorway_link": "arterial", "trunk_link": "arterial",
    "primary_link": "arterial",
    "secondary": "colectora", "tertiary": "colectora",
    "secondary_link": "colectora", "tertiary_link": "colectora",
    "unclassified": "local", "residential": "local",
    "living_street": "local", "road": "local",
    "service": "servicio", "track": "pista",
    "path": "senda", "footway": "senda", "cycleway": "senda",
    "steps": "senda", "bridleway": "senda",
}
WATERWAY_CLASSES = {"river", "stream", "canal", "drain", "ditch", "tidal_channel"}
WATER_AREAS = {"water", "reservoir", "basin", "riverbank", "lagoon", "lake",
               "pond", "river", "stream", "canal"}

# Puntos de infraestructura relevante para agricultura y logística.
POINT_RULES = {
    "amenity": {
        "hospital": ("salud", "hospital"), "clinic": ("salud", "clínica"),
        "doctors": ("salud", "consultorio"),
        "school": ("educación", "escuela"), "college": ("educación", "colegio"),
        "university": ("educación", "universidad"),
        "marketplace": ("mercado", "mercado"),
        "fuel": ("energía", "combustible"),
        "police": ("seguridad", "policía"),
        "fire_station": ("seguridad", "bomberos"),
    },
    "aeroway": {"aerodrome": ("transporte", "aeródromo"),
                "helipad": ("transporte", "helipuerto")},
    "power": {"plant": ("energía", "planta"), "substation": ("energía", "subestación")},
    "man_made": {"water_tower": ("agua", "torre de agua"),
                 "water_works": ("agua", "planta potabilizadora"),
                 "wastewater_plant": ("agua", "planta de tratamiento")},
    "landuse": {"industrial": ("industria", "zona industrial"),
                "port": ("transporte", "puerto")},
    "harbour": {"yes": ("transporte", "puerto")},
}

_HSTORE = re.compile(r'"((?:[^"\\]|\\.)*)"=>"((?:[^"\\]|\\.)*)"')


def parse_hstore(text: str | None) -> dict[str, str]:
    """Convierte el campo `other_tags` de OGR (formato hstore) en un dict."""
    if not isinstance(text, str) or not text:
        return {}
    return {k.replace('\\"', '"'): v.replace('\\"', '"')
            for k, v in _HSTORE.findall(text)}


def classify(tags: dict[str, str]) -> tuple[str, str] | None:
    for key, rules in POINT_RULES.items():
        val = tags.get(key)
        if val and val in rules:
            return rules[val]
    return None


def read_lines(where: str, columns: list[str]) -> gpd.GeoDataFrame:
    return pyogrio.read_dataframe(PBF, layer="lines", columns=columns, where=where)


def clip_lines(gdf: gpd.GeoDataFrame, mask) -> gpd.GeoDataFrame:
    """Recorta geometrías al país SIN partir filas.

    `gpd.clip` hace overlay contra el polígono: un río que cruza un borde
    interno se convierte en varias filas con el mismo `osm_id` (se observaron
    4.984 → 15.148). Aquí se intersecta cada entidad y las partes resultantes
    se recomponen en una sola geometría MultiLineString.
    """
    geoms = []
    for geom in gdf.geometry.values:
        cut = geom.intersection(mask)
        if cut.is_empty:
            geoms.append(None)
            continue
        if cut.geom_type in ("LineString", "LinearRing"):
            geoms.append(shapely.LineString(cut))
        elif cut.geom_type == "MultiLineString":
            geoms.append(cut)
        else:
            parts = [p for p in shapely.get_parts(cut)
                     if p.geom_type in ("LineString", "LinearRing")]
            geoms.append(shapely.multilinestrings(parts) if parts else None)
    out = gdf.set_geometry(gpd.GeoSeries(geoms, index=gdf.index, crs=gdf.crs))
    return out[out.geometry.notna()].copy()


def clip_polygons(gdf: gpd.GeoDataFrame, mask) -> gpd.GeoDataFrame:
    geoms = []
    for geom in gdf.geometry.values:
        cut = geom.intersection(mask)
        if cut.is_empty:
            geoms.append(None)
            continue
        if cut.geom_type == "Polygon":
            geoms.append(shapely.MultiPolygon([cut]))
        elif cut.geom_type == "MultiPolygon":
            geoms.append(cut)
        else:
            parts = [p for p in shapely.get_parts(cut) if p.geom_type == "Polygon"]
            geoms.append(shapely.MultiPolygon(parts) if parts else None)
    out = gdf.set_geometry(gpd.GeoSeries(geoms, index=gdf.index, crs=gdf.crs))
    return out[out.geometry.notna()].copy()


def main() -> int:
    t0 = time.time()
    print("=" * 66)
    print(" MÓDULO 3 — INFRAESTRUCTURA (OpenStreetMap)")
    print("=" * 66)
    if not PBF.exists():
        print(f"ERROR: falta el extracto {PBF} (ver scripts/download_data.sh)")
        return 1
    C.INFRA_DIR.mkdir(parents=True, exist_ok=True)

    # Cabecera OSM: fecha del extracto, no la fecha de descarga.
    header = osmium.io.Reader(str(PBF)).header()
    osm_timestamp = header.get("timestamp")
    print(f"extracto OSM: {PBF.name}  {PBF.stat().st_size/1e6:.1f} MB  "
          f"timestamp={osm_timestamp}")

    territory = gpd.read_file(C.TERRITORY_GPKG, layer="adm1")
    national = territory.union_all()

    # --- Red vial y cursos de agua ------------------------------------------
    print("\n-- vías y cursos de agua --")
    lines = read_lines(
        '"highway" IS NOT NULL OR "waterway" IS NOT NULL '
        'OR "other_tags" LIKE \'%"power"=>%\' ',
        ["osm_id", "name", "highway", "waterway", "other_tags"],
    )
    lines["osm_id"] = lines["osm_id"].astype("int64")
    lines["tags"] = lines["other_tags"].map(parse_hstore)
    lines = lines.drop(columns=["other_tags"])

    roads = lines[lines["highway"].notna()].copy()
    roads["road_class"] = roads["highway"].map(ROAD_CLASSES).fillna("otra")
    roads = roads[["osm_id", "name", "highway", "road_class", "geometry"]]
    roads = clip_lines(roads, national)

    waterways = lines[lines["waterway"].notna()].copy()
    waterways["waterway_class"] = waterways["waterway"].where(
        waterways["waterway"].isin(WATERWAY_CLASSES), "otro")
    waterways = waterways[["osm_id", "name", "waterway", "waterway_class",
                           "geometry"]]
    waterways = clip_lines(waterways, national)
    print(f"  vías: {len(roads):,} | cursos de agua: {len(waterways):,}")

    # --- Cuerpos de agua -----------------------------------------------------
    print("\n-- cuerpos de agua --")
    water = pyogrio.read_dataframe(
        PBF, layer="multipolygons",
        columns=["osm_id", "osm_way_id", "name", "natural", "landuse", "other_tags"],
        where=("\"natural\" = 'water' OR \"landuse\" IN ('reservoir','basin','port') "
               "OR \"other_tags\" LIKE '%\"water\"=>%'"),
    )
    # OGR deja osm_id vacío en los polígonos construidos desde relaciones
    # multipolígono; en ese caso el id del elemento es el de la relación.
    water["osm_id"] = pd.to_numeric(water["osm_id"], errors="coerce").fillna(
        pd.to_numeric(water["osm_way_id"], errors="coerce"))
    water = water[water["osm_id"].notna()].copy()
    water["osm_id"] = water["osm_id"].astype("int64")
    tags = water["other_tags"].map(parse_hstore)
    water["water_type"] = [
        d.get("water") or t.get("landuse") or t.get("natural") or "otro"
        for d, t in zip(tags, water.to_dict("records"))
    ]
    water["water_type"] = water["water_type"].where(
        water["water_type"].isin(WATER_AREAS), "otro")
    water = water[["osm_id", "name", "water_type", "geometry"]]
    water = clip_polygons(water, national)
    print(f"  polígonos: {len(water):,}")

    # --- Asentamientos -------------------------------------------------------
    print("\n-- asentamientos --")
    places = pyogrio.read_dataframe(
        PBF, layer="points", columns=["osm_id", "name", "place", "other_tags"],
        where='"place" IS NOT NULL',
    )
    places["osm_id"] = places["osm_id"].astype("int64")
    ptags = places["other_tags"].map(parse_hstore)
    places["population"] = pd.to_numeric(
        ptags.map(lambda d: d.get("population")), errors="coerce")
    places = places[["osm_id", "name", "place", "population", "geometry"]]
    places = places[places.geometry.intersects(national)].copy()
    print(f"  puntos: {len(places):,}  "
          f"(ciudades {int((places['place'] == 'city').sum())}, "
          f"pueblos {int((places['place'] == 'town').sum())}, "
          f"villas {int((places['place'] == 'village').sum())})")

    # --- Infraestructura puntual --------------------------------------------
    print("\n-- infraestructura puntual --")
    infra = pyogrio.read_dataframe(
        PBF, layer="points",
        columns=["osm_id", "name", "place", "other_tags"],
        where=('"other_tags" LIKE \'%"amenity"=>%\' OR '
               '"other_tags" LIKE \'%"aeroway"=>%\' OR '
               '"other_tags" LIKE \'%"power"=>%\' OR '
               '"other_tags" LIKE \'%"man_made"=>%\' OR '
               '"other_tags" LIKE \'%"landuse"=>%\' OR '
               '"other_tags" LIKE \'%"harbour"=>%\' OR '
               '"other_tags" LIKE \'%"healthcare"=>%\' OR '
               '"other_tags" LIKE \'%"port"=>%\''),
    )
    infra["osm_id"] = infra["osm_id"].astype("int64")
    infra["tags"] = infra["other_tags"].map(parse_hstore)
    infra["klass"] = infra["tags"].map(classify)
    infra = infra[infra["klass"].notna()].copy()
    infra["category"] = infra["klass"].map(lambda k: k[0])
    infra["facility"] = infra["klass"].map(lambda k: k[1])
    infra = infra[["osm_id", "name", "category", "facility", "geometry"]]
    infra = infra[infra.geometry.intersects(national)].copy()
    print(f"  puntos: {len(infra):,}")

    # --- Líneas eléctricas y ductos -----------------------------------------
    print("\n-- líneas eléctricas y ductos --")
    power = lines[lines["tags"].map(
        lambda d: d.get("power") in {"line", "minor_line", "cable"} or
        d.get("man_made") == "pipeline")]
    power = power.copy()
    power["infra_line_class"] = power["tags"].map(
        lambda d: "eléctrica" if d.get("power") else "ducto")
    power = power[["osm_id", "name", "infra_line_class", "geometry"]]
    power = clip_lines(power, national)
    print(f"  líneas: {len(power):,}")

    # --- Escritura -----------------------------------------------------------
    print("\n-- escritura --")
    layers = {
        "roads": roads, "waterways": waterways, "water_bodies": water,
        "settlements": places, "infrastructure": infra, "power_lines": power,
    }
    gpkg = C.INFRA_GPKG
    if gpkg.exists():
        gpkg.unlink()
    for name, gdf in layers.items():
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
        gdf = gdf.set_crs(C.CRS_STORAGE, allow_override=True)
        gdf["geometry"] = gdf.geometry.make_valid()
        pyogrio.write_dataframe(gdf, gpkg, layer=name, driver="GPKG",
                                layer_options={"SPATIAL_INDEX": "YES"})
        print(f"  {name}: {len(gdf):,} entidades")

    # --- Validación ----------------------------------------------------------
    print("\n-- validación --")
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))

    for name, gdf in layers.items():
        n = len(gdf)
        check(f"capa {name} no vacía", n > 0, f"{n:,} entidades")
        check(f"capa {name} en {C.CRS_STORAGE}",
              str(gdf.crs) == C.CRS_STORAGE, str(gdf.crs))
        check(f"capa {name} sin id OSM duplicado",
              int(gdf["osm_id"].duplicated().sum()) == 0,
              f"dup={int(gdf['osm_id'].duplicated().sum())}")

    for name, gdf in (("roads", roads), ("waterways", waterways),
                      ("water_bodies", water)):
        outside = (~gdf.geometry.intersects(national)).sum()
        check(f"capa {name} dentro del territorio nacional", outside == 0,
              f"fuera={int(outside)}")

    roads_m = roads.to_crs(C.CRS_METRIC)
    road_km = float(roads_m.length.sum()) / 1000.0
    km_by_class = (roads_m.assign(km=roads_m.length / 1000)
                   .groupby("road_class")["km"].sum().round(1).to_dict())
    print(f"  longitud por clase: {km_by_class}")
    motorized = sum(km_by_class.get(k, 0.0) for k in
                    ("arterial", "colectora", "local", "servicio"))
    main_network = km_by_class.get("arterial", 0.0) + km_by_class.get("colectora", 0.0)
    # No existe una cifra oficial desagregada por clase comparable con OSM, así
    # que se valida solo un orden de magnitud. La red primaria+secundaria
    # (~8.700 km en el extracto) cae en la banda esperada; el total incluye
    # calles residenciales, pistas y senderos mapeados por la comunidad.
    check("red vial principal plausible (5.000–15.000 km)",
          5000 <= main_network <= 15000,
          f"arterial+colectora {main_network:,.0f} km; motorizada total {motorized:,.0f} km")

    ww_m = waterways.to_crs(C.CRS_METRIC)
    ww_km = float(ww_m.length.sum()) / 1000.0
    check("longitud de cursos de agua plausible (2.000–40.000 km)",
          2000 <= ww_km <= 40000, f"{ww_km:,.0f} km")

    wb_km2 = float(water.to_crs(C.CRS_EQUAL_AREA).area.sum()) / 1e6
    check("superficie de cuerpos de agua plausible (100–2.000 km²)",
          100 <= wb_km2 <= 2000, f"{wb_km2:,.1f} km²")

    # Los 44 municipios de la reforma 2023 no son una referencia válida aquí;
    # se comprueba solo que exista una red de asentamientos suficiente.
    check("red de asentamientos suficiente (>= 200 puntos)",
          len(places) >= 200, f"{len(places):,}")

    # Densidad de vías como control de cobertura territorial.
    area_km2 = float(gpd.GeoSeries([national], crs=C.CRS_STORAGE)
                     .to_crs(C.CRS_EQUAL_AREA).area.sum()) / 1e6
    density = road_km / area_km2
    check("densidad vial plausible (0,2–4,0 km/km²)", 0.2 <= density <= 4.0,
          f"total {density:.2f} km/km² (red motorizada {motorized/area_km2:.2f})")

    if any(not c["passed"] for c in checks):
        print("\nERROR: validación de infraestructura fallida.")
        return 1

    # --- Estadísticas y procedencia -----------------------------------------
    stats = {
        "source": {"name": "Geofabrik — El Salvador extract",
                   "url": "https://download.geofabrik.de/central-america/el-salvador-latest.osm.pbf",
                   "osm_timestamp": osm_timestamp,
                   "file_bytes": PBF.stat().st_size,
                   "sha256": sha256_file(PBF)},
        "layers": {
            name: {
                "features": int(len(gdf)),
                "crs": str(gdf.crs),
                "length_km": round(float(gdf.to_crs(C.CRS_METRIC).length.sum()) / 1000, 1)
                if gdf.geom_type.isin(["LineString", "MultiLineString"]).any() else None,
                "area_km2": round(float(gdf.to_crs(C.CRS_EQUAL_AREA).area.sum()) / 1e6, 2)
                if gdf.geom_type.isin(["Polygon", "MultiPolygon"]).any() else None,
            } for name, gdf in layers.items()
        },
        "road_classes": roads["road_class"].value_counts().to_dict(),
        "road_km_by_class": km_by_class,
        "road_km_total": round(road_km, 1),
        "road_km_motorized": round(motorized, 1),
        "road_km_main_network": round(main_network, 1),
        "waterway_classes": waterways["waterway_class"].value_counts().to_dict(),
        "water_types": water["water_type"].value_counts().to_dict(),
        "settlement_types": places["place"].value_counts().to_dict(),
        "infrastructure_categories": infra["category"].value_counts().to_dict(),
        "coverage_notes": [
            "OSM es datos colaborativos: la cobertura rural y de caminos "
            "secundarios es heterogénea y no debe interpretarse como censo.",
            "Las longitudes se miden en EPSG:32616 tras recortar al territorio; "
            "los tramos que cruzan la frontera quedan truncados.",
            "Solo se publican elementos con etiquetas verificables en el "
            "extracto; no se infiere ningún dato faltante.",
        ],
        "validation": checks,
        "attribution": C.ATTRIBUTION["osm"],
    }
    (C.INFRA_DIR / "infrastructure_stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    write_manifest(
        gpkg, layer="infrastructure", source_id="osm-geofabrik",
        source_url=stats["source"]["url"], license="ODbL-1.0",
        attribution=C.ATTRIBUTION["osm"],
        native_resolution="vectorial (posición de nodos OSM)",
        effective_resolution="vectorial; precisión heterogénea según colaborador",
        transform="lectura PBF vía OGR OSM + recorte al territorio ADM1",
        extra={"layers": {k: int(len(v)) for k, v in layers.items()},
               "osm_timestamp": osm_timestamp,
               "pbf_sha256": stats["source"]["sha256"]},
    )

    print(f"\nOK — Módulo 3 completado en {time.time()-t0:.1f} s")
    print(f"  {gpkg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
