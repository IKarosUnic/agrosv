# CropAnomalyDetectionEngine — anomalías transparentes

**Módulo:** `backend/agrosv/monitoring/crop_health.py`
**Endpoint:** `POST /api/monitoring/crop-anomaly`
**Versión:** 7.0.0

## Métodos implementados

| Método | Estadístico | Requisito |
|---|---|---|
| `zscore` | (x − μ)/σ | línea base con σ > 0 |
| `robust_z` | (x − mediana)/MAD | línea base con MAD > 0 |
| `moving_average_residual` | residuo vs media móvil previa, estandarizado por σ de residuos | ventana ≥ 2 |
| `seasonal_anomaly` | z contra línea base estacional aportada | línea base declarada |

Cada resultado expone método, umbral, ventana, periodo de línea base, centro,
dispersión, índices marcados, puntuaciones, dirección, confianza, entradas y
limitaciones.

## Rechazo de modelos opacos

`isolation_forest` y métodos no listados se rechazan con un mensaje explícito:
no se entrena un modelo opaco con etiquetas arbitrarias ni se presenta su salida
como diagnóstico. La comparación contra una línea base simple queda pendiente
para cualquier método que se añada en el futuro.

## Multivariable

`multivariable(indicators, threshold)` estandariza cada variable con mediana/MAD
y toma la **mediana** de los z por fecha. La mediana reduce el peso de una señal
aislada. No es un clasificador.

## Limitaciones

1. Detecta desviación estadística, no causa.
2. Línea base corta → umbrales inestables.
3. La estacionalidad debe estar resuelta por la línea base.
4. n < 3 se rechaza; base con dispersión nula se rechaza.

## Validación

Pruebas: outlier detectado con `robust_z` y línea base declarada;
`isolation_forest` rechazado; dos variables con caída simultánea marcan el
último índice.
