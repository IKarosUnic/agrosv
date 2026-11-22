# MODULE H — Agricultural Digital Twin

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Representación digital **sincronizada** de una parcela: geometría, suelo,
topografía, clima, cultivo, manejo, historial y observaciones. Un gemelo digital
no es un visor bonito con un polígono: requiere **modelo de estado**,
**sincronización** y **comparación entre estados**.

---

## 1. Definición operativa (criterio de admisión)

Un componente solo puede llamarse gemelo digital si cumple los cuatro:

1. **Estado**: existe una estructura de estado versionada por parcela y ciclo.
2. **Sincronización**: nuevas observaciones actualizan el estado con fecha y
   fuente, de forma idempotente.
3. **Modelo**: hay al menos un modelo que proyecta el estado (crecimiento,
   balance hídrico, economía) y produce un estado modelado.
4. **Comparación**: se puede contrastar observado vs modelado vs esperado y
   registrar la diferencia.

Si falta uno, es una ficha de parcela, no un gemelo.

---

## 2. Estado del gemelo

```json
{
  "parcel_id": "…",
  "cycle_id": "…",
  "as_of": "2026-07-15T12:00:00Z",
  "geometry": { "…": "GeoJSON" },
  "environment": {
    "soil": {"source": "soilgrids", "ph": 6.1, "clay_pct": 37.0},
    "terrain": {"elev_m": 720, "slope_deg": 11.2, "aspect_deg": 210},
    "climate": {"source": "agera5", "cum_precip_mm": 312, "cum_et0_mm": 280}
  },
  "crop": {
    "code": "maiz", "variety": "local", "stage": "floracion",
    "sowing_date": "2026-05-18", "gdd": 980
  },
  "management": {"irrigation": "secano", "n_kg_ha": 60},
  "observed": {
    "ndvi_last": 0.62, "ndvi_date": "2026-07-10",
    "yield_actual": null
  },
  "modelled": {
    "biomass_t_ha": 8.1, "yield_water_limited_t_ha": 2.4,
    "model": "aquacrop-7.3", "uncertainty": {"p10": 1.8, "p90": 3.1}
  },
  "expected": {"yield_t_ha": 2.9, "source": "promedio_departamental"},
  "deviations": [
    {"variable": "ndvi", "observed": 0.62, "modelled": 0.68, "delta": -0.06}
  ],
  "state_version": 14
}
```

---

## 3. Sincronización

| Evento | Fuente | Frecuencia | Efecto |
|---|---|---|---|
| Nuevo compuesto satelital | Module A | 5–16 días | actualiza `observed.ndvi` |
| Nuevo dato climático | Module clima | diario | acumula precipitación y ET₀ |
| Operación de campo | Module D | al registrarse | actualiza manejo e historial |
| Nueva simulación | Module C | a demanda | actualiza `modelled` |
| Precio actualizado | Module E | semanal/mensual | actualiza economía |
| Observación de campo | Module D/L | al registrarse | actualiza `observed` |

Reglas:

- Cada actualización incrementa `state_version` y guarda el evento.
- Reaplicar el mismo evento no cambia el estado (idempotencia por `event_id`).
- Un dato que llega tarde (p. ej. IMERG Final) se registra con su fecha real y
  no reescribe el histórico sin dejar rastro.

---

## 4. Comparación de estados

| Comparación | Uso | Salida |
|---|---|---|
| Observado vs modelado | detectar estrés no explicado | delta y bandera |
| Modelado vs esperado | detectar anomalía productiva | ratio |
| Escenario A vs B | fechas de siembra, riego, N | tabla comparativa |
| Temporada anterior | histórico de la parcela | serie |

Ninguna comparación se publica como «pérdida» sin observación de campo.

---

## 5. Interfaz

```
GET  /api/twin/{parcel_id}?cycle_id=
GET  /api/twin/{parcel_id}/history
GET  /api/twin/{parcel_id}/deviations
POST /api/twin/{parcel_id}/scenarios
GET  /api/twin/{parcel_id}/scenarios/{scenario_id}
```

El acceso exige ser propietario o tener permiso. La versión pública muestra
solo agregados por distrito.

---

## 6. Validación

| Prueba | Criterio |
|---|---|
| Idempotencia | mismo `event_id` no altera `state_version` dos veces |
| Orden temporal | eventos fuera de orden no retroceden el estado |
| Trazabilidad | cada campo tiene `source_id` y fecha |
| Coherencia | NDVI ∈ [−1,1]; ET₀ ≥ 0; biomasa ≥ 0 |
| Reproducibilidad | reconstruir el estado desde el log da el mismo resultado |
| Comparación | `delta` = observado − modelado, sin signos invertidos |

---

## 7. Limitaciones

1. Requiere datos de parcela (Module D): no existe sin escritura y auth.
2. La sincronización climática es a 0,1°, no a la parcela.
3. El estado «esperado» depende de un promedio departamental, no de la parcela.
4. Sin calibración local, el estado modelado es un escenario, no una verdad.
5. El gemelo no predice plagas por sí solo; consume Module B.

---

## 8. Dependencias y prioridad

Depende de: Module A, C, D, E y clima. Es el **integrador** de la fase.

**Prioridad:** baja en el corto plazo. Construirlo antes de tener clima, censos
y gestión de parcelas produce una maqueta. Se recomienda como **cierre** de
Fase 2, no como inicio.
