# SCIENTIFIC_VALIDATION.md — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Premisa:** un resultado sin incertidumbre no es un resultado, es una opinión con formato numérico.

---

## 1. Qué se valida y qué no se puede validar

| Componente | ¿Validable contra observación? | Cómo |
|---|---|---|
| Precipitación CHIRPS | ⚠️ Parcial — requiere estaciones | Contraste con red MARN/SNET (no verificada) |
| Temperatura / ET0 ERA5 | ⚠️ Parcial | Contraste con estaciones; ET0 contra tanque de evaporación |
| Elevación DEM | ✅ Sí | Contra puntos geodésicos CNR |
| Pendiente derivada | ✅ Sí | Contra curvas de nivel CNR |
| Suelo (SoilGrids) | ⚠️ Parcial | Contra mapa CENTA 1:50.000 y perfiles de campo |
| Rendimiento simulado (AquaCrop) | ✅ Sí, **agregado** | Contra rendimiento censal departamental BCR 2025 |
| Decisión económica de agente | ❌ **No** | No hay observación de decisiones individuales |
| Narrativa de agente (LLM) | ❌ **No aplica** | No es una afirmación factual |

**La distinción crítica:** el rendimiento se valida a escala **departamental**, porque es la resolución de la verdad de referencia. Validar a escala de parcela es imposible con los datos disponibles y no debe intentarse ni simularse.

---

## 2. Separación de clases de modelo (obligatoria y verificable)

### 2.1 Las cuatro clases

| Clase | Definición | Ejemplos en AGROSV | Requisito de validación |
|---|---|---|---|
| **Determinista** | Misma entrada → misma salida, sin aleatoriedad | AquaCrop, balance hídrico, pendiente, escorrentía | Reproducibilidad bit a bit; validación contra observación agregada |
| **Estadístico** | Inferencia con supuestos distribucionales | SPI/SPEI, frecuencias de extremos, regresiones | Bondad de ajuste; validación fuera de muestra |
| **Aprendizaje automático** | Aprende de datos | Clasificación de cobertura, downscaling | Validación cruzada espacial y temporal; métricas fuera de muestra |
| **Generativo** | Produce texto | Narrativa de agentes, redacción | **No produce cifras.** Se evalúa legibilidad y fidelidad a los hechos dados |

### 2.2 Regla de no mezcla

Un resultado publicado declara **una sola** clase dominante y su versión. No se presenta como "resultado del modelo" la combinación de un cálculo determinista con un texto generado sin distinguir qué parte es qué.

### 2.3 Aplicación técnica

- `simulation_run.modelo` ∈ {`deterministic`, `statistical`, `ml`, `generative`} — campo obligatorio.
- `tests/architecture/test_layer_isolation.py` falla si `agrosv.agents` importa `sqlalchemy` o `agrosv.simulation`.
- El `FactsBundle` que recibe el LLM es **de solo lectura** y lleva los `provenance_id` de cada cifra. El LLM no puede introducir un número que no esté en el bundle: un validador posterior compara todo número del texto generado contra el bundle y **rechaza** la salida si aparece una cifra no presente.

Ese último control es la defensa concreta contra "el modelo de lenguaje inventa resultados agronómicos".

---

## 3. Validación del componente climático

### 3.1 CHIRPS

| Métrica | Umbral de aceptación | Método |
|---|---|---|
| Sesgo relativo anual | |bias| < 20 % | vs. estaciones (si existen) o vs. ERA5-Land |
| r de Pearson mensual | r ≥ 0,80 | por departamento, 1991–2020 |
| Índice de eficiencia KGE | KGE ≥ 0,60 | serie mensual |
| Detección de días secos consecutivos | POD ≥ 0,70, FAR ≤ 0,30 | umbral 1 mm/día, escala pentadal |
| Estacionalidad | Máximo en jun–sep, mínimo en feb–mar | Inspección de climatología |

**Advertencia que debe acompañar todo resultado de CHIRPS diario:** el valor diario es una desagregación de un total pentadal. La incertidumbre del *total pentadal* es menor que la de su *reparto diario*. Por tanto:

- Los análisis de sequía se hacen a escala **pentadal o mensual**, no diaria.
- Los índices SPI a 3 y 6 meses son válidos; el SPI a 1 mes debe presentarse con reserva.
- Nunca se reporta un "día más lluvioso del año" como si fuera un dato observado.

### 3.2 ERA5-Land

| Métrica | Umbral |
|---|---|
| Sesgo de T media mensual | < 2 °C (esperado: sesgo frío en zonas altas) |
| Sesgo de ET0 mensual | < 25 % |
| r diaria de T | ≥ 0,85 |
| Corrección por altitud | Obligatoria por encima de 800 m, con lapse rate declarado (6,5 °C/km por defecto) |

El sesgo de altitud es **sistemático y conocido**: ERA5-Land representa la elevación media de su celda de 0,1° (~11 km), no la del punto. En un país con 2.700 m de desnivel en 11 km, ignorarlo produce errores de varios °C. La corrección entra como **supuesto explícito registrado**, no como ajuste silencioso.

### 3.3 Índices de sequía

- SPI y SPEI calculados con distribución gamma (SPI) y log-logística de 3 parámetros (SPEI).
- Período de referencia: **1991–2020** (30 años, estándar OMM).
- Ventanas: 3, 6, 12 meses.
- Validación: la frecuencia de eventos SPI < −1,5 debe aproximarse al 6,7 % teórico en el período de referencia; desviación > 3 puntos porcentuales indica mal ajuste.
- **Canícula:** detectada como el período de déficit hídrico relativo dentro de la estación lluviosa (jul–ago en El Salvador). El algoritmo debe ser explícito y reproducible, no un umbral ad hoc.

---

## 4. Validación del componente agronómico

### 4.1 Protocolo de validación de rendimiento

La única verdad de referencia disponible es el rendimiento departamental del censo 2025.

```
Para cada departamento d y cultivo c:
    rendimiento_obs[d,c]  ← BCR CAP 2025 (qq/mz → kg/ha, conversión explícita)
    rendimiento_sim[d,c]  ← media de AquaCrop sobre N unidades simuladas
                              ponderadas por superficie sembrada del censo
    error[d,c] = rendimiento_sim − rendimiento_obs
```

**Métricas:**

| Métrica | Fórmula | Umbral Fase 1 |
|---|---|---|
| rBias (sesgo relativo) | Σ(sim−obs)/Σobs | |rBias| ≤ 0,25 |
| RMSE | √(mean((sim−obs)²)) | Reportar; sin umbral fijo (depende del cultivo) |
| nRMSE | RMSE / mean(obs) | ≤ 0,30 |
| KGE | 1 − √((r−1)² + (α−1)² + (β−1)²) | ≥ 0,50 |
| r de Pearson entre departamentos | — | ≥ 0,60 |

**Interpretación honesta:** con 14 departamentos, r ≥ 0,60 ya es exigente. Un r bajo **no** invalida el modelo, pero sí obliga a declarar que el modelo no reproduce la variabilidad espacial observada y a no usarlo para comparar departamentos entre sí. Se puede seguir usando para escenarios *dentro* de un departamento, que es un uso distinto.

### 4.2 Protocolo de calibración (para no hacer trampa)

1. **Separación temporal:** calibrar con un ciclo, validar con otro. Nunca calibrar y validar con el mismo año.
2. **Separación espacial:** si se calibra con el rendimiento nacional, no se puede reportar un buen ajuste departamental como validación.
3. **Máximo de parámetros ajustados: 2.** Con 14 unidades de observación, ajustar más parámetros es sobreajuste garantizado.
4. **Registro del ajuste:** cada parámetro calibrado se guarda en `crop.params_aquacrop_json` con su valor por defecto FAO, el valor calibrado y la justificación.

### 4.3 Parámetros de AquaCrop: origen obligatorio

| Parámetro | Origen | Nunca |
|---|---|---|
| Textura (arcilla/limo/arena) | SoilGrids, 0–30 cm, cuantil Q0.5 | valor "típico" de libro |
| Capacidad de campo / punto de marchitez | `wv0033` / `wv1500` de SoilGrids | estimación del LLM |
| Profundidad efectiva | SoilGrids 0–100 cm o CENTA | asumir 100 cm sin declarar |
| ET0 | ERA5-Land / Open-Meteo | calcular a mano con fórmula propia no documentada |
| Fecha de siembra | Calendario del censo/MAG por departamento | inventar |
| Parámetros de cultivo (KC, HI, etc.) | Valores FAO AquaCrop documentados | valores "ajustados" sin registro |
| Coeficiente de respuesta al estrés | FAO AquaCrop | calibración anecdótica |

Todo parámetro con valor por defecto FAO debe llevar la referencia bibliográfica en el registro del run.

---

## 5. Regla de resolución: no se publica más precisión que la del insumo más grueso

Formalización:

```
resolucion_salida = min(resolucion_efectiva de todas las entradas)
```

| Escenario | Resolución de entrada más gruesa | Resolución máxima de salida |
|---|---|---|
| PAUP con SoilGrids + CHIRPS + ERA5 | CHIRPS pentadal, SoilGrids 250 m | Pixel 250 m, escala temporal pentadal |
| Riesgo de sequía departamental | Censo (departamental) + CHIRPS | Departamento |
| NDVI de parcela con Sentinel-2 | 10 m | 10 m, condicionado a nubosidad |

**Consecuencia que debe aparecer en la interfaz:** si el usuario dibuja una parcela de 0,5 ha, el sistema debe decirle **"los datos de suelo para este punto tienen 250 m de resolución (≈6,25 ha) y no representan tu parcela; representan el paisaje circundante"**. Ocultar eso es el error más grave que AGROSV puede cometer, porque produce confianza injustificada.

---

## 6. Cuantificación de incertidumbre

### 6.1 Fuentes de incertidumbre, jerarquizadas

| # | Fuente | Magnitud esperada | Tratamiento |
|---|---|---|---|
| 1 | Suelo (SoilGrids) | **Alta** — 90 % PI amplio en textura | Monte Carlo sobre Q0.05/Q0.5/Q0.95 |
| 2 | Clima (CHIRPS/ERA5) | **Alta** — sesgo sistemático y desagregación | Escenarios múltiples (`rnl` vs `sat`) + corrección declarada |
| 3 | Parámetros de cultivo | **Media** — valores FAO genéricos | Análisis de sensibilidad univariado |
| 4 | Fecha de siembra | **Media** — varía entre productores | Ventana de siembra, no una fecha |
| 5 | Modelo (estructura) | **Media** — AquaCrop simplifica | Declarar; no cuantificable con estos datos |
| 6 | Censo (verdad de referencia) | **Baja-media** — error de encuesta | Usar intervalos publicados si existen |

**La incertidumbre del modelo (5) no se puede cuantificar con los datos disponibles.** No se le asigna un número; se declara como no cuantificada. Fingir cuantificarla con un "±10 %" es peor que admitirlo.

### 6.2 Protocolo Monte Carlo

```
n = 500 muestras (Latin Hypercube)
Entradas muestreadas:
  · textura: distribución triangular con Q05/Q50/Q95 de SoilGrids por profundidad
  · capacidad de campo / PMP: ídem sobre wv0033 y wv1500
  · precipitación: variante rnl y sat, y ±20 % de sesgo sistemático
  · temperatura: ±1,5 °C (rango de sesgo ERA5-Land en zona alta)
  · fecha de siembra: ventana de ±15 días
Salida: distribución de rendimiento → P10, P50, P90
Semilla registrada en simulation_run.seed
```

**Por qué 500 y no 10.000:** con 8 GB de RAM y AquaCrop corriendo cientos de miles de celdas-día por iteración, 500 es el punto donde el error estándar del P10/P50/P90 es menor que la incertidumbre de entrada. Más muestras no mejoran la respuesta. Es una decisión por presupuesto computacional, y se documenta como tal.

### 6.3 Presentación obligatoria

Ningún rendimiento se publica como cifra única. Siempre:

```
Rendimiento mediano: 2.140 kg/ha
Rango P10–P90: 1.480 – 2.790 kg/ha
Incertidumbre dominante: suelo (textura) y precipitación
Resolución efectiva: pixel 250 m, escala pentadal
```

---

## 7. Validación de agentes sintéticos

**Los agentes sintéticos no son evidencia estadística y no se presentan como agricultores reales.**

### 7.1 Qué sí se puede validar

| Prueba | Método | Criterio |
|---|---|---|
| **Fidelidad marginal** | χ² entre distribución de agentes y censo, por departamento × ocupación | p > 0,05, o TVD < 0,10 |
| **Cobertura** | % de clases CIIU presentes en agentes vs. censo | ≥ 90 % de las clases con ≥10 productores |
| **Consistencia interna** | Edad ≥ 18, ocupación ∈ 119 clases, municipio ∈ 44, coherencia departamento↔municipio | 100 % |
| **Estabilidad** | Dos ejecuciones con la misma semilla → misma población | Idénticas |
| **Trazabilidad de dotaciones** | % de agentes con `dotacion_fuente` no nulo | 100 % |

### 7.2 Qué **no** se puede validar y por qué

| Aspecto | Por qué no |
|---|---|
| Comportamiento real de un agricultor | No hay observación de decisiones individuales |
| Ingreso, tamaño de finca | **No están en Nemotron.** Se asignan desde censo y es un supuesto |
| Correlación ocupación–educación | El editor asume independencia dado depto/edad/sexo |
| Identidad indígena / afrodescendiente | Declarada como subrepresentada por el editor |
| Español salvadoreño auténtico | Aproximado por el LLM, no extraído de corpus autorizado |

### 7.3 Etiquetado obligatorio

Todo registro derivado de Nemotron propaga `synthetic = TRUE`. Un test falla si una salida pública contiene un valor proveniente de `agent` sin la marca.

**Texto obligatorio junto a cualquier resultado de agentes:**

> Estos agentes son perfiles **sintéticos** generados por NVIDIA a partir de distribuciones censales. No corresponden a personas reales. Las variables económicas (tamaño de finca, acceso a agua, crédito) **no** provienen del perfil: fueron asignadas por AGROSV desde el censo y son supuestos declarados. Los resultados describen comportamientos simulados bajo reglas explícitas, no observaciones de agricultores salvadoreños.

### 7.4 El error que hay que evitar

Presentar "el 47 % de los agricultores sintéticos vendería su cosecha" como si fuera un hallazgo sobre El Salvador. Es un hallazgo sobre **las reglas de decisión que AGROSV escribió**. La distinción debe estar en el texto, no solo en una nota al pie.

---

## 8. Protocolo de reproducibilidad

Un resultado es válido solo si puede reproducirse. Requisitos para publicar:

```
[ ] simulation_run registra: modelo, modelo_version, seed, ts_inicio, ts_fin
[ ] Todos los provenance_id de entrada son resolubles
[ ] Los archivos de entrada existen y su sha256 coincide con el manifiesto
[ ] La versión de software está registrada (agrosv, gdal, aquacrop)
[ ] El entorno es reproducible (lockfile)
[ ] Los parámetros de cultivo están registrados con su origen
[ ] La incertidumbre está calculada y adjunta
```

**Prueba de reproducibilidad:** re-ejecutar con la misma semilla y mismo `modelo_version` debe producir una salida idéntica bit a bit para el modelo determinista. Para Monte Carlo, idéntica con la misma semilla y misma versión de generador aleatorio. Un test de CI lo verifica sobre un caso golden.

**Invalidación:** cualquier cambio de versión de dataset, de modelo o de parámetros **invalida** los resultados previos. No se "actualizan" en silencio: se re-ejecutan y se versionan. Un resultado antiguo sigue accesible con su etiqueta de versión.

---

## 9. Auditoría de procedencia (AGENTE 7)

Ejecución periódica, muestreo aleatorio:

```bash
agrosv audit provenance --sample 200
```

Verifica, para cada cifra muestreada:

1. `provenance_id` existe en la base.
2. Apunta a un `dataset_version` con manifiesto presente.
3. El archivo de origen existe y su `sha256` coincide.
4. La transformación declarada es la que efectivamente se aplicó (re-ejecución).
5. `resolucion_efectiva` es coherente con la fuente.

**Tasa de fallo aceptable: 0 %.** Cualquier fallo bloquea la publicación y abre incidencia.

---

## 10. Umbrales de publicación

Un resultado puede publicarse cuando:

| Requisito | Umbral |
|---|---|
| Procedencia resoluble | 100 % |
| Incertidumbre calculada | 100 % |
| Etiqueta sintética (si aplica) | 100 % |
| Validación de rendimiento | rBias ≤ 0,25 **y** KGE ≥ 0,50 |
| Advertencia de resolución efectiva | Presente en la respuesta |

Si la validación de rendimiento no alcanza el umbral, el resultado **puede** publicarse con la etiqueta **"NO VALIDADO — uso exploratorio"** y sin comparaciones entre departamentos. No se publica como si estuviera validado.

---

## 11. Validación de la ampliación (2026-11-21)

Se añaden cuatro dominios de validación. Las reglas de §1–§10 siguen vigentes:
nada se publica sin fuente, incertidumbre y clase de modelo.

### 11.1 Datos censales y tabulares

| Prueba | Criterio | Si falla |
|---|---|---|
| Cuadre vertical | ∑ departamentos = nacional (± redondeo documentado) | No se publica la serie |
| Cuadre horizontal | ∑ categorías = total de tabla | Se revisa la extracción |
| Geografía | todo código existe en `dim_geography` | Se bloquea la carga |
| Confidencialidad | ninguna celda < 10 unidades | Se agrupa o se suprime |
| Unidades | manzanas ≠ hectáreas ≠ quintales, declaradas | Se bloquea |
| Preliminar vs final | campo `delivery`/`quality` presente | Se marca o no entra |

Contraste obligatorio: superficie de un cultivo (CAP 2025) vs anuario MAG del
mismo año. Una diferencia > 20 % se documenta; no se promedia para «cuadrar».

### 11.2 Amenazas naturales

| Prueba | Criterio |
|---|---|
| Metadatos completos | `layer_type`, `method`, `scale`, año, `confidence` |
| Coherencia física | clase alta de deslizamiento concentra pendiente > 25° (asociación, no prueba) |
| Observación vs amenaza | una observación nunca se rotula como predicción ni al revés |
| Vectorización | conserva referencia de página/figura del PDF original |
| Escala | no se permite zoom mayor que 2× la escala nominal sin aviso |

Una capa de amenaza **no se valida** contra un evento: se valida su coherencia
interna y se declara que no ha sido evaluada con inventario de eventos.

### 11.3 Clima y grillas

| Prueba | Criterio |
|---|---|
| Rango físico | precipitación ≥ 0; HR 0–100 %; T −5…45 °C |
| Cobertura | declarada = medida; si < 80 % → `partial: true` |
| Resolución | `native_resolution` presente en toda respuesta |
| Contraste CHIRPS vs AgERA5 | correlación mensual; diferencias > 30 % se investigan |
| Índices | línea base declarada (1991–2020) y unidad |
| Estaciones | **bloqueada**: sin datos MARN/SNET no hay validación local |

### 11.4 Agricultura multiescala

Se adopta el protocolo CEOS/WGCV: muestreo probabilístico, etiquetas
independientes del mapa, matriz de confusión, exactitud global y por clase,
estimación de área con intervalos.

| Nivel | Validación mínima |
|---|---|
| L0 vegetación | ninguna (no se publica como agricultura) |
| L1 candidato | revisión por dos analistas; κ ≥ 0,6 |
| L2 probable | contraste con ortofoto/cartografía; κ ≥ 0,7 |
| L3 verificado | campo ≥ 30 sitios/municipio; exactitud global ≥ 0,85 |

Sin matriz de confusión no hay L3, y sin L3 no hay cifras de superficie
publicadas como «superficie agrícola AGROSV».

### 11.5 Agentes sintéticos ampliados

Los perfiles Nemotron se estratifican por contexto (rural, periurbano, urbano),
tipo de productor y nivel de recursos. Se validan solo por:

1. **Plausibilidad frente a agregados censales** (distribución por sexo, edad,
   ocupación), nunca individuo a individuo.
2. **Consistencia interna** de dotaciones y decisiones.
3. **Contraste cualitativo con agricultores reales** (entrevistas), registrado
   como evidencia, no como calibración estadística.

Prohibido: presentar un perfil sintético como «agricultor típico» del país sin
intervalo y sin advertir que es sintético.

---

## 12. Validación de Fase 2 (2026-11-21)

El protocolo detallado está en `docs/SCIENTIFIC_VALIDATION_PROTOCOL.md`. Aquí se
resume lo que cambia respecto de §1–§11.

### 12.1 Niveles de madurez

| Nivel | Significado |
|---|---|
| V0 | implementado, corre |
| V1 | verificado con pruebas |
| V2 | contrastado con fuente independiente |
| V3 | validado en datos no vistos |
| V4 | operativo con revalidación |

**Estado real hoy:** Fase 1 en V1 (80 pruebas); todos los módulos de Fase 2 en
V0 o por debajo. Ninguno es V2.

### 12.2 Qué se puede contrastar y qué no

| Variable | Contraste posible | Validación real |
|---|---|---|
| Precipitación | CHIRPS vs IMERG vs ERA5 | **no** (sin estaciones) |
| Temperatura | AgERA5 vs ERA5 | **no** (sin estaciones) |
| NDVI | MODIS vs Sentinel-2 | sí (productos distintos) |
| Cobertura | fotointerpretación propia | pendiente |
| Rendimiento | censos agregados | **no** (microdatos cerrados) |
| Plagas | reportes OIRSA/ISC | parcial, cualitativa |
| Caudal | aforos MARN | **no** disponibles |

Llamar «validación» al contraste entre productos satelitales es incorrecto: es
**consistencia**. Se etiqueta así en la API.

### 12.3 Reglas nuevas

- **V-11** Ningún módulo se declara V2+ sin fila en `validation_run`.
- **V-12** Los umbrales de validación son propuestos y se justifican por escrito.
- **V-13** Un resultado sin observación independiente se etiqueta `unvalidated`.
- **V-14** La validación se repite cuando cambia el modelo o la fuente.
- **V-15** Los agentes sintéticos no se validan estadísticamente contra personas.

### 12.4 Deuda de validación reconocida

Sin estaciones de superficie, sin microdatos censales y sin aforos, AGROSV no
puede validar clima, rendimiento ni hidrología contra observación. Es la
limitación científica más importante del proyecto y no se resuelve con código.
