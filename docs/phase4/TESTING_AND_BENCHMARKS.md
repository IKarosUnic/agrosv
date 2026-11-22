# Pruebas y rendimiento

**Fase 4 — AGROSV** · Suites: `tests/test_data_*.py`, `tests/test_geo_normalization.py`, `tests/test_raster_temporal.py`, `tests/test_quality_confidence.py`, `tests/test_lineage_storage.py`, `tests/test_phase4_performance.py`

## 1. Resultado

```
$ .venv/Scripts/python.exe -m pytest tests/ -q
270 passed, 1 warning in 21.74s
```

- 109 pruebas nuevas de Fase 4 (9 archivos).
- 161 pruebas de fases anteriores siguen pasando: no se rompió
  retrocompatibilidad.
- La advertencia es de una prueba que compara áreas geográficas y proyectadas a
  propósito; no es un fallo del código.

Las pruebas que dependen de artefactos reales usan `conftest.require()` y se
**saltan** si el catálogo, la base, el DEM o la muestra CHIRPS no están
construidos. Un salto no se reporta como aprobado.

## 2. Cobertura por área

| Archivo | Qué demuestra |
|---|---|
| `test_data_catalog.py` | 9 estados, transiciones ilegales, puertas de evidencia, `PATCH` de estado, auditoría, catálogo real con 71 transiciones |
| `test_data_ingest.py` | detección por contenido, extensión incoherente, deduplicación, hash esperado, archivo vacío, reanudación de lotes, host no autorizado, descarga idéntica omitida, metadatos ráster |
| `test_geo_normalization.py` | CRS original, área en grados rechazada, área 6933 realista, distancia métrica, geometrías inválidas, duplicados, fuera de cobertura, solapamiento, reparación con log y respaldo, elección UTM/6933 |
| `test_raster_temporal.py` | perfil por cabecera, nodata no declarado, rechazo de sobremuestreo, método obligatorio, recorte sin remuestreo, ventana, bloques, rejilla, muestreo, contenedores, huecos/duplicados/centinelas, mezcla de evidencia, año hidrológico, agregación incompleta |
| `test_quality_confidence.py` | dominios numéricos, unidades, constantes, sentinelas, ceros vs faltantes, textura, coordenadas, temporal, intercomparación sin nivel V, comparación con observación, informe, seis componentes, compuesto con/sin pesos, resolución ≠ precisión |
| `test_lineage_storage.py` | nombres de artefacto, política Git, deduplicación, promoción sin sobrescritura, `run_id` reproducible, grafo, detección de archivo alterado, artefacto sin linaje, grafo real verificado |
| `test_data_pipeline.py` | vigencia por dominio, cambio de cobertura, versión nueva, artefactos ausentes, monitoreo real, ausencia de catálogo, informe anterior conservado |
| `test_data_api.py` | 13 pruebas de endpoints: catálogo, ficha, 404, 409, filtros, bbox inválido, territorios, ocurrencias, ráster, calidad, dominios, almacenamiento, linaje |
| `test_phase4_performance.py` | ventana DEM, bloques CHIRPS, consulta de observaciones, carga de catálogo, perfiles por cabecera |

## 3. Fixtures

- GeoJSON, CSV y GeoTIFF sintéticos en `tmp_path`, creados por las pruebas.
- Polígono «bowtie» para geometrías autointersectadas.
- Ráster de 20×20 y 200×200 con nodata declarado y sin declarar.
- Serie diaria con huecos, duplicados y centinelas.
- Catálogo temporal en JSON.
- Bases y almacenes temporales; nunca se toca `data/` real en las pruebas
  unitarias.
- Evidencia real cuando existe: catálogo, base, linaje, DEM y CHIRPS de Fase 3.

Ningún fixture contiene observaciones inventadas presentadas como reales.

## 4. Rendimiento

Umbrales deliberadamente holgados; buscan detectar un cambio de orden de
magnitud, no medir hardware:

| Prueba | Umbral | Qué protege |
|---|---|---|
| ventana del DEM (~6×6 km) | <2 s y menos celdas que el archivo | que no se lea el país completo |
| bloques CHIRPS | ≥1 bloque y el mayor <10 % de celdas | que no se materialice el ráster global |
| consulta de 100 observaciones | <1 s | índices y `LIMIT` |
| carga del catálogo (22 datasets) | <2 s | JSON pequeño, sin base |
| 5 perfiles ráster por cabecera | <3 s | no abrir datos completos |

La suite completa tarda ~22 s en la máquina de desarrollo. No se declara un
benchmark reproducible: no se midió memoria pico ni se ejecutó en hardware
controlado.

## 5. Defectos encontrados por las pruebas (y corregidos)

1. **Compuesto de incertidumbre**: `composite()` usaba `c.value` sobre un
   `ComponentStatement` y lanzaba `AttributeError` en lugar de `UncertaintyError`.
   Se corrigió a `c.component.value`; la prueba exige el error correcto.
2. **Encabezado HTTP no latin-1**: la licencia del DEM contiene «—» y provocaba
   `UnicodeEncodeError` al construir `X-AGROSV-License`. Se translitera a ASCII
   antes de enviar; el cuerpo conserva el texto original.
3. **Borde temporal**: filtrar observaciones por año devolvía 364 o 367 en lugar
   de 366 para 2020, por comparar `period_start`/`period_end` en UTC. Se adoptó
   fecha local de referencia con `end` inclusivo; la prueba fija 366.
4. **Hash de SQLite inestable**: el archivo cambia con WAL/checkpoint y la
   verificación de linaje fallaba tras una consulta. Se añadió hash lógico
   (`sqlite-logical`) para bases y se excluyó el archivo físico del manifiesto.
5. **Copia idéntica marcada como ciclo**: un input y output con el mismo sha256
   se interpretaba como ciclo de linaje. Se ignoran las auto-aristas; una copia
   sin cambio de contenido es una derivación válida.

Cada corrección se verificó volviendo a ejecutar la prueba afectada y, al final,
la suite completa.

## 6. Lo que las pruebas no demuestran

- Que los datos sean científicamente correctos: validan el motor, no la realidad.
- Que las comprobaciones de calidad cubran todos los errores posibles.
- Que la API resista carga concurrente o ataques: no hay pruebas de seguridad ni
  de estrés.
- Que la reconstrucción de un producto sea automática: se verifica el manifiesto,
  no se reejecuta el pipeline desde cero en la prueba.
- Cobertura de líneas: no se midió; no se afirma un porcentaje.

## 7. Reproducir

```bash
cd "/c/GIT HUB/agrosv"

# suite completa
.venv/Scripts/python.exe -m pytest tests/ -q

# solo Fase 4
.venv/Scripts/python.exe -m pytest tests/test_data_*.py \
  tests/test_geo_normalization.py tests/test_raster_temporal.py \
  tests/test_quality_confidence.py tests/test_lineage_storage.py \
  tests/test_phase4_performance.py -q
```

Si faltan artefactos, las pruebas dependientes se saltan; construir primero con
`scripts/08_build_phase4_integration.py --rebuild`.
