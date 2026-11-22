# DroughtMonitoringEngine — categorías de sequía

**Módulo:** `backend/agrosv/monitoring/risks.py`
**Endpoint:** `POST /api/monitoring/drought`
**Versión:** 7.0.0

## Cinco categorías separadas

| Categoría | Implementación |
|---|---|
| meteorológica | percentil de precipitación o P/ET0 del trimestre |
| agrícola | fracción de agua disponible agotada (si se aporta) |
| humedad del suelo | misma fracción, etiquetada aparte |
| hidrológica | **no evaluada**: sin caudales/aforos |
| vegetación | z robusto de NDVI, etiquetado como señal, no como tipo |

No se colapsan en un índice único.

## Índice estandarizado empírico

`standardized_precipitation_index(monthly_mm, scale=3, min_years=30)`:

1. exige ≥ 30 años (360 meses); si no, `InsufficientRecordError`;
2. acumula una ventana **hacia atrás** de `scale` meses;
3. agrupa por mes calendario;
4. asigna probabilidad empírica de Gringorten `(rank + 0,44)/(n + 0,12)`;
5. transforma a z normal (`statistics.NormalDist().inv_cdf`);
6. clasifica: extremadamente seco ≤ −1,645; muy seco ≤ −1,282; seco ≤ −0,842;
   húmedo ≥ 0,842; muy húmedo ≥ 1,282; extremadamente húmedo ≥ 1,645.

**No es el SPI gamma oficial.** Se documenta la diferencia y se exige registro
homogéneo y completo.

## Rachas secas

`consecutive_dry_days(precip, wet_threshold_mm=1.0)` devuelve días secos, racha
máxima y racha actual. No incorpora agua del suelo ni demanda.

## Limitaciones

1. Los percentiles dependen del periodo de referencia.
2. Los ceros y la estacionalidad marcada afectan la cola del índice empírico.
3. Sin registro de 30 años no se calcula un índice estandarizado.
4. La sequía agrícola requiere TAW y profundidad radicular verificadas.
5. La sequía hidrológica no se evalúa sin aforos.

## Validación

Pruebas: 10 años de registro se rechazan; 40 años producen z finito y método
empírico; racha seca máxima de 4 días en una serie con 7 días secos.
