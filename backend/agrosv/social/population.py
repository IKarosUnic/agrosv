"""AGROSV — AgriculturalPopulationEngine (§5.2).

Genera poblaciones sintéticas configurables. Los arquetipos son **tipos de
simulación**, no una descripción de la distribución real de productores
salvadoreños. Cada parámetro es un rango de escenario (`SCENARIO`), no una
estadística: no hay censo de productores por arquetipo ni microdatos del CAP.

Reproducibilidad: `numpy.random.default_rng(seed)` (PCG64). Misma versión de
NumPy + misma semilla + mismos arquetipos ⇒ misma población.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

import numpy as np

from . import governance as SG

ENGINE = "agricultural_population"
ENGINE_VERSION = SG.ENGINE_VERSION

DEPARTMENTS = (
    "Ahuachapán", "Santa Ana", "Sonsonate", "Chalatenango", "La Libertad",
    "San Salvador", "Cuscatlán", "La Paz", "Cabañas", "San Vicente",
    "Usulután", "San Miguel", "Morazán", "La Unión",
)

BOUNDS_BASIS = "synthetic_scenario_bounds (no observado)"

ARCHETYPES: dict[str, dict[str, Any]] = {
    "subsistence_maize": {
        "label": "Productor de subsistencia (maíz)",
        "production_system": "rainfed_subsistence",
        "primary_crop": "maize",
        "crops": ["maize", "beans"],
        "area_ha": [0.2, 1.5],
        "irrigated": [0.0, 0.10],
        "capital_usd": [50, 800],
        "credit_access": [0.0, 0.25],
        "market_access": [0.05, 0.35],
        "household_labor": [1, 4],
        "hired_labor": [0, 1],
        "tenure": ["propia", "arrendada", "familiar"],
        "risk_aversion": [0.55, 0.90],
        "info_access": [0.05, 0.40],
        "experience_years": [5, 45],
        "digital_literacy": [0.0, 0.30],
        "cooperative": [0.0, 0.10],
        "off_farm_income": [0.25, 0.75],
        "area_type": "rural",
    },
    "smallholder_basic_grains": {
        "label": "Pequeño productor de granos básicos",
        "production_system": "rainfed_smallholder",
        "primary_crop": "maize",
        "crops": ["maize", "beans", "sorghum"],
        "area_ha": [1.0, 5.0],
        "irrigated": [0.0, 0.15],
        "capital_usd": [300, 3000],
        "credit_access": [0.05, 0.40],
        "market_access": [0.20, 0.60],
        "household_labor": [2, 5],
        "hired_labor": [0, 2],
        "tenure": ["propia", "arrendada", "mixta"],
        "risk_aversion": [0.45, 0.80],
        "info_access": [0.15, 0.55],
        "experience_years": [3, 40],
        "digital_literacy": [0.05, 0.45],
        "cooperative": [0.05, 0.35],
        "off_farm_income": [0.10, 0.50],
        "area_type": "rural",
    },
    "bean_producer": {
        "label": "Productor de frijol",
        "production_system": "rainfed_smallholder",
        "primary_crop": "beans",
        "crops": ["beans", "maize"],
        "area_ha": [0.3, 3.0],
        "irrigated": [0.0, 0.10],
        "capital_usd": [100, 2000],
        "credit_access": [0.0, 0.30],
        "market_access": [0.10, 0.50],
        "household_labor": [1, 4],
        "hired_labor": [0, 1],
        "tenure": ["propia", "arrendada", "familiar"],
        "risk_aversion": [0.50, 0.85],
        "info_access": [0.10, 0.45],
        "experience_years": [3, 40],
        "digital_literacy": [0.0, 0.40],
        "cooperative": [0.0, 0.25],
        "off_farm_income": [0.20, 0.65],
        "area_type": "rural",
    },
    "coffee_smallholder": {
        "label": "Pequeño caficultor",
        "production_system": "agroforestry_smallholder",
        "primary_crop": "coffee",
        "crops": ["coffee", "maize"],
        "area_ha": [0.5, 6.0],
        "irrigated": [0.0, 0.05],
        "capital_usd": [200, 5000],
        "credit_access": [0.05, 0.45],
        "market_access": [0.15, 0.65],
        "household_labor": [2, 6],
        "hired_labor": [0, 4],
        "tenure": ["propia", "arrendada", "cooperativa"],
        "risk_aversion": [0.45, 0.80],
        "info_access": [0.15, 0.60],
        "experience_years": [5, 50],
        "digital_literacy": [0.05, 0.50],
        "cooperative": [0.20, 0.75],
        "off_farm_income": [0.05, 0.40],
        "area_type": "rural",
    },
    "vegetable_producer": {
        "label": "Productor hortícola",
        "production_system": "irrigated_horticulture",
        "primary_crop": "tomato",
        "crops": ["tomato", "sweet_pepper", "cucumber", "onion"],
        "area_ha": [0.2, 3.0],
        "irrigated": [0.45, 0.95],
        "capital_usd": [500, 8000],
        "credit_access": [0.10, 0.55],
        "market_access": [0.40, 0.85],
        "household_labor": [1, 4],
        "hired_labor": [0, 3],
        "tenure": ["propia", "arrendada", "mixta"],
        "risk_aversion": [0.35, 0.70],
        "info_access": [0.25, 0.75],
        "experience_years": [2, 30],
        "digital_literacy": [0.10, 0.65],
        "cooperative": [0.05, 0.40],
        "off_farm_income": [0.05, 0.35],
        "area_type": "rural",
    },
    "fruit_producer": {
        "label": "Productor frutícola",
        "production_system": "rainfed_or_irrigated_orchard",
        "primary_crop": "mango",
        "crops": ["mango", "avocado", "citrus", "papaya"],
        "area_ha": [0.5, 8.0],
        "irrigated": [0.15, 0.60],
        "capital_usd": [800, 12000],
        "credit_access": [0.10, 0.55],
        "market_access": [0.30, 0.80],
        "household_labor": [1, 5],
        "hired_labor": [0, 4],
        "tenure": ["propia", "arrendada"],
        "risk_aversion": [0.35, 0.70],
        "info_access": [0.20, 0.70],
        "experience_years": [3, 35],
        "digital_literacy": [0.10, 0.60],
        "cooperative": [0.05, 0.40],
        "off_farm_income": [0.05, 0.40],
        "area_type": "rural",
    },
    "mixed_crop": {
        "label": "Productor de cultivos mixtos",
        "production_system": "diversified_smallholder",
        "primary_crop": "maize",
        "crops": ["maize", "beans", "sorghum", "tomato"],
        "area_ha": [0.5, 4.0],
        "irrigated": [0.0, 0.30],
        "capital_usd": [150, 4000],
        "credit_access": [0.0, 0.40],
        "market_access": [0.15, 0.60],
        "household_labor": [2, 5],
        "hired_labor": [0, 2],
        "tenure": ["propia", "arrendada", "familiar"],
        "risk_aversion": [0.40, 0.75],
        "info_access": [0.10, 0.55],
        "experience_years": [3, 45],
        "digital_literacy": [0.05, 0.50],
        "cooperative": [0.05, 0.35],
        "off_farm_income": [0.10, 0.50],
        "area_type": "rural",
    },
    "urban_farmer": {
        "label": "Agricultor urbano",
        "production_system": "urban_small_space",
        "primary_crop": "lettuce_urban",
        "crops": ["lettuce_urban", "radish_urban", "cilantro_urban"],
        "area_ha": [0.005, 0.10],
        "irrigated": [0.60, 0.98],
        "capital_usd": [20, 600],
        "credit_access": [0.0, 0.15],
        "market_access": [0.05, 0.50],
        "household_labor": [1, 3],
        "hired_labor": [0, 0],
        "tenure": ["propia", "familiar", "comunitaria"],
        "risk_aversion": [0.30, 0.70],
        "info_access": [0.20, 0.75],
        "experience_years": [0, 20],
        "digital_literacy": [0.20, 0.85],
        "cooperative": [0.0, 0.20],
        "off_farm_income": [0.40, 0.90],
        "area_type": "urbano",
    },
    "cooperative_member": {
        "label": "Miembro de cooperativa",
        "production_system": "cooperative",
        "primary_crop": "coffee",
        "crops": ["coffee", "maize", "beans"],
        "area_ha": [0.5, 5.0],
        "irrigated": [0.0, 0.20],
        "capital_usd": [300, 6000],
        "credit_access": [0.25, 0.75],
        "market_access": [0.40, 0.85],
        "household_labor": [1, 5],
        "hired_labor": [0, 3],
        "tenure": ["propia", "cooperativa"],
        "risk_aversion": [0.35, 0.70],
        "info_access": [0.35, 0.80],
        "experience_years": [3, 45],
        "digital_literacy": [0.10, 0.60],
        "cooperative": [1.0, 1.0],
        "off_farm_income": [0.05, 0.35],
        "area_type": "rural",
    },
    "commercial_technified": {
        "label": "Productor comercial tecnificado",
        "production_system": "commercial_technified",
        "primary_crop": "sugarcane",
        "crops": ["sugarcane", "maize", "sorghum"],
        "area_ha": [10.0, 200.0],
        "irrigated": [0.30, 0.90],
        "capital_usd": [20000, 500000],
        "credit_access": [0.50, 0.95],
        "market_access": [0.70, 0.99],
        "household_labor": [0, 3],
        "hired_labor": [5, 60],
        "tenure": ["propia", "arrendada"],
        "risk_aversion": [0.20, 0.55],
        "info_access": [0.55, 0.95],
        "experience_years": [5, 40],
        "digital_literacy": [0.40, 0.90],
        "cooperative": [0.0, 0.30],
        "off_farm_income": [0.0, 0.15],
        "area_type": "rural",
    },
}


class PopulationError(ValueError):
    pass


def _uniform(rng: np.random.Generator, bounds: list[float]) -> float:
    return float(rng.uniform(bounds[0], bounds[1]))


class AgriculturalPopulationEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        from ..agriculture.catalog import CROPS

        for name, spec in ARCHETYPES.items():
            for crop in spec["crops"]:
                if crop not in CROPS:
                    raise PopulationError(f"{name}: cultivo desconocido {crop}")

    def archetypes(self) -> dict[str, Any]:
        return {
            "count": len(ARCHETYPES),
            "archetypes": [{"archetype": k, **v,
                            "parameter_basis": BOUNDS_BASIS}
                           for k, v in ARCHETYPES.items()],
            "warning": ("son tipos de simulación, no una distribución "
                        "demográfica de El Salvador"),
        }

    def generate(self, size: int = 100, *, seed: int = 42,
                 archetypes: Iterable[str] | None = None,
                 weights: Mapping[str, float] | None = None,
                 scenario_id: str | None = None) -> dict[str, Any]:
        if not isinstance(size, (int, np.integer)) or size <= 0:
            raise PopulationError("size debe ser un entero > 0")
        if size > 100_000:
            raise PopulationError(
                "size > 100 000: use lotes; no se generan millones por defecto")
        names = list(archetypes) if archetypes else list(ARCHETYPES)
        unknown = [n for n in names if n not in ARCHETYPES]
        if unknown:
            raise PopulationError(f"arquetipos desconocidos: {unknown}")
        if weights is None:
            p = np.full(len(names), 1.0 / len(names))
        else:
            raw = np.array([float(weights.get(n, 0.0)) for n in names])
            if raw.sum() <= 0:
                raise PopulationError("los pesos deben sumar > 0")
            if any(weights.get(n, 0.0) < 0 for n in names):
                raise PopulationError("los pesos no pueden ser negativos")
            p = raw / raw.sum()
            if set(weights) - set(names):
                raise PopulationError(
                    f"pesos para arquetipos no incluidos: "
                    f"{sorted(set(weights) - set(names))}")
        if len(names) == 1:
            p = np.array([1.0])

        rng = np.random.default_rng(seed)
        chosen = rng.choice(names, size=size, p=p)
        agents = []
        for index, archetype in enumerate(chosen):
            archetype = str(archetype)
            spec = ARCHETYPES[archetype]
            draw = {
                "area_ha": round(_uniform(rng, spec["area_ha"]), 3),
                "irrigated": bool(rng.random() <
                                  float(np.mean(spec["irrigated"]))),
                "capital_usd": round(_uniform(rng, spec["capital_usd"]), 2),
                "credit_access": round(_uniform(rng, spec["credit_access"]), 3),
                "market_access": round(_uniform(rng, spec["market_access"]), 3),
                "household_labor": int(rng.integers(spec["household_labor"][0],
                                                   spec["household_labor"][1] + 1)),
                "hired_labor": int(rng.integers(spec["hired_labor"][0],
                                                spec["hired_labor"][1] + 1)),
                "tenure": str(rng.choice(spec["tenure"])),
                "risk_aversion": round(_uniform(rng, spec["risk_aversion"]), 3),
                "info_access": round(_uniform(rng, spec["info_access"]), 3),
                "experience_years": int(rng.integers(
                    spec["experience_years"][0], spec["experience_years"][1] + 1)),
                "digital_literacy": round(_uniform(rng, spec["digital_literacy"]), 3),
                "cooperative": bool(rng.random() <
                                    float(np.mean(spec["cooperative"]))),
                "off_farm_income": round(_uniform(rng, spec["off_farm_income"]), 3),
                "department": str(rng.choice(DEPARTMENTS)),
            }
            agent_id = f"AGSV-{archetype}-{index:06d}"
            state = SG.make_record(
                "SYNTHETIC_AGRICULTURAL_STATE",
                {
                    "archetype": archetype,
                    "archetype_label": spec["label"],
                    "production_system": spec["production_system"],
                    "primary_crop": spec["primary_crop"],
                    "crops": list(spec["crops"]),
                    "area_ha": draw["area_ha"],
                    "irrigated": draw["irrigated"],
                    "capital_usd": draw["capital_usd"],
                    "credit_access": draw["credit_access"],
                    "market_access": draw["market_access"],
                    "household_labor": draw["household_labor"],
                    "hired_labor": draw["hired_labor"],
                    "tenure": draw["tenure"],
                    "risk_aversion": draw["risk_aversion"],
                    "info_access": draw["info_access"],
                    "experience_years": draw["experience_years"],
                    "digital_literacy": draw["digital_literacy"],
                    "cooperative": draw["cooperative"],
                    "off_farm_income": draw["off_farm_income"],
                    "department": draw["department"],
                    "area_type": spec["area_type"],
                    "parameter_basis": BOUNDS_BASIS,
                },
                method=("muestreo uniforme independiente dentro de rangos de "
                        "escenario; sin correlaciones empíricas"),
                assumptions=[
                    "los rangos son supuestos de simulación, no estadísticas",
                    "las variables se sortean de forma independiente",
                    "la asignación departamental es uniforme y no representa "
                    "la distribución real",
                    "no hay validación contra el CAP 2025 ni el CPV 2024",
                ],
                scenario_id=scenario_id,
                agent_id=agent_id,
            )
            agents.append({
                "agent_id": agent_id,
                "archetype": archetype,
                "seed": seed,
                "index": index,
                "state": state,
            })

        counts: dict[str, int] = {}
        for agent in agents:
            counts[agent["archetype"]] = counts.get(agent["archetype"], 0) + 1
        areas = [a["state"]["payload"]["area_ha"] for a in agents]
        result = {
            "size": size,
            "seed": seed,
            "archetypes_used": names,
            "weights": {n: float(round(p[i], 4)) for i, n in enumerate(names)},
            "counts": counts,
            "area_ha": {
                "min": round(min(areas), 3), "max": round(max(areas), 3),
                "mean": round(float(np.mean(areas)), 3),
                "note": "media de la muestra sintética, no del país",
            },
            "agents": agents,
            "reproducible": True,
            "representativeness": {
                "representative": False,
                "reason": ("no hay calibración contra el censo agropecuario; "
                           "los pesos son elección del analista"),
            },
        }
        return SG.synthetic_envelope(
            ENGINE, result=result,
            assumptions=[
                "población sintética con semilla reproducible",
                "parámetros de arquetipo definidos por AGROSV",
                "geografía departamental uniforme",
            ],
            limitations=[
                "no representa a los productores de El Salvador",
                "no se puede inferir ninguna distribución poblacional",
                "los rangos no provienen del CAP 2025 ni de encuestas",
            ],
            sources=["agrosv_scenario", "crop_parameters_catalog"],
            scenario_id=scenario_id,
            processing=[
                SG.AG.step("sorteo de arquetipos", "numpy.default_rng"),
                SG.AG.step("sorteo de dotaciones", "generate"),
                SG.AG.step("registro por capa", "make_record"),
            ],
            query={"size": size, "seed": seed},
        )


__all__ = ["AgriculturalPopulationEngine", "ARCHETYPES", "DEPARTMENTS",
           "PopulationError", "BOUNDS_BASIS"]
