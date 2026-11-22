# Fase 7 — incertidumbre y limitaciones

## Ausencia de datos

1. **Ninguna escena satelital integrada.** Los adaptadores se probaron con un
   GeoTIFF sintético de 4×4 píxeles.
2. **Ninguna serie de estación SNET/MARN, aforo o punto GNSS integrada.**
3. **Ningún registro de incidencia de plagas o enfermedades.** El catálogo es
   bibliográfico.
4. **Ninguna observación de campo real.** El motor de campo almacena lo que se
   le envía, en memoria.
5. No hay datos de temperatura de dosel, humedad de suelo medida ni rendimiento
   observado asociados a las capas.

## Satélite

- resolución nominal ≠ precisión temática;
- píxeles mixtos y saturación de NDVI;
- nubes, sombras y aerosoles;
- SWIR a 20 m;
- diferencias de sensor no armonizadas;
- fecha de adquisición dependiente de etiquetas.

## Series

- línea base corta → anomalías inestables;
- ventana de 15 días puede mezclar etapas;
- la estacionalidad no se elimina en la tendencia lineal;
- los huecos no son deterioro, pero también ocultan información.

## Sanidad

- ventanas térmicas de literatura sin calibración salvadoreña;
- presencia nacional ≠ presencia municipal;
- idoneidad ambiental ≠ presencia;
- síntomas ≠ diagnóstico;
- sin modelo epidemiológico validado.

## Riesgo

- clases operativas no oficiales;
- factores multiplicados como independientes;
- pesos metodológicos, no calibrados;
- exposición a inundación sin modelo hidrológico;
- susceptibilidad de suelo sin tasas;
- pérdida potencial ≠ pérdida observada.

## Alertas

- umbral de creación 0,25 operativo;
- cola y almacén en memoria;
- verificación basada en evidencia declarada, sin validar autenticidad;
- prioridad no es probabilidad;
- un aviso por pronóstico no es una observación.

## Incertidumbre no cuantificada

No se han calculado intervalos de confianza para los índices ni para las
anomalías porque no hay una muestra independiente. Los motores declaran
`uncertainty` cualitativa o `None`; no se presenta una precisión inventada.

## Escala

La resolución de 10 m permite análisis municipal o de zona; **no** parcelario.
El motor de contexto lo declara y rechaza afirmar precisión que el dato no
sostiene.
