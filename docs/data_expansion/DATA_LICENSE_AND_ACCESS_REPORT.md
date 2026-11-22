# DATA_LICENSE_AND_ACCESS_REPORT — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Advertencia:** este documento no es asesoría legal.
Registra lo que cada fuente **declara** y lo que AGROSV puede hacer con ello sin
autorización adicional.

---

## 1. Familias de licencia presentes

| Familia | Fuentes | Obligación principal | Riesgo para AGROSV |
|---|---|---|---|
| **Dominio público / abierta sin restricción** | Landsat C2, World Bank, NASA POWER, NOAA CPC | Atribución cortés | Bajo |
| **CC BY 4.0** | SoilGrids, Nemotron, WorldPop, ESA WorldCover, Dynamic World, GFW, Open-Meteo (API), ERA5/AgERA5 | Atribución; sin share-alike | Bajo |
| **CC BY-SA 2.0** | geoBoundaries | Atribución **y compartir igual** la base derivada | **Medio**: contamina derivados |
| **ODbL 1.0** | OpenStreetMap | Atribución + share-alike sobre la base derivada | **Medio-alto**: aislar esquema |
| **Copernicus** | Sentinel-1/2, Copernicus DEM | Atribución; condiciones específicas por producto | Bajo |
| **No comercial** | WorldClim, GAEZ, AquaCrop (código), Open-Meteo gratuito, APSIM, HydroSHEDS (verificar) | Sin uso comercial; a veces sin redistribución | **Alto** si AGROSV se comercializa |
| **Contractual (ToS)** | Google Weather | Prohibido recrear servicio meteorológico; caché limitada | **Alto**; excluido |
| **Sin licencia declarada** | MAG, BCR, CENTA, CNR, MARN, ANDA, ISC | Derechos reservados por defecto | **Alto**: no redistribuir |
| **Por registro** | GBIF | Licencia individual (CC0/CC BY/CC BY-NC) | Medio |
| **Propietaria / suscripción** | CABI CPC, Planet, WDPA API (token) | Pago o permiso | Alto |

---

## 2. Reglas operativas de AGROSV

| # | Regla |
|---|---|
| L-1 | Un archivo comprado **no** autoriza redistribución ni uso comercial. |
| L-2 | Las fuentes sin licencia se usan con atribución para análisis interno y **no** se redistribuyen sus archivos originales. |
| L-3 | Los derivados de OSM se publican en un GeoPackage **separado**, bajo ODbL. |
| L-4 | Los derivados de geoBoundaries se publican bajo CC BY-SA 2.0. |
| L-5 | Los productos que incorporen WorldClim, GAEZ o AquaCrop se marcan «no comercial» hasta obtener permiso. |
| L-6 | Ningún dataset con licencia no comercial se mezcla en un archivo con datos de otra licencia incompatible. |
| L-7 | Los microdatos del CPV no se redistribuyen; solo agregados. |
| L-8 | Nemotron se marca siempre como sintético y CC BY 4.0. |
| L-9 | Google Weather no se usa como archivo ni como insumo de modelo. |
| L-10 | Cada capa lleva su atribución en la respuesta de la API y en la UI. |

---

## 3. Detalle por fuente crítica

### 3.1 Estadística nacional (MAG, BCR)

- **Declarado:** ninguna licencia de reutilización en las páginas consultadas.
- **Permitido por AGROSV:** uso interno, citación, publicación de agregados
  derivados con referencia.
- **Prohibido:** redistribuir los PDF, los tabulados crudos o los microdatos.
- **Acción pendiente:** solicitud formal de licencia de reutilización al MAG y al
  BCR. Sin respuesta, el estado es «sin licencia declarada».

### 3.2 CENTA y CNR

- Productos de compra o convenio; sin licencia abierta localizada.
- **Acción:** pedir por escrito (a) licencia de uso, (b) permiso de publicación
  de derivados, (c) condiciones de uso comercial.
- Mientras no haya respuesta, AGROSV **no** publica capas derivadas de CENTA/CNR.

### 3.3 OSM (ODbL)

- La base derivada debe licenciarse ODbL y permitir extracción.
- **Arquitectura:** `territory_osm.gpkg` separado; nunca unido a SoilGrids en el
  mismo archivo.
- Atribución: «© OpenStreetMap contributors, ODbL 1.0».

### 3.4 geoBoundaries (CC BY-SA 2.0)

- Los límites publicados por AGROSV heredan CC BY-SA 2.0.
- Si se disuelven o corrigen, el derivado sigue siendo CC BY-SA.
- **Conflicto potencial:** un mapa que combine límites CC BY-SA con datos no
  compatibles debe mantener capas separadas o declarar la licencia del conjunto.

### 3.5 SoilGrids (CC BY 4.0)

- Atribución: «SoilGrids 2.0, ISRIC — World Soil Information, CC BY 4.0».
- Se puede usar comercialmente con atribución.
- La incertidumbre debe acompañar al dato.

### 3.6 CHIRPS

- La documentación lo presenta como abierto; **el aviso exacto no se verificó**
  en esta fase.
- **Acción:** leer `readme.txt` y la página de política de CHC antes de
  redistribuir. Mientras tanto: uso interno con atribución.

### 3.7 Nemotron (CC BY 4.0)

- Se puede redistribuir con atribución, incluso comercialmente.
- Debe declararse sintético y no representativo.
- No contiene nombres individuales.

### 3.8 Google Weather (ToS)

- §21.1: no usar el contenido para recrear un servicio meteorológico.
- §21.2: caché de 1 h (actual), 24 h (diario), 240 h (histórico horario);
  después debe eliminarse.
- **Decisión:** excluido del archivo y de los modelos; solo lectura efímera
  opcional en UI, si acaso.

### 3.9 Modelos (AquaCrop, DSSAT, APSIM)

| Modelo | Licencia | Consecuencia |
|---|---|---|
| AquaCrop 7.3 | © FAO, «All rights reserved», no comercial previa solicitud | Uso interno; no redistribuir código |
| DSSAT 4.8.6 | BSD-3-Clause | Uso amplio con registro |
| APSIM Next Gen | No comercial, 3 años | Solo evaluación |
| SWAT+ | LGPL-2.1 | Uso amplio |

---

## 4. Matriz de decisión

| Si AGROSV… | Entonces… |
|---|---|
| se mantiene abierto y no comercial | puede usar todo salvo Google Weather y las fuentes de pago |
| se institucionaliza sin fines de lucro | igual, con revisión de HydroSHEDS y Open-Meteo |
| se comercializa | debe sustituir AquaCrop, APSIM, WorldClim, GAEZ y Open-Meteo gratuito; renegociar CENTA/CNR/MAG |
| publica una API con derivados OSM | debe licenciar esa base bajo ODbL |
| publica mapas con límites geoBoundaries | debe atribuir CC BY-SA 2.0 |

---

## 5. Acciones de licencia prioritarias

| Prioridad | Acción | Responsable |
|---|---|---|
| 1 | Solicitud escrita a CENTA (datos + licencia de derivados) | AGROSV |
| 2 | Solicitud a CNR (El Salvador Maps, ortofoto, LiDAR) | AGROSV |
| 3 | Solicitud de licencia de reutilización a MAG y BCR | AGROSV |
| 4 | Verificar aviso legal de CHIRPS y HydroSHEDS | AGROSV |
| 5 | Definir la licencia de salida de AGROSV (sugerida: CC BY 4.0 para datos propios, ODbL para derivados OSM) | AGROSV |

---

## 6. Lo que este informe no afirma

- No afirma que una fuente sin licencia sea ilegal de usar: afirma que **no hay
  permiso declarado de redistribución**.
- No interpreta silencios institucionales como autorización.
- No sustituye la revisión legal de un contrato de compra o convenio.
