# ADR-001 — Decisiones de arquitectura de AGROSV Fase 1

Estado: **aceptado**. Fecha: noviembre de 2026.
Contexto: `SYSTEM_ARCHITECTURE.md` y `DATA_SOURCE_REGISTRY.md` de Fase 0
proponían PostgreSQL/PostGIS y un mapa base con teselas externas. Esta fase
revisa esas propuestas y documenta cada cambio antes de implementarlo.

## D-1 · Almacén vectorial: GeoPackage, no PostGIS

**Decisión.** Fase 1 usa un GeoPackage por dominio (`territory.gpkg`,
`infrastructure.gpkg`), con índice espacial, en lugar de PostgreSQL/PostGIS.

**Razones.**
- Fase 1 es de solo lectura y de un único productor: no hay escritura
  concurrente, ni edición multiusuario, ni transacciones que justifiquen un
  servidor.
- El pipeline genera las capas en lote y las versiona como artefacto
  verificable con hash; un archivo es más auditable que un dump de base.
- Fase 0 ya sancionaba SQLite/GeoPackage para prototipos
  (`SYSTEM_ARCHITECTURE.md`, «almacenamiento»), por lo que esto no contradice
  la arquitectura aprobada.
- El acceso está abstraído en `backend/agrosv/config.py` y en las funciones de
  lectura de la API: migrar a PostGIS es sustituir esas rutas, no reescribir la
  lógica.

**Consecuencia.** Si un módulo futuro necesita escritura concurrente,
versionado de ediciones o consultas espaciales complejas entre muchas capas,
se introduce PostGIS entonces, con su propio ADR. La API documenta hoy esta
limitación.

## D-2 · Mapa base: hillshade propio, no teselas de terceros

**Decisión.** El mapa base del frontend es un hillshade derivado del DEM,
servido como teselas PNG generadas por la API. No se usan Mapbox, Google,
Carto ni las teselas públicas de OpenStreetMap.

**Razones.**
- Cero claves y cero dependencias comerciales obligatorias: requisito explícito
  de la fase.
- La política de uso de teselas de OSM prohíbe el uso intensivo desde
  aplicaciones; evitarla elimina un riesgo legal.
- El hillshade ya se calcula para el Módulo 2: no se descarga ni se almacena
  nada adicional.
- Corrige la contradicción de Fase 0: `SYSTEM_ARCHITECTURE.md` mencionaba
  MapLibre con teselas OSM y `RISKS_AND_LIMITATIONS.md` advertía sobre su
  política de uso.

**Consecuencia.** El fondo no tiene toponimia ni calles. Las capas OSM
(vectoriales) aportan caminos y asentamientos, pero no hay etiquetas de texto:
no se descargan glifos ni fuentes externas. Si se requiere toponimia, habrá que
generar teselas vectoriales propias con datos ODbL.

## D-3 · Límite nacional por dissolve de ADM1

**Decisión.** El polígono nacional se construye disolviendo ADM1; el ADM0 de la
fuente se conserva pero no se usa como límite terrestre.

**Razones.** El ADM0 de geoBoundaries mide 25.339 km² e incluye 4.372,6 km² de
aguas territoriales. Usarlo como máscara del DEM habría metido mar en todas las
estadísticas (pendiente media del "país" sobre superficie oceánica). ADM1 suma
20.966,4 km², a −0,35 % de la superficie oficial.

**Consecuencia.** El área publicada es la del límite derivado, declarada como
tal; no se ajusta a la cifra oficial.

## D-4 · ADM2 se publica como histórica

**Decisión.** Los municipios se sirven con `official: false` y una nota que
explica que son los anteriores a la reforma de 2023.

**Razones.** La fuente tiene 272 polígonos; El Salvador vigente tiene 44
municipios. Publicarlos como actuales sería presentar datos no verificados como
oficiales, lo que la fase prohíbe. No se descartan porque son útiles para
series históricas y para agregar datos anteriores a 2023.

## D-5 · CRS: 4326 para almacenar, 32616 para calcular, 6933 para áreas

**Decisión.** Geometrías en EPSG:4326 (el CRS de las fuentes); derivadas
topográficas en EPSG:32616; áreas y densidades en EPSG:6933.

**Razones.**
- Calcular pendiente en grados geográficos introduce un sesgo de ~4 % entre
  latitud y longitud a 13°N; en metros no.
- EPSG:6933 (equal-area) evita la distorsión de área de Mercator al sumar
  superficies.
- UTM 16N cubre todo el país con distorsión de escala <0,15 % en el extremo
  oeste, aceptable frente a la incertidumbre del DEM.

**Consecuencia.** Las derivadas no se remuestrean nunca a 4326: se sirven en su
rejilla métrica y el frontend las reproyecta al vuelo.

## D-6 · Lectura por ventanas y teselas selectivas

**Decisión.** El DEM se lee por ventanas de teselas locales; SoilGrids descarga
solo las 138 teselas que cubren el país (de 7.692 por capa).

**Razones.** `/vsicurl` sobre los COG del DEM tardaba >4 min por cientos de
peticiones de rango, y los VRT globales de SoilGrids suman ~27 GB. Se descargó
una vez lo necesario, se cacheó en `data/raw` y se procesó localmente.

**Consecuencia.** El primer procesamiento tarda minutos y depende de la red;
las ejecuciones posteriores son rápidas porque reutilizan el caché.

## D-7 · Un solo proceso sirve API y UI

**Decisión.** FastAPI sirve `/api/*` y, si existe, `frontend/dist`.

**Razones.** Elimina CORS, evita dos servidores en producción y garantiza que
las teselas y los GeoJSON compartan origen. En desarrollo Vite hace proxy a
8000 y mantiene recarga en caliente.

## D-8 · Raster de suelos: media 0–30 cm en una capa, no seis por profundidad

**Decisión.** Se publica la media ponderada 0–30 cm de cada propiedad, no las
seis profundidades estándar.

**Razones.** El objetivo de Fase 1 es una fundación agrícola; 0–30 cm es la
profundidad de laboratorio habitual y reduce el número de capas servidas. Las
profundidades individuales siguen disponibles en el caché de `data/raw`.

**Consecuencia.** La media 0–30 cm es una derivación de AGROSV, no un producto
oficial de SoilGrids; queda declarada en el manifiesto y en LIMITATIONS.
