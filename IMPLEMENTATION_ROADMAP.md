# IMPLEMENTATION_ROADMAP.md — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Regla:** ninguna fase arranca sin criterios de aceptación cumplidos. No se avanza "para no bloquear".

---

## 0. Estrategia general

**Un departamento piloto, vertical completo, antes que 14 departamentos a medias.**

Piloto recomendado: **Ahuachapán**.
Motivos: mayor concentración de maíz del país (12,3 %), frontera con Guatemala (valida el corte de bbox), rango altitudinal amplio (0–2.400 m) que prueba la corrección por altitud, y es el departamento más occidental del país, lo que prueba el cálculo de UTM.

Segundo: **La Libertad** (8,7 % del maíz, incluye la capital y costa). Tercero: **Santa Ana** (10,6 %, relieve volcánico).
Los 14 departamentos se completan cuando el piloto pasa validación, no antes.

---

## 1. Mapa de fases

```
FASE 0   Investigación y arquitectura       ← completada
FASE 1   Cimientos + PAUP                  6-12 semanas  ← fundación implementada
FASE 1.5 Censos + hub MAG + clima         4-6 semanas   (§12, bloques 1–3)
FASE 2   Agentes y economía                4-6 semanas
FASE 2.5 Geomorfología + amenazas         4-6 semanas   (§12, bloques 4–5, en paralelo)
FASE 3   Escenarios y validación plena     6-8 semanas
FASE 3.5 Agricultura multiescala L1/L2     6-8 semanas   (§12, bloques 6–7, en paralelo)
FASE 4   Cobertura nacional                4 semanas
FASE 5   Extensión (café, caña, SAR)       por decidir
```

---

## 2. FASE 0 — Investigación y arquitectura

**Estado: entregada. Pendiente de revisión humana.**

| Entregable | Estado |
|---|---|
| `PROJECT_VISION.md` | ✅ |
| `DATA_SOURCE_REGISTRY.md` con estados verificados y evidencia | ✅ 21 fuentes, evidencia de sondeo |
| `SYSTEM_ARCHITECTURE.md` con justificación por dependencia | ✅ |
| `AGENT_ROLES.md` con propiedad de escritura exclusiva | ✅ |
| `DATA_PIPELINE.md` | ✅ |
| `SCIENTIFIC_VALIDATION.md` | ✅ |
| `IMPLEMENTATION_ROADMAP.md` | ✅ |
| `RISKS_AND_LIMITATIONS.md` | ✅ |
| `research/probe_sources.sh` reproducible | ✅ |

**Criterio de aceptación de Fase 0:** revisión humana aprobada. Sin ella no se escribe código de producción.

**Decisión bloqueante previa a Fase 1:** obtener o descartar acceso a observaciones meteorológicas de superficie de El Salvador (MARN/SNET). Si no hay estaciones, la validación climática se limita a contraste entre productos satelitales, y eso debe aceptarse formalmente antes de empezar, no descubrirse en la semana 10.

---

## 3. FASE 1 — Cimientos y primer módulo funcional (6–12 semanas)

### 3.1 Semanas 1–2 — Infraestructura (AGENTE 1, en solitario)

| Tarea | Criterio de aceptación |
|---|---|
| `registry.yaml` con las 21 fuentes del registro | Cada `source_id` del registro presente con estado y licencia |
| Esquema PostGIS + migraciones Alembic | `alembic upgrade head` en base limpia sin error |
| Contratos Pydantic (`Provenance`, `Manifest`, `PAUPResult`) | Validadores rechazan respuesta sin `provenance` ni `uncertainty` |
| CLI `agrosv` con `--dry-run` | `agrosv --help` lista ingest/build/sim/audit |
| CI: lint, tipos, tests | Pipeline verde en un PR vacío |
| Docker Compose con PostGIS | `docker compose up` levanta db + api |

**Gate:** nadie más escribe código hasta que esto esté verde.

### 3.2 Semanas 2–5 — Datos (AGENTES 2, 3, 4 en paralelo)

Cada uno en su módulo, sin tocarse.

**AGENTE 2 — Geoespacial**

| Tarea | Criterio de aceptación |
|---|---|
| Ingesta Copernicus DEM GLO-30 vía AWS | Tiles de El Salvador completos, `sha256` en manifiesto |
| Derivación pendiente/orientación | Pendiente media de Ahuachapán > pendiente media de la planicie costera |
| Escorrentía (dirección de flujo + acumulación) | Ríos principales coinciden visualmente con hidrografía OSM |
| Límites administrativos + tabla 2023↔distritos | Join agentes↔censo funciona sin huérfanos |
| SoilGrids vía WebDAV, 9 propiedades × 6 profundidades | `wv0033`/`wv1500` recortados y en unidades convencionales |
| OSM en esquema separado | `landuse=farmland` presente pero **documentado como no representativo** |
| Índice Sentinel-2 + NDVI por ventana | NDVI de un polígono de prueba calculado sin descargar escena completa |

**AGENTE 3 — Estadística agrícola**

| Tarea | Criterio de aceptación |
|---|---|
| Extraer tablas del CAP 2025 (BCR) | Suma departamental = total nacional dentro del redondeo |
| Serie de costos de producción (MAG) | Cada cifra rastrea a página del PDF |
| Documento MAG vs BCR | Discrepancias listadas, no resueltas en silencio |
| `price_series` y `cost_structure` | Con `provenance_id` por registro |
| Registro de licencias | Toda fuente con licencia declarada o marcada `RESTRICTED` |

**AGENTE 4 — Climático**

| Tarea | Criterio de aceptación |
|---|---|
| CHIRPS v3 `rnl` 1981–2025 recortado a SV | ~40 MB, sin huecos, `resolucion_efectiva=daily-disaggregated-from-pentad` |
| ERA5-Land vía CDS u Open-Meteo | T, ET0, precipitación, humedad de suelo, 1950–presente |
| Climatología 1991–2020 | Anual 1.700–2.400 mm con estación seca nov–abr |
| SPI/SPEI 3, 6, 12 meses | Frecuencia de SPI<−1,5 ≈ 6,7 % ± 3 pp |
| Corrección por altitud documentada | Lapse rate declarado en metadatos |
| Contraste CHIRPS vs ERA5-Land | r mensual por departamento reportado |

**Gate de la semana 5:** los tres módulos entregan contratos con datos reales de **Ahuachapán**. AGENTE 6 no arranca si falta uno. No se simula con datos inventados.

**AGENTE 7 — primera auditoría (semana 6)**
Auditoría de procedencia sobre los datos crudos. Tasa de fallo objetivo: 0 %.

### 3.3 Semanas 7–10 — PAUP (AGENTE 6)

Construcción en el orden de dependencia del motor (§4).

| Semana | Componente | Criterio de aceptación |
|---|---|---|
| 7 | Balance hídrico diario | Cierra el balance anual (P − ET − escorrentía − Δalmacenamiento ≈ 0) |
| 7 | Driver AquaCrop 7.3 | Corre con parámetros FAO por defecto para maíz sin error |
| 8 | Suelo desde SoilGrids | Propiedades hidráulicas derivadas de textura; comparadas con `wv0033`/`wv1500` |
| 8 | Estrés térmico | Detecta días con T > umbral de cultivo, documentado |
| 9 | Escenarios climáticos | Sequía, retraso de siembra, exceso de lluvia |
| 9 | Monte Carlo P10/P50/P90 | Semilla registrada; reproducible |
| 10 | Validación departamental | rBias y KGE contra CAP 2025 |

**Gate:** caso PAUP completo sobre un polígono de Ahuachapán en **< 60 s**, con procedencia, incertidumbre y reproducible bit a bit.

### 3.4 Semanas 11–12 — Cierre

| Tarea | Responsable |
|---|---|
| Validación completa | AGENTE 7 |
| Informe de validación | AGENTE 7 |
| Empaquetado y documentación de despliegue | AGENTE 1 |
| Revisión de aceptación de Fase 1 | Humano |

---

## 4. El motor de simulación: 8 módulos en orden de dependencia

Este es el corazón del sistema. Los módulos **no** son intercambiables en orden: cada uno consume la salida del anterior.

```
M1 Simulación de agricultores ─────────────┐
   (población de agentes, dotaciones)      │
                                            ▼
M2 Simulación de cultivos ──────────▶ M4 Balance hídrico
   (AquaCrop: fenología, biomasa)      (entrada/salida, estrés)
                                            │
M3 Modelado del suelo ──────────────────────┤
   (textura, agua disponible, PAW)          ▼
                                     M5 Estrés térmico
                                            │
                                            ▼
                                     M6 Escenarios climáticos
                                            │
                                            ▼
                                     M7 Análisis económico
                                            │
                                            ▼
                                     M8 Evaluación de riesgos
```

| Módulo | Clase de modelo | Entradas | Salidas | Fase |
|---|---|---|---|---|
| **M1** Agricultores | Generativo (texto) + reglas deterministas | Nemotron + dotaciones censales | Población, decisiones, narrativa | 2 |
| **M2** Cultivos | Determinista | Clima, suelo, manejo | Biomasa, rendimiento, fenología | 1 |
| **M3** Suelo | Determinista (pedotransferencia) | Textura, MO | Agua disponible, conductividad | 1 |
| **M4** Balance hídrico | Determinista | P, ET0, suelo, cultivo | Estrés hídrico, drenaje, riego | 1 |
| **M5** Estrés térmico | Determinista | T max/min, etapa fenológica | Índice de estrés, pérdida | 1 |
| **M6** Escenarios climáticos | Estadístico + determinista | Series históricas, deltas | Series sintéticas de escenario | 1–3 |
| **M7** Económico | Determinista + estadístico | Rendimiento, precios, costos | Ingreso, margen, pérdida | 2 |
| **M8** Riesgos | Estadístico | Distribuciones de salida | P(pérdida), VaR, mapas de riesgo | 3 |

**Separación estricta:** M1 es el único con componente generativo, y su parte generativa **no produce números**. M2–M8 son numéricos y auditables. M1 nunca alimenta M2–M8 con cifras: alimenta con *parámetros de decisión* (qué siembra, cuándo, cuánto riega), que son datos categóricos o numéricos provenientes de reglas explícitas, no del LLM.

---

## 5. FASE 2 — Agentes y economía (4–6 semanas)

**Requisito de entrada:** Fase 1 validada.

| Tarea | Responsable | Criterio de aceptación |
|---|---|---|
| Ingesta Nemotron anclada al `sha` | 5 | 148.000 filas, 25 columnas, hash verificado |
| Filtrado agrícola (div. 01) | 5 | 17.957 perfiles identificados |
| Esquema de dotaciones | 5 + 3 | 100 % con `dotacion_fuente`; 0 % inventado |
| Análisis de representatividad | 5 + 7 | χ² por depto×ocupación documentado |
| Reglas de decisión | 5 + 6 | Reglas explícitas, sin LLM, con semilla |
| Módulo económico M7 | 6 | Margen reproducible desde rendimiento + precio + costo |
| `FactsBundle` + validador de números | 1 + 5 | Test rechaza texto con cifra ausente del bundle |
| Aislamiento de capas | 7 | `agents` no importa `sqlalchemy` |

**Gate:** una corrida de 1.000 agentes de Ahuachapán produce decisiones y márgenes reproducibles, con etiqueta sintética en el 100 % de las salidas.

---

## 6. FASE 3 — Escenarios y validación plena (6–8 semanas)

| Tarea | Criterio de aceptación |
|---|---|
| Escenarios M6: sequía, canícula tardía, exceso, +2 °C | Cada escenario reproducible desde su especificación |
| Módulo de riesgos M8 | P(pérdida) y VaR con intervalo |
| Análisis de sensibilidad | Qué entrada domina la incertidumbre, por departamento |
| Validación multi-cultivo | maíz, frijol, maicillo, arroz |
| Validación multi-departamento | Ahuachapán + La Libertad + Santa Ana |
| Informe de validación publicado | Con umbrales de `SCIENTIFIC_VALIDATION.md` §10 |
| Revisión de pares interna | Aprobación de AGENTE 7 y del responsable humano |

**Gate:** validación de rendimiento con rBias ≤ 0,25 y KGE ≥ 0,50 en al menos 2 departamentos y 2 cultivos. Si no se alcanza, se publica como "NO VALIDADO — uso exploratorio" y se documenta por qué.

---

## 7. FASE 4 — Cobertura nacional (4 semanas)

Escalar de 3 a 14 departamentos no es trabajo nuevo: es ejecutar el mismo pipeline con otro bbox. El criterio de que la arquitectura sea correcta es que esta fase sea **aburrida**.

| Tarea | Criterio de aceptación |
|---|---|
| Ingesta nacional completa | ~1,2 GB, sin huecos |
| 14 departamentos × 4 cultivos | Todas las combinaciones con resultado |
| Rendimiento del pipeline | Nacional completo en < 24 h en un equipo de 16 GB |
| Verificación de escalado | Ningún cambio de código, solo configuración |

---

## 8. FASE 5 — Extensión (sin fechar)

Solo con decisión explícita y recursos:

- **Café** — requiere modelo perenne multi-anual; Nemotron tiene 1.950 perfiles en CIIU 0127; el censo publica producción de café oct-2023/sep-2024.
- **Caña de azúcar** — 669 perfiles; requiere modelo de ciclo largo.
- **Sentinel-1 SAR** — rompería la limitación de nubosidad en estación lluviosa. Es la extensión de mayor valor científico.
- **DSSAT** — solo si CENTA aporta ensayos para calibrar coeficientes genéticos.
- **Centroamérica** — el diseño lo permite; el trabajo es de licencias y datos, no de código.

---

## 9. Criterios de aceptación transversales

Aplican a toda fase, no solo al final:

| # | Criterio | Verificación |
|---|---|---|
| 1 | 100 % de cifras publicadas con `provenance_id` resoluble | `agrosv audit provenance` |
| 2 | 100 % de resultados con incertidumbre | Validador Pydantic |
| 3 | 100 % de salidas de agentes con `synthetic=TRUE` | Test de contrato |
| 4 | 0 % de números generados por LLM | Validador de `FactsBundle` |
| 5 | Reproducibilidad bit a bit del determinista | Test golden en CI |
| 6 | `resolucion_efectiva` declarada en toda capa | Validador de esquema |
| 7 | Cero tests desactivados sin justificación escrita | Revisión de AGENTE 7 |
| 8 | Cero datos inventados para desbloquear | Revisión de AGENTE 7 |

---

## 10. Qué se puede implementar inmediatamente (semana 1, sin bloqueos)

Estas tareas no dependen de ninguna gestión institucional ni credencial:

1. `registry.yaml` con las 21 fuentes verificadas de esta entrega.
2. Esquema PostGIS con tablas de procedencia.
3. Ingesta de **Copernicus DEM GLO-30** desde AWS (sin credenciales, verificado).
4. Ingesta de **CHIRPS v3 `rnl`** (sin credenciales, verificado).
5. Ingesta de **SoilGrids por WebDAV** (sin credenciales, verificado).
6. Ingesta de **OSM/Geofabrik** (sin credenciales, verificado).
7. Índice **Sentinel-2 por STAC** (sin credenciales, verificado).
8. Ingesta de **Nemotron** (sin gate, CC BY 4.0, verificado).
9. Cálculo de pendiente y escorrentía sobre DEM.
10. Contraste CHIRPS vs. Open-Meteo sin clave.

**Total de bloqueos para estas 10 tareas: cero.**

Bloqueadas a la espera de terceros: ERA5 vía CDS (token propio), CDSE/Sentinel Hub (cuenta), microdatos BCR/CENTA (permiso), estaciones MARN (no verificado que exista servicio).

---

## 11. Riesgo de cronograma y su causa más probable

La causa más probable de retraso **no es técnica**. Es la dependencia de permisos institucionales para datos del BCR y CENTA (ver `RISKS_AND_LIMITATIONS.md` §6).

Mitigación: Fase 1 se construye **enteramente con datos abiertos** (DEM, SoilGrids, CHIRPS, ERA5, Nemotron). Los datos nacionales entran como validación y mejora, no como requisito de arranque. Así el proyecto produce valor mientras la gestión institucional avanza, en lugar de esperar.

---

## 12. Roadmap ampliado y orden de implementación (2026-11-21)

Esta sección **añade** fases al mapa de §1. No elimina ni reordena lo aprobado:
Fase 1 (fundación geoespacial) ya está implementada y verificada; lo que sigue
se encadena después.

### 12.1 Orden propuesto

| Orden | Bloque | Por qué en este lugar | Depende de | Coste |
|---|---|---|---|---|
| 1 | **CPV 2024 + CAP 2025 (agregados)** | Datos públicos hoy, sin licencia pendiente; dan denominadores y estructura productiva | Nada | $0 |
| 2 | **Clima histórico: CHIRPS v3 + AgERA5** | Base de todo análisis agrícola; CHIRPS ya verificado; AgERA5 solo requiere cuenta CDS | Nada | $0 |
| 3 | **Hub agrícola MAG** (anuarios, precios, costos) | Series de contraste para validar clima y censos; extracción por cultivo piloto | 1 | Bajo (parseo) |
| 4 | **Geomorfología derivada del DEM** (unidades de relieve, cuencas validadas) | No depende de terceros; mejora la lectura territorial | Fase 1 | $0 |
| 5 | **Amenazas: un piloto vectorizado** (deslizamientos 1:50.000 o erosión 2015) | Aporta riesgo con costo bajo, declarando método y escala | 4 | Bajo |
| 6 | **Agricultura multiescala L1/L2** en Ahuachapán | Requiere clima (2), censos (1) y DEM (4) para contexto | 1, 2, 4 | Bajo (Sentinel-2) |
| 7 | **Agentes ampliados** (rural/urbano/periurbano, recursos) | Necesita censos (1) y contexto territorial (4–6) | 1, 6 | $0 |
| 8 | **CENTA MDS** | Suelo medido: el mayor salto de calidad; requiere convenio | Acuerdo institucional | Convenio |
| 9 | **CNR ortofoto/LiDAR piloto** | Habilita L3 urbano y DTM fino; requiere compra y licencia | Acuerdo + presupuesto | Alto |
| 10 | **Catastro** | Solo por parcela; no masivo | Convenio | Por trámite |
| 11 | **Google Weather** | Complemento de pronóstico puntual, opcional | Clave + facturación | Por llamada |

### 12.2 Fases resultantes

```
FASE 1    Fundación geoespacial (territorio, topo, OSM, suelos, API, UI)  ✅ IMPLEMENTADA
FASE 1.5  Censos + hub agrícola + clima histórico (bloques 1–3)            4-6 semanas
FASE 2    Geomorfología + amenazas piloto (bloques 4–5)                    4-6 semanas
FASE 2.5  Agricultura multiescala L1/L2 + agentes ampliados (6–7)          6-8 semanas
FASE 3    Suelo medido y ortofoto/LiDAR piloto (8–9)                       según convenio
FASE 4    Cobertura nacional y validación de campo (L3)                    6-8 semanas
FASE 5    Extensión (café, caña, SAR, catastro)                            por decidir
```

Los números de fase originales (2, 3, 4, 5) se conservan como **hitos de
producto**; las fases 1.5/2.5 son bloques de datos que se ejecutan en paralelo
con ellos y no los sustituyen.

### 12.3 Criterios de aceptación por bloque

| Bloque | Criterio de cierre |
|---|---|
| 1 Censos | tablas cargadas, cuadre verificado, supresión < 10 probada |
| 2 Clima | 10 años de CHIRPS y AgERA5 para SV, validación de rango y cobertura |
| 3 MAG | ≥ 1 cultivo con serie de precios y costos, trazada a página del PDF |
| 4 Geomorfología | unidades de relieve publicadas con test de sensibilidad |
| 5 Amenazas | 1 capa con metadatos completos y PDF de referencia |
| 6 Agricultura | L2 con κ ≥ 0,7 en el piloto; sin cifras L3 |
| 7 Agentes | perfiles estratificados y contraste con agregados censales |
| 8 CENTA | convenio firmado y datos con licencia |
| 9 CNR | licencia de derivados por escrito + piloto de 1 departamento |

### 12.4 Lo que se puede empezar mañana sin ningún acuerdo

1. Descargar y normalizar CPV 2024 (microdatos anonimizados + tabulados).
2. Ingerir CHIRPS v3 diario para El Salvador y calcular SPI-3.
3. Crear la cuenta CDS y descargar AgERA5 para el bbox nacional.
4. Extraer un cultivo piloto (maíz) de los anuarios MAG.
5. Derivar unidades de relieve del DEM ya publicado.
6. Vectorizar el mapa de erosión 2015 con referencia de página.

Nada de esto requiere compra, convenio ni clave de API de pago.

---

## 13. Fase 2 — Expansión científica (2026-11-21)

El mapa de fases de §1 se mantiene. Esta sección añade la Fase 2 ampliada y su
orden de ejecución. Detalle completo en `docs/PHASE_2_IMPLEMENTATION_ROADMAP.md`.

### 13.1 Las 7 etapas

| Etapa | Contenido | Estado |
|---|---|---|
| 1 Auditoría | inventario, pruebas, endpoints | **cerrada** |
| 2 Diseño | 13 módulos + grafo + infraestructura | **cerrada (docs)** |
| 3 Registro de datos | fuentes, licencias, accesibilidad | **cerrada (docs)** |
| 4 Priorización | P1–P4 justificada | **cerrada (docs)** |
| 5 Implementación selectiva | primer conjunto ejecutable | **no iniciada** |
| 6 Validación | pruebas y métricas | **parcial** (protocolo) |
| 7 Documentación | 18 docs nuevos + 7 actualizados | **cerrada** |

### 13.2 Primer conjunto recomendado (Etapa 5)

1. Provenance Engine mínimo.
2. CHIRPS + SPI-3 por celda.
3. NDVI/NDMI nacional (COG, serie).
4. Detección de cambios simple.
5. Presupuesto de maíz con precios MAG.
6. Simulación AquaCrop/DSSAT en un punto.

Ninguno requiere autenticación, PostGIS ni servicios de pago.

### 13.3 Orden por prioridad

| Prioridad | Módulos | Motivo |
|---|---|---|
| P1 | clima, censos, relieve | datos verificados, coste bajo |
| P2 | A, E, C (maíz) | valor alto, datos disponibles |
| P3 | B, F, J | requieren calibración |
| P4 | D, L, H, G, K, I, M | auth, datos oficiales o licencias |

### 13.4 Regla de avance

Una etapa no se cierra por documentos. Se cierra cuando su entregable se ejecuta
y su prueba pasa. Las etapas 2, 3, 4 y 7 son documentales **por definición**; la
5 y la 6 exigen código.
