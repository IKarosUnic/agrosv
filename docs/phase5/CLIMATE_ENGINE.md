# ClimateEngine — climatología del período, extremos y sequía

**Fase 5 · versión 5.0.0 · estado: implementado con dos puntos de reanálisis**
Código: `backend/agrosv/engines/climate.py` · API: `/api/engines/climate`

## 1. Qué existe y qué no

Trabaja con **dos coordenadas de reanálisis** y una serie diaria de
**2019-01-01 a 2025-12-31** (2.557 días por variable):

| Dataset | Coordenada | Resolución de celda | Variables |
|---|---|---|---|
| `nasa_power_point` | 13,70° N, 89,20° O | ~55 × 69 km (MERRA-2) | precipitación, Tmax, Tmin |
| `open_meteo_point` | 13,673° N, 89,174° O | ~9 km (ERA5/IFS) | precipitación, ET0, humedad relativa media, Tmax, Tmin |

Lo que **no** existe y se declara en cada respuesta:

| Variable / capacidad | Estado |
|---|---|
| Estaciones SNET/MARN | `RESTRICTED_SOURCE` |
| Normales OMM de 30 años | `INSUFFICIENT_RECORD` (7 años) |
| Pronóstico | `NOT_IMPLEMENTED` |
| Proyección climática | no integrada |
| Radiación solar, viento, presión | no integradas |
| Interpolación espacial | **no se aplica** |
| Temperatura media observada | se deriva como (Tmax+Tmin)/2 |

**Reanálisis ≠ observación.** Ninguna cifra se presenta como medición de estación.
La clase de evidencia `reanalysis` viaja en cada bloque de la respuesta.

## 2. Agregaciones

| Escala | Método | Control de cobertura |
|---|---|---|
| Diaria | serie tal como está almacenada | — |
| Mensual | suma (P, ET0) o media (T, HR) | `coverage = días presentes / días del mes ≥ 0,9` |
| Anual | suma o media | `coverage = días presentes / 365 o 366 ≥ 0,9` |
| Estacional | tabla mensual de 12 meses | `n_years` por mes |

Un período con cobertura < 0,9 se marca `quality_flag: incomplete_period` y
`complete: false`; no se rellena.

## 3. Indicadores implementados

### 3.1 Extremos de precipitación (ETCCDI)

Definiciones de Zhang et al. (2011), con día húmedo = P ≥ 1,0 mm:

| Índice | Definición |
|---|---|
| `prcptot` | suma anual de precipitación diaria |
| `rx1day` | máxima precipitación de 1 día |
| `rx5day` | máxima suma de 5 días consecutivos |
| `r95p` | suma anual de días con P > percentil 95 de días húmedos del período |
| `cdd` | máxima racha de días con P < 1 mm |
| `cwd` | máxima racha de días con P ≥ 1 mm |
| `sdii` | precipitación total / días húmedos |

El percentil 95 se calcula sobre los días húmedos del período base completo y se
publica como `r95p_threshold_mm`.

### 3.2 Rachas secas

`dry_spells()` informa por año la racha seca máxima con fechas de inicio y fin, y el
número de rachas de ≥ 5, 10, 15 y 20 días. Umbral declarado: día seco = P < 1,0 mm.

Una racha seca de reanálisis **no es una sequía agrícola**: no incorpora suelo,
demanda hídrica ni cultivo.

### 3.3 Estacionalidad

`seasonality()` combina la climatología mensual de precipitación con Tmax/Tmin:

- mes húmedo según **Walter–Lieth**: `P_mes > 2 · T_mes` (P en mm, T en °C);
- mes más húmedo y más seco;
- concentración: porcentaje de la precipitación anual en los tres meses más húmedos.

La temporada agrícola (primera/postrera) **no se deriva** de esta tabla: requiere los
calendarios del MAG/CENTA.

### 3.4 Anomalías y extremos térmicos

- temperatura media diaria = (Tmax + Tmin)/2;
- anomalía anual = media anual − media del período 2019–2025;
- días con Tmax > percentil 95 del período;
- días con Tmin < percentil 5 del período.

Una anomalía de reanálisis no es un evento extremo observado: la celda de NASA POWER
es de ~55 × 69 km.

### 3.5 Sequía: percentil, no SPI

`drought_indicator()` calcula la precipitación acumulada a 3 meses y su percentil
empírico respecto de todas las ventanas del período:

| Percentil | Categoría |
|---|---|
| ≤ 5 | extremadamente seco |
| 5–10 | muy seco |
| 10–20 | seco |
| 20–80 | normal |
| 80–90 | húmedo |
| 90–95 | muy húmedo |
| > 95 | extremadamente húmedo |

**No es el SPI.** El SPI exige ajustar una distribución (gamma mixta con ceros) sobre
≥ 30 años; con 7 años y muchos ceros el ajuste no sería defendible. La respuesta incluye
`not_spi` con esta explicación.

## 4. Normalidad climática

`normals()` devuelve `status: insufficient_record`, el período real, el número de años
(7) y el requisito OMM (30). No se publica una normal de 30 años. Se publica una
**climatología del período disponible**.

## 5. Representatividad espacial

`nearest_point(lon, lat)` devuelve el punto climático más cercano, su distancia en km
y `representative: true` solo si la distancia es ≤ 25 km. Para cualquier punto de El
Salvador la distancia es > 0 y se informa.

No se interpola el clima entre los dos puntos: un mapa interpolado con dos muestras
sería una invención con apariencia de dato. El perfil lo declara:

```json
"spatial_interpolation": {"applied": false, "reason": "..."}
```

## 6. Ejemplo real

Punto `(-89.2, 13.7)`, serie Open-Meteo:

| Año | P (mm) | ET0 (mm) |
|---|---|---|
| 2019 | 1.865,7 | 1.635,6 |
| 2020 | 2.306,2 | 1.554,4 |
| 2021 | 2.684,7 | 1.626,0 |
| 2022 | 2.791,4 | 1.556,7 |
| 2023 | 1.786,0 | 1.680,3 |
| 2024 | 2.187,2 | 1.601,5 |
| 2025 | 1.912,5 | 1.670,5 |

Estacionalidad: junio es el mes más húmedo (333,2 mm; húmedo Walter–Lieth) y enero el
más seco (7,5 mm). En 2025: Rx1day 48,0 mm, Rx5day 105,4 mm, R95p 264,6 mm,
CDD 37 días, CWD 22 días, SDII 7,45 mm/día húmedo. Indicador de sequía a 3 meses
(diciembre 2025): 278,3 mm, percentil 39, categoría `normal`.

## 7. Límites

1. Solo dos puntos: no hay cobertura nacional.
2. Reanálisis, no estación; los productos subestiman lluvias convectivas locales.
3. Siete años no son una normal; los percentiles tienen referencia débil.
4. Sin pronóstico ni proyección.
5. Sin homogeneización ni control de calidad con estaciones.
6. Una celda de 9 km o 55 km no representa un punto.

## 8. Pruebas

`tests/test_engines_climate.py` (15): haversine, agregación incompleta, rachas,
agregaciones declaradas, variable inexistente, distancia del punto, suma anual,
climatología mensual, coherencia de ETCCDI, umbral de rachas, anomalías centradas,
sequía por percentil y no SPI, normales insuficientes, Walter–Lieth y ausencia de
interpolación.
