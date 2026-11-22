# MODULE F — Agroclimatic Early Warning

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Sistema de alertas agroclimáticas y territoriales. Cada alerta es un objeto con
fuente, validez, resolución, área, confianza, limitaciones y estado. No hay
alertas «sin fecha» ni avisos sin fuente.

---

## 1. Fuentes por tipo de alerta

| Alerta | Fuente primaria | Resolución | Estado |
|---|---|---|---|
| Sequía meteorológica | CHIRPS v3 + SPI | 0,05° | **VERIFIED** |
| Déficit hídrico agrícola | AgERA5 (precip − ET₀) | 0,1° | **RESTRICTED** (cuenta CDS) |
| Lluvias intensas | GPM IMERG (0,1°, 30 min) | 0,1° | **RESTRICTED** (Earthdata) |
| Inundación | MARN/SNET (mapas PDF); IMERG como proxy | variable | **DOCUMENTED** |
| Estrés térmico | AgERA5 / ERA5 | 0,1° / 0,25° | **RESTRICTED** |
| Riesgo de erosión | DEM + precipitación + cobertura | 30 m | **DISEÑADO** |
| Riesgo fitosanitario | Module B | según modelo | **DISEÑADO** |
| Eventos extremos | NOAA CPC (0,5°), ERA5 | 0,5° / 0,25° | **VERIFIED** (CPC) |

**Google Weather**: solo pronóstico puntual en vivo; sus términos prohíben
almacenar o crear productos derivados. No alimenta alertas.

---

## 2. Esquema de alerta

```sql
alert(
  alert_id UUID PK,
  alert_type TEXT,            -- sequia|deficit_hidrico|lluvia_intensa|inundacion|
                              -- estres_termico|erosion|fitosanitario|extremo
  severity TEXT,              -- informativa|amarilla|naranja|roja
  source_id TEXT,
  issued_at TIMESTAMPTZ,
  valid_from TIMESTAMPTZ, valid_until TIMESTAMPTZ,
  native_resolution TEXT,
  area_km2 NUMERIC,
  geographies TEXT[],         -- dept | municipio | cuenca
  confidence TEXT,            -- alta|media|baja + justificación
  limitations TEXT,
  status TEXT,                -- vigente|expirada|retirada|actualizada
  inputs JSONB,               -- índices y umbrales usados
  message TEXT,
  provenance_id TEXT
);
```

Reglas:

1. `valid_until` obligatorio y `> issued_at`.
2. `status` cambia con el tiempo; una alerta expirada no se borra.
3. `confidence` nunca es «alta» si la fuente es un proxy (p. ej. IMERG para
   inundación).
4. Una alerta nueva sobre el mismo fenómeno **actualiza** (`status='actualizada'`)
   a la anterior; no la duplica.

---

## 3. Umbrales propuestos (a validar)

| Alerta | Umbral | Fuente del umbral |
|---|---|---|
| Sequía | SPI-3 < −1,0 (moderada); < −1,5 (severa) | McKee et al. (1993) |
| Déficit hídrico | precip − ET₀ acumulado 30 d < −50 mm | propuesto, a calibrar |
| Lluvia intensa | > 50 mm/24 h; > 100 mm/72 h | propuesto |
| Estrés térmico | Tmax > 35 °C en etapa reproductiva | literatura maíz/frijol |
| Erosión | pendiente > 15° + lluvia > 50 mm + suelo desnudo | propuesto |
| Fitosanitario | Module B class ≥ alto | modelo |

Los umbrales marcados «propuesto» **no** son estándar nacional: se publican como
configurables y su calibración es una tarea pendiente.

---

## 4. Notificación

| Nivel | Destino | Mecanismo |
|---|---|---|
| Departamento | tablero público, API | `GET /api/alerts?level=department` |
| Municipio/distrito | tablero + suscripción | requiere autenticación |
| Cuenca | tablero de cuencas | cruce con Module J |
| Parcela | propietario | requiere consentimiento y contacto |

No se envía SMS ni correo en Fase 2 sin proveedor definido. El diseño deja el
`notification_channel` como campo, no como promesa.

---

## 5. Interfaz

```
GET  /api/alerts?type=&level=&code=&status=
GET  /api/alerts/{alert_id}
GET  /api/alerts/subscriptions          (autenticado)
POST /api/alerts/subscriptions
```

Cada alerta devuelve `source_id`, `native_resolution`, `confidence`,
`limitations` y `status`; sin ellos no se sirve.

---

## 6. Validación

| Prueba | Criterio |
|---|---|
| Metadatos | 100 % de alertas con fuente, validez y confianza |
| Coherencia | `valid_until > issued_at`; severidad en el conjunto permitido |
| Temporal | no hay dos alertas vigentes idénticas para el mismo ámbito |
| Contraste | sequías severas coinciden con reportes MARN/SNET cuando existan |
| Falsos positivos | tasa medida sobre eventos pasados (backtest 2015–2024) |
| Latencia | IMERG Early (≈4 h) vs Final (≈3,5 meses): se declara la usada |

**Validación bloqueada:** sin estaciones de superficie no se puede medir la
tasa de acierto local; se usa contraste entre productos y reportes.

---

## 7. Limitaciones

1. La resolución de la alerta es la de su fuente (0,05°–0,5°), no la de la parcela.
2. Una alerta de sequía no equivale a pérdida de cosecha.
3. Los mapas de inundación del MARN son PDF, no capas operativas.
4. Un proxy satelital (IMERG) no sustituye un modelo hidráulico.
5. No hay alerta oficial salvadoreña de la que AGROSV sea canal.

---

## 8. Dependencias y prioridad

Depende de: Module clima (Fase 1.5), Module A (satélite), Module B
(fitosanitario), Module J (cuencas). Habilita: notificaciones y Module H.

**Prioridad:** alta para sequía y déficit hídrico (CHIRPS ya verificado);
media para inundación (limitada por datos del MARN).
