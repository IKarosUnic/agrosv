"""AGROSV Phase 8 — Subsistema C: Inteligencia de Mercados y Precios Agrícolas.

Contiene los 6 motores del Subsistema C:
1. AgriculturalMarketEngine
2. AgriculturalPriceEngine
3. PriceHistoryEngine
4. MarketSupplyDemandEngine
5. MarketComparisonEngine
6. MarketOpportunityEngine

Lee datos reales locales descargados de WFP/HDX (`wfp_food_prices_slv.csv`,
`wfp_markets_slv.csv`) y OpenStreetMap (`osm_markets_slv.json`).
"""
from __future__ import annotations

import csv
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from . import governance as EG

ENGINE_VERSION = EG.ENGINE_VERSION

PRICE_TYPES = (
    "farm_gate",
    "wholesale",
    "retail",
    "export",
    "import",
    "official_reference",
    "producer_reported",
)

CHANNEL_TYPES = (
    "wholesale_market",
    "municipal_market",
    "retail_market",
    "collection_center",
    "cooperative",
    "producer_association",
    "agro_industry",
    "export_channel",
    "direct_sale",
    "supermarket",
    "local_distribution",
)

# Mapeo explícito de commodities WFP hacia cultivos del catálogo AGROSV
WFP_TO_AGROSV_CROP = {
    "Maize (white)": "maize",
    "Beans (red)": "beans",
    "Beans (silk red)": "beans",
    "Rice": "rice",
    "Sorghum": "sorghum",
}

AGROSV_TO_WFP_COMMODITIES = {
    "maize": ("Maize (white)",),
    "beans": ("Beans (silk red)", "Beans (red)"),
    "rice": ("Rice",),
    "sorghum": ("Sorghum",),
}


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * r * math.asin(min(1.0, math.sqrt(a)))


@lru_cache(maxsize=1)
def _load_wfp_prices() -> list[dict[str, Any]]:
    path = EG.ECON_DATA_DIR / "wfp_food_prices_slv.csv"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                price = float(row["price"])
            except (KeyError, TypeError, ValueError):
                continue
            unit = row.get("unit", "")
            usd_per_kg = None
            usd_per_t = None
            usd_per_qq46 = None
            try:
                usd_per_kg = round(EG.normalize_unit_price(price, unit, target_unit="kg"), 4)
                usd_per_t = round(EG.normalize_unit_price(price, unit, target_unit="t"), 2)
                usd_per_qq46 = round(EG.normalize_unit_price(price, unit, target_unit="46 kg"), 2)
            except EG.EconomicError:
                pass
            out.append({
                "date": row["date"],
                "admin1": row.get("admin1"),
                "admin2": row.get("admin2"),
                "market": row.get("market"),
                "market_id": row.get("market_id"),
                "latitude": float(row["latitude"]) if row.get("latitude") else None,
                "longitude": float(row["longitude"]) if row.get("longitude") else None,
                "category": row.get("category"),
                "commodity": row.get("commodity"),
                "crop_id": WFP_TO_AGROSV_CROP.get(row.get("commodity", "")),
                "unit": unit,
                "price_flag": row.get("priceflag"),
                "price_type": str(row.get("pricetype") or "").strip().lower(),
                "currency": row.get("currency", "USD"),
                "price": price,
                "normalized_usd_per_kg": usd_per_kg,
                "normalized_usd_per_qq46": usd_per_qq46,
                "normalized_usd_per_t": usd_per_t,
            })
    return out


@lru_cache(maxsize=1)
def _load_wfp_markets() -> list[dict[str, Any]]:
    path = EG.ECON_DATA_DIR / "wfp_markets_slv.csv"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out.append({
                "market_id": f"WFP-{row['market_id']}",
                "name": row["market"],
                "department": row.get("admin1"),
                "municipality": row.get("admin2"),
                "latitude": float(row["latitude"]) if row.get("latitude") else None,
                "longitude": float(row["longitude"]) if row.get("longitude") else None,
                "market_type": "wholesale_or_retail_monitoring_market",
                "products_traded": ["Maize (white)", "Beans (red)", "Beans (silk red)", "Rice", "Sorghum"],
                "infrastructure": "plaza / mercado monitoreado (capacidad física no documentada)",
                "source": "wfp_markets_slv",
                "verification_status": "INTEGRATED",
                "last_verification_date": "2026-10-15",
            })
    return out


@lru_cache(maxsize=1)
def _load_osm_markets() -> list[dict[str, Any]]:
    path = EG.ECON_DATA_DIR / "osm_markets_slv.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for row in raw:
        out.append({
            "market_id": f"OSM-{row['osm_id']}",
            "name": row["name"],
            "department": None,
            "municipality": None,
            "latitude": row.get("lat"),
            "longitude": row.get("lon"),
            "market_type": "municipal_market",
            "products_traded": [],
            "infrastructure": "punto OSM category=mercado (sin detalle de infraestructura)",
            "source": "osm_markets_slv",
            "verification_status": "INTEGRATED",
            "last_verification_date": "2026-11-22",
        })
    return out


class AgriculturalMarketEngine:
    """Catálogo verificado de mercados reales de El Salvador (WFP + OSM)."""

    engine = "agricultural_market"
    version = ENGINE_VERSION

    def catalog(
        self,
        *,
        department: str | None = None,
        source: str | None = None,
        named_only: bool = False,
        limit: int = 100,
    ) -> dict[str, Any]:
        markets = _load_wfp_markets() + _load_osm_markets()
        filtered: list[dict[str, Any]] = []
        for m in markets:
            if source and source != m["source"]:
                continue
            if department and department.strip().lower() not in str(m.get("department") or "").lower():
                continue
            if named_only and str(m.get("name", "")).startswith("Mercado OSM "):
                continue
            filtered.append(m)
            if len(filtered) >= limit:
                break

        return EG.economic_envelope(
            self.engine,
            result={
                "count": len(filtered),
                "total_catalog_size": len(markets),
                "channel_taxonomy": list(CHANNEL_TYPES),
                "markets": filtered,
                "unverified_channels_note": (
                    "centros de acopio, cooperativas, supermercados y exportadores "
                    "no cuentan con directorio abierto verificado en este repositorio"
                ),
            },
            sources=["wfp_markets_slv", "osm_markets_slv"],
            assumptions=["solo se publican mercados presentes en WFP o OpenStreetMap"],
            limitations=[
                "no se inventan compradores activos ni precios de acopio privados",
                "los puntos OSM no incluyen productos ni horarios",
            ],
            evidence_class="official_statistic",
            query={"department": department, "source": source, "limit": limit},
        )


class AgriculturalPriceEngine:
    """Consulta y normaliza precios agrícolas observados (WFP/MAG) y declarados."""

    engine = "agricultural_price"
    version = ENGINE_VERSION

    def query(
        self,
        *,
        crop_id: str | None = None,
        commodity: str | None = None,
        market: str | None = None,
        price_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        target_unit: str = "t",
        limit: int = 100,
    ) -> dict[str, Any]:
        rows = _load_wfp_prices()
        if price_type:
            pt = price_type.strip().lower()
            if pt not in PRICE_TYPES:
                raise EG.EconomicError(f"price_type inválido: {price_type!r}; use {PRICE_TYPES}")
        else:
            pt = None

        commodities_filter: set[str] | None = None
        if commodity:
            commodities_filter = {commodity.strip().lower()}
        elif crop_id:
            c_key = crop_id.strip().lower()
            if c_key not in AGROSV_TO_WFP_COMMODITIES:
                return EG.economic_envelope(
                    self.engine,
                    result={
                        "available": False,
                        "crop_id": c_key,
                        "count": 0,
                        "records": [],
                        "reason": (
                            f"el cultivo {c_key!r} no tiene serie histórica en WFP El Salvador; "
                            "aporte una cotización o precio de finca con fecha y fuente"
                        ),
                    },
                    sources=["wfp_food_prices_slv"],
                    assumptions=["no se inventan precios para cultivos ausentes"],
                    limitations=["WFP El Salvador cubre maíz blanco, frijol rojo/seda, arroz, sorgo y harina de trigo"],
                    evidence_class="official_statistic",
                    query={"crop_id": crop_id, "market": market, "price_type": price_type},
                )
            commodities_filter = {c.lower() for c in AGROSV_TO_WFP_COMMODITIES[c_key]}

        matched: list[dict[str, Any]] = []
        for r in reversed(rows):  # más recientes primero
            if commodities_filter and r["commodity"].lower() not in commodities_filter:
                continue
            if market and market.strip().lower() not in str(r.get("market") or "").lower():
                continue
            if pt and r["price_type"] != pt:
                continue
            if start_date and r["date"] < start_date:
                continue
            if end_date and r["date"] > end_date:
                continue
            norm_val = round(
                EG.normalize_unit_price(r["price"], r["unit"], target_unit=target_unit), 4
            )
            matched.append(
                EG.make_economic_record(
                    product_or_activity=r["commodity"],
                    geography=f"El Salvador / {r['market']}",
                    observation_date=r["date"],
                    publication_date=r["date"],
                    reference_period=r["date"][:7],
                    currency=r["currency"],
                    unit=r["unit"],
                    source="WFP/HDX El Salvador",
                    methodology=f"monitoreo de mercado ({r['price_type']}, flag={r['price_flag']})",
                    verification_status="INTEGRATED",
                    license_name="CC BY-IGO",
                    evidence_class="official_statistic",
                    value=r["price"],
                    extra={
                        "crop_id": r["crop_id"],
                        "price_type": r["price_type"],
                        "market": r["market"],
                        "department": r["admin1"],
                        "normalized_price": norm_val,
                        "normalized_unit": f"USD/{target_unit}",
                        "normalized_usd_per_kg": r["normalized_usd_per_kg"],
                        "normalized_usd_per_qq46": r["normalized_usd_per_qq46"],
                        "normalized_usd_per_t": r["normalized_usd_per_t"],
                    },
                )
            )
            if len(matched) >= limit:
                break

        return EG.economic_envelope(
            self.engine,
            result={
                "available": bool(matched),
                "count": len(matched),
                "target_unit": f"USD/{target_unit}",
                "records": matched,
                "latest_observation_date": matched[0]["observation_date"] if matched else None,
                "note": "precios mayoristas o minoristas de plaza no equivalen automáticamente a precio recibido en finca",
            },
            sources=["wfp_food_prices_slv"],
            assumptions=["conversión explícita: 45 KG = 45 kg; 46 KG = 46 kg; Libra = 0.45359237 kg; 1 t = 1000 kg"],
            limitations=[
                "las series WFP no distinguen variedades ni grados de humedad específicos",
            ],
            evidence_class="official_statistic",
            query={"crop_id": crop_id, "commodity": commodity, "market": market, "price_type": price_type},
        )

    def normalize_and_compare(self, entries: Iterable[Mapping[str, Any]], *, target_unit: str = "t") -> dict[str, Any]:
        """Normaliza precios heterogéneos verificando unidad, moneda, calidad y tipo."""
        normalized: list[dict[str, Any]] = []
        price_types_seen: set[str] = set()
        currencies_seen: set[str] = set()
        for idx, item in enumerate(entries):
            pt = str(item.get("price_type") or "").strip().lower()
            if pt not in PRICE_TYPES:
                raise EG.EconomicError(f"precio {idx}: price_type inválido {pt!r}")
            cur = str(item.get("currency") or "USD").upper()
            currencies_seen.add(cur)
            price_types_seen.add(pt)
            val = float(item.get("price", -1))
            if val < 0:
                raise EG.EconomicError(f"precio {idx}: price inválido")
            unit = str(item.get("unit") or "kg")
            norm_p = EG.normalize_unit_price(val, unit, target_unit=target_unit)
            normalized.append({
                "product": item.get("product"),
                "quality_grade": item.get("quality_grade") or "unspecified",
                "market": item.get("market"),
                "price_type": pt,
                "currency": cur,
                "original_price": val,
                "original_unit": unit,
                "normalized_price": round(norm_p, 4),
                "normalized_unit": f"{cur}/{target_unit}",
                "observation_date": EG.check_iso_date(str(item.get("observation_date") or ""), "observation_date"),
            })
        if len(currencies_seen) > 1:
            raise EG.EconomicError(f"monedas incompatibles sin tipo de cambio: {sorted(currencies_seen)}")
        return {
            "count": len(normalized),
            "target_unit": target_unit,
            "mixed_price_types": len(price_types_seen) > 1,
            "warning": (
                "se están comparando distintos price_type (p.ej. finca vs mayorista/minorista)"
                if len(price_types_seen) > 1
                else None
            ),
            "entries": normalized,
        }


class PriceHistoryEngine:
    """Analiza tendencias descriptivas, estacionalidad, volatilidad y choques."""

    engine = "price_history"
    version = ENGINE_VERSION

    def analyze(
        self,
        *,
        crop_id: str | None = None,
        commodity: str | None = None,
        market: str = "San Salvador",
        price_type: str = "wholesale",
        series: Iterable[Mapping[str, Any]] | None = None,
        target_unit: str = "t",
    ) -> dict[str, Any]:
        points: list[dict[str, Any]] = []
        if series is not None:
            for item in series:
                d = EG.check_iso_date(str(item["date"]), "date")
                p = EG.normalize_unit_price(
                    float(item["price"]), str(item.get("unit") or target_unit), target_unit=target_unit
                )
                points.append({"date": d, "price": p})
        else:
            q = AgriculturalPriceEngine().query(
                crop_id=crop_id,
                commodity=commodity,
                market=market,
                price_type=price_type,
                target_unit=target_unit,
                limit=500,
            )
            for rec in reversed(q["result"]["records"]):
                points.append({"date": rec["observation_date"], "price": rec["normalized_price"]})

        if len(points) < 2:
            return EG.economic_envelope(
                self.engine,
                result={
                    "available": False,
                    "count": len(points),
                    "reason": "se requieren al menos 2 observaciones históricas para analizar serie",
                },
                sources=["wfp_food_prices_slv"],
                assumptions=["no se extrapola con menos de 2 puntos"],
                limitations=["serie insuficiente para tendencia o volatilidad"],
                evidence_class="official_statistic",
                query={"crop_id": crop_id, "market": market, "price_type": price_type},
            )

        points.sort(key=lambda x: x["date"])
        vals = np.array([p["price"] for p in points], dtype=float)
        mean = float(vals.mean())
        std = float(vals.std(ddof=1))
        cv = (std / mean) if mean > 0 else None
        idx = np.arange(len(vals), dtype=float)
        slope = float(np.polyfit(idx, vals, 1)[0])

        # Estacionalidad mensual descriptiva
        monthly: dict[int, list[float]] = {}
        for p in points:
            m = int(p["date"][5:7])
            monthly.setdefault(m, []).append(p["price"])
        seasonal_index = {
            f"{m:02d}": round(float(np.mean(vs)) / mean, 4) if mean > 0 else None
            for m, vs in sorted(monthly.items())
        }

        # Choques (|z-score| >= 2.0)
        shocks = []
        if std > 0:
            for p in points:
                z = (p["price"] - mean) / std
                if abs(z) >= 2.0:
                    shocks.append({
                        "date": p["date"],
                        "price": round(p["price"], 2),
                        "z_score": round(float(z), 3),
                    })

        return EG.economic_envelope(
            self.engine,
            result={
                "available": True,
                "count": len(points),
                "date_min": points[0]["date"],
                "date_max": points[-1]["date"],
                "unit": f"USD/{target_unit}",
                "descriptive_stats": {
                    "mean": round(mean, 2),
                    "std": round(std, 2),
                    "cv": round(cv, 4) if cv is not None else None,
                    "min": round(float(vals.min()), 2),
                    "max": round(float(vals.max()), 2),
                    "latest": round(float(vals[-1]), 2),
                    "linear_trend_per_obs": round(slope, 3),
                },
                "seasonal_monthly_index": seasonal_index,
                "anomalies_z_ge_2": shocks,
                "long_term_forecast_provided": False,
                "causal_explanation_claimed": False,
            },
            sources=["wfp_food_prices_slv"],
            assumptions=[
                "los índices estacionales describen promedios históricos relativos a la media de la muestra",
            ],
            limitations=[
                "series históricas descriptivas no constituyen pronóstico de largo plazo ni explicación causal",
            ],
            evidence_class="official_statistic",
            query={"crop_id": crop_id, "commodity": commodity, "market": market, "price_type": price_type},
        )


class MarketSupplyDemandEngine:
    """Representa balances de oferta y demanda documentados sin inferir demanda desde precios."""

    engine = "market_supply_demand"
    version = ENGINE_VERSION

    def balance(
        self,
        *,
        crop_id: str,
        reference_year: str,
        production_t: float | None = None,
        imports_t: float | None = None,
        exports_t: float | None = None,
        stock_change_t: float = 0.0,
        source: str = "cap_2025_public_aggregates",
    ) -> dict[str, Any]:
        crop = crop_id.strip().lower()
        cap = EG.load_json_if_exists("cap_2025_public_aggregates.json") or {}
        if production_t is None and crop in cap.get("crops", {}):
            production_t = cap["crops"][crop].get("production_t")

        apparent_supply = None
        if production_t is not None and imports_t is not None and exports_t is not None:
            apparent_supply = round(
                float(production_t) + float(imports_t) - float(exports_t) + float(stock_change_t),
                2,
            )

        missing = [
            name
            for name, val in (
                ("production_t", production_t),
                ("imports_t", imports_t),
                ("exports_t", exports_t),
            )
            if val is None
        ]
        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop,
                "reference_year": reference_year,
                "production_t": production_t,
                "imports_t": imports_t,
                "exports_t": exports_t,
                "stock_change_t": stock_change_t,
                "apparent_domestic_availability_t": apparent_supply,
                "missing_components": missing,
                "is_proxy": apparent_supply is not None,
                "note": (
                    "disponibilidad aparente = producción + importaciones - exportaciones + cambio de inventarios; "
                    "no mide demanda real ni consumo final observado"
                ),
            },
            sources=[source, "bcr_comercio_exterior"],
            assumptions=["no se infiere demanda real de mercado a partir de precios incompletos"],
            limitations=[
                "BCR comercio exterior y FAOSTAT no tienen series automáticas integradas en el repositorio",
            ],
            evidence_class="official_statistic" if not missing else "model_estimate",
            query={"crop_id": crop, "reference_year": reference_year},
        )


class MarketComparisonEngine:
    """Compara mercados alternativos distinguiendo precio bruto vs ingreso neto al productor."""

    engine = "market_comparison"
    version = ENGINE_VERSION

    def compare(
        self,
        *,
        crop_id: str,
        quantity_t: float,
        origin_lon: float | None = None,
        origin_lat: float | None = None,
        transport_cost_per_t_km: float = 0.25,
        alternatives: Iterable[Mapping[str, Any]] | None = None,
        price_type: str = "wholesale",
    ) -> dict[str, Any]:
        if quantity_t <= 0:
            raise EG.EconomicError("quantity_t debe ser > 0")
        alts = list(alternatives or [])
        if not alts:
            # Construye alternativas reales desde mercados WFP + último precio observado
            wfp_mkts = {m["name"]: m for m in _load_wfp_markets()}
            price_q = AgriculturalPriceEngine().query(
                crop_id=crop_id, price_type=price_type, target_unit="t", limit=200
            )
            latest_by_mkt: dict[str, dict[str, Any]] = {}
            for rec in price_q["result"]["records"]:
                mkt = rec["market"]
                if mkt == "National Average" or mkt in latest_by_mkt:
                    continue
                latest_by_mkt[mkt] = rec
            for mkt, rec in latest_by_mkt.items():
                meta = wfp_mkts.get(mkt, {})
                dist_km = 0.0
                if (
                    origin_lon is not None
                    and origin_lat is not None
                    and meta.get("longitude") is not None
                    and meta.get("latitude") is not None
                ):
                    dist_km = round(
                        _haversine_km(origin_lon, origin_lat, meta["longitude"], meta["latitude"]) * 1.3,
                        2,
                    )
                alts.append({
                    "market": mkt,
                    "price_per_t": rec["normalized_price"],
                    "price_type": rec["price_type"],
                    "observation_date": rec["observation_date"],
                    "distance_km": dist_km,
                    "transaction_cost_per_t": 0.0,
                    "storage_cost_per_t": 0.0,
                    "quality_requirements": "estándar de plaza (no especificado)",
                    "payment_terms": "no documentado",
                })

        if not alts:
            raise EG.EconomicError(f"sin precios de mercado disponibles para {crop_id!r}; aporte 'alternatives'")

        compared: list[dict[str, Any]] = []
        for alt in alts:
            p_t = float(alt["price_per_t"])
            dist = float(alt.get("distance_km", 0.0))
            trans_t = float(
                alt["transport_cost_per_t"]
                if alt.get("transport_cost_per_t") is not None
                else dist * transport_cost_per_t_km
            )
            tx_t = float(alt.get("transaction_cost_per_t", 0.0))
            stor_t = float(alt.get("storage_cost_per_t", 0.0))
            net_price_t = p_t - trans_t - tx_t - stor_t
            compared.append({
                "market": alt["market"],
                "price_type": alt.get("price_type", price_type),
                "observation_date": alt.get("observation_date"),
                "distance_km": round(dist, 2),
                "gross_price_per_t": round(p_t, 2),
                "transport_cost_per_t": round(trans_t, 2),
                "transaction_and_storage_per_t": round(tx_t + stor_t, 2),
                "net_producer_price_per_t": round(net_price_t, 2),
                "gross_revenue_usd": round(p_t * quantity_t, 2),
                "net_revenue_usd": round(net_price_t * quantity_t, 2),
                "quality_requirements": alt.get("quality_requirements"),
                "payment_terms": alt.get("payment_terms"),
            })
        compared.sort(key=lambda x: x["net_revenue_usd"], reverse=True)

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop_id,
                "quantity_t": quantity_t,
                "count": len(compared),
                "alternatives": compared,
                "highest_net_market": compared[0]["market"],
            },
            sources=["wfp_food_prices_slv", "wfp_markets_slv"],
            assumptions=[
                "si no se especifica ruta vial, distancia estimada = distancia geodésica × 1.3 (factor de sinuosidad)",
                f"tarifa de transporte por defecto {transport_cost_per_t_km} USD/(t·km) cuando no se aporta flete real",
            ],
            limitations=[
                "precios de plaza mayorista/minorista no garantizan compra al productor ni incluyen comisiones de intermediario no declaradas",
            ],
            evidence_class="model_estimate",
            query={"crop_id": crop_id, "quantity_t": quantity_t},
        )


class MarketOpportunityEngine:
    """Identifica oportunidades potenciales de comercialización (nunca compradores garantizados)."""

    engine = "market_opportunity"
    version = ENGINE_VERSION

    def identify(
        self,
        *,
        crop_id: str,
        quantity_t: float,
        origin_lon: float | None = None,
        origin_lat: float | None = None,
        harvest_month: int | None = None,
        storage_available: bool = False,
        alternatives: Iterable[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        comp = MarketComparisonEngine().compare(
            crop_id=crop_id,
            quantity_t=quantity_t,
            origin_lon=origin_lon,
            origin_lat=origin_lat,
            alternatives=alternatives,
        )["result"]

        seasonal_note = None
        if harvest_month is not None and crop_id in AGROSV_TO_WFP_COMMODITIES:
            hist = PriceHistoryEngine().analyze(crop_id=crop_id, market="San Salvador", price_type="wholesale")["result"]
            if hist.get("available"):
                s_idx = hist.get("seasonal_monthly_index", {}).get(f"{int(harvest_month):02d}")
                seasonal_note = {
                    "harvest_month": harvest_month,
                    "historical_seasonal_index": s_idx,
                    "interpretation": (
                        "mes históricamente por debajo de la media anual; almacenar puede ser relevante si es viable"
                        if s_idx and s_idx < 0.98
                        else "mes en o por encima de la media estacional"
                    ),
                }

        opportunities = []
        for idx, alt in enumerate(comp["alternatives"], start=1):
            opportunities.append({
                "rank": idx,
                "market": alt["market"],
                "opportunity_status": "potential_opportunity_not_guaranteed",
                "net_producer_price_per_t": alt["net_producer_price_per_t"],
                "estimated_net_revenue_usd": alt["net_revenue_usd"],
                "distance_km": alt["distance_km"],
                "storage_supported": storage_available,
            })

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop_id,
                "quantity_t": quantity_t,
                "guaranteed_buyer": False,
                "seasonal_context": seasonal_note,
                "potential_opportunities": opportunities,
            },
            sources=["wfp_food_prices_slv", "wfp_markets_slv"],
            assumptions=["las oportunidades se ordenan por ingreso neto estimado tras transporte declarado"],
            limitations=[
                "toda salida representa una oportunidad potencial, nunca un contrato o comprador confirmado",
            ],
            evidence_class="model_estimate",
            query={"crop_id": crop_id, "quantity_t": quantity_t, "harvest_month": harvest_month},
        )


__all__ = [
    "AGROSV_TO_WFP_COMMODITIES",
    "AgriculturalMarketEngine",
    "AgriculturalPriceEngine",
    "CHANNEL_TYPES",
    "MarketComparisonEngine",
    "MarketOpportunityEngine",
    "MarketSupplyDemandEngine",
    "PRICE_TYPES",
    "PriceHistoryEngine",
    "WFP_TO_AGROSV_CROP",
]
