"""Pruebas de Fase 6 — Subsistema A (inteligencia agrícola).

Las pruebas verifican software: aritmética, contratos y comportamiento ante
datos faltantes. No establecen validez científica de los parámetros.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from agrosv.agriculture.calendar import AgriculturalCalendarEngine
from agrosv.agriculture.catalog import CROPS, CropKnowledgeEngine
from agrosv.agriculture.phenology import (CropPhenologyEngine, PhenologyError,
                                          accumulate, daily_gdd)
from agrosv.agriculture.simulation import (AdapterUnavailable,
                                           CropSimulationEngine, detect)
from agrosv.agriculture.suitability import (CropSuitabilityEngine,
                                            growing_window)
from agrosv.agriculture.water_nutrient import (CropWaterNutrientEngine,
                                               WaterNutrientError,
                                               effective_precipitation,
                                               kc_series, resolve_kc)


# --- catálogo ---------------------------------------------------------------
def test_catalog_has_22_crops_with_unique_ids():
    engine = CropKnowledgeEngine()
    payload = engine.list_crops()
    assert payload["count"] == 22
    ids = [c["crop_id"] for c in payload["crops"]]
    assert len(set(ids)) == 22


def test_every_parameter_declares_status_and_gap_is_null():
    for record in CROPS.values():
        for section in ("temperature", "water", "soil", "nutrition",
                        "yield_data"):
            for value in record[section].values():
                assert "status" in value
                if value["status"] == "GAP":
                    assert value["value"] is None
        assert record["kc"]["status"] == "GAP"


def test_maize_has_national_yield_from_cap_and_no_variety_yield():
    maize = CropKnowledgeEngine().get("maize")["crop"]
    assert maize["yield"]["national_avg_t_ha"]["value"] == 2.4
    assert maize["yield"]["national_avg_t_ha"]["status"] == "NAC"
    assert maize["yield"]["range_t_ha"]["status"] == "GAP"


def test_only_five_crops_declare_minimum_simulation_inputs():
    assert CropKnowledgeEngine().audit()["simulation_ready"] == 5


def test_search_is_accent_and_case_insensitive():
    engine = CropKnowledgeEngine()
    assert engine.find("MAÍZ")["matches"] == ["maize"]
    assert "coffee" in engine.find("café")["matches"]


def test_unknown_crop_raises_key_error():
    with pytest.raises(KeyError):
        CropKnowledgeEngine().get("quinoa")


def test_urban_crops_are_gap_records_not_simulable():
    engine = CropKnowledgeEngine()
    for crop in ("lettuce_urban", "radish_urban", "cilantro_urban"):
        ready = engine.simulation_ready(crop)
        assert ready["ready"] is False
        assert "cycle_days" in ready["missing"]


def test_compare_keeps_ref_and_nac_distinct():
    comparison = CropKnowledgeEngine().compare(["maize", "coffee"])
    assert comparison["comparison"]["maize"]["national_yield"]["status"] == "NAC"
    assert "no los hace equivalentes" in comparison["warning"]


# --- fenología --------------------------------------------------------------
def test_daily_gdd_mean_method_and_zero_floor():
    assert daily_gdd(10, 30, 10) == 10
    assert daily_gdd(0, 5, 10) == 0
    assert daily_gdd(30, 10, 10) == 10  # orden invertido se corrige


def test_gdd_accumulation_is_monotonic():
    values = accumulate([10, 10, 10], [20, 20, 20], 10)
    assert values == [5.0, 10.0, 15.0]


def test_phenology_with_constant_weather_reaches_maturity():
    start = date(2024, 5, 1)
    weather = {(start + timedelta(days=i)).isoformat():
               {"tmin": 15.0, "tmax": 25.0} for i in range(400)}
    result = CropPhenologyEngine().run(
        "maize", start, variety={"gdd_to_maturity": 1000, "tbase_c": 10},
        weather=weather, weather_dataset="fixture")
    stages = result["result"]["stages"]
    assert [s["stage"] for s in stages] == [
        "emergence", "vegetative", "flowering", "grain_fill", "maturity"]
    assert stages[-1]["date"] == "2024-08-08"  # 1000 / 10 = 100 días
    assert result["result"]["complete"] is True


def test_phenology_marks_incomplete_when_series_ends():
    weather = {"2024-05-01": {"tmin": 15.0, "tmax": 25.0}}
    result = CropPhenologyEngine().run(
        "maize", "2024-05-01", variety={"gdd_to_maturity": 1000},
        weather=weather, weather_dataset="fixture")
    assert result["result"]["complete"] is False
    assert any("no alcanza la madurez" in x for x in result["limitations"])


def test_phenology_rejects_decreasing_stage_fractions():
    with pytest.raises(PhenologyError):
        CropPhenologyEngine().resolve_parameters(
            "maize", {"stage_fractions": {"a": 0.5, "b": 0.4, "c": 1.0}})


def test_crop_without_base_temperature_cannot_run_phenology():
    with pytest.raises(PhenologyError):
        CropPhenologyEngine().resolve_parameters("sweet_pepper", None)


def test_derived_gdd_is_flagged_model_derived():
    params = CropPhenologyEngine().resolve_parameters("maize", None)
    assert params["gdd_to_maturity"] is None
    assert params["gdd_status"] is None


# --- aptitud ----------------------------------------------------------------
def test_growing_window_is_circular_and_five_months():
    precip = {m: (200.0 if m in (5, 6, 7, 8, 9) else 10.0)
              for m in range(1, 13)}
    assert growing_window(precip) == [5, 6, 7, 8, 9]
    assert len(growing_window({m: 1.0 for m in range(1, 13)})) == 5


def test_suitability_never_classes_nodata_ph():
    result = CropSuitabilityEngine().evaluate("maize", -89.19, 13.69)
    payload = result["result"]
    assert payload["class"] == "not_evaluated"
    assert "ph" in payload["critical_missing"]
    assert any("faltan factores críticos" in x for x in result["limitations"])


def test_suitability_declares_sources_and_rule():
    payload = CropSuitabilityEngine().evaluate("coffee", -89.45, 13.85)
    assert payload["result"]["class"] in {"S1", "S2", "S3", "not_evaluated"}
    factors = {f["factor"] for f in payload["result"]["factors"]}
    assert {"temperature", "water", "ph", "slope"} <= factors
    assert payload["result"]["rule"]["N"].startswith("al menos")


def test_urban_system_is_not_evaluated_without_urban_data():
    payload = CropSuitabilityEngine().evaluate(
        "lettuce_urban", -89.45, 13.85, system="urban")["result"]
    assert payload["class"] == "not_evaluated"
    assert payload["critical_missing"]


def test_irrigated_water_factor_requires_explicit_assumption():
    without = CropSuitabilityEngine().evaluate(
        "coffee", -89.45, 13.85, system="irrigated")["result"]
    water = next(f for f in without["factors"] if f["factor"] == "water")
    assert water["rating"] == "not_evaluated"
    with_irrigation = CropSuitabilityEngine().evaluate(
        "coffee", -89.45, 13.85, system="irrigated",
        irrigation_available=True)["result"]
    water = next(f for f in with_irrigation["factors"]
                 if f["factor"] == "water")
    assert water["rating"] == "none"


def test_unknown_crop_in_suitability_raises():
    with pytest.raises(KeyError):
        CropSuitabilityEngine().evaluate("quinoa", -89.45, 13.85)


# --- agua y nutrientes ------------------------------------------------------
def test_effective_precipitation_methods():
    assert effective_precipitation(10, 4) == 4
    assert effective_precipitation(3, 4) == 3
    assert effective_precipitation(10, 0, method="none") == 0
    assert effective_precipitation(10, 4, method="fixed_fraction",
                                   fraction=0.5) == 5
    with pytest.raises(WaterNutrientError):
        effective_precipitation(10, 4, method="invented")


def test_kc_series_interpolates_and_stays_bounded():
    values = kc_series({"ini": 0.4, "mid": 1.1, "end": 0.6}, 100)
    assert len(values) == 100
    assert values[0] == pytest.approx(0.4)
    assert max(values) == pytest.approx(1.1, abs=0.01)


def test_kc_requires_explicit_values_or_opt_in():
    with pytest.raises(WaterNutrientError):
        resolve_kc(None, allow_reference_kc=False)
    reference = resolve_kc(None, allow_reference_kc=True)
    assert reference["status"] == "SCENARIO"
    assert "NO un coeficiente" in reference["note"]


def _weather(days: int, precip: float, et0: float):
    start = date(2024, 5, 1)
    return {(start + timedelta(days=i)).isoformat():
            {"precip_mm": precip, "et0_mm": et0} for i in range(days)}


def test_water_balance_produces_stress_without_rain():
    result = CropWaterNutrientEngine().water_balance(
        crop_id="maize", planting_date="2024-05-01", awc_mm_per_m=150,
        root_depth_cm=60, kc={"ini": 1, "mid": 1, "end": 1},
        weather=_weather(200, 0.0, 5.0))
    payload = result["result"]
    assert payload["soil"]["taw_mm"] == pytest.approx(90.0)
    assert payload["stress"]["stress_days"] > 0
    assert payload["stress"]["eta_etm_ratio"] < 1.0
    assert payload["totals"]["irrigation_mm"] == 0


def test_water_balance_rejects_missing_awc():
    with pytest.raises(WaterNutrientError):
        CropWaterNutrientEngine().water_balance(
            crop_id="maize", planting_date="2024-05-01", awc_mm_per_m=0,
            root_depth_cm=60, allow_reference_kc=True)


def test_irrigation_schedule_emits_events():
    balance = CropWaterNutrientEngine().water_balance(
        crop_id="maize", planting_date="2024-05-01", awc_mm_per_m=100,
        root_depth_cm=60, kc={"ini": 1, "mid": 1, "end": 1},
        weather=_weather(200, 0.0, 5.0))
    schedule = CropWaterNutrientEngine().irrigation_schedule(
        balance, application_efficiency=0.8)
    assert schedule["events"]
    assert schedule["gross_total_mm"] > schedule["events"][0]["net_mm"]


def test_nutrient_demand_is_removal_not_fertilizer():
    payload = CropWaterNutrientEngine().nutrient_demand(
        "maize", 2.4, yield_source="CAP 2025")
    assert payload["demand_kg_ha"]["N"]["kg_ha"] == [48.0, 72.0]
    assert payload["is_fertilizer_recommendation"] is False
    assert "NO dosis" in payload["warning"]


def test_nutrient_demand_requires_yield_source():
    with pytest.raises(WaterNutrientError):
        CropWaterNutrientEngine().nutrient_demand("maize", 2.4,
                                                  yield_source="")


def test_nutrient_gap_is_null_for_pepper():
    payload = CropWaterNutrientEngine().nutrient_demand(
        "sweet_pepper", 5.0, yield_source="fixture")
    assert payload["demand_kg_ha"]["N"]["kg_ha"] is None
    assert payload["missing"] == ["N", "P2O5", "K2O"]


# --- simulación -------------------------------------------------------------
def test_only_builtin_adapter_is_runnable():
    status = detect()
    assert status["runnable"] == ["agrosv_water_balance"]
    assert status["adapters"]["pcse_wofost"]["executable"] is False


def test_external_adapter_is_refused_explicitly():
    with pytest.raises(AdapterUnavailable) as exc:
        CropSimulationEngine().simulate(
            crop_id="maize", planting_date="2024-05-15", awc_mm_per_m=150,
            root_depth_cm=60, allow_reference_kc=True, adapter="pcse_wofost")
    assert "no está integrado" in str(exc.value)


def test_simulation_does_not_invent_yield():
    result = CropSimulationEngine().simulate(
        crop_id="maize", planting_date="2024-05-15", awc_mm_per_m=150,
        root_depth_cm=60, allow_reference_kc=True)["result"]
    assert result["outputs"]["yield"]["value_t_ha"] is None
    assert result["calibration_status"] == "uncalibrated"
    assert result["validation_status"] == "not_validated"


def test_simulation_yield_requires_ky_and_source():
    engine = CropSimulationEngine()
    with pytest.raises(Exception):
        engine.simulate(crop_id="maize", planting_date="2024-05-15",
                        awc_mm_per_m=150, root_depth_cm=60,
                        allow_reference_kc=True,
                        potential_yield_t_ha=6.0)
    with pytest.raises(Exception):
        engine.simulate(crop_id="maize", planting_date="2024-05-15",
                        awc_mm_per_m=150, root_depth_cm=60,
                        allow_reference_kc=True, potential_yield_t_ha=6.0,
                        ky=1.0)


# --- calendario -------------------------------------------------------------
def test_calendar_distinguishes_model_estimate_from_practice():
    payload = AgriculturalCalendarEngine().generate("maize")["result"]
    assert payload["classification"]["historical_practice"] is None
    assert payload["classification"]["technical_recommendation"] is None
    assert payload["classification"]["forecast_dependent"] is False
    assert payload["planting_windows"]


def test_calendar_risk_periods_follow_stages():
    payload = AgriculturalCalendarEngine().generate(
        "maize", planting_date="2024-05-15")["result"]
    assert payload["stages"]
    assert len(payload["risk_periods"]) == len(payload["stages"])
    assert all("risks" in row for row in payload["risk_periods"])


def test_calendar_reports_gap_planting_months():
    payload = AgriculturalCalendarEngine().generate("lettuce_urban")["result"]
    assert payload["planting_months_catalog"]["status"] == "GAP"
