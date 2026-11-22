"""AGROSV — SocioAgriculturalIntegrationEngine (§7.1).

Une resultados agronómicos y contexto humano **sin sustituir** los cálculos
científicos. El bloque `scientific` proviene de los motores de Fase 6; el bloque
`human` de los motores sintéticos. No hay generación de texto ni LLM en la
ruta: `llm_used` es siempre `false`.

El balance hídrico solo se ejecuta si el llamador aporta AWC, profundidad
radicular y Kc (o autoriza Kc de referencia). En caso contrario se declara
`not_evaluated` con las entradas que faltan.
"""
from __future__ import annotations

from typing import Any

from ..agriculture import governance as AG
from ..agriculture.calendar import AgriculturalCalendarEngine
from ..agriculture.suitability import CropSuitabilityEngine
from ..agriculture.water_nutrient import (CropWaterNutrientEngine,
                                          WaterNutrientError)
from ..social import governance as SG
from ..social.household import AgriculturalHouseholdEngine
from ..social.persona import AgriculturalPersonaEngine

ENGINE = "socio_agricultural_integration"
ENGINE_VERSION = AG.ENGINE_VERSION


class IntegrationError(ValueError):
    pass


class SocioAgriculturalIntegrationEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.suitability = CropSuitabilityEngine()
        self.calendar = AgriculturalCalendarEngine()
        self.water = CropWaterNutrientEngine()
        self.persona = AgriculturalPersonaEngine()
        self.household = AgriculturalHouseholdEngine()

    def profile(self, *, lon: float, lat: float, crop_id: str,
                system: str = "rainfed", variety: dict[str, Any] | None = None,
                planting_date: str | None = None,
                awc_mm_per_m: float | None = None,
                root_depth_cm: float | None = None,
                initial_depletion_mm: float = 0.0,
                kc: dict[str, Any] | None = None,
                allow_reference_kc: bool = False,
                agent: dict[str, Any] | None = None,
                seed: int = 42) -> dict[str, Any]:
        suitability = self.suitability.evaluate(
            crop_id, lon, lat, system=system,
            irrigation_available=bool(agent and agent.get("state", {})
                                      .get("payload", {}).get("irrigated")))
        calendar = self.calendar.generate(
            crop_id, planting_date=planting_date, variety=variety)

        if awc_mm_per_m is not None and root_depth_cm is not None:
            if not planting_date:
                raise IntegrationError(
                    "el balance hídrico requiere planting_date")
            try:
                water = self.water.water_balance(
                    crop_id=crop_id,
                    planting_date=planting_date,
                    awc_mm_per_m=awc_mm_per_m, root_depth_cm=root_depth_cm,
                    initial_depletion_mm=initial_depletion_mm, kc=kc,
                    allow_reference_kc=allow_reference_kc)
            except (WaterNutrientError, KeyError) as exc:
                water = {"available": False, "reason": str(exc)}
        else:
            water = {
                "available": False, "reason": "faltan entradas de suelo",
                "required_inputs": ["awc_mm_per_m", "root_depth_cm",
                                    "kc o allow_reference_kc"],
            }

        human = None
        if agent is not None:
            persona = self.persona.compose(
                agent, source_profile=agent.get("source_profile"), seed=seed
            )
            household = self.household.compose(
                agent, profile=persona.get("source_profile"), seed=seed)
            src_profile = persona.get("source_profile") or {}
            human = {
                "agent_id": agent["agent_id"],
                "archetype": agent["archetype"],
                "nemotron_backed": bool(src_profile.get("from_nemotron_dataset")),
                "nemotron_uuid": src_profile.get("uuid"),
                "persona": persona.get("persona"),
                "persona_attachable": persona.get("attachable", True),
                "reason": persona.get("reason"),
                "household": household["household"],
                "household_record": household["record"],
                "synthetic": True,
            }

        links = {
            "suitability_to_decision": ("clase S1/S2/S3/N y factores "
                                        "limitantes como restricción dura"),
            "water_to_decision": ("déficit y ETa/ETm como contexto hídrico, "
                                  "nunca como precio ni ingreso"),
            "calendar_to_decision": ("ventanas de siembra y riesgos como "
                                     "contexto temporal"),
            "household_to_decision": ("mano de obra y presupuesto como "
                                      "restricciones de recursos"),
            "rule": ("un componente sintético no puede reemplazar una clase "
                     "de aptitud ni un balance hídrico"),
        }
        result = {
            "scientific": {
                "suitability": suitability,
                "calendar": calendar,
                "water_balance": water,
                "crop_id": crop_id.strip().lower(),
                "system": system,
            },
            "human": human,
            "links": links,
            "llm_used": False,
            "agronomic_outputs_from_engines": True,
            "component_classes": {
                "suitability": "model_output",
                "calendar": "model_output",
                "water_balance": ("model_output" if water.get("available")
                                  else "not_evaluated"),
                "persona": "synthetic",
                "household": "synthetic",
            },
        }
        return AG.envelope(
            ENGINE, result=result,
            sources=["crop_parameters_catalog", "copdem30", "soilgrids_2",
                     "open_meteo_point", "fao_56", "fao_aez",
                     "agrosv_scenario"],
            limitations=[
                "los bloques científico y sintético se publican juntos pero "
                "separados",
                "la clase de aptitud no es una recomendación de siembra",
                "el balance hídrico solo existe si se aportaron AWC, "
                "profundidad y Kc",
                "ningún componente sintético valida un resultado agronómico",
            ],
            processing=[
                AG.step("aptitud", "CropSuitabilityEngine.evaluate"),
                AG.step("calendario", "AgriculturalCalendarEngine.generate"),
                AG.step("balance hídrico", "CropWaterNutrientEngine"),
                AG.step("persona y hogar", "AgriculturalPersona/Household"),
            ],
            query={"lon": lon, "lat": lat, "crop_id": crop_id,
                   "system": system},
            extra={"synthetic_components": human is not None},
        )


__all__ = ["SocioAgriculturalIntegrationEngine", "IntegrationError"]
