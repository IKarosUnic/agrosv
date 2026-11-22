# Reporte de validación matemática y empírica (Fase 8)

## 1. Validación matemática verificada (pruebas unitarias deterministas)

1. **Conversiones de unidades (§13):**
   - `1.0 mz == 0.70 ha`, `0.70 ha == 1.0 mz`.
   - `1.0 qq == 46.0 kg`, `1.0 t == 1000.0 kg`.
   - Normalización de precios WFP: `USD 45 / 45 KG == USD 1.00 / kg`; `USD 46 / 46 KG == USD 1000.00 / t`.
2. **Costos y presupuestos:**
   - Agregación `80/ha + 220/ha` en `2 ha` + `150/ciclo` = `750.00 USD` (`600` variable, `150` fijo, `375/ha`, `150/t` para `5 t`).
   - Depreciación lineal maquinaria: `(12000 - 2000) / 2000 h = 5.0 USD/h`.
   - Riego por goteo (`200 mm`, `1 ha`, eficiencia `0.90`, `capex=1000`, `10` ciclos): `depreciation_per_cycle = 100.0 USD`.
3. **Rentabilidad y equilibrio:**
   - `2 ha × 3 t/ha × 400 USD/t = 2400 USD` ingreso bruto; costo variable `1200`, fijo `300` ⇒ margen bruto `1200 USD`, margen neto operativo `900 USD`.
   - Punto de equilibrio: `precio = 250.0 USD/t`, `rendimiento = 1.875 t/ha`.
   - Inversión (`I0 = 1000`, flujos `[400, 400, 400, 400]`, `r = 0.10`): `payback = 2.5 años`, `NPV > 0`, `IRR > 0.10`.
4. **Logística y hogares:**
   - Distancias calculadas en `EPSG:32616` contra red vial OSM real.
   - Separación de capas `SOURCE_PROFILE`, `SYNTHETIC_AGRICULTURAL_STATE`, `HOUSEHOLD_STATE` y `SIMULATION_HISTORY` validada con `check_separation`.

## 2. Validación empírica lograda vs pendiente

- **Lograda (integridad de datos reales):**
  - Integración verificada de 7,864 filas reales WFP El Salvador (`2005-01-15` a `2026-10-15`), 71 mercados WFP, 39 puntos `mercado` OSM, 363 personas agrícolas reales de `Nemotron-Personas-El-Salvador` y agregados preliminares BCR CAP 2025.
- **Pendiente (requiere datos no abiertos):**
  - Validación de presupuestos reales contra encuestas de costos de finca por municipio/cultivo en El Salvador.
  - Validación de márgenes netos al productor contra precios reales recibidos en finca (*farm-gate*).
  - Validación de pérdidas poscosecha medidas en campo y tiempos reales de transporte por ruta.
  - Calibración contra microdatos del CAP 2025 (restringidos por art. 25 LEC).
