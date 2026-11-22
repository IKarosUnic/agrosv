# AGROSV — acceso a datos externos e incorporación controlada (Fase 7)

**Estado:** implementado el registro, los validadores, la correspondencia
municipal 2023 y el cálculo de error del DEM. **No** se adquirieron series de
estación, muestras de laboratorio, cuencas oficiales, aforos ni puntos GNSS.

**Regla:** un portal público, un metadato o una página de servicio no equivalen
a un dato adquirido. AGROSV no descarga, no imputa y no sustituye una serie
faltante con valores sintéticos.

## 1. Qué se añadió

| Componente | Ruta | Estado |
|---|---|---|
| Registro de seis fuentes | `backend/agrosv/onboarding/registry.py` | implementado |
| Validadores estrictos | `backend/agrosv/onboarding/validators.py` | implementado |
| Correspondencia 2023 | `data/reference/municipality_crosswalk_2023.csv` | **adquirida** (14/44/262) |
| Consulta y agregación municipal | `backend/agrosv/onboarding/municipalities.py` | implementado |
| Error vertical del DEM | `backend/agrosv/onboarding/dem.py` | implementado; sin puntos GNSS no hay resultado |
| API | `/api/onboarding` | 8 endpoints |
| CLI | `scripts/11_validate_external_data.py` | implementado |
| Zona de entrega | `data/external/` | existe; no versionada |
| Pruebas | `tests/test_phase7_onboarding.py` | 21 pruebas |

## 2. Correspondencia municipal 2023 (única fuente adquirida)

La Asamblea Legislativa publica la distribución de los 262 distritos entre los
44 municipios creados por el Decreto Legislativo N.° 762, vigente desde el
**1 de mayo de 2024**.

- Fuente: <https://www.asamblea.gob.sv/node/12806>
- Instrumento: `Decreto Legislativo N.° 762, Ley Especial para la
  Reestructuración Municipal`
- Conteos verificados: **14 departamentos, 44 municipios, 262 distritos**.
- Archivo: `data/reference/municipality_crosswalk_2023.csv` (una fila por
  distrito).
- Procedencia y SHA-256: `data/reference/municipality_crosswalk_2023.provenance.json`.

Columnas: `department`, `municipality`, `district`, `municipality_id`,
`district_id`, `legal_instrument`, `effective_date`, `source`, `official_code`.

`municipality_id` (`SV-MUN-...`) y `district_id` (`SV-DIS-...`) son
identificadores **AGROSV**. La fuente no publica códigos oficiales;
`official_code` queda vacío en lugar de inventarse.

### Correcciones de digitalización

La página de la Asamblea contiene errores de OCR en nombres de distrito. Se
corrigieron contra la forma conocida y se documentan aquí y en la procedencia:

| OCR publicado | Forma usada |
|---|---|
| `llopango` | Ilopango |
| `llobasco` | Ilobasco |
| `lntipucá` | Intipucá |
| `lzalco` | Izalco |
| `lshuatán` | Ishuatán |
| `lstepeque` | Istepeque |
| `Menendez` | Menéndez |
| `Umana` | Umaña |
| `Bolivar` | Bolívar |
| `Huizucar` | Huizúcar |
| `Chiltuipán` | Chilcuipán |

No se corrigió ningún conteo ni se añadió un distrito que la fuente no liste.

### Consulta

```bash
.venv/bin/python - <<'PY'
from agrosv.onboarding import municipalities as M
print(M.summary()["counts"])                 # 14 / 44 / 262
print(M.municipality_of("Ilopango"))         # San Salvador Este
print(M.municipality_of("El Rosario"))       # ambiguo: falta departamento
print(M.municipality_of("El Rosario", "La Paz"))
print(M.districts_of("Sonsonate Oeste"))     # Acajutla
PY
```

`aggregate_rows` agrega filas históricas por nombre de distrito. Un nombre
repetido (`El Rosario`, `San Rafael`, ...) exige `department`; si no, la fila
va a `unmapped` con la razón y no se elige un municipio al azar.

## 3. Fuentes registradas y no adquiridas

| Fuente | Estado | Qué desbloquea | Sustituto actual declarado |
|---|---|---|---|
| SNET/MARN series diarias | metadatos públicos; series por solicitud | validar reanálisis, ET0 local, fenología observada | Open-Meteo/NASA POWER, reanálisis puntual |
| CENTA Laboratorio de Suelos | restringido por solicitud | calibrar SoilGrids; CEC, textura y nutrientes medidos | SoilGrids 0–30 cm, predicción |
| Cuencas oficiales MARN | portal público sin capa vectorial confirmada | códigos oficiales y balance por cuenca | cuenca D8 derivada, sin código oficial |
| Aforos y caudales MARN | metadatos públicos; series por solicitud | validar escorrentía y curva de duración | balance P−ET0 contable, no caudal |
| Correspondencia 2023 | **adquirida** | agregación histórica → 44 municipios | no aplica |
| GNSS/CNR | servicio arancelado | error vertical del DEM | DEM sin exactitud vertical declarada |

URLs:

- Series: <https://snet.gob.sv/ver/hidrologia/archivo+historico/series+historicas>
- Caudales: <https://snet.gob.sv/ver/hidrologia/monitoreo+hidrologico/caudales>
- Atlas SIHI: <https://srt.snet.gob.sv/simih/public/atlas>
- CENTA suelos: <https://www.centa.gob.sv/servicios/suelos>
- Portal de mapas CENTA: <https://portal-de-mapas-digitales-del-centa-centa.hub.arcgis.com/>
- CNR geodesia: <https://www.cnr.gob.sv/servicios/detalle-de-servicios-del-instituto-geografico-y-del-catastro-nacional/>

Las condiciones de licencia están en el registro. MARN permite reproducción
citando la fuente; la redistribución de series crudas debe confirmarse por
escrito. CENTA no declara licencia para microdatos. El CNR cobra por vértices y
bancos de marca.

## 4. Esquemas aceptados

Todos los CSV son **largos** (una observación por fila), UTF-8 y con encabezado.
`null` vacío se rechaza: un hueco no se rellena.

### 4.1 `station_series`

`station_id, date, variable, value, unit, latitude, longitude, source`

Variables y unidades exactas: `precipitation` (mm), `temperature_max`,
`temperature_min`, `temperature_mean` (°C), `relative_humidity` (%),
`wind_speed` (m/s), `et0` (mm). Se rechazan duplicados
(estación, fecha, variable), fechas inválidas, coordenadas fuera del
rectángulo nacional y precipitación negativa. La continuidad diaria **no** se
exige: un hueco se conserva.

### 4.2 `centa_samples`

`sample_id, date, latitude, longitude, depth_cm, variable, value, unit,
lab_method, source`

Variables admitidas con rango físico: pH, materia orgánica, N total, P
disponible, K/Ca/Mg intercambiables, CEC, arcilla, arena, limo y CE. Se exige
método de laboratorio y profundidad numérica (cm). No se convierte unidad ni
se compara automáticamente con SoilGrids.

### 4.3 `basins` (GeoJSON)

`FeatureCollection` con `Polygon`/`MultiPolygon` y propiedades
`basin_code`, `name`, `area_km2`. Se valida geometría con Shapely, área
geodésica WGS84 con pyproj y unicidad de código. Una diferencia >10 % entre
área declarada y calculada se advierte, no se corrige.

### 4.4 `gauging`

`station_id, date, discharge_m3s, basin_code, source`. Caudal negativo o
duplicado (estación, fecha) se rechaza. Cero es un valor válido y se cuenta
aparte.

### 4.5 `crosswalk`

`department, municipality, district, legal_instrument, effective_date, source`
(más IDs AGROSV opcionales). Se rechazan distritos duplicados en un
departamento, municipios en dos departamentos y conteos que superen 14/44/262.
Un subconjunto se acepta con advertencia.

### 4.6 `gnss`

`point_id, latitude, longitude, date, source, horizontal_accuracy_m,
vertical_accuracy_m` y **una** de estas formas de altura:

- `orthometric_height_m`, o
- `ellipsoidal_height_m` + `geoid_undulation_m`.

Sin altura ortométrica ni ondulación declarada se rechaza: no se supone un
geoide.

## 5. Uso

```bash
# validar
PYTHONPATH=backend .venv/bin/python scripts/11_validate_external_data.py \
  --kind station_series --path data/external/estaciones.csv

# validar y comparar GNSS con el DEM
PYTHONPATH=backend .venv/bin/python scripts/11_validate_external_data.py \
  --kind gnss --path data/external/gnss.csv --dem-error

# correspondencia incluida
PYTHONPATH=backend .venv/bin/python scripts/11_validate_external_data.py \
  --kind crosswalk --path data/reference/municipality_crosswalk_2023.csv
```

API:

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/api/onboarding/meta` | fuentes, conteos y política |
| GET | `/api/onboarding/sources` | registro completo |
| GET | `/api/onboarding/sources/{id}` | ficha de una fuente |
| GET | `/api/onboarding/municipalities/summary` | 14/44/262 y procedencia |
| GET | `/api/onboarding/municipalities/lookup?district=` | municipio vigente |
| GET | `/api/onboarding/municipalities/districts?municipality=` | distritos |
| POST | `/api/onboarding/validate` | informe `{kind, path}` |
| POST | `/api/onboarding/dem-error` | métricas `{path}` GNSS |

Solo se leen rutas relativas bajo `data/external/` o `data/reference/`. Una
ruta absoluta o con `..` devuelve 400; un archivo inexistente, 404. Validar no
modifica el archivo.

## 6. Error vertical del DEM

El DEM es Copernicus GLO-30: **DSM** de 30 m, altitudes ortométricas EGM2008.
Para cada punto GNSS:

```
H = altura ortométrica
  = altura elipsoidal − ondulación del geoide   (si se aporta así)
d = DEM(lon, lat) − H
```

Se calculan `n`, sesgo, MAE, RMSE, desviación estándar, P95 de |d|, mínimo,
máximo y fracción de puntos dentro de la exactitud vertical declarada. Los
puntos sin dato en el DEM se listan como `skipped`, no se interpolan.

Límites: el DSM incluye dosel y edificaciones; una muestra pequeña no
representa el error nacional; no se evalúa error horizontal; la exactitud
depende de la época y el levantamiento GNSS. **No se declara una exactitud del
DEM sin puntos de control.** El resultado lleva
`is_official_dem_accuracy: false`.

## 7. Separación de capas

- `OBSERVED_VALIDATION_DATA`: solo si se aporta un archivo observado y validado.
- `SOURCE_PROFILE`: metadatos, URLs, licencias y requisitos.
- `SYNTHETIC_*`: no se usa para rellenar una fuente faltante.
- El error del DEM es un cálculo sobre datos observados; no es una capa
  sintética ni una calibración.

## 8. Pruebas y límites

`tests/test_phase7_onboarding.py` verifica: registro de seis fuentes; conteos
14/44/262; SHA-256 de la correspondencia; resolución de ambigüedades;
validadores de estaciones, CENTA, cuencas, aforos, correspondencia y GNSS;
métricas del DEM con dos puntos sintéticos de prueba (el DEM es real; las
alturas del fixture no son una medición); y rechazo de rutas fuera de
`data/`.

No se probó ningún archivo real de SNET, CENTA, MARN o CNR porque no se
adquirió ninguno. Los esquemas se derivan de lo que cada institución tendría
que entregar; si su formato difiere, se adapta el validador, no el dato.

## 9. Procedimiento de incorporación

1. Solicitar por escrito con `DATA_REQUEST_TEMPLATES.md`.
2. Guardar el archivo original en `data/external/` con fuente y fecha.
3. Validar con el CLI; corregir el archivo, nunca el validador para que pase.
4. Documentar procedencia, licencia, unidad, cobertura y limitaciones.
5. Solo entonces mover el resultado derivado a `data/processed/` y declararlo
   en `docs/DATA_PROVENANCE.md` y `docs/LIMITATIONS.md`.

## 10. Estado final

La Fase 7 no aumenta la exactitud de AGROSV por sí sola: elimina la ambigüedad
municipal y deja preparada la incorporación de las cinco fuentes que faltan.
Cualquier cifra de rendimiento, caudal, suelo o error del DEM sigue sin
validación local hasta que esas fuentes existan.
