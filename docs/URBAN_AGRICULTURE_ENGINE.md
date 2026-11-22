# MODULE G — Urban and Periurban Agriculture Engine

**Versión:** 1.0 · **Fecha:** 2026-11-21 · **Estado:** diseñado, **no implementado**.

Extiende el análisis agrícola al espacio urbano y periurbano. **No** reemplaza
`URBAN_AGRICULTURE.md` (metodología de detección): este documento define el
**motor** que evalúa aptitud, recursos y productividad por superficie en esos
contextos.

Diferencia clave con el documento metodológico: allí se responde «¿dónde hay
agricultura?»; aquí, «¿qué se puede producir en este espacio y con qué
limitaciones?».

---

## 1. Objetos de análisis

| Objeto | Escala típica | Detección | Motor |
|---|---|---|---|
| Huerto familiar | 10–500 m² | ortofoto + campo | aptitud + agua + sol |
| Patio productivo | 5–100 m² | campo / ortofoto | aptitud acotada |
| Terraza agrícola | 50–2.000 m² | DEM + ortofoto | pendiente, erosión |
| Huerto comunitario | 100–5.000 m² | catastro/OSM + campo | aptitud + gobernanza |
| Hidroponía | < 100 m² | campo (no detectable) | parámetros de manejo |
| Invernadero | 100–5.000 m² | ortofoto (techo) | clima interior estimado |
| Vivero | 500–20.000 m² | ortofoto + censo | aptitud + mercado |
| Solar/terreno urbano | variable | catastro | aptitud + restricciones |

---

## 2. Variables de aptitud

| Variable | Fuente | Resolución | Estado |
|---|---|---|---|
| Espacio disponible | catastro CNR / ortofoto | parcela / 0,1–1 m | **RESTRICTED** |
| Exposición solar | DEM (pendiente/orientación) + sombra de edificios | 30 m / ortofoto | parcial |
| Temperatura | AgERA5 | 0,1° | **RESTRICTED** |
| Agua disponible | red, pozo, lluvia (CHIRPS) | 0,05° / punto | parcial |
| Suelo / sustrato | SoilGrids (predicción) o análisis | 250 m | **predicción** |
| Drenaje | DEM + pendiente | 30 m | **VERIFIED** |
| Restricciones urbanas | planes municipales | — | **UNAVAILABLE** |

**Advertencia de escala:** a 250 m, SoilGrids no describe un patio. En urbano,
el suelo se declara «sustrato manejado» salvo análisis propio; no se extrapola
la predicción global a una maceta.

---

## 3. Modelo de aptitud urbana

```
aptitud = f(radiación, agua, sustrato, espacio, drenaje, restricciones)
```

- **Radiación**: horas de sol estimadas por orientación y sombra (modelo
  geométrico simple, no simulación 3D de edificios).
- **Agua**: lluvia media mensual (CHIRPS) + fuente declarada.
- **Sustrato**: clase textural declarada; nunca inferida de SoilGrids a esa escala.
- **Espacio**: superficie mínima por cultivo (tabla de referencia).
- **Restricciones**: se declaran como `unknown` si no hay normativa cargada.

Salida: clases `apto`, `apto con manejo`, `limitado`, `no apto`, con la variable
limitante y su incertidumbre.

---

## 4. Cultivos compatibles y productividad

| Cultivo | Superficie mínima | Ciclo | Observación |
|---|---|---|---|
| Hortalizas de hoja | 1–2 m² | 30–60 d | alta rotación |
| Tomate/chile | 0,5–1 m²/planta | 90–150 d | requiere tutorado |
| Hierbas aromáticas | 0,3 m² | 60–90 d | contenedor |
| Frijol de patio | 2–5 m² | 70–90 d | fijación de N |
| Maíz de patio | 4–10 m² | 100–120 d | baja eficiencia por área |
| Frutales enanos | 4–9 m² | perenne | maceta grande |

Productividad: **rangos**, no cifras únicas. Se expresan kg/m²/año con el rango
de la literatura y la advertencia de que dependen del manejo.

---

## 5. Interfaz

```
POST /api/urban/aptitude
     {geometry, water_source, substrate, sun_hours}
GET  /api/urban/crops?aptitude_class=apto&area_m2=50
GET  /api/urban/productivity?crop=tomate&area_m2=20
GET  /api/urban/context?level=district&code=
```

Cada respuesta declara `soil_source`, `resolution`, `limitations` y
`confidence` (`baja` por defecto en urbano sin ortofoto).

---

## 6. Validación

| Prueba | Criterio |
|---|---|
| Unidades | m² y kg/m² explícitos; sin mezclar con ha |
| Coherencia | superficie mínima ≤ área evaluada |
| Radiación | horas de sol ≤ horas de día astronómicas |
| Agua | demanda estimada ≤ oferta declarada o se marca déficit |
| Confianza | urbano sin ortofoto ⇒ `confidence: baja` |
| No extrapolación | suelo nunca inferido de SoilGrids para área < 1 ha |

---

## 7. Limitaciones

1. Sin catastro ni ortofoto, la detección es descriptiva, no cartográfica.
2. El sombreado por edificios no se modela en 3D en Fase 2.
3. La productividad urbana tiene poca evidencia local; se usan rangos.
4. La hidroponía no se detecta por teledetección.
5. Los patios son privados: se publica agregado por distrito.

---

## 8. Dependencias y prioridad

Depende de: `URBAN_AGRICULTURE.md` (metodología), DEM, CHIRPS, catastro/ortofoto
(CNR). Habilita: Module H (gemelo digital de huerto), Module L (reportes).

**Prioridad:** baja-media. Se implementa después de la agricultura rural L2 y
solo con un municipio piloto que tenga ortofoto disponible.
