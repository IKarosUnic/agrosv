# MODULE A — Satellite Monitoring Engine

**Versión:** 2.0 · **Fecha:** 2026-11-22 · **Estado:** **aritmética de índices y máscaras implementada** (`backend/agrosv/science/indices.py`); **adquisición, compuestos y detección de candidatos no implementados**.

Motor de observación de la vegetación y de cambios territoriales. No sustituye
al motor de cultivos ni diagnostica plagas: produce series, índices, anomalías
y candidatos con nivel de confianza.

---

## 1. Fuentes (estado verificado)

| Fuente | Producto | Resolución | Frecuencia | Acceso | Licencia | Estado |
|---|---|---|---|---|---|---|
| Sentinel-2 | L2A (reflectancia superficial) | 10/20/60 m | ~5 días (2 satélites) | STAC CDSE + cuenta | Copernicus Legal Notice (libre, comercial) | **VERIFIED** (STAC) |
| Sentinel-1 | IW GRD | 10 m (spacing), 20×22 m | 6–12 días | CDSE, cuenta | Copernicus | **VERIFIED** (catálogo) |
| Landsat 8/9 | Collection 2 L2 | 30 m (15 m pan) | 16 d; 8 d combinados | USGS/EROS, **login** | Dominio público | **RESTRICTED** (registro) |
| MODIS | MOD13Q1 NDVI/EVI | 250 m | 16 días | LP DAAC, Earthdata login | Abierta NASA | **RESTRICTED** (registro) |
| VIIRS | VJ113A1 / VJ213A1 (NDVI/EVI) | 500 m | 16 días | LP DAAC | Abierta NASA | **PENDING_VALIDATION** |
| GPM IMERG | Precipitación | 0,1° (~10 km) | 30 min | GES DISC, Earthdata | Abierta NASA | **RESTRICTED** (registro) |
| NOAA CPC | Precipitación diaria | 0,5° | diaria | FTP/HTTPS abierto | Sin restricciones | **VERIFIED** |
| SMAP | Humedad del suelo | 9 km | 3 h | NSIDC, Earthdata | Abierta NASA | **RESTRICTED** (registro) |

**Caducidades que condicionan el diseño:** Terra MODIS cesa adquisiciones el
**2026-12-01**; Suomi-NPP VIIRS deja de distribuirse el **2026-11-02**. El
motor debe usar **VJ113A1/VJ213A1** como camino principal y MODIS solo para la
serie histórica 2000–2026.

**Cuotas:** CDSE aplica límite de transferencia mensual (12 TB en cuenta
general, ventana de 30 días) y reduce velocidad al excederse. El diseño asume
**descarga selectiva por área de interés y banda**, nunca mosaicos nacionales
completos en memoria.

---

## 2. Índices y variables

| Índice | Fórmula | Uso | Advertencia |
|---|---|---|---|
| NDVI | (NIR−R)/(NIR+R) | vigor, fenología | satura en dosel denso |
| EVI | 2,5·(NIR−R)/(NIR+6R−7,5B+1) | biomasa en zonas densas | sensible a aerosol |
| NDWI | (G−NIR)/(G+NIR) | agua superficial | no confundir con humedad de suelo |
| NDMI | (NIR−SWIR1)/(NIR+SWIR1) | humedad de la vegetación | requiere SWIR (20 m en S2) |
| NBR | (NIR−SWIR2)/(NIR+SWIR2) | severidad de incendio | — |
| Cobertura vegetal | fracción derivada de NDVI | estructura | es una estimación, no un censo |

**Regla de resolución:** los índices se calculan con las bandas nativas
(10 m para NDVI/NDWI; 20 m para NDMI/NBR en S2) y la capa declara la resolución
efectiva del índice. No se remuestrea 20 m a 10 m para «mejorar» la apariencia.

---

## 3. Funciones y contrato

```
sat.composite(region, period, source)        → compuesto sin nubes (mediana)
sat.index(composite, name)                   → raster de índice + máscara
sat.anomaly(series, baseline)                → z-score o percentil por celda
sat.change(before, after, method)            → máscara de cambio + magnitud
sat.candidates(region)                       → polígonos L1 (candidato agrícola)
sat.series(geometry, index, from, to)        → serie temporal por unidad
```

Endpoints previstos (no implementados):

```
GET /api/sat/series?geometry=<GeoJSON>&index=ndvi&from=&to=
GET /api/sat/anomaly?level=department&code=&index=ndvi&period=2025-06
GET /api/sat/changes?from=&to=&min_area_ha=
GET /api/sat/candidates?level=department&code=
```

Toda respuesta incluye `source_id`, `platform`, `native_resolution`,
`cloud_cover_pct`, `composite_method`, `quality` y `provenance_id`.

---

## 4. Método

1. **Selección**: catálogo STAC por bbox, fecha y cobertura de nubes < 30 %.
2. **Compuesto**: mediana por píxel de las escenas del periodo (mensual);
   enmascarado con la banda SCL (S2) o QA (Landsat).
3. **Índices**: cálculo por banda nativa, sin remuestreo previo.
4. **Anomalía**: contra la misma celda en la línea base 2019–2024 (declarada),
   usando z-score robusto (mediana/MAD) para no depender de la media.
5. **Cambio**: diferencia de compuestos + umbral calibrado por clase; se
   publica como «cambio detectado», no como «deforestación» ni «pérdida».
6. **Candidatos agrícolas**: ver `URBAN_AGRICULTURE.md` §3 (L0–L3). El motor
   satelital solo produce L0/L1; nunca L3.

---

## 5. Validación

| Prueba | Criterio |
|---|---|
| Índice en rango | NDVI/NDWI/NDMI/NBR ∈ [−1, 1]; sin NaN fuera de máscara |
| Coherencia | NDVI de agua ≈ negativo; NDWI de agua ≈ positivo |
| Compuesto | cobertura de nubes declarada = medida |
| Anomalía | media de la línea base ≈ 0 (± 0.05) |
| Cambio | la máscara no incluye nubes ni sombras |
| Trazabilidad | cada escena usada tiene `scene_id` y fecha |

Sin estas pruebas, la capa no se publica.

---

## 6. Incertidumbre

- **Píxeles mixtos**: un píxel de 10 m puede contener cultivo, suelo y sombra.
- **Nubes y sombras**: en la estación lluviosa reducen la serie; se declara el
  número de observaciones válidas por compuesto.
- **Saturación de NDVI** en coberturas densas (café bajo sombra).
- **Cambio de plataforma** (MODIS Terra → VIIRS): series no comparables sin
  armonización; se marca el corte.

---

## 7. Limitaciones explícitas

1. No distingue cultivo de otra vegetación (eso es L1/L2 con validación).
2. No diagnostica plagas, enfermedades ni estrés específico.
3. No mide rendimiento.
4. No sustituye censos ni trabajo de campo.
5. La resolución de visualización (teselas) no es la resolución del dato.

---

## 8. Dependencias y prioridad

Depende de: STAC CDSE (o mirror), `GRID_DATA_SPECIFICATION.md`, geometrías
municipales. Habilita: Module C (forzantes), Module G (urbano), Module L
(validación comunitaria).

**Prioridad:** alta, pero **después** de clima histórico (Fase 1.5), porque el
motor necesita una línea base climática para interpretar anomalías.

---

## 9. Implementado en este ciclo (2026-11-22)

`backend/agrosv/science/indices.py` implementa el cálculo declarado por fórmula:

| Índice | Bandas | Resolución declarada | Prueba |
|---|---|---|---|
| NDVI | NIR, R | 10 m (Sentinel-2 B08/B04) | valor analítico (0,5/0,1 → 0,667) |
| EVI | NIR, R, B | 10 m | fórmula publicada verificada |
| NDWI | G, NIR | 10 m | agua → positivo |
| NDMI | NIR, SWIR1 | **20 m** (B11 nativa) | valor analítico |
| NBR | NIR, SWIR2 | **20 m** (B12 nativa) | valor analítico (0,333) |

Reglas aplicadas en código, no en prosa:

- denominador nulo → `NaN`, nunca `0` (un cero es un índice válido);
- salida recortada a [−1, 1];
- `change_mask` exige un umbral positivo y devuelve «cambio detectado», no
  «deforestación»;
- `series_anomaly` usa mediana/MAD contra una línea base declarada.

`GET /api/v1/indices` publica estas fichas y declara explícitamente lo que **no**
existe: adquisición STAC, enmascarado de nubes y compuestos. No se sirve ninguna
serie satelital porque no hay escenas archivadas; publicarlas sería inventarlas.
