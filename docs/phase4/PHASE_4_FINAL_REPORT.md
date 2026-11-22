# Informe final — Fase 4

**AGROSV — Integración, normalización y calidad de datos nacionales**
Fecha de cierre: 2026-11-22 · Versión de la capa de datos: 4.0.0

## 1. Qué se construyó

Una capa de datos científicos sobre los motores existentes, sin duplicarlos:

```
backend/agrosv/data/
  storage.py     zonas, nombres, hashes, promoción, política Git
  catalog.py     9 estados, evidencia, auditoría
  ingest.py      detección, integridad, deduplicación, lotes, descargas
  geo.py         CRS, métricas, geometrías, reparación registrada
  territory.py   IDs estables, niveles, correspondencias
  raster.py      perfil, ventanas, bloques, reproyección, contenedores
  temporal.py    UTC/local, evidencia, frecuencia, agregación, temporadas
  quality.py     comprobaciones espaciales, temporales, numéricas, científicas
  confidence.py  seis componentes de incertidumbre, sin índice arbitrario
  lineage.py     manifiestos, grafo, hash lógico de bases
  domains.py     contratos A–H
  store.py       SQLite de consulta
  api.py         /api/data
  pipeline.py    vigencia, cambios, revalidación, monitoreo
```

Se reutilizan `agrosv.science` (manifiestos, validación V0–V4, orquestador) y los
motores de Fase 1–3. La API `/api/v1` y los endpoints anteriores siguen
funcionando.

## 2. Resultados verificables

### Catálogo

- 22 datasets, 71 transiciones, auditoría estructural `ok: true`.
- Todos los estados representados: 1 DISCOVERED, 2 ACCESS_PENDING, 1 DOWNLOADED,
  1 PARSED, 2 VALIDATED, 7 INTEGRATED, 4 RESTRICTED, 3 UNAVAILABLE, 1 REJECTED.
- 10 fichas declaran campos desconocidos en `missing_fields` en lugar de
  rellenarlos (variables y, en tres casos, CRS).

### Ingesta y almacenamiento

- Almacén direccionado por contenido; una segunda importación idéntica devuelve
  `DUPLICATE` sin copiar.
- Lotes reanudables; un ítem bueno no se repite al reanudar.
- Base SQLite de 9,59 MB: 20.456 observaciones, 300 ocurrencias, 287 territorios,
  22 activos, 10 informes, R-tree activo.
- `data/raw/` y los derivados binarios quedan fuera de Git; la base y los
  rásteres derivados están en `.gitignore` y se regeneran con el script.

### Normalización

- 13 rásteres catalogados con CRS, resolución nativa, dtype y nodata.
- SoilGrids corregido a EPSG:32616 (no 4326); CHIRPS con nodata no declarado
  señalado; DEM en 4326 y derivados métricos en 32616.
- Áreas calculadas en EPSG:6933; calcular en grados lanza error.
- Reparación de geometrías con respaldo, hashes antes/después y cambio de área.
- Índice territorial de 287 unidades; la correspondencia 2023 queda
  `INCOMPLETE` y vacía a propósito.

### Calidad e incertidumbre

- 10 informes vigentes: 2 `PASS`, 8 `PASS_WITH_WARNINGS`, 0 `FAIL`.
- GBIF: 300 ocurrencias, 1 marcada `outside_land_bbox`, no eliminada.
- NASA vs Open-Meteo: `intercomparison`, n = 2.557 por variable, sin elevar nivel
  de validación.
- Seis componentes de incertidumbre; ningún dataset tiene compuesto numérico
  inventado. La plantilla queda sin cuantificar con su motivo.

### Linaje

- 5 derivaciones, 5 salidas, 4 entradas raíz, 0 sin validar.
- `verify()`: 5/5 manifiestos correctos.
- Bases SQLite verificadas por contenido lógico; archivos por sha256.
- Un archivo alterado se detecta; un artefacto sin registro no es publicable.

### API

12 endpoints de solo lectura bajo `/api/data`, probados con FastAPI TestClient:
catálogo, ficha, linaje, territorios, territorio, observaciones, ocurrencias,
metadatos ráster, informes, dominios y almacenamiento. Errores explícitos 400,
404, 409 y 503.

## 3. Criterios de aceptación

| Criterio | Evidencia | Estado |
|---|---|---|
| Catálogo funcional | 22 datasets, 9 estados, auditoría OK | cumplido |
| Ingestión reproducible | hashes, manifiestos, deduplicación, reanudación probados | cumplido |
| Metadatos normalizados | ficha completa de §3 + `missing_fields`; unidades canónicas | cumplido |
| CRS identificados y transformaciones verificadas | 13 perfiles; pruebas de área y reproyección | cumplido |
| Rásteres gestionados correctamente | nativa vs efectiva, nodata, bloques, rechazo de sobremuestreo | cumplido |
| Series temporales normalizadas | UTC/local, evidencia, frecuencia, agregación, 20.456 filas | cumplido |
| Validaciones automatizadas | motor de calidad + 10 informes | cumplido |
| Trazabilidad de derivados | 5 derivaciones, verificación 5/5 | cumplido |
| Almacenamiento eficiente | SQLite 9,59 MB + archivos; sin duplicar blobs; Git acotado | cumplido |
| API probada | 13 pruebas de endpoints | cumplido |
| Informes de calidad | 10 vigentes, con alcance y hallazgos | cumplido |
| Pruebas automatizadas | 270 pasan, 109 nuevas | cumplido |
| Documentación reproducible | 15 documentos + comandos + cifras reales | cumplido |

## 4. Verificación ejecutada

```bash
# construcción completa (exit 0)
.venv/Scripts/python.exe scripts/08_build_phase4_integration.py --rebuild
# → catalog.audit.ok=true, monitoring_ok=true, 22 datasets, 13 rásteres

# monitoreo
.venv/Scripts/python.exe -m agrosv.data.pipeline --monitor
# → ok=true, 11 frescos, 0 obsoletos/desconocidos, 0 artefactos ausentes

# suite completa
.venv/Scripts/python.exe -m pytest tests/ -q
# → 270 passed, 1 warning in 21.74s

# linaje
LineageGraph.verify()  # → {"checked": 5, "verified": 5, "ok": true}
```

Defectos corregidos durante la verificación: compuesto de incertidumbre con
`AttributeError`, encabezado HTTP no latin-1, borde temporal 364/367→366, hash
físico inestable de SQLite, copia idéntica interpretada como ciclo. Detalle en
`TESTING_AND_BENCHMARKS.md`.

## 5. Límites que permanecen

1. **No hay límites municipales 2023, distritos, cuencas, áreas protegidas ni
   parcelas verificadas.** No se sintetizaron.
2. **No hay series de estaciones SNET/MARN ni suelos CENTA.** La comparación
   climática es intercomparación de reanálisis.
3. **La muestra CHIRPS es de un día.** No es una serie nacional.
4. **Sentinel-2 son metadatos STAC**, no imágenes procesadas.
5. **Parquet, NetCDF y Zarr** se detectan, pero el entorno no tiene `pyarrow`,
   `xarray` ni `zarr` para inspección profunda.
6. **Incertidumbre**: componentes identificados, ninguno cuantificado con datos
   de referencia; no se publica un índice.
7. **Rendimiento**: pruebas con umbrales holgados, sin medición de memoria pico
   ni concurrencia.
8. **Sin programador automático**: el monitoreo se ejecuta localmente cuando el
   usuario lo decide.
9. **Auditoría estructural ≠ auditoría científica**: verifica coherencia y
   evidencia, no la verdad de las mediciones.

## 6. Decisión de honestidad

Ningún dataset se marcó `VALIDATED` o `INTEGRATED` por haber sido importado. Cada
transición tiene evidencia con referencia; los estados negativos (`RESTRICTED`,
`UNAVAILABLE`, `REJECTED`) documentan por qué no se usa un dato. Las ausencias
están en el catálogo, en la API y en este informe.

La base científica es deliberadamente conservadora: prefiere un mapa vacío a un
límite inventado, una etiqueta «sin cuantificar» a un número arbitrario y una
intercomparación declarada a una validación falsa.

## 7. Siguiente fase

Para construir los motores de inteligencia agrícola sobre esta base:

1. conseguir la tabla oficial de correspondencia 2023 y los límites vigentes;
2. acordar acceso a series SNET/MARN y datos CENTA, con licencia verificada;
3. ampliar CHIRPS a serie nacional y evaluar su error con estaciones;
4. implementar Zarr/Parquet cuando el volumen lo justifique;
5. cuantificar al menos un componente de incertidumbre con datos de referencia;
6. añadir un programador de monitoreo y CI para ejecutar la suite en cada cambio.

**Prioridad cumplida: una base de datos científica confiable antes que modelos
vistosos.**
