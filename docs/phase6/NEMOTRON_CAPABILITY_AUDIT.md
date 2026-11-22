# Auditoría de capacidades Nemotron

**Fase 6 · Etapa 1 · Inspección de `nvidia/Nemotron-Personas-El-Salvador` y `IKarosUnic/sv-people`**

## Dataset Nemotron

| Dato | Valor verificado |
|---|---|
| Identificador | `nvidia/Nemotron-Personas-El-Salvador` |
| Licencia | CC BY 4.0 |
| Filas | 148.000 |
| Columnas | 25 |
| Revisión | `68f6a21c17973d6a34ac6354d50a31c1fbcec14f` |
| Cobertura | 14 departamentos, 44 municipios |
| Anclaje | CPV 2024 / EHPM 2024 |
| Ocupación agrícola | 12,13 % en división 01 (17.957 registros) |

Campos: `uuid`, `age`, `sex`, `education_level`, `occupation`, `area`,
`department`, `municipality`, `household_type`, `marital_status`,
`languages_spoken`, `cultural_background`, y personas narrativas
(`persona`, `professional_persona`, `family_persona`, `arts_persona`,
`culinary_persona`, `sports_persona`, `travel_persona`,
`hobbies_and_interests`, `skills_and_expertise`,
`career_goals_and_ambitions`, listas asociadas).

**No contiene**: tenencia de tierra, superficie cultivada, cultivos, ingreso,
crédito, acceso a agua, insumos, maquinaria, precios ni prácticas agrícolas.

## Hallazgo de la muestra local

`data/samples/phase3/nemotron_rows/nemotron_rows_sample.json` contiene 3 filas
reales. Las tres tienen ocupaciones no agrícolas (agencias de viajes, conservación
de carne, contabilidad). Extraer un «productor» de ellas sería una invención.

Consecuencia de diseño: AGROSV **no reasigna** la ocupación de una fila de
Nemotron. Para poblaciones agrícolas genera perfiles
`schema_compatible_synthetic` y declara `from_nemotron_dataset: false`.

## sv-people / Saltbor

Inspección del repositorio público (sin clonar):

| Capacidad | Existe | Relevancia para AGROSV |
|---|---|---|
| generación de personas | sí | alta; esquema compatible |
| rasgos cognitivos y psicológicos | sí | media; AGROSV evita generalizaciones |
| memoria y estados dinámicos | sí | baja en Fase 6 |
| relaciones individuales | sí | media para difusión |
| hogares | sí | alta; AGROSV implementa su propio modelo |
| economía | sí | media; AGROSV exige hojas de precios |
| interacción social | sí | alta para multiagente |
| geografía OSM | sí | no usada en Fase 6 |
| multiagente | sí | alta |
| reglas MAUT/GOAP/HTN | sí | AGROSV usa MAUT simple |
| contexto salvadoreño | sí | alta |
| determinismo sin LLM | sí | alta; misma decisión de AGROSV |
| adaptador Nemotron con fallback | sí | referencia conceptual |
| persistencia SQLite | sí | no adoptada |

Escala reportada: ~0,57 KB por agente, 561 pruebas, 27 commits, Python 3.12,
Apache-2.0.

## Brechas que AGROSV debe cubrir

1. Estado agrícola (sistema productivo, cultivos, superficie, tenencia, riego,
   insumos, capital, crédito, mercado).
2. Vínculo entre decisión y motores científicos (aptitud, agua, calendario).
3. Economía que **rechace** operar sin precios y costos con fuente y fecha.
4. Gobernanza de cinco capas con verificación automática.
5. Adaptador de simulación con calibración y validación explícitas.

## Riesgos identificados

* **Representatividad**: 148.000 personas sintéticas no son un censo de
  productores; la división 01 no equivale a productor agropecuario.
* **Sesgos del generador**: subrepresentación de identidades indígenas y
  afrodescendientes; roles de género heredados del texto narrativo.
* **Narrativa vs. dato**: `persona` es texto generado; no debe tratarse como
  variable medida.
* **Privacidad**: no hay personas reales, pero se debe evitar reidentificación
  por combinación de municipio, edad y ocupación.

## Conclusión

Nemotron aporta esquema y contexto; no aporta agricultura. Saltbor aporta un
precedente arquitectónico; no se integra. AGROSV construye la capa agrícola y
declara que toda persona es sintética.
