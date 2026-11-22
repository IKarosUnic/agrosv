"""AGROSV — gobernanza científica de datos (Fase 5, §8).

Este módulo es la única fuente de verdad sobre **qué dato existe, de dónde
sale y qué se puede afirmar de él**. Los cinco motores de Fase 5 lo consultan
antes de publicar cualquier cifra.

Tres reglas que el módulo hace ejecutables:

1. **Un dataset no está disponible porque aparezca en un catálogo.** Toda
   fuente declara sus artefactos y `available` se calcula comprobando que los
   archivos existen y no están vacíos.
2. **Una variable ausente se declara ausente.** `UNAVAILABLE` enumera lo que
   un motor *podría* devolver y no devuelve, con el motivo y lo que haría
   falta. Ningún motor rellena ese hueco con una estimación silenciosa.
3. **Cada resultado viaja con su ficha**: identificador, fuente, URL, versión,
   fechas, CRS, resolución espacial y temporal, unidades, NoData, método,
   supuestos, incertidumbre y estado de validación.

La clase de dato (`DataClass`) separa observación, reanálisis, estimación
satelital, predicción modelada, derivado y simulado. No son intercambiables y
el motor que las mezcle debe declararlo.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .. import config as C
from ..science import registry as R

ENGINE_VERSION = "5.0.0"
ENGINES = {
    "territorial": "TerritorialEngine",
    "soil": "SoilEngine",
    "hydrology": "HydrologyEngine",
    "climate": "ClimateEngine",
    "environmental": "EnvironmentalInteractionEngine",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DataClass(str, Enum):
    """Clase de evidencia del valor. Se conserva hasta la respuesta final."""

    OBSERVED = "observed"            # medido o registrado (estación, censo, campo)
    REANALYSIS = "reanalysis"        # modelo asimilado con observaciones
    SATELLITE_ESTIMATE = "satellite_estimate"
    MODELED_PREDICTION = "modeled_prediction"  # predicción espacial (SoilGrids, DEM)
    DERIVED = "derived"              # aritmética determinista de otra clase
    FORECAST = "forecast"
    CLIMATE_PROJECTION = "climate_projection"
    SIMULATED = "simulated"          # modelo de proceso con supuestos declarados


NON_OBSERVED = frozenset({
    DataClass.REANALYSIS, DataClass.SATELLITE_ESTIMATE,
    DataClass.MODELED_PREDICTION, DataClass.FORECAST,
    DataClass.CLIMATE_PROJECTION, DataClass.SIMULATED,
})


class SourceUnavailableError(RuntimeError):
    """Se pidió una fuente cuyos artefactos no están presentes."""

    def __init__(self, source_id: str, missing: Iterable[str], note: str = "") -> None:
        missing = list(missing)
        super().__init__(
            f"fuente '{source_id}' no disponible: faltan {missing or 'artefactos'}"
            + (f" — {note}" if note else "")
        )
        self.source_id = source_id
        self.missing = missing


@dataclass
class DataSource:
    """Ficha de una fuente según §8. Los campos vacíos se declaran, no se rellenan."""

    dataset_id: str
    name: str
    institution: str
    source_url: str
    version: str | None
    acquisition_date: str | None
    processing_date: str | None
    crs: str | None
    spatial_resolution: str
    positional_accuracy: str | None
    temporal_coverage: str
    temporal_resolution: str
    units: dict[str, str]
    nodata: Any
    data_class: DataClass
    methodology: str
    assumptions: list[str]
    uncertainty: str
    validation_status: str
    license: str
    redistribution_allowed: bool
    geographic_coverage: str
    artifacts: list[Path]
    known_limitations: list[str] = field(default_factory=list)
    layer: str | None = None       # nombre de capa en manifiestos de Fase 1/2
    variables: list[str] = field(default_factory=list)

    # --- disponibilidad -----------------------------------------------------
    def missing_artifacts(self) -> list[str]:
        return [str(p) for p in self.artifacts
                if not Path(p).exists() or Path(p).stat().st_size == 0]

    @property
    def available(self) -> bool:
        return bool(self.artifacts) and not self.missing_artifacts()

    def provenance_id(self) -> str | None:
        """Identificador de versión del manifiesto que corresponda al artefacto."""
        if not self.layer:
            return None
        try:
            for ds in R.catalog():
                if ds.layer == self.layer:
                    return ds.provenance_id or ds.dataset_version
        except Exception:  # noqa: BLE001 — el catálogo es opcional
            return None
        return None

    def artifact_digest(self) -> str | None:
        """sha256 corto del primer artefacto: permite detectar cambios de fuente."""
        if not self.artifacts:
            return None
        p = Path(self.artifacts[0])
        if not p.exists() or not p.is_file():
            return None
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "institution": self.institution,
            "source_url": self.source_url,
            "version": self.version,
            "acquisition_date": self.acquisition_date,
            "processing_date": self.processing_date,
            "crs": self.crs,
            "spatial_resolution": self.spatial_resolution,
            "positional_accuracy": self.positional_accuracy,
            "temporal_coverage": self.temporal_coverage,
            "temporal_resolution": self.temporal_resolution,
            "variables": self.variables,
            "units": self.units,
            "nodata": self.nodata,
            "data_class": self.data_class.value,
            "methodology": self.methodology,
            "assumptions": self.assumptions,
            "uncertainty": self.uncertainty,
            "validation_status": self.validation_status,
            "license": self.license,
            "redistribution_allowed": self.redistribution_allowed,
            "geographic_coverage": self.geographic_coverage,
            "known_limitations": self.known_limitations,
            "artifacts": [str(p.relative_to(C.ROOT)) if str(p).startswith(str(C.ROOT))
                          else str(p) for p in self.artifacts],
            "available": self.available,
            "missing_artifacts": self.missing_artifacts(),
            "provenance_id": self.provenance_id(),
            "artifact_digest": self.artifact_digest(),
        }
        return payload


# --- Fuentes realmente presentes en este repositorio -------------------------
_COPDEM = [
    C.DEM_WGS84, C.SLOPE, C.ASPECT, C.HILLSHADE, C.RELIEF_CLASS,
]
_TERRITORY = [C.TERRITORY_GPKG]
_INFRA = [C.INFRA_GPKG]
_SOIL_RASTERS = {
    "clay": C.SOILS_RASTER_DIR / "clay_0-30cm.tif",
    "sand": C.SOILS_RASTER_DIR / "sand_0-30cm.tif",
    "silt": C.SOILS_RASTER_DIR / "silt_0-30cm.tif",
    "ph": C.SOILS_RASTER_DIR / "phh2o_0-30cm.tif",
    "soil_organic_carbon": C.SOILS_RASTER_DIR / "soc_0-30cm.tif",
    "soil_nitrogen": C.SOILS_RASTER_DIR / "nitrogen_0-30cm.tif",
}
_STORE = C.DATA / "validated" / "agrosv_data.sqlite"

_SOURCES: dict[str, DataSource] = {
    "copdem30": DataSource(
        dataset_id="copdem30",
        name="Copernicus DEM GLO-30 (DSM) y derivados topográficos",
        institution="ESA / Airbus Defence and Space / DLR (distribuido por Copernicus)",
        source_url="https://copernicus-dem-30m.s3.amazonaws.com/",
        version="GLO-30 (release 2021)",
        acquisition_date="2021",
        processing_date="2026-11-21",
        crs="EPSG:4326 (DEM); EPSG:32616 (pendiente, aspecto, hillshade, clase)",
        spatial_resolution="1 arcosegundo (~30 m en el ecuador; ~30,9 m en 13,7° N)",
        positional_accuracy=(
            "no verificada en este repositorio: el producto declara exactitud "
            "vertical de orden métrico, pero AGROSV no dispone de puntos de control"
        ),
        temporal_coverage="estático (modelo de superficie de una adquisición)",
        temporal_resolution="estático",
        units={"elevation": "m", "slope": "deg", "aspect": "deg",
               "relief_class": "class"},
        nodata=-32768.0,
        data_class=DataClass.MODELED_PREDICTION,
        methodology=(
            "DEM Copernicus GLO-30 (DSM, no DTM: incluye vegetación y edificios). "
            "Pendiente y aspecto por diferencias finitas centrales sobre rejilla "
            "métrica de 30 m (EPSG:32616); clases de relieve por umbrales "
            "documentados en config.RELIEF_BREAKS."
        ),
        assumptions=[
            "el DSM no es el terreno desnudo: la pendiente bajo dosel puede estar "
            "sobreestimada",
            "EPSG:32616 para todo el país: en el extremo oeste el factor de escala "
            "es ~1,0015 (±0,15 % en pendiente)",
            "resolución de 30 m ≠ exactitud posicional de 30 m",
        ],
        uncertainty=(
            "no cuantificada con puntos de control; la resolución no se usa como "
            "medida de precisión"
        ),
        validation_status="V1 (consistencia interna: rangos y cobertura)",
        license="Copernicus DEM (DLR/Airbus) — uso libre con atribución",
        redistribution_allowed=True,
        geographic_coverage="El Salvador (recorte nacional, 12,98–14,45° N)",
        artifacts=_COPDEM,
        known_limitations=[
            "DSM incluye edificios y dosel",
            "no resuelve obras hidráulicas ni cauces menores",
            "exactitud vertical no validada localmente",
        ],
        layer="dem30_wgs84",
        variables=["elevation", "slope", "aspect", "relief_class"],
    ),
    "geoboundaries_adm1": DataSource(
        dataset_id="geoboundaries_adm1",
        name="Límites administrativos ADM0/ADM1/ADM2 (geoBoundaries gbOpen)",
        institution="geoBoundaries (William & Mary geoLab), derivado de OpenStreetMap",
        source_url="https://www.geoboundaries.org/",
        version="gbOpen (fecha de compilación en manifiesto de capa)",
        acquisition_date="2026-11-21",
        processing_date="2026-11-21",
        crs="EPSG:4326",
        spatial_resolution="vectorial; generalización no declarada por el proveedor",
        positional_accuracy=(
            "no verificada: los límites derivados de OSM pueden diferir del "
            "límite legal; ADM0 incluye aguas territoriales y se descartó"
        ),
        temporal_coverage="instantánea de la compilación; no es una serie",
        temporal_resolution="estático",
        units={"area": "km2"},
        nodata=None,
        data_class=DataClass.OBSERVED,
        methodology=(
            "ADM0 derivado por disolución de ADM1 (el ADM0 del proveedor incluye "
            "~4.373 km² de aguas territoriales). Áreas calculadas en EPSG:6933."
        ),
        assumptions=[
            "ADM2 (272 polígonos) es la división anterior a la reforma de 2023: "
            "histórica y marcada official=false",
        ],
        uncertainty="no cuantificada; discrepancia de área nacional −0,35 % frente a 21.041 km²",
        validation_status="V1 (integridad geométrica y cobertura)",
        license="CC BY-SA 2.0",
        redistribution_allowed=True,
        geographic_coverage="El Salvador: 14 departamentos, 272 municipios históricos",
        artifacts=_TERRITORY,
        known_limitations=[
            "no hay límites municipales 2023 ni distritos en el repositorio",
            "un límite administrativo no coincide con una cuenca",
        ],
        layer="territory_meta",
        variables=["territory_id", "area"],
    ),
    "osm_sv": DataSource(
        dataset_id="osm_sv",
        name="OpenStreetMap — red hidrográfica y cuerpos de agua (extracto Geofabrik)",
        institution="OpenStreetMap contributors (extracto Geofabrik)",
        source_url="https://download.geofabrik.de/central-america/el-salvador.html",
        version="extracto con marca temporal OSM",
        acquisition_date="2026-11-21",
        processing_date="2026-11-21",
        crs="EPSG:4326",
        spatial_resolution="vectorial; precisión heterogénea según colaborador",
        positional_accuracy=(
            "desconocida por elemento: OSM no publica exactitud; no es cartografía "
            "oficial de cauces"
        ),
        temporal_coverage="instantánea del extracto",
        temporal_resolution="estático (se actualiza con el extracto)",
        units={"length": "m"},
        nodata=None,
        data_class=DataClass.OBSERVED,
        methodology=(
            "clasificación de etiquetas OSM (waterway=river/stream/canal, "
            "natural=water) y recorte al límite ADM1"
        ),
        assumptions=[
            "un cauce mapeado no es un cauce con caudal permanente",
            "la ausencia de un cauce en OSM no implica que no exista",
        ],
        uncertainty=(
            "no cuantificada; exhaustividad y posición dependen de la comunidad"
        ),
        validation_status="V1 (integridad geométrica)",
        license="ODbL 1.0",
        redistribution_allowed=True,
        geographic_coverage="El Salvador (cobertura desigual)",
        artifacts=_INFRA,
        known_limitations=[
            "cobertura incompleta y sesgada hacia zonas accesibles",
            "no hay aforos ni régimen de caudal",
        ],
        layer="infrastructure",
        variables=["waterways", "water_bodies"],
    ),
    "soilgrids_2": DataSource(
        dataset_id="soilgrids_2",
        name="SoilGrids 2.0 — propiedades 0–30 cm",
        institution="ISRIC — World Soil Information",
        source_url="https://files.isric.org/soilgrids/latest/data/",
        version="SoilGrids 2.0 (2020)",
        acquisition_date="2026-11-21",
        processing_date="2026-11-21",
        crs="EPSG:32616 (reproyectado desde Interrupted Goode Homolosine)",
        spatial_resolution="250 m (predicción); remuestreo a 250 m desde la malla nativa",
        positional_accuracy=(
            "soporte de 250 m; el error del modelo no es de 250 m y no se declara "
            "por celda"
        ),
        temporal_coverage="estático (predicción de una compilación de perfiles)",
        temporal_resolution="estático",
        units={"clay": "%", "sand": "%", "silt": "%", "ph": "", 
               "soil_organic_carbon": "g kg-1", "soil_nitrogen": "g kg-1"},
        nodata=-32768.0,
        data_class=DataClass.MODELED_PREDICTION,
        methodology=(
            "predicción espacial (machine learning) de SoilGrids 2.0, media "
            "ponderada 0–30 cm (5/30, 10/30, 15/30). Valores almacenados como "
            "enteros con escala declarada (pH 0,1; SOC/N 0,1/0,01; textura 0,1)."
        ),
        assumptions=[
            "predicción global: no sustituye una muestra de laboratorio",
            "la profundidad disponible es 0–30 cm; no hay perfiles por horizonte",
            "media 0–30 cm no es una propiedad de una capa específica",
        ],
        uncertainty=(
            "no cuantificada por celda en este repositorio; SoilGrids publica "
            "intervalos por cuantiles que no se descargaron"
        ),
        validation_status="V1 (rango y cobertura interna)",
        license="CC BY 4.0",
        redistribution_allowed=True,
        geographic_coverage="El Salvador; cobertura 97,4 % de tierra firme",
        artifacts=[Path(p) for p in _SOIL_RASTERS.values()],
        known_limitations=[
            "no es medición de laboratorio",
            "solo 0–30 cm",
            "no incluye CEC, densidad aparente, fragmentos gruesos, salinidad ni "
            "capacidad de agua disponible",
        ],
        layer="phh2o_0-30cm",
        variables=["clay", "sand", "silt", "ph", "soil_organic_carbon", "soil_nitrogen"],
    ),
    "nasa_power_point": DataSource(
        dataset_id="nasa_power_point",
        name="NASA POWER — serie diaria en un punto (13,70° N, 89,20° O)",
        institution="NASA Langley Research Center (POWER / MERRA-2)",
        source_url="https://power.larc.nasa.gov/",
        version="v2.10.5 (declarado por fila)",
        acquisition_date="2026-11-22",
        processing_date="2026-11-22",
        crs="EPSG:4326 (punto)",
        spatial_resolution="celda 0,5° × 0,625° (MERRA-2)",
        positional_accuracy=(
            "representatividad de celda de ~55 × 69 km, no de punto: no es una "
            "estación"
        ),
        temporal_coverage="2019-01-01 a 2025-12-31",
        temporal_resolution="diaria (suma para precipitación; máximo/mínimo para temperatura)",
        units={"precipitation": "mm", "temperature": "degC"},
        nodata=None,
        data_class=DataClass.REANALYSIS,
        methodology=(
            "reanálisis asimilado; días en hora solar local convertidos a UTC−6 "
            "según la base declarada por el proveedor"
        ),
        assumptions=["un punto no representa el país", "reanálisis ≠ observación"],
        uncertainty=(
            "no validada contra estaciones; la intercomparación con Open-Meteo es "
            "una comparación entre productos, no una validación"
        ),
        validation_status="V1 (integridad temporal; sin validación externa)",
        license="NASA POWER — datos abiertos, uso con atribución",
        redistribution_allowed=True,
        geographic_coverage="una coordenada (13,70° N, 89,20° O); no es cobertura nacional",
        artifacts=[_STORE],
        known_limitations=[
            "un solo punto para todo El Salvador",
            "reanálisis de celda gruesa",
            "sin estaciones de contraste",
        ],
        layer=None,
        variables=["precipitation", "temperature"],
    ),
    "open_meteo_point": DataSource(
        dataset_id="open_meteo_point",
        name="Open-Meteo Historical Weather API — serie diaria en un punto (13,673° N, 89,174° O)",
        institution="Open-Meteo (ERA5/IFS)",
        source_url="https://open-meteo.com/en/docs/historical-weather-api",
        version="archive-api v1 (declarado por fila)",
        acquisition_date="2026-11-22",
        processing_date="2026-11-22",
        crs="EPSG:4326 (punto)",
        spatial_resolution="celda ~0,1° (~9 km)",
        positional_accuracy=(
            "representatividad de celda de ~9 km; no es una estación"
        ),
        temporal_coverage="2019-01-01 a 2025-12-31",
        temporal_resolution="diaria (suma para precipitación y ET0; media para humedad)",
        units={"precipitation": "mm", "temperature": "degC", "et0": "mm",
               "relative_humidity": "%"},
        nodata=None,
        data_class=DataClass.REANALYSIS,
        methodology=(
            "reanálisis ERA5/IFS; ET0 de referencia FAO-56 calculada por el "
            "proveedor; base temporal America/El_Salvador convertida a UTC−6"
        ),
        assumptions=["un punto no representa el país", "ET0 del proveedor no se "
                     "recalcula en AGROSV"],
        uncertainty="no validada contra estaciones; sin cuantificación de error local",
        validation_status="V1 (integridad temporal; sin validación externa)",
        license="Open-Meteo — datos abiertos (CC BY 4.0 para datos; verificar términos)",
        redistribution_allowed=True,
        geographic_coverage="una coordenada (13,673° N, 89,174° O); no es cobertura nacional",
        artifacts=[_STORE],
        known_limitations=[
            "un solo punto",
            "el producto entrega ET0 pero no sus componentes",
            "sin estaciones de contraste",
        ],
        layer=None,
        variables=["precipitation", "temperature", "et0", "relative_humidity"],
    ),
    "chirps3": DataSource(
        dataset_id="chirps3",
        name="CHIRPS v3.0 — precipitación diaria (muestra de un día)",
        institution="UCSB Climate Hazards Center",
        source_url="https://data.chc.ucsb.edu/products/CHIRPS-3.0/",
        version="v3.0",
        acquisition_date="2026-11-22",
        processing_date="2026-11-22",
        crs="EPSG:4326",
        spatial_resolution="0,05° (~5,5 km)",
        positional_accuracy="estimación satelital calibrada con estaciones; no es un pluviómetro",
        temporal_coverage="un solo día (2026-01-15)",
        temporal_resolution="diaria",
        units={"precipitation": "mm"},
        nodata="no declarado en el archivo (defecto registrado en Fase 4)",
        data_class=DataClass.SATELLITE_ESTIMATE,
        methodology="recorte del producto global al rectángulo de El Salvador",
        assumptions=["un día no es una serie ni una climatología"],
        uncertainty="no cuantificada; sin comparación con pluviómetros",
        validation_status="V1 (estructura y rango)",
        license="CHIRPS — datos abiertos (CC BY 4.0 / dominio público según CHC)",
        redistribution_allowed=True,
        geographic_coverage="El Salvador, un día; no es serie nacional",
        artifacts=[C.DATA / "validated" / "chirps3" /
                   "chirps3_precip_0p05deg_sv_2026-01-15_v3.0.tif"],
        known_limitations=["un solo día", "NoData no declarado en el ráster original"],
        layer="chirps3_precip_0p05deg_sv_2026-01-15_v3.0",
        variables=["precipitation"],
    ),
}


# --- Variables que un motor podría devolver y no devuelve --------------------
# No son "pendientes": son ausencias con motivo y requisito explícito.
UNAVAILABLE: dict[str, dict[str, Any]] = {
    "soil_profile_by_horizon": {
        "variables": ["clay", "sand", "silt", "ph", "soil_organic_carbon"],
        "reason": "SoilGrids se descargó agregado a 0–30 cm; no hay horizontes ni "
                  "intervalos de profundidad adicionales en el repositorio",
        "would_require": "descargar las capas de SoilGrids para 30–60, 60–100 y "
                         "100–200 cm (o perfiles CENTA)",
        "status": "NOT_DOWNLOADED",
    },
    "soil_depth": {
        "variables": ["soil_depth"],
        "reason": "ni SoilGrids 0–30 cm ni ninguna otra fuente integrada miden "
                  "profundidad efectiva del suelo",
        "would_require": "mapa de suelos nacional (CENTA) o perfiles de campo",
        "status": "NO_SOURCE",
    },
    "soil_bulk_density": {
        "variables": ["bulk_density"],
        "reason": "no integrada; tampoco se derivó por pedotransferencia",
        "would_require": "SoilGrids bdod (no descargado) o mediciones",
        "status": "NOT_DOWNLOADED",
    },
    "soil_coarse_fragments": {
        "variables": ["coarse_fragments"],
        "reason": "no integrada; SoilGrids cfvo no descargado",
        "would_require": "SoilGrids cfvo o granulometría de campo",
        "status": "NOT_DOWNLOADED",
    },
    "soil_cec": {
        "variables": ["cation_exchange_capacity"],
        "reason": "no integrada y no se estima por pedotransferencia sin "
                  "declarar y validar los coeficientes",
        "would_require": "SoilGrids cec o laboratorio",
        "status": "NOT_DOWNLOADED",
    },
    "soil_awc": {
        "variables": ["available_water_capacity"],
        "reason": "requiere pedotransferencia desde textura y densidad aparente; "
                  "la densidad aparente no está disponible, de modo que una AWC "
                  "calculada sería un supuesto disfrazado de dato",
        "would_require": "densidad aparente y curva de retención, o AWC medida",
        "status": "BLOCKED_BY_MISSING_INPUT",
    },
    "soil_salinity": {
        "variables": ["electrical_conductivity"],
        "reason": "ninguna fuente integrada mide CE; no se infiere salinidad de "
                  "textura o clima",
        "would_require": "análisis de laboratorio (CE de extracto saturado)",
        "status": "NO_SOURCE",
    },
    "soil_national_map": {
        "variables": ["soil_unit", "soil_depth", "drainage_class"],
        "reason": "el Mapa Digital de Suelos del CENTA está en el catálogo como "
                  "RESTRICTED: sin acceso ni licencia verificados",
        "would_require": "convenio de acceso y licencia de uso/redistribución",
        "status": "RESTRICTED_SOURCE",
    },
    "groundwater_aquifers": {
        "variables": ["aquifer_boundary", "aquifer_type"],
        "reason": "no hay capa de acuíferos verificada en el repositorio "
                  "(el geoportal MARN no expone un REST verificable)",
        "would_require": "shapefile de acuíferos del MARN/ANDA con licencia",
        "status": "NO_SOURCE",
    },
    "groundwater_levels": {
        "variables": ["water_level"],
        "reason": "no hay series de niveles piezométricos ni pozos con datum",
        "would_require": "red de observación de pozos (ANDA/MARN)",
        "status": "NO_SOURCE",
    },
    "groundwater_recharge": {
        "variables": ["recharge"],
        "reason": "no se estima sin acuífero, niveles ni parámetros hidráulicos; "
                  "un número aquí sería inventado",
        "would_require": "modelo hidrogeológico calibrado o trazadores",
        "status": "BLOCKED_BY_MISSING_INPUT",
    },
    "station_observations": {
        "variables": ["precipitation", "temperature", "relative_humidity"],
        "reason": "no hay series de estaciones SNET/MARN accesibles; por eso el "
                  "clima se sirve como reanálisis y no se valida contra estación",
        "would_require": "acceso a datos horarios/diarios de SNET con licencia",
        "status": "RESTRICTED_SOURCE",
    },
    "climate_normals_wmo": {
        "variables": ["climatological_normal"],
        "reason": "la serie disponible cubre 2019–2025 (7 años); la OMM define "
                  "normales sobre 30 años. Se publica una climatología del período, "
                  "no una normal",
        "would_require": "30 años de serie homogénea y control de calidad",
        "status": "INSUFFICIENT_RECORD",
    },
    "climate_forecast": {
        "variables": ["forecast"],
        "reason": "no se integra ningún pronóstico: no hay proveedor configurado",
        "would_require": "fuente de pronóstico con licencia y horizonte declarado",
        "status": "NOT_IMPLEMENTED",
    },
    "streamflow": {
        "variables": ["discharge"],
        "reason": "no hay aforos ni series de caudal; los modelos hidrológicos no "
                  "se calibran",
        "would_require": "aforos del MARN/SNET y curvas de gasto",
        "status": "NO_SOURCE",
    },
    "official_basins": {
        "variables": ["basin", "subbasin"],
        "reason": "no hay delimitación oficial de cuencas en el repositorio; la "
                  "cuenca que calcula el motor es una derivación D8 local desde el "
                  "DEM, no un límite oficial",
        "would_require": "delimitación oficial (MARN) o HydroSHEDS con EULA revisado",
        "status": "NO_SOURCE",
    },
    "municipality_2023": {
        "variables": ["district"],
        "reason": "no hay capa de los 44 municipios vigentes ni de los 262 "
                  "distritos; la correspondencia 2023 está INCOMPLETE",
        "would_require": "tabla oficial de correspondencia y límites vigentes",
        "status": "NO_SOURCE",
    },
    "water_quality": {
        "variables": ["water_quality"],
        "reason": "no hay muestreos de calidad de agua integrados",
        "would_require": "datos de laboratorio (MARN/ANDA) con método y fecha",
        "status": "NO_SOURCE",
    },
    "water_rights": {
        "variables": ["water_right"],
        "reason": "el acceso legal al agua no es un dato físico y no existe en el "
                  "repositorio; AGROSV no infiere disponibilidad legal",
        "would_require": "registro administrativo de derechos de agua (ANDA/MARN)",
        "status": "NO_SOURCE",
    },
}


def sources() -> dict[str, DataSource]:
    return dict(_SOURCES)


def source(source_id: str) -> DataSource:
    try:
        return _SOURCES[source_id]
    except KeyError:
        raise KeyError(
            f"fuente desconocida: {source_id}; disponibles {sorted(_SOURCES)}"
        ) from None


def require(source_id: str) -> DataSource:
    """Devuelve la fuente o lanza si sus artefactos no están presentes."""
    src = source(source_id)
    missing = src.missing_artifacts()
    if missing:
        raise SourceUnavailableError(
            source_id, missing,
            "ejecute los scripts de Fase 1/4 que generan estos artefactos")
    return src


def availability_report() -> dict[str, Any]:
    """Qué se puede usar hoy y qué no, sin inferir de un catálogo."""
    entries = {sid: src.as_dict() for sid, src in _SOURCES.items()}
    available = [sid for sid, e in entries.items() if e["available"]]
    missing = [sid for sid, e in entries.items() if not e["available"]]
    return {
        "generated_at": utcnow(),
        "count": len(entries),
        "available": available,
        "unavailable": missing,
        "sources": entries,
        "unavailable_variables": UNAVAILABLE,
        "note": (
            "available se calcula comprobando artefactos, no leyendo el catálogo; "
            "un dataset RESTRICTED o UNAVAILABLE del catálogo nunca aparece aquí "
            "como utilizable"
        ),
    }


def provenance(source_id: str) -> dict[str, Any]:
    src = source(source_id)
    payload = src.as_dict()
    payload["engine_version"] = ENGINE_VERSION
    payload["provenance_id"] = src.provenance_id()
    payload["retrieved_at"] = utcnow()
    return payload


def lineage_chain(source_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Cadena de procedencia mínima para adjuntar a un resultado compuesto."""
    out = []
    for sid in source_ids:
        try:
            src = source(sid)
        except KeyError:
            out.append({"dataset_id": sid, "error": "fuente no registrada"})
            continue
        out.append({
            "dataset_id": src.dataset_id,
            "name": src.name,
            "institution": src.institution,
            "source_url": src.source_url,
            "version": src.version,
            "data_class": src.data_class.value,
            "license": src.license,
            "spatial_resolution": src.spatial_resolution,
            "temporal_coverage": src.temporal_coverage,
            "provenance_id": src.provenance_id(),
            "available": src.available,
        })
    return out


def coverage_statement() -> dict[str, Any]:
    """Cobertura geográfica real del sistema, sin redondear a «nacional»."""
    dem = source("copdem30")
    return {
        "territorial_extent": {
            "bbox_wgs84": list(C.SV_BOUNDS),
            "note": "rectángulo envolvente de ADM1, no el polígono",
        },
        "terrain": {
            "available": dem.available,
            "extent": "recorte nacional del DEM",
            "resolution": dem.spatial_resolution,
            "derived_metrics": "30 m (EPSG:32616)",
        },
        "soils": {
            "available": source("soilgrids_2").available,
            "extent": "tierra firme de El Salvador (97,4 % de cobertura medida)",
            "depth": "0–30 cm únicamente",
            "resolution": "250 m",
        },
        "hydrology": {
            "surface_water": "cauces y cuerpos de agua mapeados en OSM (cobertura incompleta)",
            "watershed": "derivación D8 local en ventana; no es delimitación oficial",
            "groundwater": "no disponible",
        },
        "climate": {
            "points": [
                {"dataset_id": "nasa_power_point", "lat": 13.70, "lon": -89.20},
                {"dataset_id": "open_meteo_point", "lat": 13.673111,
                 "lon": -89.17432},
            ],
            "period": "2019-01-01 a 2025-12-31",
            "warning": (
                "dos coordenadas no cubren El Salvador: no se interpola "
                "espacialmente el clima"
            ),
        },
        "admin_levels_present": ["country", "department", "municipality_historic"],
        "admin_levels_missing": ["municipality_2023", "district", "basin",
                                 "subbasin", "protected_area", "parcel"],
    }


def envelope(
    engine: str,
    *,
    result: dict[str, Any],
    sources: list[str],
    limitations: list[str],
    processing: list[dict[str, Any]] | None = None,
    query: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Envoltura uniforme §8/§10 para toda respuesta de motor."""
    if not limitations:
        raise ValueError(
            "un resultado sin limitaciones declaradas no es publicable")
    payload = {
        "engine": engine,
        "engine_version": ENGINE_VERSION,
        "generated_at": utcnow(),
        "query": query or {},
        "result": result,
        "sources": lineage_chain(sources),
        "coverage": coverage or {},
        "limitations": limitations,
        "processing_history": processing or [],
        "conventions": {
            "crs_query": C.CRS_STORAGE,
            "crs_metric": C.CRS_METRIC,
            "crs_area": C.CRS_EQUAL_AREA,
            "units": "SI y unidades aceptadas por agrosv.data.units",
            "nodata": "null en JSON; nunca 0 por defecto",
        },
    }
    if extra:
        payload.update(extra)
    return payload


def step(name: str, tool: str, **params: Any) -> dict[str, Any]:
    """Paso de historial de procesamiento, reproducible y con sello temporal."""
    return {"step": name, "tool": tool, "at": utcnow(), "params": params}


__all__ = [
    "DataClass", "NON_OBSERVED", "DataSource", "SourceUnavailableError",
    "UNAVAILABLE", "ENGINE_VERSION", "ENGINES", "sources", "source", "require",
    "availability_report", "provenance", "lineage_chain", "coverage_statement",
    "envelope", "step", "utcnow",
]
