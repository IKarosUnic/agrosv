"""AGROSV Phase 8 — Subsistema E: Cadena de Suministro y Logística Agrícola.

Contiene los 6 motores del Subsistema E:
1. AgriculturalSupplyChainEngine
2. AgriculturalLogisticsEngine
3. MarketAccessEngine
4. StorageAndPostHarvestEngine
5. AgriculturalDistributionEngine
6. AgriculturalValueChainEngine
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

from .. import config as C
from ..engines.territorial import CoverageError, validate_coordinate
from . import governance as EG
from .markets import _haversine_km, _load_osm_markets, _load_wfp_markets

ENGINE_VERSION = EG.ENGINE_VERSION

SUPPLY_CHAIN_STAGES = (
    "input_supplier",
    "producer",
    "collection_center",
    "cooperative",
    "processor",
    "wholesaler",
    "retailer",
    "exporter",
    "consumer",
)

# Parámetros poscosecha de referencia bibliográfica por grupo de cultivo
POSTHARVEST_REF_PARAMS: dict[str, dict[str, Any]] = {
    "maize": {"safe_moisture_pct": 13.0, "shelf_life_days_ambient": 180, "perishability": "low", "temp_c": "15-25"},
    "beans": {"safe_moisture_pct": 12.0, "shelf_life_days_ambient": 180, "perishability": "low", "temp_c": "15-25"},
    "rice": {"safe_moisture_pct": 13.0, "shelf_life_days_ambient": 180, "perishability": "low", "temp_c": "15-25"},
    "sorghum": {"safe_moisture_pct": 13.0, "shelf_life_days_ambient": 180, "perishability": "low", "temp_c": "15-25"},
    "coffee": {"safe_moisture_pct": 11.5, "shelf_life_days_ambient": 240, "perishability": "low", "temp_c": "15-22"},
    "tomato": {"safe_moisture_pct": None, "shelf_life_days_ambient": 7, "perishability": "high", "temp_c": "10-13"},
    "sweet_pepper": {"safe_moisture_pct": None, "shelf_life_days_ambient": 10, "perishability": "high", "temp_c": "7-10"},
    "cucumber": {"safe_moisture_pct": None, "shelf_life_days_ambient": 10, "perishability": "high", "temp_c": "10-12"},
    "onion": {"safe_moisture_pct": None, "shelf_life_days_ambient": 60, "perishability": "medium", "temp_c": "0-5 / seco"},
    "mango": {"safe_moisture_pct": None, "shelf_life_days_ambient": 7, "perishability": "high", "temp_c": "12-13"},
    "avocado": {"safe_moisture_pct": None, "shelf_life_days_ambient": 8, "perishability": "high", "temp_c": "5-12"},
}


def _nearest_road_distance_m(lon: float, lat: float) -> dict[str, Any]:
    """Calcula la distancia real en metros (EPSG:32616) a la vía OSM más cercana."""
    if not C.INFRA_GPKG.exists():
        return {"available": False, "reason": "infrastructure.gpkg no disponible"}
    import geopandas as gpd
    import pyproj
    from shapely.geometry import Point

    pad = 0.04  # ~4.4 km
    roads = gpd.read_file(
        C.INFRA_GPKG,
        layer="roads",
        bbox=(lon - pad, lat - pad, lon + pad, lat + pad),
    )
    if roads.empty:
        return {"available": True, "nearest_road_m": None, "within_radius_m": 4400, "note": "sin vías OSM en radio de ~4.4 km"}
    transformer = pyproj.Transformer.from_crs(C.CRS_STORAGE, C.CRS_METRIC, always_xy=True)
    x_m, y_m = transformer.transform(lon, lat)
    pt_m = Point(x_m, y_m)
    roads_m = roads.to_crs(C.CRS_METRIC)
    dists = roads_m.geometry.distance(pt_m)
    idx_min = dists.idxmin()
    row = roads.loc[idx_min]
    return {
        "available": True,
        "nearest_road_m": round(float(dists.loc[idx_min]), 1),
        "road_name": row.get("name") if "name" in roads.columns else None,
        "road_class": row.get("fclass") if "fclass" in roads.columns else (row.get("highway") if "highway" in roads.columns else None),
    }


class AgriculturalSupplyChainEngine:
    """Mapea cadenas de suministro distinguiendo vínculos evidenciados vs hipotéticos."""

    engine = "agricultural_supply_chain"
    version = ENGINE_VERSION

    def map_chain(
        self,
        *,
        crop_id: str,
        links: Iterable[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        crop = crop_id.strip().lower()
        chain_links = list(links or [])
        if not chain_links:
            # Estructura conceptual explícitamente marcada como hipotética cuando no hay evidencia
            chain_links = [
                {"from": "input_supplier", "to": "producer", "status": "hypothetical", "evidence": None},
                {"from": "producer", "to": "collection_center", "status": "hypothetical", "evidence": None},
                {"from": "collection_center", "to": "wholesaler", "status": "hypothetical", "evidence": None},
                {"from": "wholesaler", "to": "retailer", "status": "hypothetical", "evidence": None},
                {"from": "retailer", "to": "consumer", "status": "hypothetical", "evidence": None},
            ]
        parsed: list[dict[str, Any]] = []
        for idx, lk in enumerate(chain_links):
            frm = str(lk.get("from") or "").strip().lower()
            to = str(lk.get("to") or "").strip().lower()
            if frm not in SUPPLY_CHAIN_STAGES or to not in SUPPLY_CHAIN_STAGES:
                raise EG.EconomicError(f"enlace {idx}: etapa inválida ({frm!r} -> {to!r}); use {SUPPLY_CHAIN_STAGES}")
            status = str(lk.get("status") or ("evidenced" if lk.get("evidence") else "hypothetical")).lower()
            if status not in {"evidenced", "hypothetical"}:
                raise EG.EconomicError(f"enlace {idx}: status debe ser 'evidenced' o 'hypothetical'")
            if status == "evidenced" and not lk.get("evidence"):
                raise EG.EconomicError(f"enlace {idx}: marcado 'evidenced' sin campo 'evidence'")
            parsed.append({
                "from": frm,
                "to": to,
                "status": status,
                "evidence": lk.get("evidence"),
                "channel_notes": lk.get("notes"),
            })

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop,
                "stages_vocabulary": list(SUPPLY_CHAIN_STAGES),
                "links": parsed,
                "evidenced_links_count": sum(1 for l in parsed if l["status"] == "evidenced"),
                "hypothetical_links_count": sum(1 for l in parsed if l["status"] == "hypothetical"),
            },
            sources=["osm_markets_slv", "wfp_markets_slv"],
            assumptions=["todo vínculo sin evidencia documental se marca explícitamente como hypothetical"],
            limitations=["no existen flujos comerciales por actor a nivel nacional en el repositorio"],
            evidence_class="model_estimate",
            query={"crop_id": crop},
        )


class AgriculturalLogisticsEngine:
    """Evalúa acceso vial OSM, distancia a mercados y costo logístico."""

    engine = "agricultural_logistics"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        lon: float,
        lat: float,
        crop_id: str,
        quantity_t: float = 1.0,
        transport_cost_per_t_km: float = 0.25,
        vehicle_type: str = "pickup_or_light_truck",
        routed_travel_minutes: float | None = None,
        market_limit: int = 5,
    ) -> dict[str, Any]:
        try:
            lon_v, lat_v = validate_coordinate(lon, lat)
        except CoverageError as exc:
            raise EG.EconomicError(str(exc)) from None
        if quantity_t <= 0:
            raise EG.EconomicError("quantity_t debe ser > 0")

        road_info = _nearest_road_distance_m(lon_v, lat_v)
        markets = _load_wfp_markets() + _load_osm_markets()
        candidates: list[dict[str, Any]] = []
        for m in markets:
            if m.get("latitude") is None or m.get("longitude") is None:
                continue
            geo_km = _haversine_km(lon_v, lat_v, m["longitude"], m["latitude"])
            est_road_km = geo_km * 1.3
            est_cost = est_road_km * quantity_t * transport_cost_per_t_km
            candidates.append({
                "market_id": m["market_id"],
                "name": m["name"],
                "source": m["source"],
                "geodesic_km": round(geo_km, 2),
                "estimated_road_km_detour_1_3": round(est_road_km, 2),
                "estimated_transport_cost_usd": round(est_cost, 2),
            })
        candidates.sort(key=lambda x: x["geodesic_km"])
        perish = POSTHARVEST_REF_PARAMS.get(crop_id.strip().lower(), {}).get("perishability", "unspecified")

        return EG.economic_envelope(
            self.engine,
            result={
                "origin": {"lon": lon_v, "lat": lat_v},
                "crop_id": crop_id,
                "perishability": perish,
                "quantity_t": quantity_t,
                "vehicle_type": vehicle_type,
                "nearest_osm_road": road_info,
                "nearest_markets": candidates[:market_limit],
                "actual_travel_time_minutes": routed_travel_minutes,
                "travel_time_note": (
                    "tiempo aportado por el llamador"
                    if routed_travel_minutes is not None
                    else "tiempo real de viaje no calculado (sin motor de ruteo con velocidades viales actuales)"
                ),
            },
            sources=["osm_markets_slv", "wfp_markets_slv"],
            assumptions=[
                "distancia caminera aproximada = geodésica × 1.3 cuando no existe grafo ruteado",
                f"tarifa supuesta de flete {transport_cost_per_t_km} USD/(t·km)",
            ],
            limitations=[
                "no afirma tiempos reales de viaje sin datos de estado de vía ni ruteo completo",
            ],
            evidence_class="model_estimate",
            query={"lon": lon_v, "lat": lat_v, "crop_id": crop_id, "quantity_t": quantity_t},
        )


class MarketAccessEngine:
    """Distingue proximidad geográfica de acceso económico práctico al mercado."""

    engine = "market_access"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        lon: float,
        lat: float,
        crop_id: str,
        quantity_t: float = 1.0,
        expected_gross_value_usd: float | None = None,
        seasonal_road_passable: bool = True,
        transport_available: bool = True,
        meets_quality_requirements: bool = True,
        min_market_volume_t: float | None = None,
    ) -> dict[str, Any]:
        log_res = AgriculturalLogisticsEngine().evaluate(
            lon=lon, lat=lat, crop_id=crop_id, quantity_t=quantity_t, market_limit=3
        )["result"]
        nearest = log_res["nearest_markets"][0] if log_res["nearest_markets"] else None
        road_m = (log_res.get("nearest_osm_road") or {}).get("nearest_road_m")

        geo_score = 0.0
        if nearest:
            geo_score = max(0.0, min(1.0, 1.0 - nearest["geodesic_km"] / 80.0))

        barriers: list[str] = []
        if not seasonal_road_passable:
            barriers.append("inaccesibilidad vial estacional (invierno/lluvias)")
        if not transport_available:
            barriers.append("sin disponibilidad de transporte de carga")
        if not meets_quality_requirements:
            barriers.append("no cumple requisitos de calidad del comprador")
        if min_market_volume_t is not None and quantity_t < min_market_volume_t:
            barriers.append(f"volumen ({quantity_t} t) menor al mínimo del canal ({min_market_volume_t} t)")
        if road_m is not None and road_m > 2000:
            barriers.append(f"distancia a vía OSM más cercana > 2 km ({road_m} m)")

        transport_cost = nearest["estimated_transport_cost_usd"] if nearest else None
        freight_share = (
            round(transport_cost / expected_gross_value_usd, 4)
            if transport_cost is not None and expected_gross_value_usd and expected_gross_value_usd > 0
            else None
        )
        practical_accessible = (len(barriers) == 0) and (freight_share is None or freight_share < 0.35)

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop_id,
                "nearest_market": nearest,
                "nearest_road_m": road_m,
                "geographic_proximity_index": round(geo_score, 3),
                "freight_share_of_gross_value": freight_share,
                "practical_economic_access": practical_accessible,
                "barriers": barriers,
                "distinction_note": "cercanía geográfica no implica acceso práctico ni rentabilidad de comercialización",
            },
            sources=["osm_markets_slv", "wfp_markets_slv"],
            assumptions=["umbral heurístico de carga logística: flete >= 35% del valor bruto limita acceso práctico"],
            limitations=["no verifica condiciones físicas actuales de caminos rurales ni contratos"],
            evidence_class="model_estimate",
            query={"lon": lon, "lat": lat, "crop_id": crop_id, "quantity_t": quantity_t},
        )


class StorageAndPostHarvestEngine:
    """Evalúa capacidad, costo y deterioro poscosecha con parámetros por cultivo."""

    engine = "storage_post_harvest"
    version = ENGINE_VERSION

    def assess(
        self,
        *,
        crop_id: str,
        quantity_t: float,
        storage_days: int = 30,
        storage_capacity_t: float | None = None,
        storage_cost_per_t_day: float = 0.0,
        observed_moisture_pct: float | None = None,
        loss_fraction: float | None = None,
        loss_source: str | None = None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        crop = crop_id.strip().lower()
        if quantity_t < 0 or storage_days < 0:
            raise EG.EconomicError("quantity_t y storage_days deben ser >= 0")
        if loss_fraction is not None:
            if not (0.0 <= loss_fraction <= 1.0):
                raise EG.EconomicError("loss_fraction debe estar en [0, 1]")
            if loss_fraction > 0 and not loss_source:
                raise EG.EconomicError("loss_fraction > 0 requiere 'loss_source'")

        ref = POSTHARVEST_REF_PARAMS.get(crop, {})
        safe_m = ref.get("safe_moisture_pct")
        moisture_risk = None
        if observed_moisture_pct is not None and safe_m is not None:
            moisture_risk = "elevated" if observed_moisture_pct > safe_m else "within_reference"

        shelf_life = ref.get("shelf_life_days_ambient")
        shelf_exceeded = (shelf_life is not None and storage_days > shelf_life)
        capacity_shortfall_t = (
            max(0.0, quantity_t - storage_capacity_t)
            if storage_capacity_t is not None
            else None
        )
        total_storage_cost = round(quantity_t * storage_days * storage_cost_per_t_day, 2)
        lost_t = round(quantity_t * loss_fraction, 4) if loss_fraction is not None else None

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop,
                "currency": currency.upper(),
                "quantity_t": quantity_t,
                "storage_days": storage_days,
                "reference_parameters": ref or None,
                "moisture_status": moisture_risk,
                "shelf_life_exceeded": shelf_exceeded,
                "storage_capacity_t": storage_capacity_t,
                "capacity_shortfall_t": round(capacity_shortfall_t, 4) if capacity_shortfall_t is not None else None,
                "total_storage_cost": total_storage_cost,
                "estimated_loss_t": lost_t,
                "loss_source": loss_source,
            },
            sources=["crop_parameters_catalog"],
            assumptions=["parámetros poscosecha son rangos técnicos de referencia, no mediciones de bodega"],
            limitations=["no aplica tasas genéricas de pérdida cuando el usuario no declara loss_fraction con fuente"],
            evidence_class="institutional_reference",
            query={"crop_id": crop, "quantity_t": quantity_t, "storage_days": storage_days},
        )


class AgriculturalDistributionEngine:
    """Evalúa escenarios y rutas de distribución manteniendo ruteo separado del costo."""

    engine = "agricultural_distribution"
    version = ENGINE_VERSION

    def plan(
        self,
        *,
        origin_lon: float,
        origin_lat: float,
        quantity_t: float,
        routes: Iterable[Mapping[str, Any]] | None = None,
        cost_per_t_km: float = 0.25,
    ) -> dict[str, Any]:
        lon_v, lat_v = validate_coordinate(origin_lon, origin_lat)
        if quantity_t <= 0:
            raise EG.EconomicError("quantity_t debe ser > 0")

        route_list = list(routes or [])
        if not route_list:
            # Deriva rutas físicas candidatas desde mercados reales sin fijar márgenes comerciales
            mkts = AgriculturalLogisticsEngine().evaluate(
                lon=lon_v, lat=lat_v, crop_id="maize", quantity_t=quantity_t,
                transport_cost_per_t_km=cost_per_t_km, market_limit=5,
            )["result"]["nearest_markets"]
            for m in mkts:
                route_list.append({
                    "route_id": m["market_id"],
                    "destination": m["name"],
                    "distance_km": m["estimated_road_km_detour_1_3"],
                    "distance_basis": "geodesic_x_1.3",
                    "allocated_share": 1.0 if len(route_list) == 0 else 0.0,
                })

        evaluated = []
        for r in route_list:
            dist = float(r["distance_km"])
            share = float(r.get("allocated_share", 1.0))
            vol = quantity_t * share
            rate = float(r.get("cost_per_t_km", cost_per_t_km))
            evaluated.append({
                "route_id": r.get("route_id"),
                "destination": r["destination"],
                "physical_routing": {
                    "distance_km": round(dist, 2),
                    "distance_basis": r.get("distance_basis", "user_supplied"),
                },
                "economic_assumptions": {
                    "allocated_volume_t": round(vol, 4),
                    "cost_per_t_km": rate,
                    "estimated_freight_usd": round(vol * dist * rate, 2),
                },
            })

        return EG.economic_envelope(
            self.engine,
            result={
                "origin": {"lon": lon_v, "lat": lat_v},
                "quantity_t": quantity_t,
                "routes": evaluated,
                "routing_separated_from_cost_assumptions": True,
            },
            sources=["osm_markets_slv", "wfp_markets_slv"],
            assumptions=["enrutamiento físico y supuestos económicos de tarifa se reportan en bloques separados"],
            limitations=["sin grafo vial completo con pendientes ni restricciones de peso vehicular"],
            evidence_class="model_estimate",
            query={"lon": lon_v, "lat": lat_v, "quantity_t": quantity_t},
        )


class AgriculturalValueChainEngine:
    """Analiza creación y distribución de valor sin inferir poder de mercado desde brechas."""

    engine = "agricultural_value_chain"
    version = ENGINE_VERSION

    def analyze(
        self,
        *,
        crop_id: str,
        producer_price_per_t: float | None = None,
        wholesale_price_per_t: float | None = None,
        retail_price_per_t: float | None = None,
        processing_value_added_per_t: float = 0.0,
        transport_cost_per_t: float = 0.0,
        market: str = "San Salvador",
        currency: str = "USD",
    ) -> dict[str, Any]:
        # Si faltan mayorista/minorista y existe serie WFP, consultar últimas observaciones reales
        wfp_used = False
        if (wholesale_price_per_t is None or retail_price_per_t is None) and crop_id in {"maize", "beans", "rice", "sorghum"}:
            from .markets import AgriculturalPriceEngine

            pe = AgriculturalPriceEngine()
            if wholesale_price_per_t is None:
                wq = pe.query(crop_id=crop_id, market=market, price_type="wholesale", target_unit="t", limit=1)
                if wq["result"]["records"]:
                    wholesale_price_per_t = wq["result"]["records"][0]["normalized_price"]
                    wfp_used = True
            if retail_price_per_t is None:
                rq = pe.query(crop_id=crop_id, market=market, price_type="retail", target_unit="t", limit=1)
                if rq["result"]["records"]:
                    retail_price_per_t = rq["result"]["records"][0]["normalized_price"]
                    wfp_used = True

        producer_share_of_retail = (
            round(producer_price_per_t / retail_price_per_t, 4)
            if producer_price_per_t is not None and retail_price_per_t and retail_price_per_t > 0
            else None
        )
        wholesale_share_of_retail = (
            round(wholesale_price_per_t / retail_price_per_t, 4)
            if wholesale_price_per_t is not None and retail_price_per_t and retail_price_per_t > 0
            else None
        )
        wholesale_retail_spread = (
            round(retail_price_per_t - wholesale_price_per_t, 2)
            if wholesale_price_per_t is not None and retail_price_per_t is not None
            else None
        )

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop_id,
                "market": market,
                "currency": currency.upper(),
                "producer_price_per_t": producer_price_per_t,
                "wholesale_price_per_t": wholesale_price_per_t,
                "retail_price_per_t": retail_price_per_t,
                "producer_share_of_retail": producer_share_of_retail,
                "wholesale_share_of_retail": wholesale_share_of_retail,
                "wholesale_to_retail_spread_per_t": wholesale_retail_spread,
                "processing_value_added_per_t": processing_value_added_per_t,
                "transport_cost_per_t": transport_cost_per_t,
                "wfp_data_used": wfp_used,
                "market_power_inferred": False,
                "interpretation_rule": (
                    "las diferencias de precio incluyen mermas, empaque, flete, crédito y servicios; "
                    "no permiten inferir explotación ni poder de mercado sin estructura de costos completa"
                ),
            },
            sources=["wfp_food_prices_slv"] if wfp_used else ["agrosv_scenario"],
            assumptions=["todos los precios comparados están normalizados a USD/t"],
            limitations=[
                "WFP no reporta precios al productor en finca; si no se aporta, producer_share_of_retail es null",
            ],
            evidence_class="official_statistic" if wfp_used else "model_estimate",
            query={"crop_id": crop_id, "market": market},
        )


__all__ = [
    "AgriculturalDistributionEngine",
    "AgriculturalLogisticsEngine",
    "AgriculturalSupplyChainEngine",
    "AgriculturalValueChainEngine",
    "MarketAccessEngine",
    "POSTHARVEST_REF_PARAMS",
    "SUPPLY_CHAIN_STAGES",
    "StorageAndPostHarvestEngine",
]
