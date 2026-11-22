# AgriculturalRiskMappingEngine — capas GeoJSON

**Módulo:** `backend/agrosv/monitoring/integration.py`
**Endpoint:** `POST /api/monitoring/risk-map`
**Versión:** 7.0.0

## Salida

`FeatureCollection` de puntos con `properties`:

- `value`, `indicator`, `unit`;
- `modeled` (booleano), `evidence_class`;
- `source`, `observation_date`, `confidence`.

`metadata` de capa:

- indicador, fuente, fecha, `resolution_m`, `crs`, metodología, confianza,
  limitaciones, `modeled`, `interpolated: false`, número de entidades.

## Reglas

1. Toda capa exige fuente y metodología; sin ellas se rechaza.
2. Los puntos deben caer dentro de El Salvador.
3. Los puntos sin valor se omiten; si no queda ninguno, error.
4. **No se interpola** entre puntos ni se genera una superficie.
5. Un valor modelado se etiqueta `model_estimate` y `modeled: true`; no se
   presenta como medición directa.

## Formatos

La respuesta es GeoJSON. GeoPackage y COG no se generan en esta fase: no hay
dependencia de escritura vectorial ni ráster derivada, y añadirla sin datos
reales no aportaría verificación. La API documenta esta ausencia.

## Limitaciones

1. Solo puntos; no hay polígonos administrativos ni máscaras de cultivo.
2. La resolución declarada es la de la fuente, no la del espaciado de puntos.
3. Un mapa de riesgo modelado no es un mapa de daño observado.
4. No se publican capas sin metadatos completos.

## Validación

Pruebas: dos puntos, uno sin valor, producen una entidad y metadatos completos;
un punto fuera del país se rechaza.
