# SocioAgriculturalIntegrationEngine

**Fase 6 · Subsistema C · Estado: implementado; integración sin LLM**

Código: `backend/agrosv/socio/integration.py`
API: `POST /api/socio/integrate`

## Función

Producir un perfil que reúna, **en bloques separados**:

* `scientific`: aptitud, calendario y balance hídrico;
* `human`: persona y hogar sintéticos, si se aporta un agente;
* `links`: qué salida científica alimenta qué decisión;
* `component_classes`: clase de evidencia de cada bloque.

## Reglas

1. La aptitud, el calendario y el agua provienen exclusivamente de los motores
   científicos.
2. Un componente sintético no puede reemplazar una clase de aptitud ni un
   balance.
3. `llm_used` es siempre `false`; no hay generación de texto.
4. Si faltan AWC, profundidad radicular o Kc, el agua se declara
   `not_evaluated` con las entradas requeridas. No se completa con supuestos.
5. El perfil humano se publica como `synthetic: true` y no valida nada.

## Estructura de respuesta

```json
{
  "scientific": {
    "suitability": {"result": {"class": "S3", "...": "..."}},
    "calendar": {"result": {"planting_windows": []}},
    "water_balance": {"result": {"totals": {}}}
  },
  "human": {"persona": {}, "household": {}, "synthetic": true},
  "links": {"suitability_to_decision": "clase y factores limitantes"},
  "llm_used": false,
  "agronomic_outputs_from_engines": true
}
```

## Entradas

`lon`, `lat`, `crop_id`, `system`, variedad, fecha de siembra, AWC,
profundidad radicular, depleción inicial, Kc o `allow_reference_kc`, agente
opcional y semilla.

## Por qué no se usa un LLM

Un LLM podría producir una explicación plausible pero no reproducible ni
auditable. La fase exige que una decisión respete restricciones científicas;
por eso la ruta es determinista y cada número tiene motor, fuente y limitación.

## Límites

El perfil no valida la aptitud ni el balance. La presencia de un hogar sintético
no mejora la calidad agronómica. El clima es de un punto de reanálisis y el
suelo es una predicción 0–30 cm.
