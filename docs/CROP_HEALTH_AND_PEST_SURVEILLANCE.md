# MODULE B — Crop Health and Pest Surveillance

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Sistema de vigilancia fitosanitaria que **separa cuatro niveles de evidencia** y
prohíbe el diagnóstico automático. Un índice satelital no es un diagnóstico.

---

## 1. Niveles de evidencia (obligatorios)

| Nivel | Definición | Quién lo produce | Cómo se publica |
|---|---|---|---|
| `confirmed` | Diagnóstico de laboratorio o inspección oficial | MAG/DGSV, laboratorio | Punto con fecha, plaga y fuente |
| `reported` | Reporte de campo o comunitario no verificado | Técnico, productor | Punto marcado «no verificado» |
| `modelled` | Riesgo calculado por un modelo | AGROSV | Raster/polígono de riesgo con modelo y umbral |
| `suspected` | Sospecha visual (foto, sintomatología) | Cualquiera | Punto «sospecha», nunca diagnóstico |

Ningún nivel inferior puede ascender sin evidencia del nivel superior.

---

## 2. Fuentes verificadas y sus límites

| Fuente | Qué aporta | Estado |
|---|---|---|
| MAG — Dirección General de Sanidad Vegetal (DGSV) | Competencia legal de vigilancia, laboratorio, denuncias, agrodrones | **DOCUMENTED** |
| MAG — Memorias de Labores | Agregados de visitas de vigilancia (p. ej. 827 / 1.058) | **VERIFIED** (PDF) |
| ISC — Boletines agroclimáticos del café | Roya y broca: condicionantes climáticas y recomendaciones | **VERIFIED** (PDF) |
| OIRSA — URIS | Boletines regionales de plagas (p. ej. *Megalurothrips usitatus*, 2025) | **VERIFIED** |
| OIRSA — manual SAT roya | 5 niveles de alerta (azul, verde, amarilla, naranja, roja) | **VERIFIED** (PDF) |
| IPPC — El Salvador | **0 reportes de plagas** presentados | **VERIFIED** (ausencia) |
| Geoportal OIRSA | Mapas de riesgo roya/broca/ojo de gallo | **UNAVAILABLE** al sondear |

**Hallazgo negativo relevante:** El Salvador no ha presentado *pest reports* al
IPPC, por lo que ese portal **no** sirve como fuente nacional. Los boletines
del ISC son la fuente pública más cercana a un seguimiento oficial de roya y
broca.

---

## 3. Catálogo de problemas priorizados

| Problema | Cultivo | Evidencia disponible | Modelo propuesto |
|---|---|---|---|
| Roya (*Hemileia vastatrix*) | Café | ISC, OIRSA SAT, modelo Weibull germinación/infección (Colombia) | Riesgo por temperatura y humedad foliar |
| Broca (*Hypothenemus hampei*) | Café | ISC, OIRSA, matriz demográfica (PLOS ONE 2021) | Riesgo por grados-día y fenología |
| Gusano cogollero (*Spodoptera frugiperda*) | Maíz, sorgo | Sin alerta oficial SV; fichas CABI/EPPO | Riesgo por temperatura y etapa fenológica |
| Mosca blanca (*Bemisia tabaci*) | Hortalizas | EPPO (presente en SV); artículos UES | Riesgo por clima; sin serie nacional |
| Trips (*Thrips palmi*, *M. usitatus*) | Melón, frijol | OIRSA (vigilancia), boletín 2025 | Riesgo por clima seco-cálido |
| Enfermedades fúngicas | Varios | Literatura regional | Riesgo por humedad y mojado foliar |

**Advertencia:** los parámetros de los modelos publicados son de Colombia,
México, Brasil o laboratorio. **Ninguno está calibrado para El Salvador.** Se
usan como riesgo relativo, nunca como probabilidad absoluta.

---

## 4. Modelo de datos

```sql
crop_pest_catalog(crop, pest, pathogen_type, affected_stage, source_id)

pest_observation(
  obs_id, geometry, crop, pest, evidence_level,   -- confirmed|reported|suspected
  observed_at, reporter_type, source_id, photo_url,
  verification_status, verified_by, verified_at
)

pest_risk(
  risk_id, geometry, crop, pest, model_id, model_version,
  valid_from, valid_to, risk_class,          -- bajo|medio|alto|muy alto
  confidence, inputs JSONB, provenance_id
)

pest_alert(
  alert_id, risk_id, level, issued_at, valid_until,
  area_km2, affected_geographies[], message, limitations
)
```

---

## 5. Interfaz prevista

```
GET  /api/health/catalog?crop=maiz
GET  /api/health/observations?bbox=&crop=&pest=&level=
POST /api/health/observations          (requiere autenticación y consentimiento)
GET  /api/health/risk?crop=cafe&pest=roya&date=
GET  /api/health/alerts?level=department&code=
```

Toda respuesta de riesgo incluye `model_id`, `model_version`, `confidence`,
`inputs` y la frase de limitación.

---

## 6. Reglas de alerta

1. Una alerta **modelada** no puede presentarse como brote confirmado.
2. Los umbrales se publican con su fuente (p. ej. niveles OIRSA para roya).
3. Una alerta caduca: `valid_until` obligatorio.
4. Sin datos de campo, la alerta se etiqueta «preliminar, sin verificación».
5. Nunca se recomienda un producto fitosanitario: se informa el riesgo y se
   remite a la autoridad competente (DGSV).

---

## 7. Validación

| Prueba | Criterio |
|---|---|
| Separación de niveles | ninguna observación `reported` marcada como `confirmed` |
| Catálogo | toda plaga tiene al menos una fuente con URL |
| Riesgo | clases ordenadas y umbrales monótonos |
| Caducidad | `valid_until > issued_at` |
| Reproducibilidad | mismo `inputs` + `model_version` → mismo `risk_class` |
| Falsos positivos | revisión manual de una muestra de alertas antes de publicar |

**Validación científica pendiente:** comparar riesgo modelado con
observaciones confirmadas. Sin acceso a datos de la DGSV, no es posible hoy.

---

## 8. Limitaciones

1. No hay serie nacional pública de incidencia por plaga.
2. Los índices satelitales no distinguen una enfermedad de una sequía.
3. Los modelos son transferidos; su calibración local es una tarea futura.
4. La ausencia de reporte no significa ausencia de plaga.
5. La alerta es apoyo a la decisión, no diagnóstico.

---

## 9. Dependencias y prioridad

Depende de: catálogo de cultivos (Module E), clima diario (Fase 1.5), teledetección
(Module A) para forzantes. Habilita alertas fitosanitarias en Module F.

**Prioridad:** media-alta para café (roya/broca tienen fuente y modelo), baja
para cultivos sin datos oficiales. Se implementa **después** del motor climático.
