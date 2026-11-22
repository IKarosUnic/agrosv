# PlantDiseaseKnowledgeEngine — catálogo de enfermedades

**Módulo:** `backend/agrosv/monitoring/knowledge.py`, `pests.py`
**Endpoints:** `GET /api/monitoring/diseases`, `GET /api/monitoring/diseases/{id}`
**Versión:** 7.0.0

## Registros incluidos (4)

| id | Enfermedad | Agente | Tipo | Presencia |
|---|---|---|---|---|
| coffee_leaf_rust | roya del café | *Hemileia vastatrix* | fúngica | nacional confirmada |
| bean_common_bacterial_blight | añublo bacteriano común | *Xanthomonas axonopodis* pv. *phaseoli* | bacteriana | regional confirmada |
| bean_golden_yellow_mosaic | mosaico dorado | *Bean golden yellow mosaic virus* | viral | regional confirmada |
| banana_black_sigatoka | sigatoka negra | *Pseudocorynespora fijiensis* | fúngica | nacional confirmada |

## Campos

Nombre, agente causal con nombre científico y tipo, categoría, cultivos,
síntomas, condiciones favorecedoras, ventanas ambientales con fuente,
transmisión, comportamiento estacional, diagnóstico, prevención, manejo
integrado, fuentes, calidad de evidencia e incertidumbre.

## Distinciones

- fúngica / bacteriana / viral / nematodo / fisiológica / nutricional: la
  categoría es un campo explícito;
- síntomas parecidos no implican el mismo agente;
- el catálogo no diagnostica: solo documenta;
- presencia nacional/regional se declara con el mismo vocabulario que las
  plagas.

## Vacíos declarados

Dos de las cuatro enfermedades no tienen ventana ambiental cuantitativa. La
sigatoka negra y el añublo bacteriano se publican con `environmental_windows: []`
y el motor de riesgo devuelve `None` + GAP para idoneidad, en lugar de inventar
un rango.

## Limitaciones

1. No hay confirmación de cepas o razas locales.
2. La incidencia actual no está verificada.
3. El diagnóstico requiere laboratorio; la API nunca lo emite.
4. La lista no es exhaustiva ni implica ausencia de otras enfermedades.
