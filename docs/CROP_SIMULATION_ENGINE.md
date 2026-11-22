# MODULE C — Crop Simulation Engine

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Motor determinista de simulación de cultivos. Empieza por **maíz y frijol**.
No es un recomendador de cultivos ni un chatbot: ejecuta modelos agronómicos con
parámetros declarados y devuelve resultados con incertidumbre.

---

## 1. Modelos evaluados (acceso y licencia verificados)

| Modelo | Versión | Licencia real | Registro | ¿Maíz / frijol? | Veredicto |
|---|---|---|---|---|---|
| **FAO AquaCrop** | 7.3 | © FAO, «All rights reserved»; uso **no comercial** previa solicitud | No | Sí: *Maize* y *Dry beans* en la base de datos (Anexo I) | **Adoptar** para balance hídrico y rendimiento potencial |
| **DSSAT** | 4.8.6 | Código CSM **BSD-3-Clause**; binarios gratuitos con registro | Sí (email + nº de serie) | CERES-Maize, CROPGRO-Drybean | **Adoptar** para fenología y fertilización |
| **APSIM** | Next Gen (build continuo) | General Use Licence: **no comercial**, 3 años renovables; mejoras deben devolverse | Sí | Maíz; frijol vía marco Legume | **Solo evaluación**; licencia incompatible con servicio |
| **SWAT+** | 62.0.1 | **LGPL-2.1** | No | No es modelo de cultivo (cuenca) | Usar en Module J |

**Corrección respecto a Fase 0:** el registro anterior atribuía a AquaCrop
licencia BSD-3-Clause. El archivo `LICENSE` del repositorio oficial dice «All
rights reserved» con autorización no comercial previa solicitud. **Se corrige
el registro**; cualquier uso comercial requiere permiso escrito de FAO.

**Consecuencia de licencias:** AGROSV es un proyecto abierto no comercial, por
lo que AquaCrop y DSSAT son utilizables. Si el proyecto se comercializa, AquaCrop
y APSIM quedan fuera y solo DSSAT (BSD-3) y SWAT+ (LGPL) siguen disponibles.

---

## 2. Capacidades

| # | Capacidad | Modelo | Salida |
|---|---|---|---|
| 1 | Crecimiento y desarrollo | AquaCrop / DSSAT | biomasa, cobertura |
| 2 | Etapas fenológicas | DSSAT (CERES/CROPGRO) | fechas por etapa |
| 3 | Necesidades hídricas | AquaCrop | ETc, déficit, riego |
| 4 | Estrés térmico | ambos | días de estrés, impacto |
| 5 | Fechas alternativas de siembra | ambos | barrido de fechas |
| 6 | Fertilización y manejo | DSSAT | respuesta a N |
| 7 | Comparación de variedades | DSSAT (cultivares) | rendimiento relativo |
| 8 | Rendimiento potencial vs escenarios | ambos | potencial, limitado por agua, limitado por N |
| 9 | Análisis de sensibilidad | envoltorio | tornado / OAT |
| 10 | Contraste con cosechas observadas | validación | error, sesgo |

**Terminología obligatoria:**

- *Rendimiento potencial*: sin limitación de agua ni nutrientes.
- *Rendimiento limitado por agua*: solo déficit hídrico.
- *Rendimiento esperado*: **no se calcula**. Solo se reporta si existe
  observación de campo.

---

## 3. Contrato de simulación

```json
{
  "simulation_id": "sim-2026-0001",
  "crop": "maiz",
  "variety": "local-dx-01",
  "model": {"id": "aquacrop", "version": "7.3", "parameters_id": "fao-maize-v73"},
  "site": {"geometry": {...}, "soil_source": "soilgrids|centa", "climate_source": "agera5"},
  "period": {"sowing": "2026-05-15", "harvest": "2026-09-30"},
  "management": {"irrigation": "rainfed", "fertilizer_n_kg_ha": 0},
  "outputs": ["biomass", "yield_water_limited", "et", "stress_days"]
}
```

Respuesta:

```json
{
  "simulation_id": "sim-2026-0001",
  "yield_water_limited_t_ha": 2.4,
  "uncertainty": {"method": "ensemble", "p10": 1.8, "p90": 3.1},
  "limitations": ["parámetros no calibrados localmente", "clima 0.1°……"],
  "provenance_id": "sim-2026-0001@…"
}
```

Endpoints previstos:

```
POST /api/sim/crop/run
GET  /api/sim/crop/{simulation_id}
GET  /api/sim/crop/sowing-window?crop=&geometry=&year=
GET  /api/sim/crop/variants?crop=
```

---

## 4. Requisitos de datos

| Entrada | Fuente | Estado | Nota |
|---|---|---|---|
| Clima diario (T, precip, ET₀, radiación) | AgERA5 0,1° | **RESTRICTED** (cuenta CDS) | obligatorio |
| Suelo (textura, MO, profundidad) | SoilGrids / CENTA | predicción / **PENDING** | dos escenarios separados |
| Parámetros de cultivo | AquaCrop/DSSAT | **VERIFIED** (incluidos) | no calibrados para SV |
| Variedades locales | CENTA/MAG | **UNAVAILABLE** | bloquea comparación de variedades |
| Fechas de siembra reales | CAP 2025 / campo | agregado | no por parcela |
| Rendimiento observado | MAG/CAP | departamental | solo contraste agregado |

**Sin parámetros locales calibrados no se publica un rendimiento absoluto.**
Se publica un rango condicionado a los parámetros del modelo, etiquetado como
«simulación no calibrada».

---

## 5. Validación

| Prueba | Criterio |
|---|---|
| Conservación | biomasa final ≤ radiación interceptada × eficiencia máxima |
| Fenología | etapas en orden; duración dentro de rango del cultivo |
| Balance hídrico | ET + drenaje + escorrentía ≤ precipitación + riego + Δalmacenamiento (±5 %) |
| Sensibilidad | duplicar N no duplica rendimiento; sin agua, el rendimiento cae |
| Contraste | error medio vs rendimiento departamental MAG < 30 % (o se explica) |
| Reproducibilidad | mismo JSON de entrada → mismos resultados (tolerancia 1e-6) |

Si el contraste falla, se publica el error y no se «ajusta» el modelo para
coincidir.

---

## 6. Incertidumbre

- **Estructural**: dos modelos distintos dan resultados distintos; se reporta el
  rango del ensemble, no un valor único.
- **Paramétrica**: variedad y suelo; se propaga con Monte Carlo (100–1.000
  corridas).
- **Climática**: AgERA5 a 0,1° no representa el microclima de parcela.
- **De escala**: simular en el centroide de una celda de 0,1° no describe una
  ladera.

---

## 7. Limitaciones

1. No es una predicción de cosecha; es un experimento numérico.
2. No sustituye ensayos de campo.
3. Requiere calibración local antes de cualquier uso operativo.
4. Un rendimiento potencial **no** es un rendimiento esperado.
5. No modela plagas (eso es Module B) ni economía (Module E).

---

## 8. Dependencias y prioridad

Depende de: clima diario (Fase 1.5), suelo (Fase 1), catálogo de cultivos
(Module E). Habilita: Module F (alertas), Module H (gemelo digital), Module M
(experimentos).

**Prioridad:** alta para maíz y frijol, pero **después** de clima y censos. La
primera entrega debe ser una simulación reproducible de un solo sitio con
parámetros declarados y su incertidumbre, no un servicio nacional.
