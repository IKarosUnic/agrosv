"""AGROSV — AgriculturalEconomyEngine (§5.6).

No hay precios ni costos verificados en el repositorio: los documentos de MAG y
BCR son PDF sin serie tabular reutilizable. Por eso el motor **exige** hojas de
precios y costos aportadas por el usuario, cada una con fuente, fecha, moneda y
unidad. Sin ellas no se calcula economía.

No es contabilidad ni estadística económica oficial: es aritmética de escenario
sobre datos declarados.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from . import governance as SG

ENGINE = "agricultural_economy"
ENGINE_VERSION = SG.ENGINE_VERSION

COST_ITEMS = ("seed", "fertilizer", "pesticide", "labor", "irrigation",
              "equipment", "transport")


class EconomyError(ValueError):
    pass


def _require_meta(item: str, payload: Mapping[str, Any]) -> None:
    for field in ("source", "date", "currency", "unit"):
        if not payload.get(field):
            raise EconomyError(f"{item}: falta '{field}' (obligatorio)")
    try:
        date.fromisoformat(str(payload["date"]))
    except ValueError:
        raise EconomyError(f"{item}: date debe ser YYYY-MM-DD") from None
    if float(payload.get("amount", payload.get("value", 0))) < 0:
        raise EconomyError(f"{item}: el monto no puede ser negativo")


def price_sheet(entries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    out = {}
    for crop_id, payload in entries.items():
        _require_meta(f"precio {crop_id}", payload)
        price = payload.get("price_per_t")
        if price is None or float(price) < 0:
            raise EconomyError(f"precio {crop_id}: price_per_t inválido")
        out[crop_id] = {**payload, "price_per_t": float(price),
                        "is_observed": bool(payload.get("is_observed", False))}
    return out


def cost_sheet(entries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    out = {}
    for item, payload in entries.items():
        _require_meta(f"costo {item}", payload)
        amount = payload.get("amount", payload.get("value"))
        if amount is None or float(amount) < 0:
            raise EconomyError(f"costo {item}: amount inválido")
        out[item] = {**payload, "amount": float(amount)}
    return out


class AgriculturalEconomyEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def evaluate(self, *, agent: dict[str, Any],
                 costs: Mapping[str, Mapping[str, Any]],
                 prices: Mapping[str, Mapping[str, Any]],
                 yield_t_ha: float,
                 area_ha: float | None = None,
                 crop_id: str | None = None) -> dict[str, Any]:
        state = agent.get("state", {}).get("payload", {})
        crop = crop_id or state.get("primary_crop")
        if not crop:
            raise EconomyError("no hay cultivo para valorar")
        if crop not in prices:
            raise EconomyError(
                f"no hay precio para {crop}: no se inventa un precio")
        cost = cost_sheet(costs)
        price = price_sheet(prices)[crop]
        area = float(area_ha if area_ha is not None else state.get("area_ha", 1.0))
        if area <= 0:
            raise EconomyError("area_ha debe ser > 0")
        if yield_t_ha is None or yield_t_ha < 0:
            raise EconomyError("yield_t_ha debe ser ≥ 0")
        currencies = {c["currency"] for c in cost.values()} | {
            price["currency"]}
        if len(currencies) > 1:
            raise EconomyError(f"monedas incompatibles: {sorted(currencies)}")
        currency = currencies.pop()
        per_ha = {k: v["amount"] for k, v in cost.items()}
        total_cost = round(sum(per_ha.values()) * area, 2)
        revenue = round(price["price_per_t"] * yield_t_ha * area, 2)
        margin = round(revenue - total_cost, 2)
        break_even_yield = (total_cost / (price["price_per_t"] * area)
                            if price["price_per_t"] > 0 else None)
        capital = float(state.get("capital_usd", 0.0))
        result = {
            "crop_id": crop,
            "area_ha": area,
            "yield_t_ha": yield_t_ha,
            "currency": currency,
            "costs": {
                "per_ha": per_ha,
                "total": total_cost,
                "items": sorted(per_ha),
                "missing_items": [i for i in COST_ITEMS if i not in per_ha],
            },
            "revenue": revenue,
            "margin": margin,
            "margin_per_ha": round(margin / area, 2),
            "break_even_yield_t_ha": (round(break_even_yield, 3)
                                      if break_even_yield is not None else None),
            "break_even_price_per_t": (round(total_cost / (yield_t_ha * area), 2)
                                       if yield_t_ha > 0 else None),
            "credit_need": round(max(0.0, total_cost - capital), 2),
            "capital_available": capital,
            "price_context": {
                "market": price.get("market"),
                "date": price.get("date"),
                "source": price.get("source"),
                "is_observed": price.get("is_observed", False),
            },
            "cost_sources": sorted({c["source"] for c in cost.values()}),
            "is_accounting": False,
            "is_official_statistic": False,
        }
        return SG.synthetic_envelope(
            ENGINE, result=result,
            assumptions=[
                "los costos y precios fueron aportados por el usuario",
                "se aplica el mismo costo por hectárea a toda el área",
                "no hay costos fijos, depreciación, impuestos ni financiamiento",
            ],
            limitations=[
                "no es contabilidad ni estadística oficial",
                "sin hoja de precios no se ejecuta: AGROSV no inventa precios",
                "los resultados dependen por completo de las hojas aportadas",
                "no se modela riesgo de precio ni tipo de cambio",
            ],
            sources=["agrosv_scenario"],
            scenario_id=agent.get("state", {}).get("scenario_id"),
            processing=[SG.AG.step("validación de hojas", "cost_sheet/price_sheet"),
                        SG.AG.step("aritmética de margen", "evaluate")],
            query={"crop_id": crop, "area_ha": area,
                   "yield_t_ha": yield_t_ha},
        )

    def credit_need(self, *, agent: dict[str, Any],
                    costs: Mapping[str, Mapping[str, Any]],
                    area_ha: float | None = None) -> dict[str, Any]:
        state = agent.get("state", {}).get("payload", {})
        cost = cost_sheet(costs)
        area = float(area_ha if area_ha is not None else state.get("area_ha", 1.0))
        total = sum(c["amount"] for c in cost.values()) * area
        capital = float(state.get("capital_usd", 0.0))
        return {
            "total_cost": round(total, 2),
            "capital": capital,
            "credit_need": round(max(0.0, total - capital), 2),
            "credit_access": state.get("credit_access"),
            "note": ("necesidad aritmética; el acceso declarado es un "
                     "atributo sintético, no una medición"),
            "synthetic": True,
        }


__all__ = ["AgriculturalEconomyEngine", "EconomyError", "COST_ITEMS",
           "price_sheet", "cost_sheet"]
