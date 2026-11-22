# Modelo de datos censal — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Fuentes:** VII Censo de Población y VI de Vivienda 2024 (CPV 2024) y V Censo
Agropecuario y I Censo de Pesca 2025 (CAP 2025), ambos del BCR.

Reglas que gobiernan este documento:

1. **No se asume disponibilidad de microdatos.** Se documenta lo publicado y lo
   que falta.
2. **No se intenta identificar personas, hogares ni explotaciones.** No hay
   cruces que permitan reidentificación, ni se publican celdas con conteos
   pequeños.
3. **Los dos censos no son intercambiables.** Uno mide población y vivienda; el
   otro mide unidades de producción agropecuaria y pesca. Comparten geografía,
   no unidad de análisis.

---

## 1. Qué está publicado (verificado)

### CPV 2024

| Entrega | Fecha | Contenido |
|---|---|---|
| Primera | 29–31 oct 2024 | Resultados nacionales preliminares |
| Segunda | 30 ene 2025 | Fecundidad, mortalidad, emigración, educación, características económicas |
| Tercera | 2 abr 2025 | Base de datos censal anonimizada, informe de resultados, geoportal, nueva distribución urbano/rural, datos hasta distrito |
| Departamental | 25 jul 2025 | Fichas por los 14 departamentos |

- **Microdatos: públicos y anonimizados** (CSV y SPSS + diccionario de variables
  + guía de uso). Confirmado por la nota de la tercera entrega.
- **Tabulados**: Excel y PDF por tema, con desagregación
  **departamento → municipio → distrito** y bloque específico urbano/rural.
- **No publicado**: cartografía a nivel de segmento o manzana; la página de
  cartografía del subportal no es de acceso público.
- Operativo: censo de derecho, 100 % digital, 2 mayo–29 junio 2024.

### CAP 2025

| Entrega | Fecha | Contenido |
|---|---|---|
| Primera | 12 ene 2026 | Pecuario (bovinos, porcinos, aves, ovinos, caprinos, apicultura, producción de patio) y pesca |
| Segunda | 26 mar 2026 | Granos básicos, café, caña, henequén y tule, permanentes, acuicultura |
| Tercera | nov 2026 | Hortalizas, frutales, flores y follaje, pastos de corte, forestales, viveros, otros anuales, lácteos, huevos y pesca por especie/departamento |

- **Nivel de agregación: departamental** (y nacional). No hay tabulados
  municipales, distritales ni por segmento.
- **Microdatos: NO públicos.** El portal declara publicación «únicamente de
  forma agregada, sin identificar a personas, hogares o unidades de
  producción», con reserva conforme al art. 25 de la Ley Especial de
  Estadística y Censos.
- **Pendiente de publicación** (anunciado y no entregado): tenencia y uso del
  suelo / superficie total de las explotaciones, crédito y asistencia técnica
  agropecuaria, insumos/prácticas/maquinaria/riego, empleo generado.
- La tercera entrega se titula **«resultados preliminares»**: no hay cierre
  definitivo ni evaluación post-enumeración publicada.
- Periodos de referencia: día censal 2 mayo 2025; actividades mayo 2024–abril
  2025; café octubre 2023–septiembre 2024.

---

## 2. Unidad de análisis y geografía

```
CPV 2024                          CAP 2025
─────────                         ─────────
persona                           UPA (unidad de producción agrícola)
hogar                             UPP (unidad de producción pecuaria)
vivienda                          productor / explotación
     │                                 │
     └──────── distrito ───────────────┘
                 │
             municipio (44, reforma 2023)
                 │
             departamento (14)
```

**Conflicto de geografía, explícito:** el CPV 2024 publica hasta **distrito**
sobre la división vigente (44 municipios, 262 distritos). El Módulo 1 de AGROSV
publica ADM2 **histórico** (262 municipios pre-2023). Por tanto:

- Los agregados censales **no se unen** por nombre de municipio con `adm2`.
- Se une por **código de departamento** (ISO 3166-2:SV) y, cuando exista, por
  código de distrito del CNR/BCR.
- La tabla de correspondencia municipio histórico (262) ↔ distrito (262) es
  **biunívoca en la mayoría de casos**, pero debe construirse y validarse con la
  cartografía oficial, no por similitud de nombres. Estado:
  **PENDING_VALIDATION** hasta obtener esa cartografía.

**«Región agrícola»**: no hay límites oficiales descargados. Se modela como una
agrupación configurable (Occidente, Centro, Paracentral, Oriente) y se marca
`PENDING_VALIDATION` hasta contar con la delimitación del MAG.

---

## 3. Esquema propuesto

### 3.1 Tablas de hechos (agregados)

```sql
-- Población y vivienda (CPV 2024)
census_population(
  geography_level  TEXT,      -- 'department' | 'municipality' | 'district'
  geography_code   TEXT,      -- ISO 3166-2:SV o código BCR/CNR
  area_type        TEXT,      -- 'urbano' | 'rural' | 'total'
  sex              TEXT,      -- 'hombre' | 'mujer' | 'total'
  age_group        TEXT,      -- '0-4' … '80+'
  indicator        TEXT,      -- 'poblacion', 'hogares', 'viviendas', …
  value            NUMERIC,
  unit             TEXT,
  source_id        TEXT,      -- 'bcr-cpv2024'
  table_ref        TEXT,      -- p. ej. 'TAB_POB_1'
  published_at     DATE,
  PRIMARY KEY (geography_level, geography_code, area_type, sex, age_group, indicator)
);

-- Agropecuario y pesca (CAP 2025)
census_agriculture(
  geography_level  TEXT,      -- 'national' | 'department'
  geography_code   TEXT,
  producer_type    TEXT,      -- 'pequeño' | 'comercial' | 'total'
  legal_status     TEXT,      -- 'persona natural' | 'persona jurídica'
  sex              TEXT,
  crop_or_activity TEXT,      -- 'maiz', 'frijol', 'bovinos', 'pesca', …
  indicator        TEXT,      -- 'productores', 'area_sembrada', 'produccion', 'destino_venta'
  value            NUMERIC,
  unit             TEXT,      -- 'manzanas', 'quintales', 'litros', 'cabezas'
  reference_period TEXT,      -- '2024-05/2025-04'
  source_id        TEXT,      -- 'bcr-cap2025'
  table_ref        TEXT,
  published_at     DATE,
  delivery         TEXT       -- '1a' | '2a' | '3a'
);
```

### 3.2 Tablas de dimensión

```
dim_geography(code, level, name, parent_code, valid_from, valid_to, source_id)
dim_crop(code, name, group, unit_default, source_id)
dim_indicator(code, name, unit, definition, source_id)
dim_source(source_id, institution, url, license, acquired_at, notes)
```

`dim_geography` incluye `valid_from`/`valid_to`: es la única forma honesta de
convivir con el cambio 262 → 44 municipios sin reescribir la historia.

### 3.3 Microdatos CPV 2024 (aislados)

- Se almacenan **fuera** de las tablas de hechos, en `data/raw/bcr/cpv2024/`,
  con el diccionario de variables.
- Solo se cargan columnas necesarias para indicadores agregados; el identificador
  de vivienda/hogar se usa para agrupar y **no se publica**.
- El paquete de microdatos **no se redistribuye** desde la API ni el repositorio.

---

## 4. Reglas de confidencialidad y publicación

1. **Supresión primaria**: no se publica ninguna celda con menos de 10 unidades
   (hogares, personas o productores). Si el agregado queda por debajo, se
   agrupa en «otros» o se omite con nota.
2. **Sin reidentificación**: no se cruzan microdatos con catastro, OSM ni
   coordenadas para localizar un hogar o una explotación. La unidad mínima
   publicada es el distrito para población y el departamento para producción
   agropecuaria (porque es lo que el BCR publica).
3. **Sin inferencia de individuos**: los agentes Nemotron son sintéticos; no se
   «calibran» con microdatos para reproducir personas reales.
4. **Trazabilidad**: toda cifra publicada conserva `source_id`, `table_ref` y
   `published_at`, y declara si es preliminar.
5. **Los totales deben cuadrar**: suma de departamentos = nacional; si no
   cuadra, se documenta la diferencia (redondeo o «otros departamentos»).

---

## 5. Indicadores prioritarios para AGROSV

| Ámbito | Indicador | Nivel máximo | Uso |
|---|---|---|---|
| Población | Población por distrito y área urbano/rural | Distrito | Denominadores, demanda |
| Hogares | Hogares con actividad agropecuaria (si se publica) | Distrito | Agricultura doméstica |
| Vivienda | Viviendas con patio/terreno | Distrito | Agricultura en patios |
| Productores | Número por tipo y sexo | Departamento | Simulación de agentes |
| Explotaciones | UPA/UPP por departamento | Departamento | Estructura productiva |
| Superficie | Área sembrada y cosechada por cultivo | Departamento | Contraste con Sentinel-2 |
| Producción | Quintales/toneladas por cultivo | Departamento | Cadena de valor |
| Destino | Autoconsumo / venta / canal | Departamento | Seguridad alimentaria |
| Pecuaria | Existencias por categoría | Departamento | Modelo pecuario |
| Pesca | Extracción por especie | Departamento | Módulo pesquero |

**Nota:** «superficie total de las explotaciones» **no está publicada** todavía.
No se estima por diferencia ni se imputa: se marca como no disponible.

---

## 6. Validación

| Prueba | Criterio |
|---|---|
| Cuadre vertical | ∑ departamentos = total nacional (± redondeo documentado) |
| Cuadre horizontal | ∑ categorías = total de la tabla |
| Coherencia de unidades | manzanas vs hectáreas vs quintales declarados explícitamente (1 manzana = 0,6989 ha) |
| Geografía | todo código existe en `dim_geography`; sin huérfanos |
| Periodo | `reference_period` no se mezcla entre entregas |
| Confidencialidad | ninguna celda < 10; prueba automatizada de supresión |
| Contraste externo | superficie de maíz censal vs anuario MAG (diferencia explicada, no silenciada) |

Estas pruebas se incorporan a `tests/` cuando exista la ingesta; hoy el
documento fija el contrato.

---

## 7. Riesgos específicos

1. **Cambio de geografía 2023** (262 → 44 municipios): unir por nombre rompe
   series. Mitigación: claves + `valid_from/valid_to`.
2. **CAP preliminar**: las cifras pueden cambiar en la entrega definitiva.
   Mitigación: campo `delivery` y advertencia en la UI.
3. **Microdatos CPV con coordenadas**: aunque sean anonimizados, un cruce con
   catastro podría reidentificar. Mitigación: prohibición explícita de ese
   cruce.
4. **Sesgo de «producción de patio»**: el CAP la reporta en la entrega
   pecuaria; no equivale a agricultura urbana.
5. **Cifras incompletas por reserva estadística**: el BCR agrupa departamentos
   pequeños en «otros»; no se desagrega artificialmente.
