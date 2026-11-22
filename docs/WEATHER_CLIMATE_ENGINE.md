# Weather & Climate Engine — diseño

**Versión:** 1.0 · **Fecha:** 2026-11-21
**Estado:** diseño aprobado, **sin implementar**.

El motor es multicapa y separa explícitamente cuatro naturalezas de dato que no
pueden mezclarse: **pronóstico**, **reanálisis histórico**, **observación
satelital de precipitación** e **índices derivados**. Cada capa conserva su
fuente, resolución y licencia (ver `GRID_DATA_SPECIFICATION.md`).

---

## 1. Capas del motor

| Capa | Fuente | Resolución | Periodo | Estado de acceso | Licencia |
|---|---|---|---|---|---|
| L1 · Pronóstico puntual | Google Weather API | punto (modelo) | ahora–240 h | **RESTRICTED** (clave + facturación) | Google Maps Platform ToS |
| L2 · Reanálisis agrícola | AgERA5 (C3S) | 0,1° diario | 1979–presente | **RESTRICTED** (cuenta + API key CDS) | CC BY 4.0 |
| L3 · Reanálisis general | ERA5 (C3S) | ~31 km horario | 1940–presente | **RESTRICTED** (cuenta CDS) | CC BY 4.0 |
| L4 · Precipitación satelital | CHIRPS v3 | 0,05° diario | 1981–presente | **VERIFIED** (HTTP directo) | CC BY 4.0 / dominio público |
| L5 · Derivados AGROSV | cálculo propio | la del insumo | según insumo | — | obra derivada, atribución compuesta |

`VERIFIED`/`RESTRICTED` describen el canal hoy (sondas 2026-11-21), no la
calidad científica.

---

## 2. Por qué esta jerarquía y no una sola fuente

- **Google Weather** es el único con pronóstico operativo, pero sus políticas
  prohíben exportar, extraer o raspar el contenido y crear productos derivados;
  además, no se puede construir una app o modelo meteorológico cuyo propósito
  principal sea proveer información del tiempo. Por tanto: **se consulta en
  vivo, se muestra, no se almacena ni se usa como insumo de índices**.
- **AgERA5** es la fuente adecuada para agricultura: 0,1° diario, variables
  ajustadas a topografía y agregadas a día local, desde 1979.
- **ERA5** aporta contexto horario y variables que AgERA5 no incluye, a costa de
  resolución (~31 km).
- **CHIRPS v3** es la referencia de precipitación (0,05°, 1981–presente,
  GeoTIFF/NetCDF/COG; preliminar y final). CHIRPS v2 termina su producción
  después de diciembre de 2026: **se adopta v3 desde el inicio**.

---

## 3. Variables y derivados

| Variable | Fuente primaria | Derivados |
|---|---|---|
| Precipitación | CHIRPS v3 | acumulados 10/30/90 días, SPI-3/6/12 |
| Temperatura (2 m, mín/máx/media) | AgERA5 | días de calor/frío, amplitud térmica |
| Humedad relativa | AgERA5 | déficit de presión de vapor |
| Radiación solar | AgERA5 | — |
| Viento 10 m | AgERA5 | — |
| ET₀ | AgERA5 (o cálculo FAO-56) | demanda hídrica, balance climático |
| Sequía | CHIRPS + AgERA5 | SPI, SPEI, días secos consecutivos |
| Estrés hídrico | derivado | precipitación − ET₀ acumulada |

**ET₀**: si AgERA5 no la entrega directamente para la fecha requerida, se
calcula con FAO-56 Penman-Monteith y se marca `derived_from` con las variables
usadas. No se presenta como «dato de AgERA5».

---

## 4. Flujo de ingesta

```
[descarga programada]
  CHIRPS: HTTP directo (diario/pentadal/mensual)
  AgERA5/ERA5: cdsapi (petición por variable, año y bbox SV)
        │
        ▼
[validación]  rango físico · cobertura · fechas · checksum
        │
        ▼
[almacén]  data/raw/climate/<source>/  (inmutable, NetCDF/GeoTIFF original)
        │
        ▼
[normalización]  Zarr (time,y,x) por grid_id + COG mensual para el mapa
        │
        ▼
[derivados]  SPI/SPEI, acumulados, ET₀, anomalías
        │
        ▼
[manifiesto]  provenance_id, native_resolution, quality, uncertainty
```

Cadencia: CHIRPS diario (preliminar) y mensual (final); AgERA5 diario; ERA5
mensual para variables auxiliares. Ninguna descarga se repite si el archivo
existe y el checksum coincide.

---

## 5. Pronóstico (L1) — reglas de uso

1. Se consulta **por punto** (parcela, municipio, coordenada), nunca como
   descarga masiva.
2. **No se persiste** el contenido más allá de la respuesta en memoria; no se
   construyen series históricas con Google Weather.
3. **No alimenta** índices, modelos agronómicos ni capas derivadas.
4. La UI muestra la fuente y la hora de la consulta; si falla, se degrada a
   «sin pronóstico» sin inventar valores.
5. Requiere clave y facturación: es una dependencia **opcional**; AGROSV debe
   funcionar sin ella.
6. Cuota por defecto documentada por Google: 6.000 consultas/minuto. No se
   diseña nada que se acerque a ese límite.

---

## 6. Atribución obligatoria

- Copernicus (ERA5/AgERA5): «Generated using Copernicus Climate Change Service
  information [año]», visible.
- CHIRPS: «CHIRPS v3, Climate Hazards Center, UC Santa Barbara (CC BY 4.0)».
- Google Weather: «Fuente: Google Weather API» cuando se muestre en vivo.
- Los derivados declaran ambos linajes.

---

## 7. Validación

| Prueba | Método | Estado |
|---|---|---|
| Rango físico | precipitación ≥ 0; humedad 0–100 %; T −5…45 °C | Diseñada |
| Coherencia CHIRPS vs AgERA5 | correlación mensual por departamento; diferencias > 30 % se investigan | Diseñada |
| SPI | distribución gamma ajustada por mes; comparación con categorías MARN | Diseñada, **bloqueada** por falta de estaciones |
| ET₀ | contraste Penman-Monteith vs AgERA5 cuando ambas existan | Diseñada |
| Estaciones de superficie | requiere datos MARN/SNET | **BLOQUEADA** (sin acceso verificado) |

**Limitación mayor:** sin observaciones de superficie no se puede afirmar que
las series representen el clima local. Se declara desde el diseño, no al final.

---

## 8. Consultas del motor

```
GET /api/climate/forecast?lat=&lon=            → L1 en vivo (si hay clave)
GET /api/climate/series?lat=&lon=&var=&from=&to= → L2/L3/L4 por celda
GET /api/climate/aggregate?level=department&code=&var=&from=&to=
GET /api/climate/indices?index=spi3&level=department&code=&from=&to=
GET /api/climate/anomaly?var=precip&period=2025-05&baseline=1991-2020
```

Anomalías: se calcula contra una línea base declarada (por defecto 1991–2020)
y se informa la línea base en cada respuesta; sin ella, una «anomalía» no
significa nada.

---

## 9. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Google cambia ToS o precios | Pérdida de pronóstico | L1 es opcional; el resto no depende de ella |
| CDS exige API key y limita peticiones | Retraso en ingesta | Cola por variable/año; reintentos; caché local |
| CHIRPS v2 descontinuado | Series rotas | Adoptar v3 desde el inicio y documentar el corte |
| Mezclar resoluciones | Falsa precisión | `GRID_DATA_SPECIFICATION.md` §4 |
| Sin estaciones | Validación incompleta | Declarar y usar contraste entre productos |
| Datos preliminares presentados como finales | Decisión agrícola errónea | Campo `quality` + aviso en la UI |

---

## 10. Lo que el motor no hará

- No generará pronósticos propios ni «corregirá» a Google con modelos caseros.
- No asimilará datos ni producirá reanálisis.
- No almacenará contenido de Google Weather.
- No interpolará una celda de 0,25° a 30 m para simular precisión.
- No publicará un índice sin línea base, unidad y fuente.
