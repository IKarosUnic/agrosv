"""AGROSV Phase 8 — Economía Agrícola, Inteligencia de Producción, Mercados y Cadena de Valor.

Siete subsistemas interoperables (42 motores):
- A. Producción Agrícola          `production` (6 motores)
- B. Costos Agrícolas             `costs` (7 motores)
- C. Mercados y Precios           `markets` (6 motores)
- D. Rentabilidad y Riesgo        `profitability` (7 motores)
- E. Cadena y Logística           `supply_chain` (6 motores)
- F. Economía de Hogares          `household_econ` (5 motores, reutiliza Nemotron Fase 6)
- G. Inteligencia Integrada       `integration` (5 motores)
"""
from __future__ import annotations

import importlib

__all__ = [
    "governance",
    "production",
    "costs",
    "markets",
    "profitability",
    "supply_chain",
    "household_econ",
    "integration",
    "api",
    "get_engine",
    "list_engines",
]

_ENGINES: dict[str, tuple[str, str]] = {
    # Subsistema A
    "agricultural_production": ("production", "AgriculturalProductionEngine"),
    "crop_yield_analysis": ("production", "CropYieldAnalysisEngine"),
    "production_system": ("production", "ProductionSystemEngine"),
    "agricultural_productivity": ("production", "AgriculturalProductivityEngine"),
    "harvest_estimation": ("production", "HarvestEstimationEngine"),
    "production_statistics": ("production", "ProductionStatisticsEngine"),
    # Subsistema B
    "agricultural_cost": ("costs", "AgriculturalCostEngine"),
    "input_cost": ("costs", "InputCostEngine"),
    "labor_cost": ("costs", "LaborCostEngine"),
    "irrigation_cost": ("costs", "IrrigationCostEngine"),
    "machinery_equipment_cost": ("costs", "MachineryAndEquipmentCostEngine"),
    "post_harvest_cost": ("costs", "PostHarvestCostEngine"),
    "production_budget": ("costs", "ProductionBudgetEngine"),
    # Subsistema C
    "agricultural_market": ("markets", "AgriculturalMarketEngine"),
    "agricultural_price": ("markets", "AgriculturalPriceEngine"),
    "price_history": ("markets", "PriceHistoryEngine"),
    "market_supply_demand": ("markets", "MarketSupplyDemandEngine"),
    "market_comparison": ("markets", "MarketComparisonEngine"),
    "market_opportunity": ("markets", "MarketOpportunityEngine"),
    # Subsistema D
    "agricultural_profitability": ("profitability", "AgriculturalProfitabilityEngine"),
    "revenue_analysis": ("profitability", "RevenueAnalysisEngine"),
    "break_even_analysis": ("profitability", "BreakEvenAnalysisEngine"),
    "gross_margin": ("profitability", "GrossMarginEngine"),
    "net_margin": ("profitability", "NetMarginEngine"),
    "agricultural_investment_analysis": ("profitability", "AgriculturalInvestmentAnalysisEngine"),
    "agricultural_economic_risk": ("profitability", "AgriculturalEconomicRiskEngine"),
    # Subsistema E
    "agricultural_supply_chain": ("supply_chain", "AgriculturalSupplyChainEngine"),
    "agricultural_logistics": ("supply_chain", "AgriculturalLogisticsEngine"),
    "market_access": ("supply_chain", "MarketAccessEngine"),
    "storage_post_harvest": ("supply_chain", "StorageAndPostHarvestEngine"),
    "agricultural_distribution": ("supply_chain", "AgriculturalDistributionEngine"),
    "agricultural_value_chain": ("supply_chain", "AgriculturalValueChainEngine"),
    # Subsistema F
    "agricultural_household_economy": ("household_econ", "AgriculturalHouseholdEconomyEngine"),
    "agricultural_resource_allocation": ("household_econ", "AgriculturalResourceAllocationEngine"),
    "agricultural_livelihood": ("household_econ", "AgriculturalLivelihoodEngine"),
    "agricultural_technology_economics": ("household_econ", "AgriculturalTechnologyEconomicsEngine"),
    "agricultural_economic_behavior": ("household_econ", "AgriculturalEconomicBehaviorEngine"),
    # Subsistema G
    "agricultural_economic_integration": ("integration", "AgriculturalEconomicIntegrationEngine"),
    "agricultural_economic_scenario": ("integration", "AgriculturalEconomicScenarioEngine"),
    "agricultural_decision_support": ("integration", "AgriculturalDecisionSupportEngine"),
    "agricultural_economic_analysis": ("integration", "AgriculturalEconomicAnalysisEngine"),
    "agricultural_economic_reporting": ("integration", "AgriculturalEconomicReportingEngine"),
}


def list_engines() -> list[str]:
    return sorted(_ENGINES)


def get_engine(name: str):
    key = name.strip().lower()
    if key not in _ENGINES:
        raise KeyError(f"motor económico desconocido: {name}; disponibles {sorted(_ENGINES)}")
    module_name, class_name = _ENGINES[key]
    module = importlib.import_module(f".{module_name}", __name__)
    return getattr(module, class_name)()
