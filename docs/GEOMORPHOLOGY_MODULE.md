# Módulo de geomorfología y amenazas naturales

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Estado:** diseño; las capas de Fase 1 (pendiente, orientación, relieve) son el
insumo base y no se modifican.

Objetivo: describir la forma del terreno de El Salvador y separar con claridad
**peligro** (mapa de amenaza), **observación** (evento ocurrido) y
**predicción** (modelo). Hoy el país tiene mayormente lo primero en PDF; el
módulo debe poder convivir con esa carencia sin fingir capas que no existen.

---

## 1. Capas geomorfológicas

| Capa | Método | Insumo | Estado |
|---|---|---|---|
| Pendiente, orientación, clases de relieve | Gradiente sobre DEM 30 m | Copernicus GLO-30 (Fase 1) | **VERIFIED** (ya publicado) |
| Unidades de relieve (montaña, valle, llanura, meseta) | Clasificación morfométrica (geomorphons / TPI) sobre DEM | DEM 30 m | **DISEÑADO** (derivado AGROSV) |
| Volcanes | Inventario puntual con nombre, altura, tipo | MARN/SNET + DEM | **DOCUMENTED** |
| Cuencas y subcuencas | Delimitación Pfafstetter >10 km² (PNGIRH 2017) | Modelo 1:25.000 | **PENDING_VALIDATION** |
| Servicio de subcuencas | FeatureServer regional (no MARN) | — | **VERIFIED** (tercero) |
| Ríos y quebradas | OSM `waterway` | OSM (Fase 1) | **VERIFIED** |
| Lagos y embalses | OSM `water` | OSM (Fase 1) | **VERIFIED** |
| Formaciones geológicas | Mapa geológico 1:100.000 / 1:500.000 | CNR (compra) | **RESTRICTED** |
| Fallas geológicas | Geología estructural | CNR / MARN | **DOCUMENTED** |
| Curvas de nivel | Cuadrantes 1:25.000 | CNR | **RESTRICTED** (compra) |

**Regla:** toda capa derivada del DEM se etiqueta «derivado AGROSV» con el
método y los parámetros. Ninguna se presenta como cartografía oficial.

### 1.1 Cómo se clasifican las unidades de relieve

1. Se calcula el Índice de Posición Topográfica (TPI) a varias ventanas
   (p. ej. 300, 1.000 y 3.000 m) sobre el DEM en EPSG:32616.
2. Se combinan pendiente (Fase 1) y TPI para separar crestas, laderas, valles,
   llanuras y mesetas.
3. Se contrasta con el mapa geomorfológico del MAG/CNR cuando exista.
4. Se publica con umbrales explícitos y una prueba de sensibilidad: cambiar la
   ventana no debe reetiquetar más de un 15 % del territorio; si lo hace, la
   clase no es robusta y se informa.

---

## 2. Amenazas naturales: modelo de datos

Una amenaza no es un booleano. El modelo debe permitir responder «¿qué mapa,
de qué año, a qué escala y con qué método?».

```sql
hazard_layer(
  hazard_id      TEXT PRIMARY KEY,   -- 'marn-deslizamiento-2010-50k'
  phenomenon     TEXT,               -- inundacion|deslizamiento|erosion|sequia|volcanica
  layer_type     TEXT,               -- 'amenaza' | 'susceptibilidad' | 'observacion' | 'prediccion'
  source_id      TEXT,               -- 'marn-snet' | 'agrosv'
  scale          TEXT,               -- '1:50.000'
  resolution_m   INTEGER,
  published_year INTEGER,
  method         TEXT,               -- 'RUSLE', 'experto', 'estadistico', 'hidraulico'
  return_period  TEXT,               -- 'Tr=10', 'Tr=100', NULL
  classes        JSONB,              -- [{code, label, description}]
  confidence     TEXT,               -- alta|media|baja + justificación
  geometry_type  TEXT,               -- 'Polygon' | 'Raster'
  license        TEXT,
  provenance_id  TEXT
);
```

Campos que **nunca** se omiten: `layer_type`, `method`, `scale`/`resolution_m`,
año y `confidence`. Sin ellos, la capa no se publica.

### 2.1 Distinción obligatoria

| Tipo | Qué es | Ejemplo | Cómo se muestra |
|---|---|---|---|
| `amenaza` | Peligro potencial, sin evento | Mapa de susceptibilidad a deslizamientos | Capa de fondo, leyenda «potencial» |
| `observacion` | Evento ocurrido y documentado | Inundación registrada en un año | Punto/polígono con fecha y fuente |
| `prediccion` | Resultado de un modelo | Área inundable para Tr=100 | Capa con método y periodo de retorno |
| `susceptibilidad` | Propensión relativa del terreno | Clases alta/media/baja | Escala ordinal, no probabilidad |

**Prohibido** mezclar clases de susceptibilidad con probabilidad, o pintar una
observación como predicción.

---

## 3. Fuentes y estado real

| Amenaza | Producto | Año | Escala | Acceso | Estado |
|---|---|---|---|---|---|
| Inundación | Mapa preliminar de áreas susceptibles (atlas hidrológico SNET) | no verificada | no verificada | PDF/visor | **DOCUMENTED** |
| Inundación | Perfil de riesgo por inundaciones | 2014 | — | PDF | **VERIFIED** (PDF) |
| Inundación | Estudio probabilístico AECID | — | — | PDF | **DOCUMENTED** |
| Deslizamiento | Mapa de susceptibilidad por remoción en masa | no verificado | **1:50.000** | Visor/PDF | **DOCUMENTED** |
| Erosión | Susceptibilidad costero-marina (RUSLE) | **2015** | no verificada | PDF | **VERIFIED** (PDF) |
| Sequía | Mapas de seguimiento; resumen climatológico 2024 | 2024 | — | PDF | **DOCUMENTED** |
| Volcánica | Mapas para Santa Ana, San Salvador, San Miguel, San Vicente | variable | variable | PDF/JPG | **DOCUMENTED** |
| Geoportal MARN | Servicios REST | — | — | — | **UNAVAILABLE** (HTTP 522 al sondear) |
| Subcuencas | FeatureServer regional | — | — | REST/GeoJSON | **VERIFIED** (tercero) |

Sondas 2026-11-21: `geoportal.marn.gob.sv` → 522; `snet.gob.sv` atlas y
deslizamientos → 200; FeatureServer de subcuencas → 200.

---

## 4. Qué se implementa y en qué orden

1. **Unidades de relieve derivadas del DEM** (sin dependencias externas):
   montaña, valle, llanura, meseta. Publicables con el DEM actual.
2. **Cuencas y subcuencas**: validar el FeatureServer contra el PNGIRH 2017
   antes de usarlo; si no coincide, se usa solo como referencia visual.
3. **Inventario de volcanes**: puntos con nombre, altura y fuente; sin polígonos
   inventados.
4. **Amenazas**: vectorizar **una** (deslizamientos 1:50.000 o erosión 2015)
   como piloto, con revisión manual y atribución al MARN. El resto queda como
   enlace documental hasta obtener la geodatabase.
5. **Geología y fallas**: solo cuando se adquiera la cartografía del CNR
   (1:100.000, $30/hoja) con licencia de derivados.

---

## 5. Validación

| Prueba | Criterio |
|---|---|
| Coherencia geomorfológica | un «valle» no puede tener pendiente media > 15° |
| Sensibilidad | cambio de ventana TPI reetiqueta < 15 % |
| Subcuencas | ∑ áreas de subcuencas ≈ área nacional (± 2 %) |
| Amenaza vs terreno | clases altas de deslizamiento concentran pendiente > 25° (test de asociación, no de verdad) |
| Metadatos | 100 % de capas con `layer_type`, `method`, `scale`, año |
| Trazabilidad | cada capa vectorizada desde PDF conserva referencia de página y figura |

---

## 6. Riesgos

1. **Vectorizar un PDF no crea un mapa oficial.** Se etiqueta como derivado y
   se conserva el PDF de referencia.
2. **Cambio de escala**: un mapa 1:50.000 no admite zoom 14 en el visor sin
   declarar que la geometría es esquemática.
3. **Amenazas desactualizadas**: un mapa de 2010 no refleja cambios de uso del
   suelo; se muestra el año en la leyenda.
4. **Servicios de terceros**: el FeatureServer de subcuencas no es del MARN;
   puede desaparecer. Se cachea copia con hash y se documenta.
5. **Cuencas transfronterizas**: El Salvador comparte cuencas con Guatemala y
   Honduras; los límites nacionales truncan la unidad hidrológica y eso debe
   decirse.
