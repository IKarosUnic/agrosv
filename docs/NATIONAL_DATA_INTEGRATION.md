# Integración institucional nacional — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Alcance:** CNR, MAG, CENTA, BCR, MARN.
**Método:** lectura de documentación oficial + sondeo HTTP directo desde este
entorno (los códigos de la columna «Sonda» son de esa ejecución, no una promesa
de disponibilidad futura).

Este documento **no implementa** ninguna integración: fija qué existe, en qué
condiciones y qué haría falta para incorporarlo. Las capas de Fase 1
(territorio, topografía, OSM, SoilGrids) no se modifican ni se sustituyen.

---

## 0. Regla de clasificación

| Estado | Significado |
|---|---|
| **VERIFIED** | El canal respondió hoy con contenido válido y el producto es utilizable tal cual. |
| **DOCUMENTED** | Existe documentación oficial del producto, pero no se pudo descargar ni probar el acceso a los datos. |
| **RESTRICTED** | El acceso existe pero exige compra, convenio, registro, credenciales o autorización institucional. |
| **UNAVAILABLE** | Ningún medio probado devolvió el recurso. |
| **PENDING_VALIDATION** | Evidencia insuficiente o contradictoria (p. ej. URL documentada que hoy responde 404). |

`VERIFIED` describe el canal, no la calidad científica. La idoneidad se evalúa
por producto en la tabla correspondiente.

---

## 1. CNR — Centro Nacional de Registros

### 1.1 Qué ofrece

| Producto | Evidencia | Acceso | Estado |
|---|---|---|---|
| Ortofotos nacionales (proyecto *El Salvador Maps*, 20.742,5 km², hasta 10 cm) | Anuncio CNR 18-12-2023 | Consulta en plataforma; sin descarga masiva documentada | **DOCUMENTED** |
| Fotografía aérea (color, IR, B/N) | Catálogo IGCN | Compra en Dpto. de Comercialización, «desde $29» | **RESTRICTED** (pago) |
| Fotografía aérea oblicua | Listada en *El Salvador Maps* | Sin ficha pública de descarga ni precio | **DOCUMENTED** |
| LiDAR / nube de puntos | Listado en *El Salvador Maps* | Sin ficha pública de descarga ni precio | **DOCUMENTED** |
| MDT y MDS | Listados en *El Salvador Maps* | Sin ficha pública de descarga ni precio | **DOCUMENTED** |
| Curvas de nivel / altimetría | Cuadrantes 1:25.000 y 1:50.000; hojas altimétricas escaneadas y georreferenciadas | Compra (tienda en línea) | **RESTRICTED** (pago) |
| Restitución fotogramétrica | Escalas 1:1.000 y 1:5.000; $15–$252 según presentación | Compra | **RESTRICTED** (pago) |
| Modelos 3D | Listados en *El Salvador Maps* | Sin condiciones públicas | **DOCUMENTED** |
| Cartografía geológica | Escalas 1:500.000 ($4) y 1:100.000 ($30) | Compra | **RESTRICTED** (pago) |
| Cartografía catastral | Mapa de parcela $3,50; plano digital de cuadrante/sector $299,45; DXF | Compra / trámite en línea | **RESTRICTED** (pago + identificación de parcela) |
| Límites municipales (GeoJSON/SHP) y códigos de ubicación | Página de descargas del CNR | Descarga directa | **PENDING_VALIDATION** |

**Sondas ejecutadas (2026-11-21):** `https://www.cnr.gob.sv/` → 200;
catálogo de servicios del IGCN → 200; `https://elsalvadormaps.sv/` → **000**
(sin respuesta DNS/TLS); página de códigos y descargas →
**404** en la URL documentada.

### 1.2 Licencias y reutilización

- **No se localizó una licencia abierta** (CC, ODbL o equivalente) para
  ortofotos, LiDAR, MDT/MDS, restitución, modelos 3D, geología ni catastro.
- La política web del CNR trata privacidad y seguridad; no concede
  reutilización de productos geográficos.
- Comprar un archivo **no autoriza** su redistribución ni su uso comercial. Las
  condiciones deben pedirse por escrito con la cotización.

### 1.3 Qué se puede integrar realmente

| Escenario | Viabilidad | Qué haría falta |
|---|---|---|
| Ortofoto 10 cm como referencia de parcelas | Alta precisión, coste y licencia inciertos | Convenio o compra + autorización escrita de uso derivado |
| LiDAR → DTM de alta resolución | El mayor salto de precisión topográfica del país | Convenio; ~20.742 km² de nubes de puntos: almacenamiento y procesamiento propios |
| MDT/MDS nacional | Sustituiría al Copernicus GLO-30 solo si la resolución es mejor | Ficha técnica (resolución, fecha de vuelo, exactitud vertical) |
| Geología 1:100.000 | Base del módulo de geomorfología | Compra ($30/hoja) + licencia de derivados |
| Catastro | Necesario para inteligencia territorial y agricultura urbana | Trámite por parcela; **no** es descarga masiva |

**Prioridad AGROSV:** pedir al CNR (a) ficha técnica y licencia de *El Salvador
Maps*, (b) cotización de ortofoto y LiDAR para un departamento piloto
(Ahuachapán), (c) condiciones de uso de derivados. Sin (c) no se integra nada.

---

## 2. MAG — Ministerio de Agricultura y Ganadería

| Producto | Cobertura / formato | Acceso | Estado |
|---|---|---|---|
| Anuarios de Estadísticas Agropecuarias 2018-19 … 2022-23 | Nacional, dept., municipio · PDF | HTTP directo | **VERIFIED** (PDF descargable) |
| Precios diarios, semanales y mensuales | Nacional / plazas · PDF | HTTP directo | **VERIFIED** |
| Guía anual de precios de insumos 2019–2023 | Nacional · PDF | HTTP directo | **VERIFIED** |
| Costos de producción 2019-20 … 2022-23 | Por cultivo · PDF | HTTP directo | **VERIFIED** |
| Mapas temáticos (granos básicos, frutales, hortalizas, suelos, pecuario) | PDF, sin capas GIS | HTTP directo | **DOCUMENTED** (solo imagen) |
| IV Censo Agropecuario 2007-08 (resumen nacional y resultados dept./mun.) | PDF | HTTP directo | **VERIFIED** |
| V Censo Agropecuario 2025 | Ver `CENSUS_DATA_MODEL.md` | Portal BCR | **VERIFIED** (agregados) |

**Sondas:** `https://www.mag.gob.sv/servicios/estadisticas-agropecuarias` → 200;
`.../mapas-tematicos-...` → 200; anuarios y boletines → PDF 200.

**Limitación estructural:** todo lo publicado es **PDF maquetado**, no datos
tabulados. La extracción requiere parseo de tablas, revisión manual y
trazabilidad por página. No se debe presentar una cifra extraída
automáticamente sin verificación contra el PDF original.

**Licencia:** no declarada en las páginas consultadas. Se asume uso con
atribución mientras no haya respuesta institucional; **no** se redistribuirán
los PDF originales, solo agregados derivados con cita.

---

## 3. CENTA — Mapa Digital de Suelos

| Aspecto | Evidencia |
|---|---|
| Propiedades | Textura (arena, limo, arcilla), profundidad efectiva, materia orgánica, pH, nutrientes (K, P, Mg, Ca, Cu, Zn, Fe, Mn) y limitantes |
| Base | ~11.000 muestras georreferenciadas, análisis de laboratorio |
| Acceso | Visor ArcGIS (`centa.maps.arcgis.com/...`) |
| Descarga de datos | **No verificada**; la página no enlaza archivos |
| Licencia | No declarada |
| Sonda | `https://www.centa.gob.sv/mapa-digital-de-suelos` → **403** (bloqueo a clientes no navegador) |

**Estado: PENDING_VALIDATION.** Es la fuente nacional más valiosa para suelos y
la única con mediciones de laboratorio a escala de parcela. No puede
sustituirse por SoilGrids: son cosas distintas (predicción global a 250 m vs.
medición local).

**Requisito para integrar:** solicitud formal al CENTA de la geodatabase o del
servicio ArcGIS REST, con licencia de uso. Mientras no exista, AGROSV mantiene
SoilGrids **etiquetado como predicción** y no mezcla ambas fuentes en una misma
capa.

---

## 4. BCR — censos

El detalle completo está en [`CENSUS_DATA_MODEL.md`](CENSUS_DATA_MODEL.md).
Resumen de acceso:

| Fuente | Microdatos | Agregados | Estado |
|---|---|---|---|
| CPV 2024 (población y vivienda) | **Sí**, anonimizados, CSV/SPSS + diccionario | Excel/PDF dept.→municipio→distrito | **VERIFIED** |
| V Censo Agropecuario y I de Pesca 2025 | **No** (solo agregados; art. 25 Ley Especial de Estadística y Censos) | PDF/PPT + dashboards, nivel departamental | **VERIFIED** (parcial) |

**Sondas:** `geoportal.bcr.gob.sv` → 200; base de datos CPV →
200; documentación CAP → 200; preguntas frecuentes CAP → 200.

---

## 5. MARN / SNET — geomorfología y amenazas

| Capa | Producto publicado | Acceso | Estado |
|---|---|---|---|
| Inundación | «Mapa preliminar de áreas susceptibles a inundación» (atlas hidrológico); perfil de riesgo 2014; estudio probabilístico AECID | PDF/visor | **DOCUMENTED** |
| Deslizamientos | Mapa de susceptibilidad por remoción en masa, **1:50.000** | Visor/PDF | **DOCUMENTED** |
| Erosión | Mapa de susceptibilidad costero-marina, **2015**, método RUSLE | PDF | **VERIFIED** (PDF) |
| Sequía | Mapas de seguimiento; resumen climatológico 2024 | PDF | **DOCUMENTED** |
| Volcánica | Mapas para Santa Ana, San Salvador, San Miguel y San Vicente | PDF/JPG | **DOCUMENTED** |
| Subcuencas | Delimitación Pfafstetter >10 km², DEM 1:25.000 (PNGIRH 2017) | Informe PDF; geodatabase no verificada | **PENDING_VALIDATION** |
| Subcuencas (servicio) | FeatureServer alojado en plataforma regional | REST/GeoJSON | **VERIFIED** (tercero, no MARN) |
| Geología general | Mapa geológico general (SNET) | Consulta | **DOCUMENTED** |
| Geoportal MARN | — | — | **UNAVAILABLE** al sondear (HTTP 522) |

**Regla:** no se publicará ninguna capa de amenaza como «oficial» sin metadatos
de escala, año y método. Los mapas PDF no son capas GIS: si se vectorizan,
deben etiquetarse como *derivado AGROSV* y no como producto del MARN.

---

## 6. Prioridad de integración (valor / coste / riesgo)

| Orden | Fuente | Valor | Coste | Riesgo | Decisión |
|---|---|---|---|---|---|
| 1 | CPV 2024 (microdatos + tabulados) | Alto: demografía, hogares, urbano/rural | $0 | Bajo (anonimizado) | **Integrar ya** |
| 2 | CAP 2025 (agregados) | Alto: productores, superficie, producción | $0 | Bajo | **Integrar ya**, nivel departamental |
| 3 | MAG anuarios/precios/costos | Alto: series y márgenes | Bajo (parseo) | Medio (PDF) | **Integrar por cultivo piloto** |
| 4 | CHIRPS v3 + AgERA5 | Muy alto: clima histórico agrícola | $0 | Bajo | **Integrar ya** |
| 5 | AMENAZAS MARN (PDF) | Alto para riesgo | Bajo | Medio (escala/año) | **Vectorizar piloto** |
| 6 | Subcuencas (FeatureServer) | Alto: unidad hidrológica | $0 | Medio (procedencia) | **Validar contra PNGIRH** |
| 7 | CENTA MDS | Muy alto: suelo medido | Convenio | Alto (licencia) | **Solicitar acceso** |
| 8 | CNR ortofoto/LiDAR | Muy alto: precisión | Compra/convenio | Alto (licencia) | **Negociar piloto** |
| 9 | Google Weather | Medio: pronóstico puntual | Por llamada | Alto (ToS) | **Solo lectura en vivo** |
| 10 | Catastro CNR | Alto: parcela | Por parcela | Alto | **No masivo** |

---

## 7. Requisitos técnicos de integración (comunes)

1. **Nada entra sin manifiesto**: institución, URL, fecha de publicación, fecha
   de adquisición, cobertura, resolución, formato, licencia, restricciones,
   confianza y método de procesamiento (ver §8).
2. **Los archivos originales son inmutables** en `data/raw/<institucion>/` y no
   se versionan si superan el límite del repositorio.
3. **Licencias aisladas por almacén**: ODbL (OSM) no puede convivir en el mismo
   archivo derivado que datos de licencia no compatible. Un GeoPackage por
   licencia, como ya se hace en Fase 1.
4. **Los agregados censales y estadísticos no se unen con microdatos** en la
   misma tabla; se relacionan por claves geográficas explícitas.
5. **Toda capa nueva declara su clase**: observación, mapa de amenaza, mapa de
   susceptibilidad, predicción de modelo o dato administrativo.

---

## 8. Ficha obligatoria por fuente (plantilla)

```
id:               <slug único>
institución:      <CNR | MAG | CENTA | BCR | MARN | otro>
url_original:     <enlace exacto>
fecha_publicación:<AAAA-MM o AAAA>
fecha_adquisición:<AAAA-MM-DD>
cobertura:        <nacional | departamental | municipal | distrito | parcela>
resolución:       <espacial y temporal>
formato:          <PDF | XLSX | CSV | SHP | GeoPackage | COG | NetCDF | servicio>
licencia:         <texto exacto o «no declarada»>
restricciones:    <redistribución, uso comercial, confidencialidad>
confianza:        <alta | media | baja> + justificación
procesamiento:    <pasos reproducibles>
estado:           <VERIFIED | DOCUMENTED | RESTRICTED | UNAVAILABLE | PENDING_VALIDATION>
```

---

## 9. Lo que este documento NO afirma

- No afirma que el CNR tenga API pública: existe un WMS institucional
  documentado por un convenio (ETESAL, 17-12-2024), no un endpoint anónimo.
- No afirma que CENTA permita descargar sus capas: solo que el visor es
  público.
- No afirma que el CAP 2025 publique microdatos: la política declara lo
  contrario.
- No afirma que los mapas de amenaza del MARN sean capas GIS descargables.
- No convierte un PDF en dato: mientras no haya tabla verificada, es una
  referencia documental.
