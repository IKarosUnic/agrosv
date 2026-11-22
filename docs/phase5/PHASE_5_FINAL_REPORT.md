# Informe final — Fase 5

**AGROSV — Inteligencia territorial y ambiental**
Cierre: 2026-11-22 · versión de motores: **5.0.0**

---

## 1. Componentes implementados

| Componente | Archivo | Estado |
|---|---|---|
| `TerritorialEngine` | `backend/agrosv/engines/territorial.py` | implementado |
| Análisis de terreno | `backend/agrosv/engines/terrain.py` | implementado |
| `SoilEngine` | `backend/agrosv/engines/soil.py` | implementado (0–30 cm) |
| `HydrologyEngine` | `backend/agrosv/engines/hydrology.py` | implementado parcialmente |
| `ClimateEngine` | `backend/agrosv/engines/climate.py` | implementado (2 puntos) |
| `EnvironmentalInteractionEngine` | `backend/agrosv/engines/environmental.py` | implementado, sin índice compuesto |
| Gobernanza §8 | `backend/agrosv/engines/governance.py` | implementado |
| Caché derivado | `backend/agrosv/engines/cache.py` | implementado |
| API `/api/engines` | `backend/agrosv/engines/api.py` | 15 endpoints |
| Banco de rendimiento | `scripts/09_phase5_benchmark.py` | implementado |

### Estado de partida

El repositorio ya contenía los cinco motores y cuatro módulos de prueba, pero:

- 7 pruebas fallaban (3 errores reales de código, 3 expectativas incorrectas y 1
  validación ausente);
- dos reglas de interacción eran inalcanzables;
- no existían pruebas del motor ambiental ni de la API `/api/engines`;
- no existía ninguna documentación de Fase 5;
- el rendimiento no estaba medido con un instrumento reproducible.

Esta pasada auditó, reparó y completó el trabajo, y documentó lo que realmente hace.

## 2. Archivos modificados y creados

### Modificados

```
backend/agrosv/engines/api.py             +3 endpoints, errores y validación
backend/agrosv/engines/environmental.py   reglas de ausencia ejecutables
backend/agrosv/engines/hydrology.py       ventana mínima, rango Budyko ordenado
backend/agrosv/engines/soil.py            USDA corregido, perfil por profundidad
backend/agrosv/engines/territorial.py     perfil por identificador, intersección
tests/conftest.py                         require() con rutas relativas
tests/test_engines_territorial.py         expectativas TRI/TPI/pendiente corregidas
tests/test_engines_soil.py                expectativas del modelo de perfil
README.md                                 sección de Fase 5
```

### Creados

```
tests/test_engines_integration.py         36 pruebas nuevas
scripts/09_phase5_benchmark.py            medición reproducible
docs/phase5/TERRITORIAL_ENGINE.md
docs/phase5/TERRAIN_ANALYSIS_ENGINE.md
docs/phase5/SOIL_INTELLIGENCE_ENGINE.md
docs/phase5/HYDROLOGY_ENGINE.md
docs/phase5/CLIMATE_ENGINE.md
docs/phase5/ENVIRONMENTAL_INTERACTION_ENGINE.md
docs/phase5/SCIENTIFIC_METHODS_AND_ASSUMPTIONS.md
docs/phase5/ENVIRONMENTAL_DATA_VALIDATION.md
docs/phase5/PHASE_5_TESTING_REPORT.md
docs/phase5/PHASE_5_FINAL_REPORT.md
docs/phase5/benchmark_phase5.json
```

### Artefactos regenerados (no son código)

`data/manifests/*`, `data/metadata/*` y `data/validated/observations/*` se regeneraron
con `scripts/08_build_phase4_integration.py --rebuild` para eliminar rutas absolutas de
Windows. La base SQLite y la muestra CHIRPS siguen fuera de Git (`.gitignore`) y se
reconstruyen con los scripts documentados.

## 3. Datasets realmente integrados

| Dataset | Uso | Clase | Resolución | Licencia |
|---|---|---|---|---|
| Copernicus DEM GLO-30 | elevación, pendiente, aspecto, TRI/TPI | `modeled_prediction` | ~30 m | DLR/Airbus, atribución |
| geoBoundaries ADM0/1/2 | identificación territorial | `observed` | vectorial | CC BY-SA 2.0 |
| OpenStreetMap | cauces y cuerpos de agua | `observed` | vectorial | ODbL 1.0 |
| SoilGrids 2.0 | textura, pH, SOC, N (0–30 cm) | `modeled_prediction` | 250 m | CC BY 4.0 |
| NASA POWER | P, Tmax, Tmin | `reanalysis` | ~55 × 69 km | datos abiertos |
| Open-Meteo | P, ET0, HR, Tmax, Tmin | `reanalysis` | ~9 km | datos abiertos |
| CHIRPS v3.0 | una muestra de un día (catálogo) | `satellite_estimate` | ~5,5 km | datos abiertos |

Disponibles según gobernanza (comprobando artefactos, no catálogo):
`copdem30`, `geoboundaries_adm1`, `osm_sv`, `soilgrids_2`, `nasa_power_point`,
`open_meteo_point`, `chirps3`.

No se usa ningún dataset restringido (CENTA, SNET/MARN, HydroSHEDS, Protected Planet)
ni se simula su contenido.

## 4. Cobertura geográfica

| Dimensión | Cobertura real |
|---|---|
| Extensión | rectángulo `-90,179 a -87,635` O · `12,976 a 14,451` N |
| Unidades | 1 país + 14 departamentos + 272 municipios históricos = 287 |
| Suelo | tierra firme, 250 m, 0–30 cm, 97,4 % de celdas con dato |
| Clima | **2 coordenadas**, 2019-01-01 a 2025-12-31 |
| Hidrología superficial | cauces OSM, cobertura incompleta |
| Agua subterránea | **sin cobertura** |
| Municipios 2023 / distritos | **sin cobertura** |
| Cuencas oficiales | **sin cobertura** |

El clima no cubre el país: quien consulte un punto recibe la distancia al punto de
reanálisis usado y la advertencia de que no se interpola.

## 5. Métodos científicos aplicados

| Dominio | Método | Supuesto principal |
|---|---|---|
| Terreno | diferencias finitas; Riley (1999); TPI 3×3 | DSM ≠ DTM; resolución ≠ precisión |
| Suelo | triángulo USDA-NRCS; Van Bemmelen 1,724 | predicción global ≠ laboratorio |
| Hidrología | priority-flood (2014) + D8 (1984); Budyko–Fu ω=2 | sin aforos; estado estacionario |
| Clima | ETCCDI (Zhang 2011); Walter–Lieth; percentiles | reanálisis ≠ observación; 7 años ≠ normal |
| Integración | reglas declaradas, sin pesos | reglas generales, no validadas localmente |

Detalle de fórmulas, parámetros y supuestos en
`SCIENTIFIC_METHODS_AND_ASSUMPTIONS.md`.

## 6. Pruebas ejecutadas y resultados

```bash
.venv/bin/python -m pytest tests -q
# 373 passed, 33 warnings in 24.29s
```

- 102 pruebas específicas de Fase 5 (19 territorial, 22 suelo, 10 hidrología,
  15 clima, 36 integración).
- 271 pruebas de Fase 1–4 siguen pasando.
- 0 fallos, 0 omisiones en la ejecución final.
- Se corrigieron 3 errores de código, 1 validación ausente, 2 reglas inalcanzables y
  3 expectativas de prueba incorrectas. Detalle en `PHASE_5_TESTING_REPORT.md`.

## 7. Mediciones de rendimiento

5 repeticiones por operación, sin red:

| Operación | Mediana |
|---|---:|
| Perfil ambiental completo (3 km) | **0,092 s** |
| Perfil territorial (incluye cuenca) | 0,143 s |
| Terreno | 0,019 s |
| Suelo | 0,019 s |
| Cuenca D8 (3 km) | 0,032 s |
| Clima | 0,012 s |
| Intersección nacional (287 unidades) | 0,017 s |
| Caché: 1.ª / 2.ª llamada | 0,182 s / **0,0014 s** |
| RSS durante perfil 6 km | +1,0 MiB |
| Pico Python (`tracemalloc`) | 4,0 MB |

La ventana hidrológica de 3 km son 100 × 100 celdas; no se carga el DEM nacional. El
detalle y el método están en `docs/phase5/benchmark_phase5.json` y
`scripts/09_phase5_benchmark.py`.

## 8. Límites conocidos

1. **No hay validación científica**: ninguna cifra tiene error medido contra una
   referencia independiente.
2. **Suelo**: predicción global de 250 m, solo 0–30 cm, sin CEC, densidad aparente,
   fragmentos gruesos, AWC ni salinidad.
3. **Clima**: dos puntos de reanálisis, siete años, sin estaciones ni normales OMM.
4. **Hidrología**: sin caudales, sin recarga, sin agua subterránea, sin cuencas
   oficiales; D8 y Budyko no están calibrados.
5. **Territorio**: ADM2 histórico y no oficial; sin municipios 2023 ni distritos.
6. **OSM**: cobertura incompleta y precisión heterogénea; ausencia ≠ ausencia real.
7. **Incertidumbre**: identificada por componente, no cuantificada.
8. **Sin índice compuesto**: no hay pesos ni variable objetivo validados.
9. **Perfil por identificador**: punto interior, no agregado areal.
10. **Rendimiento**: medido en un host, sin concurrencia ni prueba de carga.
11. **Auditoría estructural ≠ auditoría científica**: los estados V1 verifican
    coherencia, no verdad.

## 9. Datos ausentes

Enumerados y consultables en `GET /api/engines/datasets` (`unavailable_variables`):

- perfiles de suelo por horizonte; profundidad efectiva; densidad aparente; fragmentos
  gruesos; CEC; agua disponible; salinidad; mapa nacional de suelos;
- acuíferos; niveles piezométricos; recarga; calidad del agua; derechos de agua;
- estaciones meteorológicas; normales OMM; pronóstico climático;
- caudales; cuencas oficiales; municipios 2023 y distritos.

Cada entrada incluye `reason`, `would_require` y `status`.

## 10. Recomendaciones para Fase 6

1. **Datos de estación SNET/MARN** con licencia: es la llave para validar clima,
   normales y índices extremos. Sin esto, Fase 6 hereda la misma incertidumbre.
2. **Acceso CENTA y muestras de laboratorio**: validar SoilGrids, añadir profundidad,
   densidad aparente, CEC y AWC con pedotransferencia validada.
3. **Cuencas oficiales y aforos**: sustituir la cuenca D8 local y calibrar escorrentía.
4. **Correspondencia 2023 y límites vigentes**: cerrar la brecha ADM2 histórica.
5. **Puntos de control GNSS**: cuantificar el error vertical del DEM.
6. **Cuantificar al menos un componente de incertidumbre** con referencia; mantener el
   resto como «no cuantificada».
7. **Motor de simulación agrícola** que consuma estos perfiles, con parámetros de cultivo
   explícitos; no iniciar Saltbor en esta fase.
8. **Operación**: CI que ejecute las 373 pruebas, programador de monitoreo y evaluación
   de PostGIS/Zarr solo cuando el volumen lo justifique.

## Criterios de aceptación (§14)

| Criterio | Evidencia | Estado |
|---|---|---|
| Cuatro motores principales existen e integrados | 5 motores + perfil ambiental | cumplido |
| Usan datasets verificados o declaran ausencia | gobernanza comprueba artefactos; 19 variables ausentes declaradas | cumplido |
| Consultas geográficas correctas | 4 regiones, contención, intersección, identificadores | cumplido |
| Unidades y CRS consistentes | 4326 consulta · 32616 métrico · 6933 área; pruebas | cumplido |
| Procedencia preservada | ficha §8 en cada fuente y respuesta | cumplido |
| Supuestos documentados | `SCIENTIFIC_METHODS_AND_ASSUMPTIONS.md` | cumplido |
| Incertidumbre representada | por componente; agregado no cuantificado | cumplido |
| Pruebas automatizadas pasan | 373 passed, 0 failed | cumplido |
| Funcionalidad existente operativa | 271 pruebas de fases previas pasan | cumplido |
| Rendimiento medido | benchmark reproducible con cifras | cumplido |
| Documentación refleja la implementación | 10 documentos + benchmark | cumplido |
| Validación científica | **no alcanzada**: sin referencias independientes | declarado, no reclamado |

## Principio final

AGROSV no afirma saber lo que sus datos no pueden demostrar. En esta fase se prefirió:

- un perfil sin índice compuesto a un número arbitrario;
- una cuenca de dos celdas declarada a una cuenca «plausible» inventada;
- una predicción etiquetada como predicción a un suelo presentado como medición;
- un rango de sensibilidad explicado a un intervalo de confianza falso;
- una lista de variables ausentes a una tabla completa de apariencia científica.
