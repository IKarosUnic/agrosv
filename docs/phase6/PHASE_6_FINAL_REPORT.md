# AGROSV — Informe final de Fase 6

**Inteligencia agrícola, socio-agrícola y Nemotron**
Fecha: 2026-11-22 · Versión de motores: 6.0.0

## 1. Resumen

Fase 6 añade tres subsistemas independientes pero interoperables:

* **A. Inteligencia agrícola** — 6 motores sobre el catálogo de cultivos, la
  fenología térmica, la aptitud, el agua y los nutrientes, la simulación por
  adaptadores y el calendario derivado.
* **B. Inteligencia socio-agrícola sintética** — 8 motores de población,
  persona, hogar, comportamiento, economía, adopción, resiliencia y
  multiagente, con gobernanza de cinco capas.
* **C. Simulación integrada** — 4 motores de integración, decisión, escenarios
  A–G y análisis.

Se añadieron 34 endpoints nuevos bajo `/api/agriculture`, `/api/social` y
`/api/socio`, 96 pruebas y 25 documentos. Las 373 pruebas de Fase 1–5 siguen
pasando.

La conclusión científica es deliberadamente austera: **no hay calibración ni
validación local**. Lo que existe es infraestructura reproducible, con
procedencia y con vacíos declarados.

## 2. Completamente implementado

### Agrícola

1. Catálogo de 22 cultivos con estado por parámetro (`REF`, `NAC`, `GAP`),
   búsqueda, comparación y auditoría de vacíos.
2. Fenología por GDD con etapas, series incompletas y objetivo derivado
   marcado `MODEL_DERIVED`.
3. Aptitud S1/S2/S3/N/`not_evaluated` por factores limitantes, con ventana de
   5 meses y sistemas secano/riego/urbano/periurbano.
4. Balance hídrico FAO-56 (TAW, RAW, Ks, ETa, percolación, estrés) y
   programación de riego.
5. Demanda de nutrientes por remoción, con rechazo explícito de dosis.
6. Simulación con un adaptador ejecutable y tres externos detectados pero
   rechazados.
7. Calendario derivado con ventanas, riesgos por etapa y clasificación de la
   información.

### Social

8. Población sintética de 10 arquetipos, reproducible por semilla, con límite
   de tamaño y declaración de no representatividad.
9. Persona con dos orígenes explícitos y rechazo de reasignación de rol.
10. Hogar con composición, trabajo, presupuesto e ingresos por proporción.
11. Comportamiento MAUT con restricciones duras y aprendizaje acotado.
12. Economía que exige fuente, fecha, moneda y unidad; sin precios no ejecuta.
13. Adopción con 9 tecnologías y barreras duras/blandas.
14. Resiliencia con 8 choques, exposición, capacidad e impacto.
15. Multiagente con red reproducible, difusión y choque común.
16. Gobernanza de capas con verificación automática.

### Integrado

17. Perfil que separa bloque científico y humano, sin LLM.
18. Decisión que excluye cultivos no evaluables y respeta capital, agua y
    trabajo.
19. Siete escenarios ejecutables con sobrescrituras declaradas.
20. Comparación, restricciones y hallazgos marcados como simulación.

## 3. Parcialmente implementado

| Componente | Qué falta |
|---|---|
| Aptitud | profundidad, salinidad, textura preferente y nutrientes no existen; urbano no evaluable |
| Simulación | solo balance hídrico; sin biomasa, N ni crecimiento |
| Calendario | sin práctica histórica, recomendación oficial ni pronóstico |
| Economía | sin precios ni costos por defecto; todo depende del usuario |
| Persona | perfil sintético compatible, no una fila Nemotron agrícola |
| Adopción/resiliencia | índices cualitativos, sin curvas ni datos de pérdidas |
| Multiagente | sin mercado, instituciones ni des-adopción |
| Decisión | el generador por defecto solo crea opciones de cultivo; variedad, riego, fertilizante y mercado requieren opciones aportadas por el usuario |
| Simulación | sin prácticas de manejo, nutrición ni fertilización |

## 4. Planificado, no implementado

* Adaptador de interoperabilidad con Saltbor.
* Integración ejecutable de AquaCrop-OSPy, PCSE o DSSAT.
* Calibración varietal y de Kc con ensayos locales.
* Capa de acceso a riego, agua subterránea y caudales.
* Pronóstico climático estacional.
* Precios y costos oficiales en formato reutilizable.
* Datos de agricultura urbana (espacio, luz, sustrato).
* Microdatos del CAP 2025 para calibrar arquetipos.
* Validación con encuestas de intención y adopción.

## 5. Datasets reales integrados

| Dataset | Uso en Fase 6 | Clase |
|---|---|---|
| Open-Meteo reanálisis 2019–2025 | ET0, P, Tmax/Tmin | reanálisis |
| NASA POWER | respaldo de temperatura | reanálisis |
| SoilGrids 2.0 (0–30 cm) | pH y textura | predicción modelada |
| Copernicus DEM GLO-30 | pendiente y elevación | observación derivada |
| CAP 2025 (agregados) | 2,4 t/ha de maíz | estadística oficial |
| Nemotron-Personas-SV (esquema y 3 filas) | perfil de origen | sintético |
| Catálogo de parámetros AGROSV | rangos REF | referencia |

No se integraron datos nuevos de estaciones, censos microdata, precios,
caudales ni suelos nacionales.

## 6. Datos sintéticos generados

Poblaciones de arquetipos, perfiles compatibles, hogares, decisiones,
aprendizaje, adopción, impacto de choques y difusión multiagente. Todos llevan
`synthetic: true`, `represents_real_people: false`,
`population_inference_allowed: false`, método, supuestos y
`validation_status: not_validated`.

## 7. Repositorios externos evaluados

`aquacropos/aquacrop`, `gicait/PyAEZ`, `DSSAT/dssat-csm-os`,
`ajwdewit/pcse` e `IKarosUnic/sv-people`. Ninguno fue clonado, vendorizado ni
fusionado. Detalle en `EXTERNAL_MODEL_EVALUATION.md`.

## 8. Modelos probados

* Balance FAO-56 propio: probado con series sintéticas y reanálisis.
* Fenología GDD: probada con clima constante y series truncadas.
* Reglas de aptitud: probadas con y sin datos críticos.
* MAUT, adopción y difusión: probados en reproducibilidad y restricciones.

No se ejecutaron AquaCrop, PCSE, DSSAT ni PyAEZ.

## 9. Modelos calibrados

**Ninguno.** No hay coeficientes varietales, Kc local ni parámetros de suelo
calibrados.

## 10. Modelos validados científicamente

**Ninguno.** La validación fue de software y de fuentes. No se comparó con
rendimientos, humedad de suelo ni decisiones observadas.

## 11. Validación socioeconómica

**No realizada.** Solo se verificó que los agregados del CAP citados existen y
que Nemotron no contiene variables agrícolas. No hay microdatos, encuesta de
hogares ni precios tabulares. Detalle y protocolo en
`SOCIO_AGRICULTURAL_VALIDATION.md`.

## 12. Limitaciones conocidas

1. Clima de un punto de reanálisis; no se interpola.
2. Suelo 0–30 cm, sin AWC, CEC, densidad ni salinidad.
3. El pH puede ser NoData y entonces no se clasifica.
4. La ventana de 5 meses es una convención, no un calendario.
5. Kc = 1,0 no describe un cultivo.
6. El rendimiento nacional no es un potencial.
7. Los arquetipos son tipos, no una distribución.
8. La red multiagente es artificial.
9. Los escenarios no son pronósticos.
10. No hay validación agronómica ni socioeconómica.

## 13. Rendimiento medido

| Operación | Mediana | Memoria |
|---|---|---|
| población 5.000 | 2,575 s | 11,49 MB |
| multiagente 1.000 × 10 pasos | 0,113 s | 1,07 MB |
| aptitud (café) | 0,133 s | 12,21 MB |
| fenología | 0,028 s | 2,53 MB |
| balance hídrico | 0,026 s | 2,10 MB |
| escenario 50 agentes | 3,207 s | 2,54 MB |

`docs/phase6/benchmark_phase6.json`; reproducible con
`scripts/10_phase6_benchmark.py`. No es un SLA.

## 14. Compatibilidad

Las 373 pruebas de Fase 1–5 pasan sin cambios. Los routers nuevos usan prefijos
nuevos; no se modificó ningún contrato anterior. `/api/engines/meta` sigue
respondiendo.

## 15. Pruebas

469 pruebas, 0 fallos, 0 omitidas (~36 s). 96 nuevas de Fase 6. Detalle en
`PHASE_6_TESTING_REPORT.md`.

## 16. Documentación

25 documentos en `docs/phase6/`: 6 agrícolas, 12 de Nemotron/social, 4 de
integración/validación, evaluación externa, informe de pruebas y este informe.

## 17. Prioridades para Fase 7

### 17.1 Datos externos (acceso implementado; cinco fuentes aún no adquiridas)

Fase 7 añadió el registro, los validadores y la correspondencia municipal
2023. **No** se descargaron series, muestras, cuencas, aforos ni puntos GNSS.
Detalle en `docs/phase7/DATA_ACCESS_AND_ONBOARDING.md`.

| Dataset | Estado | Qué falta para integrarlo |
|---|---|---|
| SNET/MARN series diarias | por solicitud | CSV largo validado; diccionario y licencia |
| CENTA Laboratorio de Suelos | restringido | convenio y microdatos anonimizados |
| Cuencas oficiales MARN | sin capa confirmada | GeoJSON/GPKG con códigos oficiales |
| Aforos y caudales MARN | por solicitud | caudal diario y curva de gasto |
| Correspondencia 2023 | **adquirida** | nada: 14/44/262 verificados |
| GNSS/CNR | arancelado | puntos con altura ortométrica y exactitud |

### 17.2 Prioridades

1. **Datos antes que modelos**: microdatos o tabulados municipales del CAP
   2025; precios y costos en formato reutilizable.
2. **Calibrar Kc, ciclos y coeficientes varietales** con CENTA/MAG o ensayos.
3. **AWC y profundidad de suelo** a partir de textura, densidad y perfiles.
4. **Validar aptitud** contra producción observada y mapas oficiales.
5. **Evaluar AquaCrop-OSPy** como primer adaptador externo, solo con
   parámetros locales.
6. **Adaptador Saltbor** con contrato de eventos y pruebas aisladas.
7. **Datos urbanos** de espacio, agua y luz.
8. **Pronóstico climático** con incertidumbre y verificación.
9. **Validación socioeconómica** con encuestas de intención y adopción.
10. **Interfaz de exploración** solo después de estabilizar datos y métodos.

## 18. Principio final

La fase entrega menos de lo que podría prometer y declara más de lo que falta.
Esa es la decisión correcta: un territorio que puede producir algo no autoriza a
inventar cuánto, ni a fingir que una persona sintética representa a un
productor real. La integridad científica precede a la cantidad de funciones.
