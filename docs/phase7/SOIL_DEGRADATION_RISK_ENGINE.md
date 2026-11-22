# SoilDegradationRiskEngine — susceptibilidad, no tasas

**Módulo:** `backend/agrosv/monitoring/risks.py`
**Endpoint:** `POST /api/monitoring/soil-degradation`
**Versión:** 7.0.0

## Susceptibilidad

Componentes: pendiente (0–30°), baja cobertura (1 − cobertura) y pérdida de
cobertura si se aporta. Pesos 0,45 / 0,40 / 0,15. Clase con la escala operativa
AGROSV.

## Índice relativo de erosión

Si se aportan erosividad (R) y erodibilidad (K):

```
LS ≈ 0,065 + 4,56·sin θ + 65,41·sin² θ
C  = max(0,01, 1 − cobertura)
índice = R · K · LS · C
```

Se etiqueta como **adimensional** (`R·K·LS·C`), no como t/ha/año. `LS` es una
aproximación, no un factor calculado con el DEM local.

## Prohibición de tasas

`erosion_rate` es siempre `None`, con el motivo: no se declaran tasas sin
calibración y datos de pérdida de suelo. `rusle_inputs_complete` indica si el
índice relativo pudo calcularse.

## Salinidad y materia orgánica

Se informan si se aportan, pero `evaluated: false` mientras no exista un umbral
local con fuente declarada. No se clasifican con valores inventados.

## Limitaciones

1. Susceptibilidad modelada ≠ degradación observada.
2. La cobertura debe provenir de una fuente verificada.
3. No se calculan tasas de erosión.
4. La aproximación LS no sustituye un cálculo sobre el DEM.

## Validación

Pruebas: sin R/K, `erosion_rate` y `relative_erosion_index` son `None`; con R y
K el índice es positivo y su unidad declara “adimensional”.
