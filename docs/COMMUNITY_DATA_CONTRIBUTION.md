# MODULE L — Community Data Contribution

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Permite que productores y técnicos reporten siembras, cosechas, plagas, sequías,
inundaciones y observaciones. **Un reporte comunitario no es un dato
confirmado**: entra como `reported` y solo asciende con verificación.

---

## 1. Qué se puede reportar

| Categoría | Campos mínimos | Evidencia adjunta |
|---|---|---|
| Siembra | cultivo, fecha, superficie, geometría o punto | foto opcional |
| Cosecha | cultivo, fecha, producción, unidad | foto/boleta |
| Plaga | cultivo, plaga, severidad, fecha | foto obligatoria |
| Enfermedad | cultivo, síntomas, fecha | foto obligatoria |
| Sequía | fecha, duración, afectación | foto opcional |
| Inundación | fecha, altura estimada, área | foto |
| Daño agrícola | tipo, superficie afectada | foto |
| Disponibilidad de agua | fuente, estado, fecha | foto opcional |
| Suelo | textura percibida, color, pH si midió | foto |
| Observación general | texto, fecha, punto | foto |

**No se aceptan**: datos personales de terceros, ubicaciones de viviendas,
documentos de identidad, ni contenido que permita identificar a una persona.

---

## 2. Flujo de validación

```
reporte → validación automática → triage humano → nivel de evidencia
```

| Etapa | Regla |
|---|---|
| Automática | geometría válida, fecha no futura, campos obligatorios, foto con tamaño permitido, sin datos personales |
| Duplicados | mismo usuario + misma categoría + < 50 m + < 24 h → se fusiona |
| Spam/abuso | rate limit por usuario; contenido repetido; cuentas nuevas |
| Triage | revisor humano confirma o descarta; registra motivo |
| Ascenso | `reported` → `confirmed` solo con inspección oficial o laboratorio (Module B) |

Niveles: `reported`, `suspected`, `confirmed` (ver
`CROP_HEALTH_AND_PEST_SURVEILLANCE.md` §1). La comunidad **nunca** produce
`confirmed` por sí sola.

---

## 3. Reputación y calidad

```sql
contributor(
  contributor_id UUID PK,
  role TEXT,                    -- 'productor'|'tecnico'|'investigador'|'publico'
  reputation NUMERIC DEFAULT 0, -- derivada, no autodeclarada
  reports_total INT, reports_confirmed INT,
  created_at, status TEXT
);

report(
  report_id UUID PK, contributor_id FK,
  category TEXT, geometry, observed_at,
  payload JSONB, photo_paths TEXT[],
  level TEXT,                   -- reported|suspected|confirmed
  status TEXT,                  -- pending|accepted|rejected|merged
  reviewed_by TEXT, reviewed_at, rejection_reason TEXT,
  consent_version TEXT, provenance_id TEXT
);
```

Reputación: proporción de reportes aceptados, ponderada por antigüedad. Se usa
para ordenar el triage, **no** para ascender evidencia automáticamente.

---

## 4. Consentimiento y protección

1. **Consentimiento explícito** al enviar: qué se publica (agregado), qué se
   comparte con terceros y por cuánto tiempo. Se guarda la versión.
2. **Identidad**: se separa del contenido; la vista pública no muestra nombre ni
   contacto.
3. **Ubicación**: se publica a nivel de distrito; el punto exacto solo lo ven el
   autor y los revisores.
4. **Fotos**: se eliminan metadatos EXIF antes de publicar.
5. **Borrado**: el autor puede retirar su reporte; el agregado ya publicado se
   mantiene y se documenta la baja.
6. **Exportación**: el autor puede descargar todo lo que aportó.

---

## 5. Interfaz

```
POST /api/community/reports              (autenticado)
GET  /api/community/reports?bbox=&category=&level=
GET  /api/community/reports/{id}
POST /api/community/reports/{id}/review  (revisor)
GET  /api/community/export?from=&to=     (solo datos autorizados)
```

---

## 6. Validación

| Prueba | Criterio |
|---|---|
| Campos | 100 % de reportes con categoría, fecha y geometría |
| Fecha | no futura; no anterior a 2000 |
| Geometría | válida y dentro de El Salvador |
| Duplicados | tasa de duplicados < 5 % tras la fusión |
| Abuso | rate limit efectivo en pruebas de carga |
| Privacidad | ninguna respuesta pública contiene nombre, contacto ni punto exacto |
| Ascenso | ninguna prueba permite `reported → confirmed` sin revisor |

---

## 7. Limitaciones

1. Sesgo de participación: reportan quienes tienen acceso y tiempo.
2. Un reporte no es una muestra probabilística.
3. La verificación humana es costosa y no escala sola.
4. Sin módulo de autenticación, no hay contribución (Fase 2 no lo implementa).
5. La foto no sustituye un diagnóstico de laboratorio.

---

## 8. Dependencias y prioridad

Depende de: Module D (parcelas), autenticación, Module B (evidencia).
Habilita: validación de Module A/C y datos de campo para Module M.

**Prioridad:** baja-media. Requiere autenticación y moderación; se implementa
después de la gestión de parcelas.
