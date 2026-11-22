# AgriculturalRemoteSensingEngine — contexto y escala

**Módulo:** `backend/agrosv/monitoring/change.py`
**Versión:** 7.0.0

## Función

Conecta una observación con el territorio y el suelo de Fase 5 **si esos
motores pueden responder**, y declara qué escala sostiene la resolución real.

## Escala soportada

`scale_support(resolution_m, scale)` aplica requisitos explícitos:

| Escala | Resolución máxima exigida |
|---|---|
| national | 250 m |
| departmental | 100 m |
| municipal | 30 m |
| agricultural_zone | 20 m |
| farm | 5 m |
| parcel | 2 m |

Un píxel de 10 m (Sentinel-2) sostiene análisis municipal o de zona, **no**
parcelario. La respuesta incluye el motivo y la advertencia de píxel mixto.

## Contexto Fase 5

`link_context(lat, lon, provided=None)`:

- si se aporta `provided`, se usa tal cual;
- si no, consulta `TerritorialEngine.profile` y `SoilEngine.profile_at_depth`;
- cualquier fallo se registra en `availability` con tipo de excepción y motivo;
- los campos no disponibles quedan en `None`.

No se interpola ni se completa el contexto. El usuario puede aportar un perfil
precalculado para evitar dependencias en tiempo de consulta.

## Limitaciones

1. Los motores de Fase 5 pueden no estar disponibles si faltan artefactos; se
   declara, no se sustituye.
2. La escala administrativa disponible es la histórica de Fase 1 (ADM2 previo a
   2023); la correspondencia vigente está en `/api/onboarding`.
3. La resolución nominal no equivale a exactitud temática.
4. No se calcula un índice de aptitud ni de salud a partir del contexto.
