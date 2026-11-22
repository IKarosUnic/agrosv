"""AGROSV Phase 8 — Subsistema F: Economía de Hogares Agrícolas.

Reutiliza directamente la base de Fase 6 (Nemotron + `AgriculturalHouseholdEngine` +
`TechnologyAdoptionEngine` + `FarmerBehaviorEngine` + `social.governance`) sin
duplicar ni reconstruir la generación de población ni de hogares.

Contiene los 5 motores del Subsistema F:
1. AgriculturalHouseholdEconomyEngine
2. AgriculturalResourceAllocationEngine
3. AgriculturalLivelihoodEngine
4. AgriculturalTechnologyEconomicsEngine
5. AgriculturalEconomicBehaviorEngine
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..social import governance as SG
from ..social.adoption import TECHNOLOGIES, TechnologyAdoptionEngine
from ..social.behavior import FarmerBehaviorEngine
from ..social.household import AgriculturalHouseholdEngine
from ..social.population import AgriculturalPopulationEngine
from . import governance as EG

ENGINE_VERSION = EG.ENGINE_VERSION


class AgriculturalHouseholdEconomyEngine:
    """Extiende HOUSEHOLD_STATE (Fase 6) con estructura económica sintética explícita."""

    engine = "agricultural_household_economy"
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.household_engine = AgriculturalHouseholdEngine()
        self.population_engine = AgriculturalPopulationEngine()

    def evaluate(
        self,
        *,
        agent: dict[str, Any] | None = None,
        seed: int = 42,
        use_nemotron: bool = True,
        production_expense_usd: float | None = None,
        agricultural_revenue_usd: float | None = None,
        non_agricultural_income_usd: float | None = None,
        consumption_usd: float | None = None,
        credit_obligation_usd: float = 0.0,
    ) -> dict[str, Any]:
        if agent is None:
            if use_nemotron:
                agent = self.population_engine.generate_from_nemotron(1, seed=seed)["result"]["agents"][0]
            else:
                agent = self.population_engine.generate(1, seed=seed)["result"]["agents"][0]

        src_profile = (agent.get("source_profile") or {}).get("profile")
        composed = self.household_engine.compose(agent, profile=src_profile, seed=seed)
        hh = composed["household"]
        state = agent["state"]["payload"]

        capital = float(state.get("capital_usd", 0.0))
        op_budget = float(hh["operating_budget_usd"])
        expense = float(production_expense_usd) if production_expense_usd is not None else op_budget
        ag_rev = float(agricultural_revenue_usd) if agricultural_revenue_usd is not None else None
        non_ag_inc = float(non_agricultural_income_usd) if non_agricultural_income_usd is not None else None

        net_ag = (ag_rev - expense) if ag_rev is not None else None
        total_income = (
            (net_ag + (non_ag_inc or 0.0))
            if net_ag is not None
            else non_ag_inc
        )
        savings_change = (
            (total_income - float(consumption_usd) - float(credit_obligation_usd))
            if total_income is not None and consumption_usd is not None
            else None
        )
        liquidity_gap = max(0.0, expense + float(credit_obligation_usd) - capital)

        payload = {
            "agent_id": agent["agent_id"],
            "nemotron_backed": bool((src_profile or {}).get("from_nemotron_dataset")),
            "nemotron_uuid": (src_profile or {}).get("uuid"),
            "household_state": hh,
            "capital_usd": round(capital, 2),
            "operating_budget_usd": round(op_budget, 2),
            "modeled_production_expense_usd": round(expense, 2),
            "agricultural_revenue_usd": round(ag_rev, 2) if ag_rev is not None else None,
            "non_agricultural_income_usd": round(non_ag_inc, 2) if non_ag_inc is not None else None,
            "consumption_usd": round(float(consumption_usd), 2) if consumption_usd is not None else None,
            "credit_obligation_usd": round(float(credit_obligation_usd), 2),
            "net_agricultural_cashflow_usd": round(net_ag, 2) if net_ag is not None else None,
            "net_savings_change_usd": round(savings_change, 2) if savings_change is not None else None,
            "liquidity_gap_usd": round(liquidity_gap, 2),
            "risk_exposure": hh["risk_exposure"],
            "synthetic": True,
        }
        record = SG.make_record(
            "SIMULATION_HISTORY",
            payload,
            method="extensión económica de Fase 8 sobre HOUSEHOLD_STATE de Fase 6 (Nemotron)",
            assumptions=[
                "el hogar y su dotación son sintéticos (no es una encuesta observada)",
                "ingresos o consumo no aportados permanecen en null",
            ],
            agent_id=agent["agent_id"],
            parent_ids=[composed["record"]["record_id"]],
        )
        return EG.economic_envelope(
            self.engine,
            result={"economy": payload, "record": record},
            sources=["nemotron_personas_sv", "agrosv_scenario"],
            assumptions=["reutiliza HOUSEHOLD_STATE de Fase 6 sin duplicar su motor"],
            limitations=["los flujos monetarios dependen de valores de escenario aportados"],
            evidence_class="synthetic_scenario",
            synthetic=True,
            query={"agent_id": agent["agent_id"], "use_nemotron": use_nemotron},
        )


class AgriculturalResourceAllocationEngine:
    """Analiza asignación de tierra, mano de obra, capital y agua bajo restricciones."""

    engine = "agricultural_resource_allocation"
    version = ENGINE_VERSION

    def allocate(
        self,
        *,
        agent: dict[str, Any],
        activities: Iterable[Mapping[str, Any]],
        objective: str = "balanced_food_security_and_margin",
        seed: int = 42,
    ) -> dict[str, Any]:
        state = agent["state"]["payload"]
        hh = AgriculturalHouseholdEngine().compose(agent, seed=seed)["household"]

        avail_land = float(state.get("area_ha", 1.0))
        avail_labor = float(hh["labor_days_total"])
        avail_capital = float(hh["operating_budget_usd"])
        has_irrigation = bool(state.get("irrigated", False))

        rem_land, rem_labor, rem_cap = avail_land, avail_labor, avail_capital
        act_list = list(activities)
        if not act_list:
            raise EG.EconomicError("se requiere al menos una actividad candidata")

        # Prioriza según objetivo (seguridad alimentaria, aversión al riesgo o margen)
        def _score(act: Mapping[str, Any]) -> float:
            margin_ha = float(act.get("expected_margin_per_ha", 0.0))
            food_weight = 1.5 if act.get("is_staple_food") else 1.0
            risk_pen = 1.0 - float(state.get("risk_aversion", 0.5)) * float(act.get("risk", 0.3))
            if objective == "profit_maximization":
                return margin_ha
            if objective == "food_security_first":
                return (10000.0 if act.get("is_staple_food") else 0.0) + margin_ha * risk_pen
            return margin_ha * food_weight * max(0.1, risk_pen)

        ranked = sorted(act_list, key=_score, reverse=True)
        allocated: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []

        for act in ranked:
            req_irr = bool(act.get("requires_irrigation", False))
            if req_irr and not has_irrigation:
                rejected.append({"activity": act.get("name"), "reason": "requiere riego no disponible"})
                continue
            max_ha = float(act.get("max_area_ha", avail_land))
            cost_ha = float(act.get("cost_per_ha", 0.0))
            lab_ha = float(act.get("labor_days_per_ha", 0.0))
            cap_limit = (rem_cap / cost_ha) if cost_ha > 0 else rem_land
            lab_limit = (rem_labor / lab_ha) if lab_ha > 0 else rem_land
            assigned_ha = max(0.0, min(rem_land, max_ha, cap_limit, lab_limit))
            if assigned_ha <= 1e-4:
                rejected.append({"activity": act.get("name"), "reason": "restricción de tierra, capital o trabajo"})
                continue
            rem_land -= assigned_ha
            rem_cap -= assigned_ha * cost_ha
            rem_labor -= assigned_ha * lab_ha
            allocated.append({
                "activity": act.get("name"),
                "allocated_ha": round(assigned_ha, 4),
                "capital_used_usd": round(assigned_ha * cost_ha, 2),
                "labor_days_used": round(assigned_ha * lab_ha, 1),
                "is_staple_food": bool(act.get("is_staple_food")),
            })

        return EG.economic_envelope(
            self.engine,
            result={
                "agent_id": agent["agent_id"],
                "objective": objective,
                "initial_resources": {
                    "land_ha": round(avail_land, 4),
                    "labor_days": round(avail_labor, 1),
                    "operating_budget_usd": round(avail_capital, 2),
                    "irrigated": has_irrigation,
                },
                "allocated": allocated,
                "unallocated_or_constrained": rejected,
                "remaining_resources": {
                    "land_ha": round(rem_land, 4),
                    "labor_days": round(rem_labor, 1),
                    "operating_budget_usd": round(rem_cap, 2),
                },
                "profit_only_assumed": False,
            },
            sources=["nemotron_personas_sv", "agrosv_scenario"],
            assumptions=[
                "los hogares ponderan seguridad alimentaria y aversión al riesgo además del margen",
            ],
            limitations=["asignación heurística sintética; no representa optimización empírica observada"],
            evidence_class="synthetic_scenario",
            synthetic=True,
            query={"agent_id": agent["agent_id"], "objective": objective},
        )


class AgriculturalLivelihoodEngine:
    """Analiza estrategias de medios de vida distinguiendo ingreso agrícola vs total."""

    engine = "agricultural_livelihood"
    version = ENGINE_VERSION

    def analyze(
        self,
        *,
        agent: dict[str, Any],
        crop_income_usd: float | None = None,
        livestock_income_usd: float | None = None,
        ag_wage_income_usd: float | None = None,
        non_ag_wage_income_usd: float | None = None,
        family_enterprise_income_usd: float | None = None,
        remittances_usd: float | None = None,
        seed: int = 42,
    ) -> dict[str, Any]:
        hh = AgriculturalHouseholdEngine().compose(agent, seed=seed)["household"]
        components = {
            "crop_production": crop_income_usd,
            "livestock": livestock_income_usd,
            "agricultural_employment": ag_wage_income_usd,
            "non_agricultural_employment": non_ag_wage_income_usd,
            "family_enterprise": family_enterprise_income_usd,
            "remittances": remittances_usd,
        }
        observed_vals = {k: float(v) for k, v in components.items() if v is not None}
        ag_total = sum(
            observed_vals.get(k, 0.0)
            for k in ("crop_production", "livestock", "agricultural_employment")
        )
        total = sum(observed_vals.values()) if observed_vals else None
        ag_share = round(ag_total / total, 4) if total and total > 0 else hh["income_shares"]["farm"]

        return EG.economic_envelope(
            self.engine,
            result={
                "agent_id": agent["agent_id"],
                "synthetic_household_shares": hh["income_shares"],
                "scenario_monetary_components": observed_vals or None,
                "agricultural_income_usd": round(ag_total, 2) if observed_vals else None,
                "total_household_income_usd": round(total, 2) if total is not None else None,
                "agricultural_share_of_total": ag_share,
                "diversification_count": len(observed_vals) if observed_vals else sum(
                    1 for v in hh["income_shares"].values() if v > 0
                ),
            },
            sources=["nemotron_personas_sv", "agrosv_scenario"],
            assumptions=["sin valores monetarios aportados solo se publican proporciones sintéticas"],
            limitations=["el ingreso agrícola se separa explícitamente del ingreso total del hogar"],
            evidence_class="synthetic_scenario",
            synthetic=True,
            query={"agent_id": agent["agent_id"]},
        )


class AgriculturalTechnologyEconomicsEngine:
    """Evalúa viabilidad económica y barreras de adopción reutilizando Fase 6."""

    engine = "agricultural_technology_economics"
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.adoption_engine = TechnologyAdoptionEngine()

    def evaluate(
        self,
        *,
        agent: dict[str, Any],
        technology_id: str,
        capex_usd: float | None = None,
        annual_maintenance_usd: float = 0.0,
        expected_annual_net_benefit_usd: float | None = None,
        useful_life_years: int = 5,
    ) -> dict[str, Any]:
        if technology_id not in TECHNOLOGIES:
            raise EG.EconomicError(f"tecnología desconocida: {technology_id!r}")
        adoption_res = self.adoption_engine.evaluate(agent, technology_id)["result"]
        feasible = adoption_res["decision"] != "not_feasible"

        financial = None
        if capex_usd is not None and expected_annual_net_benefit_usd is not None:
            net_yr = float(expected_annual_net_benefit_usd) - float(annual_maintenance_usd)
            payback = round(capex_usd / net_yr, 2) if net_yr > 0 else None
            total_net = net_yr * useful_life_years - capex_usd
            capital = float(agent["state"]["payload"].get("capital_usd", 0.0))
            financial = {
                "capex_usd": round(capex_usd, 2),
                "annual_maintenance_usd": round(annual_maintenance_usd, 2),
                "net_annual_benefit_usd": round(net_yr, 2),
                "payback_years": payback,
                "net_lifecycle_gain_usd": round(total_net, 2),
                "capital_shortfall_usd": round(max(0.0, capex_usd - capital), 2),
                "improves_profitability": total_net > 0 and feasible,
            }

        return EG.economic_envelope(
            self.engine,
            result={
                "agent_id": agent["agent_id"],
                "technology_id": technology_id,
                "phase6_adoption_evaluation": adoption_res,
                "financial_evaluation": financial,
                "automatic_profit_improvement_assumed": False,
            },
            sources=["agrosv_scenario"],
            assumptions=["reutiliza barreras duras (agua/superficie/capital) de TechnologyAdoptionEngine"],
            limitations=["la adopción tecnológica puede empeorar el resultado si la inversión supera los beneficios"],
            evidence_class="synthetic_scenario",
            synthetic=True,
            query={"agent_id": agent["agent_id"], "technology_id": technology_id},
        )


class AgriculturalEconomicBehaviorEngine:
    """Reutiliza FarmerBehaviorEngine (Fase 6) para decisiones económicas explícitas."""

    engine = "agricultural_economic_behavior"
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.behavior = FarmerBehaviorEngine()

    def decide(
        self,
        *,
        agent: dict[str, Any],
        decision_domain: str,
        options: Iterable[Mapping[str, Any]],
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        valid_domains = (
            "crop_selection",
            "investment",
            "input_purchase",
            "market_selection",
            "savings",
            "borrowing",
            "risk_management",
            "technology_adoption",
            "diversification",
        )
        if decision_domain not in valid_domains:
            raise EG.EconomicError(f"decision_domain inválido: {decision_domain!r}; use {valid_domains}")

        state = agent["state"]["payload"]
        chosen = self.behavior.choose(list(options), state, context=dict(context or {}))
        return EG.economic_envelope(
            self.engine,
            result={
                "agent_id": agent["agent_id"],
                "decision_domain": decision_domain,
                "behavior_output": chosen,
                "represents_observed_farmer_behavior": False,
            },
            sources=["nemotron_personas_sv", "agrosv_scenario"],
            assumptions=["decisión MAUT determinista sobre preferencias sintéticas del agente"],
            limitations=["no representa comportamiento observado empíricamente de agricultores salvadoreños"],
            evidence_class="synthetic_scenario",
            synthetic=True,
            query={"agent_id": agent["agent_id"], "decision_domain": decision_domain},
        )


__all__ = [
    "AgriculturalEconomicBehaviorEngine",
    "AgriculturalHouseholdEconomyEngine",
    "AgriculturalLivelihoodEngine",
    "AgriculturalResourceAllocationEngine",
    "AgriculturalTechnologyEconomicsEngine",
]
