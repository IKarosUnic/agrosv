# AgriculturalPersonaEngine

**Fase 6 · Subsistema B · Estado: implementado; perfiles sintéticos separados del estado agrícola**

Código: `backend/agrosv/social/persona.py`
API: `GET /api/social/personas/sample`, `POST /api/social/persona`

## Dos orígenes, nunca confundidos

| Origen | Fuente | Uso |
|---|---|---|
| `nemotron_sample` | fila real de la muestra (3 filas) | lectura sin alteración |
| `schema_compatible_synthetic` | AGROSV con el esquema Nemotron | poblaciones agrícolas |

El perfil sintético declara `from_nemotron_dataset: false`, no genera nombre ni
identidad y omite el sexo por minimización de atributos sensibles.

## Hallazgo que condiciona el diseño

Las 3 filas de la muestra tienen ocupaciones no agrícolas. Por eso
`compose()` **rechaza** adjuntar un estado agrícola a un perfil no agrícola:

```json
{
  "attachable": false,
  "reason": "el perfil de origen no declara ocupación agrícola; AGROSV no reasigna roles sin autorización explícita",
  "source_profile": {...},
  "synthetic_agricultural_state": {...}
}
```

Con `allow_role_extension=true` se permite, pero la tarjeta marca
`role_consistent_with_source: false` y `role_assigned_by_agrosv: true`.

## Composición

`compose(agent, source_profile=None)` devuelve:

* `persona.display_label`: etiqueta descriptiva, sin nombre propio;
* `persona.is_person: false`;
* `source_profile` y `agricultural_state` en claves distintas;
* `record` de capa `SIMULATION_HISTORY` con padres;
* advertencias de sinteticidad.

Nunca se fusiona el perfil con el estado: la separación es verificable con
`check_separation`.

## Ocupaciones sintéticas

Se asignan por sistema productivo («Cultivo de cereales y legumbres», «Cultivo
de café bajo sombra», «Producción agrícola urbana», etc.). Edad, educación y
tipo de hogar se sortean con semilla derivada del índice del agente.

## Verificación

`validate(records)` delega en `check_separation` y rechaza cualquier
`SOURCE_PROFILE` que contenga `crop_id`, `area_ha`, `capital_usd`,
`credit_access` o campos similares.

## Límites

No hay validación de que la distribución de edades, educación u ocupaciones
coincida con El Salvador. Un perfil sintético no es una persona y no debe
usarse para reidentificación por combinación de municipio, edad y ocupación.
