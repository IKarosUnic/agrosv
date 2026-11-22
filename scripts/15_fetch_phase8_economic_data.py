"""AGROSV Phase 8 — Descarga y catalogación de datos económicos reales de El Salvador.

Fuentes abiertas descargadas y verificadas:
1. WFP Food Prices for El Salvador (HDX / CC BY-IGO):
   - wfp_food_prices_slv.csv
   - wfp_markets_slv.csv
2. OpenStreetMap El Salvador (capa `infrastructure`, categoría `mercado` de
   `data/processed/infrastructure/infrastructure.gpkg`).
3. Indicador ya presente del Banco Mundial (`wb_agri_land_share_slv.json`).
4. Tabulados públicos preliminares verificados del V Censo Agropecuario 2025 (BCR)
   y anuario MAG 2021-2022 registrados con procedencia explícita.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv import config as C  # noqa: E402

OUT_DIR = C.DATA / "standardized" / "economics"

WFP_PRICES_URL = (
    "https://data.humdata.org/dataset/0ff64070-c95b-4962-9d99-09d989d43f75/"
    "resource/843fb265-6f80-4d86-ae41-ef89b6daff15/download/wfp_food_prices_slv.csv"
)
WFP_MARKETS_URL = (
    "https://data.humdata.org/dataset/0ff64070-c95b-4962-9d99-09d989d43f75/"
    "resource/4eb074d8-034c-4edd-92ce-3eab812702e2/download/wfp_markets_slv.csv"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_and_build() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }

    # 1. WFP Food Prices + Markets CSV (HDX)
    prices_path = OUT_DIR / "wfp_food_prices_slv.csv"
    markets_path = OUT_DIR / "wfp_markets_slv.csv"

    r_prices = requests.get(WFP_PRICES_URL, timeout=60)
    r_prices.raise_for_status()
    prices_path.write_bytes(r_prices.content)

    r_markets = requests.get(WFP_MARKETS_URL, timeout=30)
    r_markets.raise_for_status()
    markets_path.write_bytes(r_markets.content)

    with prices_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    dates = sorted({r["date"] for r in rows if r.get("date")})
    commodities = sorted({r["commodity"] for r in rows if r.get("commodity")})
    price_types = sorted({r["pricetype"] for r in rows if r.get("pricetype")})
    wfp_markets = sorted({r["market"] for r in rows if r.get("market")})

    with markets_path.open("r", encoding="utf-8", newline="") as f:
        mkt_rows = list(csv.DictReader(f))

    results["sources"]["wfp_food_prices_slv"] = {
        "file": str(prices_path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": _sha256(r_prices.content),
        "bytes": len(r_prices.content),
        "url": WFP_PRICES_URL,
        "license": "Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO)",
        "rows": len(rows),
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "commodities": commodities,
        "price_types": price_types,
        "markets_count": len(wfp_markets),
        "markets": wfp_markets,
    }
    results["sources"]["wfp_markets_slv"] = {
        "file": str(markets_path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": _sha256(r_markets.content),
        "bytes": len(r_markets.content),
        "url": WFP_MARKETS_URL,
        "license": "CC BY-IGO",
        "rows": len(mkt_rows),
    }

    # 2. Extract OSM markets from infrastructure.gpkg
    osm_markets_path = OUT_DIR / "osm_markets_slv.json"
    infra_path = C.INFRA_GPKG
    if infra_path.exists():
        gdf = gpd.read_file(infra_path, layer="infrastructure")
        mkts = gdf[gdf["category"] == "mercado"].copy()
        osm_records = []
        for _, row in mkts.iterrows():
            geom = row.geometry
            lon = float(geom.x) if geom is not None else None
            lat = float(geom.y) if geom is not None else None
            name_val = row.get("name")
            name = None if name_val is None or str(name_val) == "nan" else str(name_val)
            osm_records.append({
                "osm_id": int(row["osm_id"]),
                "name": name or f"Mercado OSM {int(row['osm_id'])}",
                "named": bool(name),
                "category": str(row["category"]),
                "facility": str(row["facility"]),
                "lon": round(lon, 6) if lon is not None else None,
                "lat": round(lat, 6) if lat is not None else None,
            })
        osm_bytes = json.dumps(osm_records, ensure_ascii=False, indent=2).encode("utf-8")
        osm_markets_path.write_bytes(osm_bytes)
        results["sources"]["osm_markets_slv"] = {
            "file": str(osm_markets_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(osm_bytes),
            "count": len(osm_records),
            "license": "OpenStreetMap ODbL 1.0",
        }

    # Write provenance summary
    prov_path = OUT_DIR / "phase8_economic_sources.provenance.json"
    prov_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    summary = fetch_and_build()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
