# CENSUS_AND_SOCIOECONOMIC_DATA — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Evidencia:** sondas propias + páginas del BCR.
El detalle del modelo de datos está en [`../CENSUS_DATA_MODEL.md`](../CENSUS_DATA_MODEL.md);
este documento inventaría **qué existe, con qué desagregación y bajo qué reglas**.

---

## 1. Operaciones censales de la ronda 2023–2027 (BCR)

| Operación | Año | Unidad | Resultados publicados | Acceso |
|---|---|---|---|---|
| Actualización cartográfica y precenso | 2023 | Segmento/vivienda | Marco muestral (no público) | Interno |
| **VII Censo de Población y VI de Vivienda (CPV)** | 2024 | Persona, hogar, vivienda | Tabulados + microdatos anonimizados | Descarga pública |
| **V Censo Agropecuario y I de Pesca (CAP)** | 2025 | Unidad de producción agropecuaria/pesquera | 3 entregas de resultados agregados | PDF/PPT + geoportal |
| Encuesta Nacional de Ingresos y Gastos de los Hogares | 2026–2027 | Hogar | No publicada aún | — |
| Cartografía y Censo Económico | 2026–2027 | Establecimiento | No publicada aún | — |

**Fuente:** páginas del Geoportal BCR y notas institucionales verificadas el
2026-11-22 (`bcr_geoportal` 200; `bcr_agropecuario` 200; `bcr_poblacion_tabulados` 200).

---

## 2. V Censo Agropecuario y I de Pesca 2025

### 2.1 Entregas verificadas

| Entrega | Fecha | Contenido | Evidencia |
|---|---|---|---|
| Primera (preliminar) | 2026-01 | Sector pecuario y pesquero | `bcr_cap_primera_pdf` → 206, `application/pdf` |
| Segunda | 2026-03 | Granos básicos (maíz, frijol, arroz, maicillo), café, caña, permanentes y semipermanentes, acuicultura | `bcr_cap_segunda_pdf` → 200, `application/pdf` |
| Tercera | 2026-11 | Hortalizas, frutales, flores y follajes, pastos de corte, forestales, viveros, otros cultivos anuales, otros animales, almacenamiento de granos, leche, huevos, captura pesquera | `bcr_cap_tercera_pdf` → 200, `application/pdf` |

Páginas de documentación: `agropecuario.bcr.gob.sv/pages/documentos-cap-seg` y
`/pages/documentacion-cap-ter` (ambas 200).

### 2.2 Cifras clave ya registradas por AGROSV

| Indicador (año agrícola 2024-2025) | Valor | Verificación |
|---|---|---|
| Maíz — superficie cosechada | 293.458 mz | Registrada en fases previas desde la presentación del BCR; **re-verificar página** |
| Maíz — producción | ~10,9 millones qq (~493.403 t) | Ibídem |
| Maíz — productores | 401.101 | Ibídem |
| Maíz — semilla híbrida / criolla | 75,0 % / 19,7 % del área | Ibídem |
| Maíz — destino autoconsumo / venta | 49,5 % / 47,8 % | Ibídem |
| Frijol — producción | 996,2 mil qq (~45.189 t) | Ibídem |
| Frijol — productores | 214.738 | Ibídem |
| Frijol — destino autoconsumo / venta | 50,3 % / 48,8 % | Ibídem |
| Concentración de maíz | Ahuachapán 12,3 %, Santa Ana 10,6 %, La Libertad 8,7 %, Usulután 8,2 %, Sonsonate 8,0 % | Ibídem |

**Nota de método:** estas cifras se citan con su fuente institucional pero sin
número de página. Antes de exponerlas en la API deben extraerse del PDF con
referencia de página y control de totales (regla R-8).

### 2.3 Desagregación disponible

| Nivel | Disponible | Nota |
|---|---|---|
| Nacional | SÍ | Todas las entregas |
| Departamental (14) | SÍ | Núcleo de la publicación |
| Municipal (44 desde 2023) | **NO publicado** en las entregas verificadas | No confundir con tabulados del CPV |
| Distrito (262) | **NO** | — |
| Unidad de producción | **NO** — prohibido por secreto estadístico | Ley Especial de Estadística y Censos, art. 25 |

### 2.4 Temas cubiertos por la boleta (según la presentación de la 2.ª entrega)

Clasificación del productor (comercial / pequeño / patio), producción agrícola y
pecuaria, uso del suelo, cultivos, comercialización, insumos y prácticas,
características sociodemográficas del productor, actividades no agropecuarias,
pesca (embarcaciones, equipo, captura, destinos).

**Temas con vacío:** tamaño de explotación por rango (publicado parcialmente),
mano de obra contratada, acceso a crédito, acceso a riego por distrito, pérdidas
poscosecha, precios recibidos por el productor.

---

## 3. VII Censo de Población y VI de Vivienda 2024

| Aspecto | Estado |
|---|---|
| Microdatos anonimizados | **SÍ** (CSV/SPSS + diccionario, según la base de datos del BCR) |
| Tabulados | XLSX/PDF, desagregación departamento → municipio → distrito |
| Población total | 6.029.976 (cifra citada en la ficha de Nemotron y en el registro del proyecto; confirmar en tabulado oficial) |
| Variables útiles para AGROSV | urbano/rural, sexo, edad, ocupación (CIIU Rev.4), departamento, municipio, vivienda, servicios |
| Acceso verificado | `poblacion.bcr.gob.sv/pages/teg-base-de-datos-y-tabulados` → 200 |
| Licencia | No declarada explícitamente; se trata como dato abierto con atribución y sin redistribución de microdatos |

**Regla de privacidad:** los microdatos del CPV **no se unen** a la base de
productores del CAP ni a geometrías de parcela. Se usan agregados y, si se
requiere microdato, solo con las salvaguardas del BCR.

---

## 4. IV Censo Agropecuario 2007-2008 (serie histórica)

| Aspecto | Estado |
|---|---|
| Publicación | Resumen nacional + resultados departamentales y municipales (PDF) |
| Acceso | `mag_censo2007` → 200 (116.135 B, página) |
| Utilidad | Comparación 2007 vs 2025 (17 años de cambio estructural) |
| Limitación | PDF; definiciones y cobertura pueden no ser comparables con el CAP 2025 |

**Regla:** cualquier comparación 2007–2025 debe declarar cambios de metodología,
de universo (unidades de producción) y de división territorial (262 → 44).

---

## 5. Otras fuentes socioeconómicas

| Fuente | Contenido | Estado |
|---|---|---|
| EHPM (Encuesta de Hogares de Propósitos Múltiples) | Ingresos, empleo, pobreza | No sondeada en esta fase; referenciada por Nemotron (2024) |
| BCR — comercio exterior | Exportaciones/importaciones agropecuarias | **VERIFIED** (portal) |
| Banco Mundial — indicadores SLV | Superficie agrícola, población rural | **VERIFIED** (API, muestra de 14.891 B) |
| WorldPop | Población en rejilla | **VERIFIED** (portal) |
| GHSL (JRC) | Asentamientos y población | **VERIFIED** (portal) |
| ONE/ONEC | Estadísticas oficiales | **UNAVAILABLE** (`one.gob.sv` no resuelve DNS el 2026-11-22) |

La caída de DNS de `one.gob.sv` es un hallazgo operativo: las estadísticas
oficiales deben buscarse en el geoportal del BCR mientras el dominio no resuelva.

---

## 6. Indicadores prioritarios para AGROSV

| Indicador | Fuente | Nivel | Uso |
|---|---|---|---|
| Productores por cultivo | CAP 2025 | Nacional/dept. | Dimensionar universo |
| Superficie y producción | CAP 2025 | Nacional/dept. | Verdad de referencia |
| % autoconsumo vs venta | CAP 2025 | Nacional | Modelos de comportamiento |
| Urbano/rural | CPV 2024 | Dept./municipio | Perfiles de productor |
| Ocupación agrícola (CIIU 01) | CPV 2024 + Nemotron | Dept./municipio | Agentes sintéticos |
| Acceso a agua y servicios | CPV 2024 | Dept./municipio | Vulnerabilidad |
| Superficie regada | CAP 2025 | Nacional/dept. | Aptitud y riego |

---

## 7. Reglas de publicación

1. No se publica una celda con menos de 10 unidades (control de divulgación).
2. No se reconstruye un microdato a partir de totales y marginales.
3. Toda tabla lleva: fuente, operación, año, nivel geográfico y fecha de descarga.
4. Los microdatos del CPV nunca salen del entorno controlado.
5. Las cifras del CAP se citan con página del PDF o código de tabulado.
