# SYSTEM_ARCHITECTURE.md — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Restricción de diseño:** debe operar completo en un solo equipo de 8–16 GB RAM, sin GPU, sin clúster, sin servicios de pago obligatorios.

---

## 1. Principio rector

AGROSV es un **sistema de datos con modelos encima**, no una aplicación con datos dentro. El orden de prioridad es:

```
1. Procedencia y versionado   ← si esto falla, nada más importa
2. Determinismo y reproducibilidad
3. Separación de clases de modelo
4. Rendimiento
5. Interfaz
```

Toda decisión técnica por debajo se justifica contra ese orden.

---

## 2. Vista de componentes

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            CAPA DE PRESENTACIÓN                              │
│  React + TypeScript + MapLibre GL JS                                         │
│  · visor de capas (COG vía TiTiler, PMTiles para vectorial)                  │
│  · panel de procedencia: toda cifra clicable → provenance_id                 │
│  · SIN lógica de cálculo                                                    │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ HTTP / JSON
┌───────────────────────────────▼──────────────────────────────────────────────┐
│                              API  (FastAPI)                                  │
│  /units         perfil agroclimático de unidad productiva (PAUP)             │
│  /scenarios     ejecución y recuperación de escenarios                       │
│  /sources       catálogo de fuentes y estados de verificación                │
│  /provenance    resolución de provenance_id                                  │
│  · Pydantic para contratos; respuesta siempre incluye `provenance` y         │
│    `uncertainty` o falla la validación                                      │
└──────┬───────────────────────────────┬───────────────────────────────────────┘
       │                               │
┌──────▼───────────────┐    ┌──────────▼──────────────────────────────────────┐
│  MOTOR DE SIMULACIÓN │    │  SERVICIO DE AGENTES SINTÉTICOS                 │
│  (determinista)      │    │  (generativo — aislado)                         │
│                      │    │                                                 │
│  · balance hídrico   │    │  · carga perfiles Nemotron                      │
│  · AquaCrop 7.3      │    │  · asigna dotaciones (desde censo, declaradas)  │
│  · estrés térmico    │    │  · simula decisión con reglas explícitas        │
│  · módulo económico  │    │  · LLM SOLO para texto, nunca para números      │
│  · Monte Carlo       │    │                                                 │
└──────┬───────────────┘    └──────────┬──────────────────────────────────────┘
       │                               │  (no escribe en tablas numéricas)
┌──────▼───────────────────────────────▼──────────────────────────────────────┐
│                        CAPA DE ACCESO A DATOS                               │
│  SQLAlchemy / GeoAlchemy2  ·  Rasterio  ·  xarray  ·  s3fs/httpfs           │
└──────┬──────────────────────────────────────────────────────────────────────┘
       │
┌──────▼───────────────────────────┐   ┌─────────────────────────────────────┐
│  POSTGRESQL 16 + POSTGIS 3.4     │   │  ALMACÉN RASTER                     │
│  · fuente única de verdad        │   │  Cloud Optimized GeoTIFF            │
│  · vectorial, tabular, agentes   │   │  + Zarr para cubos climáticos       │
│  · provenance, linaje            │   │  · data/raw inmutable               │
└──────────────────────────────────┘   └─────────────────────────────────────┘
       ▲
┌──────┴──────────────────────────────────────────────────────────────────────┐
│                     ORQUESTACIÓN POR LOTES (sin daemon)                      │
│  `agrosv ingest <source>`  ·  `agrosv build <layer>`  ·  `agrosv sim <spec>` │
│  Ejecutable a mano, en cron o en CI. Idempotente. Reanudable.               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Por qué orquestación por lotes y no colas/servicios
Un DAG con Airflow/Prefect añade un servidor, una base de metadatos y superficie de fallo, para un volumen de ~1,2 GB y ejecuciones diarias o semanales. Un CLI idempotente con manifiestos en YAML resuelve lo mismo y es depurable en una laptop. Si el proyecto crece a Centroamérica, se migra a Prefect sin reescribir la lógica (el CLI es el mismo código).

---

## 3. Justificación de cada dependencia

Formato: **qué resuelve · licencia · coste · veredicto**.

### 3.1 Backend

| Tecnología | Rol | Licencia | Coste | Veredicto |
|---|---|---|---|---|
| **Python 3.11+** | Lenguaje núcleo | PSF | $0 | ✅ Todo el ecosistema geoespacial y agronómico (Rasterio, GDAL, xarray, AquaCrop) vive aquí. No hay alternativa realista. |
| **FastAPI** | API HTTP | MIT | $0 | ✅ Pydantic da contratos tipados que permiten *impedir* respuestas sin `provenance`. Ese es el motivo, no la velocidad. |
| **Pydantic v2** | Validación de contratos | MIT | $0 | ✅ Convierte "toda cifra lleva procedencia" en una regla ejecutable, no en una convención. |

### 3.2 Geoespacial

| Tecnología | Rol | Licencia | Veredicto |
|---|---|---|---|
| **GDAL** ≥3.8 | E/S raster/vectorial | MIT/X | ✅ Dependencia de sistema, inevitable. Instalar vía conda-forge para evitar el infierno de compilación. |
| **Rasterio** | API Python sobre GDAL | BSD-3 | ✅ Necesario para leer ventanas de COG sin cargar escenas completas (clave en Sentinel-2). |
| **GeoPandas** | Vectorial tabular | BSD-3 | ✅ Une geometrías con estadística censal sin salir de pandas. |
| **Shapely 2.x** | Geometría plana | BSD-3 | ✅ Shapely 2 con backend en C es 5–10× más rápido que 1.x; importa al procesar miles de polígonos. |
| **pyproj** | Reproyección | MIT | ✅ El país cruza UTM 15N/16N; hay que reproyectar y calcular áreas métricas. |
| **rio-tiler / TiTiler** | Servir COG | BSD-3 | ✅ Evita construir un servidor de tiles propio. Sirve COG directamente a MapLibre. |

### 3.3 Datos

| Tecnología | Rol | Licencia | Veredicto |
|---|---|---|---|
| **PostgreSQL 16** | BD relacional | PostgreSQL License | ✅ Robusto, sin coste, con extensiones maduras. |
| **PostGIS 3.4** | Tipos y funciones espaciales | GPL-2.0 | ✅ Necesario para intersecciones, `ST_Area`, índices GiST y joins espaciales en SQL. GPL aquí no contamina: se usa como servidor, no se enlaza. |
| **SQLite + GeoPackage** | Réplica local / demos offline | Dominio público | ⚠️ **Uso restringido** — ver §4.2. Solo lectura, generada desde Postgres. |
| **COG (Cloud Optimized GeoTIFF)** | Almacén raster | Estándar abierto | ✅ Lectura por ventana y overviews; compatible con TiTiler y con S3. |
| **Zarr** | Cubos espacio-temporales | MIT | ✅ Para series climáticas multidimensionales; mejor que miles de GeoTIFF sueltos. |
| **xarray + rioxarray** | Álgebra sobre cubos | Apache-2.0 | ✅ Alinea CHIRPS/ERA5/DEM en un mismo eje temporal con remuestreo explícito. |

### 3.4 Procesamiento

**NumPy** (BSD-3) · **Pandas 2.x** (BSD-3) — obligatorios, sin discusión. Pandas 2 con Arrow reduce memoria ~50 % en tablas censales, relevante en 16 GB.

### 3.5 Modelado agronómico

| Tecnología | Rol | Licencia | Veredicto |
|---|---|---|---|
| **FAO AquaCrop 7.3 (Python oficial)** | Balance hídrico y rendimiento | **BSD-3** | ✅ **Fase 1.** Pocos parámetros, propiedades hidráulicas derivables de textura (novedad 7.3), análisis de frecuencia integrado. |
| **DSSAT CSM 4.8.6** | Modelo de cultivo multi-proceso | **BSD-3** | ⏸️ **Fase 3.** Ver §4.3. Requiere coeficientes genéticos calibrados que no existen abiertamente para variedades salvadoreñas. |
| **AquaCrop-OSPy (pip `aquacrop`)** | Fork Python | Apache-2.0 | ❌ **Descartado.** Basado en AquaCrop-OS v6, previo al código oficial 7.3. Dos implementaciones divergentes del mismo modelo es un riesgo de reproducibilidad inaceptable. |

### 3.6 Visualización

**React 18 + TypeScript** (MIT) — el tipado permite que el frontend consuma exactamente los contratos Pydantic generados, evitando divergencia API/UI.
**MapLibre GL JS** (BSD-3) — fork abierto de Mapbox GL, sin clave de API ni cuenta. Mapbox GL exigiría token y facturación. La elección es por coste y por ausencia de dependencia contractual, no por moda.

---

## 4. Cuestionamiento de las decisiones propuestas

Esta sección existe porque el encargo pide cuestionar lo que no tenga justificación.

### 4.1 ❌ "No incorporar tecnologías por moda" aplica a: Google Weather API

Se propuso como fuente meteorológica. **Debe rechazarse como fuente núcleo** por dos cláusulas contractuales, no por precio:
- §21.1 prohíbe usar el contenido en *"a weather app or weather model whose primary purpose is to provide weather information"*;
- §21.2 obliga a **borrar** los datos en 1 h / 24 h / 240 h según tipo.

Un archivo climático histórico es exactamente lo que AGROSV necesita y exactamente lo que la licencia prohíbe construir. Se admite solo como capa efímera de condiciones actuales en la UI.

### 4.2 ⚠️ SQLite + PostGIS simultáneos: riesgo de duplicación

El encargo pide ambos. Usarlos como **dos fuentes de verdad** viola la restricción "evitar duplicación de información" y genera divergencia silenciosa.

**Decisión:** PostgreSQL/PostGIS es la **única** fuente de verdad escribible. SQLite/GeoPackage se genera como **artefacto de exportación de solo lectura** (`agrosv export --sqlite`) para demos offline y para el prototipo inicial sin servidor. Un test de CI verifica que la réplica coincide con el origen. Ningún proceso escribe en SQLite y luego sincroniza hacia Postgres.

### 4.3 ⏸️ DSSAT en Fase 1: no es viable, no es cuestión de gusto

DSSAT necesita coeficientes genéticos por cultivar (P1, P2, P5, G1, G2, G3, PHINT) calibrados contra ensayos de campo con fenología observada. Para variedades de maíz y frijol salvadoreñas **no existe un conjunto público de calibración**. Ejecutar DSSAT con coeficientes por defecto de Iowa produce números con apariencia de rigor y sin validez local — precisamente lo que el proyecto prohíbe.

AquaCrop, en cambio, se parametriza con: textura (SoilGrids), ET0 (ERA5/Open-Meteo) y un número reducido de parámetros de cultivo con valores por defecto documentados por FAO para maíz y frijol. Es defendible desde el día uno, con incertidumbre declarada.

**DSSAT entra cuando CENTA aporte ensayos.** No antes.

### 4.4 ⚠️ PostGIS no debe almacenar los rásteres

Guardar rásteres como `raster` en PostGIS es posible y tentador. A 21.041 km² con DEM de 30 m, Sentinel-2 de 10 m y series CHIRPS de 45 años, el coste de E/S y de `VACUUM` es desproporcionado frente a COG/Zarr en sistema de archivos, que además es compatible con TiTiler y con S3 sin cambios.

**Decisión:** rásteres en COG/Zarr; **solo metadatos, huellas y estadísticas zonales** en PostGIS.

### 4.5 ✅ Lo que sí se mantiene sin cambios

Python + FastAPI, GeoPandas/Rasterio/Shapely, NumPy/Pandas/Xarray, PostGIS, COG, React/TS/MapLibre, AquaCrop. Todas pasan el filtro: gratuitas, de código abierto, con rol específico y sin alternativa mejor en su función.

---

## 5. Separación de clases de modelo (aplicada en la arquitectura)

La restricción "no permitir que un modelo de lenguaje invente resultados agronómicos" se implementa **estructuralmente**, no por disciplina.

| Clase | Implementación | Puede escribir en tablas numéricas | Cómo se audita |
|---|---|---|---|
| **Determinista** | AquaCrop, balance hídrico, geometría (pendiente, escorrentía) | ✅ sí | Reproducible bit a bit con misma entrada + versión |
| **Estadístico** | SPI/SPEI, regresiones, frecuencia de extremos | ✅ sí | Semilla + método declarados |
| **Aprendizaje automático** | Clasificación de cobertura, downscaling | ✅ sí, con validación cruzada obligatoria | Métricas fuera de muestra registradas |
| **Generativo (LLM)** | Narrativa de agente, redacción de informes | ❌ **nunca** | El módulo no tiene credenciales de escritura a tablas numéricas |

**Mecanismo de aplicación:** el paquete `agrosv.agents` recibe del motor de simulación un `FactsBundle` (dict con valores ya calculados y sus `provenance_id`) y devuelve **texto**. No tiene acceso al ORM de escritura. Un test de arquitectura (`tests/test_layer_isolation.py`) falla si `agrosv.agents` importa `sqlalchemy` o `agrosv.simulation`.

---

## 6. Modelo de datos núcleo

```sql
-- Catálogo y procedencia (el corazón del sistema)
source            (source_id PK, nombre, url, licencia, estado_verificacion,
                   cobertura, resolucion_nativa, resolucion_efectiva, notas)
dataset_version   (version_id PK, source_id FK, fecha_descarga, sha256,
                   variante, parametros_json)
provenance        (provenance_id PK, version_id FK, transformacion, ts_ejecucion,
                   software_version, seed)

-- Geografía
admin_unit        (id PK, nivel, nombre, codigo_ine, geom GEOMETRY(MultiPolygon,4326),
                   municipio_2023, distrito_previo)   -- resuelve el cambio de 2023
unit_of_analysis  (id PK, geom, admin_unit_id, elev_m, pendiente_deg, orientacion_deg,
                   geom_hash)

-- Suelo y clima
soil_profile      (id PK, unit_id FK, fuente, profundidad_cm, propiedad,
                   valor, unidad, cuantil, provenance_id FK)
climate_daily     (unit_id FK, fecha, variable, valor, unidad,
                   resolucion_efectiva, provenance_id FK, PK(unit_id,fecha,variable))

-- Agronomía
crop              (crop_id PK, nombre, ciclo_dias, params_aquacrop_json)
simulation_run    (run_id PK, unit_id, crop_id, escenario, seed,
                   modelo, modelo_version, ts_inicio, ts_fin, estado)
simulation_output (run_id FK, variable, fecha, valor, cuantil)

-- Economía
price_series      (cultivo, fecha, precio, unidad, fuente, provenance_id)
cost_structure    (cultivo, ciclo, rubro, valor, fuente)
agent             (agent_id PK, nemotron_uuid, synthetic BOOL NOT NULL DEFAULT TRUE,
                   departamento, municipio, ocupacion_ciiu, edad, sexo,
                   dotacion_json,            -- tamaño finca, agua, crédito: ASIGNADOS
                   dotacion_fuente,          -- de dónde vino cada dotación
                   provenance_id FK)
agent_decision    (agent_id FK, run_id FK, decision_json, regla_aplicada, seed)
```

**Nótese:** `agent.dotacion_*` con `dotacion_fuente` obliga a declarar de dónde salió el tamaño de finca, porque **Nemotron no lo trae**. Es la defensa contra inventar datos ausentes.

---

## 7. Estimación de almacenamiento (calculada, no estimada al azar)

Bounding box de El Salvador: lon −90,2 a −87,6 (2,6°) × lat 13,1 a 14,5 (1,4°).

| Activo | Cálculo | Tamaño |
|---|---|---|
| CHIRPS diario 1981–2025 (`rnl`) | 52 × 28 celdas × 16.436 días × 4 B = 95,7 MB; COG comprimido ~40 % | **~40 MB** |
| Copernicus DEM GLO-30 | 9.360 × 5.040 px × 2 B (Int16) = 94 MB; COG ~70 % | **~65 MB** |
| SoilGrids (9 props × 6 prof. × 3 cuantiles = 162 capas) | 1.248 × 672 px × 2 B × 162 = 272 MB; COG ~45 % | **~120 MB** |
| OSM extracto → PostGIS | 33,6 MB `.pbf` expandido | **~350 MB** |
| Nemotron (parquet íntegro, `data/raw`) | dato del editor | **542 MB** |
| Código, esquema, derivados tabulares | — | **~50 MB** |
| **Total núcleo Fase 1** | | **≈ 1,2 GB** |

Sentinel-2 **no se almacena**: lectura por ventana del COG del polígono. Un polígono de 2 ha a 10 m son ~2.000 px por banda y fecha; decenas de KB. Esto es lo que hace viable operar sin clúster.

**Conclusión:** cabe en un disco de 64 GB con holgura de 50×, y en 8 GB de RAM sin *swap* si se procesa por ventanas y por lotes.

---

## 8. Topología de despliegue

**Fase 1 — una máquina, Docker Compose:**

```yaml
services:
  db:       postgis/postgis:16-3.4          # puerto 5432, volumen persistente
  api:      agrosv/api                       # uvicorn, puerto 8000
  titiler:  ghcr.io/developmentseed/titiler  # COG → tiles, puerto 8001
  web:      agrosv/web                       # build estático servido por nginx
```

Todo local. Sin Kubernetes, sin colas, sin object storage.

**Escalado futuro (Centroamérica):** los mismos contenedores; `db` a instancia gestionada y COG a S3. La lógica no cambia porque el acceso a raster está abstraído en `agrosv.storage` (local ↔ S3 por configuración).

---

## 9. Riesgos arquitectónicos y mitigación

| Riesgo | Mitigación |
|---|---|
| GDAL rompe la instalación reproducible | Entorno fijado con `conda-lock` o wheels `rasterio`/`pyogrio`; nunca compilar a mano |
| Un cambio de esquema invalida todos los resultados | Migraciones versionadas (Alembic); `simulation_run.modelo_version` obliga a re-ejecutar, no a mezclar |
| Nemotron cambia de versión (nuevo `sha`) | Anclar al `sha` `68f6a21c…`; actualizar es una decisión explícita con re-ejecución |
| Sentinel-2 migra de colección (`sentinel-2-l2a` → `sentinel-2-c1-l2a`) | El `collection_id` es parámetro de configuración, no constante en código |
| CHIRPS v2 se apaga en dic-2026 | Nacer en v3; `product_variant` explícito en la tabla |
| Límite de 10.000 llamadas/día de Open-Meteo | Ingesta por lotes a almacén propio; la API es transporte, no origen permanente |
| Shapes de 2023 no coinciden con capas 2021 | Tabla de correspondencia obligatoria antes de cualquier join espacial |

---

## 10. Lo que la arquitectura deliberadamente **no** incluye

Sin autenticación de usuarios (no hay producto multi-usuario en Fase 1). Sin microservicios (un monolito modular es correcto a esta escala). Sin Kubernetes. Sin streaming/tiempo real. Sin vector database (no hay búsqueda semántica en el camino crítico). Sin orquestador con servidor. Sin GPU.

Cada una de estas se incorpora **cuando un requisito medido lo exija**, no antes.
