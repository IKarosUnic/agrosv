# Fase 7 — métodos científicos

## Principios

1. Observación, derivación satelital, estimación modelada, pronóstico, registro
   de campo y alerta son clases distintas y no se convierten entre sí.
2. Una ausencia de dato se publica como `null` + motivo; no se imputa.
3. Todo umbral numérico exige fuente. Sin fuente, el cálculo no se ejecuta.
4. Los métodos son deterministas y locales; no requieren LLM ni nube.

## Índices espectrales

Fórmulas normalizadas con recorte a [−1, 1], nodata → NaN y denominador nulo →
NaN. Referencias: Rouse 1974 (NDVI), Huete 1997 (EVI), Huete 1988 (SAVI),
Qi 1994 (MSAVI2), McFeeters 1996 (NDWI), Gao 1996 (NDMI), Key & Benson 2006
(NBR), Barnes 2000 (NDRE).

## Series temporales

- línea base por ventana de día del año en años distintos;
- anomalía robusta `(x − mediana)/MAD`, con MAD×1,4826;
- mínimo 3 años y 6 observaciones;
- MAD = 0 → anomalía no interpretable;
- huecos informados, nunca interpolados;
- tendencia OLS descriptiva.

## Sanidad

- estados enumerados, no puntuaciones universales;
- sensibilidad por etapa genérica y declarada;
- estrés de vegetación exige ≥ 2 indicadores;
- calor sobre umbral explícito; LST no se convierte en temperatura de dosel;
- anomalías con métodos transparentes; modelos opacos rechazados.

## Agua

- P/ET0 como cociente climático, no SPI;
- Ks FAO-56 a partir de TAW, RAW y Dr aportados;
- sequía hidrológica no evaluada sin aforos;
- NDMI sin umbral local no se usa para inferir estrés.

## Fitosanidad

- catálogo bibliográfico con ámbito de presencia;
- idoneidad = proporción ponderada de ventanas cumplidas;
- ventanas con fuente; sin ventana → GAP;
- riesgo = idoneidad × exposición × etapa;
- el motor de enfermedades nunca emite diagnóstico.

## Riesgo

- `riesgo = peligro × exposición × vulnerabilidad`;
- escala operativa AGROSV (0,10/0,25/0,50/0,75), no oficial;
- sequía por categorías separadas;
- exposición a inundación con rangos operativos y `prediction: false`;
- susceptibilidad de suelo sin tasas de erosión;
- pérdida potencial, daño observado y pérdida modelada en campos distintos.

## Sequía estandarizada

Índice **empírico**: acumulación hacia atrás, agrupación por mes calendario,
probabilidad de Gringorten y transformación normal. No es el SPI gamma oficial.
Se exigen 30 años.

## Alertas

- huella determinista y supresión de duplicados;
- ciclo de vida con transiciones válidas;
- VERIFIED exige verificador fuerte o dos débiles distintos;
- prioridad con pesos declarados y protección del evento verificado grave;
- pronóstico separado de la observación.

## Lo que las pruebas no prueban

Las pruebas verifican aritmética, contratos y lógica. **No** validan la
exactitud de un índice satelital en El Salvador, ni la calibración de umbrales,
ni la incidencia de una plaga, ni la precisión de un pronóstico. Esa validación
requiere datos independientes que el repositorio no contiene.
