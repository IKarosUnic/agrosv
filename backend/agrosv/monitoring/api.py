"""AGROSV — API de monitorización agrícola (Fase 7) bajo `/api/monitoring`.

Prefijo nuevo: los contratos de Fase 1–6 y de `/api/onboarding` no cambian.
Convenciones: `lat`/`lon` en EPSG:4326, `null` = sin dato, unidades explícitas,
`evidence_class` en cada respuesta científica.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

from .. import config as C
from ..engines import governance as G5
from . import governance as G
from .alerts import (AgriculturalAlertEngine, AgriculturalEarlyWarningEngine,
                     AgriculturalNotificationEngine, AlertPrioritizationEngine,
                     AlertVerificationEngine)
from .change import AgriculturalRemoteSensingEngine, CropChangeDetectionEngine
from .crop_health import (CropAnomalyDetectionEngine, CropHealthMonitoringEngine,
                          ThermalStressEngine, VegetationStressEngine)
from .field import AgriculturalFieldVerificationEngine
from .indices import VegetationIndexEngine
from .integration import (AgriculturalMonitoringAnalysisEngine,
                          AgriculturalMonitoringEngine,
                          AgriculturalRiskMappingEngine,
                          CropMonitoringTimelineEngine)
from .knowledge import DISEASES, PESTS
from .pests import (AgriculturalPhytosanitaryEngine, DiseaseRiskEngine,
                    PestKnowledgeEngine, PestRiskEngine,
                    PlantDiseaseKnowledgeEngine)
from .risks import (AgriculturalRiskEngine, CropLossRiskEngine,
                    DroughtMonitoringEngine, FloodAndExcessWaterRiskEngine,
                    HeatAndClimateRiskEngine, SoilDegradationRiskEngine)
from .satellites import SatelliteDataEngine
from .timeseries import SatelliteTimeSeriesEngine
from .water_stress import WaterStressDetectionEngine

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])
SERVICE_VERSION = G.ENGINE_VERSION

satellites = SatelliteDataEngine()
indices = VegetationIndexEngine()
timeseries = SatelliteTimeSeriesEngine()
change = CropChangeDetectionEngine()
remote = AgriculturalRemoteSensingEngine()
health = CropHealthMonitoringEngine()
vegetation_stress = VegetationStressEngine()
water = WaterStressDetectionEngine()
thermal = ThermalStressEngine()
anomalies = CropAnomalyDetectionEngine()
pests = PestKnowledgeEngine()
diseases = PlantDiseaseKnowledgeEngine()
pest_risk = PestRiskEngine(pests)
disease_risk = DiseaseRiskEngine(diseases)
phytosanitary = AgriculturalPhytosanitaryEngine()
risk = AgriculturalRiskEngine()
drought = DroughtMonitoringEngine()
flood = FloodAndExcessWaterRiskEngine()
heat = HeatAndClimateRiskEngine()
soil_degradation = SoilDegradationRiskEngine()
crop_loss = CropLossRiskEngine()
alerts = AgriculturalAlertEngine()
verification = AlertVerificationEngine(alerts)
prioritization = AlertPrioritizationEngine()
notifications = AgriculturalNotificationEngine()
warning = AgriculturalEarlyWarningEngine()
field = AgriculturalFieldVerificationEngine()
monitoring = AgriculturalMonitoringEngine()
timeline = CropMonitoringTimelineEngine()
mapping = AgriculturalRiskMappingEngine()
analysis = AgriculturalMonitoringAnalysisEngine()

_ALLOWED_DIRS = (C.DATA / "external", C.DATA / "reference",
                 C.DATA / "samples", C.DATA / "processed")
_ALLOWED_SUFFIXES = {".tif", ".tiff", ".json", ".geojson"}


def _headers(engine: str) -> dict[str, str]:
    return {"X-AGROSV-Engine": engine, "X-AGROSV-Version": SERVICE_VERSION,
            "X-AGROSV-Monitoring-Phase": "7"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, (KeyError, FileNotFoundError)):
        return HTTPException(404, str(exc).strip("'\""))
    if isinstance(exc, G5.SourceUnavailableError):
        return HTTPException(503, str(exc))
    if isinstance(exc, (G.MonitoringError, ValueError)):
        return HTTPException(400, str(exc))
    return HTTPException(500, f"{type(exc).__name__}: {exc}")


def _respond(engine: str, fn) -> JSONResponse:
    try:
        return JSONResponse(content=_jsonable(fn()), headers=_headers(engine))
    except Exception as exc:  # noqa: BLE001 — se traduce a HTTP
        raise _error(exc) from None


def _safe_path(raw: str | None) -> Any:
    if not raw:
        raise HTTPException(400, "falta `path`")
    path = (C.ROOT / raw).resolve()
    if not any(str(path).startswith(str(d.resolve())) for d in _ALLOWED_DIRS):
        raise HTTPException(400, "ruta fuera de data/{external,reference,samples,processed}")
    if path.suffix.lower() not in _ALLOWED_SUFFIXES:
        raise HTTPException(400, f"extensión no admitida: {path.suffix}")
    if not path.exists():
        raise HTTPException(404, f"archivo no encontrado: {raw}")
    return path


def _array(payload: dict[str, Any], key: str) -> np.ndarray:
    if key not in payload:
        raise HTTPException(400, f"falta `{key}`")
    return np.asarray(payload[key], dtype="float32")


# --- metadatos ---------------------------------------------------------------
@router.get("/meta", summary="Motores, fuentes y política científica de Fase 7")
def meta() -> JSONResponse:
    return _respond("monitoring", lambda: {
        "service_version": SERVICE_VERSION,
        "subsystems": {
            "A_satellite": ["SatelliteDataEngine", "VegetationIndexEngine",
                            "CropChangeDetectionEngine",
                            "SatelliteTimeSeriesEngine",
                            "AgriculturalRemoteSensingEngine"],
            "B_crop_health": ["CropHealthMonitoringEngine",
                              "VegetationStressEngine",
                              "WaterStressDetectionEngine",
                              "ThermalStressEngine",
                              "CropAnomalyDetectionEngine"],
            "C_phytosanitary": ["PestKnowledgeEngine",
                                "PlantDiseaseKnowledgeEngine", "PestRiskEngine",
                                "DiseaseRiskEngine",
                                "AgriculturalPhytosanitaryEngine"],
            "D_risk": ["AgriculturalRiskEngine", "DroughtMonitoringEngine",
                       "FloodAndExcessWaterRiskEngine",
                       "HeatAndClimateRiskEngine",
                       "SoilDegradationRiskEngine", "CropLossRiskEngine"],
            "E_alerts": ["AgriculturalAlertEngine",
                         "AgriculturalEarlyWarningEngine",
                         "AlertPrioritizationEngine",
                         "AlertVerificationEngine",
                         "AgriculturalNotificationEngine"],
            "F_integrated": ["AgriculturalMonitoringEngine",
                             "CropMonitoringTimelineEngine",
                             "AgriculturalRiskMappingEngine",
                             "AgriculturalFieldVerificationEngine",
                             "AgriculturalMonitoringAnalysisEngine"],
        },
        "counts": {"satellite_sources": len(satellites.sources()["sources"]),
                   "indices": len(indices.specs()["indices"]),
                   "pests": len(PESTS), "diseases": len(DISEASES)},
        "policy": {
            "llm_used": False,
            "satellite_scenes_ingested": False,
            "synthetic_test_fixtures_labeled": True,
            "alert_is_not_diagnosis": True,
            "risk_is_not_confirmed_event": True,
            "forecast_separate_from_observation": True,
            "gaps_are_null": True,
        },
        "conventions": {"crs_query": "EPSG:4326", "nodata": "null",
                        "units": "explícitas por campo"},
    })


@router.get("/sources", summary="Catálogo de fuentes satelitales evaluadas")
def sources() -> JSONResponse:
    return _respond("satellite_data", satellites.sources)


@router.get("/sources/{source_id}", summary="Ficha de una fuente satelital")
def source(source_id: str) -> JSONResponse:
    return _respond("satellite_data", lambda: satellites.source(source_id))


@router.post("/satellite/inspect", summary="Metadatos de un ráster local")
def inspect_satellite(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    path = _safe_path(payload.get("path"))
    return _respond("satellite_data", lambda: satellites.inspect(path))


@router.post("/satellite/stac", summary="Leer un Item/ItemCollection STAC local")
def stac(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    path = _safe_path(payload.get("path"))
    return _respond("satellite_data", lambda: satellites.parse_stac(path))


@router.post("/satellite/search-plan", summary="Plan de búsqueda STAC (sin ejecutar)")
def search_plan(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    bbox = payload.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise HTTPException(400, "bbox debe ser [oeste, sur, este, norte]")
    return _respond("satellite_data", lambda: satellites.stac_search_plan(
        source_id=payload.get("source_id", "sentinel2_msi"),
        bbox=tuple(float(v) for v in bbox),
        start=payload.get("start", "2024-01-01"),
        end=payload.get("end", "2024-12-31"),
        limit=int(payload.get("limit", 20))))


# --- índices -----------------------------------------------------------------
@router.get("/indices", summary="Fichas de los índices espectrales")
def index_specs() -> JSONResponse:
    return _respond("vegetation_index", indices.specs)


@router.post("/indices", summary="Calcular un índice sobre bandas en memoria")
def compute_index(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    name = payload.get("name")
    bands = payload.get("bands") or {}
    if not name or not isinstance(bands, dict):
        raise HTTPException(400, "se requieren `name` y `bands`")
    arrays = {k: np.asarray(v, dtype="float32") for k, v in bands.items()}
    cloud = payload.get("cloud_mask")
    result = indices.compute(
        name, arrays,
        cloud_mask=None if cloud is None else np.asarray(cloud, dtype=bool),
        sensor=payload.get("sensor"),
        savi_l=float(payload.get("savi_l", 0.5)))
    return _respond("vegetation_index", lambda: {
        **result.stats(),
        "cannot_conclude": indices.describe(name)["cannot_conclude"],
        "evidence_class": "satellite_derived",
    })


@router.post("/indices/raster", summary="Calcular un índice desde un GeoTIFF local")
def compute_index_raster(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    path = _safe_path(payload.get("path"))
    bands = payload.get("bands") or {}
    if not bands:
        raise HTTPException(400, "faltan bandas (nombre lógico → índice 1-based)")
    bounds = payload.get("bounds")
    observation = satellites.read(
        path, bands={k: int(v) for k, v in bands.items()},
        bounds=tuple(bounds) if bounds else None,
        cloud_band=payload.get("cloud_band"),
        reflectance_scale=payload.get("reflectance_scale"),
        reflectance_offset=float(payload.get("reflectance_offset", 0.0)),
        sensor=payload.get("sensor"))
    index_name = payload.get("index", "ndvi")
    result = indices.compute(index_name, observation.bands,
                             cloud_mask=observation.valid_mask,
                             sensor=payload.get("sensor"))
    return _respond("vegetation_index", lambda: {
        "raster": observation.as_dict(), "index": result.stats(),
        "evidence_class": "satellite_derived",
    })


# --- series temporales -------------------------------------------------------
@router.post("/timeseries", summary="Construir una serie válida (sin interpolación)")
def build_timeseries(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    records = payload.get("records") or []
    return _respond("satellite_time_series", lambda: timeseries.build(
        records, value_key=payload.get("value_key", "value"),
        max_cloud_pct=float(payload.get("max_cloud_pct", 30.0))))


@router.post("/timeseries/anomaly", summary="Anomalía estacional robusta")
def time_anomaly(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    records = payload.get("records") or []
    target = payload.get("target_date")
    if not target:
        raise HTTPException(400, "falta `target_date`")
    return _respond("satellite_time_series", lambda: {
        **timeseries.anomaly(
            records, target_date=target,
            window_days=int(payload.get("window_days", 15)),
            min_years=int(payload.get("min_years", 3)),
            min_obs=int(payload.get("min_obs", 6))),
        "evidence_class": "satellite_derived",
    })


@router.post("/change", summary="Detección de cambio entre dos fechas")
def change_detection(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("crop_change_detection", lambda: change.compare(
        _array(payload, "before"), _array(payload, "after"),
        threshold=float(payload.get("threshold", 0.1)),
        before_sensor=payload.get("before_sensor"),
        after_sensor=payload.get("after_sensor"),
        before_resolution_m=payload.get("before_resolution_m"),
        after_resolution_m=payload.get("after_resolution_m"),
        harmonized=bool(payload.get("harmonized", False)),
        before_date=payload.get("before_date"),
        after_date=payload.get("after_date")))


# --- catálogos fitosanitarios ------------------------------------------------
@router.get("/pests", summary="Catálogo de plagas documentadas")
def pest_catalog(crop: str | None = None, presence: str | None = None) -> JSONResponse:
    return _respond("pest_knowledge", lambda: pests.list(crop=crop, presence=presence))


@router.get("/pests/audit", summary="Auditoría de vacíos del catálogo de plagas")
def pest_audit() -> JSONResponse:
    return _respond("pest_knowledge", pests.audit)


@router.get("/pests/{pest_id}", summary="Ficha de una plaga")
def pest(pest_id: str) -> JSONResponse:
    return _respond("pest_knowledge", lambda: pests.get(pest_id))


@router.get("/diseases", summary="Catálogo de enfermedades documentadas")
def disease_catalog(crop: str | None = None, presence: str | None = None) -> JSONResponse:
    return _respond("plant_disease_knowledge",
                    lambda: diseases.list(crop=crop, presence=presence))


@router.get("/diseases/{disease_id}", summary="Ficha de una enfermedad")
def disease(disease_id: str) -> JSONResponse:
    return _respond("plant_disease_knowledge",
                    lambda: diseases.get(disease_id))


@router.post("/pest-risk", summary="Riesgo de plaga (idoneidad ≠ presencia)")
def pest_risk_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    pest_id = payload.get("pest_id")
    if not pest_id:
        raise HTTPException(400, "falta `pest_id`")
    return _respond("pest_risk", lambda: pest_risk.assess(
        pest_id, conditions=payload.get("conditions") or {},
        crop_id=payload.get("crop_id"), stage=payload.get("stage"),
        rules=payload.get("rules"), rules_source=payload.get("rules_source")))


@router.post("/disease-risk", summary="Riesgo de enfermedad (no diagnóstico)")
def disease_risk_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    disease_id = payload.get("disease_id")
    if not disease_id:
        raise HTTPException(400, "falta `disease_id`")
    return _respond("disease_risk", lambda: disease_risk.assess(
        disease_id, conditions=payload.get("conditions") or {},
        crop_id=payload.get("crop_id"), stage=payload.get("stage"),
        rules=payload.get("rules"), rules_source=payload.get("rules_source")))


@router.get("/phytosanitary", summary="Registros fitosanitarios y su procedencia")
def phyto_list(kind: str | None = None, crop_id: str | None = None) -> JSONResponse:
    return _respond("agricultural_phytosanitary",
                    lambda: phytosanitary.list(kind=kind, crop_id=crop_id))


@router.post("/phytosanitary", summary="Registrar evidencia fitosanitaria")
def phyto_add(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_phytosanitary", lambda: phytosanitary.add(
        kind=payload.get("kind", "community_report"),
        statement=payload.get("statement", ""),
        crop_id=payload.get("crop_id"),
        geographic_scope=payload.get("geographic_scope", ""),
        source=payload.get("source", ""),
        observed_on=payload.get("observed_on", ""),
        official=bool(payload.get("official", False)),
        confidence=payload.get("confidence")))


# --- sanidad del cultivo -----------------------------------------------------
@router.post("/crop-health", summary="Estado interpretativo del cultivo")
def crop_health(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("crop_health_monitoring", lambda: health.assess(
        payload.get("crop_id"), payload.get("stage", ""),
        ndvi_anomaly=payload.get("ndvi_anomaly"),
        ndmi_anomaly=payload.get("ndmi_anomaly"),
        rainfall_anomaly=payload.get("rainfall_anomaly"),
        temperature_anomaly=payload.get("temperature_anomaly"),
        n_observations=int(payload.get("n_observations", 0)),
        baseline_years=int(payload.get("baseline_years", 0)),
        variety=payload.get("variety"), management=payload.get("management")))


@router.post("/vegetation-stress", summary="Indicadores de estrés de vegetación")
def vegetation_stress_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("vegetation_stress", lambda: vegetation_stress.assess(
        ndvi_z=payload.get("ndvi_z"), ndmi_z=payload.get("ndmi_z"),
        rainfall_z=payload.get("rainfall_z"),
        temperature_z=payload.get("temperature_z"),
        soil_moisture_deficit=payload.get("soil_moisture_deficit")))


@router.post("/water-stress", summary="Cinco categorías de sequía, por separado")
def water_stress(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("water_stress_detection", lambda: water.assess(
        precip_mm=payload.get("precip_mm"), et0_mm=payload.get("et0_mm"),
        etc_mm=payload.get("etc_mm"), taw_mm=payload.get("taw_mm"),
        depletion_mm=payload.get("depletion_mm"),
        irrigation_mm=float(payload.get("irrigation_mm", 0.0)),
        ndmi=payload.get("ndmi"), ndmi_threshold=payload.get("ndmi_threshold"),
        ndmi_threshold_source=payload.get("ndmi_threshold_source")))


@router.post("/thermal-stress", summary="Exposición térmica sobre umbral declarado")
def thermal_stress(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("thermal_stress", lambda: thermal.assess(
        payload.get("crop_id"), payload.get("stage", ""),
        payload.get("tmax_c") or [],
        threshold_c=float(payload.get("threshold_c", 35.0)),
        threshold_source=payload.get("threshold_source", ""),
        lst_c=payload.get("lst_c"), tmin_c=payload.get("tmin_c"),
        tbase_c=payload.get("tbase_c")))


@router.post("/crop-anomaly", summary="Detección transparente de anomalías")
def crop_anomaly(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    values = payload.get("values") or []
    return _respond("crop_anomaly_detection", lambda: anomalies.detect(
        values, method=payload.get("method", "robust_z"),
        baseline=payload.get("baseline"),
        threshold=float(payload.get("threshold", 2.0)),
        window=int(payload.get("window", 3)),
        baseline_period=payload.get("baseline_period")))


# --- riesgos -----------------------------------------------------------------
@router.post("/risk", summary="Riesgo = peligro × exposición × vulnerabilidad")
def risk_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_risk", lambda: risk.assess(
        hazard=payload.get("hazard"), exposure=payload.get("exposure"),
        vulnerability=payload.get("vulnerability"),
        require_all=bool(payload.get("require_all", True)),
        detail=payload.get("detail")))


@router.post("/drought", summary="Sequías por categoría e índice estandarizado")
def drought_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    if payload.get("monthly_mm"):
        return _respond("drought_monitoring",
                        lambda: drought.standardized_precipitation_index(
                            payload["monthly_mm"],
                            scale=int(payload.get("scale", 3)),
                            min_years=int(payload.get("min_years", 30))))
    if payload.get("precipitation_mm") and payload.get("wet_threshold_mm"):
        return _respond("drought_monitoring",
                        lambda: drought.consecutive_dry_days(
                            payload["precipitation_mm"],
                            wet_threshold_mm=float(payload["wet_threshold_mm"])))
    return _respond("drought_monitoring", lambda: drought.assess(
        precip_3m_mm=payload.get("precip_3m_mm"),
        precip_percentile=payload.get("precip_percentile"),
        et0_3m_mm=payload.get("et0_3m_mm"),
        soil_deficit_fraction=payload.get("soil_deficit_fraction"),
        cdd_days=payload.get("cdd_days"),
        ndvi_anomaly=payload.get("ndvi_anomaly")))


@router.post("/flood-risk", summary="Exposición potencial a exceso de agua")
def flood_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("flood_excess_water_risk", lambda: flood.assess(
        rainfall_24h_mm=payload.get("rainfall_24h_mm"),
        rainfall_72h_mm=payload.get("rainfall_72h_mm"),
        slope_deg=payload.get("slope_deg"),
        soil_infiltration_mm_h=payload.get("soil_infiltration_mm_h"),
        drainage_distance_m=payload.get("drainage_distance_m"),
        official_flood_zone=payload.get("official_flood_zone")))


@router.post("/heat-risk", summary="Riesgo de calor y déficit de lluvia")
def heat_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("heat_climate_risk", lambda: heat.assess(
        tmax_c=payload.get("tmax_c"),
        threshold_c=float(payload.get("threshold_c", 35.0)),
        threshold_source=payload.get("threshold_source", ""),
        rainfall_mm=payload.get("rainfall_mm"), et0_mm=payload.get("et0_mm"),
        crop_id=payload.get("crop_id"), stage=payload.get("stage"),
        forecast=payload.get("forecast")))


@router.post("/soil-degradation", summary="Susceptibilidad de degradación del suelo")
def soil_degradation_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("soil_degradation_risk", lambda: soil_degradation.assess(
        slope_deg=float(payload.get("slope_deg", 0.0)),
        vegetation_cover=float(payload.get("vegetation_cover", 0.0)),
        rainfall_erosivity=payload.get("rainfall_erosivity"),
        soil_erodibility=payload.get("soil_erodibility"),
        land_cover_change=payload.get("land_cover_change"),
        salinity=payload.get("salinity"),
        organic_matter_g_kg=payload.get("organic_matter_g_kg")))


@router.post("/crop-loss", summary="Impacto potencial vs daño observado")
def crop_loss_endpoint(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("crop_loss_risk", lambda: crop_loss.exposure(
        payload.get("crop_id"), stage=payload.get("stage"),
        hazards=payload.get("hazards") or {},
        management_factor=payload.get("management_factor"),
        observed_damage_fraction=payload.get("observed_damage_fraction"),
        potential_yield_t_ha=payload.get("potential_yield_t_ha"),
        expected_yield_t_ha=payload.get("expected_yield_t_ha")))


# --- alertas -----------------------------------------------------------------
@router.post("/alerts", summary="Crear alerta estructurada con supresión de duplicados")
def create_alert(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_alert", lambda: alerts.create(
        category=payload.get("category", ""),
        geographic_scope=payload.get("geographic_scope") or {},
        observation_period=payload.get("observation_period") or {},
        detection_method=payload.get("detection_method", ""),
        risk_level=payload.get("risk_level", "low"),
        evidence=payload.get("evidence") or [],
        confidence=payload.get("confidence", "low"),
        source_datasets=payload.get("source_datasets") or [],
        crop_id=payload.get("crop_id"),
        recommended_verification=payload.get("recommended_verification"),
        review_days=int(payload.get("review_days", 14)),
        uncertainty=payload.get("uncertainty")))


@router.get("/alerts", summary="Listar alertas")
def list_alerts(status: str | None = None, category: str | None = None,
                include_expired: bool = False) -> JSONResponse:
    return _respond("agricultural_alert", lambda: alerts.list(
        status=status, category=category, include_expired=include_expired))


@router.get("/alerts/{alert_id}", summary="Detalle de una alerta")
def get_alert(alert_id: str) -> JSONResponse:
    return _respond("agricultural_alert", lambda: alerts.get(alert_id))


@router.post("/alerts/expire", summary="Expirar alertas vencidas")
def expire_alerts(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    return _respond("agricultural_alert",
                    lambda: alerts.expire(on=payload.get("on")))


@router.post("/alerts/prioritize", summary="Priorizar alertas con motivo explícito")
def prioritize_alerts(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    items = payload.get("alerts") or alerts.list()["alerts"]
    return _respond("alert_prioritization", lambda: prioritization.prioritize(
        items, crop_sensitivity=payload.get("crop_sensitivity") or {},
        exposure_area_km2=payload.get("exposure_area_km2") or {},
        evidence_quality=payload.get("evidence_quality") or {},
        on=payload.get("on")))


@router.post("/alerts/{alert_id}/transition", summary="Cambiar estado de una alerta")
def transition_alert(alert_id: str, payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_alert", lambda: alerts.transition(
        alert_id, payload.get("status", ""),
        reason=payload.get("reason", "")))


@router.post("/alerts/{alert_id}/verify", summary="Registrar y aplicar verificación")
def verify_alert(alert_id: str, payload: dict[str, Any] = Body(...)) -> JSONResponse:
    def _run() -> dict[str, Any]:
        event = verification.submit(
            alert_id, verifier_type=payload.get("verifier_type", ""),
            outcome=payload.get("outcome", ""),
            evidence=payload.get("evidence") or [],
            observed_on=payload.get("observed_on", ""),
            confidence=float(payload.get("confidence", 0.0)),
            notes=payload.get("notes", ""),
            geographic_reference=payload.get("geographic_reference"))
        evaluation = verification.evaluate(alert_id)
        if payload.get("apply"):
            evaluation = verification.apply(alert_id)
        return {"event": event, "evaluation": evaluation}

    return _respond("alert_verification", _run)


@router.post("/early-warning", summary="Aviso por pronóstico, observación o institución")
def early_warning(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    mode = payload.get("mode", "forecast")
    if mode == "forecast":
        return _respond("agricultural_early_warning",
                        lambda: warning.forecast_warning(
                            payload.get("forecast") or {},
                            crop_id=payload.get("crop_id"),
                            threshold_c=float(payload.get("threshold_c", 35.0)),
                            threshold_source=payload.get("threshold_source", ""),
                            stage=payload.get("stage")))
    if mode == "observation":
        return _respond("agricultural_early_warning",
                        lambda: warning.observation_warning(
                            category=payload.get("category", ""),
                            observed_value=float(payload.get("observed_value", 0)),
                            threshold=float(payload.get("threshold", 0)),
                            threshold_source=payload.get("threshold_source", ""),
                            geographic_scope=payload.get("geographic_scope") or {},
                            evidence=payload.get("evidence") or []))
    if mode == "official":
        return _respond("agricultural_early_warning",
                        lambda: warning.official_warning(
                            institution=payload.get("institution", ""),
                            notice_id=payload.get("notice_id", ""),
                            statement=payload.get("statement", ""),
                            valid_from=payload.get("valid_from", "")))
    raise HTTPException(400, "mode debe ser forecast, observation u official")


@router.get("/notifications", summary="Cola local de notificaciones")
def notification_queue(channel: str | None = None) -> JSONResponse:
    return _respond("agricultural_notification",
                    lambda: notifications.pending(channel=channel))


@router.post("/notifications", summary="Encolar una alerta según preferencias")
def enqueue_notification(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    def _run() -> dict[str, Any]:
        alert = alerts.get(payload.get("alert_id", ""))
        return notifications.enqueue(
            alert, preferences=payload.get("preferences") or {},
            redact=bool(payload.get("redact", False)))

    return _respond("agricultural_notification", _run)


@router.post("/notifications/sync", summary="Sincronizar la cola local")
def sync_notifications(payload: dict[str, Any] = Body(default={})) -> JSONResponse:
    return _respond("agricultural_notification",
                    lambda: notifications.sync(
                        channel=payload.get("channel", "offline_sync")))


# --- observaciones de campo --------------------------------------------------
@router.post("/field-observations", summary="Enviar una observación de campo")
def submit_field(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_field_verification",
                    lambda: field.submit(payload))


@router.get("/field-observations", summary="Listar observaciones de campo")
def list_field(status: str | None = None, obs_type: str | None = None,
               crop_id: str | None = None) -> JSONResponse:
    return _respond("agricultural_field_verification",
                    lambda: field.list(status=status, obs_type=obs_type,
                                       crop_id=crop_id))


@router.get("/field-observations/{observation_id}", summary="Vista pública de una observación")
def get_field(observation_id: str) -> JSONResponse:
    return _respond("agricultural_field_verification",
                    lambda: field.public_view(observation_id))


@router.post("/field-observations/{observation_id}/review",
             summary="Revisar una observación (no la convierte en verificada)")
def review_field(observation_id: str,
                 payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_field_verification", lambda: field.review(
        observation_id, reviewer_id=payload.get("reviewer_id", ""),
        decision=payload.get("decision", ""), notes=payload.get("notes", "")))


# --- integración -------------------------------------------------------------
@router.post("/timeline", summary="Línea temporal de eventos (sin relleno)")
def build_timeline(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("crop_monitoring_timeline", lambda: timeline.build(
        payload.get("events") or [],
        expected_interval_days=payload.get("expected_interval_days")))


@router.post("/risk-map", summary="GeoJSON de una capa de riesgo")
def risk_map(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_risk_mapping", lambda: mapping.to_feature_collection(
        payload.get("points") or [],
        indicator=payload.get("indicator", ""),
        source=payload.get("source", ""),
        observation_date=payload.get("observation_date", ""),
        resolution_m=float(payload.get("resolution_m", 0.0)),
        methodology=payload.get("methodology", ""),
        confidence=payload.get("confidence", "low"),
        limitations=payload.get("limitations") or [],
        modeled=bool(payload.get("modeled", True))))


@router.post("/analysis", summary="Análisis descriptivo de la monitorización")
def monitoring_analysis(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_monitoring_analysis", lambda: analysis.analyze(
        payload.get("records") or [],
        alerts=payload.get("alerts"),
        verification_events=payload.get("verification_events")))


@router.post("/status", summary="Estado integrado de capas para un punto")
def monitoring_status(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _respond("agricultural_monitoring", lambda: monitoring.status(
        lat=float(payload.get("lat", 0.0)), lon=float(payload.get("lon", 0.0)),
        crop_id=payload.get("crop_id"), scale=payload.get("scale", "municipal"),
        resolution_m=payload.get("resolution_m"),
        satellite_index=payload.get("satellite_index"),
        anomalies=payload.get("anomalies"), risks=payload.get("risks"),
        alert_summary=payload.get("alert_summary"),
        include_context=bool(payload.get("include_context", False))))
