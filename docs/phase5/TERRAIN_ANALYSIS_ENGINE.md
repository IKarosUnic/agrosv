# Terrain Analysis — elevación, pendiente, aspecto y morfometría

**Fase 5 · versión 5.0.0 · estado: implementado**
Código: `backend/agrosv/engines/terrain.py` · API: `/api/engines/terrain`

## 1. Qué es y qué no es

El motor describe la **forma del terreno** en un punto y en una vecindad de ~150 m.
No describe uso del suelo, fertilidad, aptitud de cultivo ni riesgo de erosión
medido: una pendiente alta es una condición física, no un diagnóstico agronómico.

Dos advertencias que viajan en cada respuesta:

- **DSM ≠ DTM.** Copernicus GLO-30 es un modelo de superficie: incluye dosel y
  edificios. La elevación no es la del suelo desnudo y la pendiente bajo vegetación
  densa puede estar sobreestimada.
- **Resolución ≠ precisión.** 30 m es el espaciado de la rejilla. La exactitud
  vertical no se ha validado con puntos de control en este repositorio.

## 2. Capas de entrada

| Capa | CRS | Resolución | Rol |
|---|---|---|---|
| `dem30_wgs84.tif` | EPSG:4326 | 1 arcosegundo (~30 m) | elevación |
| `slope_deg.tif` | EPSG:32616 | 30 m | pendiente (calculada en Fase 1) |
| `aspect_deg.tif` | EPSG:32616 | 30 m | aspecto |
| `relief_class.tif` | EPSG:32616 | 30 m | clase de relieve |

El muestreo puntual usa vecino más cercano, respeta `nodata` y aplica la escala
declarada por el archivo. Un valor enmascarado, `nodata` o no finito devuelve `null`,
nunca cero.

## 3. Variables derivadas y metodología

| Variable | Unidad | Método |
|---|---|---|
| `elevation_m` | m | muestreo del DEM |
| `slope_deg` | ° | diferencias finitas centrales sobre rejilla métrica (Fase 1) |
| `slope_pct` | % | `tan(slope_deg) · 100` (no es una conversión lineal) |
| `aspect_deg` | ° | azimut de máxima pendiente, `atan2(−dz/dx, −dz/dy)`, 0 = N, 90 = E |
| `aspect_compass` | — | 8 rumbos (N, NE, E, SE, S, SO, O, NO) |
| `relief_class` | clase | umbrales de pendiente declarados |
| `tri_m` | m | Riley et al. (1999): `√Σ(z_ij − z0)²` en ventana 3×3 |
| `tpi_m` | m | `z0 − media de los 8 vecinos` en ventana 3×3 |
| `topographic_position` | clase | cresta / ladera / valle / plano local según TPI |

### 3.1 Clases de relieve

Definidas en `config.RELIEF_BREAKS` y publicadas con la respuesta:

| Código | Rango (°) | Etiqueta |
|---|---|---|
| 0 | 0–2 | plano |
| 1 | 2–5 | suave |
| 2 | 5–12 | ondulado |
| 3 | 12–25 | quebrado |
| 4 | 25–45 | escarpado |
| 5 | 45–91 | muy escarpado |

Los umbrales son una convención AGROSV declarada, no una norma universal. Otra
elección produce otras proporciones de clases.

### 3.2 TPI: convención declarada

| TPI | Clase |
|---|---|
| ≥ +2,0 m | cresta |
| ≤ −2,0 m | valle |
| \|TPI\| ≤ 0,5 m | plano local |
| resto | ladera |

El TPI depende del tamaño de ventana. Con una ventana de 3×3 (~90–150 m) describe
posición local, no posición en una cuenca.

### 3.3 Ventana de análisis

`radius_cells` ∈ [1, 10]. La ventana (2r+1)² se lee del ráster nativo sin
remuestreo, recortada a los bordes del DEM. Una ventana incompleta se rellena con
NaN: no produce métricas inventadas. El tamaño de celda para TRI se aproxima con
111,132 m/grado (N-S) y 111,320·cos(lat) m/grado (E-O); la pendiente oficial no usa
esa aproximación.

## 4. Ejemplo real

Punto `(-89.2, 13.7)`, radio 2 celdas:

```json
{
  "elevation_m": 676.82,
  "slope_deg": 2.67,
  "slope_pct": 4.66,
  "aspect_deg": 139.8,
  "aspect_compass": "SE",
  "relief_class": {"code": 1, "label": "suave", "min_deg": 2, "max_deg": 5},
  "tri_m": 3.6,
  "tpi_m": 0.73,
  "topographic_position": "ladera",
  "window": {"radius_cells": 2, "cells": [5, 5], "approx_cell_m": 30.9}
}
```

## 5. Incertidumbre

| Componente | Estado |
|---|---|
| Vertical | no cuantificada: sin puntos de control locales |
| Horizontal | no cuantificada |
| Modelo | DSM incluye dosel y edificios |
| Escala UTM | EPSG:32616 en todo el país; ~1,0015 en el extremo oeste (±0,15 % en pendiente) |
| Zonas planas | el aspecto es inestable y puede ser nulo |

No se publica un intervalo numérico de error porque no existe una referencia con la
que calcularlo.

## 6. Rendimiento

Medido con `scripts/09_phase5_benchmark.py` (5 repeticiones, sin caché):

| Operación | Mediana |
|---|---|
| `terrain_metrics` (una consulta) | 0,019 s |
| `territorial.profile` (incluye cuenca y agua superficial) | 0,143 s |

Cada consulta abre el ráster y lee una ventana 5×5; no se carga el DEM nacional.

## 7. Planificado, no implementado

- Perfil longitudinal de pendiente y curvatura (necesita ventanas mayores y
  justificación).
- Corrección de pendiente bajo dosel con un DTM cuando exista.
- Validación vertical con puntos de control GNSS o nivelación.
- Rugosidad a escala de cuenca (hoy TRI/TPI son locales por diseño).

## 8. Pruebas

`tests/test_engines_territorial.py`:

- conversión de pendiente a porcentaje;
- clases de relieve y rumbo del aspecto;
- TRI sintético con resultado analítico (`√6` para un plano de 1 m/celda);
- TPI sintético (`0,0` en el centro de un plano) y rechazo de ventanas incorrectas;
- invariantes sobre el DEM real (rangos, unidades, limitaciones declaradas).
