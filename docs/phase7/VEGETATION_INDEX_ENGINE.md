# VegetationIndexEngine — índices espectrales

**Módulo:** `backend/agrosv/monitoring/indices.py`
**Endpoints:** `GET /api/monitoring/indices`, `POST /api/monitoring/indices`,
`POST /api/monitoring/indices/raster`
**Versión:** 7.0.0

## Índices implementados

| Índice | Fórmula | Bandas | Res. nativa | Señal |
|---|---|---|---|---|
| NDVI | (NIR−R)/(NIR+R) | nir, red | 10 m | verdor/fenología |
| EVI | 2,5(NIR−R)/(NIR+6R−7,5B+1) | nir, red, blue | 10 m | biomasa densa |
| SAVI | ((NIR−R)/(NIR+R+L))·(1+L) | nir, red | 10 m | verdor con suelo |
| MSAVI2 | (2N+1−√((2N+1)²−8(N−R)))/2 | nir, red | 10 m | verdor con suelo |
| NDWI | (G−NIR)/(G+NIR) | green, nir | 10 m | agua superficial |
| NDMI | (NIR−SWIR1)/(NIR+SWIR1) | nir, swir1 | 20 m | agua de vegetación |
| NBR | (NIR−SWIR2)/(NIR+SWIR2) | nir, swir2 | 20 m | incendio/disturbio |
| NDRE | (NIR−RE)/(NIR+RE) | nir, red_edge | 20 m | proxy de clorofila |

SAVI usa `L = 0,5` por defecto (Huete 1988), configurable. MSAVI2 sigue
Qi et al. (1994). Cada ficha incluye referencia, rango [−1, 1] y la lista
`cannot_conclude`.

## Reglas de cálculo

1. **Nodata → NaN**, nunca cero (cero es un valor válido).
2. **Denominador nulo → NaN**, nunca infinito.
3. Recorte a [−1, 1]: fuera de ese rango la razón normalizada no describe el
   índice.
4. Máscara de nube booleana: el píxel se excluye del resultado y de
   `valid_pixels`; el valor original no se sobrescribe en la escena.
5. Las bandas deben compartir forma; si no, `MonitoringError`.
6. `savi_l` fuera de [0, 1] se rechaza.

## Salida

`IndexResult.stats()` devuelve nombre, fórmula, bandas, resolución, sensor,
píxeles válidos/totales, fracción válida, mínimo, media, máximo y
`nodata_is_zero: false`. No se devuelve el arreglo completo por la API.

## Interpretación

El motor distingue tipos de señal (verdor, agua, suelo, fuego) y **no** asigna
diagnósticos. `cannot_conclude` declara explícitamente:

- NDVI no identifica especie ni cultivo;
- ningún índice diagnostica plaga, enfermedad o deficiencia nutricional;
- NDWI no mide humedad del suelo ni estrés hídrico del cultivo;
- NDMI no mide potencial hídrico ni turgencia.

`water_fraction` aplica el umbral 0 de McFeeters como **convención** declarada,
no como validación local.

## Validación

Las pruebas comparan NDVI, SAVI y MSAVI2 contra el cálculo analítico, verifican
propagación de NaN, máscara de nube, error por banda ausente y error por formas
distintas (`tests/test_phase7_monitoring.py`).

## Limitaciones

Saturación en dosel denso, píxeles mixtos, sensibilidad atmosférica, resolución
efectiva de 20 m en SWIR y ausencia de calibración local. No se ha comparado
contra muestras de campo porque no existen en el repositorio.
