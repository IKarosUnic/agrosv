"""AGROSV Phase 8 — Subsistema B: Inteligencia de Costos Agrícolas.

Contiene los 7 motores del Subsistema B:
1. AgriculturalCostEngine
2. InputCostEngine
3. LaborCostEngine
4. IrrigationCostEngine
5. MachineryAndEquipmentCostEngine
6. PostHarvestCostEngine
7. ProductionBudgetEngine
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

from ..agriculture.catalog import CROPS
from ..agriculture.water_nutrient import CropWaterNutrientEngine, WaterNutrientError
from . import governance as EG

ENGINE_VERSION = EG.ENGINE_VERSION

INPUT_CATEGORIES = (
    "seeds",
    "fertilizers",
    "soil_amendments",
    "pesticides",
    "herbicides",
    "fungicides",
    "biological_control",
    "irrigation_materials",
    "fuel",
    "packaging",
    "agricultural_services",
)

PESTICIDE_CATEGORIES = {"pesticides", "herbicides", "fungicides"}
PRICE_TYPES = ("retail", "wholesale", "quoted", "official_reference", "historical")

LABOR_ACTIVITIES = (
    "land_preparation",
    "planting",
    "irrigation",
    "fertilization",
    "weed_control",
    "pest_management",
    "harvesting",
    "sorting",
    "packaging",
    "transportation_prep",
)

LABOR_MODES = ("daily", "hourly", "seasonal", "family_unpaid", "contract")
IRRIGATION_SYSTEMS = ("manual", "surface", "sprinkler", "drip", "other")
BUDGET_TYPES = ("observed", "reference", "scenario")

COST_NATURES = ("variable", "fixed")
COST_ALLOCATIONS = ("direct", "indirect")
COST_CLASSES = ("operating", "investment", "opportunity")


class AgriculturalCostEngine:
    """Modelo configurable de costos agrícolas con desglose y conversión de unidades."""

    engine = "agricultural_cost"
    version = ENGINE_VERSION

    def aggregate(
        self,
        *,
        items: Iterable[Mapping[str, Any]],
        area_value: float = 1.0,
        area_unit: str = "ha",
        production_value: float | None = None,
        production_unit: str = "t",
        currency: str = "USD",
    ) -> dict[str, Any]:
        area_ha = EG.convert_area(area_value, area_unit, "ha")
        area_mz = EG.convert_area(area_ha, "ha", "mz")
        if area_ha <= 0:
            raise EG.EconomicError("el área debe ser > 0")

        prod_kg: float | None = None
        if production_value is not None:
            if float(production_value) < 0:
                raise EG.EconomicError("production_value debe ser >= 0")
            prod_kg = EG.convert_mass(float(production_value), production_unit, "kg")

        totals = {
            "total": 0.0,
            "by_nature": {"variable": 0.0, "fixed": 0.0},
            "by_allocation": {"direct": 0.0, "indirect": 0.0},
            "by_class": {"operating": 0.0, "investment": 0.0, "opportunity": 0.0},
            "by_category": {},
        }
        parsed_items: list[dict[str, Any]] = []

        for idx, raw in enumerate(items):
            item_cur = str(raw.get("currency") or currency).upper()
            if item_cur != currency.upper():
                raise EG.EconomicError(
                    f"ítem {idx}: moneda incompatible {item_cur!r} != {currency!r}; "
                    "convierta explícitamente antes de agregar"
                )
            nature = str(raw.get("nature") or "variable").lower()
            alloc = str(raw.get("allocation") or "direct").lower()
            c_class = str(raw.get("cost_class") or "operating").lower()
            if nature not in COST_NATURES:
                raise EG.EconomicError(f"ítem {idx}: nature inválido {nature!r}")
            if alloc not in COST_ALLOCATIONS:
                raise EG.EconomicError(f"ítem {idx}: allocation inválido {alloc!r}")
            if c_class not in COST_CLASSES:
                raise EG.EconomicError(f"ítem {idx}: cost_class inválido {c_class!r}")

            amount = float(raw.get("amount", 0.0))
            if amount < 0:
                raise EG.EconomicError(f"ítem {idx}: el monto no puede ser negativo")
            basis = str(raw.get("per") or "cycle").lower()
            if basis == "cycle":
                cycle_amount = amount
            elif basis in {"ha", "mz"}:
                basis_ha = EG.convert_area(1.0, basis, "ha")
                cycle_amount = amount * (area_ha / basis_ha)
            else:
                raise EG.EconomicError(f"ítem {idx}: base 'per' inválida {basis!r}; use cycle/ha/mz")

            cat = str(raw.get("category") or "other")
            totals["total"] += cycle_amount
            totals["by_nature"][nature] += cycle_amount
            totals["by_allocation"][alloc] += cycle_amount
            totals["by_class"][c_class] += cycle_amount
            totals["by_category"][cat] = totals["by_category"].get(cat, 0.0) + cycle_amount

            parsed_items.append({
                "name": str(raw.get("name") or cat),
                "category": cat,
                "nature": nature,
                "allocation": alloc,
                "cost_class": c_class,
                "cycle_amount": round(cycle_amount, 2),
                "source": raw.get("source") or "user_supplied",
            })

        total = totals["total"]
        per_unit: dict[str, float | None] = {
            "per_cycle": round(total, 2),
            "per_ha": round(total / area_ha, 2),
            "per_mz": round(total / area_mz, 2),
            "per_kg": round(total / prod_kg, 4) if prod_kg and prod_kg > 0 else None,
            "per_qq": (
                round(total / EG.convert_mass(prod_kg, "kg", "qq"), 2)
                if prod_kg and prod_kg > 0
                else None
            ),
            "per_t": (
                round(total / EG.convert_mass(prod_kg, "kg", "t"), 2)
                if prod_kg and prod_kg > 0
                else None
            ),
        }
        drivers = sorted(
            (
                {
                    "category": k,
                    "amount": round(v, 2),
                    "share": round(v / total, 4) if total > 0 else 0.0,
                }
                for k, v in totals["by_category"].items()
            ),
            key=lambda d: d["amount"],
            reverse=True,
        )

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "area_ha": round(area_ha, 4),
                "area_mz": round(area_mz, 4),
                "production_kg": round(prod_kg, 2) if prod_kg is not None else None,
                "totals": {
                    "total": round(total, 2),
                    "by_nature": {k: round(v, 2) for k, v in totals["by_nature"].items()},
                    "by_allocation": {k: round(v, 2) for k, v in totals["by_allocation"].items()},
                    "by_class": {k: round(v, 2) for k, v in totals["by_class"].items()},
                },
                "unit_costs": per_unit,
                "cost_drivers": drivers,
                "items": parsed_items,
            },
            sources=["agrosv_scenario"],
            assumptions=["1 mz = 0.70 ha; 1 qq = 46 kg; 1 t = 1000 kg"],
            limitations=["los costos reflejan únicamente los ítems declarados"],
            evidence_class="model_estimate",
            query={"n_items": len(parsed_items), "area_ha": area_ha},
        )


class InputCostEngine:
    """Gestiona insumos agrícolas, trazabilidad de cotizaciones y regla fitosanitaria."""

    engine = "input_cost"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        inputs: Iterable[Mapping[str, Any]],
        reference_date: str | None = None,
        stale_after_days: int = 90,
        currency: str = "USD",
    ) -> dict[str, Any]:
        ref_d = date.fromisoformat(
            EG.check_iso_date(reference_date, "reference_date")
            if reference_date
            else date.today().isoformat()
        )
        records: list[dict[str, Any]] = []
        warnings: list[str] = []
        total_cost = 0.0
        by_category: dict[str, float] = {}

        for idx, item in enumerate(inputs):
            cat = str(item.get("category") or "").strip().lower()
            if cat not in INPUT_CATEGORIES:
                raise EG.EconomicError(
                    f"insumo {idx}: categoría inválida {cat!r}; use {INPUT_CATEGORIES}"
                )
            p_type = str(item.get("price_type") or "").strip().lower()
            if p_type not in PRICE_TYPES:
                raise EG.EconomicError(
                    f"insumo {idx}: price_type inválido {p_type!r}; use {PRICE_TYPES}"
                )
            obs_str = EG.check_iso_date(str(item.get("observation_date") or ""), "observation_date")
            obs_d = date.fromisoformat(obs_str)
            age_days = (ref_d - obs_d).days
            is_outdated = age_days > stale_after_days or p_type == "historical"
            if is_outdated:
                warnings.append(
                    f"{item.get('product')}: precio con antigüedad de {age_days} días ({p_type}); no presentar como actual"
                )

            item_cur = str(item.get("currency") or currency).upper()
            if item_cur != currency.upper():
                raise EG.EconomicError(f"insumo {idx}: moneda {item_cur!r} != {currency!r}")

            price = float(item.get("price", -1))
            qty = float(item.get("quantity", 1.0))
            if price < 0 or qty < 0:
                raise EG.EconomicError(f"insumo {idx}: price y quantity deben ser >= 0")

            if cat in PESTICIDE_CATEGORIES:
                for req in ("crop_id", "target_organism", "registration_status"):
                    if not item.get(req):
                        raise EG.EconomicError(
                            f"insumo {item.get('product')!r} ({cat}): falta '{req}' "
                            "requerido por normativa salvadoreña y etiqueta"
                        )

            line_total = round(price * qty, 2)
            total_cost += line_total
            by_category[cat] = by_category.get(cat, 0.0) + line_total

            rec = EG.make_economic_record(
                product_or_activity=f"{cat}:{item.get('product')}",
                geography=str(item.get("geographic_location") or "El Salvador"),
                observation_date=obs_str,
                publication_date=item.get("publication_date"),
                reference_period=obs_str[:7],
                currency=item_cur,
                unit=str(item.get("unit") or "unidad"),
                source=str(item.get("source") or "user_supplied"),
                methodology=f"registro de precio de insumo ({p_type})",
                verification_status=str(item.get("verification_status") or "PARSED"),
                license_name=str(item.get("license") or "user_declared"),
                evidence_class=(
                    "commercial_quotation"
                    if p_type in {"retail", "wholesale", "quoted"}
                    else "institutional_reference"
                ),
                value=price,
                extra={
                    "brand": item.get("brand"),
                    "package_size": item.get("package_size"),
                    "vendor": item.get("vendor"),
                    "price_type": p_type,
                    "quantity": qty,
                    "line_total": line_total,
                    "age_days": age_days,
                    "is_outdated": is_outdated,
                    "label_compliance_declared": cat in PESTICIDE_CATEGORIES,
                },
            )
            records.append(rec)

        return EG.economic_envelope(
            self.engine,
            result={
                "count": len(records),
                "currency": currency.upper(),
                "total_input_cost": round(total_cost, 2),
                "by_category": {k: round(v, 2) for k, v in by_category.items()},
                "outdated_warnings": warnings,
                "records": records,
            },
            sources=["mag_anuarios_y_costos"],
            assumptions=["cada insumo declara fuente, fecha de observación y tipo de precio"],
            limitations=[
                "no existe serie nacional automática de precios actuales de agroservicios",
                "los precios marcados is_outdated no deben presentarse como vigentes",
            ],
            evidence_class="commercial_quotation",
            query={"n_inputs": len(records), "reference_date": ref_d.isoformat()},
        )


class LaborCostEngine:
    """Evalúa mano de obra agrícola separando trabajo remunerado y familiar no pagado."""

    engine = "labor_cost"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        entries: Iterable[Mapping[str, Any]],
        family_labor_valuation_method: str = "opportunity_shadow_wage",
        currency: str = "USD",
    ) -> dict[str, Any]:
        paid_total = 0.0
        family_imputed_total = 0.0
        total_days = 0.0
        by_activity: dict[str, dict[str, float]] = {}
        parsed: list[dict[str, Any]] = []

        for idx, item in enumerate(entries):
            act = str(item.get("activity") or "").strip().lower()
            if act not in LABOR_ACTIVITIES:
                raise EG.EconomicError(
                    f"mano de obra {idx}: actividad inválida {act!r}; use {LABOR_ACTIVITIES}"
                )
            mode = str(item.get("mode") or "daily").strip().lower()
            if mode not in LABOR_MODES:
                raise EG.EconomicError(
                    f"mano de obra {idx}: modo inválido {mode!r}; use {LABOR_MODES}"
                )
            qty = float(item.get("quantity", 0.0))
            rate = float(item.get("rate", 0.0))
            if qty < 0 or rate < 0:
                raise EG.EconomicError(f"mano de obra {idx}: quantity y rate deben ser >= 0")
            if rate > 0 and not item.get("wage_reference"):
                raise EG.EconomicError(
                    f"mano de obra {idx} ({act}): debe declarar 'wage_reference' con fuente y fecha"
                )
            cost = round(qty * rate, 2)
            days_eq = qty / 8.0 if mode == "hourly" else qty
            total_days += days_eq

            is_family = mode == "family_unpaid"
            if is_family:
                family_imputed_total += cost
            else:
                paid_total += cost

            act_bucket = by_activity.setdefault(act, {"paid": 0.0, "family_imputed": 0.0, "days": 0.0})
            act_bucket["paid" if not is_family else "family_imputed"] += cost
            act_bucket["days"] += days_eq

            parsed.append({
                "activity": act,
                "mode": mode,
                "quantity": qty,
                "rate": rate,
                "currency": currency.upper(),
                "is_paid": not is_family,
                "cost": cost,
                "wage_reference": item.get("wage_reference"),
                "wage_date": item.get("wage_date"),
            })

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "total_labor_days_eq": round(total_days, 2),
                "paid_labor_cost": round(paid_total, 2),
                "unpaid_family_labor_imputed": round(family_imputed_total, 2),
                "total_economic_labor_cost": round(paid_total + family_imputed_total, 2),
                "family_labor_valuation_method": family_labor_valuation_method,
                "by_activity": {
                    k: {kk: round(vv, 2) for kk, vv in v.items()}
                    for k, v in by_activity.items()
                },
                "entries": parsed,
            },
            sources=["agrosv_scenario"],
            assumptions=[
                "jornada estándar de 8 horas cuando el modo es hourly",
                f"mano de obra familiar no pagada valorada mediante '{family_labor_valuation_method}'",
            ],
            limitations=[
                "no existe tabla oficial automatizada de jornales municipales en el repositorio",
            ],
            evidence_class="model_estimate",
            query={"n_entries": len(parsed)},
        )


class IrrigationCostEngine:
    """Evalúa costos de riego integrando requerimientos hídricos de Fase 6."""

    engine = "irrigation_cost"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        system_type: str,
        area_ha: float,
        water_required_mm: float | None = None,
        crop_id: str | None = None,
        planting_date: str | None = None,
        awc_mm_per_m: float | None = None,
        root_depth_cm: float | None = None,
        allow_reference_kc: bool = False,
        energy_cost_per_m3: float = 0.0,
        water_tariff_per_m3: float = 0.0,
        maintenance_per_cycle: float = 0.0,
        capex_usd: float = 0.0,
        useful_life_cycles: int = 10,
        water_access_verified: bool = False,
        currency: str = "USD",
    ) -> dict[str, Any]:
        sys_t = str(system_type).strip().lower()
        if sys_t not in IRRIGATION_SYSTEMS:
            raise EG.EconomicError(
                f"sistema de riego inválido: {system_type!r}; use {IRRIGATION_SYSTEMS}"
            )
        if area_ha <= 0 or useful_life_cycles <= 0:
            raise EG.EconomicError("area_ha y useful_life_cycles deben ser > 0")

        req_mm = water_required_mm
        water_source = "user_supplied"
        if req_mm is None and crop_id and planting_date and awc_mm_per_m and root_depth_cm:
            if crop_id.strip().lower() not in CROPS:
                raise EG.EconomicError(f"cultivo desconocido: {crop_id!r}")
            try:
                wb = CropWaterNutrientEngine().water_balance(
                    crop_id=crop_id,
                    planting_date=planting_date,
                    awc_mm_per_m=awc_mm_per_m,
                    root_depth_cm=root_depth_cm,
                    allow_reference_kc=allow_reference_kc,
                )
                req_mm = float(wb["result"].get("irrigation_demand_mm_total", 0.0))
                water_source = "agrosv_fao56_water_balance"
            except WaterNutrientError as exc:
                req_mm = None
                water_source = f"unavailable: {exc}"

        if req_mm is None:
            return EG.economic_envelope(
                self.engine,
                result={
                    "available": False,
                    "system_type": sys_t,
                    "water_access_verified": water_access_verified,
                    "reason": "falta water_required_mm o entradas de suelo/cultivo para balance hídrico",
                },
                sources=["crop_parameters_catalog"],
                assumptions=["no se estima costo de bombeo sin demanda hídrica"],
                limitations=["cercanía a un río o cuerpo de agua no equivale a acceso legal ni económico al riego"],
                evidence_class="model_estimate",
                query={"system_type": sys_t, "area_ha": area_ha},
            )

        # 1 mm sobre 1 ha = 10 m³
        efficiency = {"manual": 0.55, "surface": 0.60, "sprinkler": 0.75, "drip": 0.90, "other": 0.70}[sys_t]
        net_m3 = float(req_mm) * 10.0 * float(area_ha)
        gross_m3 = net_m3 / efficiency
        pumping_cost = gross_m3 * float(energy_cost_per_m3)
        tariff_cost = gross_m3 * float(water_tariff_per_m3)
        depreciation_cycle = float(capex_usd) / float(useful_life_cycles)
        total_cycle = pumping_cost + tariff_cost + float(maintenance_per_cycle) + depreciation_cycle

        return EG.economic_envelope(
            self.engine,
            result={
                "available": True,
                "currency": currency.upper(),
                "system_type": sys_t,
                "assumed_application_efficiency": efficiency,
                "area_ha": round(area_ha, 4),
                "water_required_mm": round(float(req_mm), 2),
                "water_demand_source": water_source,
                "net_water_m3": round(net_m3, 2),
                "gross_water_m3": round(gross_m3, 2),
                "costs": {
                    "energy_pumping": round(pumping_cost, 2),
                    "water_tariff": round(tariff_cost, 2),
                    "maintenance": round(float(maintenance_per_cycle), 2),
                    "depreciation_per_cycle": round(depreciation_cycle, 2),
                    "total_per_cycle": round(total_cycle, 2),
                    "cost_per_m3_gross": round(total_cycle / gross_m3, 4) if gross_m3 > 0 else None,
                },
                "water_access_verified": water_access_verified,
            },
            sources=["crop_parameters_catalog"],
            assumptions=[
                f"eficiencia de aplicación asumida para {sys_t}: {efficiency}",
                "1 mm en 1 ha = 10 m³; depreciación lineal por ciclos útiles",
            ],
            limitations=[
                "proximidad geográfica a cauces de Fase 5 no garantiza concesión ni acceso físico/económico al agua",
            ],
            evidence_class="model_estimate",
            query={"system_type": sys_t, "area_ha": area_ha, "water_required_mm": req_mm},
        )


class MachineryAndEquipmentCostEngine:
    """Compara propiedad, alquiler y uso compartido de maquinaria agrícola."""

    engine = "machinery_equipment_cost"
    version = ENGINE_VERSION

    def compare_models(
        self,
        *,
        hours_per_cycle: float,
        purchase_price: float | None = None,
        salvage_value: float = 0.0,
        useful_life_hours: float | None = None,
        annual_maintenance: float = 0.0,
        cycles_per_year: float = 1.0,
        fuel_cost_per_hour: float = 0.0,
        operator_cost_per_hour: float = 0.0,
        rental_rate_per_hour: float | None = None,
        shared_members: int = 1,
        annual_financing_interest: float = 0.0,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if hours_per_cycle <= 0:
            raise EG.EconomicError("hours_per_cycle debe ser > 0")
        if shared_members <= 0:
            raise EG.EconomicError("shared_members debe ser >= 1")

        ownership = None
        if purchase_price is not None and useful_life_hours and useful_life_hours > 0:
            depreciation_hr = max(0.0, purchase_price - salvage_value) / useful_life_hours
            maint_cycle = annual_maintenance / max(1.0, cycles_per_year)
            fin_cycle = (purchase_price * annual_financing_interest) / max(1.0, cycles_per_year)
            var_hr = fuel_cost_per_hour + operator_cost_per_hour
            total_own = (depreciation_hr + var_hr) * hours_per_cycle + maint_cycle + fin_cycle
            ownership = {
                "depreciation_per_hour": round(depreciation_hr, 3),
                "variable_cost_per_hour": round(var_hr, 3),
                "maintenance_per_cycle": round(maint_cycle, 2),
                "financing_per_cycle": round(fin_cycle, 2),
                "total_per_cycle": round(total_own, 2),
                "shared_per_member_cycle": round(total_own / shared_members, 2),
            }

        rental = None
        if rental_rate_per_hour is not None:
            total_rent = rental_rate_per_hour * hours_per_cycle
            rental = {
                "rental_rate_per_hour": round(float(rental_rate_per_hour), 2),
                "total_per_cycle": round(total_rent, 2),
            }

        cheaper = None
        if ownership and rental:
            cheaper = (
                "rental"
                if rental["total_per_cycle"] < ownership["total_per_cycle"]
                else "ownership"
            )

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "hours_per_cycle": hours_per_cycle,
                "ownership": ownership,
                "rental": rental,
                "shared_members": shared_members,
                "cheaper_option_for_cycle": cheaper,
                "smallholder_access_note": (
                    "la propiedad de maquinaria suele ser inaccesible para pequeños "
                    "productores por restricción de capital y escala"
                ),
            },
            sources=["agrosv_scenario"],
            assumptions=["depreciación lineal: (compra - rescate) / vida útil en horas"],
            limitations=["requiere cotizaciones reales de compra o alquiler; no asume disponibilidad local"],
            evidence_class="model_estimate",
            query={"hours_per_cycle": hours_per_cycle, "shared_members": shared_members},
        )


class PostHarvestCostEngine:
    """Evalúa costos poscosecha y pérdidas separándolas de pérdidas en campo."""

    engine = "post_harvest_cost"
    version = ENGINE_VERSION

    def evaluate(
        self,
        *,
        harvested_quantity_t: float,
        handling_cost_per_t: float = 0.0,
        cleaning_sorting_per_t: float = 0.0,
        drying_per_t: float = 0.0,
        processing_per_t: float = 0.0,
        packaging_per_t: float = 0.0,
        storage_per_t: float = 0.0,
        refrigeration_per_t: float = 0.0,
        transport_per_t: float = 0.0,
        post_harvest_loss_fraction: float = 0.0,
        loss_fraction_source: str | None = None,
        quality_discount_fraction: float = 0.0,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if harvested_quantity_t < 0:
            raise EG.EconomicError("harvested_quantity_t debe ser >= 0")
        if not (0.0 <= post_harvest_loss_fraction <= 1.0):
            raise EG.EconomicError("post_harvest_loss_fraction debe estar en [0, 1]")
        if not (0.0 <= quality_discount_fraction <= 1.0):
            raise EG.EconomicError("quality_discount_fraction debe estar en [0, 1]")
        if post_harvest_loss_fraction > 0 and not loss_fraction_source:
            raise EG.EconomicError(
                "post_harvest_loss_fraction > 0 requiere 'loss_fraction_source' explícita"
            )

        unit_costs = {
            "handling": float(handling_cost_per_t),
            "cleaning_sorting": float(cleaning_sorting_per_t),
            "drying": float(drying_per_t),
            "processing": float(processing_per_t),
            "packaging": float(packaging_per_t),
            "storage": float(storage_per_t),
            "refrigeration": float(refrigeration_per_t),
            "transport": float(transport_per_t),
        }
        total_per_t = sum(unit_costs.values())
        total_cost = harvested_quantity_t * total_per_t
        lost_t = harvested_quantity_t * post_harvest_loss_fraction
        saleable_t = max(0.0, harvested_quantity_t - lost_t)

        return EG.economic_envelope(
            self.engine,
            result={
                "currency": currency.upper(),
                "harvested_quantity_t": round(harvested_quantity_t, 4),
                "post_harvest_lost_t": round(lost_t, 4),
                "saleable_quantity_t": round(saleable_t, 4),
                "quality_discount_fraction": round(quality_discount_fraction, 4),
                "effective_saleable_equivalent_t": round(
                    saleable_t * (1.0 - quality_discount_fraction), 4
                ),
                "cost_per_t_breakdown": {k: round(v, 2) for k, v in unit_costs.items()},
                "total_post_harvest_cost": round(total_cost, 2),
                "cost_per_saleable_t": (
                    round(total_cost / saleable_t, 2) if saleable_t > 0 else None
                ),
                "loss_fraction_source": loss_fraction_source,
                "separated_from_field_production_loss": True,
            },
            sources=["agrosv_scenario"],
            assumptions=["las pérdidas poscosecha se aplican sobre cantidad ya cosechada"],
            limitations=[
                "no aplica porcentajes genéricos de pérdida como medición salvadoreña verificada",
            ],
            evidence_class="model_estimate",
            query={"harvested_quantity_t": harvested_quantity_t},
        )


class ProductionBudgetEngine:
    """Genera presupuestos de producción observados, de referencia o de escenario."""

    engine = "production_budget"
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self.cost_engine = AgriculturalCostEngine()

    def build(
        self,
        *,
        budget_type: str,
        crop_id: str,
        system_id: str,
        area_ha: float,
        cycle: str,
        items: Iterable[Mapping[str, Any]],
        variety: str | None = None,
        expected_production_t: float | None = None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        b_type = str(budget_type).strip().lower()
        if b_type not in BUDGET_TYPES:
            raise EG.EconomicError(
                f"budget_type inválido: {budget_type!r}; use {BUDGET_TYPES}"
            )
        crop = crop_id.strip().lower()
        if crop not in CROPS:
            raise EG.EconomicError(f"cultivo desconocido: {crop_id!r}")

        agg = self.cost_engine.aggregate(
            items=items,
            area_value=area_ha,
            area_unit="ha",
            production_value=expected_production_t,
            production_unit="t",
            currency=currency,
        )["result"]

        ev_map = {
            "observed": "observed_transaction",
            "reference": "institutional_reference",
            "scenario": "synthetic_scenario",
        }
        return EG.economic_envelope(
            self.engine,
            result={
                "budget_id": EG.stable_id("BDG", b_type, crop, system_id, area_ha, cycle),
                "budget_type": b_type,
                "crop_id": crop,
                "variety": variety,
                "system_id": system_id,
                "cycle": cycle,
                "area_ha": agg["area_ha"],
                "area_mz": agg["area_mz"],
                "expected_production_t": expected_production_t,
                "currency": agg["currency"],
                "total_estimated_cost": agg["totals"]["total"],
                "unit_costs": agg["unit_costs"],
                "cost_breakdown": agg["totals"],
                "cost_drivers": agg["cost_drivers"],
                "line_items": agg["items"],
            },
            sources=["agrosv_scenario"] if b_type == "scenario" else ["mag_anuarios_y_costos"],
            assumptions=[f"presupuesto estrictamente etiquetado como '{b_type}'; nunca mezclado"],
            limitations=[
                "un presupuesto de referencia o escenario no equivale a gasto real observado en finca",
            ],
            evidence_class=ev_map[b_type],
            synthetic=(b_type == "scenario"),
            query={"budget_type": b_type, "crop_id": crop, "system_id": system_id, "area_ha": area_ha},
        )


__all__ = [
    "AgriculturalCostEngine",
    "BUDGET_TYPES",
    "INPUT_CATEGORIES",
    "IRRIGATION_SYSTEMS",
    "InputCostEngine",
    "IrrigationCostEngine",
    "LABOR_ACTIVITIES",
    "LABOR_MODES",
    "LaborCostEngine",
    "MachineryAndEquipmentCostEngine",
    "PRICE_TYPES",
    "PostHarvestCostEngine",
    "ProductionBudgetEngine",
]
