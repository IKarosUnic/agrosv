# Procedencia de los datos — AGROSV Fase 1

Regla de Fase 0 (`DATA_PIPELINE.md` §9): **una cifra sin manifiesto no es
publicable**. Cada capa procesada lleva un sidecar `.provenance.json` con
fuente, licencia, resolución, transformación, versiones de software y
`artifact_sha256`. La API expone estos metadatos en `/api/meta`.

## Resumen

| Capa | Fuente | Licencia | Resolución nativa | Archivo procesado |
|---|---|---|---|---|
| Límites ADM0/ADM1/ADM2 | geoBoundaries gbOpen | CC BY-SA 2.0 | vectorial, escala no declarada | `territory.gpkg` |
| Elevación | Copernicus DEM GLO-30 | DLR/Airbus, uso con atribución | 1 arcsec (~30 m) | `dem30_wgs84.tif` |
| Derivadas topográficas | AGROSV sobre el DEM | obra derivada | 30 m (EPSG:32616) | `slope_deg.tif`, `aspect_deg.tif`, `hillshade.tif`, `relief_class.tif` |
| Infraestructura | OpenStreetMap vía Geofabrik | ODbL 1.0 | vectorial OSM | `infrastructure.gpkg` |
| Suelos 0–30 cm | SoilGrids 2.0 (ISRIC) | CC BY 4.0 | 250 m (Goode Homolosine) | `soils/rasters/*.tif` |

## 1 · Límites administrativos

- **Origen**: geoBoundaries `gbOpen`, release de El Salvador (`SLV-ADM0/1/2`).
  `scripts/download_data.sh territory` reproduce la descarga.
- **Licencia**: CC BY-SA 2.0. Los límites de gbOpen derivan de OpenStreetMap vía
  osm-boundaries.com; la obra derivada mantiene la misma licencia.
- **Transformaciones** (`scripts/01_territory.py`): normalización de nombres →
  asignación de códigos ISO 3166-2:SV → dissolve de ADM1 para el límite
  nacional → join espacial de ADM2 a su departamento → validación.
- **Decisión relevante**: ADM0 de origen mide 25.339 km² porque incluye
  4.372,6 km² de aguas territoriales. El límite nacional publicado se deriva
  **por dissolve de ADM1** (20.966,4 km², −0,35 % frente a los 21.041 km²
  oficiales). Ver ADR-001.
- **ADM2**: 272 polígonos con `official=false`, `quality=name-missing` en 10 de
  ellos; cubren el 97,22 % del territorio derivado. Son los municipios
  **anteriores a la reforma de 2023**, no los 44 vigentes.

## 2 · Topografía

- **Origen**: Copernicus DEM GLO-30, bucket público
  `copernicus-dem-30m.s3.amazonaws.com`. 8 teselas de 1°×1° (N13/N14 ×
  W088–W091), ~273 MB, leídas por ventana desde `data/raw/copdem30`.
- **Por qué no CDSE**: desde el 28 de julio de 2026 el acceso a Copernicus DEM
  30 m está restringido en el Copernicus Data Space; AWS Open Data sigue
  ofreciendo el mismo producto sin autenticación (verificado en Fase 0).
- **Naturaleza del dato**: es un **DSM** (modelo de superficie), no un DTM:
  incluye dosel vegetal y edificaciones. La elevación máxima (2.725 m) es algo
  inferior a la cota del cerro El Pital (~2.730 m) por muestreo y por el propio
  DSM.
- **Derivadas** (`scripts/02_topography.py`), calculadas en EPSG:32616:
  - pendiente y orientación por gradiente central sobre la malla métrica de
    30 m; celdas cuyo vecindario 3×3 toca un borde o nodata se marcan nodata.
  - hillshade con azimut 315° y altitud solar 45° (convención ESRI): es una
    **visualización**, no una variable física.
  - clases de relieve por umbrales de pendiente (0-2, 2-5, 5-12, 12-25, 25-45,
    >45°); "relieve pronunciado" = ≥12°.
  - Los GeoTIFF se escriben como COG (DEFLATE, overviews promedio).
- **Escalas**: pendiente Int16 ×0,01; orientación Uint16 ×0,1; hillshade Uint8;
  clases Uint8. Nodata: −32768 / 65535 / 0 / 255 respectivamente.

## 3 · Infraestructura (OpenStreetMap)

- **Origen**: extracto de Geofabrik `el-salvador-latest.osm.pbf`
  (`timestamp` OSM registrado en `infrastructure_stats.json`), 35,2 MB.
- **Licencia**: ODbL 1.0. La base derivada queda sujeta a ODbL: debe ofrecerse
  bajo la misma licencia y conservar «© OpenStreetMap contributors».
- **Extracción** (`scripts/03_infrastructure.py`): lectura del PBF con el driver
  OSM de GDAL, filtros por etiqueta, clasificación y **recorte por intersección
  geométrica** contra el territorio (no `gpd.clip`, que parte las líneas y
  duplica filas: 4.984 → 15.148). Una vía que cruza la frontera queda truncada.
- **Capas**: `roads` (jerarquía arterial/colectora/local/servicio/pista/senda),
  `waterways`, `water_bodies`, `settlements`, `infrastructure` (salud,
  educación, transporte, energía, agua, industria) y `power_lines`.
- **Sin datos inferidos**: solo se publican elementos etiquetados en el
  extracto; no se completa ninguna capa por interpolación.

## 4 · Suelos

- **Origen**: SoilGrids 2.0 (ISRIC), WebDAV `files.isric.org`, VRT globales en
  Interrupted Goode Homolosine, 250 m. La API REST de SoilGrids devolvía
  `"mean": null` (servicio suspendido) durante Fase 0, por eso se usa WebDAV.
- **Volumen**: se descargan 138 teselas de 600×600 (de 7.692 por capa) — solo
  las que cubren El Salvador. Descargar los VRT completos serían ~27 GB.
- **Licencia**: CC BY 4.0.
- **Profundidad**: 0–30 cm como media ponderada por espesor de 0–5 (5/30),
  5–15 (10/30) y 15–30 cm (15/30).
- **Conversiones**: pH ×0,1; SOC dg/kg → g/kg (÷10); N cg/kg → g/kg (÷100);
  arcilla/arena/limo g/kg → % (÷10). Se almacenan como Int16 con `scale`
  declarada en el COG.
- **Advertencia**: son **predicciones de un modelo global**, no mediciones de
  laboratorio. No sustituyen al Mapa Digital de Suelos del CENTA.

### Fuentes nacionales investigadas

| Fuente | Estado | Motivo |
|---|---|---|
| Mapa Digital de Suelos (CENTA/MAG/CRS, ~11.000 muestras) | identificado, **no integrado** | plataforma ArcGIS Hub sin endpoint estable de descarga ni licencia explícita de reutilización; requiere contacto institucional |
| *Soil in El Salvador* (World Bank Data Catalog, 2017, CC BY 4.0) | identificado, **no integrado** | clasificación de suelos en polígonos; se integrará como capa de clases, separada de las predicciones continuas |
| Mapa de suelos FAO/UNESCO (mapa impreso escaneado) | descartado | no georreferenciado |

Ninguna de estas fuentes se presenta como integrada ni se usa para completar
huecos de SoilGrids.

## 5 · Software

Versiones registradas en cada manifiesto (`software`): Python 3.12.3, GDAL
3.12.2, rasterio 1.5.2, geopandas 1.2.0, shapely 2.2.0, pyproj 3.8.0, pyogrio
0.13.0, osmium 4.3.2.

## Reproductibilidad

```bash
bash scripts/download_data.sh all
.venv/bin/python scripts/01_territory.py
.venv/bin/python scripts/02_topography.py
.venv/bin/python scripts/03_infrastructure.py
.venv/bin/python scripts/04_soils.py
```

Los hashes SHA-256 de cada artefacto están en los `.provenance.json`; el del
PBF de OSM y el de los tiles del DEM también quedan en los `*_stats.json`.
