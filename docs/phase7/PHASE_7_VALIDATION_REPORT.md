# Fase 7 — informe de validación

## Validación de software (realizada)

| Componente | Qué se comprobó | Resultado |
|---|---|---|
| NDVI | (0,5−0,1)/(0,5+0,1) = 0,6667 | coincide |
| SAVI | (0,4/1,1)·1,5 = 0,54545 | coincide |
| MSAVI2 | (2−√0,8)/2 = 0,55279 | coincide |
| Nodata | NaN, no cero | verificado |
| Máscara de nube | píxel excluido, valor conservado | verificado |
| Banda ausente / formas distintas | error declarado | verificado |
| Serie estacional | z robusto contra cálculo manual | coincide |
| Huecos | 45 días detectados, sin interpolación | verificado |
| Cambio | 9/9 píxeles, declive fuerte | verificado |
| Sensores distintos | rechazo sin armonización | verificado |
| FAO-56 | Ks = 1 en Dr ≤ RAW; Ks = 0 en Dr = TAW | coincide |
| Sequía estandarizada | rechazo con 10 años; z finito con 40 | verificado |
| Rachas secas | máximo 4 días | verificado |
| Riesgo | 0,8×0,5×0,5 = 0,2 | coincide |
| Suelo | sin R/K no hay índice; sin tasas de erosión | verificado |
| Pérdida | 1 − 3/5 = 0,4 modelado, daño observado nulo | coincide |
| Alertas | duplicado, transiciones, VERIFIED, expiración | verificado |
| Prioridad | evento verificado grave primero | verificado |
| Verificación | institución oficial → VERIFIED | verificado |
| Campo | foto obligatoria, duplicado, privacidad | verificado |
| API | contratos, errores 400/404, compatibilidad | verificado |

## Validación científica (no realizada)

No se ha validado:

1. la exactitud de ningún índice satelital contra mediciones de campo;
2. la calibración de umbrales térmicos, hídricos o de riesgo;
3. la presencia actual de una plaga o enfermedad en un municipio;
4. la precisión de un pronóstico;
5. la relación entre una anomalía y una pérdida de rendimiento;
6. la bondad de la línea base estacional con series reales;
7. la exactitud del DEM o de la correspondencia municipal para el análisis
   agrícola (el DEM se evalúa en la etapa de acceso de datos).

## Por qué no se realizó

No hay en el repositorio escenas satelitales, series de estaciones, muestras de
laboratorio, registros de campo ni datos de rendimiento con licencia y
procedencia verificadas. Los fixtures sintéticos prueban el software, no la
realidad agrícola salvadoreña.

## Conclusión

La fase es **software verificado** y **ciencia pendiente de validación
empírica**. Cualquier afirmación de exactitud requeriría un conjunto
independiente de observaciones y un protocolo de validación acordado.
