"""Pruebas de la Fase 7 de monitorización agrícola.

Cubren los seis subsistemas: satélite, sanidad, fitosanidad, riesgos, alertas e
integración. Los rásteres y series de prueba son **fixtures sintéticos**
declarados; no representan observaciones reales. Las pruebas de API usan el
TestClient y no requieren red.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from agrosv import config as C
from agrosv.api import app
from agrosv.monitoring import governance as G
from agrosv.monitoring.alerts import (AgriculturalAlertEngine,
                                      AgriculturalEarlyWarningEngine,
                                      AgriculturalNotificationEngine,
                                      AlertPrioritizationEngine,
                                      AlertVerificationEngine)
from agrosv.monitoring.change import (AgriculturalRemoteSensingEngine,
                                      CropChangeDetectionEngine)
from agrosv.monitoring.crop_health import (CropAnomalyDetectionEngine,
                                           CropHealthMonitoringEngine,
                                           ThermalStressEngine,
                                           VegetationStressEngine)
from agrosv.monitoring.field import AgriculturalFieldVerificationEngine
from agrosv.monitoring.indices import VegetationIndexEngine
from agrosv.monitoring.integration import (AgriculturalMonitoringAnalysisEngine,
                                           AgriculturalRiskMappingEngine,
                                           CropMonitoringTimelineEngine)
from agrosv.monitoring.knowledge import DISEASES, PESTS
from agrosv.monitoring.pests import (AgriculturalPhytosanitaryEngine,
                                     DiseaseRiskEngine, PestKnowledgeEngine,
                                     PestRiskEngine,
                                     PlantDiseaseKnowledgeEngine)
from agrosv.monitoring.risks import (AgriculturalRiskEngine,
                                     CropLossRiskEngine,
                                     DroughtMonitoringEngine,
                                     FloodAndExcessWaterRiskEngine,
                                     HeatAndClimateRiskEngine,
                                     SoilDegradationRiskEngine)
from agrosv.monitoring.satellites import (REQUIRED_SOURCE_FIELDS,
                                          SatelliteDataEngine)
from agrosv.monitoring.timeseries import SatelliteTimeSeriesEngine
from agrosv.monitoring.water_stress import WaterStressDetectionEngine


# --- fixtures ----------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _write_scene(path):
    """Fixture sintético: 4×4, nir/red/SCL, nodata y una nube."""
    import rasterio
    from rasterio.transform import from_origin

    nir = np.full((4, 4), 0.6, dtype="float32")
    red = np.full((4, 4), 0.2, dtype="float32")
    scl = np.full((4, 4), 4, dtype="uint8")
    scl[0, 0] = 9        # nube alta
    nir[0, 1] = -9999.0  # nodata
    transform = from_origin(-89.30, 13.80, 0.001, 0.001)
    with rasterio.open(
            path, "w", driver="GTiff", height=4, width=4, count=3,
            dtype="float32", crs="EPSG:4326", transform=transform,
            nodata=-9999.0) as ds:
        ds.write(nir, 1)
        ds.write(red, 2)
        ds.write(scl.astype("float32"), 3)
        ds.update_tags(acquisition_date="2024-06-01", sensor="SYNTHETIC_FIXTURE")
    return path


def _alert_payload(**overrides):
    payload = {
        "category": "drought",
        "geographic_scope": {"scale": "municipal", "name": f"Zona-{uuid.uuid4()}"},
        "observation_period": {"start": "2024-01-01", "end": "2024-03-31"},
        "detection_method": "test_fixture",
        "risk_level": "high",
        "evidence": [{"indicator": "ndvi", "z": -2.4}],
        "confidence": "medium",
        "source_datasets": ["fixture"],
    }
    payload.update(overrides)
    return payload


# --- satélite ----------------------------------------------------------------
def test_satellite_catalog_fields_and_no_ingested_scenes():
    engine = SatelliteDataEngine()
    payload = engine.sources()
    assert payload["ingested"] == []
    assert payload["count"] >= 10
    for item in payload["sources"]:
        for field in REQUIRED_SOURCE_FIELDS:
            assert field in item, f"{item['source_id']} sin {field}"
        assert item["integration_status"] in {
            "ingested", "adapter_implemented_not_ingested", "evaluated_only",
            "catalog_planned", "optional_not_configured", "access_pending"}


def test_satellite_unknown_source_raises():
    with pytest.raises(KeyError):
        SatelliteDataEngine().source("sentinel9")


def test_raster_read_applies_nodata_and_cloud_mask(tmp_path):
    path = _write_scene(tmp_path / "scene.tif")
    observation = SatelliteDataEngine().read(
        path, bands={"nir": 1, "red": 2}, cloud_band=3)
    assert observation.crs == "EPSG:4326"
    assert observation.acquired_at == "2024-06-01"
    assert observation.valid_mask.sum() == 14  # 16 − nube − nodata
    assert not observation.valid_mask[0, 0]   # nube enmascarada
    assert observation.bands["nir"][0, 0] == pytest.approx(0.6)  # valor conservado
    assert np.isnan(observation.bands["nir"][0, 1])   # nodata → NaN
    assert observation.as_dict()["valid_fraction"] == pytest.approx(14 / 16)


def test_raster_window_and_inspection(tmp_path):
    path = _write_scene(tmp_path / "scene.tif")
    engine = SatelliteDataEngine()
    meta = engine.inspect(path)
    assert meta["width"] == 4 and meta["count"] == 3
    bounds = (-89.2995, 13.7985, -89.2985, 13.7995)
    observation = engine.read(path, bands={"nir": 1}, bounds=bounds)
    assert observation.width <= 4 and observation.height <= 4
    assert observation.provenance["windowed"] is True


def test_stac_parse_local_item_and_plan_not_executed(tmp_path):
    item = {"type": "Feature", "id": "S2B_TEST", "collection": "sentinel-2-l2a",
            "bbox": [-89.4, 13.6, -89.2, 13.8],
            "properties": {"datetime": "2024-06-01T10:00:00Z",
                           "license": "CC-BY-4.0", "eo:cloud_cover": 12},
            "assets": {"B04": {"href": "B04.tif"}, "B08": {"href": "B08.tif"}}}
    path = tmp_path / "item.json"
    path.write_text(json.dumps(item), encoding="utf-8")
    engine = SatelliteDataEngine()
    parsed = engine.parse_stac(path)
    assert parsed["count"] == 1 and parsed["network_used"] is False
    assert parsed["items"][0]["assets"] == ["B04", "B08"]
    plan = engine.stac_search_plan(
        source_id="sentinel2_msi", bbox=(-89.4, 13.6, -89.2, 13.8),
        start="2024-01-01", end="2024-12-31")
    assert plan["executed"] is False and plan["network_required"] is True
    with pytest.raises(ValueError):
        engine.stac_search_plan(source_id="marn_snet_d3_doa",
                                bbox=(-89.4, 13.6, -89.2, 13.8),
                                start="2024-01-01", end="2024-12-31")


# --- índices -----------------------------------------------------------------
def test_ndvi_formula_and_nodata_is_nan():
    engine = VegetationIndexEngine()
    result = engine.compute("ndvi", {
        "nir": np.array([0.5, 0.2, np.nan], dtype="float32"),
        "red": np.array([0.1, 0.4, 0.1], dtype="float32")})
    assert result.values[0] == pytest.approx(0.4 / 0.6, rel=1e-5)
    assert result.values[1] == pytest.approx(-0.2 / 0.6, rel=1e-5)
    assert np.isnan(result.values[2])
    assert result.stats()["nodata_is_zero"] is False


def test_savi_and_msavi_formulas():
    engine = VegetationIndexEngine()
    bands = {"nir": np.array([0.5]), "red": np.array([0.1])}
    assert engine.compute("savi", bands).values[0] == pytest.approx(
        (0.4 / 1.1) * 1.5, rel=1e-5)
    assert engine.compute("msavi", bands).values[0] == pytest.approx(
        (2.0 - np.sqrt(0.8)) / 2.0, rel=1e-5)


def test_ndmi_declares_20m_and_missing_band_fails():
    engine = VegetationIndexEngine()
    spec = engine.describe("ndmi")
    assert spec["resolution_m"] == 20
    with pytest.raises(G.MonitoringError):
        engine.compute("ndmi", {"nir": np.array([0.5])})
    with pytest.raises(G.MonitoringError):
        engine.compute("ndvi", {"nir": np.array([0.5, 0.6]),
                                "red": np.array([0.1])})


def test_cloud_mask_and_specs_cannot_conclude():
    engine = VegetationIndexEngine()
    result = engine.compute(
        "ndvi", {"nir": np.array([0.5, 0.5]), "red": np.array([0.1, 0.1])},
        cloud_mask=np.array([True, False]))
    assert result.valid_pixels == 1
    for name in engine.specs()["indices"]:
        assert engine.describe(name)["cannot_conclude"]
        assert engine.describe(name)["formula"]


# --- series temporales -------------------------------------------------------
def _season(records_years=(2018, 2019, 2020, 2021, 2022)):
    return [{"date": f"{year}-06-15", "value": value}
            for year, value in zip(records_years, (0.60, 0.62, 0.58, 0.61, 0.40))]


def test_timeseries_build_excludes_cloud_and_nan():
    engine = SatelliteTimeSeriesEngine()
    payload = engine.build([
        {"date": "2024-06-01", "value": 0.5, "cloud_cover": 10},
        {"date": "2024-06-11", "value": 0.5, "cloud_cover": 80},
        {"date": "2024-06-21", "value": None},
    ])
    assert payload["n_valid"] == 1 and payload["n_excluded"] == 2
    assert payload["period"]["start"] == "2024-06-01"


def test_gaps_detected_without_interpolation():
    engine = SatelliteTimeSeriesEngine()
    payload = engine.gaps([{"date": "2024-01-01", "value": 0.5},
                           {"date": "2024-02-15", "value": 0.4}],
                          expected_interval_days=10)
    assert payload["gap_count"] == 1
    assert payload["gaps"][0]["days"] == 45
    assert payload["interpolated"] is False


def test_seasonal_baseline_requires_min_years():
    engine = SatelliteTimeSeriesEngine()
    with pytest.raises(G.InsufficientRecordError):
        engine.anomaly(_season((2021, 2022)), target_date="2022-06-15",
                       min_years=3)


def test_anomaly_robust_z_matches_manual_calculation():
    records = _season()
    payload = SatelliteTimeSeriesEngine().anomaly(
        records, target_date="2022-06-15", min_obs=4)
    baseline = [0.60, 0.62, 0.58, 0.61]
    median = float(np.median(baseline))
    mad = float(np.median(np.abs(np.array(baseline) - median))) * 1.4826
    assert payload["robust_z"] == pytest.approx((0.40 - median) / mad, rel=1e-4)
    assert payload["direction"] == "below_baseline"


def test_trajectory_and_compare():
    engine = SatelliteTimeSeriesEngine()
    records = [{"date": f"2024-0{m}-01", "value": 0.2 + 0.1 * m}
               for m in range(1, 6)]
    trend = engine.trajectory(records, min_obs=5)
    assert trend["slope_per_day"] > 0
    comparison = engine.compare(records[:2], records[3:])
    assert comparison["median_difference"] > 0


# --- cambio ------------------------------------------------------------------
def test_change_detects_decline_and_possible_processes():
    engine = CropChangeDetectionEngine()
    before = np.full((3, 3), 0.6, dtype="float32")
    after = np.full((3, 3), 0.3, dtype="float32")
    result = engine.compare(before, after, threshold=0.1,
                            before_sensor="s2", after_sensor="s2")
    assert result["signal"] == "strong_decline"
    assert result["changed_pixels"] == 9
    assert result["attribution"] is None
    assert any("cosecha" in p for p in result["possible_processes"])


def test_change_rejects_cross_sensor_without_harmonization():
    engine = CropChangeDetectionEngine()
    grid = np.zeros((2, 2), dtype="float32")
    with pytest.raises(G.MonitoringError):
        engine.compare(grid, grid, threshold=0.1,
                       before_sensor="s2", after_sensor="landsat8")
    assert engine.compare(grid, grid, threshold=0.1, before_sensor="s2",
                          after_sensor="landsat8", harmonized=True
                          )["signal"] == "no_change_detected"


def test_change_rejects_invalid_threshold():
    with pytest.raises(G.MonitoringError):
        CropChangeDetectionEngine().compare(
            np.zeros((2, 2)), np.zeros((2, 2)), threshold=0)


def test_remote_sensing_scale_support():
    engine = AgriculturalRemoteSensingEngine()
    assert engine.scale_support(10, "municipal")["supported"] is True
    assert engine.scale_support(10, "parcel")["supported"] is False


# --- sanidad -----------------------------------------------------------------
def test_crop_health_insufficient_without_baseline():
    payload = CropHealthMonitoringEngine().assess(
        "maize", "flowering", ndvi_anomaly=-2.5,
        n_observations=6, baseline_years=1)
    assert payload["status"] == "insufficient_evidence"
    assert payload["monitoring_recommended"] is True


def test_crop_health_possible_stress_in_sensitive_stage():
    payload = CropHealthMonitoringEngine().assess(
        "maize", "flowering", ndvi_anomaly=-2.4, ndmi_anomaly=-1.9,
        n_observations=8, baseline_years=4)
    assert payload["status"] == "possible_vegetation_stress"
    assert payload["confidence"] == "medium"
    assert payload["possible_causes"]


def test_crop_health_unknown_crop_raises():
    with pytest.raises(KeyError):
        CropHealthMonitoringEngine().assess(
            "quinoa", "flowering", ndvi_anomaly=-2.0,
            n_observations=8, baseline_years=4)


def test_vegetation_stress_requires_two_indicators():
    payload = VegetationStressEngine().assess(ndvi_z=-2.5)
    assert payload["status"] == "insufficient_evidence"


def test_vegetation_stress_water_component():
    payload = VegetationStressEngine().assess(
        ndvi_z=-2.5, ndmi_z=-2.0, rainfall_z=-2.2)
    assert payload["inferred_stress"] is True
    assert any("hídrico" in c for c in payload["possible_causes"])


def test_thermal_heat_wave_and_lst_not_used():
    payload = ThermalStressEngine().assess(
        "maize", "flowering", [36.0] * 7,
        threshold_c=35.0, threshold_source="fixture de prueba",
        lst_c=45.0)
    assert payload["exposure"]["heat_wave_3d"] is True
    assert payload["land_surface_temperature"]["used_for_stress"] is False


def test_thermal_requires_threshold_source():
    with pytest.raises(G.MonitoringError):
        ThermalStressEngine().assess(
            "maize", "flowering", [36.0] * 3, threshold_c=35.0,
            threshold_source="")


def test_anomaly_methods_and_opaque_model_refused():
    engine = CropAnomalyDetectionEngine()
    payload = engine.detect(
        [0.5] * 10 + [0.1], method="robust_z",
        baseline=[0.50, 0.51, 0.49, 0.50, 0.52, 0.48], threshold=2.0)
    assert payload["flagged_indices"] == [10]
    assert payload["direction"] == "below"
    with pytest.raises(G.MonitoringError):
        engine.detect([0.5] * 5, method="isolation_forest")


def test_anomaly_multivariable():
    engine = CropAnomalyDetectionEngine()
    payload = engine.multivariable({
        "ndvi": [0.6, 0.61, 0.59, 0.60, 0.2],
        "ndmi": [0.4, 0.41, 0.39, 0.40, 0.1],
    }, threshold=2.0)
    assert payload["flagged_indices"] == [4]


# --- agua --------------------------------------------------------------------
def test_meteorological_ratio_classes():
    payload = WaterStressDetectionEngine().meteorological_ratio(30, 100)
    assert payload["ratio"] == 0.3
    assert payload["class"] == "severe_deficit"


def test_fao56_ks_boundaries():
    engine = WaterStressDetectionEngine()
    assert engine.soil_water(depletion_mm=10, taw_mm=100,
                             raw_mm=50)["ks"] == 1.0
    assert engine.soil_water(depletion_mm=100, taw_mm=100,
                             raw_mm=50)["ks"] == 0.0


def test_water_assess_separates_types_and_no_hydrology():
    payload = WaterStressDetectionEngine().assess(precip_mm=10, et0_mm=100)
    assert payload["meteorological_drought"]["class"] == "severe_deficit"
    assert payload["crop_water_stress"] is None
    assert payload["hydrological_drought"]["status"] == "not_evaluated"


def test_water_stress_from_soil_balance():
    payload = WaterStressDetectionEngine().assess(
        taw_mm=100, depletion_mm=80, etc_mm=120, precip_mm=20)
    assert payload["agricultural_drought"]["ks"] == pytest.approx(0.4)
    assert payload["conclusion"] == "possible_water_stress"


# --- fitosanidad -------------------------------------------------------------
def test_catalogs_integrity_and_presence_scopes():
    assert len(PESTS) >= 5 and len(DISEASES) >= 4
    for record in list(PESTS.values()) + list(DISEASES.values()):
        assert record["sources"]
        scope = record["distribution"]["presence_scope"]
        assert scope in {"national_confirmed", "regional_confirmed",
                         "international_record", "unconfirmed_national"}
    assert PESTS["fall_armyworm"]["distribution"]["presence_scope"] == \
        "national_confirmed"
    assert PESTS["sugarcane_borer"]["distribution"]["presence_scope"] == \
        "regional_confirmed"
    assert PESTS["fall_armyworm"]["distribution"]["note"]


def test_pest_risk_separates_presence_from_suitability():
    payload = PestRiskEngine().assess("sugarcane_borer", crop_id="sugarcane")
    assert payload["presence_evidence"]["confirmed_national"] is False
    assert payload["environmental_suitability"] is None
    assert payload["risk_index"] is None
    assert payload["gap"]


def test_pest_risk_explicit_rules_and_missing_source():
    engine = PestRiskEngine()
    rules = [{"variable": "temperature_mean_c", "min": 15, "max": 30,
              "weight": 1.0, "source": "fixture declarado"}]
    payload = engine.assess(
        "fall_armyworm", crop_id="maize", stage="flowering",
        conditions={"temperature_mean_c": 25}, rules=rules)
    assert payload["environmental_suitability"] == 1.0
    assert payload["risk_index"] == 1.0
    with pytest.raises(G.MonitoringError):
        engine.assess("fall_armyworm", conditions={"temperature_mean_c": 25},
                      rules=[{"variable": "temperature_mean_c",
                              "min": 15, "max": 30}])


def test_disease_risk_is_not_diagnosis():
    payload = DiseaseRiskEngine().assess(
        "coffee_leaf_rust", crop_id="coffee",
        conditions={"temperature_mean_c": 22})
    assert payload["diagnosis"] is None
    assert payload["infection_model"]["implemented"] is False
    assert payload["environmental_suitability"] == 1.0


def test_phytosanitary_community_cannot_be_official():
    engine = AgriculturalPhytosanitaryEngine()
    with pytest.raises(G.MonitoringError):
        engine.add(kind="community_report", statement="Hay roya",
                   crop_id="coffee", geographic_scope="municipio X",
                   source="reporte local", observed_on="2024-06-01",
                   official=True)
    record = engine.add(kind="community_report", statement="Posible roya",
                        crop_id="coffee", geographic_scope="municipio X",
                        source="reporte local", observed_on="2024-06-01")
    assert record["official"] is False
    assert engine.summary()["by_kind"]["community_report"] == 1


# --- riesgos -----------------------------------------------------------------
def test_risk_product_and_missing_component():
    engine = AgriculturalRiskEngine()
    payload = engine.assess(hazard=0.8, exposure=0.5, vulnerability=0.5)
    assert payload["risk_value"] == pytest.approx(0.2)
    assert payload["risk_class"] == "low"
    missing = engine.assess(hazard=0.8, exposure=None, vulnerability=0.5)
    assert missing["risk_value"] is None and missing["missing"] == ["exposure"]


def test_drought_index_requires_thirty_years():
    engine = DroughtMonitoringEngine()
    with pytest.raises(G.InsufficientRecordError):
        engine.standardized_precipitation_index([50.0] * 120)


def test_drought_index_computes_with_long_record():
    values = [80 + 60 * np.sin(2 * np.pi * (i % 12) / 12) + (i % 7)
              for i in range(40 * 12)]
    payload = DroughtMonitoringEngine().standardized_precipitation_index(
        values, scale=3, min_years=30)
    assert payload["n_years_in_group"] >= 30
    assert np.isfinite(payload["z"])
    assert payload["method"].startswith("estandarización empírica")


def test_consecutive_dry_days():
    payload = DroughtMonitoringEngine().consecutive_dry_days(
        [0, 0, 0, 5, 0, 0, 0, 0])
    assert payload["max_consecutive_dry_days"] == 4
    assert payload["dry_days"] == 7


def test_flood_exposure_flags_and_not_prediction():
    payload = FloodAndExcessWaterRiskEngine().assess(
        rainfall_24h_mm=60, rainfall_72h_mm=150, slope_deg=1,
        soil_infiltration_mm_h=5, drainage_distance_m=500)
    assert payload["prediction"] is False
    assert payload["process_flags"]["waterlogging"] is True
    assert payload["process_flags"]["river_flood_exposure"] is True
    assert payload["exposure_class"] is not None


def test_flood_requires_variables():
    with pytest.raises(G.InsufficientRecordError):
        FloodAndExcessWaterRiskEngine().assess()


def test_heat_keeps_forecast_separate():
    forecast = {"provider": "fixture", "issued_at": "2024-06-01",
                "valid_from": "2024-06-02", "valid_to": "2024-06-04",
                "horizon_days": 3, "uncertainty": "±2 °C",
                "values": [{"tmax_c": 36}, {"tmax_c": 37}, {"tmax_c": 36}]}
    payload = HeatAndClimateRiskEngine().assess(
        tmax_c=[36.0] * 5, threshold_c=35.0,
        threshold_source="fixture declarado", forecast=forecast)
    assert payload["mixed_with_observed"] is False
    assert payload["forecast"]["evidence_class"] == "forecast"
    assert payload["forecast"]["horizon_days"] == 3


def test_heat_forecast_requires_fields():
    with pytest.raises(G.MonitoringError):
        HeatAndClimateRiskEngine().assess(
            threshold_c=35.0, threshold_source="fixture",
            forecast={"provider": "x"})


def test_soil_degradation_refuses_erosion_rate():
    engine = SoilDegradationRiskEngine()
    payload = engine.assess(slope_deg=20, vegetation_cover=0.2)
    assert payload["erosion_rate"] is None
    assert payload["relative_erosion_index"] is None
    with_inputs = engine.assess(slope_deg=20, vegetation_cover=0.2,
                                rainfall_erosivity=100,
                                soil_erodibility=0.3)
    assert with_inputs["relative_erosion_index"] > 0
    assert with_inputs["relative_erosion_index_units"].startswith("adimensional")


def test_crop_loss_separates_impact_damage_and_modeled():
    payload = CropLossRiskEngine().exposure(
        "maize", stage="flowering", hazards={"drought": 0.8, "heat": 0.6},
        potential_yield_t_ha=5.0, expected_yield_t_ha=3.0)
    assert payload["potential_impact"] is not None
    assert payload["observed_damage"]["fraction"] is None
    assert payload["modeled_loss"]["fraction"] == pytest.approx(0.4)
    assert payload["is_actual_yield_loss"] is False


# --- alertas -----------------------------------------------------------------
def _make_alert(engine: AgriculturalAlertEngine, **overrides):
    return engine.create(**_alert_payload(**overrides))["alert"]


def test_alert_dedup_and_required_fields():
    engine = AgriculturalAlertEngine()
    payload = _alert_payload()
    first = engine.create(**payload)
    second = engine.create(**payload)
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    alert = first["alert"]
    for field in ("alert_id", "category", "geographic_scope", "detected_at",
                  "observation_period", "source_datasets", "detection_method",
                  "risk_level", "evidence", "confidence", "expires_at",
                  "status", "model_version"):
        assert field in alert
    assert alert["status"] == "DETECTED"


def test_alert_requires_evidence_and_datasets():
    engine = AgriculturalAlertEngine()
    with pytest.raises(G.MonitoringError):
        engine.create(**_alert_payload(evidence=[]))
    with pytest.raises(G.MonitoringError):
        engine.create(**_alert_payload(source_datasets=[]))


def test_alert_transition_rules_and_immutability():
    engine = AgriculturalAlertEngine()
    alert = _make_alert(engine)
    with pytest.raises(G.MonitoringError):
        engine.transition(alert["alert_id"], "VERIFIED")
    updated = engine.transition(alert["alert_id"], "NEEDS_VERIFICATION",
                                reason="revisar")
    assert updated["status"] == "NEEDS_VERIFICATION"
    assert updated["original"]["status"] == "DETECTED"
    with pytest.raises(G.MonitoringError):
        engine.transition(alert["alert_id"], "DETECTED")


def test_verified_requires_strong_or_two_weak_verifiers():
    engine = AgriculturalAlertEngine()
    weak = _make_alert(engine)
    with pytest.raises(G.MonitoringError):
        engine.transition(weak["alert_id"], "NEEDS_VERIFICATION")
        engine.transition(weak["alert_id"], "VERIFIED", verification_events=[
            {"verifier_type": "community_report", "outcome": "confirmed",
             "confidence": 0.9}])
    strong = _make_alert(engine)
    engine.transition(strong["alert_id"], "NEEDS_VERIFICATION")
    verified = engine.transition(strong["alert_id"], "VERIFIED",
                                 verification_events=[
                                     {"verifier_type": "official_institution",
                                      "outcome": "confirmed",
                                      "confidence": 0.9}])
    assert verified["status"] == "VERIFIED"


def test_alert_expiration():
    engine = AgriculturalAlertEngine()
    alert = _make_alert(engine)
    future = (date.today() + timedelta(days=60)).isoformat()
    payload = engine.expire(on=future)
    assert alert["alert_id"] in payload["expired"]


def test_prioritization_verified_high_first():
    engine = AgriculturalAlertEngine()
    verified = _make_alert(engine, risk_level="high")
    engine.transition(verified["alert_id"], "NEEDS_VERIFICATION")
    engine.transition(verified["alert_id"], "VERIFIED", verification_events=[
        {"verifier_type": "field_inspection", "outcome": "confirmed",
         "confidence": 0.9}])
    algorithmic = _make_alert(engine, risk_level="very_high", confidence="low")
    ranked = AlertPrioritizationEngine().prioritize(
        [engine.get(algorithmic["alert_id"]),
         engine.get(verified["alert_id"])])
    assert ranked["ranking"][0]["alert_id"] == verified["alert_id"]
    assert ranked["ranking"][0]["verified_high_severity"] is True
    assert ranked["ranking"][0]["reasons"]


def test_notification_preferences_privacy_and_sync():
    engine = AgriculturalAlertEngine()
    alert = _make_alert(engine, crop_id="maize",
                        geographic_scope={"scale": "municipal",
                                          "name": "Suchitoto",
                                          "latitude": 13.9, "longitude": -89.0})
    notifications = AgriculturalNotificationEngine()
    rejected = notifications.enqueue(alert, preferences={"crops": ["beans"]})
    assert rejected["queued"] is False
    queued = notifications.enqueue(
        alert, preferences={"crops": ["maize"], "min_severity": "moderate",
                            "channels": ["api", "offline_sync"]},
        redact=True)
    assert queued["queued"] is True
    assert queued["item"]["geographic_scope"]["latitude"] is None
    assert queued["item"]["personal_data_included"] is False
    assert notifications.sync()["delivered"] >= 1


def test_early_warning_forecast_is_not_deterministic():
    forecast = {"provider": "fixture", "issued_at": "2024-06-01",
                "valid_from": "2024-06-02", "valid_to": "2024-06-04",
                "horizon_days": 3, "uncertainty": "±2 °C",
                "values": [36.0, 37.0, 36.0]}
    payload = AgriculturalEarlyWarningEngine().forecast_warning(
        forecast, threshold_c=35.0, threshold_source="fixture declarado")
    assert payload["status"] == "possible_heat_warning"
    assert payload["deterministic"] is False
    assert payload["warning_type"] == "forecast_based"


def test_verification_workflow_confirms_with_official_source():
    alerts = AgriculturalAlertEngine()
    verification = AlertVerificationEngine(alerts)
    alert = _make_alert(alerts)
    verification.submit(alert["alert_id"], verifier_type="official_institution",
                        outcome="confirmed",
                        evidence=[{"document": "nota oficial"}],
                        observed_on="2024-06-02", confidence=0.9,
                        notes="confirmado por institución")
    applied = verification.apply(alert["alert_id"])
    assert applied["alert"]["status"] == "VERIFIED"
    assert applied["alert"]["original"]["status"] == "DETECTED"
    assert len(applied["alert"]["verification_events"]) == 1


# --- campo -------------------------------------------------------------------
def _field_payload(**overrides):
    payload = {
        "observation_type": "crop_observation",
        "latitude": 13.70, "longitude": -89.20,
        "observed_on": date.today().isoformat(),
        "contributor_id": f"user-{uuid.uuid4().hex[:8]}",
        "crop_id": "maize", "photos": ["foto.jpg"],
    }
    payload.update(overrides)
    return payload


def test_field_photo_required_sets_needs_evidence():
    engine = AgriculturalFieldVerificationEngine()
    record = engine.submit(_field_payload(observation_type="pest_suspected",
                                          photos=[]))
    assert record["status"] == "needs_evidence"
    assert record["verified_scientific_record"] is False


def test_field_duplicate_and_privacy():
    engine = AgriculturalFieldVerificationEngine()
    first = engine.submit(_field_payload(observation_type="water_stress"))
    second = engine.submit(_field_payload(observation_type="water_stress",
                                          latitude=13.7001, longitude=-89.2001))
    assert second["quality_checks"]["duplicate_of"] == first["observation_id"]
    public = engine.public_view(first["observation_id"])
    assert public["latitude"] == 13.7
    assert public["coordinate_precision"].startswith("redondeada")


def test_field_rejects_outside_country_and_future():
    engine = AgriculturalFieldVerificationEngine()
    with pytest.raises(G.MonitoringError):
        engine.submit(_field_payload(latitude=0, longitude=0))
    with pytest.raises(G.MonitoringError):
        engine.submit(_field_payload(observed_on="2999-01-01"))


def test_field_review_does_not_verify():
    engine = AgriculturalFieldVerificationEngine()
    record = engine.submit(_field_payload())
    reviewed = engine.review(record["observation_id"],
                             reviewer_id="reviewer-1", decision="accept",
                             notes="revisado")
    assert reviewed["status"] == "accepted"
    assert reviewed["verified_scientific_record"] is False


# --- integración -------------------------------------------------------------
def test_timeline_orders_events_and_reports_gaps():
    engine = CropMonitoringTimelineEngine()
    payload = engine.build([
        {"date": "2024-06-10", "type": "harvest", "source": "field"},
        {"date": "2024-05-01", "type": "planting", "source": "field"},
        {"date": "2024-05-01", "type": "planting", "source": "field"},
    ], expected_interval_days=10)
    assert [e["type"] for e in payload["events"]] == ["planting", "planting",
                                                      "harvest"]
    assert payload["missing_periods"]
    assert len(payload["duplicates_suspected"]) == 1
    assert payload["interpolated"] is False


def test_timeline_rejects_unknown_type():
    with pytest.raises(G.MonitoringError):
        CropMonitoringTimelineEngine().build([
            {"date": "2024-05-01", "type": "teleport"}])
        CropMonitoringTimelineEngine().build(
            [{"date": "2024-05-01", "type": "alert",
              "evidence_class": "invented"}])


def test_risk_map_geojson_metadata():
    payload = AgriculturalRiskMappingEngine().to_feature_collection(
        [{"latitude": 13.7, "longitude": -89.2, "value": 0.6},
         {"latitude": 13.8, "longitude": -89.1, "value": None}],
        indicator="drought_index", source="fixture", observation_date="2024-06-01",
        resolution_m=1000, methodology="índice declarado", confidence="low",
        limitations=["modelado"])
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
    assert payload["metadata"]["modeled"] is True
    assert payload["metadata"]["interpolated"] is False
    assert payload["features"][0]["properties"]["modeled"] is True
    with pytest.raises(G.MonitoringError):
        AgriculturalRiskMappingEngine().to_feature_collection(
            [{"latitude": 0, "longitude": 0, "value": 0.6}],
            indicator="x", source="s", observation_date="2024-01-01",
            resolution_m=1000, methodology="m", confidence="low",
            limitations=[])


def test_analysis_is_descriptive_not_causal():
    records = [{"date": f"2024-0{m}-01", "value": 0.4 + 0.02 * m}
               for m in range(1, 7)]
    payload = AgriculturalMonitoringAnalysisEngine().analyze(
        records, alerts=[{"category": "drought", "detected_at": "2024-06-01"}])
    assert payload["descriptive"]["n"] == 6
    assert payload["trend"]["slope_per_day"] > 0
    assert payload["inference"]["causal_claim"] is False


# --- API ---------------------------------------------------------------------
def test_api_meta_and_catalogs(client):
    meta = client.get("/api/monitoring/meta")
    assert meta.status_code == 200
    assert meta.json()["policy"]["satellite_scenes_ingested"] is False
    sources = client.get("/api/monitoring/sources").json()
    assert sources["ingested"] == []
    pests = client.get("/api/monitoring/pests").json()
    assert pests["count"] >= 5
    assert client.get("/api/monitoring/pests/nope").status_code == 404
    diseases = client.get("/api/monitoring/diseases").json()
    assert diseases["count"] >= 4


def test_api_indices_and_timeseries(client):
    response = client.post("/api/monitoring/indices", json={
        "name": "ndvi",
        "bands": {"nir": [0.5, 0.2], "red": [0.1, 0.4]}})
    assert response.status_code == 200
    assert response.json()["mean"] == pytest.approx(0.1666666, rel=1e-4)
    series = client.post("/api/monitoring/timeseries", json={
        "records": [{"date": "2024-06-01", "value": 0.5},
                    {"date": "2024-06-11", "value": 0.4, "cloud_cover": 90}]})
    assert series.status_code == 200
    assert series.json()["n_valid"] == 1


def test_api_index_raster(client):
    path = C.DATA / "external" / "_test_phase7_scene.tif"
    _write_scene(path)
    try:
        response = client.post("/api/monitoring/indices/raster", json={
            "path": "data/external/_test_phase7_scene.tif",
            "bands": {"nir": 1, "red": 2}, "cloud_band": 3, "index": "ndvi"})
        assert response.status_code == 200
        body = response.json()
        assert body["index"]["valid_pixels"] == 14
        assert body["raster"]["crs"] == "EPSG:4326"
    finally:
        os.remove(path)


def test_api_alert_lifecycle(client):
    payload = _alert_payload()
    created = client.post("/api/monitoring/alerts", json=payload)
    assert created.status_code == 200
    alert = created.json()["alert"]
    duplicate = client.post("/api/monitoring/alerts", json=payload)
    assert duplicate.json()["duplicate"] is True
    assert client.get(
        f"/api/monitoring/alerts/{alert['alert_id']}").status_code == 200
    ranked = client.post("/api/monitoring/alerts/prioritize", json={})
    assert ranked.status_code == 200
    assert ranked.json()["count"] >= 1
    transition = client.post(
        f"/api/monitoring/alerts/{alert['alert_id']}/transition",
        json={"status": "NEEDS_VERIFICATION", "reason": "revisión"})
    assert transition.status_code == 200
    assert transition.json()["status"] == "NEEDS_VERIFICATION"


def test_api_errors_are_declared(client):
    assert client.post("/api/monitoring/change", json={
        "before": [0.1], "after": [0.1], "threshold": 0}).status_code == 400
    assert client.post("/api/monitoring/crop-health", json={
        "crop_id": "quinoa", "stage": "flowering",
        "ndvi_anomaly": -1, "n_observations": 9,
        "baseline_years": 4}).status_code == 404
    assert client.post("/api/monitoring/pest-risk", json={
        "pest_id": "nope"}).status_code == 404
    assert client.post("/api/monitoring/satellite/inspect", json={
        "path": "../../etc/passwd"}).status_code == 400


def test_api_backward_compatibility(client):
    for path in ("/api/health", "/api/engines/meta", "/api/agriculture/meta",
                 "/api/onboarding/meta", "/api/monitoring/meta"):
        assert client.get(path).status_code == 200, path
