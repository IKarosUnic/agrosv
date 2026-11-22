# Métodos científicos y supuestos — Fase 5

**AGROSV · versión de motores 5.0.0 · 2026-11-22**

Este documento reúne las fórmulas, parámetros y supuestos que los motores aplican.
Toda cifra publicada por un motor debe poder rastrearse hasta una entrada de esta
página y hasta la ficha de su dataset (`/api/engines/datasets/{id}`).

## 1. Clases de evidencia

| Clase | Significado | Ejemplos en AGROSV |
|---|---|---|
| `observed` | medido o registrado | límites administrativos, cauces OSM |
| `reanalysis` | modelo asimilado con observaciones | NASA POWER, Open-Meteo |
| `satellite_estimate` | estimación satelital | CHIRPS (una muestra de un día) |
| `modeled_prediction` | predicción espacial | SoilGrids, DEM |
| `derived` | aritmética determinista de otra clase | pendiente %, materia orgánica |
| `simulated` | modelo de proceso con supuestos | D8, Budyko |
| `forecast` | pronóstico | **no se sirve** |
| `climate_projection` | proyección climática | **no se sirve** |

Un valor nunca cambia de clase al pasar por un motor: la respuesta final conserva la
clase de cada fuente y etiqueta los derivados.

## 2. Fórmulas

### 2.1 Terreno

```
pendiente (%)      = tan(pendiente°) · 100
aspecto (°)        = atan2(−dz/dx, −dz/dy)        (0 = N, 90 = E)
TRI (Riley 1999)   = √Σ(z_ij − z0)²               (ventana 3×3)
TPI                = z0 − media(z_ij, i≠0,j≠0)    (ventana 3×3)
```

Pendiente y aspecto se calcularon en Fase 1 por diferencias finitas centrales sobre la
rejilla métrica EPSG:32616.

### 2.2 Suelo

```
clase textural   triángulo USDA-NRCS (arena, limo, arcilla)
materia orgánica MO (%) = SOC (g kg⁻¹) × 1,724 / 10
```

### 2.3 Hidrología

```
cuenca           priority-flood + D8 + recorrido inverso
área (km²)       celdas de la cuenca × (30 m)² / 10⁶
déficit (mm)     P − ET0
aridez           P / ET0
Budyko–Fu        E/P = 1 + φ − (1 + φ^ω)^(1/ω),  φ = ET0/P
escorrentía Q    P · (1 − E/P)
```

### 2.4 Clima

```
T media diaria   (Tmax + Tmin)/2
Rx1day           max(P_diaria)
Rx5day           max(Σ 5 días consecutivos)
R95p             Σ P de días con P > p95(días húmedos)
CDD              máxima racha con P < 1 mm
CWD              máxima racha con P ≥ 1 mm
SDII             Σ P / nº días húmedos
Walter–Lieth     mes húmedo si P_mes > 2 · T_mes
sequía           percentil empírico de P acumulada a 3 meses
distancia        haversine, R = 6.371,0088 km
```

### 2.5 Reglas de limitación e interacción

Se aplican como condicionales declarados; no hay suma, media ponderada ni puntuación.
El umbral y la consecuencia se publican con cada hallazgo.

## 3. Parámetros y estado de calibración

| Parámetro | Valor | Origen | ¿Calibrado? |
|---|---|---|---|
| Día húmedo | 1,0 mm | convención ETCCDI | no aplica |
| Percentiles de extremos | p95 / p5 del período | descriptivo | no |
| Umbral de cobertura temporal | 0,9 | control de calidad AGROSV | no |
| Categorías de sequía | p5/10/20/80/90/95 | convención AGROSV | no |
| TPI cresta / valle / plano | +2,0 / −2,0 / 0,5 m | convención AGROSV | no |
| Clases de relieve | 2/5/12/25/45° | convención AGROSV | no |
| Factor Van Bemmelen | 1,724 (rango 1,7–2,0) | literatura edafológica | no |
| Budyko ω | 2,0 (sensibilidad 1,5–3,0) | elección documentada | **no calibrado** |
| Ventana hidrológica | 1–30 km, resolución 30 m | recurso computacional | no aplica |
| Radio de búsqueda de cauce | 10 km | convención AGROSV | no aplica |
| Representatividad climática | ≤ 25 km | convención AGROSV | no aplica |

Ningún parámetro se calibró con datos de El Salvador. Se presentan como supuestos
declarados, no como valores óptimos.

## 4. Supuestos por motor

### Territorial

- ADM0 derivado por disolución de ADM1; el ADM0 del proveedor incluye aguas.
- ADM2 es la división pre-2023 y se marca `official: false`.
- Un punto fuera de todo polígono pero dentro del bbox está en aguas territoriales.
- El perfil por identificador usa un punto interior representativo, no un agregado.

### Terreno

- El DEM es un DSM: incluye dosel y edificios.
- EPSG:32616 para todo el país; error de escala ~0,15 % en el extremo oeste.
- TRI/TPI describen una ventana local (~150 m), no una cuenca.
- En zonas planas el aspecto es inestable.

### Suelo

- La media 0–30 cm representa la capa completa con pesos 5/30, 10/30, 15/30.
- No se interpola entre profundidades ni se reparte la media.
- Las limitaciones son reglas sobre una predicción, no un diagnóstico.

### Hidrología

- Estado estacionario anual: sin cambio de almacenamiento.
- Budyko incluye todo el excedente; no separa infiltración, recarga ni caudal base.
- P y ET0 provienen de productos distintos.
- Un cauce mapeado no implica caudal ni disponibilidad.
- La cuenca D8 es local y puede estar truncada.

### Clima

- La serie 2019–2025 es homogénea solo en lo declarado por el proveedor.
- Un punto de reanálisis no representa una cuenca ni un punto.
- No se interpola espacialmente.
- Los índices ETCCDI se calculan con la definición, pero sobre 7 años.

### Ambiental

- Las reglas son agronómicas generales, no calibradas localmente.
- La ausencia de un componente se declara; no se sustituye.
- No hay índice compuesto mientras no exista metodología validada.

## 5. Política de incertidumbre

1. Cada componente declara su clase de evidencia y su confianza cualitativa.
2. La incertidumbre se cuantifica **solo** cuando existe una referencia con la que
   calcularla. Hoy no existe para ningún componente.
3. Los rangos publicados (p. ej. Budyko ω 1,5–3,0) son **sensibilidad**, no intervalos
   de confianza.
4. Un componente sin cuantificar se publica como «no cuantificada» con su motivo.
5. No se agregan incertidumbres en un número único.

## 6. Reproducibilidad

- **Versión**: `5.0.0` en cada respuesta (`engine_version`).
- **Procedencia**: cada fuente declara identificador, institución, URL, versión, fechas,
  CRS, resolución, unidades, `nodata`, método, supuestos, incertidumbre, validación y
  licencia.
- **Huellas**: `artifact_digest` (sha256 corto del primer artefacto) y
  `provenance_id` del manifiesto de Fase 1/2.
- **Caché**: clave `sha256(motor + versión + parámetros + huella de artefactos)`;
  un cambio de fuente invalida el resultado anterior.
- **Historial**: `processing_history` enumera cada paso con herramienta, parámetros y
  sello temporal UTC.
- **Datos originales**: los motores solo leen; no sobrescriben `data/processed` ni
  `data/raw`. Los derivados van a `data/derived/cache/` y son descartables.
- **Sin red**: ninguna consulta de motor requiere red ni servicio de pago.

## 7. Qué haría falta para validar

| Afirmación | Evidencia necesaria |
|---|---|
| Elevación y pendiente exactas | puntos de control GNSS/nivelación |
| Suelo representativo | muestras de laboratorio georreferenciadas (CENTA) |
| Clima representativo | series diarias de estaciones SNET/MARN |
| Cuenca correcta | delimitación oficial o aforos |
| Escorrentía realista | aforos y curvas de gasto |
| Reglas agronómicas útiles | ensayos de rendimiento locales |

Mientras esas referencias no existan, los motores son **verificados por software**, no
**validados científicamente**. La distinción se mantiene en todos los documentos.

## 8. Referencias metodológicas

- Barnes, R., Lehman, C., Mulla, D. (2014). Priority-flood: an optimal depression-filling
  algorithm for digital elevation models.
- Budyko, M. I. (1974); Fu, B. P. (1981). Curvas de balance hídrico.
- O'Callaghan, J. F., Mark, D. M. (1984). The extraction of drainage networks from
  digital elevation data.
- Riley, S. J., DeGloria, S. D., Elliot, R. (1999). A terrain ruggedness index.
- USDA-NRCS. Soil texture triangle.
- Van Bemmelen (1890). Factor de conversión carbono orgánico → materia orgánica.
- Zhang, X. et al. (2011). Indices for monitoring changes in extremes (ETCCDI).
- Walter, H., Lieth, H. Climatodiagrama y meses húmedos.
