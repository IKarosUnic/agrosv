# PROJECT_VISION.md — AGROSV

**Versión:** 1.0 (Fase 0 — Investigación y arquitectura)
**Fecha:** 2026-11-21
**Estado:** entregable para revisión. No autoriza implementación.

---

## 1. Qué es AGROSV

AGROSV es una plataforma abierta de **inteligencia agrícola y simulación geoespacial** para El Salvador. Integra datos geográficos, topografía, suelos, estadística agrícola nacional, climatología histórica, modelos agronómicos deterministas y agentes sintéticos de agricultores.

AGROSV **no es un chatbot**. No responde preguntas en lenguaje natural como producto principal. Es un sistema computacional que produce:

- series y superficies de datos derivados, con procedencia verificable;
- resultados de modelos agronómicos con incertidumbre cuantificada;
- escenarios contrafactuales (sequía, costos, agua, pérdidas) reproducibles;
- poblaciones de agentes sintéticos que permiten estudiar heterogeneidad de respuestas.

La unidad de análisis es la **unidad productiva simulada**: un polígono o punto con un cultivo, una fecha de siembra, un perfil de suelo, una serie climática y un perfil económico.

---

## 2. Problema que atiende

El Salvador tiene ~21.041 km² y 14 departamentos. La agricultura de granos básicos es de pequeña escala y alta sensibilidad climática: el V Censo Agropecuario y I de Pesca 2025 (BCR) registra **401.101 productores de maíz** y **214.738 de frijol** para el ciclo mayo 2024 – abril 2025, con **293.458 manzanas** cosechadas de maíz y **~493.403 t** de producción.

Tres carencias concretas justifican la plataforma:

1. **Fragmentación de datos.** La información existe (BCR, MAG, CENTA, MARN, CNR) pero está en PDF, portales ArcGIS sin API documentada y hojas de cálculo dispersas. No hay una capa integrada y versionada.
2. **Resolución espacial insuficiente para decisiones locales.** Los productos globales disponibles (SoilGrids 250 m, CHIRPS 0,05°, ERA5 0,25°) tienen celdas mucho mayores que una parcela de 0,5–2 ha. Usarlos sin declarar esa limitación produce recomendaciones falsamente precisas.
3. **Ausencia de simulación contrafactual.** No hay forma de preguntar "¿qué pasa en Ahuachapán si la canícula se corre tres semanas?" con trazabilidad de supuestos.

---

## 3. Objetivos

### 3.1 Objetivo general
Construir infraestructura científica y computacional reproducible que permita simular escenarios agrícolas y climáticos a escala de unidad productiva en El Salvador, con procedencia completa de datos y separación estricta entre modelo determinista, estadístico, aprendizaje automático y agente generativo.

### 3.2 Objetivos específicos (ordenados por dependencia)

| # | Objetivo | Entregable verificable |
|---|---|---|
| O1 | Integrar geografía, topografía, suelos y clima en un almacén único versionado | Esquema PostGIS + catálogo de fuentes con hashes |
| O2 | Establecer una línea base agroclimática por unidad productiva | Serie 1981–presente de precipitación (CHIRPS), ET0 y temperatura (ERA5/ERA5-Land) recortada a El Salvador |
| O3 | Ejecutar balance hídrico y rendimiento potencial con un modelo agronómico determinista | AquaCrop 7.3 ejecutado en lote con parámetros derivados de textura |
| O4 | Cuantificar incertidumbre de entrada y de parámetros | Intervalos P10/P50/P90 por Monte Carlo sobre cuantiles SoilGrids |
| O5 | Vincular resultados biofísicos con estadística agrícola nacional | Comparación rendimiento simulado vs. rendimiento censal por departamento |
| O6 | Poblar agentes sintéticos con perfiles Nemotron y dotaciones económicas declaradas | Tabla `agents` con campo `synthetic=true` y linaje de cada atributo |
| O7 | Simular decisiones y pérdidas económicas bajo escenarios | Motor de escenarios con semilla registrada y salida auditable |
| O8 | Publicar resultados con procedencia y advertencias en cada cifra | API + visor con `provenance_id` en toda respuesta |

---

## 4. Alcance

### 4.1 Dentro del alcance (Fase 1)
- El Salvador continental, 14 departamentos, 44 municipios (reforma territorial 2023).
- Cultivos iniciales: **maíz, frijol, maicillo (sorgo), arroz** — los cuatro granos básicos del censo 2025. Café y caña quedan como extensión posterior (existen como clases CIIU en Nemotron y como rubros censales, pero requieren parámetros de cultivo perenne y modelo multi-anual).
- Resolución de trabajo: **departamento y municipio** para estadística; **pixel 250 m y polígono de parcela simulada** para biofísica.
- Ventana climática: 1981–presente (CHIRPS), 1950–presente (ERA5-Land).
- Operación por lotes y en un solo equipo (8–16 GB RAM, sin GPU).

### 4.2 Fuera del alcance (explícito)
- Predicción de precios de mercado o asesoría financiera.
- Recomendación de agroquímicos, dosis o variedades específicas.
- Identificación de parcelas o productores reales. AGROSV no georreferencia personas.
- Sustituir encuestas oficiales, censos o extensionismo del MAG/CENTA.
- Cobertura fuera de El Salvador (Centroamérica queda como diseño futuro, no implementación).
- Tiempo real operativo (nowcasting, alertas tempranas con SLA).

---

## 5. Principios de diseño (no negociables)

1. **Ningún modelo de lenguaje produce un número agronómico.** El LLM puede narrar, redactar y dar voz a un agente sintético; nunca calcula rendimiento, balance hídrico, pérdida económica ni probabilidad.
2. **Toda cifra publicada tiene procedencia.** Cada valor en la API lleva `provenance_id` que resuelve a: fuente, versión, fecha de descarga, licencia, resolución, transformación y hash.
3. **Separación de datos crudos y transformados.** `data/raw/` es inmutable y nunca se edita; `data/processed/` se reconstruye por script.
4. **La resolución se declara.** Ninguna salida se presenta con más precisión espacial que su fuente más gruesa (ver `SCIENTIFIC_VALIDATION.md` §5).
5. **Lo sintético se etiqueta.** Todo registro derivado de Nemotron lleva `synthetic=true` propagado hasta la salida final.
6. **Reproducibilidad obligatoria.** Semilla, versión de librería, versión de dataset y fecha de ejecución quedan registradas; un resultado sin eso es inválido.
7. **Prioridad a lo gratuito y abierto.** Ninguna dependencia paga es requisito para operar (ver `RISKS_AND_LIMITATIONS.md` §5).
8. **Escala por lotes, no por servicios.** El sistema debe correr completo sin clúster.

---

## 6. Limitaciones fundacionales (declaradas desde el día uno)

Estas limitaciones **no son defectos a corregir**, son restricciones del estado del arte y de los datos disponibles. Deben aparecer en la interfaz y en la API.

| Limitación | Consecuencia práctica |
|---|---|
| SoilGrids tiene 250 m de resolución | Un píxel ≈ 6,25 ha. No representa una parcela de 0,7 ha. Es un **prior de paisaje**, no un dato de parcela. |
| CHIRPS tiene 0,05° (~5,5 km) | No resuelve gradientes topográficos de la cadena volcánica. Además, el dato **diario es un desagregado de pentadas** (vía ERA5 o IMERG), no una observación diaria independiente. |
| ERA5 (0,25°) y ERA5-Land (0,1°) | Demasiado gruesos para relieve salvadoreño; requieren corrección por altitud declarada como supuesto. |
| Nemotron no contiene tenencia de tierra, tamaño de finca, ingreso, acceso a agua ni crédito | Las dotaciones económicas de los agentes **deben asignarse desde el censo** y declararse como supuesto, no como dato del perfil. |
| Nemotron asume independencia ocupación × educación dado departamento, edad y sexo | No se puede analizar correlación ocupación–educación dentro de los agentes sin introducir un modelo propio. |
| Cobertura satelital óptica | Sentinel-2 tiene revisita nominal de 5 días, pero en la estación lluviosa (mayo–octubre) la revisita efectiva se degrada a semanas. Noviembre–abril es la ventana útil para monitoreo óptico. |
| Datos de validación de rendimiento | Existen a escala departamental (BCR/MAG), no por parcela. La validación es **agregada**, no punto a punto. |
| Sin coeficientes genéticos locales calibrados | DSSAT no es viable en Fase 1: requiere coeficientes cultivar calibrados con ensayos locales que no están disponibles abiertamente. |

---

## 7. Criterio de éxito de la Fase 0

La Fase 0 se considera cumplida cuando:

- [x] Cada fuente tiene estado VERIFIED / DOCUMENTED / RESTRICTED / UNAVAILABLE / PENDING_VALIDATION con evidencia de la prueba realizada (`DATA_SOURCE_REGISTRY.md` §3).
- [x] Existe una arquitectura con justificación por dependencia y coste (`SYSTEM_ARCHITECTURE.md`).
- [x] Existe un flujo de datos con validación y almacenamiento (`DATA_PIPELINE.md`).
- [x] Existe metodología de validación e incertidumbre (`SCIENTIFIC_VALIDATION.md`).
- [x] Existe una hoja de ruta con criterios de aceptación (`IMPLEMENTATION_ROADMAP.md`).
- [x] Existen roles de agente con fronteras de escritura definidas (`AGENT_ROLES.md`).
- [x] Existen riesgos y limitaciones clasificados (`RISKS_AND_LIMITATIONS.md`).
- [x] Se identificó el primer módulo funcional a construir (§8).
- [ ] **Revisión humana aprobada** ← pendiente. Sin esto no se implementa.

---

## 8. Primer módulo funcional recomendado

**PAUP — Perfil Agroclimático de Unidad Productiva.**

Un pipeline determinista, sin LLM, que recibe:

```
{ polígono o punto, cultivo, fecha de siembra, escenario climático }
```

y devuelve, con procedencia completa:

1. elevación, pendiente, orientación (Copernicus DEM GLO-30);
2. propiedades de suelo con cuantiles Q05/Q50/Q95 (SoilGrids, y CENTA cuando esté disponible);
3. serie diaria de precipitación (CHIRPS) y ET0/temperatura (ERA5-Land vía Open-Meteo o CDS);
4. balance hídrico y rendimiento potencial (AquaCrop 7.3);
5. indicadores de estrés hídrico y de sequía (SPI/SPEI a 3 y 6 meses);
6. P10/P50/P90 del rendimiento por Monte Carlo de entradas.

**Por qué este y no otro:** es la unidad atómica de la que dependen los otros siete módulos del motor de simulación. Sin un PAUP confiable, la simulación económica de agentes no tiene sustrato biofísico y se convierte en narrativa. Es además verificable contra rendimiento censal departamental desde la primera iteración, lo que permite cerrar el ciclo científico antes de añadir complejidad.

Detalle en `IMPLEMENTATION_ROADMAP.md` §4.

---

## 9. Preguntas abiertas que bloquean la Fase 1

1. **Licencia de los datos del BCR y CENTA.** No se localizó una licencia explícita de reutilización para el Censo Agropecuario 2025 ni para el Mapeo Digital de Suelos. Sin claridad, AGROSV puede usar los datos internamente pero no redistribuirlos. Requiere consulta formal.
2. **Acceso a observaciones meteorológicas de superficie de El Salvador.** MARN/SNET operan la red nacional; no se verificó un servicio de descarga. Sin estaciones, CHIRPS y ERA5 no tienen validación local.
3. **Licencia de los datos de precio y costo de producción del MAG.** El "Informe anual sobre costos de producción" se publica como PDF; la reutilización no está declarada.
4. **Autorización institucional.** Si AGROSV va a publicar cifras sobre agricultores salvadoreños, conviene un acuerdo con MAG/CENTA/BCR antes de la primera publicación, no después.

Ninguna de estas cuatro se resuelve con código. Se resuelven con gestión institucional y deben iniciarse en paralelo a la Fase 1 técnica.
