"""AGROSV — configuración central.

Ninguna ruta ni constante de proyección debe estar codificada en otro lugar.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Rutas -------------------------------------------------------------------
# AGROSV_ROOT permite ejecutar desde cualquier cwd (scripts, tests, api).
ROOT = Path(os.environ.get("AGROSV_ROOT", Path(__file__).resolve().parents[2]))

DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"

TERRITORY_DIR = PROCESSED / "territory"
TOPOGRAPHY_DIR = PROCESSED / "topography"
INFRA_DIR = PROCESSED / "infrastructure"
SOILS_DIR = PROCESSED / "soils"

TERRITORY_GPKG = TERRITORY_DIR / "territory.gpkg"
DEM_WGS84 = TOPOGRAPHY_DIR / "dem30_wgs84.tif"
SLOPE = TOPOGRAPHY_DIR / "slope_deg.tif"
ASPECT = TOPOGRAPHY_DIR / "aspect_deg.tif"
HILLSHADE = TOPOGRAPHY_DIR / "hillshade.tif"
RELIEF_CLASS = TOPOGRAPHY_DIR / "relief_class.tif"

INFRA_GPKG = INFRA_DIR / "infrastructure.gpkg"
SOILS_GPKG = SOILS_DIR / "soils.gpkg"
SOILS_RASTER_DIR = SOILS_DIR / "rasters"

# --- Sistemas de referencia --------------------------------------------------
# Justificación en docs/ADR-001-architecture-decisions.md
CRS_STORAGE = "EPSG:4326"   # geometrías: interoperabilidad, es el CRS de las fuentes
CRS_METRIC = "EPSG:32616"   # UTM 16N: cálculo de pendiente/aspecto en metros
CRS_EQUAL_AREA = "EPSG:6933"  # áreas y densidades (evita distorsión de Mercator)

# El extremo occidental del país (lon < -90.0) cae fuera del meridiano central
# de la zona 16N (-87). La distorsión de escala resultante a -90.2 es ~0.15%,
# aceptable para pendiente. Se documenta como supuesto en LIMITATIONS.md.
CRS_METRIC_NOTE = (
    "EPSG:32616 aplicado a todo el territorio. En el extremo oeste "
    "(lon -90.2) el factor de escala es ~1.0015 (error de pendiente ~0.15%), "
    "considerado despreciable frente a la incertidumbre vertical del DEM."
)

# --- Extensión de El Salvador -------------------------------------------------
# Derivada de ADM1 (no de ADM0, que incluye aguas territoriales).
SV_BOUNDS = (-90.1790975, 12.976046, -87.6351394, 14.4510488)
SV_AREA_KM2_REF = 21041.0  # superficie terrestre oficial (referencia de validación)
SV_AREA_TOLERANCE = 0.03   # ±3% admisible para el límite derivado

# --- DEM ----------------------------------------------------------------------
DEM_COLLECTION = "copernicus-dem-30m"
DEM_S3_BASE = "https://copernicus-dem-30m.s3.amazonaws.com"
# Convención de nombres de Copernicus DEM: el hemisferio va PEGADO al grado:
#   Copernicus_DSM_COG_10_N13_00_W090_00_DEM
DEM_TILE_TEMPLATE = (
    "{base}/Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
    "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif"
)
# Zona 1x1 grado que cubre El Salvador; se leen ventanas, no tiles completos.
DEM_TILE_GRID = {"lat": (13, 14), "lon": (-91, -90, -89, -88)}

# --- Atribución (obligatoria en UI y exportaciones, ver DATA_PROVENANCE.md) ---
ATTRIBUTION = {
    "geoboundaries": (
        "Límites administrativos: geoBoundaries (gbOpen), CC BY-SA 2.0, "
        "derivados de OpenStreetMap vía osm-boundaries.com."
    ),
    "copdem": (
        "Modelo digital de elevación: © DLR e.V. 2010-2014 y © Airbus Defence and "
        "Space GmbH 2014-2018, proporcionado bajo COPERNICUS por la Unión Europea "
        "y la ESA; todos los derechos reservados. Producto derivado (pendiente, "
        "aspecto, hillshade) calculado por AGROSV."
    ),
    "osm": (
        "Datos de infraestructura: © OpenStreetMap contributors, ODbL 1.0. "
        "Base de datos derivada sujeta a ODbL."
    ),
    "soilgrids": (
        "Propiedades del suelo: SoilGrids 2.0, ISRIC — World Soil Information, "
        "CC BY 4.0. Predicciones a 250 m; no son mediciones de laboratorio."
    ),
}

# --- Umbrales de calidad ------------------------------------------------------
MIN_VALID_GEOM_RATIO = 1.0     # ninguna geometría inválida tolerada
MAX_NODATA_RATIO_DEM = 0.05    # >5% de celdas sin dato dentro del país = fallo
MAX_NODATA_RATIO_SLOPE = 0.05

# Clases de relieve (pendiente en grados). Umbrales documentados en LIMITATIONS.
RELIEF_BREAKS = [
    (0, 2, "plano"),
    (2, 5, "suave"),
    (5, 12, "ondulado"),
    (12, 25, "quebrado"),
    (25, 45, "escarpado"),
    (45, 91, "muy_escarpado"),
]
RELIEF_PRONOUNCED_MIN_DEG = 12.0  # "relieve pronunciado" = quebrado o superior
