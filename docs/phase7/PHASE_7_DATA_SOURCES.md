# Fase 7 — fuentes de datos

**Estado:** ninguna fuente satelital ni fitosanitaria nueva está integrada. Este
documento distingue evaluación, adaptador y datos realmente presentes.

## Fuentes nacionales

| Fuente | Uso previsto | Acceso | Estado |
|---|---|---|---|
| MARN / SNET — estaciones y series | observación meteorológica e hidrológica | web; series por solicitud | `access_pending` |
| MARN — D3-DOA (observación atmosférica) | productos nacionales de teledetección | visor web; sin API confirmada | `access_pending` |
| CENTA — laboratorio de suelos y guías técnicas | validación edáfica y recomendaciones | solicitud institucional | `access_pending` |
| MAG — estadísticas y avisos | producción y sanidad | publicaciones web | evaluado, no ingerido |
| BCR — comercio y censo agropecuario | contexto económico | publicaciones | fuera de alcance de Fase 7 |
| OIRSA — programas fitosanitarios | registros regionales | web | evaluado; usado como referencia bibliográfica |
| Universidades y centros públicos | investigación local | publicaciones | no integrado |
| Asamblea Legislativa — Decreto 762 | correspondencia municipal 2023 | publicación oficial | **adquirida** (fase de acceso de datos) |

## Teledetección internacional

| Fuente | Resolución | Cobertura histórica | Licencia | Estado |
|---|---|---|---|---|
| Sentinel-2 MSI | 10/20/60 m | 2015– | Copernicus, atribución | adaptador local, sin ingesta |
| Sentinel-1 C-SAR | 10/40 m | 2014– | Copernicus | evaluado |
| Landsat 8/9 | 30 m (térmico 100) | 2013– / 2021– | dominio público | evaluado |
| MODIS | 250–1000 m | 2000– | abierto NASA | evaluado |
| VIIRS | 375/750 m | 2012– | abierto NASA/NOAA | evaluado |
| Copernicus Data Space | — | — | términos Copernicus | catálogo planificado |
| NASA Earthdata | — | — | abierto con registro | catálogo planificado |
| USGS EarthExplorer | — | — | según producto | catálogo planificado |
| Google Earth Engine | — | — | términos Google | opcional, no configurado |

## Clima y agricultura

| Fuente | Variables | Estado |
|---|---|---|
| CHIRPS | precipitación | presente en Fase 4 como muestra; no usado como observación de Fase 7 |
| GPM IMERG | precipitación | evaluado, no integrado |
| ERA5 / AgERA5 | meteorología | evaluado, no integrado |
| NOAA | clima y ENSO | evaluado, no integrado |
| FAO GIEWS | avisos alimentarios | evaluado, no integrado |
| FAO WaPOR | ET y biomasa | evaluado, no integrado |
| CABI Compendium | fichas de plagas/enfermedades | **referencia citada** |
| IPPC | normas y diagnósticos | referencia citada |
| CGIAR | investigación | no integrado |

## Qué significa “integrado”

Solo se declara integrado un dataset cuyos archivos están presentes, el proceso
de lectura funciona y la procedencia queda registrada. En Fase 7:

- **datos satelitales integrados: ninguno**;
- **datos fitosanitarios integrados como observación: ninguno** (el catálogo es
  conocimiento bibliográfico, no un registro de incidencia);
- **correspondencia municipal 2023: adquirida** en la etapa de acceso de datos,
  con SHA-256 y validación 14/44/262.

## Consecuencia

Los motores funcionan con entradas aportadas por el usuario y con fixtures
sintéticos en las pruebas. No se presentan resultados de fixtures como
observaciones de El Salvador.
