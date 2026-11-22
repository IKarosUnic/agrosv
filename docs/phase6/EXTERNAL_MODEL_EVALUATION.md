# Evaluación técnica de repositorios externos

**Fase 6 · Etapa 1 · Ningún repositorio fue clonado, vendorizado ni fusionado**

La evaluación se hizo sobre la documentación pública, metadatos de paquetes y
el árbol del repositorio en GitHub. No se ejecutaron los modelos: sus
requisitos de calibración no se cumplen con los datos disponibles en AGROSV.

## Criterios

Licencia, mantenimiento, dependencias, arquitectura, metodología científica,
modelos disponibles, formatos de entrada/salida, complejidad de integración,
reutilización, limitaciones y compatibilidad con AGROSV.

## Modelos agrícolas

| Repositorio | Licencia | Mantenimiento verificado | Lenguaje / dependencias | Metodología | Integración | Decisión Fase 6 |
|---|---|---|---|---|---|---|
| `aquacropos/aquacrop` | Apache-2.0 | activo; PyPI `aquacrop` 3.1.2; ~541 commits | Python; NumPy/pandas | AquaCrop 7.1: agua del suelo, biomasa, rendimiento; sin salinidad, fertilidad, malezas ni perennes | media: API Python, requiere clima diario, suelo, cultivo calibrado | **no integrado**; candidato prioritario para Fase 7 |
| `gicait/PyAEZ` | MIT | PyPI 2.2 (dic-2023) | Python ≥3.6; NumPy, GDAL/rasterio | AEZ: clima, cultivo, restricciones clima-suelo-terreno, aptitud económica; orientado a rejillas | media-alta: LUT y rejillas, no puntos | **no integrado**; AGROSV reimplementa reglas declaradas, no su algoritmo |
| `DSSAT/dssat-csm-os` | BSD-3-Clause | v4.8.6 (2026) | Fortran/C, CMake | 45+ cultivos; coeficientes genéticos vía GENCALC/GLUE | alta: binario, `.SOL/.WTH/.CUL`, calibración varietal | **no integrado**; sin coeficientes salvadoreños |
| `ajwdewit/pcse` | EUPL-1.2 | v6.x (2026) | Python ≥3.9; PyYAML, pandas, openpyxl, dotmap, pydispatcher, traitlets-pcse | WOFOST, LINTUL3, LINGRA, ALCEPAS; potencial, agua y N | media: API Python, requiere cultivo/variedad y manejo | **no integrado**; licencia y parámetros |

### Lo que se reutilizó conceptualmente

* FAO-56 (AquaCrop y PCSE comparten la base): balance de agua, Kc, ETc, TAW/RAW,
  Ks. AGROSV lo implementa de forma nativa y transparente.
* Marco de evaluación de tierras / AEZ (PyAEZ): clases S1/S2/S3/N y factores
  limitantes. AGROSV usa reglas propias y lo declara.
* Advertencia de DSSAT y PCSE: sin coeficientes varietales no hay simulación
  defendible.

### Lo que no se copió

Código, tablas de decisión, coeficientes de cultivo, LUT de PyAEZ, archivos de
suelo o clima, ni binarios. No se añadieron dependencias.

## Nemotron y población sintética

| Repositorio | Licencia | Estado | Capacidades | Integración | Decisión |
|---|---|---|---|---|---|
| `IKarosUnic/sv-people` (Saltbor) | Apache-2.0 | Python 3.12; 27 commits; 561 pruebas reportadas | personas, cognición, memoria, estados, hogares, economía, MAUT/GOAP/HTN, geografía OSM, multiagente, adaptador Nemotron con fallback sin LLM, SQLite (~0,57 KB/agente) | media: solapamiento con Subsistema B | **no integrado ni fusionado**, por instrucción explícita |

`sv-people` demuestra que una simulación determinista sin LLM es viable y que
el costo por agente puede ser muy bajo. AGROSV implementa su propia capa para
mantener independencia y evitar duplicar la arquitectura de Saltbor.

## Regla de interoperabilidad

En Fase 6 no hay acoplamiento directo. Los contratos previstos son:

1. `SOURCE_PROFILE` compatible con el esquema Nemotron.
2. Identificadores estables (`AGSV-<arquetipo>-<índice>`).
3. Eventos de simulación con capa, procedencia y escenario.
4. Un adaptador futuro puede traducir esos registros al formato de Saltbor sin
   compartir estado ni base de datos.

## Conclusión

Ningún modelo externo se presenta como integrado. La línea base ejecutable es
el balance FAO-56 de AGROSV. La prioridad de Fase 7 es obtener parámetros
locales antes de adoptar un modelo externo, no adoptarlo para sustituir la
falta de datos.
