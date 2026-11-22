"""AGROSV — registro de fuentes externas pendientes de adquisición.

Ninguna fuente de este registro se presenta como integrada salvo la
correspondencia municipal 2023, que se deriva de la distribución oficial
publicada por la Asamblea Legislativa.

Estados:

    acquired_official              descargada/derivada de fuente oficial
    public_metadata_series_on_request  metadatos públicos; series por solicitud
    public_portal_not_machine_readable portal público sin capa descargable
    restricted_by_request          acceso restringido o confidencial
    paid_request_cnr               servicio arancelado del CNR
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExternalSource:
    source_id: str
    name: str
    institution: str
    purpose: str
    access_status: str
    access_url: str
    license_status: str
    evidence_class: str
    expected_format: str
    required_fields: tuple[str, ...]
    validator: str
    unlocks: tuple[str, ...]
    fallback: str
    notes: tuple[str, ...] = ()
    dataset_path: str | None = None
    counts: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "institution": self.institution,
            "purpose": self.purpose,
            "access_status": self.access_status,
            "access_url": self.access_url,
            "license_status": self.license_status,
            "evidence_class": self.evidence_class,
            "expected_format": self.expected_format,
            "required_fields": list(self.required_fields),
            "validator": self.validator,
            "unlocks": list(self.unlocks),
            "fallback": self.fallback,
            "notes": list(self.notes),
            "dataset_path": self.dataset_path,
            "counts": self.counts,
            "acquired": self.access_status == "acquired_official",
        }


SOURCES: dict[str, ExternalSource] = {
    "snet_marn_stations": ExternalSource(
        source_id="snet_marn_stations",
        name="Series diarias de estaciones SNET/MARN",
        institution="MARN — Dirección General del Observatorio de Amenazas y "
                    "Recursos Naturales (SNET)",
        purpose=("Sustituir el punto de reanálisis por observaciones de "
                 "estación y permitir validación local de lluvia, temperatura "
                 "y ET0."),
        access_status="public_metadata_series_on_request",
        access_url=("https://snet.gob.sv/ver/hidrologia/archivo+historico/"
                    "series+historicas"),
        license_status=("MARN permite la reproducción total o parcial citando "
                        "la fuente y su período de validez; la redistribución "
                        "de series crudas requiere confirmación escrita"),
        evidence_class="observed_station",
        expected_format="CSV largo (una fila por estación-día-variable)",
        required_fields=("station_id", "date", "variable", "value", "unit",
                         "latitude", "longitude", "source"),
        validator="station_series",
        unlocks=("validación del reanálisis", "ET0 local", "fenología con "
                 "observaciones", "climatología de estación"),
        fallback=("Open-Meteo y NASA POWER, declarados como reanálisis en un "
                  "punto, no como estación"),
        notes=("el portal publica metadatos y series históricas por estación; "
               "no se encontró un archivo nacional descargable",
               "no se descargó ninguna serie en Fase 6/7"),
    ),
    "centa_soil_lab": ExternalSource(
        source_id="centa_soil_lab",
        name="Muestras georreferenciadas del Laboratorio de Suelos CENTA",
        institution="CENTA — Laboratorio de Suelos / MAG",
        purpose=("Sustituir la predicción SoilGrids 0–30 cm por mediciones "
                 "locales de pH, materia orgánica, textura, CEC y nutrientes."),
        access_status="restricted_by_request",
        access_url="https://www.centa.gob.sv/servicios/suelos",
        license_status=("No declarada para datos muestra a muestra; sujeta a "
                        "confidencialidad y autorización institucional"),
        evidence_class="observed_laboratory",
        expected_format="CSV largo (una fila por muestra-variable)",
        required_fields=("sample_id", "date", "latitude", "longitude",
                         "depth_cm", "variable", "value", "unit",
                         "lab_method", "source"),
        validator="centa_samples",
        unlocks=("calibración de SoilGrids", "CEC, densidad y nutrientes",
                 "textura medida", "recomendación de fertilización defendible"),
        fallback=("SoilGrids 0–30 cm, declarado como predicción y sin CEC, "
                  "densidad ni nutrientes disponibles"),
        notes=("el laboratorio presta servicios y publica mapas digitales "
               "agregados; no hay microdatos públicos",
               "se requiere convenio y definir anonimización"),
    ),
    "marn_basins": ExternalSource(
        source_id="marn_basins",
        name="Cuencas y subcuencas oficiales de MARN",
        institution="MARN — Dirección General del Observatorio de Amenazas y "
                    "Recursos Naturales",
        purpose=("Sustituir la cuenca derivada por D8 con límites y códigos "
                 "oficiales y permitir agregación hidrológica comparable."),
        access_status="public_portal_not_machine_readable",
        access_url="https://srt.snet.gob.sv/simih/public/atlas",
        license_status="Atribución a MARN; verificar términos de descarga",
        evidence_class="official_boundary",
        expected_format="GeoJSON o GeoPackage (Polygon/MultiPolygon, EPSG:4326)",
        required_fields=("basin_code", "name", "area_km2"),
        validator="basins",
        unlocks=("códigos oficiales de cuenca", "balance por cuenca oficial",
                 "comparación con la cuenca D8"),
        fallback=("cuenca D8 derivada del DEM, declarada como derivada y sin "
                  "código oficial"),
        notes=("el atlas SIHI publica mapas; no se confirmó una capa vectorial "
               "descargable con códigos",
               "puede requerir solicitud a la DGOA"),
    ),
    "marn_gauging": ExternalSource(
        source_id="marn_gauging",
        name="Registros de aforo y caudal de estaciones hidrométricas",
        institution="MARN — Servicio Hidrológico / SNET",
        purpose=("Validar el balance P−ET0 y la escorrentía derivada con "
                 "caudales observados."),
        access_status="public_metadata_series_on_request",
        access_url=("https://snet.gob.sv/ver/hidrologia/monitoreo+hidrologico/"
                    "caudales"),
        license_status=("MARN permite reproducción citando la fuente; "
                        "confirmar condiciones para series crudas"),
        evidence_class="observed_gauging",
        expected_format="CSV largo (estación-día-caudal)",
        required_fields=("station_id", "date", "discharge_m3s", "basin_code",
                         "source"),
        validator="gauging",
        unlocks=("validación de escorrentía", "curva de duración de caudales",
                 "calibración hidrológica"),
        fallback=("balance P−ET0 declarado como contable, no como caudal "
                  "observado"),
        notes=("el portal describe la red y los aforos bimensuales; no se "
               "encontró descarga masiva",
               "se requiere la versión de la curva de gasto"),
    ),
    "municipality_crosswalk_2023": ExternalSource(
        source_id="municipality_crosswalk_2023",
        name="Correspondencia municipio → distrito (Decreto 762, 2023)",
        institution="Asamblea Legislativa de El Salvador",
        purpose=("Permitir que cualquier dato histórico a nivel de municipio "
                 "se agregue a los 44 municipios vigentes sin perder los 262 "
                 "distritos."),
        access_status="acquired_official",
        access_url="https://www.asamblea.gob.sv/node/12806",
        license_status="Información pública oficial; atribución a la Asamblea",
        evidence_class="official_legal_mapping",
        expected_format="CSV (una fila por distrito)",
        required_fields=("department", "municipality", "district",
                         "legal_instrument", "effective_date", "source"),
        validator="crosswalk",
        unlocks=("agregación histórica → 44 municipios", "unión por distrito",
                 "trazabilidad legal del cambio"),
        fallback="no aplica: el conjunto está adquirido",
        counts={"departments": 14, "municipalities": 44, "districts": 262},
        dataset_path="data/reference/municipality_crosswalk_2023.csv",
        notes=("derivado de la distribución publicada por la Asamblea; no es "
               "un archivo catastral",
               "sin códigos oficiales porque la fuente no los publica",
               "correcciones de digitalización documentadas en la procedencia"),
    ),
    "gnss_control_points": ExternalSource(
        source_id="gnss_control_points",
        name="Vértices GNSS y bancos de marca del CNR",
        institution="CNR — Instituto Geográfico y del Catastro Nacional",
        purpose=("Cuantificar el error vertical del DEM (sesgo, MAE, RMSE, P95) "
                 "con puntos de control independientes."),
        access_status="paid_request_cnr",
        access_url=("https://www.cnr.gob.sv/servicios/detalle-de-servicios-"
                    "del-instituto-geografico-y-del-catastro-nacional/"),
        license_status=("Servicio arancelado (catálogo CNR); condiciones de "
                        "uso por solicitud"),
        evidence_class="geodetic_control",
        expected_format="CSV (un punto por fila, con altitud y precisión)",
        required_fields=("point_id", "latitude", "longitude",
                         "orthometric_height_m", "horizontal_accuracy_m",
                         "vertical_accuracy_m", "date", "source"),
        validator="gnss",
        unlocks=("error vertical del DEM", "sesgo por región", "decisión sobre "
                 "si el DEM sirve para pendiente y drenaje"),
        fallback=("DEM Copernicus GLO-30 sin exactitud vertical declarada; "
                  "solo resolución nominal de 30 m"),
        notes=("el CNR ofrece vértices, bancos de marca y puntos de control "
               "horizontal/vertical por arancel",
               "no se usó el ajuste SIRGAS-ES2007: es otra época y otro "
               "propósito",
               "se requiere altura ortométrica o elipsoidal + ondulación"),
    ),
}


def sources() -> dict[str, Any]:
    return {
        "count": len(SOURCES),
        "sources": [s.as_dict() for s in SOURCES.values()],
        "acquired": [s.source_id for s in SOURCES.values()
                     if s.access_status == "acquired_official"],
        "not_acquired": [s.source_id for s in SOURCES.values()
                         if s.access_status != "acquired_official"],
        "rule": ("un metadato público o un portal no equivale a un dato "
                 "adquirido; no se rellena ninguna serie"),
    }


def source(source_id: str) -> ExternalSource:
    try:
        return SOURCES[source_id]
    except KeyError:
        raise KeyError(f"fuente externa desconocida: {source_id}; "
                       f"disponibles {sorted(SOURCES)}") from None


__all__ = ["ExternalSource", "SOURCES", "sources", "source"]
