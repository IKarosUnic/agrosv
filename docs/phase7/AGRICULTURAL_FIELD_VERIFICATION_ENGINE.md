# AgriculturalFieldVerificationEngine — observaciones de campo

**Módulo:** `backend/agrosv/monitoring/field.py`
**Endpoints:** `POST/GET /api/monitoring/field-observations`,
`POST /api/monitoring/field-observations/{id}/review`
**Versión:** 7.0.0

## Tipos admitidos

Observación de cultivo, sospecha de plaga, síntomas de enfermedad, estrés
hídrico, daño por inundación, daño por calor, pérdida de cultivo y práctica de
manejo.

## Controles al enviar

- coordenada dentro de El Salvador;
- fecha ISO no futura;
- fotografía obligatoria para plaga, enfermedad y pérdida de cultivo; si falta,
  el estado es `needs_evidence`;
- advertencia si la coordenada tiene precisión de ~1 km;
- **duplicado** si el mismo tipo y cultivo están a ≤ 500 m y ≤ 7 días; se
  informa `duplicate_of`, no se borra;
- identificador `FLD-<sha256[:12]>`;
- historial `audit` desde el envío.

## Estados

`received`, `needs_evidence`, `in_review`, `accepted`, `rejected`. La revisión
acepta, rechaza o pide evidencia, y **siempre** deja
`verified_scientific_record: false`: aceptar una observación no la convierte en
registro científico verificado.

## Privacidad

- `publish_coordinates` por defecto `false`;
- la vista pública redondea a 2 decimales (~1 km) y declara la precisión;
- no se expone el identificador del contribuyente en la vista pública;
- no hay datos personales más allá del identificador aportado.

## Limitaciones

1. No se verifica la autenticidad de las fotografías.
2. La detección de duplicados es geométrica y temporal, no semántica.
3. El almacén es en memoria.
4. La revisión es un flujo de trabajo, no una validación científica.
