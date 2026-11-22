# Matriz de reutilización y extensión

**Fase 6 · Nemotron y sv-people frente a la capa agrícola de AGROSV**

Leyenda: **R** reutilizado conceptualmente, **E** extendido por AGROSV,
**N** no usado, **P** planificado.

| Capacidad | Nemotron dataset | sv-people | Acción AGROSV | Estado |
|---|---|---|---|---|
| Esquema de persona | sí | adaptador | R: contrato `SOURCE_PROFILE` | E implementado |
| Perfil narrativo | sí | sí | N: texto generado no es variable | — |
| Edad, educación, ocupación | sí | sí | R: campos del perfil | E |
| Departamento/municipio | sí | OSM | R: departamento; municipio `null` si es sintético | E |
| Tipo de hogar | sí | sí | R: entrada del hogar sintético | E |
| Composición del hogar | no | sí | E: tamaño, adultos, niños | E |
| Trabajo del hogar | no | parcial | E: días disponibles por proporción | E |
| Ingreso y gasto | no | sí | E: proporciones y presupuesto, sin dólares observados | E |
| Estado agrícola | no | no | E: arquetipos, cultivos, superficie, riego, tenencia | E |
| Capital y crédito | no | parcial | E: rangos de escenario | E |
| Decisión | no | MAUT/GOAP/HTN | E: MAUT simple inspeccionable | E |
| Aprendizaje | no | sí | E: actualización acotada | E |
| Adopción tecnológica | no | no | E: índice de propensión | E |
| Resiliencia | no | parcial | E: exposición/capacidad/impacto | E |
| Multiagente | no | sí | E: red anillo + lazo, difusión | E |
| Geografía OSM | no | sí | N: no hay capa de infraestructura agrícola | P |
| Memoria episódica | no | sí | N: no requerida para decisiones de una ronda | P |
| Persistencia | no | SQLite | N: AGROSV usa registros JSON y artefactos | — |
| LLM | generativo | opcional | N: ninguna ruta lo usa | — |
| Calibración poblacional | anclaje censal general | no | P: requiere microdatos CAP | P |
| Interoperabilidad Saltbor | — | — | P: adaptador de formato | P |

## Lo que AGROSV decidió no duplicar

* Generación de personas: se usa el esquema, no se reimplementa un PGM.
* Cognición y memoria: fuera del alcance agrícola de Fase 6.
* Economía completa: AGROSV solo calcula márgenes con hojas aportadas.
* Geografía: Fase 5 ya tiene territorio; no se añade OSM.

## Lo que AGROSV añadió y no existía

1. Vínculo explícito entre aptitud científica y decisión.
2. Restricciones duras que ninguna preferencia puede anular.
3. Rechazo de economía sin precios y costos con fuente/fecha.
4. Verificación automática de separación de capas.
5. Escenarios A–G con supuestos declarados y resultados no predictivos.

## Riesgo de duplicación

El solapamiento con Saltbor es real en hogares, economía y multiagente. Se
aceptó para no acoplar el proyecto a un repositorio externo en esta fase. La
matriz deja explícito qué se reimplementó y por qué; una Fase 7 puede sustituir
esos módulos por un adaptador si la interoperabilidad se demuestra.
