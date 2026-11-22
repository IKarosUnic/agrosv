# MODULE K — Biodiversity and Ecosystem Services

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Integra conservación en la aptitud agrícola. No es un inventario de biodiversidad:
es un conjunto de capas y restricciones que permiten evaluar compatibilidad
entre producción y conservación, con datos verificables.

---

## 1. Capas y fuentes

| Capa | Fuente propuesta | Estado | Nota |
|---|---|---|---|
| Cobertura forestal | Sentinel-2 / Landsat (clasificación propia) | **DISEÑADO** | derivado AGROSV, no mapa oficial |
| Áreas protegidas | MARN / SINAP | **PENDING_VALIDATION** | sin shapefile verificado |
| Corredores ecológicos | MARN / PNGIRH | **DOCUMENTED** | sin geometría pública verificada |
| Cuerpos de agua | OSM (Fase 1) | **VERIFIED** | 1.205 polígonos |
| Ríos y quebradas | OSM (Fase 1) | **VERIFIED** | 7.880 km |
| Fragmentación | cálculo propio sobre cobertura | **DISEÑADO** | métricas de paisaje |
| Erosión (servicio) | RUSLE (Module J) | **DISEÑADO** | control de suelo |
| Polinizadores | literatura + cobertura floral | **PENDING_VALIDATION** | sin monitoreo nacional |

**Advertencia:** no se publicará un «mapa de áreas protegidas» propio si no se
obtiene la capa oficial. Mientras tanto, la capa se marca `unavailable` y la
restricción ambiental se aplica solo con datos verificados.

---

## 2. Métricas

| Métrica | Método | Uso |
|---|---|---|
| Superficie forestal | clasificación con validación (L2/L3) | línea base |
| Fragmentación | nº de parches, tamaño medio, densidad de borde | corredores |
| Conectividad | distancia al parche más cercano | corredores |
| Índice de vegetación | NDVI/NDMI (Module A) | estado |
| Riesgo de erosión | RUSLE (Module J) | servicio de control |
| Servicio de polinización | proxy por cobertura floral y distancia a hábitat | indicador, no medición |
| Carbono orgánico del suelo | SoilGrids (predicción) | indicador |

**Regla:** un servicio ecosistémico calculado con un proxy se etiqueta
`proxy` y no se monetiza.

---

## 3. Restricciones en la aptitud agrícola

El motor de aptitud (Module G / C) puede recibir restricciones:

```json
{
  "restrictions": [
    {"type": "protected_area", "buffer_m": 0, "source": "marn-sinap", "status": "pending"},
    {"type": "riparian_buffer", "buffer_m": 30, "source": "osm-waterway"},
    {"type": "slope_limit", "max_deg": 30, "source": "copdem30"},
    {"type": "erosion_risk", "max_class": "alta", "source": "rusle"}
  ]
}
```

Solo se aplican restricciones con fuente verificada. Las pendientes y la
hidrografía ya lo están; las áreas protegidas, no.

---

## 4. Modelo de datos

```sql
land_cover(
  grid_id TEXT, cell_id TEXT, date DATE,
  class TEXT, confidence TEXT, method TEXT, source_id TEXT
);

protected_area(
  pa_id TEXT PK, name TEXT, category TEXT,
  source_id TEXT, geometry GEOMETRY(MultiPolygon,4326)
);

landscape_metric(
  unit_id TEXT, metric TEXT, value NUMERIC,
  method TEXT, date DATE, source_id TEXT
);

ecosystem_service(
  service_id TEXT PK, type TEXT, geometry,
  indicator NUMERIC, unit TEXT, method TEXT,
  is_proxy BOOLEAN, source_id TEXT
);
```

---

## 5. Interfaz

```
GET /api/bio/landcover?bbox=&date=
GET /api/bio/protected-areas?bbox=
GET /api/bio/fragmentation?unit=basin&id=
GET /api/bio/services?type=erosion_control&bbox=
GET /api/bio/constraints?geometry=
```

---

## 6. Validación

| Prueba | Criterio |
|---|---|
| Cobertura | clases válidas; sin solapes |
| Área protegida | la capa oficial, si existe, prevalece sobre cualquier derivado |
| Métricas | fragmentación ≥ 0; bordes ≤ perímetro total |
| Proxy declarado | 100 % de servicios con `is_proxy` explícito |
| Restricción | toda restricción aplicada tiene fuente y fecha |

---

## 7. Limitaciones

1. Sin capa oficial de áreas protegidas, la restricción ambiental es parcial.
2. La clasificación de cobertura es propia y requiere validación (L2/L3).
3. La polinización no se mide; se aproxima.
4. La fragmentación depende de la resolución de la cobertura.
5. No se monetizan servicios ecosistémicos.

---

## 8. Dependencias y prioridad

Depende de: Module A (cobertura), Module J (erosión), MARN (áreas protegidas).
Habilita: restricciones en Module C/G.

**Prioridad:** baja-media. Primero la capa de cobertura validada; las áreas
protegidas solo cuando exista la fuente oficial.
