# NATIONAL_GEODATA_INVENTORY — AGROSV Fase 3

**Fecha de consulta:** 2026-11-22 · **Evidencia:** `research/raw/phase3/probes_20261122_r3.json`.
Complementa —no sustituye— [`../NATIONAL_DATA_INTEGRATION.md`](../NATIONAL_DATA_INTEGRATION.md)
y las capas ya construidas en Fase 1 (`data/processed/territory`, `topography`).

---

## 1. División territorial

### 1.1 Estructura vigente

| Nivel | Cantidad | Nota |
|---|---|---|
| Nacional | 1 | 20.742 km² (superficie declarada por CNR) |
| Departamental | 14 | Estable |
| Municipal | **44** | Reforma territorial de 2023 |
| Distrital | **262** | Antiguos municipios, ahora distritos |

**Advertencia de compatibilidad:** la capa ADM2 de AGROSV Fase 1 proviene de
geoBoundaries 2021 y contiene **272 polígonos históricos**. Ese número no
coincide con los 262 distritos oficiales. La diferencia debe reconciliarse antes
de usar la capa como referencia legal o de unirla a tabulados del CPV 2024. La
capa se publica como **histórica** con `official: false`, lo cual es correcto,
pero no exime de documentar la discrepancia.

| Capa | Fuente | Cobertura | Licencia | Estado |
|---|---|---|---|---|
| Límite nacional | geoBoundaries SLV ADM0 | Nacional | CC BY-SA 2.0 | **VERIFIED** (muestra 321.639 B) |
| Departamentos (14) | geoBoundaries ADM1 (2021) | Nacional | CC BY-SA 2.0 | **VERIFIED** |
| Municipios históricos | geoBoundaries ADM2 (2021) | 272 polígonos | CC BY-SA 2.0 | **VERIFIED** (con reserva) |
| Municipios 2023 (44) | No hay capa abierta verificada | — | — | **GAP** |
| Distritos (262) | CNR / BCR (no descarga verificada) | — | — | **PENDING_VALIDATION** |
| Centros poblados | OSM (nodos `place`) | Nacional | ODbL 1.0 | **VERIFIED** (Fase 1) |
| Cantones y caseríos | OSM parcial; CNR no abierto | Parcial | ODbL 1.0 | **PENDING_VALIDATION** |

### 1.2 Identificadores geográficos

| Sistema | Disponibilidad | Riesgo |
|---|---|---|
| Código de departamento (2 dígitos, ISO 3166-2 `SV-XX`) | Estable | Bajo |
| Código de municipio | Cambió con la reforma 2023 | **Alto** si se mezclan versiones |
| Código de distrito | CNR/BCR, no publicado como catálogo abierto | **Alto** |
| `GID_0/1/2` de geoBoundaries | Disponible | No es código oficial |
| `boundaryID` de geoBoundaries | Disponible (`SLV-ADM1-98794003`) | Solo para trazabilidad de la fuente |

**Regla AGROSV:** se conserva el identificador original de la fuente **y** se
añade un `territory_id` propio estable; la tabla de correspondencia entre
versiones se versiona en `data/metadata/`.

### 1.3 Evidencia

```
GET https://www.geoboundaries.org/api/current/gbOpen/SLV/ADM1/   → 200, 1.702 B
  boundaryID: SLV-ADM1-98794003 · year: 2021 · license: CC BY-SA 2.0
GET https://www.cnr.gob.sv/                                       → 200, 130.722 B
GET https://www.cnr.gob.sv/descargas/                             → 200, pero es un
  gestor de descargas administrativo (licitaciones, UACI, publicaciones):
  0 enlaces a .zip/.shp/.geojson/.gpkg/.csv
```

**Hallazgo:** la página «Descargas» del CNR **no publica datos geográficos**. El
catálogo de productos del IGCN es de **compra**. No existe una descarga abierta
de límites oficiales verificada en esta ronda.

---

## 2. Catastro y cartografía nacional (CNR)

| Producto | Escala / resolución declarada | Acceso | Estado |
|---|---|---|---|
| Ortofoto nacional (*El Salvador Maps*, 20.742,5 km²) | hasta 10 cm (declarado) | Visor | **DOCUMENTED** |
| Fotografía aérea (color, IR, B/N) | según vuelo | Compra, «desde $29» | **RESTRICTED** |
| Fotografía oblicua | no publicada | Sin ficha | **DOCUMENTED** |
| LiDAR / nube de puntos | no publicada | Sin ficha | **DOCUMENTED** |
| MDT y MDS | no publicada | Sin ficha | **DOCUMENTED** |
| Curvas de nivel 1:25.000 y 1:50.000 | 1:25k / 1:50k | Compra | **RESTRICTED** |
| Restitución fotogramétrica | 1:1.000 y 1:5.000 | Compra ($15–$252) | **RESTRICTED** |
| Modelos 3D | no publicada | Sin condiciones públicas | **DOCUMENTED** |
| Cartografía geológica | 1:500.000 ($4) y 1:100.000 ($30/hoja) | Compra | **RESTRICTED** |
| Catastro (mapa de parcela $3,50; plano digital $299,45) | parcela | Compra por trámite | **RESTRICTED** |

### 2.1 El Salvador Maps: problema técnico verificado

```
GET https://www.elsalvadormaps.sv/            → ConnectError: CERTIFICATE_VERIFY_FAILED
GET https://mapa.elsalvadormaps.sv/cnr/map/4  → ConnectError: CERTIFICATE_VERIFY_FAILED
GET (verify=False)                            → 200, 4.326 B (solo la cáscara HTML)
```

El certificado TLS del sitio **no valida** con una cadena de confianza estándar.
Con validación desactivada solo se obtiene la página de entrada; la aplicación
requiere sesión. **Consecuencia:** no es una fuente automatizable ni citable como
servicio estable; se documenta su existencia y se recomienda no usarla en
pipelines.

### 2.2 Qué pedir al CNR (prioridad AGROSV)

1. Ficha técnica de *El Salvador Maps*: resolución real, fecha de vuelo,
   exactitud vertical/horizontal, sistema geodésico.
2. Licencia escrita de uso y de publicación de **derivados** (pendientes,
   hillshade, modelos de aptitud).
3. Cotización de ortofoto + LiDAR para un departamento piloto (Ahuachapán).
4. Catálogo de códigos de ubicación geográfica (departamento/municipio/distrito).
5. Condiciones del servicio WMS institucional (existe por convenio, no es
   endpoint anónimo).

**No se asume** que comprar un archivo autorice su redistribución.

---

## 3. Topografía y geomorfología

| Producto | Resolución | Fuente | Acceso | Estado |
|---|---|---|---|---|
| DEM | **30 m** | Copernicus DEM GLO-30 | AWS S3 abierto (Range 206) | **VERIFIED** |
| DEM | 90 m | Copernicus DEM GLO-90 | AWS S3 | **VERIFIED** |
| DEM | 30 m | SRTM GL1 | Earthdata Login | **DOCUMENTED** (login) |
| DEM | 30 m | NASADEM | LP DAAC (login) | **DOCUMENTED** |
| DSM | 30 m | ALOS World 3D | JAXA (registro) | **DOCUMENTED** (URL 404 hoy) |
| DEM nacional | no publicada | CNR | Compra/convenio | **RESTRICTED** |
| Curvas de nivel | 1:25k / 1:50k | CNR | Compra | **RESTRICTED** |
| Pendiente, orientación, hillshade, clases de relieve | 30 m | Derivados AGROSV del DEM | Local | **VERIFIED** (Fase 1) |

**Naturaleza del DEM:** Copernicus GLO-30 es un **DSM** (superficie), no un DTM:
incluye vegetación y edificios. La pendiente derivada está sesgada en zonas
urbanas y boscosas. Para hidrología se usa el DEM tal cual con esa advertencia.

**Comparación recomendada:** Copernicus 30 m vs SRTM 30 m vs NASADEM en un AOI
con relieve fuerte (volcán de Santa Ana o cordillera de Apaneca) para cuantificar
la discrepancia vertical antes de elegir el DEM de referencia. No se declara
«el mejor DEM» sin esa prueba.

### 3.1 Geología, fallas y amenazas

| Capa | Fuente | Escala | Acceso | Estado |
|---|---|---|---|---|
| Geología general | SNET/MARN | no publicada | Consulta | **DOCUMENTED** |
| Geología 1:100.000 | CNR | 1:100k | Compra ($30/hoja) | **RESTRICTED** |
| Fallas y estructuras | MARN/SNET | no publicada | PDF/visor | **DOCUMENTED** |
| Susceptibilidad a deslizamientos | MARN | **1:50.000** | PDF/visor | **DOCUMENTED** |
| Susceptibilidad a inundación | MARN | no publicada | PDF/visor | **DOCUMENTED** |
| Erosión (RUSLE) | MARN | 2015 | PDF | **VERIFIED** (PDF) |
| Volcanes | MARN/SNET | mapas por volcán | PDF/JPG | **DOCUMENTED** |

**Regla:** un PDF vectorizado es un **derivado AGROSV**, no un producto del MARN.
Se etiqueta como tal y se registra la escala de digitalización.

---

## 4. Cobertura y uso del suelo

| Producto | Resolución | Cobertura temporal | Acceso | Estado |
|---|---|---|---|---|
| ESA WorldCover | 10 m | 2020, 2021 | Descarga | **VERIFIED** (portal) |
| Dynamic World | 10 m | 2015–presente | Earth Engine | **VERIFIED** (portal) |
| Copernicus Global Land Cover | 100 m | anual | Descarga | **VERIFIED** (portal) |
| Hansen/GFW | 30 m | 2000–presente | Descarga | **VERIFIED** (portal) |
| MAG — mapas temáticos | PDF | sin fecha clara | 200 | **VERIFIED** (documento) |
| MAG — granos básicos | PDF, 1.362.195 B | — | 200 | **VERIFIED** |
| MAG — frutales | PDF, 3.939.575 B | — | 200 | **VERIFIED** |
| MAG — hortalizas | PDF, 6.282.423 B | — | 200 | **VERIFIED** |
| MAG — suelos | PDF, 1.324.595 B | — | 200 | **VERIFIED** |
| MAG — variables climáticas | PDF, 1.452.603 B | — | 200 | **VERIFIED** |
| OSM `landuse=farmland` | vectorial | actual | Overpass/Geofabrik | **VERIFIED** (cobertura insuficiente) |

**Cobertura OSM:** en el bounding box nacional solo hay ~1.554 `ways` con
`landuse=farmland` (medición de fase previa). El Salvador tiene ~293.000 mz de
maíz. OSM **no** sirve para delimitar cultivos.

**Cuidado terminológico:** «cobertura vegetal» (NDVI, WorldCover «crops») no es
«cultivo agrícola confirmado». El mapa temático del MAG es cartografía de zonas
productoras, no un inventario parcelario.

---

## 5. Descargas efectivamente disponibles

| Recurso | URL | Tamaño / estado |
|---|---|---|
| OSM shapefiles por capa | `download.geofabrik.de/central-america/el-salvador/el-salvador-latest-free.shp.zip` | **206**, 88.096.457 B anunciados |
| OSM PBF | `…/el-salvador/el-salvador-latest.osm.pbf` | **404** (ruta antigua y nueva) |
| Directorio Geofabrik SV | `download.geofabrik.de/central-america/el-salvador/` | 200, 32.112 B |
| Límite nacional | geoBoundaries `gjDownloadURL` | 200, 321.639 B (muestra) |
| Copernicus DEM 30 m | `copernicus-dem-30m.s3.amazonaws.com/...` | 206 (Range) |
| Copernicus DEM 90 m | `copernicus-dem-90m.s3.amazonaws.com/...` | 206 (Range) |

**Cambio de ruta detectado:** el extracto de El Salvador dejó de estar en
`central-america/el-salvador-latest.osm.pbf` y pasó a un subdirectorio propio.
Un pipeline con la ruta antigua falla con 404: hay que fijar la ruta nueva y
verificarla en cada ejecución.

---

## 6. Ruta de integración territorial

1. **Consolidar** una tabla de correspondencia 262 distritos ↔ 44 municipios ↔
   14 departamentos, con fuente oficial (BCR/CNR) y hash.
2. **Solicitar** los códigos de ubicación geográfica al CNR.
3. **Validar** la capa histórica de 272 polígonos contra la tabla oficial y
   documentar las diferencias.
4. **No publicar** límites municipales 2023 derivados de disolver distritos por
   nombre sin verificación geométrica.
5. **Mantener** las capas OSM en un GeoPackage separado por licencia ODbL.
