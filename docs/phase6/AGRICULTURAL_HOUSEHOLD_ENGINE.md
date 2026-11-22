# AgriculturalHouseholdEngine

**Fase 6 · Subsistema B · Estado: implementado; hogar sintético con consistencia interna**

Código: `backend/agrosv/social/household.py`
API: `POST /api/social/household`

## Modelo

El hogar es una unidad productiva y de consumo. No reproduce estadísticas de
hogares ni ingresos observados.

| Variable | Cálculo |
|---|---|
| tipo | del perfil de origen o sorteo (`unipersonal`, `nuclear`, `monoparental`, `extendida`) |
| tamaño | rango por tipo: 1; 3–5; 2–4; 5–8 |
| adultos / niños | derivados del tipo y del tamaño |
| unidades de consumo | `adultos + 0,5 × niños` (convención declarada) |
| días de trabajo familiar | `adultos × 300 × (1 − 0,6 × ingreso_extrapredial)` |
| días contratados | `hired_labor × 250 × 0,8` |
| presupuesto operativo | `capital × fracción (0,3–0,7)` |
| ingreso por fuente | proporciones normalizadas: finca, fuera de finca, remesas, cooperativa |

No se publican ingresos ni gastos en dólares: no hay precios, salarios ni
consumo observados. El presupuesto operativo es una fracción del capital
sintético, no un ingreso.

## Opciones de adaptación

Se activan según dotaciones: trabajo extrapredial, apoyo cooperativo, ahorros
(capital ≥ 1.000), riego, diversificación.

## Consistencia

`consistency()` verifica:

* composición suma el tamaño;
* trabajo y presupuesto no negativos;
* proporciones de ingreso suman 1 (±0,01);
* hay al menos un adulto si hay niños.

Es consistencia **interna del registro**, no validación empírica.

## Minimización

Solo se conserva `household_type` y tamaño. No se propagan sexo, religión,
identidad ni dirección. La respuesta lista los atributos omitidos.

## Límites

El tamaño y la composición son sintéticos; la disponibilidad de trabajo es una
proporción, no una encuesta de uso del tiempo; el modelo no incluye remesas
reales, crédito, salud, educación ni consumo calórico.
