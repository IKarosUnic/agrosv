"""AGROSV — CropKnowledgeEngine (Fase 6, §4.1).

Catálogo extensible de cultivos con **procedencia por parámetro**. Cada valor
declara su estado:

    REF           rango agronómico de referencia (FAO-56, AquaCrop, guías CENTA/MAG)
    NAC           estadística nacional publicada (CAP 2025)
    GAP           no existe dato; se publica `null`
    MODEL_DERIVED estimación derivada por AGROSV
    SCENARIO      supuesto configurable de escenario

El catálogo **no** está calibrado para variedades salvadoreñas. No se inventa
ningún parámetro: los cultivos sin datos verificados (lechuga, banano, plátano,
rábano, cilantro) existen como fichas con `GAP` y sirven para declarar la
ausencia, no para simular.

Fuente principal: `docs/data_expansion/CROP_PARAMETERS_CATALOG.md` (Fase 3).
"""
from __future__ import annotations

import unicodedata
from typing import Any, Iterable

from . import governance as AG

ENGINE = "crop_knowledge"
ENGINE_VERSION = AG.ENGINE_VERSION

_REQUIRED = (
    "crop_id", "scientific_name", "local_names", "family", "crop_type",
    "lifecycle", "growth_habit", "cycle_days", "temperature", "water", "soil",
    "nutrition", "kc", "planting_months", "yield_data", "pests", "diseases",
    "sources", "confidence", "production_systems", "gaps",
)


def _p(value: Any, unit: str, status: str = "REF",
       source: str = "crop_parameters_catalog", note: str | None = None
       ) -> dict[str, Any]:
    return {"value": value, "unit": unit, "status": status, "source": source,
            "note": note}


def _gap(unit: str, note: str) -> dict[str, Any]:
    return {"value": None, "unit": unit, "status": "GAP",
            "source": None, "note": note}


def _crop(**kwargs: Any) -> dict[str, Any]:
    missing = [k for k in _REQUIRED if k not in kwargs]
    if missing:
        raise ValueError(f"ficha de cultivo incompleta {kwargs.get('crop_id')}: "
                         f"faltan {missing}")
    return kwargs


CROPS: dict[str, dict[str, Any]] = {
    # --- granos básicos -----------------------------------------------------
    "maize": _crop(
        crop_id="maize", scientific_name="Zea mays L.",
        local_names=["maíz", "milpa", "maíz blanco", "maíz amarillo"],
        family="Poaceae", crop_type="basic_grain", lifecycle="annual",
        growth_habit="erect",
        cycle_days=_p([90, 140], "d"),
        temperature={
            "opt_c": _p([24, 30], "degC"),
            "tbase_c": _p(10.0, "degC", note="temperatura base de literatura"),
            "abs_c": _gap("degC", "el catálogo no publica límites absolutos"),
        },
        water={
            "etc_season_mm": _p([500, 800], "mm"),
            "critical_stages": _p(["floración", "llenado de grano"], "stage"),
            "rainfed_suitability": _p(True, "bool"),
        },
        soil={
            "ph_range": _p([5.5, 7.5], "pH", note="óptimo 6,0–7,0"),
            "depth_min_cm": _p(60, "cm"),
            "slope_max_pct": _p(15, "%"),
            "texture_pref": _gap("USDA class", "no publicado por el catálogo"),
            "drainage": _gap("class", "depende del mapa nacional de suelos"),
        },
        nutrition={
            "n_kg_per_t": _p([20, 30], "kg/t"),
            "p2o5_kg_per_t": _p([8, 12], "kg/t"),
            "k2o_kg_per_t": _p([15, 25], "kg/t"),
        },
        kc=_gap("adimensional", "Kc local por etapa no disponible"),
        planting_months=_gap("month", "no hay calendario oficial en el repositorio"),
        yield_data={
            "national_avg_t_ha": _p(
                2.4, "t/ha", "NAC", "cap_2025",
                "derivado de superficie y producción CAP 2024-25; cálculo AGROSV"),
            "range_t_ha": _gap("t/ha", "sin rendimiento por variedad ni zona"),
        },
        pests=["gusano cogollero (Spodoptera frugiperda)", "barrenador",
               "pulgón"],
        diseases=["mancha de asfalto", "roya", "pudriciones de mazorca"],
        sources=["crop_parameters_catalog", "cap_2025"],
        confidence="media para NAC; baja para parámetros REF",
        production_systems=["rainfed", "irrigated", "smallholder",
                            "commercial", "family"],
        gaps=["coeficientes genéticos por variedad", "Kc local",
              "calendario oficial", "umbrales económicos de plagas"],
    ),
    "beans": _crop(
        crop_id="beans", scientific_name="Phaseolus vulgaris L.",
        local_names=["frijol", "frijol rojo", "frijol negro", "frijol de seda"],
        family="Fabaceae", crop_type="basic_grain", lifecycle="annual",
        growth_habit="climbing_or_bush",
        cycle_days=_p([65, 90], "d"),
        temperature={
            "opt_c": _p([18, 24], "degC"),
            "tbase_c": _p(10.0, "degC", note="temperatura base de literatura"),
            "abs_c": _gap("degC", "no publicado"),
        },
        water={
            "etc_season_mm": _p([300, 500], "mm"),
            "critical_stages": _p(["floración", "formación de vaina"], "stage"),
            "rainfed_suitability": _p(True, "bool"),
        },
        soil={
            "ph_range": _p([6.0, 7.5], "pH"),
            "depth_min_cm": _p(40, "cm"),
            "slope_max_pct": _p(15, "%"),
            "texture_pref": _gap("USDA class", "no publicado"),
            "drainage": _gap("class", "no publicado"),
        },
        nutrition={
            "n_kg_per_t": _p([30, 40], "kg/t",
                             note="la fijación simbiótica reduce la demanda de N"),
            "p2o5_kg_per_t": _p([10, 15], "kg/t"),
            "k2o_kg_per_t": _p([20, 30], "kg/t"),
        },
        kc=_gap("adimensional", "Kc local por etapa no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "CAP 2025 agregado no desagregado"),
               "range_t_ha": _gap("t/ha", "sin rendimiento por variedad")},
        pests=["mosca blanca (Bemisia tabaci)", "lorito verde", "ácaros"],
        diseases=["mosaico dorado", "antracnosis", "mustia hilachosa"],
        sources=["crop_parameters_catalog", "cap_2025"],
        confidence="baja",
        production_systems=["rainfed", "smallholder", "family", "commercial"],
        gaps=["coeficientes genéticos", "Kc local", "calendario oficial"],
    ),
    "rice": _crop(
        crop_id="rice", scientific_name="Oryza sativa L.",
        local_names=["arroz", "arroz de riego"],
        family="Poaceae", crop_type="basic_grain", lifecycle="annual",
        growth_habit="erect",
        cycle_days=_p([100, 140], "d"),
        temperature={"opt_c": _p([22, 32], "degC"),
                     "tbase_c": _p(10.0, "degC", note="literatura"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([450, 700], "mm",
                                   note="riego; no incluye percolación"),
               "critical_stages": _p(["floración", "llenado"], "stage"),
               "rainfed_suitability": _p(False, "bool",
                                         note="el catálogo indica riego dominante")},
        soil={"ph_range": _p([5.0, 7.0], "pH"),
              "depth_min_cm": _p(30, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _p([15, 25], "kg/t"),
                   "p2o5_kg_per_t": _p([6, 10], "kg/t"),
                   "k2o_kg_per_t": _p([12, 20], "kg/t")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["sogata", "barrenador del tallo"],
        diseases=["piricularia", "añublo bacteriano"],
        sources=["crop_parameters_catalog", "cap_2025"],
        confidence="baja",
        production_systems=["irrigated", "commercial"],
        gaps=["Kc local", "calendario", "rendimiento nacional"],
    ),
    "sorghum": _crop(
        crop_id="sorghum", scientific_name="Sorghum bicolor (L.) Moench",
        local_names=["sorgo", "maicillo"],
        family="Poaceae", crop_type="basic_grain", lifecycle="annual",
        growth_habit="erect",
        cycle_days=_p([90, 120], "d"),
        temperature={"opt_c": _p([25, 32], "degC"),
                     "tbase_c": _p(10.0, "degC", note="literatura"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([450, 650], "mm"),
               "critical_stages": _p(["floración", "llenado"], "stage"),
               "rainfed_suitability": _p(True, "bool",
                                         note="tolerante a sequía y canícula")},
        soil={"ph_range": _p([5.5, 7.5], "pH"),
              "depth_min_cm": _p(60, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _p([20, 30], "kg/t"),
                   "p2o5_kg_per_t": _p([8, 12], "kg/t"),
                   "k2o_kg_per_t": _p([15, 25], "kg/t")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["pulgón", "mosca del sorgo"],
        diseases=["antracnosis", "ergot"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["rainfed", "smallholder", "family"],
        gaps=["Kc local", "calendario", "rendimiento"],
    ),
    # --- hortalizas ---------------------------------------------------------
    "tomato": _crop(
        crop_id="tomato", scientific_name="Solanum lycopersicum L.",
        local_names=["tomate", "jitomate"],
        family="Solanaceae", crop_type="horticulture", lifecycle="annual",
        growth_habit="bush_or_staked",
        cycle_days=_p([90, 120], "d"),
        temperature={"opt_c": _p([20, 27], "degC"),
                     "tbase_c": _p(10.0, "degC", note="literatura"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([400, 600], "mm"),
               "critical_stages": _p(["floración", "cuajado", "llenado"], "stage"),
               "rainfed_suitability": _p(False, "bool",
                                         note="riego normalmente necesario")},
        soil={"ph_range": _p([5.5, 7.0], "pH"),
              "depth_min_cm": _p(40, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _p([3.0, 4.0], "kg/t"),
                   "p2o5_kg_per_t": _p([1.0, 1.5], "kg/t"),
                   "k2o_kg_per_t": _p([4.0, 6.0], "kg/t")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["mosca blanca", "minador", "trips"],
        diseases=["tizón temprano", "tizón tardío", "virus del mosaico"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["irrigated", "protected", "commercial", "periurban"],
        gaps=["Kc local", "calendario", "rendimiento"],
    ),
    "sweet_pepper": _crop(
        crop_id="sweet_pepper", scientific_name="Capsicum annuum L.",
        local_names=["chile dulce", "pimiento", "chile verde"],
        family="Solanaceae", crop_type="horticulture", lifecycle="annual",
        growth_habit="bush",
        cycle_days=_p([90, 120], "d"),
        temperature={"opt_c": _p([20, 28], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([400, 600], "mm"),
               "critical_stages": _p(["floración", "cuajado"], "stage"),
               "rainfed_suitability": _p(False, "bool")},
        soil={"ph_range": _p([5.5, 7.0], "pH"),
              "depth_min_cm": _p(40, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["picudo", "mosca blanca"],
        diseases=["marchitez", "mancha bacteriana"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["irrigated", "protected", "commercial"],
        gaps=["Kc", "T base", "nutrición", "rendimiento"],
    ),
    "onion": _crop(
        crop_id="onion", scientific_name="Allium cepa L.",
        local_names=["cebolla", "cebolla blanca"],
        family="Amaryllidaceae", crop_type="horticulture", lifecycle="annual",
        growth_habit="bulb",
        cycle_days=_p([100, 140], "d"),
        temperature={"opt_c": _p([15, 25], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([350, 550], "mm"),
               "critical_stages": _p(["formación de bulbo"], "stage"),
               "rainfed_suitability": _p(False, "bool")},
        soil={"ph_range": _p([6.0, 7.0], "pH"),
              "depth_min_cm": _p(25, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["trips", "mosca de la cebolla"],
        diseases=["mildiú", "podredumbre blanca"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["irrigated", "commercial"],
        gaps=["Kc", "T base", "nutrición", "rendimiento"],
    ),
    "cucumber": _crop(
        crop_id="cucumber", scientific_name="Cucumis sativus L.",
        local_names=["pepino", "pepino de ensalada"],
        family="Cucurbitaceae", crop_type="horticulture", lifecycle="annual",
        growth_habit="vine",
        cycle_days=_p([55, 75], "d"),
        temperature={"opt_c": _p([20, 30], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([400, 600], "mm"),
               "critical_stages": _p(["floración", "producción de fruto"], "stage"),
               "rainfed_suitability": _p(False, "bool")},
        soil={"ph_range": _p([5.5, 7.0], "pH"),
              "depth_min_cm": _p(30, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["mosca blanca", "áfidos"],
        diseases=["mildiú velloso", "oídio"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["irrigated", "protected", "periurban"],
        gaps=["Kc", "T base", "nutrición", "rendimiento"],
    ),
    "cabbage": _crop(
        crop_id="cabbage", scientific_name="Brassica oleracea var. capitata L.",
        local_names=["repollo", "col"],
        family="Brassicaceae", crop_type="horticulture", lifecycle="annual",
        growth_habit="rosette_head",
        cycle_days=_p([80, 120], "d"),
        temperature={"opt_c": _p([15, 22], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([350, 500], "mm"),
               "critical_stages": _p(["formación de cabeza"], "stage"),
               "rainfed_suitability": _p(True, "bool")},
        soil={"ph_range": _p([6.0, 7.5], "pH"),
              "depth_min_cm": _p(30, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["oruga de la col", "pulgón"],
        diseases=["hernia de la col", "mildiú"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["rainfed", "irrigated", "smallholder"],
        gaps=["Kc", "T base", "nutrición", "rendimiento"],
    ),
    # --- frutales -----------------------------------------------------------
    "mango": _crop(
        crop_id="mango", scientific_name="Mangifera indica L.",
        local_names=["mango", "mango criollo"],
        family="Anacardiaceae", crop_type="fruit", lifecycle="perennial",
        growth_habit="tree",
        cycle_days=_gap("d", "perenne: no aplica un ciclo anual"),
        temperature={"opt_c": _p([24, 30], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([700, 1200], "mm"),
               "critical_stages": _p(["floración", "cuajado"], "stage"),
               "rainfed_suitability": _p(True, "bool")},
        soil={"ph_range": _p([5.5, 7.5], "pH"),
              "depth_min_cm": _p(100, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["mosca de la fruta", "cochinilla"],
        diseases=["antracnosis", "oidio"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["rainfed", "commercial", "family"],
        gaps=["Kc", "nutrición", "rendimiento", "portainjertos"],
    ),
    "avocado": _crop(
        crop_id="avocado", scientific_name="Persea americana Mill.",
        local_names=["aguacate", "palta"],
        family="Lauraceae", crop_type="fruit", lifecycle="perennial",
        growth_habit="tree",
        cycle_days=_gap("d", "perenne"),
        temperature={"opt_c": _p([20, 28], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([1000, 1500], "mm"),
               "critical_stages": _p(["floración", "cuajado"], "stage"),
               "rainfed_suitability": _p(False, "bool",
                                         note="requiere drenaje y riego en verano")},
        soil={"ph_range": _p([5.5, 7.0], "pH"),
              "depth_min_cm": _p(60, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _p("bien drenado", "class", note="requisito cualitativo")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["ácaros", "trips"],
        diseases=["pudrición radicular", "antracnosis"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["irrigated", "commercial"],
        gaps=["Kc", "nutrición", "rendimiento"],
    ),
    "citrus": _crop(
        crop_id="citrus", scientific_name="Citrus spp.",
        local_names=["cítricos", "naranja", "limón", "mandarina"],
        family="Rutaceae", crop_type="fruit", lifecycle="perennial",
        growth_habit="tree",
        cycle_days=_gap("d", "perenne"),
        temperature={"opt_c": _p([23, 30], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([900, 1200], "mm"),
               "critical_stages": _p(["floración", "cuajado"], "stage"),
               "rainfed_suitability": _p(True, "bool")},
        soil={"ph_range": _p([5.5, 7.0], "pH"),
              "depth_min_cm": _p(60, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["mosca de la fruta", "ácaros"],
        diseases=["tristeza", "gomosis"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["rainfed", "irrigated", "commercial"],
        gaps=["Kc", "nutrición", "rendimiento", "especie específica"],
    ),
    "papaya": _crop(
        crop_id="papaya", scientific_name="Carica papaya L.",
        local_names=["papaya"],
        family="Caricaceae", crop_type="fruit", lifecycle="short_lived_perennial",
        growth_habit="herbaceous_tree",
        cycle_days=_p([270, 360], "d"),
        temperature={"opt_c": _p([22, 30], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([1200, 1500], "mm"),
               "critical_stages": _p(["floración", "cuajado"], "stage"),
               "rainfed_suitability": _p(False, "bool",
                                         note="sensible a anegamiento")},
        soil={"ph_range": _p([5.5, 7.0], "pH"),
              "depth_min_cm": _p(40, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _p("bien drenado", "class")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["ácaros", "mosca de la fruta"],
        diseases=["virus de la mancha anular", "antracnosis"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["irrigated", "commercial"],
        gaps=["Kc", "nutrición", "rendimiento"],
    ),
    # --- cultivos comerciales y perennes ------------------------------------
    "coffee": _crop(
        crop_id="coffee", scientific_name="Coffea arabica L.",
        local_names=["café", "café oro", "café pergamino"],
        family="Rubiaceae", crop_type="commercial_perennial",
        lifecycle="perennial", growth_habit="shrub",
        cycle_days=_p([1095, 1460], "d", note="a primera cosecha: 3–4 años"),
        temperature={"opt_c": _p([18, 24], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([1000, 1800], "mm"),
               "critical_stages": _p(["floración", "llenado del grano"], "stage"),
               "rainfed_suitability": _p(True, "bool")},
        soil={"ph_range": _p([5.0, 6.5], "pH"),
              "depth_min_cm": _p(60, "cm"),
              "slope_max_pct": _gap("%", "apto en laderas con sombra y conservación"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _p([30, 40], "kg/t",
                                    note="por tonelada de café oro"),
                   "p2o5_kg_per_t": _p([8, 12], "kg/t"),
                   "k2o_kg_per_t": _p([30, 40], "kg/t")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "CAP 2025 no desagregado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["broca (Hypothenemus hampei)"],
        diseases=["roya (Hemileia vastatrix)", "ojo de gallo", "antracnosis"],
        sources=["crop_parameters_catalog", "cap_2025"],
        confidence="baja",
        production_systems=["rainfed", "agroforestry", "smallholder",
                            "commercial"],
        gaps=["Kc", "calendario", "rendimiento por zona", "suelos de cordillera"],
    ),
    "sugarcane": _crop(
        crop_id="sugarcane", scientific_name="Saccharum officinarum L.",
        local_names=["caña de azúcar", "caña"],
        family="Poaceae", crop_type="commercial_perennial",
        lifecycle="perennial", growth_habit="tall_grass",
        cycle_days=_p([365, 540], "d", note="plantilla; rebrotes anuales"),
        temperature={"opt_c": _p([24, 32], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([1200, 1800], "mm"),
               "critical_stages": _p(["macollamiento", "crecimiento de tallo"],
                                     "stage"),
               "rainfed_suitability": _p(True, "bool",
                                         note="riego complementario en verano")},
        soil={"ph_range": _p([5.5, 8.0], "pH"),
              "depth_min_cm": _p(80, "cm"),
              "slope_max_pct": _p(12, "%", note="≤12 % mecanizable"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _p([1.5, 2.5], "kg/t",
                                    note="por tonelada de caña"),
                   "p2o5_kg_per_t": _p([0.8, 1.2], "kg/t"),
                   "k2o_kg_per_t": _p([2.0, 3.0], "kg/t")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "CAP 2025 no desagregado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["taladrador del tallo (Diatraea spp.)", "salivazo"],
        diseases=["mosaico", "raquitismo de la soca"],
        sources=["crop_parameters_catalog", "cap_2025"],
        confidence="baja",
        production_systems=["rainfed", "irrigated", "commercial"],
        gaps=["Kc", "calendario", "rendimiento por ingenio"],
    ),
    "cacao": _crop(
        crop_id="cacao", scientific_name="Theobroma cacao L.",
        local_names=["cacao", "cacao criollo"],
        family="Malvaceae", crop_type="commercial_perennial",
        lifecycle="perennial", growth_habit="tree",
        cycle_days=_gap("d", "perenne"),
        temperature={"opt_c": _p([22, 30], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([1200, 1800], "mm"),
               "critical_stages": _p(["floración", "llenado de mazorca"], "stage"),
               "rainfed_suitability": _p(True, "bool")},
        soil={"ph_range": _p([5.5, 7.0], "pH"),
              "depth_min_cm": _p(60, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["monilia", "chinche del cacao"],
        diseases=["moniliasis", "escoba de bruja"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["agroforestry", "smallholder", "family"],
        gaps=["Kc", "nutrición", "rendimiento", "sombra"],
    ),
    "coconut": _crop(
        crop_id="coconut", scientific_name="Cocos nucifera L.",
        local_names=["coco", "cocotero"],
        family="Arecaceae", crop_type="fruit", lifecycle="perennial",
        growth_habit="palm",
        cycle_days=_gap("d", "perenne"),
        temperature={"opt_c": _p([25, 32], "degC"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _p([1200, 2000], "mm"),
               "critical_stages": _p(["floración", "llenado del fruto"], "stage"),
               "rainfed_suitability": _p(True, "bool")},
        soil={"ph_range": _p([5.5, 8.0], "pH"),
              "depth_min_cm": _p(60, "cm"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["escarabajo rinoceronte", "ácaros"],
        diseases=["amarillamiento letal", "pudrición del cogollo"],
        sources=["crop_parameters_catalog"],
        confidence="baja",
        production_systems=["rainfed", "coastal", "family"],
        gaps=["Kc", "nutrición", "rendimiento"],
    ),
    # --- agricultura urbana (fichas GAP deliberadas) -----------------------
    "lettuce_urban": _crop(
        crop_id="lettuce_urban", scientific_name="Lactuca sativa L.",
        local_names=["lechuga", "lechuga de hoja"],
        family="Asteraceae", crop_type="urban_horticulture",
        lifecycle="annual", growth_habit="rosette",
        cycle_days=_gap("d", "no hay parámetro verificado en el catálogo"),
        temperature={"opt_c": _gap("degC", "no publicado"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _gap("mm", "no publicado"),
               "critical_stages": _gap("stage", "no publicado"),
               "rainfed_suitability": _gap("bool", "no publicado")},
        soil={"ph_range": _gap("pH", "no publicado"),
              "depth_min_cm": _gap("cm", "contenedor: no aplica igual"),
              "slope_max_pct": _gap("%", "no aplica en contenedor"),
              "texture_pref": _gap("USDA class", "sustrato, no suelo"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=[], diseases=[],
        sources=["crop_parameters_catalog"],
        confidence="sin parámetros",
        production_systems=["urban", "container", "small_space"],
        gaps=["todos los parámetros agronómicos", "sustrato", "riego urbano"],
    ),
    "radish_urban": _crop(
        crop_id="radish_urban", scientific_name="Raphanus sativus L.",
        local_names=["rábano", "rabanito"],
        family="Brassicaceae", crop_type="urban_horticulture",
        lifecycle="annual", growth_habit="rosette",
        cycle_days=_gap("d", "no hay parámetro verificado"),
        temperature={"opt_c": _gap("degC", "no publicado"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _gap("mm", "no publicado"),
               "critical_stages": _gap("stage", "no publicado"),
               "rainfed_suitability": _gap("bool", "no publicado")},
        soil={"ph_range": _gap("pH", "no publicado"),
              "depth_min_cm": _gap("cm", "contenedor"),
              "slope_max_pct": _gap("%", "no aplica"),
              "texture_pref": _gap("USDA class", "sustrato"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=[], diseases=[],
        sources=["crop_parameters_catalog"],
        confidence="sin parámetros",
        production_systems=["urban", "container", "short_cycle"],
        gaps=["todos los parámetros agronómicos"],
    ),
    "cilantro_urban": _crop(
        crop_id="cilantro_urban", scientific_name="Coriandrum sativum L.",
        local_names=["cilantro", "culantro"],
        family="Apiaceae", crop_type="urban_horticulture",
        lifecycle="annual", growth_habit="herb",
        cycle_days=_gap("d", "no hay parámetro verificado"),
        temperature={"opt_c": _gap("degC", "no publicado"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _gap("mm", "no publicado"),
               "critical_stages": _gap("stage", "no publicado"),
               "rainfed_suitability": _gap("bool", "no publicado")},
        soil={"ph_range": _gap("pH", "no publicado"),
              "depth_min_cm": _gap("cm", "contenedor"),
              "slope_max_pct": _gap("%", "no aplica"),
              "texture_pref": _gap("USDA class", "sustrato"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=[], diseases=[],
        sources=["crop_parameters_catalog"],
        confidence="sin parámetros",
        production_systems=["urban", "container", "short_cycle"],
        gaps=["todos los parámetros agronómicos"],
    ),
    "banana": _crop(
        crop_id="banana", scientific_name="Musa acuminata Colla",
        local_names=["banano", "guineo"],
        family="Musaceae", crop_type="fruit", lifecycle="perennial",
        growth_habit="herbaceous_pseudostem",
        cycle_days=_gap("d", "no hay ciclo verificado en el catálogo"),
        temperature={"opt_c": _gap("degC", "no publicado"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _gap("mm", "no publicado"),
               "critical_stages": _gap("stage", "no publicado"),
               "rainfed_suitability": _gap("bool", "no publicado")},
        soil={"ph_range": _gap("pH", "no publicado"),
              "depth_min_cm": _gap("cm", "no publicado"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["picudo negro", "nematodos"],
        diseases=["sigatoka negra", "mal de Panamá"],
        sources=["crop_parameters_catalog"],
        confidence="sin parámetros",
        production_systems=["rainfed", "irrigated", "family"],
        gaps=["todos los parámetros agronómicos verificados"],
    ),
    "plantain": _crop(
        crop_id="plantain", scientific_name="Musa × paradisiaca L.",
        local_names=["plátano", "plátano macho"],
        family="Musaceae", crop_type="fruit", lifecycle="perennial",
        growth_habit="herbaceous_pseudostem",
        cycle_days=_gap("d", "no hay ciclo verificado en el catálogo"),
        temperature={"opt_c": _gap("degC", "no publicado"),
                     "tbase_c": _gap("degC", "no publicado"),
                     "abs_c": _gap("degC", "no publicado")},
        water={"etc_season_mm": _gap("mm", "no publicado"),
               "critical_stages": _gap("stage", "no publicado"),
               "rainfed_suitability": _gap("bool", "no publicado")},
        soil={"ph_range": _gap("pH", "no publicado"),
              "depth_min_cm": _gap("cm", "no publicado"),
              "slope_max_pct": _gap("%", "no publicado"),
              "texture_pref": _gap("USDA class", "no publicado"),
              "drainage": _gap("class", "no publicado")},
        nutrition={"n_kg_per_t": _gap("kg/t", "no publicado"),
                   "p2o5_kg_per_t": _gap("kg/t", "no publicado"),
                   "k2o_kg_per_t": _gap("kg/t", "no publicado")},
        kc=_gap("adimensional", "no disponible"),
        planting_months=_gap("month", "no hay calendario oficial"),
        yield_data={"national_avg_t_ha": _gap("t/ha", "no derivado"),
               "range_t_ha": _gap("t/ha", "no disponible")},
        pests=["picudo negro", "nematodos"],
        diseases=["sigatoka negra", "mal de Panamá"],
        sources=["crop_parameters_catalog"],
        confidence="sin parámetros",
        production_systems=["rainfed", "family", "smallholder"],
        gaps=["todos los parámetros agronómicos verificados"],
    ),
}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").strip()


def _validate() -> None:
    for cid, record in CROPS.items():
        if record["crop_id"] != cid:
            raise ValueError(f"crop_id inconsistente: {cid}")
        for section in ("cycle_days", "kc"):
            if "status" not in record[section]:
                raise ValueError(f"{cid}.{section} sin estado")
        for section in ("temperature", "water", "soil", "nutrition",
                        "yield_data"):
            for key, value in record[section].items():
                if not isinstance(value, dict) or "status" not in value:
                    raise ValueError(f"{cid}.{section}.{key} sin estado")
        for source_id in record["sources"]:
            AG.source(source_id)


_validate()


class CropKnowledgeEngine:
    """Consulta del catálogo: listar, buscar, comparar y auditar vacíos."""

    engine = ENGINE
    version = ENGINE_VERSION

    def list_crops(self, *, crop_type: str | None = None,
                   production_system: str | None = None) -> dict[str, Any]:
        rows = []
        for record in CROPS.values():
            if crop_type and record["crop_type"] != crop_type:
                continue
            if production_system and production_system not in \
                    record["production_systems"]:
                continue
            rows.append({
                "crop_id": record["crop_id"],
                "scientific_name": record["scientific_name"],
                "local_names": record["local_names"],
                "crop_type": record["crop_type"],
                "lifecycle": record["lifecycle"],
                "cycle_days": record["cycle_days"],
                "parameter_status": self._status_summary(record),
            })
        return {
            "count": len(rows),
            "crops": sorted(rows, key=lambda r: r["crop_id"]),
            "types": sorted({r["crop_type"] for r in CROPS.values()}),
            "note": ("un cultivo con parámetros GAP no se puede simular; la "
                     "ficha existe para declarar la ausencia"),
        }

    def get(self, crop_id: str) -> dict[str, Any]:
        key = crop_id.strip().lower()
        if key not in CROPS:
            raise KeyError(f"cultivo desconocido: {crop_id}; "
                           f"disponibles {sorted(CROPS)}")
        record = dict(CROPS[key])
        record["yield"] = record.pop("yield_data")
        return {
            "crop": record,
            "provenance": [AG.ficha(s) for s in record["sources"]],
            "parameter_gaps": record["gaps"],
            "simulation_ready": self.simulation_ready(key),
        }

    def find(self, text: str) -> dict[str, Any]:
        needle = _normalize(text)
        hits = []
        for record in CROPS.values():
            haystack = [_normalize(record["crop_id"]),
                        _normalize(record["scientific_name"]),
                        *[_normalize(n) for n in record["local_names"]]]
            if any(needle in item for item in haystack):
                hits.append(record["crop_id"])
        return {"query": text, "matches": sorted(hits), "count": len(hits)}

    def compare(self, crop_ids: Iterable[str]) -> dict[str, Any]:
        rows = {}
        for cid in crop_ids:
            record = CROPS.get(cid.strip().lower())
            if record is None:
                rows[cid] = {"error": "cultivo desconocido"}
                continue
            rows[cid] = {
                "cycle_days": record["cycle_days"],
                "temperature_opt_c": record["temperature"]["opt_c"],
                "etc_season_mm": record["water"]["etc_season_mm"],
                "ph_range": record["soil"]["ph_range"],
                "depth_min_cm": record["soil"]["depth_min_cm"],
                "slope_max_pct": record["soil"]["slope_max_pct"],
                "national_yield": record["yield_data"]["national_avg_t_ha"],
            }
        return {"count": len(rows), "comparison": rows,
                "warning": "comparar REF con NAC no los hace equivalentes"}

    def simulation_ready(self, crop_id: str) -> dict[str, Any]:
        """Un cultivo es simulable solo si tiene ciclo y temperatura base."""
        record = CROPS[crop_id]
        missing = []
        if record["cycle_days"]["status"] == "GAP":
            missing.append("cycle_days")
        if record["temperature"]["tbase_c"]["status"] == "GAP":
            missing.append("temperature.tbase_c")
        if record["water"]["etc_season_mm"]["status"] == "GAP":
            missing.append("water.etc_season_mm")
        return {"ready": not missing, "missing": missing,
                "note": ("'ready' solo significa que existen parámetros mínimos; "
                         "no implica calibración ni validación")}

    def audit(self) -> dict[str, Any]:
        total = len(CROPS)
        ready = sum(1 for c in CROPS if self.simulation_ready(c)["ready"])
        gaps = sum(len(c["gaps"]) for c in CROPS.values())
        statuses: dict[str, int] = {}
        for record in CROPS.values():
            for section in ("cycle_days", "kc"):
                statuses[record[section]["status"]] = \
                    statuses.get(record[section]["status"], 0) + 1
        return {
            "crops": total,
            "simulation_ready": ready,
            "declared_gaps": gaps,
            "status_counts": statuses,
            "national_statistics": sum(
                1 for c in CROPS.values()
                if c["yield_data"]["national_avg_t_ha"]["status"] == "NAC"),
            "note": ("el catálogo declara más vacíos que valores: es su "
                     "propósito, no un defecto"),
        }

    @staticmethod
    def _status_summary(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "cycle": record["cycle_days"]["status"],
            "kc": record["kc"]["status"],
            "national_yield": record["yield_data"]["national_avg_t_ha"]["status"],
        }


__all__ = ["CropKnowledgeEngine", "CROPS", "ENGINE", "ENGINE_VERSION"]
