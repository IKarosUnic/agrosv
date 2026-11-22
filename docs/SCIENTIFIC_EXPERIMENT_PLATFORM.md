# MODULE M — Scientific Experiment Platform

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Plataforma para diseñar, ejecutar y **reproducir** experimentos con los motores
de AGROSV. Su prueba de fuego es simple: otra persona, con el mismo registro,
obtiene el mismo resultado.

---

## 1. Un experimento, en AGROSV

```json
{
  "experiment_id": "exp-2026-001",
  "title": "Fechas de siembra de maíz en Zapotitán",
  "hypothesis": "Retrasar 15 días la siembra reduce el estrés en floración",
  "design": {
    "type": "factorial",
    "factors": {
      "sowing_date": ["2026-05-15", "2026-05-30", "2026-06-15"],
      "irrigation": ["secano", "riego_apoyo"]
    },
    "replicates": 3,
    "unit": "parcela_virtual"
  },
  "domain": {
    "type": "puntos",
    "geometries": ["…"],
    "soil_source": "soilgrids",
    "climate_source": "agera5"
  },
  "models": [{"name": "aquacrop", "version": "7.3", "params": {}}],
  "outputs": ["yield_t_ha", "et_actual_mm", "stress_days"],
  "created_by": "…",
  "created_at": "2026-11-21"
}
```

Unidades experimentales pueden ser parcelas reales (Module D) o virtuales
(celdas con suelo y clima asignados). Se distingue en `unit`.

---

## 2. Ciclo de vida

```
draft → designed → queued → running → completed | failed → archived
```

Cada transición se registra con fecha, actor y motivo. Un experimento
`completed` es inmutable; para cambiarlo se crea una versión nueva.

---

## 3. Registro de reproducibilidad

```sql
experiment(
  experiment_id TEXT PK, version INT, title, hypothesis,
  design JSONB, domain JSONB, outputs TEXT[],
  status TEXT, created_by, created_at
);

run(
  run_id TEXT PK, experiment_id FK, version INT,
  model_name TEXT, model_version TEXT,
  inputs_hash TEXT,          -- SHA-256 de todos los insumos
  params JSONB, code_version TEXT, container_digest TEXT NULL,
  started_at, finished_at, status TEXT, error TEXT
);

run_result(
  run_id FK, treatment JSONB, metric TEXT, value NUMERIC, unit TEXT,
  uncertainty JSONB
);
```

`inputs_hash` incluye: geometrías, versión de suelo, versión de clima, versión
del modelo y parámetros. Si cambia algo, el hash cambia.

---

## 4. Comparación y exportación

- Comparación de tratamientos con media, dispersión y tamaño de efecto.
- Comparación entre temporadas y entre sitios.
- Exportación: CSV de resultados, JSON del diseño, GeoJSON del dominio y un
  `manifest.json` con versiones y hashes.
- **Reproducir**: `POST /api/experiments/{id}/reproduce` vuelve a ejecutar con
  los mismos insumos y compara hashes; si difieren, falla con diagnóstico.

---

## 5. Interfaz

```
POST /api/experiments
GET  /api/experiments?status=&owner=
GET  /api/experiments/{id}
POST /api/experiments/{id}/run
GET  /api/experiments/{id}/results
POST /api/experiments/{id}/reproduce
GET  /api/experiments/{id}/export
```

---

## 6. Validación

| Prueba | Criterio |
|---|---|
| Diseño | factores y niveles declarados; réplicas ≥ 2 |
| Dominio | geometrías válidas y dentro del país |
| Insumos | todo insumo con `source_id` y versión |
| Reproducción | mismo hash ⇒ mismo resultado (tolerancia 1e-6) |
| Inmutabilidad | un experimento completado no se modifica |
| Exportación | el paquete reproduce el resultado sin acceso a la base |

---

## 7. Limitaciones

1. Reproducir requiere las mismas fuentes (AgERA5, SoilGrids), que pueden
   cambiar de versión: se archiva la versión usada, no la fuente completa.
2. Un experimento con parcelas virtuales no valida el modelo contra realidad.
3. El diseño estadístico no reemplaza un ensayo de campo.
4. La plataforma no ejecuta modelos externos no registrados.

---

## 8. Dependencias y prioridad

Depende de: Module C (simulación), clima, suelo, Module D (parcelas reales).
Habilita: investigación universitaria y validación científica.

**Prioridad:** media. Es barato una vez que existe el motor de simulación y es
la mejor vía para que AGROSV sea usado por universidades.
