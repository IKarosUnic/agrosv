# Agricultura multiescala: rural, periurbana y urbana

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Estado:** diseño metodológico; **no** hay clasificación automática en
producción.

Regla central: **no toda vegetación es cultivo**. Un píxel verde puede ser
parque, césped, matorral, bosque ribereño, huerto o cultivo abandonado. Cualquier
capa de «agricultura» que produzca AGROSV debe poder demostrar su exactitud y
declarar su nivel de confianza.

---

## 1. Los tres contextos

| Contexto | Definición operativa | Unidad típica | Fuente principal |
|---|---|---|---|
| **Rural** | Explotaciones fuera del suelo urbano, con superficie continua | Parcela/UPA | CAP 2025, Sentinel-2, OSM |
| **Periurbano** | Franja de transición urbano-rural, parcelas intercaladas con vivienda | Parcela pequeña | Sentinel-2, CNR (ortofoto), OSM, CPV 2024 |
| **Urbano** | Producción dentro del tejido urbano: patios, azoteas, solares, huertos comunitarios | Huerto/patio (<0,1 ha) | Ortofoto CNR, trabajo de campo, OSM |

La distinción **no** es administrativa: depende de la estructura del paisaje y
de la unidad de producción, no del límite municipal.

---

## 2. Qué se puede detectar con qué

| Objeto | Sentinel-2 (10 m) | Ortofoto CNR (≤1 m) | Campo | Censo |
|---|---|---|---|---|
| Parcela comercial > 1 ha | Sí, con series temporales | Sí | Verificación | Superficie departamental |
| Cultivo pequeño 0,5–1 ha | Parcial (píxeles mixtos) | Sí | Necesaria | No desagregado |
| Huerto familiar | No fiable | Sí, con interpretación | Necesaria | No desagregado |
| Agricultura en patio | No | Posible en ortofoto de alta resolución, con revisión manual | Imprescindible | Indicador indirecto |
| Vivero | No como clase propia | Sí | Sí | Rubro en CAP (departamental) |

Evidencia de los límites: en un estudio de 867 campos menores de 0,5 ha,
Sentinel-2 no aportó evidencia fiable del estado agrícola en el 10 % de los
campos; en paisajes urbanos intercalados, las técnicas estándar de teledetección
pueden no ser apropiadas. Por eso la ortofoto y el campo son requisito, no
mejora opcional.

---

## 3. Método por niveles de confianza

Se propone una escala explícita; cada polígono publicado lleva `confidence`.

| Nivel | Nombre | Cómo se obtiene | Qué se puede afirmar |
|---|---|---|---|
| **L0** | Vegetación | Índice de vegetación (NDVI) sobre Sentinel-2 | Solo «hay vegetación», nunca «hay cultivo» |
| **L1** | Candidato agrícola | Serie temporal + reglas espaciales (tamaño, forma, contexto) | «Compatible con uso agrícola»; requiere revisión |
| **L2** | Agrícola probable | L1 + contraste con ortofoto o cartografía CNR | «Probablemente agrícola», con fecha |
| **L3** | Verificado | L2 + verificación de campo o censo a la escala adecuada | «Agrícola verificado» en fecha y lugar |

**Publicación:** el mapa por defecto muestra L2 y L3; L0/L1 solo como capas de
diagnóstico, con leyenda que lo diga.

### 3.1 Flujo técnico propuesto

```
Sentinel-2 L2A (STAC CDSE, 10 m)
  → compuestos mensuales sin nubes (mediana)
  → NDVI / NDWI + textura + estacionalidad
  → segmentación (SLIC o segmentación por umbrales)
  → reglas espaciales: área mínima, compacidad, contexto urbano/rural
  → cruce con OSM (landuse=farmland, allotments, gardens) y CNR
  → etiqueta L1 / L2
  → muestreo estratificado + campo → matriz de confusión → L3
```

Referencia metodológica: protocolo CEOS/WGCV de validación de cobertura
(muestreo probabilístico, matriz de confusión, exactitud por clase y estimación
de área con intervalos de confianza).

---

## 4. Datos auxiliares y su papel

| Fuente | Uso | Límite |
|---|---|---|
| Sentinel-2 L2A | Detección y fenología | 10 m; píxeles mixtos; nubes |
| Ortofoto CNR | Delimitación de parcelas y patios | **RESTRICTED**: compra/convenio |
| OSM | Contexto (uso del suelo, caminos, edificaciones) | Cobertura desigual; no es censo |
| CPV 2024 | Hogares y viviendas por distrito, urbano/rural | No dice si un hogar cultiva |
| CAP 2025 | Superficie y productores por departamento | Sin desagregación espacial |
| CNR catastro | Límites de parcela | Por parcela, no masivo |

**Contraste, no verdad:** los totales censales sirven para comprobar el orden de
magnitud de la superficie detectada, no para asignar cultivos a polígonos.
Estudios comparables advierten que las unidades censales no coinciden con los
límites administrativos usados en el análisis y que las estadísticas no
permiten inferir la distribución espacial.

---

## 5. Agricultura urbana y periurbana: protocolo específico

1. **Base**: ortofoto de alta resolución (CNR) recortada por distrito urbano.
2. **Interpretación visual asistida**: solares con hileras, camas elevadas,
   invernaderos, árboles frutales en patio. Se digitaliza a mano con doble
   revisor; la discordancia se resuelve con una tercera revisión.
3. **Muestreo de campo**: mínimo 30 sitios por municipio piloto, estratificados
   por densidad de vegetación y tipo de barrio; registro fotográfico y
   geolocalización aproximada (no se publica la ubicación exacta de un hogar).
4. **Confidencialidad**: los polígonos de patio se publican **agregados por
   distrito** (conteo y superficie), no como geometrías identificables.
5. **Censo**: se usa para denominadores (hogares con patio) y para comparar
   prevalencia, nunca para etiquetar un polígono concreto.

---

## 6. Validación y métricas exigidas

| Métrica | Umbral para publicar L3 |
|---|---|
| Exactitud global | ≥ 0,85 |
| Exactitud de usuario (agricultura) | ≥ 0,80 |
| Exactitud de productor (agricultura) | ≥ 0,75 |
| Matriz de confusión | publicada con intervalos de confianza |
| Estimación de área | por clase, con error estándar |
| Revisión de campo | ≥ 30 sitios/municipio piloto |
| Concordancia entre revisores | κ ≥ 0,7 |

Sin matriz de confusión no hay capa L3. Una capa L1 se publica solo con la
etiqueta «candidato» y sin cifras de superficie.

---

## 7. Riesgos

1. **Falsa precisión**: presentar 10 m como si identificara patios. Mitigación:
   niveles de confianza y exclusión de L0/L1 del mapa principal.
2. **Estacionalidad**: un cultivo cosechado se ve como suelo desnudo; un barbecho
   como vegetación. Mitigación: series multitemporales, no una imagen.
3. **Confusión urbana**: árboles y césped en parques. Mitigación: contexto,
   textura y ortofoto.
4. **Privacidad**: identificar un huerto familiar. Mitigación: publicación
   agregada por distrito.
5. **Cobertura de nubes**: en la época lluviosa faltan observaciones.
   Mitigación: compuestos mensuales y declaración de huecos.
6. **Dependencia del CNR**: sin ortofoto no hay L2/L3 urbano; el módulo se
   limita a rural con Sentinel-2.

---

## 8. Entregables de la primera iteración

1. Capa L1 de candidatos agrícolas para **un departamento piloto**
   (Ahuachapán), con metodología y límites declarados.
2. Informe de exactitud con muestra de campo planificada (no inventada).
3. Comparación de superficie detectada contra CAP 2025 y anuario MAG, con
   diferencias explicadas.
4. Ninguna capa L3 hasta completar el muestreo.
