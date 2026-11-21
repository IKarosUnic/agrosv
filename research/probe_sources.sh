#!/usr/bin/env bash
# AGROSV — sonda reproducible de fuentes de datos (Fase 0).
#
# Reproduce LAS verificaciones registradas en DATA_SOURCE_REGISTRY.md.
# Solo lectura. No descarga datasets completos (con excepción de un tile DEM
# que se descarta a /dev/null). Sin credenciales.
#
# Uso:  bash research/probe_sources.sh
# Salida: informe en stdout; exit 0 si todas las sondas esperadas pasan.

set -uo pipefail

UA="AGROSV-research/0.1 (academic; +https://github.com/)"
BBOX_W=-90.2; BBOX_S=13.1; BBOX_E=-87.6; BBOX_N=14.5
LAT=13.69; LON=-89.22

pass=0; fail=0

# probe <nombre> <url> <esperado:ok|restricted> [metodo] [data]
probe() {
  local name="$1" url="$2" expect="${3:-ok}" method="${4:-GET}" data="${5:-}"
  local code size
  if [[ "$method" == "GET" ]]; then
    code=$(curl -sS -o /tmp/agrosv_probe.$$ -w '%{http_code}' -m 90 -L -A "$UA" "$url" 2>/dev/null)
  else
    code=$(curl -sS -o /tmp/agrosv_probe.$$ -w '%{http_code}' -m 90 -L -A "$UA" -X "$method" -H 'Content-Type: application/json' -d "$data" "$url" 2>/dev/null)
  fi
  size=$(wc -c < /tmp/agrosv_probe.$$ 2>/dev/null || echo 0)

  local verdict
  case "$expect" in
    ok)         [[ "$code" == 200 || "$code" == 206 ]] && verdict=PASS || verdict=FAIL ;;
    restricted) [[ "$code" == 401 || "$code" == 403 || "$code" == 405 ]] && verdict=PASS || verdict=FAIL ;;
    *)          verdict=FAIL ;;
  esac

  if [[ "$verdict" == PASS ]]; then pass=$((pass+1)); else fail=$((fail+1)); fi
  printf '%-4s %-34s HTTP %-4s %10s B  %s\n' "$verdict" "$name" "$code" "$size" "$url"
}

echo "=============================================================="
echo " AGROSV — sonda de fuentes  ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
echo "=============================================================="

echo
echo "-- Nemotron Personas El Salvador --"
probe nemotron-meta    "https://huggingface.co/api/datasets/nvidia/Nemotron-Personas-El-Salvador" ok
probe nemotron-parquet "https://huggingface.co/api/datasets/nvidia/Nemotron-Personas-El-Salvador/parquet" ok
probe nemotron-size    "https://datasets-server.huggingface.co/size?dataset=nvidia%2FNemotron-Personas-El-Salvador" ok
probe nemotron-card    "https://huggingface.co/datasets/nvidia/Nemotron-Personas-El-Salvador/raw/main/README.md" ok

echo
echo "-- Topografía: Copernicus DEM GLO-30 (via AWS, NO CDSE) --"
probe copdem30-tile \
  "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N13_00_W090_00_DEM/Copernicus_DSM_COG_10_N13_00_W090_00_DEM.tif" ok

echo
echo "-- Suelos: SoilGrids --"
# La API REST responde 200 pero devuelve valores null (servicio suspendido): se
# documenta como PENDING_VALIDATION, no como exito.
probe soilgrids-rest \
  "https://rest.isric.org/soilgrids/v2.0/properties/query?lon=${LON}&lat=${LAT}&property=phh2o&depth=0-5cm&value=mean" ok
echo "     ^ AVISO: si el cuerpo contiene \"mean\":null, la API esta DEGRADADA. Usar WebDAV."
probe soilgrids-webdav "https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_mean.vrt" ok
probe soilgrids-layers "https://files.isric.org/soilgrids/latest/data/phh2o/" ok

echo
echo "-- Clima: CHIRPS v3 --"
probe chirps-readme "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/readme.txt" ok
probe chirps-final  "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/" ok
probe chirps-rnl    "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/2025/" ok

echo
echo "-- Clima: ERA5 / Open-Meteo --"
probe cds-catalogue "https://cds.climate.copernicus.eu/api/retrieve/v1/processes" ok
# El catalogo es publico; el ENVIO de un trabajo exige token personal (RESTRICTED).
probe cds-jobs-auth "https://cds.climate.copernicus.eu/api/retrieve/v1/jobs" restricted
probe openmeteo-archive \
  "https://archive-api.open-meteo.com/v1/archive?latitude=${LAT}&longitude=${LON}&start_date=2024-01-01&end_date=2024-01-05&daily=precipitation_sum,temperature_2m_max,et0_fao_evapotranspiration&timezone=America%2FEl_Salvador" ok
probe openmeteo-forecast \
  "https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&daily=precipitation_sum&forecast_days=3" ok

echo
echo "-- Observacion satelital: Sentinel-2 (STAC + COG en S3) --"
probe s2-collection "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a" ok
probe s2-search "https://earth-search.aws.element84.com/v1/search" ok POST \
  "{\"collections\":[\"sentinel-2-l2a\"],\"bbox\":[-89.35,13.6,-89.1,13.8],\"datetime\":\"2025-01-01T00:00:00Z/2025-03-01T00:00:00Z\",\"limit\":2}"

echo
echo "-- Geografia: OSM --"
probe geofabrik-sv "https://download.geofabrik.de/central-america/el-salvador-latest.osm.pbf" ok
probe geoboundaries "https://www.geoboundaries.org/api/current/gbOpen/SLV/ADM1/" ok

echo
echo "-- Estadistica agricola nacional --"
probe mag-home     "https://www.mag.gob.sv/" ok
probe mag-anuario  "https://www.mag.gob.sv/wp-content/uploads/2022/12/Anuario-de-Estad%C3%ADsticas-Agropecuarias-2021-2022.pdf" ok
probe bcr-geoportal "https://agropecuario.bcr.gob.sv/" ok
probe bcr-cap-pdf  "https://censo2024.bcr.gob.sv/wp-content/uploads/tablas-geoportal/censoagro/Segunda_entrega_de_resultados_CAP_2025.pdf" ok

echo
echo "-- Modelos agronomicos --"
probe fao-aquacrop "https://www.fao.org/aquacrop/" ok
probe aquacrop-license "https://raw.githubusercontent.com/KUL-RSDA/AquaCrop/main/LICENSE" ok
probe dssat        "https://dssat.net/" ok

echo
echo "-- Restringidos (se espera 401/403/405; su ausencia de clave es intencional) --"
probe cdse-identity "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token" restricted

rm -f /tmp/agrosv_probe.$$
echo
echo "=============================================================="
printf ' RESULTADO: %d PASS / %d FAIL\n' "$pass" "$fail"
echo " Nota: PASS = el canal responde hoy. NO implica aptitud cientifica"
echo "       ni permiso de redistribucion. Ver DATA_SOURCE_REGISTRY.md secc. 5 y 6."
echo "=============================================================="
[[ $fail -eq 0 ]]
