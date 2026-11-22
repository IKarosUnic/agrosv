# Validación de datos ambientales — Fase 5

**AGROSV · versión 5.0.0 · 2026-11-22**

## 1. Alcance

Este documento separa dos cosas que suelen confundirse:

- **verificación de software**: el código hace lo que declara, con unidades y CRS
  coherentes, sobre artefactos presentes y con resultados reproducibles;
- **validación científica**: las cifras coinciden con la realidad dentro de un error
  conocido, medido contra una referencia independiente.

Fase 5 logra lo primero. **No logra lo segundo** para ningún motor, porque el
repositorio no contiene estaciones, muestras de laboratorio, aforos ni puntos de control.
La política V0–V4 de Fase 2 se mantiene: ninguna capa se promueve por haber sido
importada.

## 2. Estado por dataset

| Dataset | Clase | Verificado | No validado |
|---|---|---|---|
| `copdem30` | `modeled_prediction` | CRS, resolución, `nodata`, rango, cobertura | exactitud vertical y horizontal; DSM vs DTM |
| `geoboundaries_adm1` | `observed` | integridad geométrica, contención, área | coincidencia con el límite legal |
| `osm_sv` | `observed` | integridad, distancias, cobertura declarada | exhaustividad y exactitud de cauces |
| `soilgrids_2` | `modeled_prediction` | CRS, escala, unidades, suma textural, NoData | error del modelo; acuerdo con laboratorio |
| `nasa_power_point` | `reanalysis` | integridad temporal, unidades, cobertura | sesgo frente a estación |
| `open_meteo_point` | `reanalysis` | integridad temporal, unidades, cobertura | sesgo frente a estación |
| `chirps3` | `satellite_estimate` | estructura y rango de una muestra de un día | serie, sesgo, calibración local |

Ninguno alcanza un nivel de validación externa. `V1` significa consistencia interna y
cobertura, no verdad.

## 3. Comprobaciones ejecutadas

### 3.1 Estructura y metadatos

- 13 rásteres catalogados con CRS, resolución nativa, `dtype` y `nodata`.
- Apertura por cabecera y por ventana; ninguna lectura completa del país.
- Unidades canónicas y escala declarada aplicada al muestrear.
- `null` para NoData; nunca cero por defecto.

### 3.2 CRS y geometría

- Consultas en EPSG:4326, métricas en EPSG:32616, áreas en EPSG:6933.
- Ida y vuelta 4326 → 32616 → 4326 con error < 1 × 10⁻⁹ grados.
- Área nacional derivada: **20.966,364 km²** frente a **21.041 km²** de referencia
  → **−0,35 %**, dentro de la tolerancia declarada de ±3 %.
- Contención administrativa resuelta con geometría exacta, no por centroides.

### 3.3 Suelo

- Las fracciones arena + limo + arcilla suman 95–105 % en las celdas válidas.
- pH en rango 3,5–10,0 cuando hay dato; fuera de rango se marca como posible artefacto.
- Clase textural contrastada contra 12 combinaciones conocidas del triángulo USDA.
- Celdas NoData devuelven `available: false` con motivo, sin imputación.
- **No** se comparó con análisis de laboratorio: no existen.

### 3.4 Hidrología

- Área de cuenca ≤ área de la ventana (invariante geométrico).
- `truncated` verdadero cuando la cuenca toca el borde.
- Budyko: `0 ≤ Q ≤ P` para todos los casos probados.
- Balance: `P − ET0` coincide con la diferencia de las medias publicadas (±0,2 mm).
- **No** se comparó con aforos: no existen.

### 3.5 Clima

- Cobertura anual ≥ 0,9 en los siete años; períodos incompletos se marcan.
- Coherencia ETCCDI: `Rx5day ≥ Rx1day`, `R95p ≤ PRCPTOT`, `CDD/CWD ≤ 366`.
- Anomalías centradas en el período (media ≈ 0).
- Intercomparación NASA POWER vs Open-Meteo: **n = 2.557 por variable**, clasificada
  como `intercomparison`.

**Una intercomparación no es una validación.** Dos productos pueden coincidir y ambos
estar sesgados. No eleva el nivel de validación de ninguno.

### 3.6 Cobertura espacial

- El rectángulo nacional se declara como bbox, no como polígono.
- Un punto fuera del bbox se rechaza; uno dentro pero en aguas se declara fuera de tierra.
- El clima informa distancia al punto usado y no interpola.
- El suelo declara 97,4 % de cobertura de tierra firme; las celdas sin dato se informan.

## 4. Conflictos entre fuentes

| Comparación | Resultado |
|---|---|
| SoilGrids vs CENTA | **imposible**: CENTA está `RESTRICTED`; no se detectan conflictos |
| NASA POWER vs Open-Meteo | intercomparación disponible; no se declara conflicto ni acuerdo |
| DEM vs verdad de campo | sin puntos de control; no evaluable |

La ausencia de conflictos publicada por el motor de suelo es una consecuencia de la
falta de una segunda fuente, no una prueba de consistencia.

## 5. Licencias y redistribución

| Dataset | Licencia | Redistribución |
|---|---|---|
| copdem30 | Copernicus DEM (DLR/Airbus), uso libre con atribución | sí, con atribución |
| geoboundaries_adm1 | CC BY-SA 2.0 | sí, compartir igual |
| osm_sv | ODbL 1.0 | sí, base derivada ODbL |
| soilgrids_2 | CC BY 4.0 | sí |
| nasa_power_point | datos abiertos NASA, atribución | sí |
| open_meteo_point | datos abiertos (verificar términos del proveedor) | sí |
| chirps3 | datos abiertos CHC | sí |

Las fuentes restringidas (CENTA, SNET/MARN, HydroSHEDS) **no** se redistribuyen ni se
usan en cálculos; aparecen en el catálogo con su estado y motivo.

## 6. Qué falta para validar

1. Serie diaria de estaciones SNET/MARN con control de calidad.
2. Muestras de suelo CENTA georreferenciadas con método de laboratorio.
3. Puntos de control GNSS para el DEM.
4. Aforos y curvas de gasto para caudales.
5. Delimitación oficial de cuencas.
6. Ensayos de rendimiento para las reglas agronómicas.

Solicitar esos datos es la recomendación principal de Fase 6, no aumentar el número de
variables publicadas.

## 7. Conclusión

- **Verificación de software:** superada (373 pruebas; ver
  `PHASE_5_TESTING_REPORT.md`).
- **Validación científica:** no alcanzada; ninguna cifra tiene error medido contra una
  referencia independiente.
- **Trazabilidad:** cada cifra conserva dataset, versión, licencia, resolución, unidades,
  método y supuestos.
- **Honestidad:** las ausencias están enumeradas y son consultables por API.
