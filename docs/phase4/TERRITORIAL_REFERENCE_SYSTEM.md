# Sistema de referencia territorial

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/territory.py` · Datos: `data/metadata/territory_index.json` · Pruebas: `tests/test_geo_normalization.py`, `tests/test_data_api.py`

## 1. Principio

Un territorio se identifica por un **código estable**, no por su nombre. Los
nombres cambian por reformas administrativas, varían en ortografía y se repiten
(por ejemplo, varios municipios homónimos en distintos departamentos). Depender
del nombre produce uniones incorrectas que no siempre fallan de forma visible.

```
nombre normalizado ≠ identidad
código + nivel + fuente + vigencia = identidad
```

## 2. Niveles

`LEVELS` define prefijo, padre y si el límite oficial es obligatorio:

| Nivel | Prefijo | Padre | Oficial requerido |
|---|---|---|---|
| `country` | `SV` | — | sí |
| `department` | `SV-ADM1` | country | sí |
| `municipality_2023` | `SV-ADM2` | department | sí |
| `municipality_historic` | `SV-ADM2H` | department | no |
| `district` | `SV-DIS` | municipality_2023 | sí |
| `basin` | `SV-BAS` | country | no |
| `subbasin` | `SV-SUB` | basin | no |
| `microbasin` | `SV-MIC` | subbasin | no |
| `protected_area` | `SV-AP` | country | no |
| `agricultural_unit` | `SV-AGU` | department | no |
| `parcel` | `SV-PAR` | district | no |

`make_territory_id(level, source_code, name)` produce el ID a partir del código
de fuente cuando existe; el nombre solo entra como componente de respaldo y se
normaliza (minúsculas, sin acentos, guiones). Un nombre repetido dentro del mismo
padre lanza `AmbiguousTerritoryError`: no se elige uno arbitrariamente.

## 3. Contenido real

`territory_index.json` contiene **287 territorios**:

| Nivel | N | Fuente | Estado |
|---|---|---|---|
| country | 1 | derivado de ADM1 (unión) | oficial |
| department | 14 | GeoBoundaries ADM1 | oficial, ISO 3166-2:SV |
| municipality_historic | 272 | GeoBoundaries ADM2 (pre-reforma 2023) | no oficial para 2023 |
| **Total** | **287** | | |

**No hay** `municipality_2023`, `district`, `basin`, `subbasin`, `microbasin`,
`protected_area`, `agricultural_unit` ni `parcel`. Esas capas no estaban
disponibles con límites verificables en la Fase 3. El sistema **no las
sintetiza**: `assert_no_synthetic_boundaries()` falla si se intenta registrar un
nivel oficial sin fuente y código.

La API lo declara: `GET /api/data/territories?level=municipality_2023` devuelve
`total: 0` con la nota «no se sintetizan límites». Un mapa vacío es honesto; un
mapa inventado no.

## 4. Correspondencia 2023

La reforma municipal de 2023 redujo 262 distritos a 44 municipios. No existe en
el repositorio una tabla oficial verificada distrito → municipio 2023. El archivo
`data/metadata/crosswalks/district_2023_municipality.json` se crea con
`status: "INCOMPLETE"` y sin filas:

```json
{
  "source_level": "municipality_historic",
  "target_level": "municipality_2023",
  "status": "INCOMPLETE",
  "limitation": "No existe en el repositorio una tabla oficial verificada...",
  "required_evidence": "Publicación del BCR/CNR con códigos de distrito y municipio, fecha de vigencia y decreto de reforma"
}
```

`CrosswalkTable.coverage()` devuelve 0 % y se publica en el resumen de
construcción. Inventar la correspondencia rompería la comparabilidad con el
censo; por eso se deja vacía y se marca.

## 5. Geometría y áreas

Cada entrada (`TerritoryEntry`) guarda:

- `territory_id`, `level`, `name`, `name_norm`, `parent_id`;
- `source_code`, `source_id`, `official`;
- `area_km2` calculada en **EPSG:6933** (nunca en grados);
- `bbox`, `centroid`;
- `geometry` (GeoJSON) o `geometry_ref` (ruta al GeoPackage).

La base SQLite normaliza estos campos en la tabla `territories`, con índice por
nivel. El GeoPackage completo (1,6 MB) permanece en `data/processed/`; la base
solo guarda la geometría necesaria para consultas puntuales, no una copia del
archivo.

## 6. Consultas

- `GET /api/data/territories?level=department&parent_id=SV` → 14.
- `GET /api/data/territory/SV` → país con 14 hijos y geometría.
- `GET /api/data/territory/SV-ADM1-SS` → departamento de San Salvador.
- `GET /api/data/observations?territory_id=...` → filtra por la columna
  `territory_id` de la observación, que puede ser nula si el dato no tiene
  asignación territorial verificada.

## 7. Diferencias entre sistemas

El diseño separa explícitamente:

- **administrativo**: país, departamento, municipio, distrito;
- **hidrográfico**: cuenca, subcuenca, microcuenca;
- **agrícola**: unidad de análisis, parcela.

Un municipio no es una cuenca y una cuenca no es un departamento. Cada nivel
declara su padre y su fuente. Las agregaciones futuras deberán declarar qué
sistema usan; el catálogo no asume equivalencias.

## 8. Limitaciones

- Los 272 municipios históricos no equivalen a los 44 vigentes. Cualquier serie
  temporal que cruce 2023 debe resolverse con la tabla oficial, que aún no está.
- No hay límites de cuencas ni de áreas protegidas verificados; existen fuentes
  potenciales (HydroSHEDS, Protected Planet) pero su licencia o acceso no está
  resuelto y figuran como `DISCOVERED`/`RESTRICTED`.
- No hay parcelas catastrales: no se inventan polígonos parcelarios ni se
  atribuye precisión parcelaria a datos de 250 m.
- El nombre normalizado sirve para búsqueda y detección de duplicados, no como
  clave primaria.
