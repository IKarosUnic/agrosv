# RISKS_AND_LIMITATIONS.md — AGROSV

**Versión:** 1.0 · **Fecha:** 2026-11-21

Escala de severidad: **Crítico** (invalida el proyecto o expone a responsabilidad legal) · **Alto** (degrada la utilidad científica) · **Medio** (coste o retraso) · **Bajo** (molestia gestionable).

---

## 1. Riesgos técnicos

| # | Riesgo | Sev. | Prob. | Impacto | Mitigación |
|---|---|---|---|---|---|
| T1 | **GDAL rompe la reproducibilidad.** Es dependencia de sistema con binarios frágiles; una versión distinta cambia resultados de reproyección. | Alto | Alta | Resultados no reproducibles | Entorno fijado con `conda-lock` o wheels; `gdal_version` registrado en cada manifiesto; CI con imagen Docker fija |
| T2 | **SoilGrids REST está caído.** Verificado: devuelve `null` con HTTP 200. | Alto | **Confirmado** | Pipeline silenciosamente vacío | Usar WebDAV. Validador que **falla** si una propiedad de suelo es nula |
| T3 | **Overpass público no soporta volumen.** Verificado: HTTP 502 por saturación. | Medio | Alta | Ingesta intermitente | Extracto Geofabrik local con osm2pgsql; Overpass solo para consultas puntuales |
| T4 | **Copernicus DEM 30 m restringido en CDSE** desde 28-jul-2026 | Medio | **Confirmado** | Fuente aparentemente disponible deja de funcionar | Usar AWS S3 (`copernicus-dem-30m`), verificado sin credenciales |
| T5 | **Migración de colección Sentinel-2** (`sentinel-2-l2a` → `sentinel-2-c1-l2a`) | Medio | Alta | Enlaces STAC obsoletos | `collection_id` como configuración, no constante |
| T6 | **CHIRPS v2 se apaga en dic-2026** | Medio | **Confirmado** | Serie histórica se congela | Nacer en v3; `product_variant` explícito |
| T7 | **Resolución insuficiente** (SoilGrids 250 m, CHIRPS 5,5 km) frente a parcelas de 0,5–2 ha | **Crítico** | **Confirmado** | Recomendaciones falsamente precisas | Declarar `resolucion_efectiva`; regla de no publicar más precisión que el insumo más grueso (`SCIENTIFIC_VALIDATION.md` §5) |
| T8 | **CHIRPS diario es desagregado de pentadas**, no observación diaria | **Crítico** | **Confirmado** | Análisis de extremos diarios inválidos | Análisis a escala pentadal/mensual; advertencia en toda salida diaria |
| T9 | Incompatibilidad de límites administrativos: capas geoBoundaries 2021 vs. 44 municipios de 2023 | Alto | **Confirmado** | Joins espaciales fallan o atribuyen mal | Tabla de correspondencia obligatoria (`AGENT_ROLES.md`, AGENTE 2) |
| T10 | **Costo del pipeline nacional** en 16 GB RAM | Medio | Media | Ejecuciones largas | Procesamiento por ventanas y lotes; Sentinel-2 nunca se almacena completo |
| T11 | Dependencia de Open-Meteo para ET0 | Medio | Media | Si cambia su licencia, se rompe el flujo | Archivo propio obligatorio; CDS como ruta alternativa |
| T12 | Divergencia entre dos implementaciones de AquaCrop (oficial vs. OSPy) | Alto | Media | Resultados no comparables | Usar **solo** la oficial 7.3; versión registrada por run |

---

## 2. Riesgos científicos

| # | Riesgo | Sev. | Impacto | Mitigación |
|---|---|---|---|---|
| C1 | **Confundir agentes sintéticos con evidencia.** Es el riesgo más grave del proyecto. | **Crítico** | Afirmaciones falsas sobre agricultores salvadoreños; daño reputacional e institucional | `synthetic=TRUE` propagado con test; texto obligatorio (`SCIENTIFIC_VALIDATION.md` §7.3); prohibición de lenguaje que implique observación |
| C2 | **Nemotron no contiene variables económicas.** Sin tamaño de finca, tenencia, ingreso, acceso a agua ni crédito, los agentes no pueden tener dotaciones sin inventarlas. | **Crítico** | Simulación económica sin base | Asignación desde censo con `dotacion_fuente` obligatorio; campo nulo declarado si no hay fuente |
| C3 | **Ausencia de estaciones meteorológicas de superficie verificadas.** Sin observación local, CHIRPS y ERA5 no tienen validación independiente. | Alto | Incertidumbre climática no cuantificable | Contraste entre productos; declarar la limitación; gestionar acceso a MARN/SNET |
| C4 | **Sin coeficientes genéticos locales calibrados**, DSSAT no es válido. | Alto | Modelo con apariencia de rigor sin validez | No usar DSSAT en Fase 1; AquaCrop con parámetros FAO documentados |
| C5 | **Validación solo agregada** (departamental), nunca por parcela. | Alto | No se puede afirmar precisión local | Declararlo; no hacer comparaciones intra-departamentales |
| C6 | **Sesgo de altitud en ERA5-Land** (celda de 11 km vs. relieve de 2.700 m) | Alto | Errores de °C en zonas altas | Corrección por lapse rate declarada como supuesto |
| C7 | **Sobreajuste en calibración** con 14 unidades de observación | Medio | Modelo que no generaliza | Máximo 2 parámetros ajustados; separación temporal y espacial |
| C8 | **Subrepresentación de identidades indígenas y afrodescendientes** (declarada por el editor) | Medio | Sesgo en la población de agentes | Documentar; no usar agentes para inferencias sobre esos grupos |
| C9 | **Independencia ocupación×educación** asumida por el editor | Medio | Correlaciones inexistentes en los datos | No analizar esa relación sin modelo propio declarado |
| C10 | **Español salvadoreño aproximado por LLM**, no corpus autorizado | Bajo | Texto narrativo no auténtico | No usar la narrativa como dato lingüístico |
| C11 | **Incertidumbre del modelo no cuantificable** con los datos disponibles | Alto | Se puede fingir cuantificarla | Declararla como no cuantificada; no asignarle un ±% |
| C12 | Contaminación de validación por circularidad (usar el mismo año para calibrar y validar) | Alto | Métricas infladas | Protocolo de separación temporal obligatorio |

---

## 3. Riesgos de datos y gobernanza

| # | Riesgo | Sev. | Impacto | Mitigación |
|---|---|---|---|---|
| D1 | **Sin API para estadística agrícola.** BCR y MAG publican PDF; el feed DCAT del geoportal BCR/CENTA devolvió 0 datasets. | Alto | Extracción manual; no automatizable | Extracción asistida con verificación humana; solicitar microdatos formalmente |
| D2 | **Nemotron puede cambiar de versión** (nuevo `sha`) | Medio | Resultados no reproducibles | Anclar a `68f6a21c…`; actualización = decisión explícita con re-ejecución |
| D3 | **Deriva de OpenStreetMap**: el `.pbf` cambia cada día | Bajo | Resultados no reproducibles | Guardar fecha de extracción; no usar `latest` en producción |
| D4 | **Doble fuente de verdad SQLite/PostGIS** | Alto | Divergencia silenciosa | SQLite solo como exportación de lectura, con test de coherencia |
| D5 | **Duplicación de datos** entre Zarr y PostGIS | Medio | Inconsistencia | Un dueño por dato; test de muestreo de 1.000 puntos |
| D6 | Datos de precio y costo solo en PDF, sin serie estructurada | Medio | Fase 2 bloqueada parcialmente | Extracción manual versionada; documentar el hueco |

---

## 4. Riesgos legales y de licencia

| # | Riesgo | Sev. | Detalle | Mitigación |
|---|---|---|---|---|
| L1 | **Licencia no declarada del Censo Agropecuario 2025 (BCR) y del Mapeo Digital de Suelos (CENTA).** | **Crítico** | No se localizó licencia de reutilización. Usar internamente es defendible; **redistribuir no lo es**. | Tratar como `RESTRICTED`; esquema `external_restricted`; consulta formal escrita antes de publicar derivados |
| L2 | **Google Weather API §21.1** prohíbe usar el contenido en *"a weather app or weather model whose primary purpose is to provide weather information"* | **Crítico** | AGROSV es parcialmente un modelo agroclimático | **No usar** como fuente núcleo. Solo capa efímera de UI, si acaso |
| L3 | **Google Weather API §21.2** exige borrar datos en 1 h / 24 h / 240 h / 30 días | **Crítico** | Incompatible con archivo histórico | Ídem L2 |
| L4 | **ODbL de OpenStreetMap** es *share-alike* sobre bases derivadas | Alto | Mezclar OSM con datos propietarios contamina el conjunto | Esquema PostGIS separado; exportación pública por esquema, nunca mezclada |
| L5 | **Copernicus DEM** exige aviso de atribución específico y literal | Medio | Omisión = incumplimiento de licencia | Texto de atribución almacenado en `registry.yaml` y renderizado en la UI |
| L6 | **Open-Meteo es CC BY 4.0 solo para uso no comercial**; el uso comercial exige plan pago | Alto | Si AGROSV se institucionaliza o comercializa, incumple | Presupuestar plan pago o migrar a CDS (gratuito, CC BY 4.0) para producción; nunca depender del nivel gratuito en producción |
| L7 | **Reidentificación** a partir de perfiles sintéticos | Bajo | Nemotron no expone nombres y excluye menores; riesgo declarado bajo por el editor | No intentar reidentificar; no cruzar con registros del RNPN |
| L8 | **Uso de datos de personas para simulación de comportamiento** | Medio | Aunque sintéticos, simulan decisiones de agricultores reales por distribución | Transparencia explícita; comité ético institucional antes de publicación |
| L9 | Atribución de CC BY 4.0 (SoilGrids, Nemotron, ERA5) | Medio | Omisión = incumplimiento | Atribución obligatoria en UI y en cada exportación |
| L10 | Publicar cifras sobre agricultores sin acuerdo institucional | Alto | Conflicto con MAG/CENTA/BCR | Iniciar conversación **antes** de la primera publicación, no después |

---

## 5. Riesgos económicos

| # | Riesgo | Sev. | Detalle |
|---|---|---|---|
| E1 | **Los datos núcleo son gratuitos.** El coste real es de ingeniería. | Bajo | No hay barrera económica de entrada: DEM, CHIRPS, SoilGrids, ERA5, OSM, Sentinel-2, Nemotron, AquaCrop = $0 |
| E2 | **Open-Meteo comercial** | Medio | Plan mensual fijo; **precio no verificado, no se asume**. Alternativa gratuita: CDS (CC BY 4.0) |
| E3 | **Google Weather API** | Medio | Precio por 1.000 llamadas **no verificado**. Irrelevante si se descarta por ToS |
| E4 | **CDSE/Sentinel Hub** cuotas de procesamiento | Bajo | Nivel gratuito suficiente para el volumen de SV; STAC+S3 evita el problema |
| E5 | **Horas de ingeniería** | Alto | Es el 100 % del coste. 7 agentes × 12 semanas es la estimación de Fase 1–2 |
| E6 | **Coste de oportunidad de la gestión institucional** | Alto | Meses de espera por permisos pueden paralizar la publicación, aunque no el desarrollo |
| E7 | **Almacenamiento y cómputo** | Bajo | ~1,2 GB y un equipo de 16 GB; coste marginal ~$0 |

---

## 6. Riesgo institucional (el más probable de todos)

**Riesgo:** AGROSV produce resultados técnicamente sólidos pero no puede publicarlos porque (a) los datos nacionales no tienen licencia de reutilización y (b) no hay acuerdo con las instituciones que los producen.

**Por qué es el más probable:** los riesgos técnicos tienen solución conocida y verificada en esta Fase 0. Este no.

**Mitigación, en orden:**

1. **Construir Fase 1 enteramente con datos abiertos.** DEM, SoilGrids, CHIRPS, ERA5, Sentinel-2, Nemotron. Ninguno requiere permiso. El sistema produce valor sin depender de nadie.
2. **Los datos nacionales entran como validación y mejora**, no como requisito de arranque.
3. **Iniciar la conversación institucional en la semana 1**, en paralelo al código, no al final.
4. **Separar esquemas** para que la publicación parcial sea posible: se puede publicar lo abierto aunque lo restringido no esté autorizado.
5. **Preparar el caso de uso para las instituciones** (no para AGROSV): qué obtiene el MAG/CENTA/BCR a cambio de abrir sus datos.

---

## 7. Limitaciones permanentes (no son riesgos, son restricciones)

Estas no se resuelven con esfuerzo. Se declaran y se diseñan alrededor.

| Limitación | Consecuencia | Qué se hace |
|---|---|---|
| SoilGrids 250 m ≈ 6,25 ha | No representa una parcela | Prior de paisaje; el mapa CENTA 1:50.000 es la vía de mejora |
| CHIRPS 0,05° ≈ 5,5 km | No resuelve la cadena volcánica | Declarar; pentadal; corregir por altitud con supuesto |
| CHIRPS diario desagregado | No es observación diaria | Análisis pentadal/mensual |
| ERA5-Land 0,1° ≈ 11 km | Sesgo en relieve | Lapse rate declarado |
| Sentinel-2 óptico y nubosidad | Revisita efectiva de semanas en lluviosa | Ventana nov–abr; SAR es la solución futura |
| Copernicus DEM es un **DSM** | Incluye vegetación y edificios | Declararlo; no usar como DTM |
| Nemotron sin variables económicas | Dotaciones son supuesto | `dotacion_fuente` obligatorio |
| Nemotron 17.957 agentes agrícolas vs. 401.101 productores de maíz | No es una muestra del universo de productores | Son universos distintos; declararlo |
| Nemotron: independencia ocupación×educación | Sin correlaciones | No analizarlas |
| Validación solo a escala departamental | Sin precisión por parcela | No prometerla |
| Incertidumbre del modelo no cuantificable | No hay banda de error del modelo | Declarar como no cuantificada |
| Sin coeficientes genéticos locales | DSSAT no viable | AquaCrop en Fase 1 |
| OSM no tiene cobertura agrícola (1.554 ways en todo el país) | No sirve para delimitar cultivos | Usar solo para vialidad/hidrografía/infraestructura |
| Catálogo de 44 municipios (2023) vs. capas de 2021 | Incompatibilidad de joins | Tabla de correspondencia |

---

## 8. Los cinco riesgos que deben vigilarse semanalmente

Si solo se puede vigilar cinco:

1. **C1 — agentes sintéticos presentados como evidencia.** Un desliz aquí destruye la credibilidad del proyecto completo.
2. **T7/T8 — publicar más precisión de la que los datos soportan.** Es el error que hace inútil un sistema científico: parecer exacto y estar equivocado.
3. **L1 — licencia de BCR/CENTA.** Puede impedir publicar todo lo que dependa de esos datos.
4. **C3 — ausencia de estaciones de superficie.** Sin esto, la parte climática no se puede validar de verdad.
5. **Institucional (§6).** El riesgo que hace fracasar proyectos técnicamente correctos.

---

## 9. Señales de alerta tempranas

Indicadores de que algo va mal antes de que sea evidente:

| Señal | Significado |
|---|---|
| Aparece un resultado sin `provenance_id` en un PR | El sistema de procedencia no está aplicado; los tests no cubren |
| Alguien pide "rellenar" un hueco de datos para avanzar | Está a punto de fabricarse un dato |
| Un texto generado contiene una cifra que no está en el `FactsBundle` | El validador de números no funciona |
| Se usa SoilGrids para hablar de "esta parcela" | Se está violando la regla de resolución |
| Se cita a los agentes como "agricultores" sin "sintéticos" | Riesgo C1 materializándose |
| Se activa un test con `skip` sin justificación | Erosión de la garantía de calidad |
| Se ejecuta DSSAT con coeficientes por defecto | Se está produciendo rigor aparente sin validez |

---

## 10. Riesgos de la ampliación (2026-11-21)

Se añaden a §1–§9. Ninguno reemplaza los existentes.

### 10.1 Institucionales y de acceso

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| CNR no autoriza reutilización de ortofoto/LiDAR | Alta | Alto (sin L2/L3 urbano) | Convenio con licencia escrita antes de invertir; piloto en un departamento |
| CENTA no entrega la geodatabase de suelos | Media | Alto (sin suelo medido) | Solicitud formal; mantener SoilGrids etiquetado como predicción |
| MARN sin servicios estables (geoportal 522) | Alta | Medio | Copia local con hash; PDF como referencia; vectorización declarada |
| CAP 2025 nunca publica municipios ni microdatos | Alta | Medio | Diseñar el sistema para nivel departamental; no prometer más |
| Cambio de autoridades o de prioridades | Media | Alto | Artefactos reproducibles; nada depende de un servidor ajeno |

### 10.2 Científicos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Presentar 250 m (SoilGrids) como suelo de parcela | Decisiones de fertilización erróneas | Etiqueta «predicción» + advertencia en API/UI |
| Mezclar AgERA5 (0,1°) y CHIRPS (0,05°) sin declarar | Falsa precisión | `GRID_DATA_SPECIFICATION.md` §4 |
| Confundir susceptibilidad con probabilidad | Mala evaluación de riesgo | `hazard_layer.layer_type` obligatorio |
| NDVI → «cultivo» | Sobreestimar superficie agrícola | Niveles L0–L3 y matriz de confusión |
| Microdatos CPV + catastro | Reidentificación | Prohibición explícita; publicación agregada por distrito |
| CAP preliminar usado como definitivo | Cifras que cambian | Campo `delivery` y aviso visible |

### 10.3 Legales y contractuales

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Google Weather: prohibición de almacenar/derivar | Uso indebido del servicio | Solo consulta en vivo; no alimenta índices ni capas |
| Licencias no declaradas (MAG, MARN, CNR, CENTA) | Redistribución no autorizada | No se redistribuyen originales; solo agregados con cita |
| ODbL contaminando derivados | Obligación de liberar la base | Aislamiento por almacén y por licencia |
| Datos personales en microdatos | Sanción legal | Agregación, supresión y no publicación de microdatos |

### 10.4 Técnicos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Volumen de LiDAR/ortofoto nacional | Almacenamiento y proceso fuera de alcance | Procesar por departamento piloto; no descargar todo |
| Zarr y COG duplicando la misma variable | Deriva y desorden | Zarr = análisis; COG = servicio; una sola fuente de verdad por variable |
| Series climáticas con huecos | Índices sesgados | `quality` por celda; no rellenar para publicar |
| Dependencia de `cdsapi` | Descargas fallidas | Reintentos, caché y registro de versión del dataset |

### 10.5 Limitaciones permanentes nuevas

1. **Sin estaciones de superficie verificadas**, el clima de AGROSV es
   consistente entre productos satelitales, no validado localmente.
2. **El catastro no es público masivo**: la inteligencia territorial a escala de
   parcela será siempre parcial.
3. **La agricultura urbana no es detectable de forma exhaustiva** con 10 m;
   requiere ortofoto y campo.
4. **El CAP 2025 no permitirá mapas municipales**: su nivel es departamental.
5. **Ningún mapa de amenaza del país está disponible hoy como capa GIS oficial**
   verificada en este entorno.

---

## 11. Riesgos de la Fase 2 (2026-11-21)

### 11.1 Riesgos científicos nuevos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Confundir contraste entre productos con validación | alto | etiqueta `consistency`, no `validated` |
| Presentar rendimiento potencial como esperado | alto | etiqueta obligatoria y rango p10–p90 |
| Umbrales agronómicos no calibrados para SV | medio | publicarlos como supuestos |
| Un «gemelo digital» que es un visor | alto | criterio de admisión de 4 puntos (Module H) |
| Escenarios climáticos leídos como pronóstico | alto | separación explícita en API y UI |

### 11.2 Riesgos de licencia nuevos

1. **AquaCrop no es BSD-3**: su `LICENSE` dice «All rights reserved» y exige
   solicitud para uso no comercial. Corregido en `DATA_SOURCE_REGISTRY.md` §8.1.
2. **DSSAT** es BSD-3 pero requiere registro.
3. **APSIM Next Gen**: uso general no comercial por 3 años.
4. **WorldClim 2.1 y GAEZ v4**: no comercial y sin redistribución.
5. **MODIS Terra** cesa el 2026-12-01; el pipeline debe migrar a VJ113A1/VJ213A1.
6. **PDF del MAG**: sin licencia declarada; solo agregados derivados con cita.

### 11.3 Riesgos de arquitectura

| Riesgo | Consecuencia | Mitigación |
|---|---|---|
| Auth no definido | bloquea D, L, H | aislar; no bloquear P1–P3 |
| Crecimiento de la API sin versión | rompe clientes | `/api/v1` con deprecación |
| Datos privados en caché pública | fuga | nunca cachear respuestas autenticadas |
| Orquestador artesanal | fallos silenciosos | manifiesto + hashes + reintentos |
| Sobrecarga de módulos | nada termina | P1 primero, un módulo por ciclo |

### 11.4 Riesgo de los agentes sintéticos

El mayor riesgo de la Fase 2 no es técnico: es que un perfil sintético se cite
como si describiera a un productor real. Mitigación: etiqueta visible, nota
metodológica y prohibición de publicar distribuciones como si fueran censales.

### 11.5 Limitaciones permanentes añadidas

1. Sin estaciones, sin microdatos y sin aforos, clima, rendimiento e hidrología
   quedan sin validación local.
2. La parcela declarada no tiene validez catastral.
3. La resolución de una alerta es la de su fuente, nunca la de la parcela.
4. La proximidad a un río no implica agua disponible legalmente.
5. Un LLM no calcula variables científicas en AGROSV.
