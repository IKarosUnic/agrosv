# MODULE E — Agricultural Economic Intelligence

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Motor de costos, ingresos y márgenes con **precios fechados y trazables**. No
inventa precios ni extrapola series sin declararlo.

---

## 1. Fuentes (estado verificado)

| Fuente | Contenido | Frecuencia | Formato | Estado |
|---|---|---|---|---|
| MAG — Informe diario de precios | Precios mayoristas | Diaria | PDF | **VERIFIED** |
| MAG — Informe semanal | Precios por plaza | Semanal | PDF | **VERIFIED** |
| MAG — Informe mensual | Mayorista y consumidor | Mensual | PDF | **VERIFIED** |
| MAG — Guía anual de precios de insumos | Semillas, fertilizantes | Anual (2019–2023) | PDF | **VERIFIED** |
| MAG — Informe anual de costos de producción | Costos por cultivo (2019-20…2022-23) | Anual | PDF | **VERIFIED** |
| MAG — Anuarios de Estadísticas Agropecuarias | Producción, superficie | Anual | PDF | **VERIFIED** |
| BCR — V Censo Agropecuario 2025 | Producción, destino, canales | Por entrega | PDF/PPT | **VERIFIED** (agregados) |

**Licencia:** ninguna de estas fuentes declara licencia de reutilización. Se
usan con atribución y **no** se redistribuyen los PDF; se publican agregados
derivados con cita y fecha.

**Regla de precios:** un precio sin fecha, plaza y unidad no entra al motor. Los
PDF se extraen con referencia de página y revisión humana.

---

## 2. Estructura de costos

| Componente | Fuente | Unidad |
|---|---|---|
| Semilla | Guía de insumos MAG | USD/ha o USD/mz |
| Fertilizante | Guía de insumos MAG | USD/ha |
| Pesticida | Guía de insumos MAG | USD/ha |
| Mano laboral | Costos de producción MAG | jornales/ha |
| Riego | Costos MAG + consumo energético | USD/ha |
| Transporte | Costos MAG / encuesta | USD/qq |
| Servicios (maquila) | Costos MAG | USD/ha |
| Costo financiero | Tasa de referencia (BCR) | % anual |

**Conversiones declaradas:** 1 manzana = 0,6989 ha; 1 quintal = 45,36 kg;
moneda USD (El Salvador no emite moneda propia desde 2001).

---

## 3. Cálculos y terminología

| Indicador | Fórmula | Etiqueta obligatoria |
|---|---|---|
| Costo total | ∑ costos directos + indirectos | *estimado* si viene de tabla MAG |
| Ingreso bruto | rendimiento × precio | *estimado* o *observado* |
| Margen bruto | ingreso bruto − costos directos | *estimado* |
| Punto de equilibrio | costos fijos / (precio − costo variable unitario) | *estimado* |
| Rentabilidad | margen / costos | *estimada* |

**Prohibido** llamar «rentabilidad comprobada» a un margen calculado con
precios de referencia. La etiqueta se guarda en el resultado, no solo en la UI.

---

## 4. Escenarios y sensibilidad

- **Precio**: ±20 % sobre el precio de la última semana documentada.
- **Rendimiento**: rango del motor de simulación (p10–p90), nunca un único valor.
- **Costo de insumos**: ±15 % sobre la guía anual vigente.
- **Análisis**: tornado por variable y matriz de dos vías (precio × rendimiento).

Toda salida incluye el conjunto de supuestos en JSON y su `provenance_id`.

---

## 5. Modelo de datos

```sql
price_series(
  price_id, product_code, market, price_type,   -- mayorista|consumidor|insumo
  price_date, value_usd, unit, source_id, page_ref
);

cost_structure(
  cost_id, crop_code, season, activity,
  value_usd_per_ha, source_id, year, notes
);

budget_scenario(
  scenario_id, parcel_id NULL, crop_code, area_ha,
  yield_t_ha, price_usd_t, assumptions JSONB,
  revenue_usd, cost_usd, gross_margin_usd, break_even_yield,
  label TEXT,                                   -- 'estimado' | 'observado'
  provenance_id
);
```

---

## 6. Interfaz

```
GET  /api/econ/prices?product=maiz&from=&to=&type=mayorista
GET  /api/econ/costs?crop=maiz&season=2025
POST /api/econ/budget
GET  /api/econ/compare?crops=maiz,frijol&area_ha=1
GET  /api/econ/sensitivity?scenario_id=
```

Toda respuesta incluye `as_of` (fecha del último precio usado) y `label`.

---

## 7. Validación

| Prueba | Criterio |
|---|---|
| Precio fechado | 100 % de precios con `price_date` y `source_id` |
| Unidad | unidad explícita y conversión verificada |
| Cuadre | ∑ componentes = costo total (± 1 %) |
| Coherencia | ingreso > 0; punto de equilibrio dentro de rango físico |
| Contraste | costo por hectárea vs informe MAG del mismo año (< 20 % de diferencia) |
| Sensibilidad | precios y rendimiento mueven el margen en la dirección esperada |

---

## 8. Limitaciones

1. Los precios son de plaza y fecha; no representan el precio que recibe cada
   productor.
2. Los costos son promedios de productores; no capturan heterogeneidad.
3. La extracción de PDF puede introducir errores: se revisa y se cita página.
4. No hay serie de precios de insumos posterior a 2023 verificada.
5. El margen no incluye costos de oportunidad ni riesgo climático.

---

## 9. Dependencias y prioridad

Depende de: catálogo de cultivos, ingestión de PDF (DATA_PIPELINE §11.1),
simulación para el rendimiento. Habilita: Module H (gemelo digital), agentes
(Module 4 de IA), Module M (experimentos).

**Prioridad:** alta para un cultivo piloto (maíz). Es barato: solo requiere
parseo y revisión, sin cuentas ni licencias.
