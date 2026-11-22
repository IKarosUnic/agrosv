# MODULE I — Climate Change Scenarios

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Analiza cómo cambia la aptitud agrícola bajo escenarios climáticos. **No** es
pronóstico meteorológico: es proyección climática a décadas, con incertidumbre
estructural de modelos globales.

---

## 1. Fuentes (acceso verificado)

| Fuente | Contenido | Resolución | Acceso | Licencia | Estado |
|---|---|---|---|---|---|
| CMIP6 (ESGF) | GCM, SSP126/245/370/585 | ~100–200 km | ESGF/Metagrid; algunos nodos piden OpenID | Términos CMIP6 (abierto) | **DOCUMENTED** |
| WorldClim 2.1 | 19 bioclimáticas + futuro CMIP6 | 30″ (~1 km), 2,5′, 5′, 10′ | Descarga directa | **No comercial, sin redistribución** | **DOCUMENTED** |
| GAEZ v4 (FAO/IIASA) | Aptitud y rendimiento potencial, RCP | 5′ (~9 km); 30″ selectivo | REST/WCS/WMS + TIFF | **No comercial, atribución** | **DOCUMENTED** |
| ERA5 | Reanálisis histórico | 0,25° | CDS, cuenta | CC BY 4.0 | **RESTRICTED** |
| AgERA5 | Reanálisis agrícola | 0,1° | CDS, cuenta | CC BY 4.0 | **RESTRICTED** |

**Nota de licencia:** WorldClim y GAEZ **no permiten redistribución**. Sus
derivados AGROSV pueden publicarse con atribución, pero los archivos originales
no se incorporan al repositorio ni se sirven desde la API.

---

## 2. Escenarios y periodos

| Escenario | Camino socioeconómico | Uso |
|---|---|---|
| SSP1-2.6 | sostenibilidad | límite inferior |
| SSP2-4.5 | intermedio | escenario central |
| SSP3-7.0 | regional rivalry | alto |
| SSP5-8.5 | fósil | límite superior |

Periodos: **2021–2040**, **2041–2060**, **2061–2080**, **2081–2100**, con
línea base 1991–2020 (misma que el motor climático).

**Regla:** no se publica un solo escenario. Todo resultado se muestra como
rango (mínimo–máximo entre escenarios y modelos) o como mapa de consenso.

---

## 3. Variables y derivados

| Variable | Cálculo | Uso |
|---|---|---|
| ΔT media/máx/mín | diferencia vs línea base | estrés térmico |
| ΔPrecipitación anual y estacional | diferencia y % | disponibilidad hídrica |
| Estacionalidad | inicio/fin de lluvias, canícula | calendario de siembra |
| Días > 35 °C | conteo | estrés reproductivo |
| Balance precip − ET₀ | acumulado | déficit hídrico |
| Zonas agroecológicas | desplazamiento por T y P | aptitud |
| Aptitud por cultivo | reglas o GAEZ | maíz, frijol, arroz, sorgo, café, cacao, hortalizas, frutales |

---

## 4. Método

1. **Downscaling**: WorldClim (1 km) como base; no se inventa una rejilla más
   fina. Si se requiere 30 m, es un producto derivado con su ADR.
2. **Corrección de sesgo**: WorldClim ya está corregido; si se usa CMIP6 directo,
   se documenta el método (delta o quantile mapping).
3. **Índices**: se calculan sobre la serie corregida, no sobre el GCM crudo.
4. **Aptitud**: se aplican umbrales por cultivo (documentados) o se usa GAEZ
   como referencia externa; nunca ambos mezclados en un mismo mapa.
5. **Consenso**: se reporta el acuerdo entre modelos (nº de modelos con el mismo
   signo de cambio).

---

## 5. Cultivos y umbrales (propuestos, a validar)

| Cultivo | T óptima | Límite térmico | Sensibilidad hídrica |
|---|---|---|---|
| Maíz | 24–30 °C | > 35 °C en floración | alta |
| Frijol | 18–24 °C | > 30 °C | alta |
| Arroz | 25–30 °C | > 35 °C | muy alta (riego) |
| Sorgo | 26–32 °C | tolerante | media |
| Café | 18–22 °C | > 24 °C pierde calidad | media |
| Cacao | 22–28 °C | > 32 °C | alta (sombra) |
| Hortalizas | variable | variable | alta |
| Frutales | variable | variable | media |

Estos umbrales provienen de literatura agronómica general; **no** están
calibrados para variedades salvadoreñas. Se publican como supuestos.

---

## 6. Interfaz

```
GET /api/climate/scenarios?crop=maiz&ssp=245&period=2041-2060
GET /api/climate/aptitude?crop=maiz&ssp=585&period=2081-2100&level=department
GET /api/climate/stress?variable=tmax_gt35&ssp=370&period=2041-2060
GET /api/climate/agroecological-shift?baseline=1991-2020&period=2041-2060
```

Cada respuesta declara `ssp`, `period`, `baseline`, `models_used`,
`agreement_pct`, `downscaling_method` y `limitations`.

---

## 7. Validación

| Prueba | Criterio |
|---|---|
| Coherencia | ΔT positivo en todos los SSP a largo plazo |
| Rango | ΔT dentro de lo publicado por IPCC AR6 para Centroamérica |
| Estacionalidad | la canícula no desaparece en el modelo sin justificación |
| Consenso | se informa el % de modelos de acuerdo |
| Reproducibilidad | misma versión de WorldClim/CMIP6 → mismo resultado |
| No mezcla | nunca se presenta una proyección como pronóstico |

---

## 8. Limitaciones

1. Resolución de 1 km: no describe una ladera ni una parcela.
2. Incertidumbre entre modelos mayor que la señal en precipitación.
3. Los umbrales de cultivo no están calibrados localmente.
4. GAEZ y WorldClim tienen licencias no comerciales: condicionan el uso del
   producto final.
5. Una proyección a 2050 no informa la siembra de este año.

---

## 9. Dependencias y prioridad

Depende de: motor climático histórico (Fase 1.5), Module C (simulación) para
traducir clima a rendimiento.

**Prioridad:** baja-media. Es científicamente atractivo pero costoso y con
licencias restrictivas; se implementa cuando exista una línea base validada y
un caso de uso concreto (p. ej. café en tierras altas).
