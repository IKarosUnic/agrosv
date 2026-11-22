# AGRICULTURAL_KNOWLEDGE_DATABASE — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Alcance:** qué conocimiento agronómico nacional existe,
dónde está, en qué formato y qué falta para operar los módulos de AGROSV.
Los parámetros numéricos por cultivo están en
[`CROP_PARAMETERS_CATALOG.md`](CROP_PARAMETERS_CATALOG.md).

---

## 1. Fuentes de conocimiento agronómico

| Fuente | Contenido | Formato | Acceso verificado | Estado |
|---|---|---|---|---|
| **MAG — Anuarios de Estadísticas Agropecuarias** | Superficie, producción, rendimiento, precios, comercio, mapas temáticos | PDF maquetado | 200 (`mag_anuario_2021_22`, 4.321.899 B) | **VERIFIED** |
| **MAG — mapas temáticos** | Zonas productoras de granos básicos, café, caña; uso del suelo; variables climáticas | 8 PDF (1,3–6,3 MB) | 200 | **VERIFIED** (documentos) |
| **MAG — costos de producción** | Costos por cultivo y ciclo | PDF | 200 | **VERIFIED** |
| **MAG — guía de precios de insumos** | Semillas, fertilizantes, agroquímicos | PDF | 200 | **VERIFIED** |
| **BCR — V Censo Agropecuario y I de Pesca 2025** | Productores, superficie, producción, variedades, destino, riego, prácticas | PDF/PPT, 3 entregas | 200/206 | **VERIFIED** (agregados) |
| **CENTA** | Variedades, recomendaciones, manejo, suelos | Visor/páginas; descarga no verificada | 403 a cliente automatizado | **PENDING_VALIDATION** |
| **CENTA/MAG — boletines técnicos y guías de cultivo** | Manejo por cultivo | PDF | Parcial | **DOCUMENTED** |
| **FAO AquaCrop 7.3** | Parámetros de cultivo (maíz, frijol, etc.) | Base de datos del modelo | Repositorio | **VERIFIED** (licencia FAO no comercial) |
| **DSSAT 4.8.6** | Coeficientes genéticos, fenología | Código + base | GitHub | **VERIFIED** (BSD-3, registro) |
| **FAOSTAT** | Producción, área, rendimiento nacional | API/bulk | API 521; bulk 403 | **PENDING_VALIDATION** |
| **OIRSA / IPPC** | Plagas y estatus fitosanitario | Portal | 200 | **VERIFIED** (portal) |

**Consecuencia estructural:** todo el conocimiento agronómico nacional publicado
es **PDF maquetado**. No hay una base de datos de cultivos descargable. La
extracción exige parseo de tablas, referencia de página y revisión humana; no se
automatiza sin control.

---

## 2. Catálogo de cultivos de El Salvador

### 2.1 Granos básicos (seguridad alimentaria)

| Cultivo | Nombre científico | Relevancia nacional | Fuente de superficie/producción |
|---|---|---|---|
| Maíz | *Zea mays* L. | Principal cultivo; ~293.458 mz cosechadas (2024-25) | CAP 2025 (2.ª entrega) |
| Frijol | *Phaseolus vulgaris* L. | Segunda base de la dieta; ~214.738 productores | CAP 2025 |
| Arroz | *Oryza sativa* L. | Producción nacional limitada; importación dominante | CAP 2025 / anuario MAG |
| Sorgo / maicillo | *Sorghum bicolor* (L.) Moench | Tolerante a sequía; zonas cálidas | CAP 2025 |

Los valores de superficie y productores citados provienen de la presentación del
BCR verificada en fases previas del proyecto y registrada en
`DATA_SOURCE_REGISTRY.md` §3.11. **Deben re-verificarse contra la página del PDF**
antes de publicarlos en la API.

### 2.2 Agroindustriales

| Cultivo | Nombre científico | Relevancia | Nota |
|---|---|---|---|
| Café | *Coffea arabica* L. (y *C. canephora*) | Exportación histórica; cordilleras cafetaleras | CENTA publica capa específica de suelos para cordilleras |
| Caña de azúcar | *Saccharum officinarum* L. | Azúcar y alcohol; ingenios | CAP 2025 incluye superficie y producción |

### 2.3 Frutales

| Cultivo | Nombre científico | Presencia documentada |
|---|---|---|
| Mango | *Mangifera indica* L. | Sí (mapas temáticos de frutales) |
| Aguacate | *Persea americana* Mill. | Sí |
| Cítricos (naranja, limón) | *Citrus* spp. | Sí |
| Papaya | *Carica papaya* L. | Sí |
| Otros (plátano, guayaba, marañón) | *Musa* spp., *Psidium guajava*, *Anacardium occidentale* | Parcial |

### 2.4 Hortalizas

Tomate (*Solanum lycopersicum*), chile (*Capsicum* spp.), cebolla (*Allium cepa*),
pepino (*Cucumis sativus*), repollo (*Brassica oleracea* var. *capitata*), pipián
(*Cucurbita argyrosperma*), güisquil (*Sechium edule*), zanahoria (*Daucus carota*),
remolacha (*Beta vulgaris*), rábano (*Raphanus sativus*).

### 2.5 Otros sistemas

Cacao (*Theobroma cacao*), coco (*Cocos nucifera*), henequén (*Agave fourcroydes*),
tule, sistemas agroforestales café-sombra.

---

## 3. Producción agrícola: qué está publicado y con qué desagregación

| Indicador | Nacional | Departamental | Municipal | Parcela |
|---|---|---|---|---|
| Superficie cultivada | SÍ | SÍ | Parcial (anuario MAG histórico) | **NO** |
| Producción | SÍ | SÍ | Parcial | **NO** |
| Rendimiento | SÍ (calculado) | SÍ | Parcial | **NO** |
| N.º de productores | SÍ | SÍ | **NO** publicado | **NO** |
| Variedades | SÍ (% del área en maíz) | **NO** | **NO** | **NO** |
| Destino (autoconsumo/venta) | SÍ | **NO** | **NO** | **NO** |
| Riego | SÍ | Parcial | **NO** | **NO** |
| Pérdidas poscosecha | No verificado | **NO** | **NO** | **NO** |

**Regla:** el CAP 2025 no publica microdatos (Ley Especial de Estadística y
Censos, art. 25, según la documentación del BCR). AGROSV **no infiere** datos
municipales ni de parcela a partir de agregados departamentales.

---

## 4. Sistemas de producción documentados

| Sistema | Descripción | Dónde se documenta |
|---|---|---|
| Milpa (maíz + frijol, a veces sorgo) | Asociación tradicional de subsistencia | Literatura nacional; CAP 2025 (cultivo combinado) |
| Monocultivo de maíz | Comercial y subsistencia | CAP 2025 |
| Café bajo sombra | Agroforestería | ISC, CENTA, MAG |
| Caña de azúcar | Plantación industrial | Ingenios, CAP 2025 |
| Producción en patio | Huertos familiares | CAP 2025 (sección 3 de la boleta) |
| Agricultura urbana y periurbana | Tecnificada y de traspatio | `docs/URBAN_AGRICULTURE.md` |

---

## 5. Vacíos que bloquean módulos

| Vacío | Bloquea | Severidad |
|---|---|---|
| Variedades locales con coeficientes de cultivo | Simulación por variedad (DSSAT) | **Alta** |
| Fechas de siembra por zona y año | Almanaque dinámico, ventanas | **Alta** |
| Rendimiento observado por parcela | Validación de modelos | **Alta** |
| Pérdidas poscosecha | Análisis económico | Media |
| Prácticas de manejo (fertilización real) | Modelos de N | Media |
| Paquetes tecnológicos por zona | Recomendaciones | Media |
| Costos desagregados por labor y maquinaria | Márgenes finos | Media |

---

## 6. Ruta de integración

1. **Extraer tablas del CAP 2025** (3 entregas) a CSV con referencia de página,
   revisión humana y control de totales contra el PDF.
2. **Extraer el anuario MAG 2021-2022** para series históricas y precios.
3. **Solicitar a CENTA** fichas técnicas de variedades y guías de manejo.
4. **Cruzar** el catálogo de cultivos con los parámetros de AquaCrop/DSSAT y
   marcar explícitamente qué está calibrado y qué no.
5. **No publicar** rendimiento potencial como rendimiento esperado.

---

## 7. Referencias internas

- `docs/CROP_SIMULATION_ENGINE.md` — modelos, contrato de simulación, validación.
- `docs/AGRICULTURAL_ECONOMIC_INTELLIGENCE.md` — costos y márgenes.
- `docs/CENSUS_DATA_MODEL.md` — esquema censal y confidencialidad.
- `docs/data_expansion/CROP_PARAMETERS_CATALOG.md` — parámetros por cultivo.
