# AlertVerificationEngine — verificación con evidencia

**Módulo:** `backend/agrosv/monitoring/alerts.py`
**Endpoint:** `POST /api/monitoring/alerts/{id}/verify`
**Versión:** 7.0.0

## Verificadores

**Fuertes:** `official_institution`, `field_inspection`, `independent_dataset`.
**Débiles:** `extension_report`, `community_report`, `photograph`.

## Eventos

`submit(alert_id, verifier_type, outcome, evidence, observed_on, confidence,
notes, geographic_reference)`:

- resultado ∈ `confirmed`, `not_confirmed`, `inconclusive`;
- exige evidencia no vacía y fecha ISO;
- `confidence` acotada a [0, 1];
- calcula `verification_id` determinista;
- marca `community_observation` cuando el verificador es comunitario.

Los eventos se guardan **aparte** de la alerta.

## Evaluación

`evaluate(alert_id)` recomienda:

- `VERIFIED` si hay un verificador fuerte confirmado con confianza ≥ 0,5, o dos
  tipos débiles distintos confirmados;
- `DISMISSED` si hay rechazos y ninguna confirmación;
- `NEEDS_VERIFICATION` en el resto.

Un reporte comunitario **no verifica por sí solo**: la respuesta lo declara con
`community_only`.

## Aplicación

`apply(alert_id)`:

1. evalúa;
2. si la transición directa no está permitida (p. ej. DETECTED → VERIFIED),
   pasa primero por NEEDS_VERIFICATION y registra el evento;
3. aplica el estado final con los eventos como respaldo.

La alerta original permanece inmutable en `original`.

## Limitaciones

1. No se valida la autenticidad de los documentos aportados.
2. La confianza del verificador es declarada por quien registra.
3. `accepted` en campo no equivale a `VERIFIED` científico.
4. No hay integración automática con sistemas institucionales.
