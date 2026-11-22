# DATA_GAPS_AND_LIMITATIONS — AGROSV Fase 3

**Fecha:** 2026-11-22 · Registro explícito de lo que **no** se tiene, **no** se
pudo verificar o **no** se debe afirmar. Es el documento que impide que AGROSV
confunda un vacío con un cero.

---

## 1. Vacíos por dominio

| # | Dominio | Vacío | Severidad | Impacto | Acción |
|---|---|---|---|---|---|
| G-01 | Suelos | Acceso a datos CENTA (mediciones) | **Crítica** | Sin fertilidad real ni profundidad efectiva | Solicitud institucional |
| G-02 | Suelos | P, K, Ca, Mg, micronutrientes | **Crítica** | Sin recomendación de fertilización | CENTA / laboratorio |
| G-03 | Suelos | Propiedades hidráulicas en SoilGrids `latest` | **Alta** | Balance hídrico sin datos directos | Pedotransferencia declarada |
| G-04 | Suelos | Salinidad (CE) y compactación | **Alta** | Riego y manejo limitados | Medición de campo |
| G-05 | Hidrología | Series de aforos | **Crítica** | Modelo no calibrable | SNET/MARN |
| G-06 | Hidrología | Subcuencas oficiales (PNGIRH 2017) | **Alta** | Unidad hidrológica no oficial | Solicitud |
| G-07 | Hidrología | Pozos, niveles freáticos, recarga | **Alta** | Sin agua subterránea | MARN/ANDA |
| G-08 | Hidrología | Calidad del agua | **Alta** | Sin aptitud para riego | MARN/ANDA |
| G-09 | Clima | Series de estaciones SNET | **Crítica** | Sin validación de satélite | Solicitud |
| G-10 | Clima | Metadatos de estaciones (QC, altura, período) | **Alta** | Sin control de calidad | Solicitud |
| G-11 | Clima | Perspectiva estacional oficial por API | **Media** | Almanaque limitado a histórico | CIIFEN/SNET |
| G-12 | Territorio | Municipios 2023 (44) y distritos (262) como capa oficial | **Crítica** | Uniones censales incorrectas | BCR/CNR |
| G-13 | Territorio | Códigos de ubicación geográfica | **Alta** | Claves inestables | CNR |
| G-14 | Catastro | Parcelas, ortofoto, LiDAR | **Alta** | Sin inteligencia de parcela | CNR (compra/convenio) |
| G-15 | Geología | Fallas, geomorfología, susceptibilidad como GIS | **Alta** | Sin modelo de amenaza | MARN/CNR |
| G-16 | Cobertura | Mapa de cultivos validado | **Crítica** | No se puede medir superficie por teledetección | Clasificación + campo |
| G-17 | Producción | Rendimiento por variedad y zona | **Alta** | Sin calibración de modelos | CENTA/MAG |
| G-18 | Producción | Fechas de siembra reales por zona y año | **Alta** | Ventanas de siembra inciertas | MAG/encuestas |
| G-19 | Producción | Pérdidas poscosecha | **Media** | Cadena incompleta | MAG |
| G-20 | Censos | Microdatos del CAP 2025 | **Crítica** (por ley) | Sin análisis de unidad productiva | No insistir; usar agregados |
| G-21 | Censos | Desagregación municipal del CAP | **Alta** | Sin perfil municipal | Solicitud de tabulados |
| G-22 | Fitosanidad | Vigilancia (trampeo, brotes) | **Alta** | Sin línea base | MAG/CENTA |
| G-23 | Fitosanidad | Boletines del ISC por API | **Media** | Roya/broca no automatizable | ISC |
| G-24 | Economía | Precios en formato tabular | **Alta** | Series no automatizables | MAG |
| G-25 | Economía | Precios al productor por departamento | **Alta** | Márgenes reales desconocidos | MAG |
| G-26 | Economía | Costos posteriores a 2022-23 | **Media** | Desactualización | MAG |
| G-27 | Nemotron | Dotaciones (tierra, agua, crédito, ingreso) | **Alta** | Agentes sin restricciones reales | Derivar de CAP/CPV, etiquetar |
| G-28 | Nemotron | Representatividad estadística | **Crítica** | No usar como encuesta | Declararlo siempre |
| G-29 | Satélite | Sentinel-1 procesado | **Media** | Sin monitoreo en época lluviosa | Cuenta CDSE + cadena SAR |
| G-30 | Satélite | Verdad de campo | **Crítica** | Sin validación de clasificadores | Muestreo de campo |

---

## 2. Limitaciones técnicas verificadas

| Limitación | Consecuencia | Mitigación |
|---|---|---|
| CHIRPS diario es desagregado de pentadas | No sirve para extremos diarios finos | Trabajar a pentada o declarar |
| Copernicus DEM es un DSM | Pendiente sesgada en bosque/ciudad | Declarar; considerar corrección |
| SoilGrids a 250 m | No es propiedad de parcela | Usar como prior |
| OSM sin cobertura agrícola | No delimita cultivos | No usarlo para superficie |
| Sentinel-2 con nubes | Series discontinuas en invierno | Sentinel-1 o composiciones |
| MODIS Terra cesa 2026-12-01 | Corte de serie | Migrar a VIIRS con aviso |
| Nemotron sintético | Sin valor probatorio | Solo simulación |

---

## 3. Limitaciones institucionales

| Situación | Efecto | Qué **no** se puede concluir |
|---|---|---|
| MAG/BCR sin licencia declarada | No redistribuir | Que el dato sea de libre uso |
| CENTA bloquea clientes no navegador (403) | No automatizable | Que no exista el dato |
| CNR vende productos | Coste y convenio | Que exista una API pública |
| MARN con 503/522 | Sin hidrología oficial | Que no haya datos internos |
| ISC 403 | Sin boletines automatizados | Que la roya no se monitoree |

---

## 4. Cosas que AGROSV no debe afirmar todavía

1. «Superficie de maíz en El Salvador» calculada por teledetección.
2. «Rendimiento esperado» de una parcela.
3. «Disponibilidad de agua» por proximidad a un río.
4. «Suelo de esta parcela» a partir de SoilGrids.
5. «Riesgo de plaga» presentado como brote observado.
6. «Productor típico» derivado de Nemotron.
7. «Caudal» o «recarga» sin aforos.
8. «Precio actual» sin fecha y plaza.
9. «Límite municipal oficial» usando la capa histórica de 2022.
10. «Cobertura forestal» como equivalente a bosque primario.

---

## 5. Incertidumbre por fuente (resumen)

| Fuente | Incertidumbre dominante | Cómo se reporta |
|---|---|---|
| CHIRPS | Temporal (pentadal) y topográfica | `effective_resolution` |
| AgERA5 | Espacial 0,1° | Declarada en el manifiesto |
| SoilGrids | Modelo global; error en relieve | Intervalos Q0.05–Q0.95 |
| DEM 30 m | DSM, exactitud vertical | Ficha del producto |
| Sentinel-2 | Nubosidad, mezcla espectral | Máscara SCL y % válido |
| CAP 2025 | Agregación departamental | Nivel geográfico explícito |
| Nemotron | Sintético, sin dotaciones | Etiqueta `synthetic` |
| Precios MAG | Muestreo no probabilístico | Nota metodológica del boletín |

---

## 6. Prioridad para cerrar vacíos

| Orden | Vacío | Por qué primero |
|---|---|---|
| 1 | G-12/G-13 (territorio oficial) | Todo análisis territorial depende de ello |
| 2 | G-09/G-10 (estaciones) | Sin observación no hay validación climática |
| 3 | G-01/G-02 (suelos CENTA) | Bloquea fertilidad y modelos |
| 4 | G-05/G-06 (aforos y subcuencas) | Bloquea hidrología |
| 5 | G-16/G-30 (cultivos y campo) | Bloquea teledetección agrícola |
| 6 | G-17/G-18 (rendimiento y siembra) | Bloquea calibración |
| 7 | G-24/G-25 (precios) | Bloquea economía fina |

---

## 7. Regla de honestidad

Un vacío documentado es un activo: permite planificar la solicitud institucional,
diseñar el experimento y evitar publicar ciencia falsa. Un vacío rellenado con
una estimación no declarada es un pasivo que contaminará todos los módulos.
