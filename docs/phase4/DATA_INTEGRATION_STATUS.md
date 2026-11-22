# Estado de integración de datos

**Fase 4 — AGROSV** · Fuente: `data/metadata/datasets.json` (22 datasets) · Verificación: `Catalog.audit()` y `monitoring.json`

Este documento responde a una pregunta concreta: **¿qué datos se pueden usar hoy
y en qué condiciones?** No es una lista de deseos. Cada estado tiene evidencia
registrada; ninguno se elevó por haber sido importado.

## 1. Resumen

| Estado | N | Significado operativo |
|---|---|---|
| INTEGRATED | 7 | metadatos públicos y observaciones consultables por API |
| VALIDATED | 2 | calidad aprobada, sin carga en la base de consulta |
| DOWNLOADED | 1 | archivo presente; sin parseo/validación |
| PARSED | 1 | estructura leída; sin validación científica |
| ACCESS_PENDING | 2 | fuente identificada; acceso/licencia sin resolver |
| RESTRICTED | 4 | existe, pero su licencia/condiciones impiden el uso previsto |
| UNAVAILABLE | 3 | el servicio o dato ya no está disponible |
| REJECTED | 1 | descartado con motivo documentado |
| DISCOVERED | 1 | identificado, sin descarga ni acceso |

Auditoría: 22 fichas, 71 transiciones, `ok: true`. La auditoría es estructural;
no reevalúa la ciencia.

## 2. Ficha por dataset

| Dataset | Dominio | Estado | Nivel | Qué hay realmente |
|---|---|---|---|---|
| copdem30 | TERRITORIO | INTEGRATED | V1 | DEM 30 m y derivados (pendiente, aspecto, sombreado, relieve) |
| geoboundaries_adm1 | TERRITORIO | INTEGRATED | V1 | 14 departamentos; base del índice territorial |
| osm_sv | TERRITORIO | INTEGRATED | V1 | vialidad (extracto); precisión variable |
| soilgrids_2 | SUELOS | INTEGRATED | V1 | 6 propiedades 0–30 cm, 250 m, predicción global |
| nasa_power_point | CLIMA | INTEGRATED | V1 | 7.671 observaciones diarias en un punto |
| open_meteo_point | CLIMA | INTEGRATED | V1 | 12.785 observaciones diarias en un punto |
| gbif_sv | BIODIVERSIDAD | INTEGRATED | V1 | 300 ocurrencias; 1 fuera del bbox terrestre, marcada |
| chirps3 | CLIMA | VALIDATED | V1 | 1 día recortado a SV; no es serie nacional |
| worldbank_agri_share | AGRICULTURA | VALIDATED | V1 | indicador nacional anual (superficie agrícola, %) |
| sentinel2_c1_l2a | TERRITORIO | DOWNLOADED | V0 | metadatos STAC de escenas; no imágenes ni análisis |
| nemotron_sv | ECONOMÍA | PARSED | V0 | filas de muestra; sin validación |
| faostat | AGRICULTURA | ACCESS_PENDING | V0 | API/CSV identificados; condiciones por verificar |
| cnr_elsalvadormaps | TERRITORIO | ACCESS_PENDING | V0 | visor; sin capa descargable verificada |
| agera5 | CLIMA | RESTRICTED | V0 | requiere cuenta/token CDS |
| centa_suelos | SUELOS | RESTRICTED | V0 | visor/geodatabase sin acceso verificado |
| protectedplanet | BIODIVERSIDAD | RESTRICTED | V0 | API con token y uso no comercial |
| worldclim_21 | CLIMA | RESTRICTED | V0 | no comercial, sin redistribución |
| fao_ecocrop | AGRICULTURA | UNAVAILABLE | V0 | servicio retirado |
| mag_anuario_2022_23 | AGRICULTURA | UNAVAILABLE | V0 | PDF sin tabla legible verificada |
| marn_geoportal | HIDROLOGÍA | UNAVAILABLE | V0 | REST no verificable |
| soilgrids_rest | SUELOS | REJECTED | V0 | la consulta REST no entregó el producto esperado |
| hydrosheds | HIDROLOGÍA | DISCOVERED | V0 | identificado; EULA por revisar |

## 3. Qué se puede consultar hoy

`GET /api/data/observations` sirve **solo** datasets `INTEGRATED`:

| Dataset | Filas | Variables principales | Clase de evidencia |
|---|---|---|---|
| nasa_power_point | 7.671 | precipitación, temperatura máx/mín, humedad, viento, radiación | reanalysis |
| open_meteo_point | 12.785 | precipitación, temperatura máx/mín, ET0, viento | reanalysis |
| total | 20.456 | | |

Ocurrencias: 300 (GBIF). Territorios: 287 (1 país, 14 departamentos, 272
municipios históricos). Activos registrados: 22. Informes de calidad vigentes:
10 (todos `PASS` o `PASS_WITH_WARNINGS`; ninguno `FAIL` en la base).

Rásteres gestionados: 13 (5 del DEM/derivados, 6 de SoilGrids, 2 de CHIRPS). No
se sirven por API como descarga; solo metadatos.

## 4. Qué no está integrado y por qué

- **Límites municipales 2023, distritos, cuencas y áreas protegidas**: no hay
  capa verificada. El índice territorial no los inventa; la correspondencia
  2023 está `INCOMPLETE`.
- **Parcelas catastrales**: no hay información legalmente accesible.
- **Estaciones SNET/MARN y aforos**: sin acceso a series; por eso no hay
  validación climática contra observaciones.
- **Suelos CENTA**: restringido; SoilGrids es una predicción global, no un
  reemplazo equivalente.
- **Precios y fitosanidad**: no hay series tabuladas verificadas; el dominio
  tiene contrato, no datos.
- **CHIRPS nacional**: solo una muestra de un día; no se presenta como serie.
- **Sentinel-2**: solo metadatos STAC; no se descargaron ni procesaron imágenes.

## 5. Advertencias científicas

- **Resolución ≠ precisión**: SoilGrids a 250 m no tiene error de 250 m; el DEM a
  30 m no tiene exactitud de 30 m.
- **Reanálisis ≠ observación**: NASA POWER y Open-Meteo no son estaciones. La
  comparación entre ambos es una intercomparación (n = 2.557), no una validación.
- **Predicción ≠ medición**: SoilGrids es un modelo global; no se mezcla con
  muestras de laboratorio sin declararlo.
- **Cobertura de un punto ≠ cobertura nacional**: las series climáticas cubren
  dos coordenadas, no El Salvador.
- **GBIF**: 300 registros no representan la biodiversidad nacional; el sesgo de
  muestreo no se corrige agregando.
- **Datos ausentes ≠ cero**: los ceros de precipitación son datos; los
  centinelas y vacíos se reportan como tales.

## 6. Trazabilidad

- 5 derivaciones registradas (recorte CHIRPS, 3 normalizaciones CSV, carga de la
  base); 5/5 verificadas.
- Cada dataset tiene historial de transiciones con evidencia.
- El catálogo ráster declara CRS, resolución, nodata y contenedor recomendado.
- El monitoreo (`monitoring.json`) está `ok: true`: 11 datasets activos frescos,
  0 obsoletos/desconocidos, 0 artefactos ausentes, 0 informes `FAIL` vigentes.

## 7. Conclusión operativa

AGROSV puede hoy: consultar series de reanálisis en dos puntos, ocurrencias de
GBIF, 14 departamentos con geometría, metadatos de 13 rásteres y los informes de
calidad asociados. **No** puede todavía: agregar por municipio 2023, cuenca o
parcela; validar clima contra estaciones; sustituir cartografía nacional de
suelos; ni presentar CHIRPS como serie nacional. Esas ausencias están declaradas,
no disimuladas, y son el punto de partida de la siguiente fase.
