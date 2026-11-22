# AgriculturalEconomyEngine

**Fase 6 · Subsistema B · Estado: implementado; exige hojas de costos y precios del usuario**

Código: `backend/agrosv/social/economy.py`
API: `POST /api/social/economy`

## Regla principal

AGROSV **no tiene precios ni costos verificados**. Los documentos de MAG y BCR
son PDF sin serie tabular reutilizable. Por eso el motor no ejecuta sin hojas
aportadas y rechaza cualquier entrada sin fuente, fecha, moneda y unidad.

## Validación

Cada ítem de costo requiere: `amount`, `unit`, `currency`, `date` (`YYYY-MM-DD`)
y `source`. Cada precio requiere: `price_per_t`, `unit`, `currency`, `date`,
`market` y `source`. Montos negativos y monedas mezcladas son error.

## Cálculo

```
costo_total    = Σ costo_por_ha × área
ingreso        = precio_por_t × rendimiento_t_ha × área
margen         = ingreso − costo_total
margen/ha      = margen / área
umbral_rendimiento = costo_total / (precio × área)
umbral_precio      = costo_total / (rendimiento × área)
necesidad_crédito  = max(0, costo_total − capital)
```

## Salidas

Costos por hectárea, total, ítems faltantes, ingreso, margen, umbrales,
necesidad de crédito, contexto de precio (mercado, fecha, fuente, si es
observado) y fuentes de costo. `is_accounting: false` y
`is_official_statistic: false`.

## Ítems considerados

Semilla, fertilizante, pesticida, mano de obra, riego, equipo y transporte. Si
falta un ítem, se informa en `missing_items`; no se rellena con cero
silenciosamente.

## Lo que no hace

* No inventa precios de mercado.
* No calcula depreciación, impuestos, financiamiento ni tipo de cambio.
* No usa el rendimiento nacional del CAP como rendimiento del agente.
* No produce una recomendación de inversión.
* No es contabilidad ni estadística económica oficial.

## Uso previsto

Comparar escenarios de costo o precio **bajo supuestos explícitos**, por
ejemplo un alza de 30 % en insumos o una caída de 30 % en precio de venta. El
resultado es aritmética de escenario, no una proyección.
