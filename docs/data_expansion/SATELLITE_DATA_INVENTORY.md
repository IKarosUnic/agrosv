# SATELLITE_DATA_INVENTORY — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Evidencia:** sondas propias + muestra STAC descargada.
El diseño del motor está en [`../SATELLITE_MONITORING_ENGINE.md`](../SATELLITE_MONITORING_ENGINE.md);
aquí se inventaría el **acceso real** a los datos.

---

## 1. Matriz de misiones

| ID | Sensor | Variables | Resolución | Revisita | Historia | Acceso | Licencia | Estado |
|---|---|---|---|---|---|---|---|---|
| `s2_l2a` | Sentinel-2 MSI L2A | 13 bandas + SCL | 10/20/60 m | 5 días (2 satélites) | 2015– | STAC público + COG en S3 | Copernicus, atribución | **VERIFIED** |
| `s2_c1_l2a` | Sentinel-2 Collection-1 L2A | Ibídem | Ibídem | Ibídem | 2022– (baseline nueva) | STAC público | Ibídem | **VERIFIED** (listado) |
| `s1_grd` | Sentinel-1 IW GRD | VV/VH | 10 m (spacing) | 6–12 días | 2014– | CDSE (OAuth2) | Copernicus | **RESTRICTED** (cuenta) |
| `landsat_c2` | Landsat 8/9 OLI-TIRS C2 | 7 bandas + QA | 30 m (100 m térmico) | 16 días | 1982– | USGS EarthExplorer (login) | Dominio público | **VERIFIED** (portal) |
| `mod13q1` | MODIS Terra | NDVI/EVI 16 d | 250 m | 16 días | 2000– | LP DAAC (login) | Abierta | **VERIFIED** (portal) |
| `vj113a1` | VIIRS Suomi-NPP | NDVI/EVI | 250 m | Diaria (composite) | 2012– | Earthdata | Abierta | **PENDING_VALIDATION** |
| `gpm_imerg` | GPM IMERG | Precipitación | 0,1°, 30 min | 30 min | 2000– | Earthdata | Abierta | **RESTRICTED** (login) |
| `smap_l4` | SMAP L4 | Humedad del suelo | 9 km, 3 h | 3 h | 2015– | Earthdata | Abierta | **DOCUMENTED** |
| `worldcover` | ESA WorldCover | Cobertura 11 clases | 10 m | Anual (2020, 2021) | 2020–2021 | Descarga directa | CC BY 4.0 | **VERIFIED** (portal) |
| `dynamic_world` | Dynamic World | Cobertura probabilística 9 clases | 10 m | ~2–5 días | 2015– | Earth Engine/API | CC BY 4.0 | **VERIFIED** (portal) |
| `jrc_gsw` | JRC Global Surface Water | Agua superficial | 30 m | Anual | 1984–2021 | Descarga directa | Abierta | **VERIFIED** |
| `planet` | PlanetScope | 4 bandas | 3 m | Diaria | 2016– | Comercial | Suscripción | **RESTRICTED** (pago) |

---

## 2. Evidencia de acceso real a Sentinel-2

### 2.1 Búsqueda STAC

```
POST https://earth-search.aws.element84.com/v1/search
{"collections":["sentinel-2-l2a"],"bbox":[-89.35,13.60,-89.10,13.80],
 "datetime":"2025-01-01T00:00:00Z/2025-03-01T00:00:00Z","limit":2}
→ 200, 42.425 B
```

Muestra: `data/samples/phase3/sentinel2_stac/s2_stac_search.json`
(sha256 `049c3afc7efa…`). Item devuelto: **`S2B_15PZR_20250227_0_L2A`**.

**Hallazgo de interoperabilidad:** el mismo endpoint devuelve **HTTP 400** si
`datetime` se envía como `"2025-01-01/2025-03-01"`. Exige RFC3339 completo con
hora y `Z`. Cualquier cliente debe enviar `…T00:00:00Z/…T00:00:00Z`.

**Colecciones disponibles** (9 en el catálogo, consultado el 2026-11-22):
`sentinel-2-l2a`, `sentinel-2-c1-l2a`, `sentinel-2-pre-c1-l2a`, `sentinel-2-l1c`,
`sentinel-1-grd`, `landsat-c2-l2`, `cop-dem-glo-30`, `cop-dem-glo-90`, `naip`.
**Usar `sentinel-2-c1-l2a` para trabajo nuevo**: es la colección de la línea de
procesamiento vigente; `sentinel-2-l2a` sigue disponible pero corresponde a la
generación anterior.

### 2.2 Lectura por rango del COG

```
GET https://sentinel-cogs.s3.us-west-2.amazonaws.com/.../B04.tif
Range: bytes=0-2047
→ 206, 2.048 B
```

No se descarga la escena completa: se lee solo la ventana del polígono. Esto es
lo que hace viable el monitoreo de parcelas sin almacenar imágenes enteras.

### 2.3 Zonas UTM

El Salvador cae en **15P** y **16P**. Tile confirmado: 15PZR.

### 2.4 Limitación estacional

Ventana útil **noviembre–abril**. En estación lluviosa la nubosidad reduce la
revisita efectiva a semanas. La solución estándar es **Sentinel-1 (SAR)**;
requiere cuenta CDSE (OAuth2) y procesamiento específico (speckle, geometría).

---

## 3. Cobertura y uso del suelo: qué detecta y qué no

| Pregunta | Sentinel-2 | WorldCover/Dynamic World | MAG (PDF) |
|---|---|---|---|
| ¿Hay vegetación? | SÍ (NDVI/EVI) | SÍ | SÍ (mapa temático) |
| ¿Es cultivo de maíz? | **NO sin verdad de campo** | **NO** (clase «crops» genérica) | SÍ declarado, pero sin fecha ni metodología pública |
| ¿Cambió la cobertura? | SÍ (series temporales) | SÍ (probabilidades) | No (mapa estático) |
| ¿Área de un cultivo específico? | Solo con clasificación supervisada validada | No | Solo como referencia cartográfica |

**Regla:** cobertura vegetal ≠ cultivo agrícola confirmado. AGROSV no debe
publicar «superficie de maíz» derivada de NDVI sin un clasificador validado
contra el CAP 2025.

---

## 4. Restricciones operativas

| Restricción | Efecto |
|---|---|
| Cuota CDSE (12 TB/30 días) | Obliga a archivar índices, no reflectancia |
| MODIS Terra cesa el 2026-12-01 | Migrar a VJ113A1/VJ213A1; **no concatenar series sin aviso** |
| Earthdata/USGS/CDS requieren cuenta | La reproducibilidad pública exige archivar la versión usada |
| Planet es comercial | No usar como dependencia del producto abierto |
| Sentinel-1 requiere procesamiento SAR | No es un «drop-in» de Sentinel-2 |

---

## 5. Primeros productos recomendados

1. **Serie NDVI 10 m** por AOI piloto (Ahuachapán o La Libertad) con
   `sentinel-2-c1-l2a`, máscara SCL y lectura por rango.
2. **Máscara de agua permanente** con JRC GSW (30 m) para separar riego de
   secano.
3. **Cobertura anual** con WorldCover 2021 como capa de contexto, no como verdad
   agrícola.
4. **Comparación** de la serie NDVI con el calendario de siembra del MAG.

Ninguno de estos productos requiere descargar el país completo: se calculan por
AOI y se publican como índices con procedencia.

---

## 6. Evidencia reproducible

- `research/raw/phase3/probes_20261122_r3.json`: `stac_earth_search`,
  `stac_cdse`, `usgs_landsat_c2`, `lpdaac_modis`, `gpm_imerg`, `esa_worldcover`,
  `dynamic_world`, `gfw_hansen`, `ghsl`, `copernicus_clms`.
- `data/samples/phase3/sentinel2_stac/` — búsqueda STAC y lectura COG.
- `data/samples/phase3/chirps3_day/` — ráster validado (no satelital óptico,
  pero misma lógica de muestreo).
