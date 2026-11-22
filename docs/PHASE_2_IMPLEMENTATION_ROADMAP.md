# Phase 2 Implementation Roadmap

**Versión:** 2.0 · **Fecha:** 2026-11-22 · **Estado:** ejecución **iniciada**; infraestructura transversal, núcleo hidrológico y API `/api/v1` implementados y probados (ver `PHASE_2_IMPLEMENTATION_REPORT.md`).

Plan de ejecución de Fase 2 en 7 etapas. No implementa todos los módulos: define
qué se construye, en qué orden y con qué puerta de aceptación.

---

## 1. Principio de ejecución

> Cada etapa entrega algo que se puede ejecutar y verificar, o no se cierra.

Una etapa cerrada con solo documentos **no cuenta** como avance de software.
Los entregables se marcan `doc` (documento) o `code` (software verificable).

---

## 2. Etapas

### ETAPA 1 — Auditoría (cerrada)

| Entregable | Tipo | Estado |
|---|---|---|
| Inventario de módulos, endpoints y pruebas | doc | **hecho** |
| Confirmación de 80 pruebas y 13 endpoints | code | **verificado** |
| Lista de documentos existentes y faltantes | doc | **hecho** |

**Puerta:** nada se rompe; no se reescribe lo que funciona.

---

### ETAPA 2 — Diseño (cerrada con esta entrega)

| Entregable | Tipo | Estado |
|---|---|---|
| 13 documentos de módulo (A–M) | doc | **hecho** |
| Grafo de dependencias y priorización | doc | **hecho** |
| Infraestructura transversal (provenance, QC, versionado, incertidumbre, validación, reproducibilidad, orquestador) | doc | **hecho** |
| Estimaciones computacionales | doc | **hecho** |

**Puerta:** cada módulo tiene propósito, interfaz, método, validación,
incertidumbre, limitaciones, dependencias y «qué no hace».

---

### ETAPA 3 — Registro de datos

| Entregable | Tipo | Estado |
|---|---|---|
| Registro maestro de fuentes con estado | doc | **hecho** (ampliado) |
| Corrección de licencias erróneas (AquaCrop) | doc | **hecho** |
| Sondas de accesibilidad por fuente | code | **parcial** (20 sondas Fase 1.5) |

**Puerta:** ninguna fuente entra sin URL, institución, licencia y estado.

**Bloqueos conocidos:** MARN/SNET sin API; CENTA MDS sin descarga; microdatos
de censos no públicos; áreas protegidas sin shapefile.

---

### ETAPA 4 — Priorización

| Prioridad | Contenido | Justificación |
|---|---|---|
| P1 | Clima (CHIRPS + normales), censos, relieve | datos verificados, sin auth, coste bajo |
| P2 | Satélite (A), Economía (E), Simulación maíz (C) | valor alto, datos disponibles |
| P3 | Fitosanitario (B), Alertas (F), Hidrología (J) | requieren calibración |
| P4 | Parcelas (D), Comunidad (L), Gemelo (H), Urbano (G), Biodiversidad (K), Clima futuro (I), Experimentos (M) | auth, datos oficiales o licencias |

**Puerta:** cada módulo tiene prioridad escrita y motivo; no hay «todo es
prioritario».

---

### ETAPA 5 — Implementación selectiva

Alcance recomendado para el próximo ciclo de código, con el estado real de este:

| # | Entregable | Módulo | Prueba de aceptación |
|---|---|---|---|
| 1 | `Provenance Engine` + versionado por hash | Transversal | **hecho** — `science/registry.py` |
| 2 | Serie CHIRPS por celda y SPI-3 | Clima/F | pendiente |
| 3 | Aritmética de índices espectrales y anomalías | A | **hecho** — `science/indices.py`; adquisición pendiente |
| 4 | Detección de cambios entre 2 fechas | A | **hecho** — `indices.change_mask` exige umbral |
| 5 | Presupuesto de maíz con precios MAG fechados | E | pendiente (PDF sin licencia de reutilización) |
| 6 | Manifiestos de corrida verificables por hash | C/Transversal | **hecho** — `science/reproducibility.py`; modelo de cultivo pendiente |

**Puerta:** cada entregable con prueba automatizada y datos reales.

---

### ETAPA 6 — Validación

| Entregable | Tipo | Estado |
|---|---|---|
| Protocolo de validación | doc | **hecho** |
| Pruebas de integridad geoespacial | code | **hecho** — `science/qc.py` + 30 pruebas |
| Contraste CHIRPS vs IMERG vs ERA5 | code | **pendiente** (requiere cuentas) |
| Validación con estaciones | code | **bloqueada** |

**Puerta:** ningún módulo se etiqueta V2+ sin métricas registradas.

---

### ETAPA 7 — Documentación

| Entregable | Tipo | Estado |
|---|---|---|
| 18 documentos nuevos en `docs/` | doc | **hecho** |
| 7 documentos raíz actualizados | doc | **hecho** |
| Verificación automática de documentos | code | **hecho** — `scripts/05_verify_phase2_docs.py` |

**Puerta:** script que comprueba existencia, secciones obligatorias y enlaces.

---

## 3. Cronograma relativo (no fechas)

```
Ciclo 1: Provenance + clima (SPI) + NDVI nacional
Ciclo 2: cambios + economía + simulación maíz
Ciclo 3: fitosanitario + alertas + hidrología básica
Ciclo 4: auth + parcelas + comunidad
Ciclo 5: gemelo digital + experimentos
Ciclo 6: biodiversidad + clima futuro + urbano
```

Un ciclo es «lo que cabe en un periodo de trabajo con revisión», no un mes
calendario. No se prometen fechas.

---

## 4. Riesgos de ejecución

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Sin estaciones, no hay validación climática | alto | contraste entre productos; declarar `unvalidated` |
| Licencias no comerciales (AquaCrop, WorldClim, GAEZ) | alto | uso interno/resultados, no redistribución |
| Cuota CDSE agotada | medio | priorizar índices, no reflectancia completa |
| Auth no definido | alto para D/L/H | aislar; no bloquear P1–P3 |
| Microdatos censales cerrados | medio | usar agregados publicados |
| Complejidad de SWAT+ | medio | empezar con D8 + SCS-CN |

---

## 5. Qué NO se hará en Fase 2

- No se implementan los 13 módulos.
- No se despliega infraestructura en la nube de pago.
- No se entrena un modelo de IA generativa para calcular variables científicas.
- No se publican datos de fuentes que prohíben redistribución.
- No se declara ningún módulo «completo» sin prueba.

---

## 6. Criterio de cierre de Fase 2

La fase se considera arquitectónicamente completa cuando:

1. Los 13 módulos están definidos y con dependencias.
2. Las fuentes están registradas con estado y licencia.
3. Existe grafo y priorización.
4. Existe protocolo de validación e incertidumbre.
5. Existen estimaciones computacionales.
6. La verificación documental pasa.
7. La funcionalidad de Fase 1 sigue intacta (80 pruebas verdes).

**No** se considera completa por tener documentos: se considera completa por
tener arquitectura verificable y un primer conjunto de módulos ejecutables
identificado.

---

## 7. Ciclo de implementación ejecutado (2026-11-22)

| Entregable | Tipo | Evidencia |
|---|---|---|
| Contrato `ScientificResult` | code | `science/schemas.py`; rechaza salidas sin limitaciones, sin procedencia o con confianza alta sin cuantiles |
| Registro/versionado de datasets | code | `science/registry.py`; `dataset_version` derivado del hash |
| QC geoespacial | code | `science/qc.py`; detecta ráster vacío y geometría duplicada |
| Incertidumbre | code | `science/uncertainty.py`; Monte Carlo con semilla obligatoria |
| Validación V0–V4 | code | `science/validation.py`; nivel deducido, no elegido |
| Reproducibilidad | code | `science/reproducibility.py`; detecta archivo alterado |
| Orquestador | code | `science/orchestrator.py`; reintentos, reanudación, ciclos |
| Motor hidrológico D8 | code | `science/hydrology.py`; invariantes sobre DEM real |
| Índices espectrales | code | `science/indices.py`; valores analíticos |
| API `/api/v1` (9 rutas) | code | `backend/agrosv/api_v2.py` |
| Paquetes offline | code | ZIP por departamento con manifiesto y atribución |
| Informe de implementación | doc | `PHASE_2_IMPLEMENTATION_REPORT.md` |

Resultado: **161 pruebas verdes** (89 previas + 72 nuevas). Sigue sin existir
clima, adquisición satelital, simulación de cultivos, economía, fitosanidad,
alertas, autenticación ni parcelas.
