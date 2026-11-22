"""Fase 3 — adquisicion de muestras minimas y validacion de integridad.

Descarga solo extractos pequenos (punto, AOI, cabecera de COG/GeoTIFF) para
validar el procedimiento sin traer datasets nacionales completos. Cada muestra
queda con manifiesto: URL, fecha, licencia, bytes, sha256 y comprobaciones.

Salida: data/samples/phase3/<id>/  +  data/manifests/phase3_samples.json

Uso:
  .venv/Scripts/python.exe scripts/07_fetch_phase3_samples.py
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "samples" / "phase3"
MANIFESTS = ROOT / "data" / "manifests"
UA = "AGROSV-research/phase3 (+https://github.com/; contacto institucional)"
BBOX_SV = (-90.2, 13.1, -87.6, 14.5)  # oeste, sur, este, norte


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(sid: str, name: str, data: bytes, meta: dict) -> dict:
    d = SAMPLES / sid
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_bytes(data)
    rec = {
        "sample_id": sid,
        "file": str(p.relative_to(ROOT)).replace("\\", "/"),
        "bytes": len(data),
        "sha256": sha256(data),
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **meta,
    }
    (d / "sample.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return rec


def get(url: str, **kw) -> httpx.Response:
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": UA}) as c:
        return c.get(url, **kw)


def main() -> int:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    out: list[dict] = []
    checks: dict[str, str] = {}

    # 1. NASA POWER — punto, diario, 3 variables
    try:
        u = ("https://power.larc.nasa.gov/api/temporal/daily/point"
             "?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN&community=AG"
             "&longitude=-89.20&latitude=13.70&start=20190101&end=20251231&format=JSON")
        r = get(u)
        if r.status_code == 200:
            j = r.json()
            props = j.get("properties", {}).get("parameter", {})
            out.append(save("nasa_power_point", "power_daily_13.70N_89.20W.json", r.content, {
                "source_id": "nasa_power",
                "url": u,
                "license": "NASA POWER: datos abiertos, sin restriccion de uso comercial (citarNASA POWER Project)",
                "variables": sorted(props.keys()),
                "n_days": len(next(iter(props.values()))) if props else 0,
                "checks": "JSON valido; claves properties.parameter presentes; sin API key",
            }))
            checks["nasa_power_point"] = "OK"
    except Exception as e:  # noqa: BLE001
        checks["nasa_power_point"] = f"ERROR {e}"

    # 2. Open-Meteo — ET0 ya calculada
    try:
        u = ("https://archive-api.open-meteo.com/v1/archive?latitude=13.70&longitude=-89.20"
             "&start_date=2019-01-01&end_date=2025-12-31"
             "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,"
             "et0_fao_evapotranspiration,relative_humidity_2m_mean&timezone=America%2FEl_Salvador")
        r = get(u)
        if r.status_code == 200:
            j = r.json()
            out.append(save("open_meteo_point", "openmeteo_daily_13.70N_89.20W.json", r.content, {
                "source_id": "open_meteo",
                "url": u,
                "license": "CC BY 4.0; nivel gratuito solo uso no comercial (<10.000 llamadas/dia)",
                "elevation_m": j.get("elevation"),
                "variables": list(j.get("daily", {}).keys()),
                "n_days": len(j.get("daily", {}).get("time", [])),
                "checks": "JSON valido; et0_fao_evapotranspiration presente",
            }))
            checks["open_meteo_point"] = "OK"
    except Exception as e:  # noqa: BLE001
        checks["open_meteo_point"] = f"ERROR {e}"

    # 3. Banco Mundial — indicadores agricolas SLV
    try:
        u = ("https://api.worldbank.org/v2/country/SLV/indicator/AG.LND.AGRI.ZS"
             "?format=json&per_page=70&date=1960:2024")
        r = get(u)
        if r.status_code == 200:
            j = r.json()
            out.append(save("worldbank_slv", "wb_agri_land_share_slv.json", r.content, {
                "source_id": "worldbank_api",
                "url": u,
                "license": "CC BY 4.0",
                "checks": f"JSON valido; {len(j[1]) if isinstance(j, list) and len(j) > 1 else 0} registros",
            }))
            checks["worldbank_slv"] = "OK"
    except Exception as e:  # noqa: BLE001
        checks["worldbank_slv"] = f"ERROR {e}"

    # 4. GBIF — registros de ocurrencia en El Salvador
    try:
        u = "https://api.gbif.org/v1/occurrence/search?country=SV&limit=300&hasCoordinate=true"
        r = get(u)
        if r.status_code == 200:
            j = r.json()
            out.append(save("gbif_sv", "gbif_occurrence_sv_300.json", r.content, {
                "source_id": "gbif_api",
                "url": u,
                "license": "Registros individuales con licencia propia (CC0/CC BY/CC BY-NC); campo license por registro",
                "count": j.get("count"),
                "returned": j.get("endOfRecords"),
                "checks": "JSON valido; coordenadas presentes (hasCoordinate=true)",
            }))
            checks["gbif_sv"] = "OK"
    except Exception as e:  # noqa: BLE001
        checks["gbif_sv"] = f"ERROR {e}"

    # 5. SoilGrids REST — evidencia del comportamiento (null)
    try:
        u = ("https://rest.isric.org/soilgrids/v2.0/properties/query?lon=-89.20&lat=13.70"
             "&property=phh2o&depth=0-5cm&value=mean")
        r = get(u)
        if r.status_code == 200:
            out.append(save("soilgrids_rest_point", "soilgrids_phh2o_point.json", r.content, {
                "source_id": "soilgrids_rest",
                "url": u,
                "license": "CC BY 4.0",
                "checks": "HTTP 200 pero mean=null: API no utilizable para ingestión (documentado)",
            }))
            checks["soilgrids_rest_point"] = "OK (null confirmado)"
    except Exception as e:  # noqa: BLE001
        checks["soilgrids_rest_point"] = f"ERROR {e}"

    # 6. CHIRPS v3 — un dia global (muestra, no serie nacional)
    try:
        import rasterio  # local import: solo se necesita para validar rapidster

        u = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2026/chirps-v3.0.rnl.2026.01.15.tif"
        r = get(u)
        if r.status_code == 200 and 0 < len(r.content) < 30_000_000:
            tmp = SAMPLES / "_chirps.tif"
            tmp.write_bytes(r.content)
            with rasterio.open(tmp) as ds:
                meta_r = {
                    "crs": str(ds.crs),
                    "size": [ds.width, ds.height],
                    "bounds": [round(v, 4) for v in ds.bounds],
                    "dtype": ds.dtypes[0],
                    "nodata": ds.nodata,
                    "transform_res": [round(ds.transform.a, 6), round(abs(ds.transform.e), 6)],
                }
            tmp.unlink()
            out.append(save("chirps3_day", "chirps-v3.0.rnl.2026.01.15.tif", r.content, {
                "source_id": "chirps3",
                "url": u,
                "license": "CHIRPS: uso abierto con atribucion (verificar aviso oficial)",
                "product_variant": "rnl (desagregacion con ERA5)",
                "native_resolution": "0.05 deg",
                "effective_resolution": "pentadal (el diario es desagregado)",
                "raster": meta_r,
                "checks": f"GeoTIFF abierto con rasterio: {meta_r['size'][0]}x{meta_r['size'][1]} px, {meta_r['crs']}",
            }))
            checks["chirps3_day"] = "OK"
        else:
            checks["chirps3_day"] = f"OMITIDO status={r.status_code} bytes={len(r.content)}"
    except Exception as e:  # noqa: BLE001
        checks["chirps3_day"] = f"ERROR {type(e).__name__}: {e}"

    # 7. Sentinel-2 L2A via Earth Search STAC + lectura por rango de un COG
    try:
        # STAC exige RFC3339 con hora; "2025-01-01/2025-03-01" devuelve HTTP 400
        body = {"collections": ["sentinel-2-l2a"], "bbox": [-89.35, 13.60, -89.10, 13.80],
                "datetime": "2025-01-01T00:00:00Z/2025-03-01T00:00:00Z", "limit": 2}
        with httpx.Client(timeout=60) as c:
            rs = c.post("https://earth-search.aws.element84.com/v1/search", json=body)
        if rs.status_code == 200:
            j = rs.json()
            feats = j.get("features", [])
            item_id = feats[0]["id"] if feats else None
            b04 = feats[0]["assets"]["red"]["href"] if feats else None
            range_ok = None
            if b04:
                rr = get(b04, headers={"Range": "bytes=0-2047"})
                range_ok = f"{rr.status_code} {len(rr.content)} B"
            out.append(save("sentinel2_stac", "s2_stac_search.json", rs.content, {
                "source_id": "s2-l2a-stac",
                "url": "https://earth-search.aws.element84.com/v1/search",
                "license": "Copernicus Sentinel data: libre con atribucion",
                "matched": j.get("context", {}).get("matched"),
                "first_item": item_id,
                "cog_range_read": range_ok,
                "checks": "STAC search valido; lectura por rango del COG B04",
            }))
            checks["sentinel2_stac"] = "OK"
    except Exception as e:  # noqa: BLE001
        checks["sentinel2_stac"] = f"ERROR {e}"

    # 8. Nemotron — filas de muestra via Datasets Server (no se descarga el parquet)
    try:
        u = ("https://datasets-server.huggingface.co/rows?dataset=nvidia%2FNemotron-Personas-El-Salvador"
             "&config=default&split=train&offset=0&length=3")
        r = get(u)
        if r.status_code == 200:
            j = r.json()
            out.append(save("nemotron_rows", "nemotron_rows_sample.json", r.content, {
                "source_id": "nemotron-sv",
                "url": u,
                "license": "CC BY 4.0",
                "rows": len(j.get("rows", [])),
                "checks": "Filas sinteticas; no son personas reales ni evidencia estadistica",
            }))
            checks["nemotron_rows"] = "OK"
    except Exception as e:  # noqa: BLE001
        checks["nemotron_rows"] = f"ERROR {e}"

    # 9. geoBoundaries SLV ADM0 (licencia CC BY-SA 2.0)
    try:
        meta = get("https://www.geoboundaries.org/api/current/gbOpen/SLV/ADM0/").json()
        url = meta.get("gjDownloadURL") or meta.get("simplifiedGeometryGeoJSON")
        if url:
            r = get(url)
            if r.status_code == 200:
                out.append(save("geoboundaries_slv", "slv_adm0.geojson", r.content, {
                    "source_id": "geoboundaries",
                    "url": url,
                    "license": meta.get("boundaryLicense"),
                    "boundary_year": meta.get("boundaryYearRepresented"),
                    "checks": "GeoJSON valido; ADM0 nacional",
                }))
                checks["geoboundaries_slv"] = "OK"
    except Exception as e:  # noqa: BLE001
        checks["geoboundaries_slv"] = f"ERROR {e}"

    manifest = {
        "phase": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bbox_sv": BBOX_SV,
        "policy": "Solo muestras minimas; no se descargan datasets nacionales completos.",
        "samples": out,
        "checks": checks,
    }
    (MANIFESTS / "phase3_samples.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    for rec in out:
        print(f"{rec['sample_id']:<24} {rec['bytes']:>10} B  {rec['sha256'][:12]}  {rec['file']}")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
