# Scientific Validation Protocol

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** protocolo definido, **sin resultados de validación**.

Reglas para decidir cuándo un resultado de AGROSV puede llamarse validado. Sin
observaciones independientes no hay validación: hay una ejecución.

---

## 1. Principios

1. **Independencia**: los datos de validación no se usan para calibrar.
2. **Separación temporal**: entrenar/calibrar en un periodo, validar en otro.
3. **Separación espacial**: calibrar en unas zonas, validar en otras no vistas.
4. **Trazabilidad**: cada métrica se guarda con dataset, versión y fecha.
5. **Declaración**: un módulo sin validación se etiqueta `unvalidated`.
6. **Nada de circularidad**: no se valida un modelo con su propia salida.

---

## 2. Niveles de madurez

| Nivel | Significado | Requisito |
|---|---|---|
| V0 | implementado | corre y produce salida |
| V1 | verificado | pruebas unitarias e integración pasan |
| V2 | contrastado | comparado con una fuente independiente |
| V3 | validado | métricas aceptables en datos no vistos |
| V4 | operativo | V3 + monitorización y revalidación periódica |

Ningún módulo de Fase 2 está por encima de V1. **No se declara V2+ sin
resultados.**

---

## 3. Métricas por tipo de salida

### Continuas (rendimiento, temperatura, NDVI)

| Métrica | Fórmula | Umbral propuesto |
|---|---|---|
| Sesgo | media(pred − obs) | \|sesgo\| < 10 % de la media obs |
| MAE | media\|pred − obs\| | < 15 % |
| RMSE | √media(pred − obs)² | < 20 % |
| R² | 1 − SS_res/SS_tot | > 0,5 |
| KGE | 1 − √((r−1)² + (α−1)² + (β−1)²) | > 0,5 |

Los umbrales son **propuestas**, no estándares; se ajustan por variable con
justificación escrita.

### Categóricas (aptitud, clases de riesgo)

| Métrica | Uso |
|---|---|
| Matriz de confusión | todas las clases |
| Exactitud global | referencia, insuficiente sola |
| Kappa | acuerdo corregido por azar |
| F1 por clase | clases desbalanceadas |
| Área bajo ROC | binario |

### Alertas (sequía, plagas)

| Métrica | Definición |
|---|---|
| POD (probabilidad de detección) | aciertos / eventos observados |
| FAR (ratio de falsas alarmas) | falsas alarmas / alertas emitidas |
| CSI (índice de éxito crítico) | aciertos / (aciertos + fallos + falsas alarmas) |
| Lead time | días de antelación |

Objetivo mínimo propuesto para alertas: POD > 0,6 y FAR < 0,4. **No alcanzado
ni medido aún.**

---

## 4. Diseño de validación

```
1. Definir la variable y su unidad.
2. Fijar el conjunto de calibración (espacio + tiempo).
3. Reservar validación ciega (≥ 30 % de los datos o ≥ 3 temporadas).
4. Ejecutar sin tocar el conjunto ciego.
5. Calcular métricas una sola vez.
6. Registrar resultados y limitaciones.
7. Revalidar cuando cambie el modelo o la fuente.
```

**Tamaño mínimo:** ≥ 30 observaciones independientes para métricas continuas;
≥ 30 eventos para alertas. Menos que eso se reporta como «evidencia
insuficiente», no como resultado.

---

## 5. Fuentes de verdad disponibles

| Variable | Fuente independiente | Estado |
|---|---|---|
| Rendimiento | encuestas MAG, censo BCR | **PENDING** (microdatos no disponibles) |
| Precipitación | estaciones MARN/SNET | **UNAVAILABLE** |
| Temperatura | estaciones MARN/SNET | **UNAVAILABLE** |
| Cobertura del suelo | puntos de validación propios / fotointerpretación | **PENDING** |
| Plagas | reportes OIRSA/ISC, inspecciones | **DOCUMENTED** |
| Áreas protegidas | MARN/SINAP | **PENDING** |
| Caudal | aforos MARN | **UNAVAILABLE** |

**Consecuencia honesta:** sin estaciones ni microdatos, la validación de clima y
rendimiento es **cruzada entre productos** (CHIRPS vs IMERG vs ERA5), no contra
observación. Eso es contraste, no validación.

---

## 6. Registro de validación

```sql
validation_run(
  validation_id TEXT PK,
  module TEXT, variable TEXT, unit TEXT,
  model_version TEXT, dataset_version TEXT,
  split JSONB,                 -- espacio, tiempo, n
  metrics JSONB,               -- bias, mae, rmse, r2, kge, pod, far
  level TEXT,                  -- V1..V4
  passed BOOLEAN,
  limitations TEXT,
  executed_at TIMESTAMPTZ
);
```

Un módulo sin fila en `validation_run` aparece como `unvalidated` en la API.

---

## 7. Pruebas que sí se pueden ejecutar hoy

| Prueba | Estado |
|---|---|
| 80 pruebas de Fase 1 | **pasando** |
| Integridad de datos (CRS, nulos, cobertura) | ejecutable |
| Coherencia física (pendiente, ET, balance) | ejecutable |
| Contraste CHIRPS vs IMERG vs ERA5 | ejecutable con cuentas |
| Validación con estaciones | **bloqueada** |
| Validación de rendimiento con censos | **bloqueada** por microdatos |

---

## 8. Limitaciones

1. Sin observaciones independientes, V2+ es inalcanzable.
2. Los umbrales propuestos no están respaldados por una norma nacional.
3. La validación cruzada entre productos comparte errores sistemáticos.
4. Una validación hecha una vez no es permanente: las fuentes cambian.

---

## 9. Dependencias

Requiere: Data Provenance Engine, Dataset Versioning, Uncertainty Engine y
acceso a datos de validación. Es transversal a todos los módulos.
