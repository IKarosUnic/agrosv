#!/usr/bin/env bash
# AGROSV — descarga reproducible de datos crudos.
#
# Todo se guarda en data/raw/ y NUNCA se mezcla con el código. Los archivos se
# verifican por tamaño mínimo; los hashes quedan en los manifiestos
# .provenance.json de cada capa procesada.
#
# Uso: bash scripts/download_data.sh [territory|dem|osm|soilgrids|all]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW="$ROOT/data/raw"
WHAT="${1:-all}"

mkdir -p "$RAW"/{geoboundaries,copdem30,osm,soilgrids}

fetch() {  # fetch <url> <destino> <bytes_minimos>
  local url="$1" dest="$2" min="${3:-1000}"
  if [[ -s "$dest" ]] && (( $(stat -c%s "$dest") >= min )); then
    echo "  ya existe: ${dest#$ROOT/} ($(stat -c%s "$dest") bytes)"
    return 0
  fi
  echo "  bajando: $url"
  curl -fsSL --retry 3 --max-time 600 -o "$dest" "$url"
  local size; size=$(stat -c%s "$dest")
  (( size >= min )) || { echo "ERROR: $dest tiene $size bytes (< $min)"; exit 1; }
}

territory() {
  echo "== Límites administrativos (geoBoundaries gbOpen, CC BY-SA 2.0)"
  for lvl in ADM0 ADM1 ADM2; do
    fetch "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/SLV/$lvl/SLV-$lvl.geojson" \
          "$RAW/geoboundaries/SLV-$lvl.geojson" 100000
  done
}

dem() {
  echo "== Copernicus DEM GLO-30 (AWS Open Data, ~30 m)"
  for lat in 13 14; do
    for lon in 091 090 089 088; do
      local name="Copernicus_DSM_COG_10_N${lat}_00_W${lon}_00_DEM"
      fetch "https://copernicus-dem-30m.s3.amazonaws.com/$name/$name.tif" \
            "$RAW/copdem30/$name.tif" 30000000
    done
  done
}

osm() {
  echo "== OpenStreetMap — extracto de El Salvador (Geofabrik, ODbL 1.0)"
  fetch "https://download.geofabrik.de/central-america/el-salvador-latest.osm.pbf" \
        "$RAW/osm/el-salvador-latest.osm.pbf" 20000000
}

soilgrids() {
  echo "== SoilGrids 2.0 (ISRIC, CC BY 4.0)"
  echo "  Las teselas 600x600 las descarga scripts/04_soils.py de forma selectiva:"
  echo "  solo las que cubren El Salvador (138 teselas de 7.692 por capa)."
  echo "  Descargar el VRT global completo sería ~27 GB innecesarios."
}

case "$WHAT" in
  territory) territory ;;
  dem)       dem ;;
  osm)       osm ;;
  soilgrids) soilgrids ;;
  all)       territory; dem; osm; soilgrids ;;
  *) echo "uso: $0 [territory|dem|osm|soilgrids|all]"; exit 1 ;;
esac

echo "listo. datos crudos en ${RAW#$ROOT/}"
