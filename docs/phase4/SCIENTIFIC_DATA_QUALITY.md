# Motor de calidad científica

**Fase 4 — AGROSV** · Implementación: `backend/agrosv/data/quality.py` · Informes: `data/metadata/quality_reports/` · Pruebas: `tests/test_quality_confidence.py`

## 1. Qué es y qué no es

El motor ejecuta comprobaciones **reproducibles** sobre archivos y series y
produce un `QualityReport` con hallazgos, severidad y alcance. No emite un
«puntaje de calidad» único. Un `PASS` significa «no se encontraron errores con
las comprobaciones ejecutadas», no «el dato es científicamente correcto».

```
PASS ≠ verdad
PASS_WITH_WARNINGS ≠ aprobado sin reservas
FAIL ≠ dato inútil (puede ser un problema de metadatos)
```

El estado del catálogo (`VALIDATED`) exige un informe pasado, ≥3 comprobaciones y
un alcance declarado. La calidad y el estado son dimensiones distintas.

## 2. Familias de validación

### Espaciales

- coordenadas fuera de rango (latitud ∉ [−90, 90], longitud ∉ [−180, 180]);
- puntos fuera de la cobertura declarada (bounds de El Salvador);
- geometrías inválidas, vacías, autointersectadas;
- duplicados geométricos;
- resoluciones inconsistentes entre capas (`assert_same_grid`);
- CRS ausente o distinto del declarado.

### Temporales

- fechas inválidas;
- períodos faltantes;
- duplicados de fecha;
- frecuencia inconsistente con las etiquetas;
- centinelas tratados como dato;
- series vacías o demasiado cortas.

### Numéricas

- valores fuera del dominio de error grosero (pH 95, precipitación negativa);
- unidades incompatibles (`degC` para precipitación);
- series constantes sospechosas;
- errores de escala (p. ej. SoilGrids en unidades crudas ×10);
- datos faltantes frente a ceros (`check_missing_vs_zero`);
- distribuciones anómalas (asimetría extrema);
- suma textural distinta de 100 % (no se renormaliza en silencio).

Los dominios provienen de `units.py` y son **cotas de imposibilidad**, no rangos
climáticos normales. Un valor dentro del rango puede seguir siendo erróneo.

### Científicas

`compare_sources()` compara dos series cuando existe base para hacerlo. Su
resultado declara:

- `comparison_class: "comparison"` si una fuente es observacional;
- `comparison_class: "intercomparison"` si ambas son reanálisis/simulación;
- métricas: n emparejado, sesgo, MAE, RMSE, correlación, diferencias relativas;
- `evidence` (nivel V2/V3) **solo** en el primer caso;
- `evidence_use`: una intercomparación **no** incrementa el nivel de validación.

Caso real: NASA POWER vs Open-Meteo para temperatura máxima y mínima, n = 2.557
por variable. El resultado es `intercomparison`, con `evidence: null`. Se
documentan las diferencias; no se declara que una fuente «valida» a la otra.

## 3. Informes reales (última ejecución)

| Dataset | Estado | Comprobaciones | Hallazgos | Alcance |
|---|---|---|---|---|
| copdem30 | PASS | 3 | 2 informativos | capa nacional completa (DEM y derivados) |
| geoboundaries_adm1 | PASS | 8 | 0 | ADM1, 14 departamentos |
| chirps3 | PASS_WITH_WARNINGS | 12 | 2 | 1 día global recortado a SV |
| nasa_power_point | PASS_WITH_WARNINGS | 4 | 5 | punto 13,70 N, 89,20 O, 2019–2025 |
| open_meteo_point | PASS_WITH_WARNINGS | 5 y 7 | 6 y 8 | punto 13,67 N, 89,17 O, 2019–2025 |
| gbif_sv | PASS_WITH_WARNINGS | 4 | 6 | 300 ocurrencias |
| soilgrids_2 | PASS_WITH_WARNINGS | 10 | 2 | 6 propiedades 0–30 cm |
| worldbank_agri_share | PASS_WITH_WARNINGS | 3 | 2 | indicador nacional anual |
| osm_sv | PASS_WITH_WARNINGS | 4 | 4 | vialidad (extracto Geofabrik) |

Dos datasets (`open_meteo_point`) tienen dos informes vigentes porque se
evaluaron dos artefactos distintos (JSON de muestra y CSV normalizado). La API
los devuelve ordenados por `created_at` descendente.

En `data/metadata/quality_reports/` pueden coexistir informes de ejecuciones
anteriores. En la reconstrucción actual quedan dos `FAIL` históricos (GBIF y
SoilGrids) que **no** están en la base de consulta: la base contiene solo los
informes de la última ejecución. No se borraron del disco porque documentan una
revisión previa; el informe vigente es el más reciente por `created_at`.

## 4. Hallazgos concretos que importan

- **GBIF**: 300 ocurrencias; 1 registro queda fuera del *bounding box* terrestre
  (clave 6131109486, *Thunnus albacares*, lon −90,375171, lat 13,052772). No se
  elimina: se marca `outside_land_bbox` y el informe lo explica. El sesgo de
  muestreo de GBIF no se corrige por agregación.
- **CHIRPS**: el ráster declara `nodata=None` pero contiene −9999. El motor
  reporta el centinela como advertencia; el recorte no lo reescribe.
- **SoilGrids**: unidades crudas del proveedor (pH ×10, carbono en dg/kg) se
  convierten con factores declarados; el informe revisa suma textural y dominio.
- **NASA POWER**: 2.557 días por variable; el informe verifica huecos y
  duplicados. La serie es reanálisis, no estación.
- **OSM**: la precisión varía por elemento; no se le atribuye exactitud
  parcelaria ni se usa como límite administrativo.

## 5. Estructura de un informe

```json
{
  "report_id": "b77372c6936c09e8",
  "dataset_id": "nasa_power_point",
  "artifact": "data/samples/phase3/nasa_power_point/power_daily_13.70N_89.20W.json",
  "status": "PASS_WITH_WARNINGS",
  "checks_run": 4,
  "scope": "muestra de punto: 13,70 N, 89,20 W, 2019–2025",
  "findings": [
    {"code": "clase_de_evidencia", "severity": "info",
     "message": "NASA POWER es reanálisis, no una estación...",
     "detail": {"evidence_class": "reanalysis"}}
  ],
  "parameters": {"comparison": "intercomparación con Open-Meteo..."},
  "generated_at": "2026-11-22T04:19:48Z"
}
```

`QualityReport.save()` escribe el JSON y lo devuelve; la base guarda el mismo
contenido en `quality_reports`.

## 6. Severidad y estado

- `error` → `FAIL` (no puede sostener `VALIDATED`);
- solo advertencias → `PASS_WITH_WARNINGS`;
- sin hallazgos → `PASS`.

Un informe con `FAIL` no se usa como evidencia de validación: la puerta del
catálogo lo rechaza explícitamente.

## 7. Límites

- Las comprobaciones son **sintácticas y de plausibilidad**. No sustituyen
  validación contra mediciones de campo.
- No hay estaciones SNET/MARN ni datos del CENTA para comparar; por eso no se
  declara validación nacional de clima ni de suelos.
- Las pruebas con fixtures sintéticos verifican el motor, no la realidad. La
  documentación lo repite para que no se confunda cobertura de pruebas con
  evidencia científica.
- No se calcula incertidumbre por variable en los informes; eso corresponde al
  modelo de `confidence.py`, que en esta fase queda como plantilla declarativa.
- La comparación NASA/Open-Meteo usa dos productos que comparten parte de sus
  fuentes (ERA5/IFS y MERRA-2 no son independientes en todos los procesos): la
  intercomparación no es una validación independiente.
