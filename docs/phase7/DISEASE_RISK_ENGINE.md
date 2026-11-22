# DiseaseRiskEngine — condiciones favorables, no diagnóstico

**Módulo:** `backend/agrosv/monitoring/pests.py`
**Endpoint:** `POST /api/monitoring/disease-risk`
**Versión:** 7.0.0

## Método

Igual que el motor de plagas: ventanas ambientales con fuente (o reglas del
llamador), exposición del cultivo y factor de etapa. La idoneidad es la
proporción ponderada de ventanas cumplidas.

## Salida

`presence_evidence`, `environmental_suitability`, `suitability_detail`,
`crop_exposure`, `favorable_conditions` (texto documentado), `risk_index`,
`diagnosis: null`, `infection_model`, `gap`, método y limitaciones.

## Prohibiciones implementadas

1. **`diagnosis` siempre es `null`.** El motor no emite diagnósticos.
2. **`infection_model.implemented` es `false`** con el motivo: no hay modelo
   epidemiológico validado para el patosistema salvadoreño en el repositorio.
3. No se inventan umbrales de infección: sin ventana con fuente, la idoneidad
   es `None` + GAP.
4. Humedad relativa, lluvia o temperatura favorables **no** equivalen a
   infección.
5. Los síntomas requieren confirmación fitopatológica.

## Casos cubiertos

- roya del café: ventana térmica 20–25 °C de literatura (no calibrada);
- añublo bacteriano y mosaico dorado: sin ventana cuantitativa → GAP;
- sigatoka negra: sin ventana cuantitativa → GAP.

## Validación

Prueba: con temperatura dentro de la ventana de roya, la idoneidad es 1, pero
`diagnosis` es `None` y `infection_model.implemented` es `False`.
