# Normalización geoespacial

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/geo.py` · Pruebas: `tests/test_geo_normalization.py`

## 1. Reglas duras

1. **Se conserva el CRS original** de cada fuente. La normalización no destruye
   esa información: `transform_vector()` añade `_crs_source` y un registro en
   `attrs` con el CRS de origen y el motivo.
2. **EPSG:4326 es el formato de intercambio** (coordenadas geográficas), no un
   sistema para medir. `area_km2()` y `distance_m()` lanzan
   `GeographicMetricError` si se les pide calcular en grados.
3. Para cálculos métricos se elige una proyección **documentada**:
   - área pequeña dentro de una zona UTM → EPSG:32615 o 32616, declarando zona y
     factor de escala;
   - área nacional → **EPSG:6933** (cilíndrica de áreas equivalentes), porque El
     Salvador cruza las zonas 15 y 16 y una UTM única introduciría distorsión.
4. Nada se reproyecta sin motivo declarado (`reason`) y propósito (`purpose`).

## 2. Elección de CRS métrico

`choose_metric_crs(bounds)` devuelve una decisión, no un identificador suelto:

```json
{
  "epsg": 6933,
  "name": "WGS 84 / NSIDC EASE-Grid 2.0 Global",
  "equal_area": true,
  "reason": "extensión cruza zonas UTM 15 y 16",
  "scale_note": "proyección de áreas equivalentes; úsese para área y densidad, no para distancias locales"
}
```

Para una ventana pequeña devuelve la UTM correspondiente con `equal_area: false`
y la nota de escala. `utm_epsg(lon, lat)` calcula la zona; no se adivina.

Comprobación numérica: un cuadrado de 1°×1° en el ecuador mide ≈12.364 km². La
prueba exige un valor entre 11.000 y 13.500 km² y que **no** coincida con el área
en grados (1,0). Si alguien vuelve a calcular áreas en 4326, la prueba falla.

## 3. Transformación de vectores

```python
out = transform_vector(gdf, "EPSG:32616",
                       reason="pendiente y distancia en metros",
                       purpose="distance")
```

- exige CRS de origen y destino;
- rechaza destino geográfico si el propósito es área/distancia;
- conserva la tabla de atributos;
- registra `crs_original`, `crs_target`, `reason`, `purpose`, `preserved_original: true`;
- **no modifica** el GeoDataFrame de entrada.

`transform_geometry()` hace lo mismo para una geometría individual.

## 4. Validación de geometrías

`validate_geometries(gdf, bounds=SV_BOUNDS)` devuelve un `GeometryReport` con
comprobaciones nombradas y severidad:

| Comprobación | Qué detecta | Severidad |
|---|---|---|
| `geometrias_nulas` | geometría `None` | error |
| `geometrias_vacias` | `is_empty` | error |
| `geometrias_invalidas` | `is_valid == False` | error |
| `autointersecciones` | anillos que se cruzan (bowtie) | error |
| `duplicados_geometricos` | WKB idéntico | warning |
| `fuera_de_cobertura` | centroide/extensión fuera de El Salvador | error |
| `solapamientos_topologicos` | polígonos que se solapan | warning |

Una capa sin CRS no llega a este informe: `transform_vector()` y
`repair_geometries()` lanzan `CRSConversionError` antes de operar.

El reporte no repara nada. Un solapamiento puede ser legítimo (áreas protegidas
que se superponen); por eso es advertencia y se documenta, no se elimina.

## 5. Reparación no silenciosa

`repair_geometries()` es explícita y conserva el original:

- exige CRS;
- copia el archivo original a `backup_path` antes de tocar nada;
- calcula sha256 del original;
- aplica `make_valid` (u otro método declarado) y registra por geometría:
  `geometry_hash_before`, `geometry_hash_after`, `area_before`, `area_after`,
  `area_change_pct`, `method`, `reason`;
- añade la columna `geom_repaired`;
- devuelve `(gdf_reparado, RepairLog)`.

La prueba `test_reparacion_registrada_conserva_hash_y_area` verifica que el
polígono original sigue inválido (no se mutó) y que el log contiene hashes
distintos y cambio de área. No existe una ruta de reparación silenciosa.

## 6. Cobertura y solapamiento

`coverage_union(gdf)` calcula, en proyección de áreas equivalentes:

- suma de áreas individuales,
- área de la unión,
- área de solapamiento (suma − unión).

Se usa para detectar dobles conteos entre capas administrativas o áreas
protegidas. No «corrige» la capa: informa.

## 7. Casos reales de Fase 4

- **Copernicus DEM** se almacena en EPSG:4326; pendiente, aspecto, sombreado y
  clases de relieve se derivan en **EPSG:32616** a 30 m. El catálogo declara
  ambos CRS y el ráster derivado conserva la resolución nativa.
- **SoilGrids** se descubrió en **EPSG:32616**, no en 4326 como se suponía. El
  catálogo se corrigió y el catálogo ráster declara la rejilla UTM 16N. La
  consulta del proveedor reproyecta desde 4326; el archivo local no.
- **CHIRPS** está en EPSG:4326 a 0,05°. El recorte a El Salvador se hace sin
  remuestreo (`resampling: none`).
- **GeoBoundaries ADM1** está en EPSG:4326 y se usa para el índice territorial;
  las áreas se calculan en 6933, no en grados.

## 8. Límites

- No se implementó corrección topológica entre capas administrativas (por
  ejemplo, ajustar límites departamentales a una línea costera común). Se
  detectan solapamientos, no se reescriben límites oficiales.
- `make_valid` puede partir un polígono en varias partes; el log lo refleja en el
  cambio de área y en el WKT resultante, pero la decisión de aceptar la
  reparación es humana.
- La proyección nacional 6933 es adecuada para área; no para distancias de
  ingeniería ni para pendientes locales.
