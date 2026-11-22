# Metodología económica de Fase 8

## 1. Conversiones explícitas de unidades (El Salvador)

Definidas y probadas en `backend/agrosv/economics/governance.py`:

- **Área:** `1 manzana (mz) = 0.70 ha`, `1 ha = 1.428571 mz`, `1 m² = 0.0001 ha`.
- **Masa:** `1 quintal salvadoreño (qq / 46 KG) = 46.0 kg`, `1 saco WFP ("45 KG") = 45.0 kg`, `1 libra = 0.45359237 kg`, `1 tonelada métrica (t) = 1000.0 kg`.
- **Normalización de precios:** `precio_normalizado(target) = (precio / kg(unidad_origen)) × kg(unidad_destino)`.

## 2. Fórmulas económicas principales

- **Costo unitario:** `costo_total / área_ha`, `costo_total / área_mz`, `costo_total / producción_kg` (o `qq`, `t`).
- **Depreciación lineal de maquinaria:** `(precio_compra - valor_rescate) / vida_útil_horas`.
- **Demanda bruta de agua de riego:** `m3_netos = lamina_mm × 10 × area_ha`; `m3_brutos = m3_netos / eficiencia_sistema`.
- **Ingreso neto por canales:** `sum(volumen_vendible × share_i × precio_i × factor_calidad_i - volumen_i × (flete_i + comercializacion_i))`.
- **Margen bruto:** `ingreso_bruto - sum(costos_variables_directos)` (nunca presentado como utilidad neta).
- **Margen neto escalonado:**
  - `resultado_caja = ingreso - costos_variables - costos_fijos_efectivo`
  - `resultado_contable = resultado_caja - depreciación - financiamiento`
  - `resultado_economico = resultado_contable - trabajo_familiar_imputado - costo_oportunidad`
- **Punto de equilibrio:**
  - `precio_eq = (costos_fijos + costo_var_ha × area_ha) / (rendimiento × area_ha) + costo_venta_t`
  - `rendimiento_eq = costo_total / (area_ha × (precio_t - costo_venta_t))`
- **Inversión:** Periodo de recuperación acumulado (`payback_years`), Valor Actual Neto (`NPV = -I0 + sum(CF_t / (1+r)^t)`) y TIR (`IRR` por bisección).
- **Riesgo económico:** Enlace multiplicativo `R = H × E × V` de Fase 7 (`AgriculturalRiskEngine`) y estrés de margen bajo choques declarados.

## 3. Separación de inferencias

- Ninguna tendencia descriptiva de precios WFP se extrapola como pronóstico de largo plazo.
- Ningún margen mayorista-minorista se interpreta como poder de mercado o explotación.
- Ningún escenario condicional es una predicción.
