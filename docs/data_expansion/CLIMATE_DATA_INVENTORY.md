# CLIMATE_DATA_INVENTORY — AGROSV Fase 3

**Fecha de consulta:** 2026-11-22 · **Evidencia:** sondas propias + muestras en
`data/samples/phase3/`. Cada fila distingue **observación**, **reanálisis**,
**producto satelital** y **modelo**. No se mezclan.

---

## 1. Matriz de fuentes

| ID | Fuente | Tipo | Resolución espacial | Temporal | Historia | Acceso | Licencia declarada | Estado |
|---|---|---|---|---|---|---|---|---|
| `snet_meteorologia` | MARN/SNET | Observación en estación | Puntual | Diaria/horaria (según estación) | Décadas (variable) | Portal | No declarada | **VERIFIED** (portal) |
| `chirps3` | UCSB CHC | Satélite + estaciones | 0,05° (~5,5 km); nativo pentadal | Diaria (desagregada), pentadal, mensual | 1981– (rnl); 1998– (sat) | HTTP directo | Abierta con atribución (verificar aviso) | **VERIFIED** |
| `agera5` | Copernicus C3S | Reanálisis calibrado para agro | 0,1° (~11 km) | Diaria | 1979– | CDS con token | CC BY 4.0 | **RESTRICTED** |
| `era5` | Copernicus C3S | Reanálisis | 0,25° | Horaria | 1940– | CDS con token | CC BY 4.0 | **RESTRICTED** |
| `era5_land` | Copernicus C3S | Reanálisis de superficie | 0,1° | Horaria | 1950– | CDS con token | CC BY 4.0 | **RESTRICTED** |
| `gpm_imerg` | NASA GPM | Satélite | 0,1° | 30 min | 2000– | Earthdata Login | Abierta | **RESTRICTED** (login) |
| `noaa_cpc_precip` | NOAA CPC | Observación + interpolación | 0,5° | Diaria | 1979– | HTTP directo | Abierta | **VERIFIED** |
| `nasa_power` | NASA LaRC | Reanálisis + satélite, punto | Punto (0,5°×0,625°) | Diaria | 1981– | REST, sin clave | Abierta, sin restricción comercial | **VERIFIED** |
| `open_meteo` | Open-Meteo | Agregador (ERA5/IFS) | 0,1° / 9 km | Horaria/diaria | 1940– | REST, sin clave | CC BY 4.0; gratuito **no comercial** | **VERIFIED** |
| `worldclim_21` | WorldClim | Interpolación climatológica | 30″ (~1 km) | Normales 1970–2000 y futuro | — | Descarga | **No comercial, sin redistribución** | **DOCUMENTED** |
| `gaez_v4` | FAO/IIASA | Modelo agroclimático | 5′; 30″ selectivo | Normales y escenarios | — | REST/WCS | **No comercial, atribución** | **DOCUMENTED** |
| `google_weather` | Google | Modelo + observación | Modelo propio | Horaria/diaria | 24 h histórico | API con clave | ToS Google (§21.1/§21.2) | **RESTRICTED** (contractual) |
| `esgf_cmip6` | ESGF | GCM | 100–200 km | Diaria/mensual | 1850–2100 | ESGF/Metagrid | Términos CMIP6 | **DOCUMENTED** |

---

## 2. Variables disponibles por fuente

| Variable | SNET | CHIRPS | AgERA5 | ERA5-Land | IMERG | CPC | POWER | Open-Meteo | WorldClim |
|---|---|---|---|---|---|---|---|---|---|
| T máx / mín / media | SÍ | — | SÍ | SÍ | — | SÍ | SÍ | SÍ | SÍ |
| Precipitación | SÍ | SÍ | SÍ | SÍ | SÍ | SÍ | SÍ | SÍ | SÍ |
| Humedad relativa | SÍ | — | SÍ | SÍ | — | — | SÍ | SÍ | SÍ |
| Radiación solar | SÍ (si hay piranómetro) | — | SÍ | SÍ | — | — | SÍ | SÍ | SÍ |
| Viento | SÍ | — | SÍ | SÍ | — | — | SÍ | SÍ | SÍ |
| ET₀ | Derivada | — | SÍ | Derivada | — | — | SÍ | SÍ (FAO-56) | — |
| Humedad del suelo | No abierto | — | SÍ (capas) | SÍ | — | — | SÍ | SÍ | — |
| Presión | SÍ | — | SÍ | SÍ | — | — | SÍ | SÍ | — |
| Anomalías / SPI | — | Calculable | Calculable | Calculable | Calculable | — | — | — | — |

**Ninguna fuente entrega «eventos extremos» como variable.** Los extremos se
derivan (percentiles, SPI, días consecutivos secos) con método declarado.

---

## 3. Evidencia de descarga real

### 3.1 CHIRPS v3 — muestra validada

```
GET https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2026/chirps-v3.0.rnl.2026.01.15.tif
→ 200, 14.000.124 B, image/tiff
```

Validación con `rasterio`:

| Propiedad | Valor |
|---|---|
| CRS | EPSG:4326 |
| Tamaño | 7.200 × 2.400 px |
| Extensión | −180, −60, 180, 60 |
| Resolución | 0,05° × 0,05° |
| Tipo | float32 |
| Nodata | no declarado (−9999 convencional, **no** en metadatos) |

Archivo: `data/samples/phase3/chirps3_day/`, sha256 `1769f6f4fffe…`.
**Dos variantes diarias no intercambiables:** `rnl` (pentadas desagregadas con
ERA5, 1981–) y `sat` (desagregadas con IMERG Late V07, 1998–).

**Limitación científica central:** CHIRPS es nativo pentadal/mensual. El archivo
diario es una desagregación; su rejilla de 0,05° **no implica información real a
5,5 km diarios**. Para eventos extremos diarios hay que declararlo o trabajar a
escala pentadal. CHIRPS v2 deja de producirse después de diciembre de 2026.

### 3.2 NASA POWER — serie de punto (sin clave)

```
GET https://power.larc.nasa.gov/api/temporal/daily/point
    ?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN&community=AG
    &longitude=-89.20&latitude=13.70&start=20190101&end=20251231&format=JSON
→ 200, 128.012 B
```

Muestra: 2.557 días, 3 variables, `properties.parameter`. Sirve para
prototipado y validación rápida; no es una fuente de parcela.

### 3.3 Open-Meteo — ET₀ lista para modelos

```
GET https://archive-api.open-meteo.com/v1/archive?latitude=13.70&longitude=-89.20
    &start_date=2019-01-01&end_date=2025-12-31
    &daily=precipitation_sum,temperature_2m_max,temperature_2m_min,
           et0_fao_evapotranspiration,relative_humidity_2m_mean
→ 200, 92.997 B
```

Ventaja: entrega `et0_fao_evapotranspiration` ya calculada, que es el forzamiento
de AquaCrop. **Restricción contractual:** el nivel gratuito es solo para uso no
comercial (<10.000 llamadas/día); uso comercial exige plan de pago.

### 3.4 Fuentes con cuenta (no verificadas con credenciales)

`agera5` y `era5_land` responden 200 en la página del catálogo CDS, pero la
descarga exige token personal. **No se descargó ni se verificó una extracción.**
No se inventan credenciales.

---

## 4. Lo que no existe o no se pudo verificar

| Vacío | Consecuencia |
|---|---|
| Serie histórica de estaciones SNET en formato abierto | No se puede validar CHIRPS/ERA5 contra observación nacional |
| Metadatos de estaciones (coordenadas, altura, período, QC) | Sin ellos no hay control de calidad ni interpolación defendible |
| Radar meteorológico | No identificado como dato abierto |
| Evapotranspiración medida (lisímetros) | ET₀ solo estimada |
| Humedad de suelo medida en red nacional | Solo reanálisis/satélite |
| Datos oficiales de canícula por año | Se infiere de precipitación; no hay declaración oficial descargable |

---

## 5. Almanaque agroclimático (sección 6.1)

### 5.1 Qué se puede calcular y con qué

| Indicador | Definición operativa propuesta | Entrada mínima | Incertidumbre |
|---|---|---|---|
| Inicio de época lluviosa | Primer período de 5 días con ≥ 25 mm y sin 7 días secos posteriores (criterio declarado) | Precipitación diaria CHIRPS/POWER | Alta: depende del umbral y del producto |
| Fin de época lluviosa | Último período húmedo antes de la estación seca | Ibídem | Alta |
| Canícula | Déficit relativo de lluvia de 10–20 días en julio–agosto | Precipitación diaria/pentadal | Media; el fenómeno es real pero su fecha varía por año y región |
| Ventana de siembra | Período con humedad de suelo suficiente para germinación | Precipitación + ET₀ + suelo | Media |
| Ventana de cosecha | Madurez + lluvia por debajo de umbral | Clima + ciclo del cultivo | Media |
| Períodos secos | Días consecutivos < 1 mm | Precipitación diaria | Baja (definición explícita) |
| Acumulación de lluvia | Suma por etapa fenológica | Clima + fenología | Baja |
| Estrés térmico | Días por encima de Tmax crítica del cultivo | T máx + parámetro del cultivo | Media |
| Estrés hídrico | Déficit ETc vs ET₀ | Clima + Kc + suelo | Alta (parámetros) |

### 5.2 Regla de separación obligatoria

| Capa | Qué es | Horizonte | Fuente |
|---|---|---|---|
| **Pronóstico meteorológico** | Predicción numérica | 1–10 días | Open-Meteo/IFS, Google (opcional) |
| **Perspectiva estacional** | Probabilidad climática | 1–6 meses | CIIFEN/NOAA (no verificado como API en esta fase) |
| **Climatología histórica** | Normales y distribución | 1981–presente | CHIRPS, AgERA5, POWER |
| **Escenario simulado** | «Si la lluvia fuera X» | Definido por el usuario | Modelo AGROSV, etiquetado como escenario |

**Nunca** se presenta un escenario como pronóstico, ni una normal climática como
predicción de la campaña.

### 5.3 Requisito para publicar un almanaque

1. Serie diaria completa y trazable (CHIRPS o POWER) con versión y hash.
2. Umbrales declarados en el resultado, no en documentación aparte.
3. Comparación con al menos una fuente independiente (p. ej. CHIRPS vs POWER).
4. Reporte de años en que el criterio no se cumple (no ocultar fallos).
5. Etiqueta «calculado por AGROSV», no «dato oficial del MAG».

---

## 6. Prioridad de integración

| Orden | Fuente | Motivo |
|---|---|---|
| 1 | CHIRPS v3 (pentadal) + POWER | Gratis, sin clave, serie larga, ya validado |
| 2 | AgERA5 | ET₀ y variables completas para AquaCrop (requiere cuenta) |
| 3 | Estaciones SNET (solicitud) | Única verdad observada nacional |
| 4 | IMERG | Eventos intensos, complemento a CHIRPS |
| 5 | WorldClim/GAEZ | Solo para aptitud y contraste, no para operación |

---

## 7. Evidencia reproducible

- `scripts/06_probe_phase3_sources.py r3` → `probes_20261122_r3.json`
  (`chirps3_readme`, `chirps3_daily_dir`, `chirps3_tif_2026`, `nasa_power`,
  `open_meteo_archive`, `agera5_cds`, `era5_land_cds`, `gpm_imerg`,
  `noaa_cpc_precip`, `worldclim21`, `gaez_v4`, `esgf_cmip6`).
- `scripts/07_fetch_phase3_samples.py` → `data/manifests/phase3_samples.json`.
