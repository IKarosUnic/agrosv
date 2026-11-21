# AGENT_ROLES.md — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Propósito:** distribuir el trabajo entre siete agentes sin que se pisen. La clave no es la lista de tareas, es **quién escribe en qué**.

---

## 1. Regla de oro: propiedad de escritura exclusiva

Un conflicto entre agentes casi nunca es un desacuerdo técnico; es dos agentes escribiendo el mismo archivo o la misma tabla. Se resuelve con propiedad exclusiva.

| Recurso | Propietario único | Quién lee | Quién **no** puede escribir |
|---|---|---|---|
| `data/metadata/registry.yaml` | AGENTE 1 | todos | todos los demás |
| `data/raw/<source>/` | AGENTE 1 (solo escribe el ingestor que él autoriza) | todos | nadie edita jamás |
| `src/agrosv/geo/` | AGENTE 2 | 2, 6 | — |
| `src/agrosv/ingest/mag_*.py`, `bcr_*.py` | AGENTE 3 | 3, 6, 7 | — |
| `src/agrosv/climate/` | AGENTE 4 | 4, 6, 7 | — |
| `src/agrosv/agents/` | AGENTE 5 | 5, 6 | 1, 2, 3, 4, 7 |
| `src/agrosv/agronomy/`, `economics/` | AGENTE 6 | 6, 7 | — |
| `tests/`, `db/migrations/` (revisión) | AGENTE 7 | todos | nadie fusiona sin su aprobación |
| `db/migrations/*.sql` (autoría) | autor del módulo | — | debe pasar revisión de 7 |
| Los 8 documentos de Fase 0 | AGENTE 1 | todos | cambios por PR con revisión de 7 |

**Ningún agente modifica el módulo de otro.** Si necesita un cambio, abre un issue con el contrato esperado.

---

## 2. Contratos de interfaz entre agentes

Cada frontera es un archivo o una tabla, nunca una llamada implícita.

```
AGENTE 2 ──geometría + topografía──▶ AGENTE 6
          (admin_unit, unit_of_analysis con elevación/pendiente/orientación)

AGENTE 4 ──series climáticas───────▶ AGENTE 6
          (climate_daily normalizada: fecha, variable, valor, resolucion_efectiva)

AGENTE 2 ──perfiles de suelo───────▶ AGENTE 6
          (soil_profile con cuantiles Q05/Q50/Q95)

AGENTE 3 ──verdad de referencia────▶ AGENTE 6 (validación)
          (rendimiento/superficie/precio por departamento y ciclo)

AGENTE 5 ──población de agentes────▶ AGENTE 6 (simulación económica)
          (agent + dotacion_json + dotacion_fuente)

AGENTE 6 ──FactsBundle─────────────▶ AGENTE 5 (narrativa)
          (solo lectura de números ya calculados; sin escritura de vuelta)

AGENTE 7 ──aprobación──────────────▶ todos
```

**Formato de contrato:** clases Pydantic en `src/agrosv/contracts/`, propiedad compartida revisada por AGENTE 1. Un cambio de contrato rompe CI y obliga a los dos lados a actualizar en el mismo PR.

---

## 3. Los siete agentes

### AGENTE 1 — Arquitecto de infraestructura

**Misión:** que el sistema exista, sea reproducible y no mienta sobre sus datos.

**Responsabilidades**
- Propiedad de `registry.yaml`: única fuente de verdad de fuentes, licencias, estados de verificación. Ningún `source_id` entra al código sin estar aquí.
- Esquema de base de datos, migraciones (co-autoría con 7), contratos Pydantic.
- Entorno reproducible: lockfiles, versiones de GDAL, CI.
- CLI `agrosv` y orquestación por lotes.
- Aplicación técnica de "toda cifra lleva procedencia": campos obligatorios, validadores, tests de contrato.

**Entregables**
`db/schema.sql` · `db/migrations/*` · `src/agrosv/contracts/*.py` · `src/agrosv/cli.py` · `registry.yaml` · `.github/workflows/ci.yml` · `docker-compose.yml`

**Depende de:** nadie. **Bloquea a:** todos.

**No hace:** no ingiere datos de fuente, no implementa modelos, no decide metodología científica (la implementa).

---

### AGENTE 2 — Investigador geoespacial

**Misión:** convertir el territorio en capas utilizables.

**Responsabilidades**
- Ingesta Copernicus DEM GLO-30 desde AWS (no CDSE, restringido desde jul-2026).
- Derivación: pendiente, orientación, relieve, direcciones de flujo y escorrentía acumulada.
- Límites administrativos y **tabla de correspondencia 2023 ↔ distritos previos** (bloqueante para todos los joins).
- OSM: vialidad rural, hidrografía, infraestructura, localidades. Mantener en esquema PostGIS separado por ODbL.
- Suelos: SoilGrids vía **WebDAV** (no REST, roto), con `wv0033`/`wv1500` que consume AquaCrop.
- Indexado de Sentinel-2: catálogo de escenas disponibles sobre el país y cálculo de NDVI/NDWI por ventana.

**Entregables**
`src/agrosv/geo/{dem,admin,osm,soil,s2}.py` · `data/processed/topography/` · `admin_unit` + `municipio_map` · `soil_profile` · script de máscara de nubes SCL

**Depende de:** AGENTE 1 (esquema). **Bloquea a:** AGENTE 6.

**Criterio de aceptación:** pendiente media por departamento es coherente con el relieve conocido (cadena volcánica y cordillera norte más empinadas que planicie costera), y todo polígono de prueba tiene elevación, pendiente y perfil de suelo con cuantiles.

**No hace:** no decide qué cultivo modelar, no genera estadística agrícola, no toca Nemotron.

---

### AGENTE 3 — Investigador de datos agrícolas MAG/BCR

**Misión:** establecer la verdad de referencia nacional y su linaje.

**Responsabilidades**
- **Corregir la premisa del encargo:** la fuente primaria 2025 es el **BCR (V Censo Agropecuario y I de Pesca 2025)**, no el MAG. El Anuario del MAG se detiene en 2021-2022. Documentar esa sustitución.
- Extraer tablas de PDF censales con verificación humana (no hay API). Generar CSV versionados con `provenance_id` por tabla.
- Construir series por departamento: superficie cosechada, producción, rendimiento, número de productores, uso de semilla, destino de la producción.
- Costos de producción por cultivo desde el informe anual del MAG.
- Precios: DEFENSORÍA/BCR/MAG según disponibilidad verificada.
- **Registrar explícitamente la licencia de cada dato**; si no está declarada, marcarlo `RESTRICTED-redistribución`.

**Entregables**
`src/agrosv/ingest/bcr_cap2025.py` · `src/agrosv/ingest/mag_{anuario,costos}.py` · `data/processed/agriculture/*.csv` + `.provenance.json` · tabla `price_series`, `cost_structure` · documento de discrepancias MAG vs BCR

**Depende de:** AGENTE 1. **Bloquea a:** AGENTE 6 (validación) y AGENTE 5 (dotaciones).

**Criterio de aceptación:** la suma de producción departamental cuadra con el total nacional dentro del redondeo publicado; cada cifra es rastreable al número de página del PDF.

**No hace:** no interpreta los datos, no los usa para calibrar sin autorización de 7.

---

### AGENTE 4 — Investigador climático

**Misión:** series climáticas consistentes con resolución efectiva declarada.

**Responsabilidades**
- CHIRPS v3, variante `rnl` (1981–) como serie principal. Declarar que el dato diario **es una desagregación pentadal** y que su resolución efectiva es pentadal.
- ERA5-Land vía CDS (`cdsapi`, requiere token del usuario) y/o Open-Meteo como transporte. **Nunca** almacenar solo la respuesta de Open-Meteo: el archivo debe ser propio.
- Variables: precipitación, T max/min/media, ET0 FAO-56, humedad de suelo, radiación, viento.
- Índices de sequía: SPI y SPEI a 3, 6, 12 meses; detección de canícula; anomalías respecto a climatología 1991–2020.
- Corrección por altitud declarada como supuesto explícito (lapse rate), nunca silenciosa.
- Pronósticos: solo donde exista fuente abierta (Open-Meteo / GFS / IFS). **Google Weather descartado** por ToS (§3.7 del registro).

**Entregables**
`src/agrosv/climate/{chirps,era5,drought,downscale}.py` · `climate_daily` en Zarr + PostGIS · `drought_indices` · informe de resolución efectiva por variable

**Depende de:** AGENTE 1, y de AGENTE 2 para la geometría de unidades. **Bloquea a:** AGENTE 6.

**Criterio de aceptación:** la climatología 1991–2020 de precipitación anual por departamento es del orden de 1.700–2.400 mm con estación seca nov–abr bien definida; toda serie declara `resolucion_efectiva`.

**No hace:** no modela cultivos, no corrige con estaciones que no existen.

---

### AGENTE 5 — Especialista en Nemotron Personas

**Misión:** población de agentes sintéticos útil, honesta y etiquetada.

**Responsabilidades**
- Ingesta del dataset anclado al `sha` `68f6a21c17973d6a34ac6354d50a31c1fbcec14f`.
- Filtrado de perfiles agrícolas por clase CIIU división 01 (17.957 perfiles verificados) y agroindustria asociada.
- **Documentar la brecha de representatividad:** 17.957 agentes vs. 401.101 productores de maíz del censo. Son universos distintos; debe quedar escrito y visible en la UI.
- **Diseñar el esquema de dotaciones** (tamaño de finca, tenencia, acceso a agua, crédito, activos) que **Nemotron no contiene**, con asignación desde distribuciones censales y `dotacion_fuente` obligatorio por campo.
- Respetar y propagar las limitaciones del editor: indígena/afrodescendiente subrepresentado, roles de género heredados del LLM, español aproximado, independencia ocupación×educación.
- Construir el marco de decisión del agente: reglas económicas explícitas (no LLM) que producen decisiones; el LLM solo verbaliza.
- Garantizar `synthetic = TRUE` propagado hasta cualquier salida.

**Entregables**
`src/agrosv/agents/{load_nemotron,filter_agri,endowments,decision_rules,narrate}.py` · tabla `agent` + `agent_decision` · `docs/NEMOTRON_COVERAGE.md` con el análisis de representatividad · test que falla si una salida pierde la marca sintética

**Depende de:** AGENTE 1 (esquema), AGENTE 3 (distribuciones censales para dotaciones). **Bloquea a:** AGENTE 6 (simulación económica).

**Criterio de aceptación:** 100 % de agentes con `synthetic=TRUE`; 100 % de `dotacion_fuente` no nulo; ninguna afirmación sobre agricultores reales; contraste chi-cuadrado entre marginales de agentes y marginales censales documentado con su resultado.

**No hace:** no calcula rendimientos, no fija precios, no escribe en tablas numéricas.

---

### AGENTE 6 — Especialista en modelos agronómicos

**Misión:** el motor de simulación, determinista y auditable.

**Responsabilidades**
- Implementar los 8 módulos del motor (§4 de `IMPLEMENTATION_ROADMAP.md`) en orden de dependencia.
- AquaCrop 7.3 oficial (no AquaCrop-OSPy), con parámetros de suelo derivados de textura y `wv0033`/`wv1500`.
- Balance hídrico diario, estrés hídrico y térmico, escenarios climáticos.
- Monte Carlo sobre cuantiles de suelo y variantes climáticas (semilla registrada).
- Módulo económico: ingreso, costo, pérdida, punto de indiferencia.
- Emitir `FactsBundle` para AGENTE 5.
- **Nunca** invocar un LLM en el camino numérico.

**Entregables**
`src/agrosv/agronomy/{water_balance,aquacrop_driver,thermal_stress,scenarios}.py` · `src/agrosv/economics/{budget,risk}.py` · `simulation_run`/`simulation_output` · `tests/golden/` con casos de referencia congelados

**Depende de:** 2 (geometría/suelo), 4 (clima), 3 (validación y economía), 5 (agentes). **Bloquea a:** el primer módulo funcional.

**Criterio de aceptación:** un caso PAUP sobre un polígono de Ahuachapán corre de extremo a extremo en < 60 s, produce P10/P50/P90 y su salida es idéntica bit a bit al repetir con la misma semilla.

**No hace:** no decide qué es "correcto" agronómicamente sin respaldo en literatura FAO documentada.

---

### AGENTE 7 — Auditor de calidad y reproducibilidad

**Misión:** que nadie pueda publicar un número sin defensa.

**Responsabilidades**
- Revisión de **todas** las migraciones antes de fusionar.
- Suite de pruebas: unitarias, de contrato, de aislamiento de capas (que `agents` no importe `sqlalchemy`), golden tests de simulación.
- Validación científica según `SCIENTIFIC_VALIDATION.md`: contra verdad censal, métricas de error, propagación de incertidumbre.
- Auditoría de procedencia: muestreo aleatorio de N cifras publicadas y verificación de que cada una resuelve a un `provenance_id` válido y a un archivo con hash correcto.
- Congelar versiones: cualquier cambio de versión de dataset o de modelo obliga a re-etiquetar resultados previos.
- Custodiar las advertencias: ninguna salida puede publicarse sin sus limitaciones asociadas.

**Entregables**
`tests/**` · `docs/VALIDATION_REPORT_<fecha>.md` · `scripts/audit_provenance.py` · informes de bloqueo (qué no se puede publicar y por qué)

**Depende de:** todos. **Veto sobre:** todos.

**Criterio de aceptación:** cero cifras publicadas sin procedencia resoluble; cero resultados sin incertidumbre; ningún test desactivado sin justificación escrita y aprobación del responsable humano.

**No hace:** no implementa funcionalidad. Su entregable es un veredicto.

---

## 4. Secuencia de trabajo

```
Semana 1–2   AGENTE 1 solo: esquema, contratos, CLI, CI. Nadie más escribe código.
Semana 2–5   AGENTE 2 ∥ AGENTE 3 ∥ AGENTE 4   (paralelo, módulos disjuntos)
             AGENTE 5 prepara análisis de Nemotron (sin escribir en BD aún)
Semana 6     AGENTE 7 primera auditoría de datos crudos y procedencia
Semana 7–10  AGENTE 6 construye PAUP, consumiendo los contratos de 2, 3, 4
Semana 10    AGENTE 5 conecta agentes al PAUP
Semana 11–12 AGENTE 7 validación completa + AGENTE 1 empaquetado
```

**Punto de sincronización único:** al final de la semana 5, los tres módulos de datos deben entregar sus contratos con datos reales sobre al menos un departamento piloto. Si uno falla, AGENTE 6 no arranca — no se simula con datos inventados para "no bloquear".

---

## 5. Conflictos previsibles y su resolución

| Conflicto | Resolución acordada de antemano |
|---|---|
| 2 y 6 discrepan sobre la resolución de suelo a usar | 2 decide el dato; 6 decide el modelo. La resolución efectiva la fija `registry.yaml`, no la conversación. |
| 4 quiere downscaling, 7 lo considera no validado | El downscaling solo entra si 7 aprueba un protocolo de validación. Mientras, se declara el sesgo de altitud. |
| 5 quiere dar a los agentes datos de ingreso | No existen en Nemotron. Se asignan desde censo con `dotacion_fuente`; si no hay fuente, el campo queda nulo y el agente lo declara. **Nunca se inventa.** |
| 3 encuentra que MAG y BCR no coinciden | Se publican ambas series con su procedencia. No se promedia ni se elige una en silencio. |
| 1 quiere cambiar un contrato | Lo anuncia, sube versión, y ambos lados actualizan en el mismo PR. |
| 6 quiere usar DSSAT en Fase 1 | Rechazado por falta de coeficientes genéticos calibrados (ver `SYSTEM_ARCHITECTURE.md` §4.3). Requiere evidencia de calibración. |
