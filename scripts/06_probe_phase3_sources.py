"""Fase 3 — sondeo reproducible de fuentes de datos para El Salvador.

No descarga datasets completos: comprueba que el canal responde y registra
codigo HTTP, tipo de contenido, tamano y una muestra del cuerpo. Las descargas
grandes usan Range para leer solo las cabeceras.

Salida:
  research/raw/phase3/probes_<AAAAMMDD>.json   (evidencia completa)
  research/raw/phase3/probes_<AAAAMMDD>.csv    (resumen legible)
  research/raw/phase3/probe_summary.json        (conteos por estado)

Uso:
  .venv/Scripts/python.exe scripts/06_probe_phase3_sources.py
"""

from __future__ import annotations

import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "raw" / "phase3"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 AGROSV-research"
)

# (id, institucion, categoria, url, metodo, range_bytes, nota)
PROBES: list[tuple[str, str, str, str, str, str, str]] = [
    # ---------------- NACIONAL ----------------
    ("cnr_home", "CNR", "territorial", "https://www.cnr.gob.sv/", "GET", "", ""),
    ("cnr_servicios", "CNR", "territorial", "https://www.cnr.gob.sv/servicios/", "GET", "", ""),
    ("cnr_descargas", "CNR", "territorial", "https://www.cnr.gob.sv/descargas/", "GET", "", ""),
    ("cnr_elsalvadormaps", "CNR", "territorial", "https://elsalvadormaps.sv/", "GET", "", ""),
    ("mag_home", "MAG", "produccion", "https://www.mag.gob.sv/", "GET", "", ""),
    ("mag_estadisticas", "MAG", "produccion", "https://www.mag.gob.sv/servicios/estadisticas-agropecuarias", "GET", "", ""),
    ("mag_mapas", "MAG", "produccion", "https://www.mag.gob.sv/servicios/mapas-tematicos/", "GET", "", ""),
    ("mag_precios", "MAG", "economico", "https://www.mag.gob.sv/servicios/precios/", "GET", "", ""),
    ("centa_home", "CENTA", "suelos", "https://www.centa.gob.sv/", "GET", "", ""),
    ("centa_suelos", "CENTA", "suelos", "https://www.centa.gob.sv/mapa-digital-de-suelos", "GET", "", ""),
    ("bcr_geoportal", "BCR", "censo", "https://geoportal.bcr.gob.sv/", "GET", "", ""),
    ("bcr_poblacion_tabulados", "BCR/ONEC", "censo", "https://poblacion.bcr.gob.sv/pages/teg-base-de-datos-y-tabulados", "GET", "", ""),
    ("bcr_agropecuario", "BCR", "censo", "https://agropecuario.bcr.gob.sv/", "GET", "", ""),
    ("bcr_cap_documentacion", "BCR", "censo", "https://agropecuario.bcr.gob.sv/pages/documentacion-cap-ter", "GET", "", ""),
    ("one_home", "ONEC", "economico", "https://one.gob.sv/", "GET", "", ""),
    ("snet_hidrologia", "MARN/SNET", "hidrologia", "https://www.snet.gob.sv/Hidrologia/atlas.htm", "GET", "", ""),
    ("snet_geologia", "MARN/SNET", "geologia", "https://www.snet.gob.sv/ver/geologia/amenaza+deslizamientos", "GET", "", ""),
    ("marn_home", "MARN", "hidrologia", "https://www.marn.gob.sv/", "GET", "", ""),
    ("marn_geoportal", "MARN", "hidrologia", "https://geoportal.marn.gob.sv/", "GET", "", ""),
    ("anda_home", "ANDA", "hidrologia", "https://www.anda.gob.sv/", "GET", "", ""),
    ("oirsa_home", "OIRSA", "fitosanidad", "https://www.oirsa.org/", "GET", "", ""),
    ("ippc_sv", "IPPC/FAO", "fitosanidad", "https://www.ippc.int/en/countries/el-salvador/", "GET", "", ""),
    ("isc_cafe", "ISC", "produccion", "https://www.isc.gob.sv/", "GET", "", ""),
    ("mag_censo2007", "MAG", "censo", "https://www.mag.gob.sv/servicios/estadisticas-agropecuarias/", "GET", "", ""),
    ("rmgir_subcuencas", "RMGIR (tercero)", "hidrologia", "https://rmgir.proyectomesoamerica.org/arcgis/rest/services/Sub_Cuencas_El_Salvador/MapServer?f=json", "GET", "", ""),
    # ---------------- INTERNACIONAL: relieve ----------------
    ("copdem30_aws", "Copernicus/ESA", "topografia", "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N13_00_W090_00_DEM/Copernicus_DSM_COG_10_N13_00_W090_00_DEM.tif", "GET", "0-2047", "cabecera COG"),
    ("copdem90_aws", "Copernicus/ESA", "topografia", "https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_N13_00_W090_00_DEM/Copernicus_DSM_COG_30_N13_00_W090_00_DEM.tif", "GET", "0-2047", "cabecera COG"),
    ("srtm_earthdata", "NASA/USGS", "topografia", "https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/", "GET", "", "requiere Earthdata Login"),
    ("nasadem_lpdaac", "NASA", "topografia", "https://lpdaac.usgs.gov/products/nasadem_hgtv001/", "GET", "", ""),
    ("alos_aw3d30", "JAXA", "topografia", "https://www.eorc.jaxa.jp/ALOS/en/dataset/aw3d30/aw3d30_e.htm", "GET", "", "registro"),
    ("opentopography", "OpenTopography", "topografia", "https://portal.opentopography.org/raster?opentopoID=OTSRTM.082015.4326.1", "GET", "", "requiere clave API"),
    # ---------------- INTERNACIONAL: suelos ----------------
    ("soilgrids_rest", "ISRIC", "suelos", "https://rest.isric.org/soilgrids/v2.0/properties/query?lon=-89.2&lat=13.7&property=phh2o&depth=0-5cm&value=mean", "GET", "", "comprobar null"),
    ("soilgrids_webdav_phh2o", "ISRIC", "suelos", "https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt", "GET", "0-4095", "cabecera VRT"),
    ("soilgrids_webdav_clay", "ISRIC", "suelos", "https://files.isric.org/soilgrids/latest/data/clay/clay_0-30cm_mean.vrt", "GET", "0-4095", ""),
    ("isric_wosis", "ISRIC", "suelos", "https://data.isric.org/geonetwork/srv/eng/catalog.search#/metadata/9a4d4d7d-9d4d-4a4d-9d4d", "GET", "", "perfil WoSIS"),
    ("fao_hwsd_v2", "FAO", "suelos", "https://www.fao.org/soils-portal/data-hub/soil-maps-and-databases/harmonized-world-soil-database-v2/en/", "GET", "", ""),
    ("fao_glosis", "FAO/GSP", "suelos", "https://glosis-ows.geo.science.uni-bonn.de/", "GET", "", ""),
    # ---------------- INTERNACIONAL: hidrologia ----------------
    ("hydrosheds", "WWF/USGS", "hidrologia", "https://www.hydrosheds.org/products", "GET", "", ""),
    ("hydrobasins", "WWF", "hidrologia", "https://www.hydrosheds.org/products/hydrobasins", "GET", "", ""),
    ("hydroatlas", "WWF", "hidrologia", "https://www.hydrosheds.org/products/hydroatlas", "GET", "", ""),
    ("fao_aquastat", "FAO", "hidrologia", "https://www.fao.org/aquastat/en/", "GET", "", ""),
    ("fao_gmia", "FAO", "hidrologia", "https://www.fao.org/aquastat/en/geospatial-information/global-maps-irrigated-areas/", "GET", "", ""),
    ("jrc_global_surface_water", "JRC", "hidrologia", "https://global-surface-water.appspot.com/", "GET", "", ""),
    ("whymap", "BGR/UNESCO", "hidrologia", "https://www.whymap.org/whymap/EN/Home/whymap_node.html", "GET", "", ""),
    ("wri_aqueduct", "WRI", "hidrologia", "https://www.wri.org/aqueduct", "GET", "", ""),
    # ---------------- INTERNACIONAL: clima ----------------
    ("chirps3_readme", "UCSB CHC", "clima", "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/readme.txt", "GET", "", ""),
    ("chirps3_daily_dir", "UCSB CHC", "clima", "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2025/", "GET", "", ""),
    ("nasa_power", "NASA", "clima", "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN&community=AG&longitude=-89.2&latitude=13.7&start=20240101&end=20240105&format=JSON", "GET", "", ""),
    ("open_meteo_archive", "Open-Meteo", "clima", "https://archive-api.open-meteo.com/v1/archive?latitude=13.69&longitude=-89.22&start_date=2024-01-01&end_date=2024-01-05&daily=precipitation_sum,temperature_2m_max,et0_fao_evapotranspiration", "GET", "", ""),
    ("agera5_cds", "Copernicus C3S", "clima", "https://cds.climate.copernicus.eu/datasets/sis-agrometeorological-indicators", "GET", "", "requiere token CDS"),
    ("era5_land_cds", "Copernicus C3S", "clima", "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land", "GET", "", ""),
    ("worldclim21", "WorldClim", "clima", "https://www.worldclim.org/data/worldclim21.html", "GET", "", ""),
    ("noaa_cpc_precip", "NOAA CPC", "clima", "https://psl.noaa.gov/data/gridded/data.cpc.globalprecip.html", "GET", "", ""),
    ("gpm_imerg", "NASA GPM", "clima", "https://gpm.nasa.gov/data/imerg", "GET", "", "requiere Earthdata Login"),
    ("gaez_v4", "FAO/IIASA", "clima", "https://gaez.fao.org/", "GET", "", ""),
    # ---------------- INTERNACIONAL: cobertura y satelite ----------------
    ("esa_worldcover", "ESA", "cobertura", "https://esa-worldcover.org/en", "GET", "", ""),
    ("dynamic_world", "Google/World Resources", "cobertura", "https://dynamicworld.app/", "GET", "", ""),
    ("gfw_hansen", "Global Forest Watch", "cobertura", "https://data.globalforestwatch.org/", "GET", "", ""),
    ("ghsl", "JRC", "cobertura", "https://ghsl.jrc.ec.europa.eu/", "GET", "", ""),
    ("worldpop", "WorldPop", "censo", "https://www.worldpop.org/", "GET", "", ""),
    ("copernicus_clms", "Copernicus", "cobertura", "https://land.copernicus.eu/en/products/global-dynamic-land-cover", "GET", "", ""),
    ("stac_cdse", "ESA/Copernicus", "satelite", "https://stac.dataspace.copernicus.eu/v1/", "GET", "", ""),
    ("stac_earth_search", "Element84/AWS", "satelite", "https://earth-search.aws.element84.com/v1/collections", "GET", "", ""),
    ("usgs_earthexplorer", "USGS", "satelite", "https://earthexplorer.usgs.gov/", "GET", "", "requiere login"),
    ("lpdaac_modis", "NASA LP DAAC", "satelite", "https://lpdaac.usgs.gov/products/mod13q1v061/", "GET", "", "requiere Earthdata Login"),
    # ---------------- INTERNACIONAL: agricultura, censos, economia ----------------
    ("faostat_api", "FAO", "economico", "https://fenixservices.fao.org/faostat/api/v1/en/definitions/domain", "GET", "", ""),
    ("faostat_bulk", "FAO", "economico", "https://bulks-faostat.fao.org/production/Area_Harvested_and_Planted_area_E_All_Data_(Normalized).zip", "GET", "0-1023", "zip"),
    ("worldbank_api", "World Bank", "economico", "https://api.worldbank.org/v2/country/SLV/indicator/AG.LND.ARBL.HA?format=json&per_page=5", "GET", "", ""),
    ("gbif_api", "GBIF", "biodiversidad", "https://api.gbif.org/v1/occurrence/search?country=SV&limit=1", "GET", "", ""),
    ("protectedplanet_sv", "UNEP-WCMC", "biodiversidad", "https://www.protectedplanet.net/country/SLV", "GET", "", ""),
    ("wdpa_api", "UNEP-WCMC", "biodiversidad", "https://api.protectedplanet.net/v3/protected_areas?token=demo", "GET", "", "requiere token"),
    ("eppo_gd", "EPPO", "fitosanidad", "https://gd.eppo.int/", "GET", "", ""),
    ("cabi_cpc", "CABI", "fitosanidad", "https://www.cabi.org/cpc/", "GET", "", "suscripcion"),
    ("fao_ecocrop", "FAO", "cultivos", "https://ecocrop.fao.org/ecocrop/srv/en/home", "GET", "", "servicio retirado (comprobar)"),
    ("giews_crop_calendar", "FAO GIEWS", "cultivos", "https://cropcalendar.app/", "GET", "", ""),
    ("usda_psd", "USDA FAS", "economico", "https://apps.fas.usda.gov/psdonline/app/index.html", "GET", "", ""),
    ("huggingface_nemotron", "NVIDIA", "personas", "https://huggingface.co/api/datasets/nvidia/Nemotron-Personas-El-Salvador", "GET", "", ""),
    ("geoboundaries_slv_adm1", "geoBoundaries", "territorial", "https://www.geoboundaries.org/api/current/gbOpen/SLV/ADM1/", "GET", "", ""),
    ("osm_geofabrik", "OpenStreetMap", "territorial", "https://download.geofabrik.de/central-america/el-salvador-latest.osm.pbf", "GET", "0-1023", "pbf"),
    # ---------------- RONDA 2: URLs corregidas / añadidas ----------------
    ("mag_precios_informe", "MAG", "economico", "https://www.mag.gob.sv/informe-mensual-de-precios-de-productos-agropecuarios", "GET", "", "página con 48 PDF de precios"),
    ("mag_insumos_guia", "MAG", "economico", "https://www.mag.gob.sv/guia-anual-de-precios-de-insumos-agropecuarios", "GET", "", ""),
    ("mag_anuario_2022_23", "MAG", "produccion", "https://www.mag.gob.sv/wp-content/uploads/2024/02/1-Anuario-de-Estad%C3%ADsticas-Agropecuarias-2022-2023-final-1.pdf", "GET", "0-2047", "PDF"),
    ("mag_boletin_precios_2023_12", "MAG", "economico", "https://www.mag.gob.sv/wp-content/uploads/2024/05/Informe-mensual-DICIEMBRE-2023.pdf", "GET", "0-2047", "PDF"),
    ("mag_mapas_tematicos_b", "MAG", "cobertura", "https://www.mag.gob.sv/mapas-tematicos/", "GET", "", ""),
    ("cnr_elsalvadormaps_retry", "CNR", "territorial", "https://www.elsalvadormaps.sv/", "GET", "", "reintento"),
    ("cnr_elsalvadormaps_app", "CNR", "territorial", "https://mapa.elsalvadormaps.sv/cnr/map/4", "GET", "", "visor"),
    ("one_www", "ONEC", "economico", "https://www.one.gob.sv/", "GET", "", ""),
    ("snet_meteorologia", "MARN/SNET", "clima", "https://www.snet.gob.sv/ver/meteorologia/", "GET", "", ""),
    ("snet_hidrologia_ver", "MARN/SNET", "hidrologia", "https://www.snet.gob.sv/ver/hidrologia/", "GET", "", ""),
    ("marn_home_retry", "MARN", "hidrologia", "https://www.marn.gob.sv/", "GET", "", "reintento"),
    ("osm_geofabrik_head", "OpenStreetMap", "territorial", "https://download.geofabrik.de/central-america/el-salvador-latest.osm.pbf", "HEAD", "", ""),
    ("soilgrids_clay_0_5", "ISRIC", "suelos", "https://files.isric.org/soilgrids/latest/data/clay/clay_0-5cm_mean.vrt", "GET", "0-2047", "profundidad nativa"),
    ("soilgrids_wv0033_0_5", "ISRIC", "suelos", "https://files.isric.org/soilgrids/latest/data/wv0033/wv0033_0-5cm_mean.vrt", "GET", "0-2047", "agua a 33 kPa"),
    ("soilgrids_wv1500_0_5", "ISRIC", "suelos", "https://files.isric.org/soilgrids/latest/data/wv1500/wv1500_0-5cm_mean.vrt", "GET", "0-2047", "agua a 1500 kPa"),
    ("alos_aw3d30_index", "JAXA", "topografia", "https://www.eorc.jaxa.jp/ALOS/en/aw3d30/index.htm", "GET", "", ""),
    ("hydrosheds_data", "WWF/USGS", "hidrologia", "https://data.hydrosheds.org/", "GET", "", ""),
    ("esgf_cmip6", "ESGF", "clima", "https://esgf-node.llnl.gov/search/cmip6/", "GET", "", ""),
    ("fao_gaez_download", "FAO/IIASA", "clima", "https://gaez.fao.org/pages/data-access-download", "GET", "", ""),
    ("chirps3_tif_2026", "UCSB CHC", "clima", "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2026/chirps-v3.0.rnl.2026.01.15.tif", "GET", "0-2047", "cabecera GeoTIFF"),
    ("jrc_gsw_download", "JRC", "hidrologia", "https://global-surface-water.appspot.com/download", "GET", "", ""),
    ("usgs_landsat_c2", "USGS", "satelite", "https://www.usgs.gov/landsat-missions/landsat-collection-2", "GET", "", ""),
    ("nasa_earthdata_login", "NASA", "satelite", "https://urs.earthdata.nasa.gov/", "GET", "", "registro"),
    ("worldbank_agri_share", "World Bank", "economico", "https://api.worldbank.org/v2/country/SLV/indicator/AG.LND.AGRI.ZS?format=json&per_page=5", "GET", "", ""),
    ("centa_hub", "CENTA", "suelos", "https://portal-de-mapas-digitales-del-centa-centa.hub.arcgis.com/", "GET", "", "ArcGIS Hub"),
    ("centa_hub_search", "CENTA", "suelos", "https://portal-de-mapas-digitales-del-centa-centa.hub.arcgis.com/api/search/v1/collections/all/items?limit=50", "GET", "", "catálogo máquina-a-máquina"),
    ("bcr_cap_segunda_pdf", "BCR", "censo", "https://censo2024.bcr.gob.sv/wp-content/uploads/tablas-geoportal/censoagro/Segunda_entrega_de_resultados_CAP_2025.pdf", "GET", "0-2047", "PDF"),
    ("bcr_cap_tercera_pdf", "BCR", "censo", "https://censo2024.bcr.gob.sv/wp-content/uploads/tablas-geoportal/Presentaci%C3%B3n_tercera_entrega_CAP_2025.pdf", "GET", "0-2047", "PDF"),
    ("bcr_cap_seg_docs", "BCR", "censo", "https://agropecuario.bcr.gob.sv/pages/documentos-cap-seg", "GET", "", ""),
    # ---------------- RONDA 3: mapas tematicos MAG, Geofabrik corregido ----------------
    ("mag_mapas_page", "MAG", "cobertura", "https://www.mag.gob.sv/mapas-tematicos-sobre-frutales-granos-basicos-hortalizas-pecuarios-y-suelos/", "GET", "", "8 PDF temáticos"),
    ("mag_pdf_granos", "MAG", "cobertura", "https://www.mag.gob.sv/wp-content/uploads/2021/06/granos-basicos.pdf", "GET", "0-1023", "PDF"),
    ("mag_pdf_suelos", "MAG", "suelos", "https://www.mag.gob.sv/wp-content/uploads/2021/06/suelos.pdf", "GET", "0-1023", "PDF"),
    ("mag_pdf_clima", "MAG", "clima", "https://www.mag.gob.sv/wp-content/uploads/2021/06/variables-climaticas.pdf", "GET", "0-1023", "PDF"),
    ("mag_pdf_hortalizas", "MAG", "cobertura", "https://www.mag.gob.sv/wp-content/uploads/2021/06/hortalizas.pdf", "GET", "0-1023", "PDF"),
    ("mag_pdf_frutales", "MAG", "cobertura", "https://www.mag.gob.sv/wp-content/uploads/2021/06/frutales.pdf", "GET", "0-1023", "PDF"),
    ("mag_anuario_2021_22", "MAG", "produccion", "https://www.mag.gob.sv/wp-content/uploads/2022/12/Anuario-de-Estad%C3%ADsticas-Agropecuarias-2021-2022.pdf", "GET", "0-2047", "PDF"),
    ("geofabrik_sv_pbf_r3", "OpenStreetMap", "territorial", "https://download.geofabrik.de/central-america/el-salvador/el-salvador-latest.osm.pbf", "HEAD", "", "ruta corregida"),
    ("geofabrik_sv_shp", "OpenStreetMap", "territorial", "https://download.geofabrik.de/central-america/el-salvador/el-salvador-latest-free.shp.zip", "HEAD", "", "shapefiles por capa"),
    ("bcr_cap_primera_pdf", "BCR", "censo", "https://censo2024.bcr.gob.sv/wp-content/uploads/tablas-geoportal/censoagro/Primera_entrega_de_resultados_CAP_2025.pdf", "GET", "0-2047", "PDF"),
]


def probe(item) -> dict:
    pid, inst, cat, url, method, rng, note = item
    headers = {"User-Agent": UA, "Accept": "*/*"}
    if rng:
        headers["Range"] = f"bytes={rng}"
    started = datetime.now(timezone.utc)
    rec = {
        "id": pid,
        "institution": inst,
        "category": cat,
        "url": url,
        "method": method,
        "range": rng,
        "note": note,
        "probed_at": started.isoformat(timespec="seconds"),
    }
    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as c:
            r = c.request(method, url)
        rec.update(
            status=r.status_code,
            bytes=len(r.content),
            content_type=r.headers.get("content-type", ""),
            final_url=str(r.url),
            elapsed_ms=int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        )
        ctype = rec["content_type"].lower()
        if any(k in ctype for k in ("json", "text", "xml", "html")):
            body = r.text[:600].replace("\n", " ")
            rec["snippet"] = body
        elif r.status_code < 400:
            rec["snippet"] = r.content[:16].hex()
    except Exception as exc:  # noqa: BLE001 - el fallo es el dato
        rec.update(status=None, bytes=0, content_type="", final_url="", error=f"{type(exc).__name__}: {exc}")
    return rec


def classify(rec: dict) -> str:
    st = rec.get("status")
    if st is None:
        return "UNAVAILABLE"
    if st in (401, 402, 403):
        return "RESTRICTED"
    if st == 404:
        return "DOCUMENTED"  # URL documentada que hoy no responde
    if 200 <= st < 300:
        return "VERIFIED"
    if st in (429, 502, 503, 522, 524):
        return "UNAVAILABLE"
    return "PENDING_VALIDATION"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if len(sys.argv) > 1:
        stamp = f"{stamp}_{sys.argv[1]}"
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(probe, PROBES))

    for rec in results:
        rec["channel_status"] = classify(rec)

    payload = {
        "phase": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "probe_count": len(results),
        "method": "HTTP GET/HEAD con User-Agent de navegador; Range para archivos grandes",
        "results": results,
    }
    json_path = OUT / f"probes_{stamp}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = OUT / f"probes_{stamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "institution", "category", "status", "channel_status", "bytes", "content_type", "url", "error"])
        for r in results:
            w.writerow([r["id"], r["institution"], r["category"], r.get("status"), r["channel_status"], r["bytes"], r["content_type"], r["url"], r.get("error", "")])

    counts: dict[str, int] = {}
    for r in results:
        counts[r["channel_status"]] = counts.get(r["channel_status"], 0) + 1
    summary = {
        "generated_at": payload["generated_at"],
        "probe_count": len(results),
        "by_status": counts,
        "failed_ids": [r["id"] for r in results if r["channel_status"] != "VERIFIED"],
    }
    (OUT / "probe_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    for r in sorted(results, key=lambda x: (x["channel_status"], x["id"])):
        print(f"{r['channel_status']:<20} {str(r.get('status')):<5} {r['bytes']:>9}  {r['id']}")
    print("\n" + json.dumps(summary["by_status"], ensure_ascii=False))
    print(f"escrito: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
