# WaterStressDetectionEngine — cinco categorías de sequía

**Módulo:** `backend/agrosv/monitoring/water_stress.py`
**Endpoint:** `POST /api/monitoring/water-stress`
**Versión:** 7.0.0

## Categorías separadas

1. **Meteorológica** — P/ET0 del periodo y clases operativas AGROSV:
   severo < 0,50; moderado 0,50–0,75; leve 0,75–1,00; sin déficit ≥ 1,00.
2. **Agrícola** — balance de agua del suelo FAO-56 (Ks).
3. **Déficit de humedad del suelo** — Dr/TAW con clases declaradas.
4. **Estrés hídrico del cultivo** — solo si existe Ks o un umbral de NDMI con
   fuente declarada.
5. **Hidrológica** — **no evaluada**: no hay caudales ni aforos integrados.

## FAO-56

```
Ks = 1                        si Dr ≤ RAW
Ks = (TAW − Dr)/(TAW − RAW)    si Dr > RAW, acotado a [0, 1]
```

`TAW = (θfc − θwp)·Zr` y `RAW = p·TAW` son entradas del usuario. Si no se
declara `p`, se usa `RAW = 0,5·TAW` y se anota el supuesto. Se valida
`0 ≤ RAW < TAW`.

## Demanda

Si se aporta ETc, se compara con precipitación + riego declarado. El riego solo
cuenta si el usuario lo declara: **proximidad a una fuente no es acceso legal,
físico ni económico al agua**.

## NDMI

Se informa su valor, pero no se usa para inferir estrés salvo que el llamador
aporte un umbral y su fuente. Sin umbral local verificado no se inventa uno.

## Limitaciones

1. No se calcula SPI/SPEI aquí (ver `DROUGHT_MONITORING_ENGINE.md`).
2. Un cociente P/ET0 bajo no prueba estrés del cultivo.
3. El balance no incluye capilaridad ni flujo lateral.
4. Ks < 1 indica déficit relativo, no pérdida de rendimiento.
5. NDMI no es humedad del suelo medida.

## Validación

Pruebas: clase severa con P/ET0 = 0,3; Ks = 1 en Dr ≤ RAW; Ks = 0 en Dr = TAW;
P baja sin estrés de cultivo declarado; Ks = 0,4 produce
`possible_water_stress`.
