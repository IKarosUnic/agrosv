# Plantillas de solicitud de datos externos

**Uso:** adaptar el texto, enviarlo por el canal institucional oficial y
conservar la respuesta. No se inventan correos, funcionarios ni plazos. Las
URLs de cada servicio están en `DATA_ACCESS_AND_ONBOARDING.md` y en
`backend/agrosv/onboarding/registry.py`.

Cada solicitud pide, como mínimo: diccionario de variables, unidades, método,
cobertura, fechas, licencia y formato. Sin esos metadatos el archivo no pasa el
validador.

---

## A. SNET/MARN — series diarias de estaciones

**Asunto:** Solicitud de series diarias de estaciones meteorológicas para
validación científica (AGROSV)

Estimados señores de la Dirección General del Observatorio de Amenazas y
Recursos Naturales:

Solicito, con fines de investigación no comercial, las series diarias de las
estaciones de la red nacional para el período [FECHA INICIO]–[FECHA FIN], con:

1. Identificador y nombre de estación, latitud, longitud y elevación.
2. Variables: precipitación (mm), temperatura máxima, mínima y media (°C),
   humedad relativa (%), velocidad del viento (m/s) y, si está disponible,
   ET0 (mm).
3. Una fila por estación, fecha y variable; valor vacío cuando no haya
   registro (no interpolar).
4. Banderas de control de calidad y motivo de ausencia.
5. Diccionario de variables, unidades y cambios de instrumento.
6. Condiciones de uso y texto de atribución.

Formato preferido: CSV UTF-8. Si la entrega es por estación, se acepta un
archivo por estación. Indíquenme el procedimiento, el costo si lo hubiera y el
plazo estimado.

Atentamente,
[NOMBRE, INSTITUCIÓN, CORREO, FECHA]

**Criterio de aceptación:** `station_series` válido; sin duplicados; unidad
exacta; coordenadas dentro de El Salvador.

---

## B. SNET/MARN — aforos y caudales

**Asunto:** Solicitud de registros de caudal y curvas de gasto

Solicito, para [ESTACIONES O CUENCAS], los registros de caudal medio diario
(m³/s) del período [FECHA INICIO]–[FECHA FIN], con:

1. Identificador de estación, río, cuenca y coordenadas.
2. Fecha, caudal y bandera de dato estimado/observado.
3. Curva de gasto vigente y sus cambios (fecha de validez).
4. Períodos sin registro, explicitados como vacíos.
5. Licencia y atribución.

Formato preferido: CSV UTF-8 con una fila por estación y fecha.

**Criterio de aceptación:** `gauging` válido; caudal no negativo; sin
duplicados estación-fecha; `basin_code` informado.

---

## C. MARN — cuencas y subcuencas oficiales

**Asunto:** Solicitud de capa vectorial oficial de cuencas y subcuencas

Solicito la capa oficial de cuencas y subcuencas de El Salvador en formato
vectorial (GeoJSON, GeoPackage o Shapefile), con:

1. Código oficial de cuenca/subcuenca y nombre.
2. Área oficial y sistema de referencia.
3. Nivel jerárquico y relación con la red hidrográfica.
4. Fecha de elaboración y escala.
5. Licencia y atribución.

Si la capa no es distribuible, solicito al menos la tabla de códigos, nombres
y áreas, y la referencia del mapa oficial.

**Criterio de aceptación:** `basins` válido; geometría poligonal válida;
códigos únicos; área declarada coherente con la geodésica.

---

## D. CENTA — Laboratorio de Suelos

**Asunto:** Solicitud de datos de muestras de suelo para calibración de
SoilGrids

Solicito, con fines de investigación, un extracto de resultados del Laboratorio
de Suelos para [MUNICIPIOS/CULTIVOS/PERÍODO], con:

1. Identificador de muestra anónimo (sin nombre del productor).
2. Fecha, latitud, longitud y profundidad (cm).
3. pH, materia orgánica (%), N total (%), P disponible (mg/kg), K, Ca y Mg
   intercambiables (cmol(+)/kg), CEC (cmol(+)/kg), textura (%) y CE (dS/m),
   según lo que exista.
4. Método analítico por variable y límite de detección.
5. Condiciones de uso, anonimización y atribución.

Formato preferido: CSV largo (muestra-variable), sin agregación previa. Si los
datos están sujetos a confidencialidad, propongo un convenio con variables
agregadas por municipio y sin identificación de productores.

**Criterio de aceptación:** `centa_samples` válido; método y profundidad
obligatorios; rangos físicos; sin duplicados muestra-variable-profundidad.

---

## E. CNR — vértices GNSS y bancos de marca

**Asunto:** Cotización y condiciones de puntos de control GNSS para evaluar el
error vertical del DEM

Solicito cotización y condiciones de uso de [N] puntos de control GNSS
distribuidos en [DEPARTAMENTOS], con:

1. Coordenadas, altura ortométrica (o elipsoidal + ondulación del geoide) y
   sistema/época de referencia.
2. Exactitud horizontal y vertical declarada.
3. Fecha de medición, marca o vértice y estado de monumentación.
4. Licencia de uso y restricciones de publicación.
5. Si la altura es elipsoidal, el modelo de geoide y su versión.

Indíquenme el arancel por vértice/banco de marca, el plazo y si la entrega
incluye certificado o ficha técnica.

**Criterio de aceptación:** `gnss` válido; altura ortométrica o
elipsoidal+ondulación; exactitudes positivas; coordenadas nacionales. Sin esto
no se publica una exactitud del DEM.

---

## F. Asamblea Legislativa — confirmación de la correspondencia 2023

La distribución ya se incorporó desde <https://www.asamblea.gob.sv/node/12806>.
Solo si se necesita una confirmación formal:

**Asunto:** Confirmación de la distribución de distritos del Decreto 762

Solicito confirmación de la lista de 262 distritos y su asignación a los 44
municipios del Decreto Legislativo N.° 762, vigente desde el 1 de mayo de 2024,
incluyendo nombres oficiales y cualquier feudo o corrección posterior.

**Criterio de aceptación:** `crosswalk` válido; 14/44/262; fechas de vigencia
coherentes.

---

## G. Diccionario mínimo que debe acompañar cualquier entrega

| Campo | Descripción |
|---|---|
| `source` | institución y unidad que entrega |
| `retrieved_at` | fecha de entrega |
| `license` | condiciones y atribución |
| `crs` | EPSG o datum/época |
| `units` | unidad por variable |
| `method` | instrumento o método analítico |
| `qc_flag` | observado, estimado, dudoso, ausente |
| `coverage` | estaciones/muestras y período |
| `known_gaps` | cortes, cambios de instrumento, huelgas |

Sin este diccionario el archivo se valida solo estructuralmente y **no** se
declara integrado.
