# AgriculturalCalendarEngine

**Fase 6 · Subsistema A · Estado: implementado; calendario derivado, no oficial**

Código: `backend/agrosv/agriculture/calendar.py`
Pruebas: clasificación, ventanas, riesgos por etapa, cultivos sin calendario
API: `GET /api/agriculture/calendar?crop_id=&planting_date=`

## Qué produce

* **Ventanas de siembra** por criterio climático.
* **Etapas** si se aporta fecha de siembra (fenología térmica).
* **Períodos de riesgo** por etapa: déficit, exceso, mes seco.
* **Clasificación explícita** de cada tipo de información.

## Criterios declarados

Ventana de siembra: mes con

```
P_mes ≥ 60 mm   y   0,5 ≤ P_mes / ET0_mes ≤ 2,0
```

Los umbrales son convenciones AGROSV. En el punto de reanálisis, maíz obtiene
ventanas en mayo, julio–agosto y noviembre; junio queda fuera por exceso
(P/ET0 > 2), consistente con la canícula, pero el motor no lo interpreta como
tal.

Riesgos por etapa:

| Riesgo | Regla |
|---|---|
| déficit hídrico | P_mes < ET0_mes |
| exceso de lluvia | P_mes > 2 × ET0_mes |
| mes seco | P_mes < 60 mm |
| calor | **no evaluado**: faltan límites absolutos por cultivo |

## Clasificación de la información

```json
"classification": {
  "historical_practice": null,
  "technical_recommendation": null,
  "model_estimate": "ventanas y riesgos calculados con climatología 2019–2025",
  "forecast_dependent": false,
  "forecast_available": false
}
```

No hay calendario histórico por municipio, recomendación CENTA/MAG
georreferenciada, épocas de fertilización, ventanas de riego ni umbrales de
monitoreo de plagas. Todo eso se declara en `unavailable`; no se rellena.

## Por qué no hay un calendario nacional

El país tiene al menos tres regímenes de humedad y gradientes altitudinales que
cambian el ciclo. Un calendario único sería una generalización sin sustento.
El motor calcula por punto y declara que el clima es de reanálisis.

## Límites

No es un calendario agrícola oficial, no usa pronóstico, no incorpora variedad,
mercado, mano de obra ni preferencias del productor. Las ventanas no son
recomendaciones de siembra.
