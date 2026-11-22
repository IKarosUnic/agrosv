"""AGROSV — WaterStressDetectionEngine (Fase 7, §5.3).

Cinco conceptos que **no** se sustituyen entre sí:

1. sequía meteorológica — déficit de precipitación frente a ET0;
2. sequía agrícola — déficit de agua del suelo que afecta al cultivo;
3. déficit de humedad del suelo — contenido relativo;
4. estrés hídrico del cultivo — reducción de la transpiración (FAO-56, Ks);
5. sequía hidrológica — caudales/niveles bajo lo normal (**no calculable**:
   no hay aforos integrados).

Precipitación baja **no** equivale a estrés del cultivo: hace falta agua del
suelo, demanda y, si existe, una señal de la vegetación.
"""
from __future__ import annotations

from typing import Any

from . import governance as G

ENGINE = "water_stress_detection"
ENGINE_VERSION = G.ENGINE_VERSION

#: Clases operativas de AGROSV para P/ET0. No son un índice oficial de sequía.
PRECIP_RATIO_CLASSES: tuple[tuple[float, str, str], ...] = (
    (0.5, "severe_deficit", "P/ET0 < 0,50"),
    (0.75, "moderate_deficit", "P/ET0 0,50–0,75"),
    (1.0, "slight_deficit", "P/ET0 0,75–1,00"),
    (float("inf"), "no_climatic_deficit", "P/ET0 ≥ 1,00"),
)


def _classify_ratio(ratio: float) -> str:
    for limit, label, _ in PRECIP_RATIO_CLASSES:
        if ratio < limit:
            return label
    return "no_climatic_deficit"


class WaterStressDetectionEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def meteorological_ratio(self, precip_mm: float, et0_mm: float) -> dict[str, Any]:
        """Cociente P/ET0 del periodo, con su clase declarada."""
        if not (G.is_number(precip_mm) and G.is_number(et0_mm)):
            raise G.MonitoringError("P y ET0 deben ser números finitos")
        if precip_mm < 0 or et0_mm <= 0:
            raise G.MonitoringError("P ≥ 0 y ET0 > 0")
        ratio = float(precip_mm) / float(et0_mm)
        return {
            "precipitation_mm": float(precip_mm), "et0_mm": float(et0_mm),
            "ratio": round(ratio, 4), "class": _classify_ratio(ratio),
            "method": "P/ET0 del periodo",
            "limitations": [
                "no es SPI/SPEI: no estandariza por distribución ni por años",
                "no incorpora el agua almacenada en el suelo",
                "un cociente bajo no prueba estrés del cultivo",
            ],
        }

    def soil_water(self, *, depletion_mm: float, taw_mm: float,
                   raw_mm: float) -> dict[str, Any]:
        """Coeficiente Ks de FAO-56 a partir del agua disponible.

        Ks = 1 si Dr ≤ RAW; (TAW − Dr)/(TAW − RAW) en caso contrario, acotado
        a [0, 1]. TAW = (θfc − θwp)·Zr y RAW = p·TAW son entradas del usuario.
        """
        for name, value in (("depletion_mm", depletion_mm), ("taw_mm", taw_mm),
                            ("raw_mm", raw_mm)):
            if not G.is_number(value):
                raise G.MonitoringError(f"{name} debe ser finito")
        if taw_mm <= 0:
            raise G.MonitoringError("TAW debe ser > 0")
        if not 0 <= raw_mm < taw_mm:
            raise G.MonitoringError("RAW debe cumplir 0 ≤ RAW < TAW")
        dr = max(0.0, float(depletion_mm))
        if dr <= raw_mm:
            ks = 1.0
        else:
            ks = (float(taw_mm) - dr) / (float(taw_mm) - float(raw_mm))
        ks = max(0.0, min(1.0, ks))
        return {
            "depletion_mm": dr, "taw_mm": float(taw_mm), "raw_mm": float(raw_mm),
            "ks": round(ks, 4),
            "depletion_fraction": round(min(1.0, dr / float(taw_mm)), 4),
            "stress": bool(ks < 1.0),
            "method": "balance de agua del suelo FAO-56 (Ks)",
            "limitations": [
                "TAW y RAW dependen de textura y profundidad radicular aportadas",
                "no incluye capilaridad ni flujo lateral",
                "Ks < 1 indica déficit relativo, no una pérdida de rendimiento",
            ],
        }

    def assess(self, *, precip_mm: float | None = None,
               et0_mm: float | None = None, etc_mm: float | None = None,
               taw_mm: float | None = None,
               depletion_mm: float | None = None,
               irrigation_mm: float = 0.0,
               ndmi: float | None = None,
               ndmi_threshold: float | None = None,
               ndmi_threshold_source: str | None = None) -> dict[str, Any]:
        meteorological = None
        if G.is_number(precip_mm) and G.is_number(et0_mm):
            meteorological = self.meteorological_ratio(precip_mm, et0_mm)

        agricultural = None
        if G.is_number(taw_mm) and G.is_number(depletion_mm):
            raw = 0.5 * float(taw_mm)  # p = 0,5 por defecto, declarado abajo
            agricultural = self.soil_water(depletion_mm=depletion_mm,
                                          taw_mm=float(taw_mm), raw_mm=raw)
            agricultural["raw_assumption"] = ("RAW = 0,5·TAW por defecto; "
                                              "puede declararse otro valor")

        soil_deficit = None
        if agricultural is not None:
            soil_deficit = {
                "depletion_fraction": agricultural["depletion_fraction"],
                "class": ("sin_deficit" if agricultural["ks"] >= 1.0 else
                          "deficit_moderado" if agricultural["ks"] >= 0.5 else
                          "deficit_severo"),
                "method": "Dr/TAW con umbrales declarados",
            }

        crop_stress = None
        evidence: list[str] = []
        if agricultural is not None:
            evidence.append("balance_de_agua_del_suelo")
        if G.is_number(ndmi) and G.is_number(ndmi_threshold):
            if not ndmi_threshold_source:
                raise G.MonitoringError(
                    "un umbral de NDMI exige fuente declarada")
            evidence.append("ndmi")
        if agricultural is not None:
            crop_stress = {
                "status": ("possible_water_stress" if agricultural["stress"]
                           else "no_water_deficit_detected"),
                "ks": agricultural["ks"],
                "restriction": ("sin restricción" if agricultural["ks"] >= 1.0
                                else "restricción parcial" if agricultural["ks"] >= 0.5
                                else "restricción severa"),
                "evidence": evidence,
                "method": "Ks FAO-56; NDMI solo si hay umbral con fuente",
            }
        demand = None
        if G.is_number(etc_mm):
            supply = (float(precip_mm or 0.0) + float(irrigation_mm or 0.0))
            demand = {
                "etc_mm": float(etc_mm), "supply_mm": round(supply, 3),
                "irrigation_mm": float(irrigation_mm or 0.0),
                "ratio": round(supply / float(etc_mm), 4) if etc_mm else None,
                "note": ("el riego solo cuenta si el usuario lo declara; "
                         "proximidad a una fuente no es acceso al agua"),
            }
        hydrological = {
            "value": None, "status": "not_evaluated",
            "reason": ("no hay series de caudales ni aforos oficiales "
                       "integradas en el repositorio"),
        }
        missing = [name for name, value in (
            ("precip_mm", precip_mm), ("et0_mm", et0_mm),
            ("taw_mm", taw_mm), ("depletion_mm", depletion_mm)) if value is None]
        return {
            "engine": self.engine, "engine_version": self.version,
            "evidence_class": "model_estimate",
            "method": "balance P−ET0 y agua del suelo FAO-56, por separado",
            "meteorological_drought": meteorological,
            "agricultural_drought": agricultural,
            "soil_moisture_deficit": soil_deficit,
            "crop_water_stress": crop_stress,
            "hydrological_drought": hydrological,
            "crop_demand": demand,
            "ndmi": {
                "value": G.finite_or_none(ndmi),
                "threshold": G.finite_or_none(ndmi_threshold),
                "threshold_source": ndmi_threshold_source,
                "used": bool(G.is_number(ndmi) and G.is_number(ndmi_threshold)),
            },
            "conclusion": (
                None if crop_stress is None else crop_stress["status"]),
            "missing_evidence": missing,
            "assumptions": [
                "RAW = 0,5·TAW cuando no se declara otro valor",
                "el balance es del periodo consultado, no una simulación diaria",
            ],
            "limitations": [
                "no se calcula sequía hidrológica sin aforos",
                "un déficit meteorológico no implica estrés del cultivo",
                "NDMI no es humedad del suelo medidas",
            ],
            "note": ("las cinco categorías se informan por separado; "
                     "no se colapsan en un índice único"),
        }
