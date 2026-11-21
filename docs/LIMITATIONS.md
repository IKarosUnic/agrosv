# Limitaciones conocidas — AGROSV Fase 1

Este documento es parte del contrato de la fase: ninguna capa se presenta como
más precisa de lo que es. La API lo publica en `/api/limitations`.

## Territorio

1. **Los límites no son oficiales.** geoBoundaries es una compilación abierta;
   no sustituye la demarcación del Instituto Geográfico Nacional (CNR).
2. **ADM2 es histórica.** Los 272 polígonos corresponden a los municipios
   anteriores a la reforma de 2023. Los 44 municipios vigentes **no** están
   representados. Toda respuesta de `/api/territory/municipalities` incluye
   `official: false`.
3. **Cobertura ADM2 del 97,22 %.** El 2,78 % restante (583,3 km²) son
   principalmente cuerpos de agua y franja costera excluidos de los polígonos
   municipales (Jisquilisco 227,4 km²; Cerrón Grande 128,5; Ilopango 81,8;
   Coatepeque 25,2; Fonseca 28,7). No se rellenó con geometrías inventadas.
4. **10 municipios sin nombre** en la fuente; se marcan `quality=name-missing`.
5. **Área nacional 20.966,4 km²** (−0,35 % frente a 21.041 km² oficiales). La
   diferencia proviene de la generalización del límite, no de una corrección
   manual.

## Topografía

1. **El DEM es un DSM, no un DTM.** Incluye vegetación y edificaciones: en zonas
   boscosas la elevación del terreno puede quedar por debajo del valor del
   raster. La pendiente derivada hereda ese sesgo.
2. **Resolución efectiva 30 m (1 arcsec).** No hay información válida por
   debajo de esa escala; el zoom 14 del mapa interpola, no revela detalle.
3. **Exactitud vertical** del GLO-30: típicamente <4 m en error absoluto
   vertical (LE90) según la especificación del producto; no se dispone de
   puntos de control nacionales para verificarlo.
4. **Pendiente en UTM 16N para todo el país.** En el extremo occidental
   (lon −90,2°) el factor de escala es ~1,0015: error relativo de pendiente
   ~0,15 %, despreciable frente a la incertidumbre vertical.
5. **Pendiente por gradiente central de 30 m.** No es un algoritmo de Horn; en
   laderas muy suaves (<2°) el ruido del DSM domina la señal.
6. **Hillshade**: azimut 315° y altitud 45° son una convención de visualización,
   no una iluminación real ni una variable física.
7. **Bordes**: las celdas cuyo vecindario 3×3 toca nodata se marcan nodata; esto
   elimina una franja de ~1 celda en costas y fronteras.
8. **Nodata en el rectángulo envolvente ≈54 %** (mar y países vecinos). Dentro
   del país es 0,03 % en el DEM y 0,25 % en la pendiente.

## Infraestructura (OpenStreetMap)

1. **La cobertura es heterogénea.** OSM es colaborativo: la densidad de caminos
   rurales y pistas varía por departamento. **No es un censo vial** y no debe
   usarse para planificación sin contraste con MOP/CENTA.
2. **Red vial: 40.215 km totales** de los cuales 8.754 km son arteriales y
   colectoras. La cifra incluye pistas y senderos mapeados; la red oficial
   pavimentada es bastante menor. Solo se valida el orden de magnitud.
3. **Recorte fronterizo.** Las vías y ríos que cruzan la frontera se truncan en
   el límite; su longitud al otro lado no se contabiliza.
4. **Cuerpos de agua: 522,6 km² en 1.205 polígonos.** Los polígonos pequeños
   (charcas, estanques) están subrepresentados; los grandes embalses dependen
   del mapeo comunitario.
5. **Fechas.** El extracto tiene su propio `timestamp` OSM (registrado en
   `infrastructure_stats.json`); los datos cambian con cada actualización de
   Geofabrik.
6. **Licencia ODbL.** Cualquier obra derivada debe publicarse bajo ODbL y
   mantener la atribución; no es compatible con licencias cerradas.

## Suelos

1. **Son predicciones, no mediciones.** SoilGrids 2.0 es un modelo global de
   aprendizaje automático a 250 m; el error local puede ser grande y no
   representa variabilidad intra-parcela.
2. **Cobertura 97,4 % sobre tierra firme.** SoilGrids solo modela tierra: los
   cuerpos de agua interiores son nodata por diseño. Las celdas de 250 m que
   cruzan la costa o un cuerpo de agua no mapeado también pueden ser nodata.
3. **Textura coherente por construcción.** Arcilla+arena+limo suma 100 %
   porque provienen del mismo modelo; esa suma **no** es una validación externa.
4. **Profundidad agregada.** La media 0–30 cm ponderada por espesor no es una
   capa oficial de SoilGrids; es una derivación documentada de este proyecto.
5. **Sin calibración nacional.** No se ha comparado contra el Mapa Digital de
   Suelos del CENTA ni contra análisis de laboratorio. Debe preferirse la fuente
   nacional cuando se obtenga acceso.
6. **Unidades.** Se convierten a unidades agronómicas (pH, g/kg, %) y se declara
   el factor de escala en cada COG; leer el raster sin aplicar `scale` da el
   entero almacenado.

## Plataforma

1. **Sin base de datos espacial.** Las capas se leen por ventana desde
   GeoPackage/COG. Es adecuado para lectura y consulta puntual; no hay
   escritura concurrente ni edición multiusuario (ver ADR-001).
2. **Teselas generadas al vuelo.** Cada tesela cuesta una lectura de ventana;
   no hay caché en disco. Para tráfico alto haría falta un caché o teselado
   previo.
3. **Consultas puntuales por vecino más cercano.** No se interpola
   bilinealmente en `/elevation` ni en `/soils/point`.
4. **Idioma y alcance.** Interfaz en español; solo El Salvador. No hay
   autenticación ni datos personales.
5. **Rendimiento medido en este entorno** (8 vCPU, sin GPU): elevación puntual
   <80 ms, suelo puntual <200 ms, tesela <1,5 s, GeoJSON de departamentos
   ~90 KB. No se ha probado en dispositivos de gama baja reales.
