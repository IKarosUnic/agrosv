"""AGROSV — SatelliteDataEngine y catálogo de fuentes (Fase 7, §4.1).

Arquitectura de proveedores **modular y opcional**: el núcleo no depende de
ninguna nube. Se implementan dos adaptadores que funcionan sin red:

* `SatelliteDataEngine.read` — lee GeoTIFF/COG con rasterio por ventana:
  bandas, máscara de validez, máscara de nube, CRS, resolución y fecha.
* `SatelliteDataEngine.parse_stac` — lee un Item/ItemCollection STAC local.

La consulta remota se representa con `stac_search_plan`, que construye la
petición pero **no la ejecuta**. Estado real: no hay escenas integradas en el
repositorio; los adaptadores se prueban con rásteres sintéticos.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from . import governance as G

ENGINE = "satellite_data"
ENGINE_VERSION = G.ENGINE_VERSION

REQUIRED_SOURCE_FIELDS = (
    "provider", "satellite", "sensor", "spatial_resolution_m",
    "temporal_resolution", "bands", "geographic_coverage",
    "historical_availability", "processing_level", "cloud_limitations",
    "access_method", "license", "download_restrictions", "update_frequency",
    "data_format", "integration_status", "known_limitations", "source_url",
)

#: Clases de la máscara de escena (SCL) de Sentinel-2 L2A que se enmascaran.
SCL_INVALID_CLASSES = frozenset({0, 1, 2, 3, 8, 9, 10, 11})
SCL_CLASS_NAMES = {
    0: "no_data", 1: "saturated_or_defective", 2: "dark_area",
    3: "cloud_shadow", 4: "vegetation", 5: "not_vegetated", 6: "water",
    7: "unclassified", 8: "cloud_medium_probability",
    9: "cloud_high_probability", 10: "thin_cirrus", 11: "snow",
}


def _source(**kwargs: Any) -> dict[str, Any]:
    missing = [k for k in REQUIRED_SOURCE_FIELDS if k not in kwargs]
    if missing:
        raise ValueError(f"ficha incompleta {kwargs.get('source_id')}: faltan {missing}")
    return kwargs


SATELLITE_SOURCES: dict[str, dict[str, Any]] = {
    "sentinel2_msi": _source(
        source_id="sentinel2_msi",
        provider="ESA / Copernicus",
        satellite="Sentinel-2A/2B/2C",
        sensor="MSI (multiespectral)",
        spatial_resolution_m={"B02_B03_B04_B08": 10,
                              "B05_B06_B07_B8A_B11_B12": 20, "B01_B09": 60},
        temporal_resolution="5 días con la constelación completa",
        bands=["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08",
               "B8A", "B09", "B11", "B12", "SCL"],
        geographic_coverage="global (tierra emergida)",
        historical_availability="desde 2015-06-23 (S2A); 2017-03 (S2B); 2024 (S2C)",
        processing_level="L1C (TOA) y L2A (reflectancia superficial)",
        cloud_limitations=("cobertura nubosa frecuente en la estación lluviosa; "
                           "exige enmascarado SCL/QA60 y compuestos temporales"),
        access_method=("Copernicus Data Space Ecosystem: STAC/OData con OAuth2; "
                       "descarga directa de productos"),
        license=("datos Copernicus: uso libre y abierto con atribución a la "
                 "Unión Europea/ESA"),
        download_restrictions=("sin pago por Sentinel; requiere registro y "
                               "aceptar términos; almacenamiento local a cargo "
                               "del usuario"),
        update_frequency="adquisición continua; L2A en horas-días",
        data_format="JPEG2000 original; COG tras conversión",
        integration_status="adapter_implemented_not_ingested",
        source_url="https://dataspace.copernicus.eu/",
        known_limitations=[
            "NDMI y NBR usan SWIR de 20 m: su resolución efectiva no es 10 m",
            "L2A corrige atmósfera pero no elimina sombras de relieve",
            "píxeles mixtos: 10 m no resuelve una parcela pequeña",
        ],
    ),
    "sentinel1_csar": _source(
        source_id="sentinel1_csar",
        provider="ESA / Copernicus",
        satellite="Sentinel-1A/1C",
        sensor="C-SAR (radar)",
        spatial_resolution_m={"IW_GRD": 10, "EW_GRD": 40},
        temporal_resolution="6–12 días por satélite según órbita",
        bands=["VV", "VH"],
        geographic_coverage="global",
        historical_availability="desde 2014-10 (S1A); 2024 (S1C)",
        processing_level="GRD (detected) y SLC (complejo)",
        cloud_limitations=("no afectado por nubes; afectado por speckle, viento "
                           "sobre agua y geometría de observación"),
        access_method="Copernicus Data Space Ecosystem (STAC/OData)",
        license="datos Copernicus: uso libre con atribución",
        download_restrictions="registro requerido; productos pesados (GB/escena)",
        update_frequency="adquisición continua",
        data_format="GeoTIFF (GRD) / HDF5 (SLC)",
        integration_status="evaluated_only",
        source_url="https://dataspace.copernicus.eu/",
        known_limitations=[
            "la retrodispersión no es un índice de vigor",
            "requiere corrección de terreno para comparar fechas",
            "no se usa en esta fase para estimar humedad de suelo",
        ],
    ),
    "landsat8_oli": _source(
        source_id="landsat8_oli",
        provider="USGS / NASA",
        satellite="Landsat 8",
        sensor="OLI / TIRS",
        spatial_resolution_m={"multiespectral": 30, "pancromático": 15,
                              "térmico": 100},
        temporal_resolution="16 días",
        bands=["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B10", "B11", "QA_PIXEL"],
        geographic_coverage="global",
        historical_availability="desde 2013-04",
        processing_level="Collection 2 Level-1 y Level-2",
        cloud_limitations="máscara QA_PIXEL; nubes y sombras frecuentes",
        access_method="USGS EarthExplorer y Earthdata/STAC",
        license="dominio público (USGS)",
        download_restrictions="sin costo; registro EarthExplorer requerido",
        update_frequency="cada 16 días",
        data_format="GeoTIFF (Collection 2)",
        integration_status="evaluated_only",
        source_url="https://earthexplorer.usgs.gov/",
        known_limitations=[
            "30 m es más grueso que Sentinel-2: no apto para parcelas pequeñas",
            "la banda térmica de 100 m no es temperatura de dosel",
            "útil para tendencias largas, no para monitoreo semanal",
        ],
    ),
    "landsat9_oli2": _source(
        source_id="landsat9_oli2",
        provider="USGS / NASA",
        satellite="Landsat 9",
        sensor="OLI-2 / TIRS-2",
        spatial_resolution_m={"multiespectral": 30, "pancromático": 15,
                              "térmico": 100},
        temporal_resolution="16 días (8 días combinado con Landsat 8)",
        bands=["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B10", "B11", "QA_PIXEL"],
        geographic_coverage="global",
        historical_availability="desde 2021-09-27",
        processing_level="Collection 2 Level-1 y Level-2",
        cloud_limitations="máscara QA_PIXEL",
        access_method="USGS EarthExplorer y Earthdata/STAC",
        license="dominio público (USGS)",
        download_restrictions="sin costo; registro requerido",
        update_frequency="cada 16 días",
        data_format="GeoTIFF (Collection 2)",
        integration_status="evaluated_only",
        source_url="https://earthexplorer.usgs.gov/",
        known_limitations=[
            "mismas limitaciones de resolución que Landsat 8",
            "serie corta para una climatología de 30 años por sí sola",
        ],
    ),
    "modis": _source(
        source_id="modis",
        provider="NASA LP DAAC",
        satellite="Terra / Aqua",
        sensor="MODIS",
        spatial_resolution_m={"MOD09GA": 500, "MOD13Q1": 250, "MOD11A2": 1000},
        temporal_resolution="diario (reflectancia) y 16 días (compuestos)",
        bands=["sur_refl_b01", "sur_refl_b02", "sur_refl_b03", "sur_refl_b04",
               "sur_refl_b06", "sur_refl_b07", "LST_Day_1km", "LST_Night_1km"],
        geographic_coverage="global",
        historical_availability="desde 2000-02 (Terra); 2002-07 (Aqua)",
        processing_level="L2G / L3 (compuestos)",
        cloud_limitations=("los compuestos reducen nubes pero mezclan fechas; "
                           "QA por píxel obligatoria"),
        access_method="NASA Earthdata (LP DAAC), Earthdata Search y STAC",
        license="abierto (NASA), sin restricción de uso",
        download_restrictions="registro Earthdata; sin costo",
        update_frequency="diario / 16 días",
        data_format="HDF4 / GeoTIFF",
        integration_status="evaluated_only",
        source_url="https://search.earthdata.nasa.gov/",
        known_limitations=[
            "250–500 m: un píxel contiene varias parcelas y caminos",
            "los compuestos de 16 días no son observaciones instantáneas",
            "útil para tendencias regionales, no para una finca",
        ],
    ),
    "viirs": _source(
        source_id="viirs",
        provider="NASA / NOAA",
        satellite="Suomi NPP, NOAA-20, NOAA-21",
        sensor="VIIRS",
        spatial_resolution_m={"I_bands": 375, "M_bands": 750},
        temporal_resolution="diario (con paso orbital)",
        bands=["M3", "M4", "M5", "M7", "M11", "I1", "I2", "I3"],
        geographic_coverage="global",
        historical_availability="desde 2012-01 (Suomi NPP)",
        processing_level="L1B / L2 / L3",
        cloud_limitations="productos de reflectancia y LST con QA; nubes",
        access_method="NASA Earthdata / LAADS DAAC",
        license="abierto (NASA/NOAA)",
        download_restrictions="registro Earthdata; sin costo",
        update_frequency="diario",
        data_format="HDF5 / NetCDF",
        integration_status="evaluated_only",
        source_url="https://ladsweb.modaps.eosdis.nasa.gov/",
        known_limitations=[
            "750 m en bandas M: no apto para agricultura parcelaria",
            "la detección de fuego no equivale a daño agrícola",
        ],
    ),
    "copernicus_data_space": _source(
        source_id="copernicus_data_space",
        provider="ESA / Unión Europea",
        satellite="n/a (plataforma de acceso)",
        sensor="n/a",
        spatial_resolution_m={"n/a": None},
        temporal_resolution="n/a",
        bands=[],
        geographic_coverage="global",
        historical_availability="desde 2014 (operación Copernicus)",
        processing_level="catálogo de productos",
        cloud_limitations="n/a",
        access_method="STAC, OData y OAuth2; API de catálogo",
        license="términos Copernicus; atribución obligatoria",
        download_restrictions="registro y cuota justa; sin pago por Sentinel",
        update_frequency="continua",
        data_format="varios",
        integration_status="catalog_planned",
        source_url="https://dataspace.copernicus.eu/",
        known_limitations=[
            "es un punto de acceso, no un sensor",
            "los productos de terceros tienen licencias aparte",
        ],
    ),
    "nasa_earthdata": _source(
        source_id="nasa_earthdata",
        provider="NASA",
        satellite="n/a (plataforma de acceso)",
        sensor="n/a",
        spatial_resolution_m={"n/a": None},
        temporal_resolution="n/a",
        bands=[],
        geographic_coverage="global",
        historical_availability="depende del producto",
        processing_level="catálogo de productos",
        cloud_limitations="n/a",
        access_method="Earthdata Login + Earthdata Search + CMR/STAC",
        license="abierto salvo productos restringidos declarados",
        download_restrictions="registro obligatorio; algunas colecciones requieren aprobación",
        update_frequency="continua",
        data_format="varios",
        integration_status="catalog_planned",
        source_url="https://search.earthdata.nasa.gov/",
        known_limitations=[
            "no todos los productos son de descarga abierta",
            "la autenticación no se configura en esta fase",
        ],
    ),
    "usgs_earthexplorer": _source(
        source_id="usgs_earthexplorer",
        provider="USGS",
        satellite="Landsat y otros",
        sensor="varios",
        spatial_resolution_m={"depende_del_producto": None},
        temporal_resolution="depende del producto",
        bands=[],
        geographic_coverage="global",
        historical_availability="depende del producto",
        processing_level="catálogo de productos",
        cloud_limitations="n/a",
        access_method="EarthExplorer (web) y Machine-to-Machine API",
        license="dominio público para Landsat; otros según producto",
        download_restrictions="registro; M2M requiere solicitud de acceso",
        update_frequency="continua",
        data_format="varios",
        integration_status="catalog_planned",
        source_url="https://earthexplorer.usgs.gov/",
        known_limitations=["la API M2M exige credenciales que esta fase no configura"],
    ),
    "google_earth_engine": _source(
        source_id="google_earth_engine",
        provider="Google",
        satellite="n/a (plataforma de procesamiento)",
        sensor="n/a",
        spatial_resolution_m={"n/a": None},
        temporal_resolution="n/a",
        bands=[],
        geographic_coverage="global",
        historical_availability="depende del catálogo",
        processing_level="plataforma de análisis",
        cloud_limitations="n/a",
        access_method="API Python/JavaScript con cuenta y proyecto",
        license="términos de Google Earth Engine; datasets con licencia propia",
        download_restrictions=("requiere registro, proyecto y cuotas; no es "
                               "dependencia del núcleo"),
        update_frequency="continua",
        data_format="n/a (procesamiento remoto)",
        integration_status="optional_not_configured",
        source_url="https://earthengine.google.com/",
        known_limitations=[
            "servicio externo: no puede ser requisito para el cálculo local",
            "los resultados deben exportarse y documentar la versión del dataset",
        ],
    ),
    "marn_snet_d3_doa": _source(
        source_id="marn_snet_d3_doa",
        provider="MARN / SNET (El Salvador)",
        satellite="productos nacionales derivados",
        sensor="n/a (productos institucionales)",
        spatial_resolution_m={"no_publicada": None},
        temporal_resolution="no publicada en formato máquina",
        bands=[],
        geographic_coverage="El Salvador",
        historical_availability="no verificada",
        processing_level="no documentado públicamente",
        cloud_limitations="no documentado",
        access_method="portal web y solicitud institucional",
        license="no declarada; uso sujeto a autorización del MARN",
        download_restrictions="sin descarga masiva ni API pública confirmada",
        update_frequency="no verificada",
        data_format="visor web / imágenes",
        integration_status="access_pending",
        source_url="https://www.snet.gob.sv/",
        known_limitations=[
            "no se confirmó capa vectorial ni serie descargable",
            "se prefiere la fuente nacional cuando exista acceso autorizado",
        ],
    ),
}

INTEGRATION_STATUSES = (
    "ingested", "adapter_implemented_not_ingested", "evaluated_only",
    "catalog_planned", "optional_not_configured", "access_pending",
)


@dataclass
class RasterObservation:
    """Observación ráster local; nodata y nube ya aplicados."""

    path: str
    crs: str | None
    transform: tuple[float, ...]
    width: int
    height: int
    bands: dict[str, np.ndarray]
    valid_mask: np.ndarray
    cloud_mask: np.ndarray | None
    acquired_at: str | None
    sensor: str | None
    resolution: tuple[float, float] | None
    nodata: float | None
    driver: str
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def valid_fraction(self) -> float:
        return float(self.valid_mask.mean()) if self.valid_mask.size else 0.0

    def stats(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, arr in self.bands.items():
            vals = arr[np.isfinite(arr)]
            out[name] = {
                "n": int(vals.size),
                "min": float(vals.min()) if vals.size else None,
                "mean": float(vals.mean()) if vals.size else None,
                "max": float(vals.max()) if vals.size else None,
                "nodata_fraction": (round(1.0 - vals.size / arr.size, 6)
                                    if arr.size else None),
            }
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path, "crs": self.crs,
            "transform": list(self.transform),
            "width": self.width, "height": self.height,
            "resolution": list(self.resolution) if self.resolution else None,
            "acquired_at": self.acquired_at, "sensor": self.sensor,
            "driver": self.driver, "nodata": self.nodata,
            "valid_fraction": round(self.valid_fraction, 6),
            "bands": sorted(self.bands), "band_stats": self.stats(),
            "provenance": self.provenance,
        }


def _clean(arr: np.ndarray, nodata: float | None) -> np.ndarray:
    """Enmascarado y centinela de nodata → NaN (nunca cero)."""
    data = np.ma.asarray(arr, dtype="float32")
    out = np.asarray(data.filled(np.nan), dtype="float32")
    if nodata is not None and np.isfinite(nodata):
        out = np.where(out == np.float32(nodata), np.nan, out)
    return np.where(np.isfinite(out), out, np.nan).astype("float32")


def scl_mask(scl: np.ndarray, *,
             invalid: Iterable[int] = SCL_INVALID_CLASSES) -> np.ndarray:
    """Máscara booleana: True = píxel utilizable."""
    return ~np.isin(np.asarray(scl), list(invalid))


class SatelliteDataEngine:
    """Lectura local de escenas y metadatos; sin dependencia de red."""

    engine = ENGINE
    version = ENGINE_VERSION

    def sources(self) -> dict[str, Any]:
        return {
            "count": len(SATELLITE_SOURCES),
            "sources": [dict(SATELLITE_SOURCES[k]) for k in sorted(SATELLITE_SOURCES)],
            "integration_statuses": list(INTEGRATION_STATUSES),
            "ingested": [k for k, v in SATELLITE_SOURCES.items()
                         if v["integration_status"] == "ingested"],
            "note": ("ninguna escena satelital está integrada; los adaptadores "
                     "leen archivos locales aportados por el usuario"),
        }

    def source(self, source_id: str) -> dict[str, Any]:
        if source_id not in SATELLITE_SOURCES:
            raise KeyError(f"fuente desconocida: {source_id}; "
                           f"use {sorted(SATELLITE_SOURCES)}")
        return dict(SATELLITE_SOURCES[source_id])

    def inspect(self, path: str | Path) -> dict[str, Any]:
        """Metadatos de un ráster sin leer las bandas completas."""
        import rasterio

        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"ráster no encontrado: {p}")
        with rasterio.open(p) as ds:
            tags = {k.lower(): v for k, v in ds.tags().items()}
            acquired = (tags.get("acquisition_date") or tags.get("date")
                        or tags.get("datetime") or tags.get("sensing_time"))
            return {
                "path": str(p), "driver": ds.driver,
                "crs": str(ds.crs) if ds.crs else None,
                "width": ds.width, "height": ds.height, "count": ds.count,
                "dtype": ds.dtypes[0], "nodata": ds.nodata,
                "bounds": list(ds.bounds), "resolution": list(ds.res),
                "is_tiled": bool(ds.profile.get("tiled", False)),
                "block_shape": list(ds.block_shapes[0]),
                "overviews": [int(x) for x in (ds.overviews(1) or [])],
                "acquired_at": acquired, "tags": tags,
                "band_descriptions": [d or f"band_{i + 1}"
                                      for i, d in enumerate(ds.descriptions)],
                "provenance": {"source": "local_file"},
            }

    def read(self, path: str | Path, *, bands: Mapping[str, int],
             bounds: tuple[float, float, float, float] | None = None,
             cloud_band: int | None = None,
             cloud_invalid: Iterable[int] = SCL_INVALID_CLASSES,
             reflectance_scale: float | None = None,
             reflectance_offset: float = 0.0,
             sensor: str | None = None) -> RasterObservation:
        """Lee bandas por ventana y aplica nodata, nube y escala declarada.

        `bands` mapea nombre lógico → índice 1-based. `bounds` se expresa en el
        CRS del archivo; si se pasa, solo se leen esas filas/columnas.
        """
        import rasterio
        from rasterio.windows import from_bounds

        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"ráster no encontrado: {p}")
        if not bands:
            raise ValueError("se requiere al menos una banda")
        with rasterio.open(p) as ds:
            window = None
            if bounds is not None:
                window = from_bounds(*bounds, transform=ds.transform)
            data: dict[str, np.ndarray] = {}
            for name, index in bands.items():
                if not 1 <= int(index) <= ds.count:
                    raise ValueError(f"banda {index} fuera de rango (1–{ds.count})")
                arr = ds.read(int(index), window=window, masked=True)
                values = _clean(arr, ds.nodata)
                if reflectance_scale is not None:
                    values = (values * float(reflectance_scale)
                              + float(reflectance_offset) * float(reflectance_scale))
                data[name] = values.astype("float32")
            cloud = None
            if cloud_band is not None:
                raw = ds.read(int(cloud_band), window=window, masked=True)
                cloud = scl_mask(np.asarray(raw.filled(np.nan)),
                                 invalid=cloud_invalid)
            shape = next(iter(data.values())).shape
            valid = np.ones(shape, dtype=bool)
            for arr in data.values():
                valid &= np.isfinite(arr)
            if cloud is not None:
                valid &= cloud
            tags = {k.lower(): v for k, v in ds.tags().items()}
            acquired = (tags.get("acquisition_date") or tags.get("date")
                        or tags.get("datetime") or tags.get("sensing_time"))
            res = ds.res
            observation = RasterObservation(
                path=str(p), crs=str(ds.crs) if ds.crs else None,
                transform=tuple(ds.transform.to_gdal()),
                width=ds.width, height=ds.height, bands=data,
                valid_mask=valid, cloud_mask=cloud, acquired_at=acquired,
                sensor=sensor or tags.get("sensor"),
                resolution=(float(res[0]), float(res[1])),
                nodata=ds.nodata, driver=ds.driver,
                provenance={
                    "crs": str(ds.crs) if ds.crs else None,
                    "windowed": window is not None,
                    "reflectance_scale": reflectance_scale,
                    "reflectance_offset": reflectance_offset,
                    "cloud_masked": cloud is not None, "nodata": ds.nodata,
                },
            )
            if window is not None:
                observation.width = int(window.width)
                observation.height = int(window.height)
            return observation

    def parse_stac(self, path: str | Path) -> dict[str, Any]:
        """Lee un Item o ItemCollection STAC local, sin descargar activos."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"STAC no encontrado: {p}")
        payload = json.loads(p.read_text(encoding="utf-8"))
        if payload.get("type") == "FeatureCollection":
            items = payload.get("features")
        else:
            items = [payload]
        out = []
        for item in items or []:
            props = item.get("properties") or {}
            assets = item.get("assets") or {}
            out.append({
                "id": item.get("id"), "collection": item.get("collection"),
                "datetime": props.get("datetime"), "bbox": item.get("bbox"),
                "license": props.get("license"), "platform": props.get("platform"),
                "cloud_cover": props.get("eo:cloud_cover"),
                "assets": sorted(assets),
                "asset_hrefs": {k: (v or {}).get("href") for k, v in assets.items()},
                "source_file": str(p),
            })
        return {"type": "ItemCollection", "count": len(out), "items": out,
                "network_used": False}

    def stac_search_plan(self, *, source_id: str,
                         bbox: tuple[float, float, float, float],
                         start: str, end: str,
                         limit: int = 50) -> dict[str, Any]:
        """Construye —sin ejecutar— la búsqueda STAC de una fuente."""
        if source_id not in SATELLITE_SOURCES:
            raise KeyError(f"fuente desconocida: {source_id}")
        collections = {
            "sentinel2_msi": ["sentinel-2-l2a"],
            "sentinel1_csar": ["sentinel-1-grd"],
            "landsat8_oli": ["landsat-c2-l2"],
            "landsat9_oli2": ["landsat-c2-l2"],
            "modis": ["modis-13Q1-061", "modis-09A1-061"],
        }.get(source_id)
        if not collections:
            raise ValueError(f"{source_id} no expone una colección STAC agrícola "
                             "verificada en esta fase")
        endpoint = ("https://catalogue.dataspace.copernicus.eu/stac/search"
                    if source_id.startswith("sentinel")
                    else "https://earth-search.aws.element84.com/v1/search")
        return {
            "source_id": source_id, "endpoint": endpoint, "method": "POST",
            "payload": {"collections": collections, "bbox": list(bbox),
                        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
                        "limit": int(limit)},
            "executed": False, "network_required": True,
            "note": ("plan de consulta: no se ejecuta sin red ni credenciales; "
                     "el resultado debe guardarse como ItemCollection local"),
        }

    def summary(self) -> dict[str, Any]:
        return G.result(
            engine=ENGINE, evidence_class="satellite_observation",
            method="catálogo de fuentes y adaptadores locales",
            value=self.sources(),
            limitations=[
                "no hay escenas integradas: se requieren archivos locales",
                "ninguna consulta remota se ejecuta automáticamente",
                "la resolución nominal no garantiza precisión parcelaria",
            ])
