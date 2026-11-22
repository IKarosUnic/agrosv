# Fase 7 — informe final de monitorización agrícola

**Versión:** 7.0.0 · **Fecha:** 2026-11-22
**Alcance:** satélite, sanidad del cultivo, plagas y enfermedades, riesgos
agrícolas, alertas y monitorización integrada para El Salvador.

## 1. Resumen ejecutivo

Se implementaron **31 motores** en seis subsistemas, una API con 51 rutas bajo
`/api/monitoring`, una base de conocimiento fitosanitaria con procedencia y 69
pruebas nuevas. La suite completa pasa: **559 pruebas**.

**No se integró ninguna escena satelital ni serie de campo.** Los adaptadores
leen archivos locales y toda la cadena se verificó con fixtures sintéticos
declarados. La fase es software verificado; la validación científica empírica
está pendiente.

## 2. Componentes completamente implementados

### A. Satélite y teledetección
- `SatelliteDataEngine`: catálogo de 11 fuentes, lectura GeoTIFF/COG por
  ventana, nodata, máscara SCL, escala de reflectancia, STAC local, plan de
  búsqueda sin ejecución.
- `VegetationIndexEngine`: NDVI, EVI, SAVI, MSAVI2, NDWI, NDMI, NBR, NDRE.
- `CropChangeDetectionEngine`: diferencia con umbral, rechazo de sensores no
  armonizados, procesos posibles sin atribución.
- `SatelliteTimeSeriesEngine`: línea base estacional, z robusto, huecos,
  media móvil, tendencia OLS, comparación.
- `AgriculturalRemoteSensingEngine`: escala soportada y contexto Fase 5 opcional.

### B. Sanidad del cultivo
`CropHealthMonitoringEngine` (5 estados), `VegetationStressEngine` (≥ 2
indicadores), `WaterStressDetectionEngine` (5 categorías + Ks FAO-56),
`ThermalStressEngine` (umbral con fuente, LST no usada), `CropAnomalyDetectionEngine`
(4 métodos transparentes; modelos opacos rechazados).

### C. Plagas y enfermedades
Catálogo de **5 plagas** y **4 enfermedades** con fuente, ámbito de presencia y
calidad de evidencia. `PestRiskEngine` y `DiseaseRiskEngine` separan presencia,
idoneidad, exposición y riesgo. `AgriculturalPhytosanitaryEngine` impide
etiquetar reportes comunitarios como oficiales.

### D. Riesgo agrícola
`AgriculturalRiskEngine` (producto de tres factores), `DroughtMonitoringEngine`
(cinco categorías + índice estandarizado empírico con 30 años),
`FloodAndExcessWaterRiskEngine` (exposición, no predicción),
`HeatAndClimateRiskEngine` (pronóstico separado),
`SoilDegradationRiskEngine` (sin tasas de erosión), `CropLossRiskEngine`
(potencial/observado/modelado separados).

### E. Alertas y aviso temprano
`AgriculturalAlertEngine` (huella, duplicados, ciclo de vida inmutable),
`AgriculturalEarlyWarningEngine` (pronóstico/observación/oficial separados),
`AlertPrioritizationEngine` (pesos + protección del evento verificado),
`AlertVerificationEngine` (verificador fuerte o dos débiles),
`AgriculturalNotificationEngine` (cola local, sin PII, sin servicios de pago).

### F. Monitorización integrada
`AgriculturalMonitoringEngine`, `CropMonitoringTimelineEngine`,
`AgriculturalRiskMappingEngine` (GeoJSON con metadatos),
`AgriculturalFieldVerificationEngine` (calidad, duplicados, privacidad,
revisión), `AgriculturalMonitoringAnalysisEngine` (descriptivo, sin causalidad).

## 3. Componentes parciales

| Componente | Implementado | Falta |
|---|---|---|
| Sentinel-2 | lectura local y STAC | descarga autenticada y compuestos |
| Sentinel-1 | ficha y evaluación | lectura, corrección de terreno, uso agrícola |
| MODIS/VIIRS/Landsat | fichas y plan STAC | ingesta y armonización |
| Riesgo de plaga | motor y catálogo | ventanas calibradas y vigilancia |
| Riesgo de enfermedad | motor | modelo epidemiológico validado |
| Sequía | índice empírico | SPI/SPEI oficiales y serie de 30 años |
| Inundación | exposición | modelo hidrológico/hidráulico |
| Suelo | susceptibilidad | RUSLE calibrado y datos de pérdida |
| Campo | flujo completo | persistencia y autenticación |

## 4. Componentes planificados (no implementados)

- descarga y caché de escenas satelitales;
- compuestos temporales y armonización multsensor;
- segmentación de parcelas y máscaras de cultivo;
- modelo epidemiológico por patosistema;
- asimilación de datos y calibración de umbrales;
- persistencia en base de datos y autenticación de contribuyentes;
- exportación GeoPackage/COG de capas de riesgo;
- integración directa con SNET/MARN, CENTA, OIRSA o MAG.

## 5. Datos

- **Satélites integrados:** ninguno.
- **Satélites evaluados:** Sentinel-1, Sentinel-2, Landsat 8, Landsat 9, MODIS,
  VIIRS, Copernicus Data Space, NASA Earthdata, USGS EarthExplorer, Google Earth
  Engine, MARN/SNET D3-DOA.
- **Cobertura geográfica:** El Salvador (validación de coordenadas); sin
  cobertura raster propia.
- **Cobertura temporal:** depende del archivo aportado; no hay serie integrada.
- **Resolución:** la de la fuente; 10 m no sostiene escala parcelaria.
- **Fitosanidad:** 5 plagas y 4 enfermedades; presencia nacional confirmada
  (FAW, broca, mosca blanca, roya del café, sigatoka negra) y regional
  (barrenador de caña, picudo del banano, añublo bacteriano, mosaico dorado).
- **Registros salvadoreños confirmados:** a nivel de país, no de municipio.
- **Riesgos modelados:** todos los índices son estimaciones; ninguno es un
  evento observado.
- **Observaciones de campo:** 0 reales; el motor almacena las que se le envían.
- **Alertas generadas:** 0 reales (las de prueba viven en memoria y no se
  publican).
- **Alertas verificadas:** 0 reales.

## 6. Validación

**Lograda:** aritmética de índices, propagación de nodata, máscara de nube,
línea base y z robusto, detección de huecos, FAO-56, índice estandarizado con
registro suficiente, producto de riesgo, separación potencial/observado/modelado,
ciclo de vida y verificación de alertas, controles de campo, contratos de API y
compatibilidad.

**Pendiente:** exactitud satelital, calibración de umbrales, incidencia real de
plagas, precisión de pronósticos, relación anomalía–pérdida, series reales.

## 7. Rendimiento

NDVI 1000×1000: 24,5 ms · cambio 1000×1000: 20,4 ms · anomalía 40 obs: 0,28 ms ·
10.000 riesgos: 91,3 ms · 2.000 alertas: 34,6 ms · API: 2,7–3,1 ms · RSS máximo
150,4 MB. Detalle en `PHASE_7_TESTING_REPORT.md` y
`scripts/13_phase7_benchmark.py`.

## 8. Limitaciones principales

1. Sin escenas ni series reales, la cadena científica no está validada.
2. Los umbrales de literatura no están calibrados para El Salvador.
3. La vigilancia fitosanitaria no existe en el repositorio.
4. Los almacenes de alertas y campo son en memoria.
5. No hay autenticación ni control de acceso por roles.
6. La resolución satelital abierta no permite afirmaciones parcelarias.
7. La correspondencia municipal vigente (44 municipios) convive con los límites
   históricos de Fase 1; el análisis territorial debe declarar cuál usa.

## 9. Interoperabilidad

Los motores exponen diccionarios JSON con identificadores estables
(`pest_id`, `disease_id`, `alert_id`, `observation_id`), unidades explícitas y
`evidence_class`. La API no importa Nemotron ni Saltbor y no fusiona
repositorios:

- **Nemotron (Fase 6):** la monitorización consume sus salidas (etapas
  fenológicas, sensibilidad, catálogo de cultivos) a través de
  `agrosv.agriculture`; no genera población ni hogares.
- **Saltbor:** no se integra. La frontera es HTTP/JSON: una respuesta de
  `/api/monitoring/*` puede serializarse y consumirse sin compartir código.
- **Datos externos:** el registro de fuentes y los validadores de
  `/api/onboarding` siguen siendo la vía para incorporar series; ningún motor
  de monitorización descarga datos por su cuenta.

## 10. Prioridades recomendadas para Fase 8

1. **Adquirir una serie Sentinel-2 L2A** para un piloto departamental, con
   compuestos mensuales y máscara SCL, y validarla contra observaciones de campo.
2. **Obtener series SNET/MARN** por solicitud institucional para calibrar
   sequía y estrés hídrico.
3. **Establecer un piloto de campo** con 20–30 parcelas georreferenciadas para
   validar índices y umbrales.
4. **Conectar el catálogo fitosanitario con OIRSA/MAG** mediante registros
   oficiales versionados.
5. **Persistir alertas, verificaciones y observaciones** en una base de datos con
   auditoría y autenticación.
6. **Evaluar un modelo epidemiológico** por patosistema antes de implementarlo.
7. **Producir capas administrativas vigentes** (44 municipios) para agregación.
8. **Medir el desempeño** de la detección con matrices de confusión cuando exista
   verdad de campo.
