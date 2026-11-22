"""AGROSV Phase 8 — Gobernanza de datos económicos, unidades y procedencia (§12).

Reglas transversales:
1. Cada registro económico preserva identificador, producto/actividad, referencia
   geográfica, fecha de observación/publicación, periodo, moneda, unidad,
   fuente, metodología, estado de verificación y licencia.
2. Nunca se sobrescriben precios o costos históricos sin conservar su historial.
3. No se mezclan monedas ni unidades sin conversión explícita y probada.
4. No se confunde observación real con referencia, estimación de modelo o
   escenario sintético.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Iterable

from .. import config as C
from ..agriculture import governance as AG

ENGINE_VERSION = "8.0.0"
SERVICE = "agrosv.economics"

ECON_DATA_DIR = C.DATA / "standardized" / "economics"

ECONOMIC_STATUSES = (
    "DISCOVERED",
    "ACCESS_PENDING",
    "DOWNLOADED",
    "PARSED",
    "VALIDATED",
    "INTEGRATED",
    "RESTRICTED",
    "UNAVAILABLE",
    "REJECTED",
)

ECONOMIC_EVIDENCE_CLASSES = (
    "observed_transaction",
    "producer_reported",
    "official_statistic",
    "institutional_reference",
    "commercial_quotation",
    "model_estimate",
    "synthetic_scenario",
    "hypothetical_assumption",
)

# Conversiones explícitas para El Salvador
MANZANA_TO_HA = 0.70
HA_TO_MANZANA = 1.0 / MANZANA_TO_HA
KG_PER_QUINTAL_SV = 46.0      # Quintal métrico/comercial salvadoreño (100 lb españolas ≈ 46 kg)
KG_PER_WFP_BAG_45 = 45.0      # Saco reportado por WFP/MAG en CSV HDX ("45 KG")
KG_PER_LB = 0.45359237
KG_PER_TON = 1000.0

MASS_TO_KG: dict[str, float] = {
    "kg": 1.0,
    "kilogram": 1.0,
    "kilogramo": 1.0,
    "g": 0.001,
    "t": KG_PER_TON,
    "ton": KG_PER_TON,
    "tm": KG_PER_TON,
    "mt": KG_PER_TON,
    "qq": KG_PER_QUINTAL_SV,
    "quintal": KG_PER_QUINTAL_SV,
    "46 kg": 46.0,
    "45 kg": 45.0,
    "lb": KG_PER_LB,
    "libra": KG_PER_LB,
    "libras": KG_PER_LB,
    "50 pounds": 50.0 * KG_PER_LB,
    "100 lb": 100.0 * KG_PER_LB,
}

AREA_TO_HA: dict[str, float] = {
    "ha": 1.0,
    "hectare": 1.0,
    "hectarea": 1.0,
    "hectárea": 1.0,
    "mz": MANZANA_TO_HA,
    "manzana": MANZANA_TO_HA,
    "m2": 0.0001,
    "km2": 100.0,
    "acre": 0.40468564224,
}


class EconomicError(ValueError):
    """Error de validación o conversión económica en Fase 8."""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8"))
    return f"{prefix}-{digest.hexdigest()[:12]}"


def convert_mass(value: float, from_unit: str, to_unit: str) -> float:
    """Convierte masa entre unidades agrícolas salvadoreñas e internacionales."""
    u_from = str(from_unit).strip().lower()
    u_to = str(to_unit).strip().lower()
    if u_from not in MASS_TO_KG:
        raise EconomicError(f"unidad de masa desconocida: {from_unit!r}")
    if u_to not in MASS_TO_KG:
        raise EconomicError(f"unidad de masa destino desconocida: {to_unit!r}")
    kg = float(value) * MASS_TO_KG[u_from]
    return kg / MASS_TO_KG[u_to]


def convert_area(value: float, from_unit: str, to_unit: str) -> float:
    """Convierte superficie entre ha, mz (0.70 ha), m², km² y acres."""
    u_from = str(from_unit).strip().lower()
    u_to = str(to_unit).strip().lower()
    if u_from not in AREA_TO_HA:
        raise EconomicError(f"unidad de área desconocida: {from_unit!r}")
    if u_to not in AREA_TO_HA:
        raise EconomicError(f"unidad de área destino desconocida: {u_to!r}")
    ha = float(value) * AREA_TO_HA[u_from]
    return ha / AREA_TO_HA[u_to]


def normalize_unit_price(
    price: float,
    unit: str,
    *,
    target_unit: str = "kg",
) -> float:
    """Normaliza un precio por unidad de masa (p.ej. USD/45 KG -> USD/kg o USD/t)."""
    u_src = str(unit).strip().lower()
    u_dst = str(target_unit).strip().lower()
    if u_src not in MASS_TO_KG or u_dst not in MASS_TO_KG:
        raise EconomicError(f"no se puede normalizar precio de {unit!r} a {target_unit!r}")
    price_per_kg = float(price) / MASS_TO_KG[u_src]
    return price_per_kg * MASS_TO_KG[u_dst]


def check_iso_date(value: str, field_name: str = "date") -> str:
    try:
        date.fromisoformat(str(value)[:10])
    except ValueError:
        raise EconomicError(f"{field_name} debe ser ISO YYYY-MM-DD: recibido {value!r}") from None
    return str(value)[:10]


def make_economic_record(
    *,
    product_or_activity: str,
    geography: str,
    observation_date: str,
    publication_date: str | None,
    reference_period: str,
    currency: str,
    unit: str,
    source: str,
    methodology: str,
    verification_status: str,
    license_name: str,
    evidence_class: str,
    value: Any,
    version: str = ENGINE_VERSION,
    uncertainty: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye un registro económico completo conforme a §12."""
    if verification_status not in ECONOMIC_STATUSES:
        raise EconomicError(f"estado de verificación inválido: {verification_status!r}")
    if evidence_class not in ECONOMIC_EVIDENCE_CLASSES:
        raise EconomicError(f"evidence_class inválido: {evidence_class!r}")
    obs_date = check_iso_date(observation_date, "observation_date")
    pub_date = check_iso_date(publication_date, "publication_date") if publication_date else None
    record = {
        "record_id": stable_id(
            "ECN", product_or_activity, geography, obs_date, unit, currency, source, value
        ),
        "product_or_activity": product_or_activity,
        "geography": geography,
        "observation_date": obs_date,
        "publication_date": pub_date,
        "reference_period": reference_period,
        "currency": currency,
        "unit": unit,
        "value": value,
        "source": source,
        "methodology": methodology,
        "verification_status": verification_status,
        "evidence_class": evidence_class,
        "license": license_name,
        "version": version,
        "uncertainty": uncertainty,
    }
    if extra:
        record.update(extra)
    return record


def economic_envelope(
    engine: str,
    *,
    result: dict[str, Any],
    sources: Iterable[str],
    assumptions: Iterable[str],
    limitations: Iterable[str],
    evidence_class: str,
    synthetic: bool = False,
    processing: list[dict[str, Any]] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if evidence_class not in ECONOMIC_EVIDENCE_CLASSES:
        raise EconomicError(f"evidence_class inválido: {evidence_class!r}")
    lim_list = list(limitations)
    if not lim_list:
        raise EconomicError("todo resultado económico debe declarar limitaciones")
    return {
        "engine": engine,
        "engine_version": ENGINE_VERSION,
        "service": SERVICE,
        "timestamp_utc": utcnow(),
        "evidence_class": evidence_class,
        "synthetic": bool(synthetic),
        "llm_used": False,
        "sources": [SOURCE_REGISTRY.get(s, {"dataset_id": s}) for s in sources],
        "assumptions": list(assumptions),
        "limitations": lim_list,
        "processing": processing or [],
        "query": query or {},
        "result": result,
    }


# Registro estructurado de fuentes nacionales e internacionales (§11)
SOURCE_REGISTRY: dict[str, dict[str, Any]] = {
    "wfp_food_prices_slv": {
        "dataset_id": "wfp_food_prices_slv",
        "name": "WFP Food Prices for El Salvador (HDX)",
        "institution": "World Food Programme (WFP) / fuentes nacionales (MAG)",
        "url": "https://data.humdata.org/dataset/wfp-food-prices-for-el-salvador",
        "license": "CC BY-IGO",
        "geographic_coverage": "El Salvador (14 mercados departamentales + promedio nacional)",
        "temporal_coverage": "2005-01-15 a 2026-10-15",
        "variables": ["price", "usdprice", "pricetype", "commodity", "unit", "market"],
        "units": {"price": "USD por unidad reportada (45 KG, 46 KG, Libra, 50 Pounds)"},
        "update_frequency": "mensual",
        "methodology": "monitoreo de mercados mayoristas y minoristas",
        "access_restrictions": "ninguna (descarga abierta CSV)",
        "integration_status": "INTEGRATED",
        "known_limitations": [
            "cubre 6 productos básicos (frijol rojo/seda, maíz blanco, arroz, sorgo, harina de trigo); no cubre café, caña ni hortalizas",
            "precios mayoristas y minoristas de plaza no equivalen a precio en finca",
        ],
    },
    "wfp_markets_slv": {
        "dataset_id": "wfp_markets_slv",
        "name": "WFP Markets El Salvador",
        "institution": "World Food Programme (WFP)",
        "url": "https://data.humdata.org/dataset/wfp-food-prices-for-el-salvador",
        "license": "CC BY-IGO",
        "geographic_coverage": "El Salvador (71 mercados georreferenciados)",
        "temporal_coverage": "actualizado 2026",
        "variables": ["market_id", "market", "admin1", "admin2", "latitude", "longitude"],
        "units": {"coordinates": "EPSG:4326"},
        "update_frequency": "periódica",
        "methodology": "directorio georreferenciado de plazas de monitoreo",
        "access_restrictions": "ninguna",
        "integration_status": "INTEGRATED",
        "known_limitations": ["no incluye volumen transado ni capacidad de almacenamiento"],
    },
    "osm_markets_slv": {
        "dataset_id": "osm_markets_slv",
        "name": "OpenStreetMap El Salvador — Mercados y Red Vial",
        "institution": "OpenStreetMap contributors",
        "url": "https://www.openstreetmap.org/",
        "license": "ODbL 1.0",
        "geographic_coverage": "El Salvador (39 puntos `mercado` + red vial nacional)",
        "temporal_coverage": "corte local Fase 1–4",
        "variables": ["osm_id", "name", "category", "facility", "lon", "lat"],
        "units": {"coordinates": "EPSG:4326", "distances": "km (EPSG:32616)"},
        "update_frequency": "estático local",
        "methodology": "extracción OSM a GeoPackage local",
        "access_restrictions": "atribución ODbL",
        "integration_status": "INTEGRATED",
        "known_limitations": ["completitud desigual en mercados rurales y centros de acopio"],
    },
    "cap_2025_public_aggregates": {
        "dataset_id": "cap_2025_public_aggregates",
        "name": "BCR — V Censo Agropecuario y I de Pesca 2025 (agregados públicos)",
        "institution": "Banco Central de Reserva (BCR)",
        "url": "https://www.bcr.gob.sv/",
        "license": "Datos agregados públicos; microdatos restringidos (art. 25 LEC)",
        "geographic_coverage": "Nacional y participaciones departamentales seleccionadas",
        "temporal_coverage": "ciclo mayo 2024 – abril 2025 (publicado 2026)",
        "variables": ["area_mz", "production_qq", "cattle_head", "poultry_birds"],
        "units": {"area": "manzanas / hectáreas", "production": "quintales / toneladas"},
        "update_frequency": "decenal / entregas 2026",
        "methodology": "censo agropecuario digital BCR/FAO",
        "access_restrictions": "microdatos restringidos por ley; solo agregados preliminares",
        "integration_status": "VALIDATED",
        "known_limitations": [
            "cifras preliminares sin tabulado municipal abierto",
            "no cubre todos los cultivos frutales u hortícolas en entregas públicas 1–2",
        ],
    },
    "worldbank_agri_share": {
        "dataset_id": "worldbank_agri_share",
        "name": "Banco Mundial WDI — Indicadores agrícolas El Salvador",
        "institution": "World Bank",
        "url": "https://api.worldbank.org/v2/country/SLV/indicator/AG.LND.AGRI.ZS",
        "license": "CC BY 4.0",
        "geographic_coverage": "Nacional (El Salvador)",
        "temporal_coverage": "1961–2024",
        "variables": ["AG.LND.AGRI.ZS"],
        "units": {"AG.LND.AGRI.ZS": "% superficie terrestre"},
        "update_frequency": "anual",
        "methodology": "compilación FAO/WDI",
        "access_restrictions": "ninguna (API sufrió timeouts en consulta en vivo 2026-11-22)",
        "integration_status": "INTEGRATED",
        "known_limitations": ["solo indicador de uso de tierra local; consultas WDI adicionales dieron timeout"],
    },
    "mag_anuarios_y_costos": {
        "dataset_id": "mag_anuarios_y_costos",
        "name": "MAG — Anuarios Agropecuarios, Costos de Producción y Guía de Insumos",
        "institution": "Ministerio de Agricultura y Ganadería (MAG)",
        "url": "https://www.mag.gob.sv/",
        "license": "Publicación institucional",
        "geographic_coverage": "El Salvador",
        "temporal_coverage": "2021–2024",
        "variables": ["costos_por_cultivo", "precios_insumos", "produccion_anuario"],
        "units": {"costos": "USD/mz", "produccion": "qq"},
        "update_frequency": "anual / periódica",
        "methodology": "boletines y anuarios en PDF maquetado",
        "access_restrictions": "PDF sin serie tabular abierta automatizable; URL 2022-23 retornó 404",
        "integration_status": "ACCESS_PENDING",
        "known_limitations": ["requiere extracción tabular auditada de PDF y verificación humana"],
    },
    "centa_boletines": {
        "dataset_id": "centa_boletines",
        "name": "CENTA — Guías técnicas y coeficientes de cultivo",
        "institution": "Centro Nacional de Tecnología Agropecuaria y Forestal (CENTA)",
        "url": "https://www.centa.gob.sv/",
        "license": "Publicación institucional",
        "geographic_coverage": "El Salvador",
        "temporal_coverage": "estático",
        "variables": ["requerimientos_tecnicos", "densidad", "fertilizacion"],
        "units": {"varias": "kg/ha, qq/mz, jornales/mz"},
        "update_frequency": "irregular",
        "methodology": "boletines técnicos PDF",
        "access_restrictions": "403 a cliente automatizado",
        "integration_status": "RESTRICTED",
        "known_limitations": ["descarga automatizada bloqueada (HTTP 403)"],
    },
    "faostat": {
        "dataset_id": "faostat",
        "name": "FAOSTAT — Producción, Precios al Productor y Comercio",
        "institution": "FAO",
        "url": "https://www.fao.org/faostat/",
        "license": "CC BY-NC-SA 3.0 IGO (verificar uso)",
        "geographic_coverage": "Nacional (El Salvador)",
        "temporal_coverage": "1961–presente",
        "variables": ["production", "yield", "producer_prices", "trade"],
        "units": {"production": "t", "yield": "hg/ha", "prices": "USD/t"},
        "update_frequency": "anual",
        "methodology": "estadísticas nacionales armonizadas FAO",
        "access_restrictions": "API retornó 521 y bulk 403 en auditoría previa",
        "integration_status": "UNAVAILABLE",
        "known_limitations": ["endpoints bloqueados desde este entorno"],
    },
    "fao_giews_amis": {
        "dataset_id": "fao_giews_amis",
        "name": "FAO GIEWS / AMIS — Alerta alimentaria y mercados",
        "institution": "FAO",
        "url": "https://www.fao.org/giews/",
        "license": "CC BY-IGO",
        "geographic_coverage": "Global / Centroamérica",
        "temporal_coverage": "mensual",
        "variables": ["price_warnings", "commodity_balances"],
        "units": {"indices": "adimensional"},
        "update_frequency": "mensual",
        "methodology": "monitoreo global",
        "access_restrictions": "sin serie tabular directa integrada",
        "integration_status": "DISCOVERED",
        "known_limitations": ["cobertura agregada global/regional"],
    },
    "bcr_comercio_exterior": {
        "dataset_id": "bcr_comercio_exterior",
        "name": "BCR — Estadísticas de Comercio Exterior Agropecuario",
        "institution": "Banco Central de Reserva (BCR)",
        "url": "https://www.bcr.gob.sv/",
        "license": "Datos públicos institucionales",
        "geographic_coverage": "Nacional",
        "temporal_coverage": "mensual / anual",
        "variables": ["imports_usd", "imports_kg", "exports_usd", "exports_kg"],
        "units": {"valor": "USD", "volumen": "kg"},
        "update_frequency": "mensual",
        "methodology": "registros aduaneros SAC",
        "access_restrictions": "consultas en portal interactivo sin descarga masiva directa",
        "integration_status": "ACCESS_PENDING",
        "known_limitations": ["pendiente de ingesta tabular por partida arancelaria"],
    },
    "cepal_iica_ifad_usda_comtrade": {
        "dataset_id": "cepal_iica_ifad_usda_comtrade",
        "name": "CEPAL / IICA / IFAD / USDA PSD / UN Comtrade",
        "institution": "Organismos internacionales",
        "url": "https://comtradeplus.un.org/",
        "license": "Mixta (algunas API requieren suscripción/token)",
        "geographic_coverage": "Nacional / regional",
        "temporal_coverage": "anual",
        "variables": ["trade_flows", "macro_agri", "supply_utilization"],
        "units": {"varias": "USD, t"},
        "update_frequency": "anual",
        "methodology": "compilaciones estadísticas internacionales",
        "access_restrictions": "Comtrade requiere clave para volumen completo; no integrados localmente",
        "integration_status": "DISCOVERED",
        "known_limitations": ["no descargados en esta fase"],
    },
}


def load_json_if_exists(filename: str) -> Any | None:
    path = ECON_DATA_DIR / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "AREA_TO_HA",
    "ECONOMIC_EVIDENCE_CLASSES",
    "ECONOMIC_STATUSES",
    "ECON_DATA_DIR",
    "ENGINE_VERSION",
    "EconomicError",
    "HA_TO_MANZANA",
    "KG_PER_LB",
    "KG_PER_QUINTAL_SV",
    "KG_PER_TON",
    "KG_PER_WFP_BAG_45",
    "MANZANA_TO_HA",
    "MASS_TO_KG",
    "SERVICE",
    "SOURCE_REGISTRY",
    "check_iso_date",
    "convert_area",
    "convert_mass",
    "economic_envelope",
    "load_json_if_exists",
    "make_economic_record",
    "normalize_unit_price",
    "stable_id",
    "utcnow",
]
