# Plan de integración Nemotron ↔ AGROSV

**Fase 6 · Estado: capa de extensión propia implementada; sin acoplamiento a Saltbor**

## Principio

Nemotron es una base de contexto humano sintético. No sustituye censos,
encuestas, mediciones agronómicas ni modelos validados. AGROSV mantiene su
propio esquema y solo comparte el **contrato de perfil de origen**.

## Frontera de integración

```
Nemotron (dataset)                AGROSV
┌──────────────────┐      ┌──────────────────────────────┐
│ SOURCE_PROFILE   │─────▶│ AgriculturalPersonaEngine     │
│ (esquema, 25 col)│      │  + SYNTHETIC_AGRICULTURAL_STATE│
└──────────────────┘      │  + HOUSEHOLD_STATE            │
                          │  + SIMULATION_HISTORY         │
                          └──────────────┬───────────────┘
                                         │ eventos
                          ┌──────────────▼───────────────┐
                          │ Saltbor (Fase 7+, opcional)   │
                          │  adaptador, no fusión         │
                          └──────────────────────────────┘
```

## Contrato `SOURCE_PROFILE`

Campos mínimos: `uuid` (o `null` si es sintético), `age`, `education_level`,
`occupation`, `area`, `department`, `municipality`, `household_type`,
`origin` (`nemotron_sample` | `schema_compatible_synthetic`),
`not_a_real_person: true`.

Prohibido en esta capa: `crop_id`, `area_ha`, `irrigated`, `capital_usd`,
`credit_access`, `yield_t_ha`, precios o ingresos. La verificación
`check_separation` rechaza esos campos.

## Contrato de eventos

Cada registro sintético lleva:

```json
{
  "record_id": "SYN-<hash>",
  "layer": "SYNTHETIC_AGRICULTURAL_STATE",
  "synthetic": true,
  "generation_method": "...",
  "created_at": "...",
  "scenario_id": "...",
  "agent_id": "AGSV-...",
  "parents": ["..."],
  "assumptions": ["..."],
  "validation_status": "not_validated",
  "payload": {}
}
```

## Etapas

| Etapa | Estado Fase 6 | Descripción |
|---|---|---|
| E1 esquema | hecho | perfiles compatibles, sin narrativa como variable |
| E2 estado agrícola | hecho | arquetipos y dotaciones sintéticas |
| E3 hogar | hecho | composición, trabajo, presupuesto, ingresos por proporción |
| E4 decisión | hecho | MAUT con restricciones duras |
| E5 adopción y resiliencia | hecho | índices de escenario |
| E6 multiagente | hecho | difusión reproducible |
| E7 adaptador Saltbor | **no hecho** | requiere acuerdo de formato y pruebas conjuntas |
| E8 calibración empírica | **no hecho** | requiere microdatos del CAP o encuestas |

## Reglas de integración

1. No se comparte base de datos ni se importa el paquete de Saltbor.
2. No se modifica el repositorio externo.
3. Un perfil de origen nunca se sobrescribe con estado agrícola.
4. Un LLM no participa en cálculos agronómicos ni en la decisión.
5. Una población generada no se usa para inferir prevalencias reales.

## Requisitos para Fase 7

* Microdatos o tabulados municipales del CAP 2025 (acceso legal).
* Calibración de arquetipos contra superficie, tenencia y sistema productivo.
* Parámetros de cultivo locales para que un modelo externo sea defendible.
* Pruebas de interoperabilidad con Saltbor en un entorno aislado.
