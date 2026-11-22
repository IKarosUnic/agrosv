# DATA_SOURCE_REGISTRY — AGROSV Fase 3

**Versión:** 3.0 · **Fecha de consulta:** 2026-11-22 · **Sondas:** 118
ejecutadas — 85 VERIFIED, 14 DOCUMENTED, 11 UNAVAILABLE, 7 RESTRICTED,
1 PENDING_VALIDATION.
**Evidencia:** `research/raw/phase3/probes_20261122_r3.json` (+ líneas base
`…_baseline.json` y `…_r2.json`), reproducibles con
`scripts/06_probe_phase3_sources.py`.

Este registro **amplía** [`../../DATA_SOURCE_REGISTRY.md`](../../DATA_SOURCE_REGISTRY.md)
sin borrar sus estados. Cuando una comprobación nueva contradice una anterior, se
señala explícitamente en §5.

---

## 1. Estados y columnas

| Estado | Significado |
|---|---|
| **VERIFIED** | Petición real con respuesta válida y contenido utilizable. |
| **DOCUMENTED** | Documentación oficial localizada; acceso a datos no probado. |
| **RESTRICTED** | Existe pero exige compra, registro, credenciales o autorización. |
| **UNAVAILABLE** | Ningún medio probado devolvió el recurso (DNS, TLS, 5xx, 404 de la ruta documentada). |
| **PENDING_VALIDATION** | Evidencia insuficiente o contradictoria. |

`VERIFIED` describe **el canal**, no la calidad científica. Caduca: se repite en
cada fase (R-10).

Abreviaturas de la tabla: **Nd** = no declarada; **Nv** = no verificado;
**—** = no aplica.

---

## 2. Fuentes nacionales

| ID | Nombre / institución | Contenido | Cobertura · resolución | Formato · acceso | Auth / API | Licencia | Coste | Calidad · incertidumbre | Pub/Act | Consulta | Evidencia | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `cnr_home` | CNR — portal | Servicios registrales y cartográficos | Nacional | HTML | No | Nd | $0 | Institucional | — | 2026-11-22 | 200, 130.722 B | **VERIFIED** |
| `cnr_servicios` | CNR — catálogo IGCN | Productos por compra | Nacional | HTML | No | Nd | — | — | — | 2026-11-22 | 200, 131.111 B | **VERIFIED** |
| `cnr_descargas` | CNR — «Descargas» | **Solo documentos administrativos** (licitaciones, UACI, publicaciones); 0 enlaces geo | Nacional | HTML + gestor WP | No | Nd | $0 | No es fuente geoespacial | — | 2026-11-22 | 200, 132.833 B; 0 `.zip/.shp/.gpkg/.csv` | **VERIFIED** (canal) / **sin datos** |
| `cnr_elsalvadormaps` | CNR — *El Salvador Maps* | Ortofoto, LiDAR, MDT/MDS, 3D, catastro | Nacional · hasta 10 cm (declarado) | Visor | Sesión | Nd | Desconocido | Ficha técnica no pública | — | 2026-11-22 | **TLS inválido**; con `verify=False` 200 (4.326 B) | **DOCUMENTED** |
| `mag_home` | MAG — portal | Institución | Nacional | HTML | No | Nd | $0 | — | — | 2026-11-22 | 200, 123.312 B | **VERIFIED** |
| `mag_estadisticas` | MAG/DGEA — estadísticas | Producción, precios, SIG | Nacional, dept., municipio | HTML → PDF | No | Nd | $0 | PDF maquetado | — | 2026-11-22 | 200, 116.135 B | **VERIFIED** |
| `mag_anuario_2021_22` | MAG — Anuario 2021-2022 | Superficie, producción, precios, comercio, mapas | Nacional/dept./municipio | PDF | No | Nd | $0 | Alta (oficial); extracción manual | 2022-12 | 2026-11-22 | 200, 4.321.899 B | **VERIFIED** |
| `mag_anuario_2022_23` | MAG — Anuario 2022-2023 | Ibídem | Ibídem | PDF | No | Nd | $0 | — | 2024-02 | 2026-11-22 | **404** en la URL indexada | **DOCUMENTED** |
| `mag_precios_informe` | MAG — Informes mensuales de precios | Precios mayorista/consumidor | Nacional, plazas | HTML + 48 PDF | No | Nd | $0 | Serie 2020–2023 | — | 2026-11-22 | 200, 126.087 B | **VERIFIED** |
| `mag_boletin_precios_2023_12` | MAG — Boletín dic-2023 | Precios, insumos, comercio | Nacional | PDF | No | Nd | $0 | Alta; tablas maquetadas | 2023-12 | 2026-11-22 | 200, 5.869.837 B | **VERIFIED** |
| `mag_insumos_guia` | MAG — Guía de precios de insumos | Semillas, fertilizantes | Nacional | PDF | No | Nd | $0 | Serie 2019–2023 | — | 2026-11-22 | 200, 111.731 B | **VERIFIED** |
| `mag_mapas_page` | MAG — mapas temáticos | Granos, frutales, hortalizas, suelos, clima, pecuario | Nacional | HTML + 8 PDF | No | Nd | $0 | Cartografía sin metadatos GIS | — | 2026-11-22 | 200, 112.351 B | **VERIFIED** |
| `mag_pdf_granos` | MAG — zonas de granos básicos | Zonas productoras | Nacional | PDF | No | Nd | $0 | No es capa GIS | — | 2026-11-22 | 200, 1.362.195 B | **VERIFIED** |
| `mag_pdf_suelos` | MAG — mapa de suelos | Suelos (temático) | Nacional | PDF | No | Nd | $0 | Escala no declarada | — | 2026-11-22 | 200, 1.324.595 B | **VERIFIED** |
| `mag_pdf_clima` | MAG — variables climáticas | Clima (temático) | Nacional | PDF | No | Nd | $0 | Escala no declarada | — | 2026-11-22 | 200, 1.452.603 B | **VERIFIED** |
| `mag_pdf_hortalizas` | MAG — zonas de hortalizas | Zonas productoras | Nacional | PDF | No | Nd | $0 | 6,3 MB | — | 2026-11-22 | 200, 6.282.423 B | **VERIFIED** |
| `mag_pdf_frutales` | MAG — zonas de frutales | Zonas productoras | Nacional | PDF | No | Nd | $0 | — | — | 2026-11-22 | 200, 3.939.575 B | **VERIFIED** |
| `mag_censo2007` | MAG — IV Censo Agropecuario 2007-08 | Resultados nacional/dept./municipio | Nacional | PDF | No | Nd | $0 | Serie histórica | 2008 | 2026-11-22 | 200, 116.135 B (página) | **VERIFIED** |
| `centa_home` | CENTA — portal | Institución | Nacional | HTML | No | Nd | $0 | — | — | 2026-11-22 | **403** (bloqueo a no navegador) | **RESTRICTED** |
| `centa_suelos` | CENTA — Mapa Digital de Suelos | Textura, pH, MO, nutrientes, erosión | Nacional · escala no verificada | HTML/visor | No | Nd | $0 | ~11.000 muestras (declarado) | Pub. 2026-06-05 | 2026-11-22 | **403** | **PENDING_VALIDATION** |
| `centa_hub` | CENTA — Portal de Mapas Digitales (ArcGIS Hub) | Suelos, clima, relieve, potencial de cultivos | Nacional | Hub | No | Nd | $0 | Anuncia descarga | — | 2026-11-22 | 200; `api/search/v1` → **0 ítems** | **PENDING_VALIDATION** |
| `bcr_geoportal` | BCR — Geoportal | Cartografía censal, tabulados | Nacional→distrito | HTML/dashboards | No | Nd (dato abierto) | $0 | Alta (oficial) | — | 2026-11-22 | 200, 106.062 B | **VERIFIED** |
| `bcr_poblacion_tabulados` | BCR/ONEC — CPV 2024 | Tabulados y base de datos | Nacional→distrito | XLSX/PDF/CSV/SPSS | No | Nd | $0 | Microdatos anonimizados | 2024 | 2026-11-22 | 200, 308.821 B | **VERIFIED** |
| `bcr_agropecuario` | BCR — CAP 2025 | Resultados censo agropecuario | Nacional/dept. | HTML/dashboards | No | Nd | $0 | Agregados | 2025–2026 | 2026-11-22 | 200, 407.497 B | **VERIFIED** |
| `bcr_cap_documentacion` | BCR — documentación CAP (3.ª entrega) | Metodología y resultados | Nacional/dept. | HTML + PDF | No | Nd | $0 | Alta | 2026-11 | 2026-11-22 | 200, 407.524 B | **VERIFIED** |
| `bcr_cap_seg_docs` | BCR — documentación CAP (2.ª entrega) | Metodología y resultados | Nacional/dept. | HTML + PDF | No | Nd | $0 | Alta | 2026-03 | 2026-11-22 | 200 | **VERIFIED** |
| `bcr_cap_primera_pdf` | BCR — 1.ª entrega CAP | Pecuario y pesca | Nacional/dept. | PDF | No | Nd | $0 | Alta | 2026-01 | 2026-11-22 | 206, `application/pdf` | **VERIFIED** |
| `bcr_cap_segunda_pdf` | BCR — 2.ª entrega CAP | Granos, café, caña, acuicultura | Nacional/dept. | PDF | No | Nd | $0 | Alta | 2026-03 | 2026-11-22 | 200, `application/pdf` | **VERIFIED** |
| `bcr_cap_tercera_pdf` | BCR — 3.ª entrega CAP | Hortalizas, frutales, forestal, pesca | Nacional/dept. | PDF | No | Nd | $0 | Alta | 2026-11 | 2026-11-22 | 200, `application/pdf` | **VERIFIED** |
| `snet_hidrologia_ver` | MARN/SNET — hidrología | Atlas, red hídrica | Nacional | HTML | No | Nd | $0 | Sin series descargables | — | 2026-11-22 | 200, 33.552 B | **VERIFIED** (portal) |
| `snet_meteorologia` | MARN/SNET — meteorología | Estaciones, pronóstico | Nacional | HTML | No | Nd | $0 | Sin datos crudos verificados | — | 2026-11-22 | 200, 31.535 B | **VERIFIED** (portal) |
| `snet_geologia` | MARN/SNET — geología | Amenaza por deslizamientos | Nacional · 1:50.000 | HTML/PDF | No | Nd | $0 | Sin metadatos completos | — | 2026-11-22 | 200, 21.576 B | **DOCUMENTED** |
| `marn_home` | MARN — portal | Institución | Nacional | HTML | No | Nd | $0 | — | — | 2026-11-22 | **503** (2 intentos) | **UNAVAILABLE** |
| `marn_geoportal` | MARN — geoportal | Servicios REST | Nacional | REST | Nd | Nd | $0 | — | — | 2026-11-22 | **522** | **UNAVAILABLE** |
| `anda_home` | ANDA — portal | Agua potable | Nacional | HTML | No | Nd | $0 | — | — | 2026-11-22 | **403** | **RESTRICTED** |
| `oirsa_home` | OIRSA — portal | Alertas fitosanitarias | Regional | HTML/JS | No | Nd | $0 | Sin API verificada | — | 2026-11-22 | 200 (372 B, app JS) | **DOCUMENTED** |
| `ippc_sv` | IPPC — El Salvador | Estatus fitosanitario | Nacional | HTML | No | Abierta (FAO) | $0 | 0 reportes de plagas al consultar | — | 2026-11-22 | 200, 82.958 B | **VERIFIED** |
| `isc_cafe` | ISC — café | Roya, broca, boletines | Nacional | HTML | Sesión | Nd | $0 | — | — | 2026-11-22 | **403** | **RESTRICTED** |
| `one_home` | ONEC — estadísticas | Estadísticas oficiales | Nacional | — | — | — | — | Dominio no resuelve | — | 2026-11-22 | **DNS falla** | **UNAVAILABLE** |
| `rmgir_subcuencas` | RMGIR — subcuencas SV (tercero) | Subcuencas | Nacional | REST/GeoJSON | No | Nd | $0 | Procedencia no MARN | — | 2026-11-22 | **404** (ruta documentada) | **UNAVAILABLE** |
| `osm_sv` | OpenStreetMap — extracto SV | Vialidad, hidrografía, lugares | Nacional | `.shp.zip` / `.osm.pbf` | No | ODbL 1.0 | $0 | Cobertura agrícola insuficiente | diaria | 2026-11-22 | SHP **206**, 88.096.457 B; PBF **404** | **VERIFIED** (SHP) |
| `nemotron-sv` | NVIDIA — Nemotron Personas SV | 148.000 personas sintéticas | Nacional · 44 municipios | Parquet/JSON | HF API | CC BY 4.0 | $0 | Sintético, no representativo | 2026-06-05 | 2026-11-22 | 200; 3 filas muestreadas | **VERIFIED** |
| `geoboundaries` | geoBoundaries — SLV | ADM0/ADM1/ADM2 | Nacional | GeoJSON/SHP | REST | CC BY-SA 2.0 | $0 | ADM2 2021 no refleja 2023 | 2021 | 2026-11-22 | 200, 1.702 B; ADM0 321.639 B | **VERIFIED** |

---

## 3. Fuentes internacionales

| ID | Nombre / institución | Contenido | Cobertura · resolución | Temporal | Formato · acceso | Auth | Licencia | Coste | Calidad · incertidumbre | Consulta | Evidencia | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `copdem30` | Copernicus DEM GLO-30 | Elevación (DSM) | Global · 30 m | 2011–2015 | COG GeoTIFF · S3 | No | Copernicus DEM (atribución) | $0 | Buena; es DSM | 2026-11-22 | 206 (Range) | **VERIFIED** |
| `copdem90` | Copernicus DEM GLO-90 | Elevación (DSM) | Global · 90 m | 2011–2015 | COG GeoTIFF · S3 | No | Ibídem | $0 | Menor detalle | 2026-11-22 | 206 | **VERIFIED** |
| `srtm` | NASA SRTM GL1 | Elevación | Global 60N–56S · 30 m | 2000 | HGT/GeoTIFF | Earthdata | Abierta | $0 | Antigua; vacíos urbanos | 2026-11-22 | landing 404 | **DOCUMENTED** (login) |
| `nasadem` | NASA NASADEM | Elevación | Global · 30 m | 2000 | GeoTIFF | Earthdata | Abierta | $0 | Mejor que SRTM | 2026-11-22 | 200, 301.402 B | **DOCUMENTED** |
| `alos_aw3d30` | JAXA ALOS World 3D | DSM | Global · 30 m | 2006–2011 | GeoTIFF | Registro | JAXA (atribución) | $0 | — | 2026-11-22 | **404** | **DOCUMENTED** |
| `opentopography` | OpenTopography | Agregador DEM/LiDAR | Global | — | API | Clave API | Según dataset | $0/no comercial | — | 2026-11-22 | 200, 126.503 B | **DOCUMENTED** |
| `soilgrids` | SoilGrids 2.0 (ISRIC) — WebDAV | 13 propiedades, 6 profundidades | Global · 250 m | 2017–2022 | VRT + COG | No | CC BY 4.0 | $0 | Error mayor en relieve | 2026-11-22 | 206; listado 15 dirs | **VERIFIED** |
| `soilgrids_rest` | SoilGrids 2.0 — REST | Ibídem | Global · 250 m | — | JSON | No | CC BY 4.0 | $0 | **Devuelve null** | 2026-11-22 | 200 con `mean:null` | **PENDING_VALIDATION** |
| `isric_wosis` | ISRIC WoSIS | Perfiles medidos | Global | 1930– | Catálogo | No | CC BY 4.0 (verificar) | $0 | Datos puntuales | 2026-11-22 | 200, 15.234 B | **DOCUMENTED** |
| `fao_hwsd` | FAO HWSD v2 | Suelos armonizados | Global · ~1 km | 2023 | Raster/vector | No | FAO (verificar) | $0 | Baja resolución | 2026-11-22 | **404** | **UNAVAILABLE** |
| `fao_glosis` | FAO GLOSIS | Suelos | Global | — | OGC | — | — | — | DNS falla | 2026-11-22 | ConnectError | **UNAVAILABLE** |
| `hydrosheds` | HydroSHEDS | Red hídrica | Global | 2000 | SHP/GeoTIFF | No | Verificar EULA | $0 | Buena topología | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `hydrobasins` | HydroBASINS | Cuencas anidadas | Global | — | SHP | No | Ibídem | $0 | No oficial SV | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `hydroatlas` | HydroATLAS | Atributos por cuenca | Global | — | SHP/CSV | No | Ibídem | $0 | Derivado | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `fao_aquastat` | FAO AQUASTAT | Agua y riego por país | Global | anual | Web/CSV | No | FAO (verificar) | $0 | Agregado nacional | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `fao_gmia` | FAO GMIA | Superficie regada | Global · ~10 km | 2005 | Raster | No | FAO | $0 | Antiguo | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `jrc_gsw` | JRC Global Surface Water | Agua superficial | Global · 30 m | 1984–2021 | Raster | No | Abierta (atribución) | $0 | Detecta agua, no uso | 2026-11-22 | 200, 85.949 B | **VERIFIED** |
| `whymap` | WHYMAP (BGR/UNESCO) | Acuíferos transfronterizos | Global | 2008– | PDF/GIS | No | Abierta | $0 | Muy general | 2026-11-22 | 200 | **VERIFIED** |
| `wri_aqueduct` | WRI Aqueduct | Estrés hídrico | Global | 2023 | Web/CSV | No | CC BY 4.0 | $0 | Modelado | 2026-11-22 | 200 | **VERIFIED** |
| `chirps3` | CHIRPS v3 (UCSB CHC) | Precipitación | 60N–60S · 0,05° | 1981– (rnl) / 1998– (sat) | GeoTIFF/NetCDF/COG | No | Abierta (verificar aviso) | $0 | Diario desagregado; nativo pentadal | 2026-11-22 | 200, 14.000.124 B validado | **VERIFIED** |
| `nasa_power` | NASA POWER | T, precip, radiación, ET₀ | Punto · 0,5° | 1981– | JSON/CSV | No | Abierta, uso comercial permitido | $0 | Reanálisis; no parcela | 2026-11-22 | 200; muestra 128.012 B | **VERIFIED** |
| `open_meteo` | Open-Meteo | ERA5/IFS, ET₀ FAO-56 | 0,1°/9 km | 1940– | JSON | No | CC BY 4.0; gratuito **no comercial** | $0 / plan pago | Agregador; dependencia externa | 2026-11-22 | 200; muestra 92.997 B | **VERIFIED** |
| `agera5` | AgERA5 (C3S) | T, precip, ET₀, radiación | Global · 0,1° | 1979– | NetCDF/Zarr | Token CDS | CC BY 4.0 | $0 | Calibrado para agro | 2026-11-22 | catálogo 200 | **RESTRICTED** |
| `era5_land` | ERA5-Land | Reanálisis de superficie | Global · 0,1° | 1950– | NetCDF/GRIB | Token CDS | CC BY 4.0 | $0 | Sin corrección topográfica | 2026-11-22 | catálogo 200 | **RESTRICTED** |
| `gpm_imerg` | NASA GPM IMERG | Precipitación | Global · 0,1° · 30 min | 2000– | HDF5/NetCDF | Earthdata | Abierta | $0 | Mejor para intensidad | 2026-11-22 | 200 (portal) | **RESTRICTED** |
| `noaa_cpc` | NOAA CPC Global Precipitation | Precipitación | Global · 0,5° | 1979– | NetCDF | No | Abierta | $0 | Gruesa | 2026-11-22 | 200 | **VERIFIED** |
| `worldclim_21` | WorldClim 2.1 | 19 bioclimáticas + futuro | Global · 30″ | 1970–2000, SSP | GeoTIFF | No | **No comercial, sin redistribución** | $0 | Interpolación | 2026-11-22 | 200 | **DOCUMENTED** |
| `gaez_v4` | FAO/IIASA GAEZ v4 | Aptitud y rendimiento potencial | Global · 5′/30″ | normales y escenarios | REST/WCS/TIFF | No | **No comercial, atribución** | $0 | Modelo global | 2026-11-22 | 200 | **DOCUMENTED** |
| `esgf_cmip6` | ESGF CMIP6 | GCM, SSP126/245/370/585 | ~100–200 km | 1850–2100 | NetCDF | Cuenta ESGF | Términos CMIP6 | $0 | Muy grueso para SV | 2026-11-22 | 200 | **DOCUMENTED** |
| `s2_l2a` | Sentinel-2 L2A | 13 bandas + SCL | Global · 10/20/60 m | 2015– | COG/STAC | No | Copernicus (atribución) | $0 | Nubes en época lluviosa | 2026-11-22 | STAC 200; COG 206 | **VERIFIED** |
| `s2_c1_l2a` | Sentinel-2 Collection-1 L2A | Ibídem | Global · 10 m | 2022– | COG/STAC | No | Ibídem | $0 | Colección vigente | 2026-11-22 | listada en catálogo | **VERIFIED** |
| `s1_grd` | Sentinel-1 IW GRD | VV/VH | Global · 10 m | 2014– | SAFE/COG | OAuth2 CDSE | Copernicus | $0 | Requiere proceso SAR | 2026-11-22 | catálogo CDSE 200 | **RESTRICTED** |
| `landsat_c2` | Landsat 8/9 Collection 2 | 7 bandas + QA | Global · 30 m | 1982– | COG | EarthExplorer | Dominio público | $0 | Serie larga | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `mod13q1` | MODIS MOD13Q1 | NDVI/EVI | Global · 250 m · 16 d | 2000–2026 | HDF | Earthdata | Abierta | $0 | **Terra cesa 2026-12-01** | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `esa_worldcover` | ESA WorldCover | Cobertura 11 clases | Global · 10 m | 2020–2021 | COG | No | CC BY 4.0 | $0 | 2 años | 2026-11-22 | 200 | **VERIFIED** |
| `dynamic_world` | Dynamic World | Cobertura probabilística | Global · 10 m | 2015– | Earth Engine | Google | CC BY 4.0 | $0 | Probabilidades, no clases | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `gfw_hansen` | Global Forest Watch | Cobertura forestal, alertas | Global · 30 m | 2000– | GeoTIFF/API | No | CC BY 4.0 | $0 | «Tree cover» ≠ bosque | 2026-11-22 | 200 | **VERIFIED** |
| `ghsl` | GHSL (JRC) | Asentamientos, población | Global · 10–100 m | 1975–2030 | Raster | No | Abierta | $0 | — | 2026-11-22 | 200 | **VERIFIED** |
| `worldpop` | WorldPop | Población en rejilla | Global · 100 m | 2000–2020 | GeoTIFF | No | CC BY 4.0 | $0 | Modelado | 2026-11-22 | 200 | **VERIFIED** |
| `faostat` | FAOSTAT | Producción, comercio, precios | Global por país | 1961– | API/CSV | No | FAO (verificar) | $0 | Agregado nacional | 2026-11-22 | API **521**; bulk **403** | **PENDING_VALIDATION** |
| `worldbank_api` | World Bank Open Data | Indicadores | Global por país | 1960– | JSON/CSV | No | CC BY 4.0 | $0 | Agregado | 2026-11-22 | 200; 14.891 B | **VERIFIED** |
| `gbif` | GBIF | Ocurrencias de especies | Global | 1600– | JSON/Parquet | No | Por registro | $0 | Sesgo de muestreo | 2026-11-22 | 200; 300 registros | **VERIFIED** |
| `protectedplanet` | Protected Planet (UNEP-WCMC) | Áreas protegidas | Global | — | Web/API | Token para API | No comercial | $0 | — | 2026-11-22 | 200; API **401** | **RESTRICTED** |
| `eppo_gd` | EPPO Global Database | Distribución de plagas | Global | — | Web | No | EPPO | $0 | Por país | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `cabi_cpc` | CABI CPC | Fichas de plagas | Global | — | Web | Suscripción | Propietaria | Pago | — | 2026-11-22 | **403** | **RESTRICTED** |
| `usda_psd` | USDA FAS PSD | Oferta/demanda mundial | Global | 1960– | Web/API | No | Dominio público (US Gov) | $0 | Agregado | 2026-11-22 | 200 | **VERIFIED** (portal) |
| `fao_ecocrop` | FAO EcoCrop | Requerimientos de cultivos | Global | — | Web | — | — | — | **Servicio retirado (503)** | 2026-11-22 | **503** | **UNAVAILABLE** |
| `google_weather` | Google Weather API | Condiciones y pronóstico | Global | 24 h histórico | JSON | Clave | ToS Google §21 | Por llamada | No sirve de archivo | 2026-11-22 | documentación 200 | **RESTRICTED** |

---

## 4. Ficha completa (plantilla obligatoria)

```yaml
id: soilgrids
name: SoilGrids 2.0
institution: ISRIC — World Soil Information
official_url: https://files.isric.org/soilgrids/latest/data/
description: Predicción global de propiedades del suelo por machine learning
variables: [bdod, cec, cfvo, clay, nitrogen, ocd, ocs, phh2o, sand, silt, soc, wrb]
coverage: global
spatial_resolution: 250 m
temporal_resolution: static (2017-2022)
publication_date: 2020 (v2.0)
update_date: continuous (latest)
format: VRT + COG GeoTIFF
access_method: HTTP/WebDAV
api: false (WebDAV); REST API suspendida
authentication: none
license: CC BY 4.0
restrictions: attribution required
cost: 0
quality: moderate; high uncertainty in complex terrain
uncertainty: Q0.05/Q0.5/Q0.95 published per property
consulted_at: 2026-11-22
verification_evidence: HTTP 206 on /phh2o/phh2o_0-5cm_mean.vrt; directory listing 200
status: VERIFIED
```

Toda fila de las tablas §2–§3 que no tenga un campo lo declara como `Nd`
(no declarado) o `Nv` (no verificado). No se rellena por inferencia.

---

## 5. Correcciones respecto a registros anteriores

| Afirmación previa | Verificación 2026-11-22 | Acción |
|---|---|---|
| SoilGrids ofrece `wv0010/wv0033/wv1500` utilizables por AquaCrop | **No existen** en `latest/data/`; 404 | Corregido en `SOIL_DATA_INVENTORY.md` §3.1; usar pedotransferencia |
| OSM Geofabrik en `central-america/el-salvador-latest.osm.pbf` | **404**; la ruta es `/central-america/el-salvador/…` y el PBF también da 404; el `.shp.zip` responde 206 (88 MB) | Actualizado; usar shapefiles |
| El Salvador Maps accesible | **Certificado TLS inválido** | Marcado DOCUMENTED, no automatizable |
| CNR tiene página de descargas geográficas | La página existe pero solo contiene documentos administrativos | Aclarado: no hay descarga geoespacial abierta |
| `rmgir` FeatureServer de subcuencas | **404** | Marcado UNAVAILABLE |
| CENTA publica capas descargables | El Hub responde 200 pero su API devuelve **0 ítems** | PENDING_VALIDATION |
| `one.gob.sv` operativo | **DNS no resuelve** | UNAVAILABLE; usar geoportal BCR |
| Anuario MAG 2022-2023 descargable | **404** en la URL indexada | DOCUMENTED; usar 2021-2022 |

---

## 6. Fuentes descartadas y por qué

| Fuente | Motivo |
|---|---|
| Google Weather API | ToS §21.1 prohíbe recrear servicio meteorológico; §21.2 exige borrar caché |
| FAO EcoCrop | Servicio retirado (503) |
| GADM | Licencia no comercial y sin redistribución; geoBoundaries cubre la necesidad |
| Planet | Comercial; no apto para producto abierto |
| WDPA API | Requiere token; usar descarga institucional con acuerdo |
| CABI CPC | Suscripción |

---

## 7. Reglas del registro

1. **R-11** Toda fila nueva exige sonda reproducible y fecha.
2. **R-12** Un `VERIFIED` que falle en la siguiente ronda cambia a `UNAVAILABLE`
   o `DOCUMENTED`; no se conserva «porque antes funcionaba».
3. **R-13** La licencia se escribe con el texto exacto cuando exista; si no,
   `Nd` y el dato queda restringido para redistribución.
4. **R-14** Ninguna fuente nacional se publica sin autorización escrita.
5. **R-15** Las fuentes sintéticas (Nemotron) se marcan siempre como sintéticas.
