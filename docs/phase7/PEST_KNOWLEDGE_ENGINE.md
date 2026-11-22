# PestKnowledgeEngine — catálogo trazable de plagas

**Módulo:** `backend/agrosv/monitoring/knowledge.py`, `pests.py`
**Endpoints:** `GET /api/monitoring/pests`, `GET /api/monitoring/pests/{id}`,
`GET /api/monitoring/pests/audit`
**Versión:** 7.0.0

## Registros incluidos (5)

| id | Nombre científico | Cultivos | Presencia |
|---|---|---|---|
| fall_armyworm | *Spodoptera frugiperda* | maíz, sorgo, arroz, caña | nacional confirmada |
| coffee_berry_borer | *Hypothenemus hampei* | café | nacional confirmada |
| whitefly | *Bemisia tabaci* | frijol, tomate, chile, pepino, repollo | nacional confirmada |
| sugarcane_borer | *Diatraea saccharalis* | caña, maíz | regional confirmada |
| banana_weevil | *Cosmopolites sordidus* | banano, plátano | regional confirmada |

## Campos por registro

Identidad taxonómica, nombres comunes y locales, cultivos y hospederos, ámbito
de presencia con países y nota, ciclo de vida, condiciones favorecedoras,
ventanas ambientales cuantitativas (con fuente), daño, monitoreo, manejo
integrado, importancia económica, fuentes (institución, título, URL), calidad de
evidencia e incertidumbre.

## Ámbitos de presencia

- `national_confirmed`: presencia documentada en El Salvador;
- `regional_confirmed`: Centroamérica, sin registro salvadoreño verificado en
  este repositorio;
- `international_record`;
- `unconfirmed_national`.

**La presencia documentada en el país no implica presencia actual en un
municipio ni en una parcela.** Cada ficha lo repite.

## Fuentes

CABI Compendium (fichas de especie), FAO (gusano cogollero), OIRSA (programas
regionales), IICA/PROMECAFE (broca), CENTA (frijol). Las URL están en el
registro y en la respuesta de la API.

## Auditoría

`audit()` devuelve conteo por ámbito y por calidad de evidencia, y cuántos
registros **no** tienen ventana cuantitativa. Ese número es un vacío declarado,
no un fallo oculto.

## Validación de integridad

Al importar el módulo se comprueba: id consistente, nombre científico
binomial, fuentes presentes, ámbito válido, calidad válida y fuente en cada
ventana. Cualquier incumplimiento impide importar el catálogo.

## Limitaciones

1. Las ventanas térmicas son rangos de literatura marcados
   `literature_uncalibrated`; no son umbrales epidemiológicos locales.
2. No hay datos de incidencia municipal ni nacional actuales.
3. El catálogo cubre plagas documentadas, no todas las existentes.
4. No se afirma ausencia de una plaga no listada.
