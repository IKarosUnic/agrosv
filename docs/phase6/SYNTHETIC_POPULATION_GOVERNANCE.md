# Gobernanza de población sintética

**Fase 6 · Regla transversal · Implementada en código y verificada por pruebas**

Código: `backend/agrosv/social/governance.py`
API: `GET /api/social/layers`, `/api/social/separation`

## Cinco capas que nunca se fusionan

| Capa | Contenido | Sintética |
|---|---|---|
| `SOURCE_PROFILE` | perfil de origen Nemotron o esquema compatible | sí (la fila Nemotron es sintética) |
| `SYNTHETIC_AGRICULTURAL_STATE` | cultivos, superficie, riego, capital, crédito | sí |
| `HOUSEHOLD_STATE` | composición, trabajo, presupuesto, ingresos por proporción | sí |
| `SIMULATION_HISTORY` | decisiones, aprendizaje, difusión, escenarios | sí |
| `OBSERVED_VALIDATION_DATA` | evidencia real independiente | no |

`make_record` **rechaza** crear `OBSERVED_VALIDATION_DATA`: una fuente real se
registra con su ficha, no se genera. También rechaza
`evidence_class = observed_statistic` en un registro sintético.

## Registro mínimo

```json
{
  "record_id": "SYN-…",
  "layer": "SYNTHETIC_AGRICULTURAL_STATE",
  "synthetic": true,
  "evidence_class": "synthetic",
  "engine_version": "6.0.0",
  "generation_method": "…",
  "created_at": "…",
  "scenario_id": "…",
  "agent_id": "AGSV-…",
  "parents": ["…"],
  "assumptions": ["…"],
  "validation_status": "not_validated",
  "payload": {}
}
```

## Verificación automática

`check_separation(records)`:

* exige capa válida;
* exige método y al menos un supuesto no vacío;
* rechaza campos agrícolas en `SOURCE_PROFILE` (`crop_id`, `area_ha`,
  `irrigated`, `capital_usd`, `credit_access`, `yield_t_ha`, precios,
  `household_income`);
* rechaza observado marcado como sintético.

Devuelve `valid`, `errors` y conteo por capa. Los escenarios lo ejecutan antes
de publicar.

## Prohibiciones

1. Presentar una persona generada como persona real.
2. Inferir distribuciones poblacionales de un número arbitrario de personas.
3. Mezclar estado agrícola dentro del perfil de origen.
4. Usar un LLM para reemplazar un cálculo agronómico.
5. Publicar un resultado sintético sin `synthetic: true` ni limitaciones.
6. Tratar una clase de aptitud o un índice de adopción como medición.

## Minimización

Los perfiles sintéticos omiten sexo, religión, identidad y dirección exacta. Los
hogares no propagan atributos sensibles. No se generan nombres propios.

## Representatividad

Ninguna población de Fase 6 es representativa. La representatividad exigiría
calibración contra el CAP 2025 o una encuesta representativa, y eso no está
disponible en el repositorio.
