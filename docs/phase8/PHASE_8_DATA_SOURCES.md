# Fuentes de datos de Fase 8

## 1. Fuentes integradas y validadas localmente

| ID | Fuente / Institución | URL directa | Licencia | Cobertura geográfica y temporal | Estado | Archivo local / notas |
|---|---|---|---|---|---|---|
| `wfp_food_prices_slv` | WFP Food Prices for El Salvador (HDX / fuentes MAG) | https://data.humdata.org/dataset/wfp-food-prices-for-el-salvador | CC BY-IGO | El Salvador (14 mercados + promedio nacional); **2005-01-15 a 2026-10-15** (7,864 filas) | `INTEGRATED` | `data/standardized/economics/wfp_food_prices_slv.csv` (`1,042,431 B`, `Wholesale` y `Retail`) |
| `wfp_markets_slv` | WFP Markets El Salvador (HDX) | https://data.humdata.org/dataset/wfp-food-prices-for-el-salvador | CC BY-IGO | El Salvador (71 mercados georreferenciados) | `INTEGRATED` | `data/standardized/economics/wfp_markets_slv.csv` (`4,121 B`) |
| `osm_markets_slv` | OpenStreetMap El Salvador (`infrastructure.gpkg`) | https://www.openstreetmap.org/ | ODbL 1.0 | El Salvador (39 puntos `mercado` + red vial OSM) | `INTEGRATED` | `data/standardized/economics/osm_markets_slv.json` |
| `cap_2025_public_aggregates` | BCR — V Censo Agropecuario 2025 (agregados públicos preliminares) | https://www.bcr.gob.sv/ | Datos públicos agregados (microdatos restringidos art. 25 LEC) | Nacional y participaciones departamentales seleccionadas (`2024-05 / 2025-04`) | `VALIDATED` | `data/standardized/economics/cap_2025_public_aggregates.json` (`maize`, `beans`, `rice`, ganado) |
| `worldbank_agri_share` | Banco Mundial WDI (`AG.LND.AGRI.ZS`) | https://api.worldbank.org/v2/country/SLV/indicator/AG.LND.AGRI.ZS | CC BY 4.0 | Nacional, 1961–2024 | `INTEGRATED` | `data/samples/phase3/worldbank_slv/wb_agri_land_share_slv.json` |
| `nemotron_personas_sv` | NVIDIA `Nemotron-Personas-El-Salvador` | https://huggingface.co/datasets/nvidia/Nemotron-Personas-El-Salvador | CC BY 4.0 | 14 departamentos (363 filas agrícolas reales extraídas de 3,000 escaneadas) | `INTEGRATED` | `data/samples/phase3/nemotron_rows/nemotron_agricultural_corpus.json` |

## 2. Fuentes evaluadas pero NO integradas (accesibilidad y brechas)

| ID | Institución | URL | Variables esperadas | Restricción / motivo observado | Estado |
|---|---|---|---|---|---|
| `mag_anuarios_y_costos` | MAG El Salvador | https://www.mag.gob.sv/ | Costos de producción por cultivo, precios de insumos, anuarios | PDF maquetados sin serie tabular abierta; URL `2022-23` dio 404 | `ACCESS_PENDING` |
| `centa_boletines` | CENTA | https://www.centa.gob.sv/ | Coeficientes técnicos y costos recomendados | HTTP 403 a clientes automatizados | `RESTRICTED` |
| `faostat` | FAO | https://www.fao.org/faostat/ | Producción, precios al productor, comercio | API HTTP 521 / bulk HTTP 403 en auditoría | `UNAVAILABLE` |
| `worldbank_wdi_live` | World Bank | https://api.worldbank.org/ | Rendimiento de cereales y valor agregado agrícola | Timeout (>15–25 s) en consulta en vivo el 2026-11-22 | `UNAVAILABLE` |
| `bcr_comercio_exterior` | BCR | https://www.bcr.gob.sv/ | Importaciones y exportaciones por partida SAC | Portal interactivo sin descarga masiva tabular integrada | `ACCESS_PENDING` |
| `fao_giews_amis` | FAO | https://www.fao.org/giews/ | Alertas de precios y balances globales | Sin descarga tabular integrada | `DISCOVERED` |
| `cepal_iica_ifad_usda_comtrade` | CEPAL/IICA/IFAD/USDA/UN Comtrade | https://comtradeplus.un.org/ | Flujos comerciales y series macro | Requieren credenciales o extracción externa no integrada | `DISCOVERED` |
