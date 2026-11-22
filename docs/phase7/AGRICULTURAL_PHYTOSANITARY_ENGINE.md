# AgriculturalPhytosanitaryEngine — evidencia con procedencia

**Módulo:** `backend/agrosv/monitoring/pests.py`
**Endpoints:** `GET/POST /api/monitoring/phytosanitary`
**Versión:** 7.0.0

## Tipos de registro

- `official_notice` — comunicado institucional;
- `scientific_publication`;
- `extension_report`;
- `community_report`;
- `algorithmic_risk_estimate`.

## Regla de oro

**Solo un `official_notice` puede marcarse `official: true`.** Intentar marcar
un reporte comunitario como oficial lanza `MonitoringError`. Un reporte
comunitario o una estimación algorítmica no es un comunicado oficial.

## Registro

`add(kind, statement, crop_id, geographic_scope, source, observed_on,
official, confidence)`:

- exige fuente (≥ 3 caracteres);
- valida fecha ISO;
- calcula `record_id = PHY-<sha256[:16]>` sobre el contenido;
- conserva `evidence_class = kind`, `registered_at`, `confidence` acotada;
- se guarda en memoria del proceso (no hay base de datos en esta fase).

## Consulta

- `list(kind, crop_id)` ordena por fecha descendente e informa cuántos son
  oficiales;
- `summary()` cuenta por tipo y oficiales;
- `threat_catalog(crop_id)` combina plagas y enfermedades del catálogo con los
  reportes registrados, sin inferir presencia.

## Limitaciones

1. El almacén es en memoria: no persiste entre reinicios.
2. No hay integración automática con OIRSA/IPPC/MAG; los registros se aportan
   manualmente con su fuente.
3. No se agregan reportes en un “nivel oficial”.
4. Un reporte verificado por una persona sigue siendo `field_observation` hasta
   que una fuente institucional lo confirme.
