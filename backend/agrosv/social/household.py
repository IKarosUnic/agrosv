"""AGROSV — AgriculturalHouseholdEngine (§5.4).

El hogar es una unidad productiva y de consumo sintética. No reproduce
estadísticas de hogares: no hay ingresos en dólares porque no hay precios ni
salarios verificados en el repositorio. Se modelan **proporciones** y un
presupuesto operativo derivado del capital sintético.

Atributos sensibles: solo se conserva `household_type` y tamaño; no se
propaga sexo, religión, identidad ni dirección.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import governance as SG

ENGINE = "agricultural_household"
ENGINE_VERSION = SG.ENGINE_VERSION

SIZE_BY_TYPE = {
    "unipersonal": (1, 1),
    "nuclear": (3, 5),
    "monoparental": (2, 4),
    "extendida": (5, 8),
}


class HouseholdError(ValueError):
    pass


class AgriculturalHouseholdEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def compose(self, agent: dict[str, Any], *, profile: dict[str, Any] | None
                = None, seed: int = 42) -> dict[str, Any]:
        if "state" not in agent:
            raise HouseholdError("el agente no tiene estado agrícola sintético")
        state = agent["state"]["payload"]
        index = int(agent.get("index", 0))
        rng = np.random.default_rng(seed * 7_919 + index)
        household_type = (profile or {}).get("household_type")
        if household_type not in SIZE_BY_TYPE:
            household_type = str(rng.choice(list(SIZE_BY_TYPE),
                                            p=[0.08, 0.58, 0.14, 0.20]))
        lo, hi = SIZE_BY_TYPE[household_type]
        size = int(rng.integers(lo, hi + 1))
        if household_type == "unipersonal":
            adults, children = 1, 0
        elif household_type == "monoparental":
            adults = 1
            children = max(0, size - adults)
        else:
            adults = int(min(size, rng.integers(2, 4)))
            children = max(0, size - adults)
        if adults + children != size:
            raise HouseholdError("composición inconsistente")

        off_farm = float(state.get("off_farm_income", 0.0))
        availability = max(0.2, 1.0 - 0.6 * off_farm)
        labor_days = int(round(adults * 300 * availability))
        hired = int(state.get("hired_labor", 0))
        total_labor_days = labor_days + int(round(hired * 250 * 0.8))
        consumption_units = round(adults + 0.5 * children, 2)
        capital = float(state.get("capital_usd", 0.0))
        operating_share = float(rng.uniform(0.3, 0.7))
        operating_budget = round(capital * operating_share, 2)

        farm_share = max(0.1, 1.0 - off_farm - 0.1 * float(
            state.get("cooperative", False)))
        remittance = float(rng.uniform(0.0, 0.15)) if rng.random() < 0.25 else 0.0
        shares = {
            "farm": farm_share,
            "off_farm": off_farm,
            "remittances": remittance,
            "cooperative": 0.10 if state.get("cooperative") else 0.0,
        }
        total = sum(shares.values())
        if total <= 0:
            raise HouseholdError("no hay fuentes de ingreso")
        shares = {k: round(v / total, 3) for k, v in shares.items()}

        payload = {
            "household_type": household_type,
            "size": size,
            "adults": adults,
            "children": children,
            "consumption_units": consumption_units,
            "labor_days_household": labor_days,
            "labor_days_hired": int(round(hired * 250 * 0.8)),
            "labor_days_total": total_labor_days,
            "labor_availability_factor": round(availability, 3),
            "operating_budget_usd": operating_budget,
            "operating_budget_share_of_capital": round(operating_share, 3),
            "income_shares": shares,
            "risk_exposure": {
                "single_crop": len(state.get("crops", [])) <= 1,
                "rainfed": not state.get("irrigated", False),
                "low_capital_buffer": capital < 1000,
            },
            "adaptation_options": [
                option for option, present in (
                    ("off_farm_labor", shares["off_farm"] >= 0.2),
                    ("cooperative_support", state.get("cooperative", False)),
                    ("savings", capital >= 1000),
                    ("irrigation", state.get("irrigated", False)),
                    ("diversification", len(state.get("crops", [])) > 1),
                ) if present
            ],
            "sensitive_attributes_omitted": ["sexo", "religión", "identidad",
                                             "dirección exacta"],
            "note": ("proporciones y presupuesto sintéticos; no son ingresos "
                     "ni gastos observados"),
        }
        record = SG.make_record(
            "HOUSEHOLD_STATE", payload,
            method=("composición a partir de tipo de hogar y dotaciones "
                    "sintéticas; sorteo con semilla del agente"),
            assumptions=[
                "el tamaño del hogar es sintético",
                "la disponibilidad de trabajo es una proporción, no una "
                "encuesta de uso del tiempo",
                "el presupuesto operativo es una fracción del capital "
                "sintético, no un ingreso",
                "no hay precios ni salarios observados",
            ],
            agent_id=agent["agent_id"],
            parent_ids=[agent["state"].get("record_id")],
            validation_status="not_validated")
        consistency = self.consistency(payload)
        return {
            "household": payload,
            "record": record,
            "consistency": consistency,
            "synthetic": True,
        }

    def consistency(self, household: dict[str, Any]) -> dict[str, Any]:
        checks = {
            "composition_sums": household["adults"] + household["children"]
            == household["size"],
            "labor_non_negative": household["labor_days_total"] >= 0,
            "budget_non_negative": household["operating_budget_usd"] >= 0,
            "income_shares_sum_to_one": abs(
                sum(household["income_shares"].values()) - 1.0) <= 0.01,
            "children_need_adult": household["children"] == 0 or
            household["adults"] >= 1,
        }
        return {"valid": all(checks.values()), "checks": checks,
                "note": ("consistencia interna del registro sintético; no es "
                         "validación empírica")}


__all__ = ["AgriculturalHouseholdEngine", "HouseholdError", "SIZE_BY_TYPE"]
