"""AGROSV Phase 8 — Subsistema A: Inteligencia de Producción Agrícola.

Contiene los 6 motores del Subsistema A:
1. AgriculturalProductionEngine
2. CropYieldAnalysisEngine
3. ProductionSystemEngine
4. AgriculturalProductivityEngine
5. HarvestEstimationEngine
6. ProductionStatisticsEngine
"""
from __future__ import annotations

import json
import math
from typing import Any, Iterable, Mapping

import numpy as np

from .. import config as C
from ..agriculture.calendar import AgriculturalCalendarEngine
from ..agriculture.catalog import CROPS
from ..agriculture.phenology import CropPhenologyEngine
from ..agriculture.suitability import CropSuitabilityEngine
from ..agriculture.water_nutrient import CropWaterNutrientEngine, WaterNutrientError
from . import governance as EG

ENGINE_VERSION = EG.ENGINE_VERSION

PRODUCTION_SCALES = ("national", "departmental", "municipal", "agricultural_zone", "parcel")

YIELD_CLASSIFICATIONS = (
    "official_observed",
    "survey_based",
    "experimental",
    "model_estimated",
    "synthetic_scenario",
)

PRODUCTION_SYSTEMS: dict[str, dict[str, Any]] = {
    "rainfed": {
        "label": "Agricultura de secano",
        "water_regime": "rainfed",
        "typical_cycles_per_year": 1,
        "intensification": "low_to_medium",
        "characteristics": ["dependiente de precipitación", "alta exposición a canícula"],
    },
    "irrigated": {
        "label": "Agricultura bajo riego",
        "water_regime": "irrigated",
        "typical_cycles_per_year": 2,
        "intensification": "medium_to_high",
        "characteristics": ["requiere fuente y sistema de riego", "menor exposición a déficit hídrico"],
    },
    "smallholder": {
        "label": "Pequeña agricultura familiar",
        "water_regime": "mixed",
        "typical_cycles_per_year": 1,
        "intensification": "low_to_medium",
        "characteristics": ["mano de obra familiar predominante", "restricciones de capital"],
    },
    "subsistence": {
        "label": "Agricultura de subsistencia",
        "water_regime": "rainfed",
        "typical_cycles_per_year": 1,
        "intensification": "low",
        "characteristics": ["alto autoconsumo", "baja mecanización"],
    },
    "commercial": {
        "label": "Agricultura comercial",
        "water_regime": "mixed",
        "typical_cycles_per_year": 2,
        "intensification": "high",
        "characteristics": ["orientada a mercado", "mayor uso de insumos certificados"],
    },
    "intensive": {
        "label": "Agricultura intensiva",
        "water_regime": "irrigated",
        "typical_cycles_per_year": 2,
        "intensification": "high",
        "characteristics": ["alta densidad de insumos y mano de obra por ha"],
    },
    "extensive": {
        "label": "Agricultura extensiva",
        "water_regime": "rainfed",
        "typical_cycles_per_year": 1,
        "intensification": "low",
        "characteristics": ["bajo insumo por ha en superficies mayores"],
    },
    "agroforestry": {
        "label": "Sistemas agroforestales",
        "water_regime": "rainfed",
        "typical_cycles_per_year": 1,
        "intensification": "medium",
        "characteristics": ["árboles de sombra + cultivo principal (p.ej. café)"],
    },
    "protected": {
        "label": "Agricultura protegida",
        "water_regime": "irrigated",
        "typical_cycles_per_year": 3,
        "intensification": "very_high",
        "characteristics": ["invernadero/macrotúnel", "alta inversión inicial"],
    },
    "urban_periurban": {
        "label": "Agricultura urbana y periurbana",
        "water_regime": "irrigated",
        "typical_cycles_per_year": 3,
        "intensification": "medium_to_high",
        "characteristics": ["espacios reducidos", "ciclos cortos de hortalizas"],
    },
    "mixed_crop": {
        "label": "Cultivos asociados / milpa",
        "water_regime": "rainfed",
        "typical_cycles_per_year": 1,
        "intensification": "low_to_medium",
        "characteristics": ["asocio maíz-frijol o maíz-sorgo"],
    },
    "diversified": {
        "label": "Finca diversificada",
        "water_regime": "mixed",
        "typical_cycles_per_year": 2,
        "intensification": "medium",
        "characteristics": ["múltiples rubros agrícolas y/o pecuarios"],
    },
}


def _check_crop(crop_id: str) -> str:
    key = str(crop_id).strip().lower()
    if key not in CROPS:
        raise EG.EconomicError(f"cultivo desconocido en catálogo AGROSV: {crop_id!r}")
    return key


class ProductionStatisticsEngine:
    """Integra estadísticas oficiales verificadas (CAP 2025, WDI) sin inventar desagregaciones."""

    engine = "production_statistics"
    version = ENGINE_VERSION

    def _load_cap(self) -> dict[str, Any] | None:
        return EG.load_json_if_exists("cap_2025_public_aggregates.json")

    def _load_wb_agri_land(self) -> list[dict[str, Any]]:
        path = C.DATA / "samples" / "phase3" / "worldbank_slv" / "wb_agri_land_share_slv.json"
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list) and len(raw) > 1 and isinstance(raw[1], list):
            return [r for r in raw[1] if r.get("value") is not None]
        return []

    def summary(
        self,
        *,
        crop_id: str | None = None,
        scale: str = "national",
        department: str | None = None,
        municipality: str | None = None,
    ) -> dict[str, Any]:
        if scale not in PRODUCTION_SCALES:
            raise EG.EconomicError(f"escala inválida: {scale!r}; use {PRODUCTION_SCALES}")
        if scale in {"municipal", "parcel"} or municipality:
            return EG.economic_envelope(
                self.engine,
                result={
                    "available": False,
                    "scale": scale,
                    "municipality": municipality,
                    "reason": (
                        "no existen estadísticas oficiales municipales ni parcelarias "
                        "abiertas en el repositorio; AGROSV prohíbe inferirlas desde "
                        "totales nacionales"
                    ),
                    "unavailable_sources": ["cap_2025_municipal", "mag_anuario_tabular"],
                },
                sources=["cap_2025_public_aggregates"],
                assumptions=["los agregados nacionales no se desagregan proporcionalmente"],
                limitations=[
                    "el CAP 2025 no publica microdatos ni tabulados municipales abiertos",
                ],
                evidence_class="official_statistic",
                query={"crop_id": crop_id, "scale": scale, "municipality": municipality},
            )

        cap = self._load_cap()
        wb = self._load_wb_agri_land()
        records: list[dict[str, Any]] = []

        if cap:
            crops_block = cap.get("crops", {})
            target_keys = (
                [crop_id.strip().lower()]
                if crop_id and crop_id.strip().lower() in crops_block
                else ([] if crop_id else list(crops_block))
            )
            for key in target_keys:
                c = crops_block[key]
                geo = f"El Salvador ({department})" if department else "El Salvador"
                dept_share = (c.get("departmental_production_shares") or {}).get(department) if department else None
                if department and dept_share is None:
                    continue
                val = (
                    {
                        "national_production_qq": c.get("production_qq"),
                        "departmental_share": dept_share,
                        "implied_departmental_qq": (
                            round(c["production_qq"] * dept_share, 1)
                            if c.get("production_qq") and dept_share is not None
                            else None
                        ),
                    }
                    if department
                    else c
                )
                records.append(
                    EG.make_economic_record(
                        product_or_activity=key,
                        geography=geo,
                        observation_date="2025-04-30",
                        publication_date="2026-03-01",
                        reference_period=cap.get("reference_period", "2024-05 / 2025-04"),
                        currency="N/A",
                        unit="mz / qq / t",
                        source=cap["institution"],
                        methodology="V Censo Agropecuario 2025 (entregas públicas preliminares)",
                        verification_status="VALIDATED",
                        license_name=cap["license"],
                        evidence_class="official_statistic",
                        value=val,
                        uncertainty="cifras preliminares sin evaluación post-enumeración publicada",
                    )
                )

        wb_latest = wb[0] if wb else None
        return EG.economic_envelope(
            self.engine,
            result={
                "available": bool(records or wb_latest),
                "scale": scale,
                "crop_id": crop_id,
                "department": department,
                "cap_2025_records": records,
                "cap_2025_livestock": (cap or {}).get("livestock") if not crop_id else None,
                "worldbank_agricultural_land_pct": (
                    {
                        "indicator": "AG.LND.AGRI.ZS",
                        "year": wb_latest["date"],
                        "value_pct": round(float(wb_latest["value"]), 2),
                        "series_years": f"{wb[-1]['date']}–{wb[0]['date']}" if wb else None,
                    }
                    if wb_latest
                    else None
                ),
                "external_unavailable": ["faostat", "mag_anuario_2022_23"],
            },
            sources=["cap_2025_public_aggregates", "worldbank_agri_share"],
            assumptions=[
                "1 manzana = 0.70 ha y 1 quintal = 46 kg para equivalencias métricas",
            ],
            limitations=[
                "CAP 2025 corresponde a entregas públicas preliminares 1 y 2",
                "FAOSTAT y anuarios PDF del MAG no tienen serie tabular integrada",
                "no cubre estadísticas municipales ni parcelarias",
            ],
            evidence_class="official_statistic",
            query={"crop_id": crop_id, "scale": scale, "department": department},
        )


class ProductionSystemEngine:
    """Representa sistemas productivos y su manejo sin estandarizar fincas a la fuerza."""

    engine = "production_system"
    version = ENGINE_VERSION

    def catalog(self) -> dict[str, Any]:
        return {
            "count": len(PRODUCTION_SYSTEMS),
            "systems": [{"system_id": k, **v} for k, v in PRODUCTION_SYSTEMS.items()],
        }

    def profile(
        self,
        system_id: str,
        *,
        crop_id: str,
        area_ha: float,
        management: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        sid = str(system_id).strip().lower()
        if sid not in PRODUCTION_SYSTEMS:
            raise EG.EconomicError(
                f"sistema productivo desconocido: {system_id!r}; use {sorted(PRODUCTION_SYSTEMS)}"
            )
        crop = _check_crop(crop_id)
        if area_ha <= 0:
            raise EG.EconomicError("area_ha debe ser > 0")
        mgmt = dict(management or {})
        spec = PRODUCTION_SYSTEMS[sid]
        crop_spec = CROPS[crop]
        area_mz = round(EG.convert_area(area_ha, "ha", "mz"), 4)

        reported_fields = {
            "variety": mgmt.get("variety"),
            "crop_rotation": mgmt.get("crop_rotation"),
            "plant_density_plants_ha": mgmt.get("plant_density_plants_ha"),
            "irrigation_method": mgmt.get("irrigation_method"),
            "fertilization_plan": mgmt.get("fertilization_plan"),
            "pest_management": mgmt.get("pest_management"),
            "labor_days_per_cycle": mgmt.get("labor_days_per_cycle"),
            "machinery_used": mgmt.get("machinery_used"),
            "cycle_days": mgmt.get("cycle_days") or crop_spec.get("cycle_days", {}).get("typical"),
        }
        missing = [k for k, v in reported_fields.items() if v is None]

        return EG.economic_envelope(
            self.engine,
            result={
                "system_id": sid,
                "system_spec": spec,
                "crop_id": crop,
                "area_ha": round(float(area_ha), 4),
                "area_mz": area_mz,
                "management": reported_fields,
                "missing_management_fields": missing,
                "standardized_farm_assumed": False,
            },
            sources=["crop_parameters_catalog"],
            assumptions=[
                "1 manzana = 0.70 hectáreas",
                "los campos de manejo no aportados quedan como null (no se asume finca estándar)",
            ],
            limitations=[
                "los parámetros agronómicos del catálogo no están calibrados por variedad local",
            ],
            evidence_class="institutional_reference",
            query={"system_id": sid, "crop_id": crop, "area_ha": area_ha},
        )


class CropYieldAnalysisEngine:
    """Analiza rendimientos por ha/mz separando estrictamente su clase de evidencia."""

    engine = "crop_yield_analysis"
    version = ENGINE_VERSION

    def analyze(
        self,
        *,
        crop_id: str,
        observations: Iterable[Mapping[str, Any]],
        target_unit: str = "t/ha",
    ) -> dict[str, Any]:
        crop = _check_crop(crop_id)
        obs_list = list(observations)
        if not obs_list:
            raise EG.EconomicError("se requiere al menos una observación de rendimiento")

        normalized: list[dict[str, Any]] = []
        by_class: dict[str, list[float]] = {}
        by_region: dict[str, list[float]] = {}
        by_season: dict[str, list[float]] = {}

        for idx, item in enumerate(obs_list):
            y_class = str(item.get("yield_class") or "").strip().lower()
            if y_class not in YIELD_CLASSIFICATIONS:
                raise EG.EconomicError(
                    f"observación {idx}: yield_class inválido {y_class!r}; use {YIELD_CLASSIFICATIONS}"
                )
            val = item.get("yield_value")
            if val is None or float(val) < 0:
                raise EG.EconomicError(f"observación {idx}: yield_value inválido")
            mass_u = str(item.get("mass_unit") or "t").strip().lower()
            area_u = str(item.get("area_unit") or "ha").strip().lower()
            # Convertir a t/ha de forma uniforme
            tons = EG.convert_mass(float(val), mass_u, "t")
            ha = EG.convert_area(1.0, area_u, "ha")
            t_per_ha = tons / ha
            qq_per_mz = EG.convert_mass(t_per_ha, "t", "qq") * EG.MANZANA_TO_HA

            region = str(item.get("region") or "no_especificada")
            season = str(item.get("season") or "no_especificada")
            entry = {
                "yield_class": y_class,
                "original_value": float(val),
                "original_unit": f"{mass_u}/{area_u}",
                "yield_t_ha": round(t_per_ha, 4),
                "yield_qq_mz": round(qq_per_mz, 4),
                "region": region,
                "season": season,
                "management": item.get("management"),
                "year": item.get("year"),
                "source": item.get("source") or "user_supplied",
            }
            normalized.append(entry)
            by_class.setdefault(y_class, []).append(t_per_ha)
            by_region.setdefault(region, []).append(t_per_ha)
            by_season.setdefault(season, []).append(t_per_ha)

        def _stats(vals: list[float]) -> dict[str, Any]:
            arr = np.array(vals, dtype=float)
            mean = float(arr.mean())
            std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
            cv = (std / mean) if mean > 0 else None
            return {
                "n": len(vals),
                "mean_t_ha": round(mean, 4),
                "mean_qq_mz": round(EG.convert_mass(mean, "t", "qq") * EG.MANZANA_TO_HA, 4),
                "min_t_ha": round(float(arr.min()), 4),
                "max_t_ha": round(float(arr.max()), 4),
                "std_t_ha": round(std, 4),
                "cv": round(cv, 4) if cv is not None else None,
            }

        class_stats = {k: _stats(v) for k, v in by_class.items()}
        mixed_classes = len(class_stats) > 1
        # Evita mezclar clases en un promedio nacional engañoso
        official_only = by_class.get("official_observed")
        ev_class = "official_statistic" if (len(class_stats) == 1 and official_only) else "model_estimate"

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop,
                "target_unit": target_unit,
                "count": len(normalized),
                "observations": normalized,
                "stats_by_yield_class": class_stats,
                "stats_by_region": {k: _stats(v) for k, v in by_region.items()},
                "stats_by_season": {k: _stats(v) for k, v in by_season.items()},
                "mixed_evidence_classes": mixed_classes,
                "unit_conversions": {
                    "area": "1 mz = 0.70 ha",
                    "mass": "1 qq = 46 kg; 1 t = 1000 kg",
                },
                "national_statistic_claimed": False,
            },
            sources=["crop_parameters_catalog"],
            assumptions=[
                "1 mz = 0.70 ha y 1 qq = 46 kg",
                "los promedios por clase no se combinan entre sí cuando hay mezcla de orígenes",
            ],
            limitations=[
                "rendimientos experimentales, modelados o sintéticos nunca equivalen a estadística nacional",
            ],
            evidence_class=ev_class,
            query={"crop_id": crop, "n_observations": len(obs_list)},
        )


class AgriculturalProductivityEngine:
    """Calcula indicadores físicos y económicos de productividad sin confundirlos."""

    engine = "agricultural_productivity"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        crop_id: str,
        production_t: float,
        area_ha: float,
        labor_days: float | None = None,
        water_m3: float | None = None,
        input_cost_usd: float | None = None,
        energy_mj: float | None = None,
        gross_revenue_usd: float | None = None,
        total_cost_usd: float | None = None,
    ) -> dict[str, Any]:
        crop = _check_crop(crop_id)
        if area_ha <= 0 or production_t < 0:
            raise EG.EconomicError("area_ha debe ser > 0 y production_t >= 0")

        prod_kg = production_t * 1000.0
        land_t_ha = production_t / area_ha
        land_qq_mz = EG.convert_mass(land_t_ha, "t", "qq") * EG.MANZANA_TO_HA

        indicators = {
            "land_productivity_t_ha": round(land_t_ha, 4),
            "land_productivity_qq_mz": round(land_qq_mz, 4),
            "labor_productivity_kg_per_day": (
                round(prod_kg / labor_days, 3) if labor_days and labor_days > 0 else None
            ),
            "water_productivity_kg_per_m3": (
                round(prod_kg / water_m3, 4) if water_m3 and water_m3 > 0 else None
            ),
            "input_productivity_kg_per_usd": (
                round(prod_kg / input_cost_usd, 4)
                if input_cost_usd and input_cost_usd > 0
                else None
            ),
            "energy_productivity_kg_per_mj": (
                round(prod_kg / energy_mj, 4) if energy_mj and energy_mj > 0 else None
            ),
        }
        economic_indicators = {
            "revenue_per_ha_usd": (
                round(gross_revenue_usd / area_ha, 2)
                if gross_revenue_usd is not None
                else None
            ),
            "benefit_cost_ratio": (
                round(gross_revenue_usd / total_cost_usd, 4)
                if gross_revenue_usd is not None and total_cost_usd and total_cost_usd > 0
                else None
            ),
            "note": "la productividad física no implica rentabilidad financiera",
        }
        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop,
                "area_ha": round(float(area_ha), 4),
                "production_t": round(float(production_t), 4),
                "physical_productivity": indicators,
                "economic_productivity": economic_indicators,
            },
            sources=["crop_parameters_catalog"],
            assumptions=["cálculos deterministas de razón producto / insumo sobre datos declarados"],
            limitations=[
                "indicadores sin datos de entrada quedan como null",
                "no comparar sistemas entre cultivos, climas o calidades distintas sin normalización",
            ],
            evidence_class="model_estimate",
            query={"crop_id": crop, "area_ha": area_ha, "production_t": production_t},
        )


class HarvestEstimationEngine:
    """Estima ventanas de cosecha y producción esperada conectando Fases 6 y 7."""

    engine = "harvest_estimation"
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.calendar = AgriculturalCalendarEngine()
        self.phenology = CropPhenologyEngine()
        self.water = CropWaterNutrientEngine()

    def estimate(
        self,
        *,
        crop_id: str,
        planting_date: str,
        area_ha: float,
        variety: Mapping[str, Any] | None = None,
        reference_yield_t_ha: float | None = None,
        awc_mm_per_m: float | None = None,
        root_depth_cm: float | None = None,
        allow_reference_kc: bool = False,
        satellite_ndvi_anomaly: float | None = None,
    ) -> dict[str, Any]:
        crop = _check_crop(crop_id)
        if area_ha <= 0:
            raise EG.EconomicError("area_ha debe ser > 0")
        p_date = EG.check_iso_date(planting_date, "planting_date")

        cal = self.calendar.generate(crop, planting_date=p_date, variety=dict(variety) if variety else None)
        pheno_result: dict[str, Any] = {"available": False}
        try:
            pheno = self.phenology.run(crop, planting_date=p_date, variety=dict(variety) if variety else None)
            pheno_result = {"available": True, **pheno.get("result", {})}
        except Exception as exc:  # noqa: BLE001
            pheno_result = {"available": False, "reason": str(exc)}
        stages_obj = pheno_result.get("stages")
        if isinstance(stages_obj, list) and stages_obj:
            harvest_window = stages_obj[-1]
        elif isinstance(stages_obj, dict):
            harvest_window = stages_obj.get("maturity") or (cal.get("result") or {}).get("harvest_window")
        else:
            harvest_window = (cal.get("result") or {}).get("harvest_window")

        water_summary: dict[str, Any] = {"available": False, "reason": "faltan awc_mm_per_m y root_depth_cm"}
        stress_ratio: float | None = None
        if awc_mm_per_m is not None and root_depth_cm is not None:
            try:
                wb = self.water.water_balance(
                    crop_id=crop,
                    planting_date=p_date,
                    awc_mm_per_m=awc_mm_per_m,
                    root_depth_cm=root_depth_cm,
                    allow_reference_kc=allow_reference_kc,
                )
                wres = wb.get("result", {})
                eta = wres.get("eta_mm_total")
                etm = wres.get("etm_mm_total")
                stress_ratio = round(eta / etm, 4) if (eta is not None and etm and etm > 0) else None
                water_summary = {
                    "available": True,
                    "days_simulated": wres.get("days"),
                    "eta_etm_ratio": stress_ratio,
                    "stress_days": wres.get("stress_days"),
                }
            except WaterNutrientError as exc:
                water_summary = {"available": False, "reason": str(exc)}

        # Producción esperada SOLO si el usuario aporta rendimiento de referencia
        estimated_prod_t = None
        yield_note = "no se estima tonelaje sin reference_yield_t_ha aportado"
        if reference_yield_t_ha is not None:
            if reference_yield_t_ha < 0:
                raise EG.EconomicError("reference_yield_t_ha debe ser >= 0")
            factor = stress_ratio if stress_ratio is not None else 1.0
            estimated_prod_t = round(float(reference_yield_t_ha) * float(area_ha) * factor, 3)
            yield_note = (
                "estimación modelada multiplicando rendimiento de referencia × área × razón ETa/ETm"
                if stress_ratio is not None
                else "estimación aritmética sobre rendimiento de referencia sin ajuste hídrico"
            )

        sat_note = (
            "anomalía NDVI recibida solo como indicador contextual; el satélite no mide toneladas cosechadas"
            if satellite_ndvi_anomaly is not None
            else "sin observación satelital adjunta"
        )

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop,
                "planting_date": p_date,
                "area_ha": round(float(area_ha), 4),
                "expected_harvest_window": harvest_window,
                "is_observed_harvest_date": False,
                "calendar_summary": cal.get("result"),
                "water_balance": water_summary,
                "satellite_context": {
                    "ndvi_anomaly": satellite_ndvi_anomaly,
                    "direct_production_measurement": False,
                    "note": sat_note,
                },
                "estimated_production_t": estimated_prod_t,
                "estimated_production_qq": (
                    round(EG.convert_mass(estimated_prod_t, "t", "qq"), 2)
                    if estimated_prod_t is not None
                    else None
                ),
                "yield_estimation_note": yield_note,
            },
            sources=["crop_parameters_catalog"],
            assumptions=[
                "las ventanas fenológicas se derivan de duraciones de referencia del catálogo AGROSV",
                "una ventana de cosecha esperada no equivale a fecha observada en campo",
            ],
            limitations=[
                "no existe un modelo varietal calibrado de biomasa/rendimiento",
                "las observaciones satelitales no miden producción cosechada sin calibración de campo",
            ],
            evidence_class="model_estimate",
            query={"crop_id": crop, "planting_date": p_date, "area_ha": area_ha},
        )


class AgriculturalProductionEngine:
    """Motor integrador de producción agrícola multi-escala (Subsistema A)."""

    engine = "agricultural_production"
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.suitability = CropSuitabilityEngine()
        self.systems = ProductionSystemEngine()
        self.harvest = HarvestEstimationEngine()
        self.stats = ProductionStatisticsEngine()

    def assess(
        self,
        *,
        crop_id: str,
        scale: str = "parcel",
        system_id: str = "rainfed",
        area_ha: float = 1.0,
        lon: float | None = None,
        lat: float | None = None,
        department: str | None = None,
        planting_date: str | None = None,
        reference_yield_t_ha: float | None = None,
        management: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if scale not in PRODUCTION_SCALES:
            raise EG.EconomicError(f"escala inválida: {scale!r}; use {PRODUCTION_SCALES}")
        crop = _check_crop(crop_id)
        sys_prof = self.systems.profile(
            system_id, crop_id=crop, area_ha=area_ha, management=management
        )["result"]

        suitability_block: dict[str, Any] = {"evaluated": False}
        if lon is not None and lat is not None:
            suitability_block = self.suitability.evaluate(
                crop, lon, lat,
                system=system_id if system_id in {"rainfed", "irrigated"} else "rainfed",
                irrigation_available=(system_id in {"irrigated", "protected", "intensive"}),
            )["result"]

        harvest_block = (
            self.harvest.estimate(
                crop_id=crop,
                planting_date=planting_date,
                area_ha=area_ha,
                reference_yield_t_ha=reference_yield_t_ha,
            )["result"]
            if planting_date
            else None
        )

        official_context = (
            self.stats.summary(crop_id=crop, scale=scale, department=department)["result"]
            if scale in {"national", "departmental"}
            else {"available": False, "note": "contexto estadístico oficial solo disponible a escala nacional/departamental"}
        )

        return EG.economic_envelope(
            self.engine,
            result={
                "crop_id": crop,
                "scale": scale,
                "department": department,
                "production_system": sys_prof,
                "territorial_suitability": suitability_block,
                "harvest_estimation": harvest_block,
                "official_statistics_context": official_context,
                "distinction": {
                    "official_observed": "proveniente de CAP 2025 / WDI cuando existe",
                    "modeled_estimate": "salida de aptitud, calendario o balance hídrico",
                    "hypothetical_scenario": "supuestos de área o rendimiento aportados por el usuario",
                },
            },
            sources=["crop_parameters_catalog", "cap_2025_public_aggregates"],
            assumptions=[
                "la escala espacial determina si existen estadísticas oficiales o solo análisis de sitio",
            ],
            limitations=[
                "el análisis parcelario requiere datos reales de finca aportados por el usuario",
                "no sustituye mediciones de campo ni el CAP 2025",
            ],
            evidence_class="model_estimate",
            query={"crop_id": crop, "scale": scale, "system_id": system_id, "area_ha": area_ha},
        )


__all__ = [
    "AgriculturalProductionEngine",
    "AgriculturalProductivityEngine",
    "CropYieldAnalysisEngine",
    "HarvestEstimationEngine",
    "PRODUCTION_SCALES",
    "PRODUCTION_SYSTEMS",
    "ProductionStatisticsEngine",
    "ProductionSystemEngine",
    "YIELD_CLASSIFICATIONS",
]
