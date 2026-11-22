# MODULE D — Farm and Parcel Management

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Gestión digital de explotaciones y parcelas: la única parte de AGROSV donde se
**escriben** datos. Todo lo demás es lectura. Eso cambia los requisitos:
autenticación, propiedad del dato, historial y protección de información privada.

---

## 1. Alcance funcional

| Función | Descripción | Obligatorio |
|---|---|---|
| Dibujar parcela | Polígono en el mapa o coordenadas | Sí |
| Importar geometría | GeoJSON, KML, GPX, Shapefile (con validación) | Sí |
| Calcular superficie | EPSG:6933 (equal-area), no Web Mercator | Sí |
| Sectores productivos | Subdivisión de la parcela | Sí |
| Cultivo y variedad | Catálogo + variedad declarada | Sí |
| Historial de siembra | Fecha, superficie, ciclo | Sí |
| Fertilización | Producto, dosis, fecha, costo | Sí |
| Riego | Fuente, volumen, método | Sí |
| Tratamientos | Producto, dosis, motivo | Sí |
| Cosecha | Fecha, producción, destino | Sí |
| Producción real | kg/ha o qq/mz | Sí |
| Fotografías y observaciones | Adjuntos georreferenciados | Sí |
| Comparación entre temporadas | Series por parcela | Sí |

---

## 2. Modelo de datos

```sql
farm(
  farm_id UUID PK, owner_id UUID, name TEXT,
  created_at, updated_at
);

parcel(
  parcel_id UUID PK, farm_id UUID FK,
  geometry GEOMETRY(Polygon, 4326),
  area_ha NUMERIC,              -- calculada en EPSG:6933
  soil_source TEXT,             -- 'soilgrids' | 'centa' | 'field'
  elevation_m NUMERIC,
  slope_deg NUMERIC,
  privacy_level TEXT            -- 'private' | 'aggregate_only'
);

production_sector(
  sector_id UUID PK, parcel_id UUID FK, geometry, area_ha, label
);

crop_cycle(
  cycle_id UUID PK, parcel_id UUID FK, sector_id UUID NULL,
  crop_code TEXT, variety TEXT,
  sowing_date DATE, harvest_date DATE NULL,
  season TEXT,                  -- 'primera' | 'postrera' | 'apante'
  expected_yield NUMERIC, actual_yield NUMERIC,
  unit TEXT
);

field_operation(
  op_id UUID PK, cycle_id UUID FK,
  op_type TEXT,                 -- 'fertilizacion'|'riego'|'tratamiento'|'labor'
  op_date DATE, product TEXT, dose NUMERIC, dose_unit TEXT,
  cost_usd NUMERIC, notes TEXT
);

observation(
  obs_id UUID PK, parcel_id UUID FK, cycle_id UUID NULL,
  observed_at TIMESTAMPTZ, category TEXT,
  geometry GEOMETRY(Point,4326), photo_path TEXT, notes TEXT,
  evidence_level TEXT           -- ver CROP_HEALTH §1
);
```

**Regla de superficie:** se almacena la geometría en EPSG:4326 y se calcula el
área en EPSG:6933 al guardar; nunca se recalcula en Mercator para mostrarla.

---

## 3. Privacidad y seguridad

1. **Propiedad**: cada parcela pertenece a un `owner_id`; nadie más la ve
   completa.
2. **Agregación**: la vista pública solo muestra agregados por distrito con
   supresión < 5 parcelas.
3. **Ubicación**: no se publica el centroide ni la geometría de una parcela
   privada; los análisis externos usan el polígono internamente y devuelven solo
   resultados.
4. **Consentimiento**: el productor autoriza explícitamente qué se comparte y
   con quién; se guarda la versión del consentimiento.
5. **Borrado**: eliminar una parcela elimina sus registros y adjuntos; el
   historial agregado ya publicado no se reescribe (se documenta la baja).
6. **Autenticación**: obligatoria para escribir. Fase 2 no define proveedor;
   cualquier solución debe permitir exportar y borrar los datos del usuario.
7. **Sin datos personales innecesarios**: no se pide documento, teléfono ni
   dirección; solo lo que el productor decida.

---

## 4. Interfaz

```
POST   /api/farms
POST   /api/farms/{farm_id}/parcels
PATCH  /api/parcels/{parcel_id}
GET    /api/parcels/{parcel_id}          (propietario)
POST   /api/parcels/{parcel_id}/cycles
POST   /api/cycles/{cycle_id}/operations
POST   /api/parcels/{parcel_id}/observations
GET    /api/parcels/{parcel_id}/history?from=&to=
GET    /api/parcels/{parcel_id}/compare?seasons=2025,2026
GET    /api/farms/{farm_id}/export       (GeoJSON + CSV autorizados)
```

Ningún endpoint devuelve parcelas de otro usuario. Los endpoints de análisis
(`/api/sim/crop/run`, `/api/sat/series`) aceptan una parcela solo si el
solicitante es propietario o tiene permiso explícito.

---

## 5. Validación

| Prueba | Criterio |
|---|---|
| Geometría | válida, sin auto-intersecciones; se repara con `make_valid` y se avisa |
| CRS | entrada 4326; área en 6933 |
| Área | > 0,01 ha y < 10.000 ha (fuera de rango → revisión) |
| Solapes | dos parcelas del mismo dueño no se solapan > 5 % sin confirmación |
| Fechas | siembra < cosecha; operaciones dentro del ciclo |
| Unidades | kg/ha, qq/mz, m³/ha declarados; 1 mz = 0,6989 ha |
| Adjuntos | tipo y tamaño permitidos; sin metadatos EXIF de ubicación al publicar |

---

## 6. Relación con los motores científicos

| Motor | Qué recibe de la parcela | Qué devuelve |
|---|---|---|
| Module C (simulación) | geometría, suelo, ciclo, manejo | rendimiento simulado + incertidumbre |
| Module A (satélite) | geometría y fechas | serie de índices y anomalías |
| Module E (economía) | operaciones y costos | margen estimado |
| Module F (alertas) | ubicación | alertas que aplican |
| Module H (gemelo digital) | todo el historial | estado sincronizado |

La parcela es la **unidad de unión** entre datos reales y modelos. Sin ella, los
motores solo trabajan a escala de celda climática o municipio.

---

## 7. Limitaciones

1. Requiere autenticación y almacenamiento persistente: **no** es Fase 1
   (que es solo lectura).
2. No sustituye un catastro: la parcela declarada no tiene validez legal.
3. La calidad depende de quien digita; se marcan campos sin verificar.
4. La importación de Shapefile puede traer CRS erróneo: siempre se pide el CRS.
5. La privacidad impide publicar mapas de parcelas individuales.

---

## 8. Dependencias y prioridad

Depende de: catálogo de cultivos, territorio, autenticación, almacén de
escritura (SQLite/PostgreSQL). Habilita: Module H (gemelo digital), Module M
(experimentos), Module L (contribución).

**Prioridad:** media. Es imprescindible para el gemelo digital y para validar
modelos con datos reales, pero **no** debe construirse antes de que existan
datos de clima y suelo que hagan útiles los análisis.
