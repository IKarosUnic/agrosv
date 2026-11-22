# AGRICULTURAL_ECONOMIC_DATA — AGROSV Fase 3

**Fecha:** 2026-11-22 · **Evidencia:** sondas propias.
El motor de cálculo está en [`../AGRICULTURAL_ECONOMIC_INTELLIGENCE.md`](../AGRICULTURAL_ECONOMIC_INTELLIGENCE.md);
aquí se inventarían las **fuentes de precio, costo y comercio**.

**Regla de oro:** todo precio debe llevar **fecha, unidad, moneda, plaza y
fuente**. Un precio sin esos cinco campos no entra a AGROSV.

---

## 1. Precios

| ID | Fuente | Producto | Frecuencia | Formato | Acceso | Estado |
|---|---|---|---|---|---|---|
| `mag_precios_diario` | MAG/DGEA — informe diario | Mayorista | Diaria | PDF | HTTP | **VERIFIED** (fases previas) |
| `mag_precios_semanal` | MAG/DGEA — informe semanal | Por plaza | Semanal | PDF | HTTP | **VERIFIED** (fases previas) |
| `mag_precios_mensual` | MAG/DGEA — informe mensual | Mayorista y consumidor | Mensual | PDF | HTTP | **VERIFIED** |
| `mag_precios_informe` | Página índice de informes | — | — | HTML + 48 PDF enlazados | 200 (126.087 B) | **VERIFIED** |
| `mag_insumos_guia` | MAG — guía anual de precios de insumos | Semillas, fertilizantes, agroquímicos | Anual | PDF | 200 (111.731 B) | **VERIFIED** |
| `bcr_cap_precios` | CAP 2025 | Precio recibido / destino | Por entrega | PDF/PPT | 200 | **VERIFIED** (agregado) |
| `defensoria_precios` | Defensoría del Consumidor — sondeo semanal | Canasta y hortalizas | Semanal | PDF | HTTP | **DOCUMENTED** |
| `faostat_prices` | FAOSTAT | Precios al productor | Anual | API/bulk | API 521; bulk 403 | **PENDING_VALIDATION** |
| `worldbank_pink` | Banco Mundial | Commodities internacionales | Mensual | XLSX/API | API 200 | **VERIFIED** (API) |

### 1.1 Evidencia concreta de precios MAG

```
GET https://www.mag.gob.sv/informe-mensual-de-precios-de-productos-agropecuarios
→ 200, 126.087 B, 48 enlaces .pdf (2020–2023)

GET https://www.mag.gob.sv/wp-content/uploads/2024/05/Informe-mensual-DICIEMBRE-2023.pdf
→ 200, 5.869.837 B, application/pdf
```

El boletín mensual contiene: promedio mensual, mínimo, máximo, moda, precio
promedio por kg, comparación con el mes anterior y con el mismo mes del año
anterior, y precios de insumos, maquinaria y comercio exterior. **Es un PDF
maquetado**: la extracción requiere parseo de tablas y verificación humana.

### 1.2 Estructura mínima de un registro de precio

```yaml
source_id: mag_precios_mensual
product: maíz blanco
market: La Tiendona
price_type: mayorista        # mayorista | consumidor | productor
value: 45.74
unit: USD/quintal            # o USD/kg, USD/caja, USD/unidad
currency: USD
date: 2023-12
page: 6
source_url: https://www.mag.gob.sv/wp-content/uploads/2024/05/Informe-mensual-DICIEMBRE-2023.pdf
retrieved_at: 2026-11-22
verification: manual
```

**Conversiones declaradas:** 1 quintal = 45,36 kg; 1 manzana = 0,6989 ha;
El Salvador usa USD desde 2001.

---

## 2. Costos de producción

| Componente | Fuente | Unidad | Estado |
|---|---|---|---|
| Semilla | Guía de insumos MAG | USD/ha o USD/mz | **VERIFIED** (documento) |
| Fertilizante | Guía de insumos MAG | USD/quintal, USD/ha | **VERIFIED** |
| Agroquímicos | Guía de insumos MAG | USD/ha | **VERIFIED** |
| Mano de obra | Informe anual de costos MAG | jornales/ha, USD/jornal | **VERIFIED** |
| Maquinaria y aperos | Guía de insumos / costos | USD/ha, USD/hora | **VERIFIED** |
| Transporte | Costos MAG / encuesta | USD/qq | Parcial |
| Riego (energía y agua) | Costos MAG + tarifa | USD/ha | Parcial |
| Costo financiero | Tasa de referencia BCR | % anual | **VERIFIED** (BCR) |

**Cobertura temporal verificada:** informes de costos 2019-20 a 2022-23. No se
localizó una edición posterior en esta ronda.

---

## 3. Comercio exterior

| Indicador | Fuente | Acceso | Estado |
|---|---|---|---|
| Exportaciones e importaciones agropecuarias | BCR — base de comercio exterior | Portal | **VERIFIED** |
| Balanza comercial por producto | BCR / anuario MAG | PDF | **VERIFIED** |
| Producción, oferta y demanda mundiales | USDA FAS PSD | Portal web | **VERIFIED** (portal) |
| Comercio por país y producto | FAOSTAT | API/bulk | **PENDING_VALIDATION** |
| Precios internacionales | Banco Mundial | API | **VERIFIED** |

**Limitación:** los valores de comercio del anuario MAG son agregados anuales;
no permiten reconstruir flujos por empresa ni por aduana.

---

## 4. Infraestructura de comercialización

| Elemento | Fuente | Estado |
|---|---|---|
| Mercados mayoristas (La Tiendona, plazas departamentales) | MAG — informe de precios | **VERIFIED** (nombres y plazas en PDF) |
| Centros de acopio de granos | CAP 2025 (3.ª entrega: capacidad de almacenamiento) | **VERIFIED** (agregado) |
| Plantas de beneficio de café | ISC / MAG | **RESTRICTED** (ISC 403) |
| Ingenios azucareros | CAP 2025 / industria | Parcial |
| Infraestructura vial rural | OSM | **VERIFIED** (capa de Fase 1) |

---

## 5. Vacíos

| Vacío | Impacto | Prioridad |
|---|---|---|
| Serie de precios en formato tabular (no PDF) | Automatización y series largas | **Alta** |
| Precios al productor por departamento | Márgenes reales | **Alta** |
| Costos 2023-24 en adelante | Actualidad del margen | Media |
| Precios de alquiler de tierra | Costo fijo relevante | Media |
| Salarios agrícolas por zona | Costo de mano de obra | Media |
| Márgenes de intermediación | Análisis de cadena | Media |
| Precios de insumos por marca y presentación | Costeo fino | Baja |

---

## 6. Ruta de integración

1. **Parsear el boletín mensual** de diciembre 2023 como piloto: 3 productos,
   verificación manual, referencia de página.
2. **Construir el esquema** `price_record` con los cinco campos obligatorios.
3. **Extraer la guía de insumos** 2023 y los costos 2022-23.
4. **Solicitar al MAG** series tabulares (CSV/XLSX); el PDF no es una base de datos.
5. **No calcular márgenes** con precios de años distintos sin deflactar ni
   declarar el desfase.

---

## 7. Evidencia reproducible

- `research/raw/phase3/probes_20261122_r3.json`: `mag_precios_informe`,
  `mag_insumos_guia`, `mag_boletin_precios_2023_12`, `mag_pdf_*`,
  `worldbank_api`, `worldbank_agri_share`, `faostat_api`, `faostat_bulk`,
  `usda_psd`, `bcr_agropecuario`.
- `data/samples/phase3/worldbank_slv/` — 14.891 B, indicador de superficie
  agrícola, para validar el patrón de consumo de API.
