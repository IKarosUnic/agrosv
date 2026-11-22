# CropPhenologyEngine

**Fase 6 · Subsistema A · Estado: implementado; sin fotoperíodo ni validación**

Código: `backend/agrosv/agriculture/phenology.py`
Pruebas: etapas, aritmética de GDD, series incompletas, parámetros inválidos
API: `GET /api/agriculture/phenology?crop_id=&planting_date=`

## Método

Tiempo térmico por el método de la media diaria:

```
GDD_día = max(0, (Tmax + Tmin)/2 − Tbase)
```

`Tbase` proviene de la variedad o del catálogo (maíz, frijol, arroz, sorgo y
tomate: 10 °C, valor de literatura). Si el cultivo no tiene `Tbase` ni el
llamador la aporta, el motor **no estima**: lanza `PhenologyError`.

El objetivo a madurez puede ser:

1. `variety.gdd_to_maturity` explícito (estado `REF` o `SCENARIO`), o
2. derivado como `(Tmedia del período − Tbase) × ciclo medio`, con estado
   `MODEL_DERIVED` y rango a partir del ciclo mínimo/máximo del catálogo.

## Etapas

Convención AGROSV (no calibración varietal), como fracción del GDD total:

| Etapa | Fracción |
|---|---|
| emergencia | 0,08 |
| vegetativo | 0,45 |
| floración | 0,62 |
| llenado | 0,85 |
| madurez | 1,00 |

La fecha de cada etapa es el primer día cuya suma acumulada alcanza el umbral.
No se interpola la hora del cruce.

## Entradas y salidas

Entrada: cultivo, fecha de siembra, variedad opcional (`gdd_to_maturity`,
`tbase_c`, `stage_fractions`, `tmax_cap_c`) y, opcionalmente, una serie diaria
`{fecha: {tmin, tmax}}`. Sin serie explícita se usa la reanálisis Open-Meteo
(punto único, 2019–2025).

Salida: etapas con fecha, GDD acumulado, umbral y días después de siembra;
`complete`; parámetros usados con su estado; supuestos; envoltura §8 con
fuentes y limitaciones.

## Lo que no se implementó

* **Fotoperíodo.** Si la variedad se declara sensible, el resultado sigue
  siendo solo térmico y se agrega una limitación explícita.
* **Vernalización.**
* **Efecto del estrés hídrico sobre el desarrollo.** El balance hídrico existe,
  pero no acopla fenología.
* **Calibración por variedad salvadoreña.** No hay coeficientes en el
  repositorio.

## Ejemplo verificado

Maíz sembrado el 2024-05-15 en el punto de reanálisis: emergencia 2024-05-23,
floración 2024-07-26, madurez 2024-09-09 (117 días, 1.725 °C·día). Es un
resultado **de software** sobre clima de reanálisis; no una validación de ciclo
para una variedad local.

## Límites

Una fecha de madurez derivada no es un calendario de siembra, no incorpora
manejo, no representa el lote y no tiene intervalo de confianza. La serie
climática es de un punto y no se interpola espacialmente.
