# SatelliteDataEngine — datos satelitales y adaptadores

**Módulo:** `backend/agrosv/monitoring/satellites.py`
**Endpoint:** `GET /api/monitoring/sources`, `POST /api/monitoring/satellite/*`
**Versión:** 7.0.0

## Estado real

- **Once fuentes evaluadas y documentadas** (siete sensores/plataformas de
  observación y cuatro plataformas de acceso).
- **Cero escenas integradas en el repositorio.** `integration_status` lo declara
  fuente por fuente.
- Dos adaptadores implementados y probados con un ráster sintético:
  `read` (GeoTIFF/COG local, por ventana) y `parse_stac` (Item/ItemCollection
  STAC local).

## Fichas de fuente

Toda ficha declara los campos exigidos por §4.1: proveedor, satélite, sensor,
resolución, frecuencia temporal, bandas, cobertura, histórico, nivel de
proceso, nubes, método de acceso, licencia, restricciones, actualización,
formato, estado de integración, limitaciones y URL. `REQUIRED_SOURCE_FIELDS`
lo comprueba al construir el catálogo.

| Fuente | Resolución | Frecuencia | Acceso | Estado |
|---|---|---|---|---|
| Sentinel-2 MSI | 10/20/60 m | ~5 d | CDSE (STAC/OData) | adaptador, sin ingesta |
| Sentinel-1 C-SAR | 10/40 m | 6–12 d | CDSE | solo evaluado |
| Landsat 8 OLI/TIRS | 30 m (térmico 100) | 16 d | EarthExplorer/Earthdata | solo evaluado |
| Landsat 9 OLI-2/TIRS-2 | 30 m | 16 d (8 d combinado) | EarthExplorer/Earthdata | solo evaluado |
| MODIS | 250/500/1000 m | diario/16 d | LP DAAC | solo evaluado |
| VIIRS | 375/750 m | diario | LAADS DAAC | solo evaluado |
| Copernicus Data Space | — | — | portal | catálogo planificado |
| NASA Earthdata | — | — | portal | catálogo planificado |
| USGS EarthExplorer | — | — | portal/M2M | catálogo planificado |
| Google Earth Engine | — | — | API | opcional, no configurado |
| MARN/SNET D3-DOA | no publicada | no publicada | web/solicitud | acceso pendiente |

Todas las fuentes abiertas se pueden procesar localmente. GEE **no** es
dependencia: es una plataforma externa opcional y su resultado exigiría
exportación y versión documentada.

## Contrato de lectura

```python
SatelliteDataEngine().read(
    path, bands={"nir": 8, "red": 4}, bounds=(w, s, e, n),
    cloud_band=13, reflectance_scale=1e-4, reflectance_offset=-0.1)
```

- `bands`: nombre lógico → índice 1-based.
- `bounds`: ventana en el CRS del archivo (no se carga el ráster completo).
- nodata y máscara de nube se aplican a `valid_mask`; **la banda conserva el
  valor** y el píxel inválido se excluye del cálculo.
- `SCL_INVALID_CLASSES = {0,1,2,3,8,9,10,11}` (SCL de Sentinel-2 L2A).
- La escala de reflectancia se declara por parámetro; no se adivina.

`inspect` devuelve CRS, resolución, bounds, dtype, nodata, bloques, overviews,
fecha de adquisición de etiquetas y descripciones de banda.

## STAC

`parse_stac` lee metadatos locales y devuelve `network_used: false`.
`stac_search_plan` construye la petición (endpoint, colecciones, bbox,
intervalo) y la marca `executed: false`. Sin red ni credenciales no se ejecuta:
un adaptador que finge consultar sería peor que no tenerlo.

## Limitaciones

1. No hay escenas ni productos satelitales descargados: toda la cadena queda
   probada con fixtures sintéticos claramente etiquetados.
2. La resolución nominal no garantiza precisión parcelaria.
3. Sentinel-1 no se usa para humedad del suelo en esta fase.
4. No se configuran credenciales ni se almacenan productos pesados.
5. La fecha de adquisición depende de las etiquetas del archivo.
