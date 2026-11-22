"""AGROSV — gobernanza de datos agrícolas (Fase 6, §8 y §12).

Extiende la gobernanza de Fase 5 con las fuentes propias de esta fase y con un
vocabulario de evidencia adecuado a parámetros agronómicos:

    observed_statistic   estadística oficial publicada (CAP 2025, censo)
    reference_parameter  valor de referencia bibliográfico (FAO-56, rangos REF)
    model_output         salida de un modelo (simulación, tiempo térmico)
    derived              aritmética determinista de otra clase
    synthetic            dato generado para simulación, no observado
    scenario             supuesto configurable de escenario

Reglas:

1. Un parámetro sin fuente se publica como `null` + estado `GAP`; nunca con un
   valor «razonable».
2. Un resultado sintético lleva `synthetic: true` y no se mezcla con observado.
3. Toda respuesta incluye fuentes, limitaciones, supuestos e historial.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..engines import governance as G5

ENGINE_VERSION = "6.0.0"
SERVICE = "agrosv.agriculture"

EVIDENCE_CLASSES = (
    "observed_statistic",
    "reference_parameter",
    "model_output",
    "derived",
    "synthetic",
    "scenario",
)

PARAMETER_STATUS = ("REF", "NAC", "GAP", "MODEL_DERIVED", "SCENARIO")


class ParameterGapError(LookupError):
    """Se pidió un parámetro que el catálogo declara ausente."""


@dataclass
class AgriculturalSource:
    """Ficha de fuente de Fase 6 con los campos exigidos por §8."""

    dataset_id: str
    name: str
    institution: str
    source_url: str
    version: str | None
    license: str
    redistribution_allowed: bool
    evidence_class: str
    spatial_resolution: str
    temporal_coverage: str
    units: dict[str, str]
    methodology: str
    assumptions: list[str]
    uncertainty: str
    validation_status: str
    variables: list[str] = field(default_factory=list)
    known_limitations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "institution": self.institution,
            "source_url": self.source_url,
            "version": self.version,
            "license": self.license,
            "redistribution_allowed": self.redistribution_allowed,
            "evidence_class": self.evidence_class,
            "spatial_resolution": self.spatial_resolution,
            "temporal_coverage": self.temporal_coverage,
            "units": self.units,
            "methodology": self.methodology,
            "assumptions": self.assumptions,
            "uncertainty": self.uncertainty,
            "validation_status": self.validation_status,
            "variables": self.variables,
            "known_limitations": self.known_limitations,
        }


_SOURCES: dict[str, AgriculturalSource] = {
    "crop_parameters_catalog": AgriculturalSource(
        dataset_id="crop_parameters_catalog",
        name="Catálogo de parámetros de cultivo AGROSV Fase 3",
        institution="AGROSV (compilación de FAO-56, AquaCrop y guías CENTA/MAG)",
        source_url="docs/data_expansion/CROP_PARAMETERS_CATALOG.md",
        version="3.0 (2026-11-22)",
        license="Documento interno AGROSV; valores REF de fuentes citadas",
        redistribution_allowed=True,
        evidence_class="reference_parameter",
        spatial_resolution="no espacial (rangos por cultivo)",
        temporal_coverage="estático",
        units={"cycle_days": "d", "temperature": "degC", "water": "mm",
               "pH": "", "depth": "cm", "slope": "%",
               "nutrient": "kg/t"},
        methodology=(
            "rangos agronómicos de referencia; cada valor declara REF (bibliográfico), "
            "NAC (estadística nacional) o GAP (ausente)"),
        assumptions=[
            "ningún parámetro está calibrado para variedades salvadoreñas",
            "los rangos no son mediciones locales",
        ],
        uncertainty=(
            "rango publicado; no hay intervalo de confianza ni validación local"),
        validation_status="V1 (coherencia interna); sin validación agronómica",
        variables=["cycle", "temperature", "water", "soil", "nutrition"],
        known_limitations=[
            "sin coeficientes genéticos por variedad",
            "sin Kc local por etapa",
            "sin calendarios oficiales de siembra",
        ],
    ),
    "cap_2025": AgriculturalSource(
        dataset_id="cap_2025",
        name="V Censo Agropecuario y I Censo de Pesca 2025 — agregados públicos",
        institution="Banco Central de Reserva (BCR) / Oficina Nacional de Estadística",
        source_url="https://www.bcr.gob.sv/",
        version="entregas 1–3 (2026), resultados preliminares",
        license="Datos agregados publicados; microdatos NO públicos (art. 25 LEC)",
        redistribution_allowed=True,
        evidence_class="observed_statistic",
        spatial_resolution="departamental y nacional",
        temporal_coverage="mayo 2024 – abril 2025 (referencia)",
        units={"area": "ha", "production": "t", "producers": "count"},
        methodology="tabulados oficiales agregados",
        assumptions=["los agregados no identifican unidades de producción"],
        uncertainty="sin evaluación post-enumeración publicada",
        validation_status="V1 (publicación oficial); preliminar",
        variables=["area", "production", "producers"],
        known_limitations=[
            "sin tabulados municipales",
            "microdatos restringidos",
            "cifras preliminares",
        ],
    ),
    "nemotron_personas_sv": AgriculturalSource(
        dataset_id="nemotron_personas_sv",
        name="Nemotron-Personas-El-Salvador",
        institution="NVIDIA / WideLabs",
        source_url="https://huggingface.co/datasets/nvidia/Nemotron-Personas-El-Salvador",
        version="1.0 (sha 68f6a21c17973d6a34ac6354d50a31c1fbcec14f)",
        license="CC BY 4.0",
        redistribution_allowed=True,
        evidence_class="synthetic",
        spatial_resolution="departamento y municipio (44)",
        temporal_coverage="anclaje CPV 2024 / EHPM 2024",
        units={"age": "years"},
        methodology=(
            "personas generadas con un PGM anclado a distribuciones censales; "
            "AGROSV usa únicamente el esquema y, cuando existe, la muestra"),
        assumptions=[
            "cada persona es sintética; no corresponde a una persona real",
            "no contiene tenencia, superficie, ingreso, crédito ni acceso a agua",
        ],
        uncertainty="no representativa de productores agropecuarios",
        validation_status="fuente verificada; sin validación agrícola",
        variables=["age", "sex", "education_level", "occupation", "area",
                   "municipality", "department", "household_type"],
        known_limitations=[
            "subrepresenta identidades indígenas y afrodescendientes",
            "roles de género heredados del modelo narrativo",
            "ocupación independiente de educación en el modelo generativo",
        ],
    ),
    "fao_56": AgriculturalSource(
        dataset_id="fao_56",
        name="FAO Irrigation and Drainage Paper 56 — evapotranspiración del cultivo",
        institution="FAO",
        source_url="https://www.fao.org/3/x0490e/x0490e00.htm",
        version="1998",
        license="Referencia metodológica; no se redistribuye el documento",
        redistribution_allowed=False,
        evidence_class="reference_parameter",
        spatial_resolution="no espacial (método)",
        temporal_coverage="no aplica",
        units={"et0": "mm/d", "kc": "adimensional", "awc": "mm/m"},
        methodology="balance de agua en la zona radicular y coeficientes de cultivo",
        assumptions=["Kc específicos por cultivo y etapa son responsabilidad del usuario"],
        uncertainty="no aplica al método; sí a los parámetros",
        validation_status="método publicado y aceptado",
        variables=["et0", "kc", "soil_water_balance"],
        known_limitations=["FAO-56 no prescribe una fórmula única de lluvia efectiva"],
    ),
    "fao_aez": AgriculturalSource(
        dataset_id="fao_aez",
        name="FAO Land Evaluation / Agro-Ecological Zoning — marco metodológico",
        institution="FAO",
        source_url="https://www.fao.org/land-water/resources/tools/software/pyaez/en",
        version="marco AEZ; PyAEZ 2.2 (MIT) evaluado, no integrado",
        license="Referencia metodológica",
        redistribution_allowed=False,
        evidence_class="reference_parameter",
        spatial_resolution="no espacial (método)",
        temporal_coverage="no aplica",
        units={},
        methodology="clases S1/S2/S3/N por factores limitantes",
        assumptions=[
            "AGROSV usa una simplificación declarada, no el algoritmo oficial de PyAEZ",
        ],
        uncertainty="las clases dependen de umbrales y datos de entrada",
        validation_status="marco de referencia; implementación AGROSV no validada",
        variables=["suitability"],
        known_limitations=["sin LUT oficial de PyAEZ ni datos GAEZ"],
    ),
    "agrosv_scenario": AgriculturalSource(
        dataset_id="agrosv_scenario",
        name="Parámetros de escenario AGROSV (sintéticos)",
        institution="AGROSV",
        source_url="docs/phase6/",
        version=ENGINE_VERSION,
        license="AGROSV",
        redistribution_allowed=True,
        evidence_class="scenario",
        spatial_resolution="no espacial",
        temporal_coverage="escenario",
        units={"currency": "USD"},
        methodology="valores configurables elegidos para experimentos de simulación",
        assumptions=["no son precios, costos ni dotaciones observadas"],
        uncertainty="no cuantificada; dependen del analista",
        validation_status="no validado ni representativo",
        variables=["costs", "prices", "endowments", "shocks"],
        known_limitations=[
            "no sustituye estadísticas de precios, censos ni encuestas",
        ],
    ),
}


def sources() -> dict[str, AgriculturalSource]:
    return dict(_SOURCES)


def source(source_id: str) -> AgriculturalSource:
    try:
        return _SOURCES[source_id]
    except KeyError:
        raise KeyError(f"fuente agrícola desconocida: {source_id}; "
                       f"disponibles {sorted(_SOURCES)}") from None


def ficha(source_id: str) -> dict[str, Any]:
    """Ficha §8 de una fuente agrícola o, si no es local, de Fase 5."""
    if source_id in _SOURCES:
        payload = _SOURCES[source_id].as_dict()
        payload["engine_version"] = ENGINE_VERSION
        return payload
    payload = G5.source(source_id).as_dict()
    payload["engine_version"] = ENGINE_VERSION
    return payload


def lineage(source_ids: Iterable[str]) -> list[dict[str, Any]]:
    out = []
    for sid in source_ids:
        try:
            payload = ficha(sid)
        except KeyError:
            out.append({"dataset_id": sid, "error": "fuente no registrada"})
            continue
        keep = ("dataset_id", "name", "institution", "source_url", "version",
                "license", "evidence_class", "spatial_resolution",
                "temporal_coverage", "validation_status")
        out.append({k: payload.get(k) for k in keep})
    return out


def envelope(
    engine: str,
    *,
    result: dict[str, Any],
    sources: list[str],
    limitations: list[str],
    processing: list[dict[str, Any]] | None = None,
    query: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not limitations:
        raise ValueError("un resultado sin limitaciones no es publicable")
    payload = {
        "engine": engine,
        "engine_version": ENGINE_VERSION,
        "generated_at": G5.utcnow(),
        "query": query or {},
        "result": result,
        "sources": lineage(sources),
        "limitations": limitations,
        "processing_history": processing or [],
        "synthetic": False,
        "conventions": {
            "crs_query": "EPSG:4326",
            "units": "SI; manzana = 0,6989 ha cuando se declare",
            "currency": "USD (El Salvador)",
            "null": "sin dato; nunca 0 por defecto",
        },
    }
    if extra:
        payload.update(extra)
    return payload


def step(name: str, tool: str, **params: Any) -> dict[str, Any]:
    return G5.step(name, tool, **params)


__all__ = [
    "ENGINE_VERSION", "SERVICE", "EVIDENCE_CLASSES", "PARAMETER_STATUS",
    "ParameterGapError", "AgriculturalSource", "sources", "source", "ficha",
    "lineage", "envelope", "step",
]
