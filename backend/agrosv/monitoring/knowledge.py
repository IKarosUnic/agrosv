"""AGROSV — base de conocimiento de plagas y enfermedades (Fase 7, §6.1–§6.2).

Cada registro declara:

* identidad taxonómica y nombres locales;
* cultivos y hospederos documentados;
* **ámbito de presencia**: `national_confirmed` (documentada en El Salvador),
  `regional_confirmed` (Centroamérica, sin registro salvadoreño verificado en
  este repositorio), `international_record` o `unconfirmed_national`;
* condiciones favorecedoras en texto y, solo cuando existe una fuente, una
  ventana cuantitativa marcada como `literature_uncalibrated`;
* daño, monitoreo, manejo integrado, importancia económica;
* fuentes con institución, título y URL;
* calidad de evidencia e incertidumbre.

Una ventana de literatura **no** es un umbral epidemiológico validado para El
Salvador. El motor de riesgo nunca la presenta como probabilidad de presencia.
"""
from __future__ import annotations

PRESENCE_SCOPES = ("national_confirmed", "regional_confirmed",
                   "international_record", "unconfirmed_national")
EVIDENCE_QUALITY = ("high", "moderate", "low")


def _src(institution: str, title: str, url: str) -> dict[str, str]:
    return {"institution": institution, "title": title, "url": url}


CABI = "CABI Compendium (datasheet)"
FAO = "FAO"
OIRSA = "OIRSA"
IICA = "IICA / PROMECAFE"
CENTA = "CENTA (El Salvador)"
IPPC = "IPPC"

_SCOPE_NOTE = ("la presencia documentada en el país no implica presencia "
               "actual en un municipio ni en una parcela")

PESTS: dict[str, dict] = {
    "fall_armyworm": {
        "pest_id": "fall_armyworm",
        "scientific_name": "Spodoptera frugiperda",
        "common_names": ["fall armyworm", "gusano cogollero"],
        "local_names": ["gusano cogollero", "cogollero del maíz"],
        "taxonomy": {"class": "Insecta", "order": "Lepidoptera",
                     "family": "Noctuidae"},
        "affected_crops": ["maize", "sorghum", "rice", "sugarcane"],
        "host_plants": ["Zea mays", "Sorghum bicolor", "Oryza sativa",
                        "gramíneas cultivadas y arvenses"],
        "distribution": {
            "presence_scope": "national_confirmed",
            "countries": ["El Salvador", "Centroamérica", "América"],
            "note": _SCOPE_NOTE,
        },
        "life_cycle": ("huevo → 6 estadios larvarios → pupa en suelo → adulto; "
                       "el daño lo produce la larva en el cogollo"),
        "favoring_conditions": ("temperaturas cálidas y cultivo en etapas "
                                "tempranas; maíz de siembra escalonada"),
        "environmental_windows": [
            {"variable": "temperature_mean_c", "min": 15.0, "max": 30.0,
             "source": CABI, "status": "literature_uncalibrated"},
        ],
        "damage": ("ventanas y perforaciones en hojas jóvenes, destrucción "
                   "del cogollo; daño severo puede reducir el stand"),
        "monitoring": ["inspección de cogollos", "conteo de larvas por planta",
                       "trampas de feromona como apoyo, no como diagnóstico"],
        "ipm": ["muestreo temprano", "control biológico donde esté disponible",
                "rotación y destrucción de residuos", "uso responsable de "
                "insecticidas según registro y etiqueta"],
        "economic_importance": "alta en maíz y sorgo",
        "sources": [
            _src(CABI, "Spodoptera frugiperda (fall armyworm) datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(FAO, "Fall Armyworm: FAO action", "https://www.fao.org/fall-armyworm/en/"),
        ],
        "evidence_quality": "high",
        "uncertainty": ("presencia nacional documentada; incidencia local y "
                        "umbral económico no verificados"),
    },
    "coffee_berry_borer": {
        "pest_id": "coffee_berry_borer",
        "scientific_name": "Hypothenemus hampei",
        "common_names": ["coffee berry borer", "broca del café"],
        "local_names": ["broca del café", "broca"],
        "taxonomy": {"class": "Insecta", "order": "Coleoptera",
                     "family": "Curculionidae"},
        "affected_crops": ["coffee"],
        "host_plants": ["Coffea arabica", "Coffea canephora"],
        "distribution": {
            "presence_scope": "national_confirmed",
            "countries": ["El Salvador", "Centroamérica", "América"],
            "note": _SCOPE_NOTE,
        },
        "life_cycle": ("la hembra perfora el fruto y oviposita en la semilla; "
                       "varias generaciones se solapan dentro del grano"),
        "favoring_conditions": ("frutos disponibles, sombra y temperaturas "
                                "cálidas; mal manejo de residuos de cosecha"),
        "environmental_windows": [
            {"variable": "temperature_mean_c", "min": 20.0, "max": 30.0,
             "source": CABI, "status": "literature_uncalibrated"},
        ],
        "damage": "perforación del grano, pérdida de peso y calidad",
        "monitoring": ["porcentaje de frutos perforados", "muestreo por lotes",
                       "trampas con atrayente como apoyo"],
        "ipm": ["recolección oportuna y completa", "manejo de residuos",
                "sombrío regulado", "control biológico donde esté disponible"],
        "economic_importance": "alta en café",
        "sources": [
            _src(CABI, "Hypothenemus hampei datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(IICA, "Manejo de la broca del café en Centroamérica",
                 "https://promecafe.net/"),
        ],
        "evidence_quality": "high",
        "uncertainty": "presencia nacional; infestación actual no verificada",
    },
    "whitefly": {
        "pest_id": "whitefly",
        "scientific_name": "Bemisia tabaci",
        "common_names": ["sweetpotato whitefly", "mosca blanca"],
        "local_names": ["mosca blanca"],
        "taxonomy": {"class": "Insecta", "order": "Hemiptera",
                     "family": "Aleyrodidae"},
        "affected_crops": ["beans", "tomato", "sweet_pepper", "cucumber",
                           "cabbage"],
        "host_plants": ["Phaseolus vulgaris", "Solanum lycopersicum",
                        "Capsicum spp.", "Cucumis sativus", "hospederos amplios"],
        "distribution": {
            "presence_scope": "national_confirmed",
            "countries": ["El Salvador", "Centroamérica", "América"],
            "note": _SCOPE_NOTE,
        },
        "life_cycle": ("huevo → ninfa → adulto; ciclo corto y solapado en "
                       "clima cálido"),
        "favoring_conditions": ("clima cálido y seco, cultivos escalonados y "
                                "hospederos alternos"),
        "environmental_windows": [
            {"variable": "temperature_mean_c", "min": 20.0, "max": 32.0,
             "source": CABI, "status": "literature_uncalibrated"},
        ],
        "damage": ("succión de savia, fumagina y transmisión de virus "
                   "(begomovirus)"),
        "monitoring": ["conteo de adultos en el envés", "revisión de ninfas",
                       "detección de síntomas virales"],
        "ipm": ["barreras y mallas", "hospederos alternos bajo control",
                "control biológico", "rotación de modos de acción"],
        "economic_importance": "alta en hortalizas y frijol",
        "sources": [
            _src(CABI, "Bemisia tabaci datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(FAO, "Manejo integrado de plagas en hortalizas",
                 "https://www.fao.org/"),
        ],
        "evidence_quality": "high",
        "uncertainty": "presencia nacional; razas y resistencia no verificadas",
    },
    "sugarcane_borer": {
        "pest_id": "sugarcane_borer",
        "scientific_name": "Diatraea saccharalis",
        "common_names": ["sugarcane borer", "barrenador del tallo"],
        "local_names": ["barrenador del tallo de la caña"],
        "taxonomy": {"class": "Insecta", "order": "Lepidoptera",
                     "family": "Crambidae"},
        "affected_crops": ["sugarcane", "maize"],
        "host_plants": ["Saccharum officinarum", "Zea mays"],
        "distribution": {
            "presence_scope": "regional_confirmed",
            "countries": ["Centroamérica", "América"],
            "note": ("presencia regional documentada; no se localizó en este "
                     "repositorio un registro salvadoreño verificado"),
        },
        "life_cycle": ("larva perfora el tallo y completa el desarrollo dentro "
                       "de la caña; pupa en el tallo o residuos"),
        "favoring_conditions": "cañaverales maduros y residuos sin manejo",
        "environmental_windows": [],
        "damage": "galerías en el tallo, pérdida de sacarosa y volcamiento",
        "monitoring": ["disección de tallos", "conteo de entrenudos dañados",
                       "liberaciones de control biológico evaluadas"],
        "ipm": ["manejo de residuos", "control biológico con parasitoides",
                "variedades resistentes donde existan"],
        "economic_importance": "media-alta en caña de azúcar",
        "sources": [
            _src(CABI, "Diatraea saccharalis datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(OIRSA, "Programas fitosanitarios regionales",
                 "https://www.oirsa.org/"),
        ],
        "evidence_quality": "moderate",
        "uncertainty": "presencia salvadoreña no verificada en fuentes de este repositorio",
    },
    "banana_weevil": {
        "pest_id": "banana_weevil",
        "scientific_name": "Cosmopolites sordidus",
        "common_names": ["banana weevil", "picudo del banano"],
        "local_names": ["picudo negro", "picudo del banano"],
        "taxonomy": {"class": "Insecta", "order": "Coleoptera",
                     "family": "Curculionidae"},
        "affected_crops": ["banana", "plantain"],
        "host_plants": ["Musa spp."],
        "distribution": {
            "presence_scope": "regional_confirmed",
            "countries": ["Centroamérica", "América"],
            "note": ("presencia regional; no se verificó un registro "
                     "salvadoreño específico en este repositorio"),
        },
        "life_cycle": "larva barrenando el cormo; adulto de hábitos nocturnos",
        "favoring_conditions": "residuos de cosecha y humedad del suelo",
        "environmental_windows": [],
        "damage": "galerías en el cormo, debilitamiento y volcamiento",
        "monitoring": ["trampas de pseudotallo", "revisión de cormos",
                       "conteo de plantas caídas"],
        "ipm": ["material de siembra limpio", "manejo de residuos",
                "trampas", "control biológico donde esté disponible"],
        "economic_importance": "media en musáceas",
        "sources": [
            _src(CABI, "Cosmopolites sordidus datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(OIRSA, "Sanidad vegetal en musáceas", "https://www.oirsa.org/"),
        ],
        "evidence_quality": "moderate",
        "uncertainty": "presencia salvadoreña no verificada",
    },
}

DISEASES: dict[str, dict] = {
    "coffee_leaf_rust": {
        "disease_id": "coffee_leaf_rust",
        "name": "roya del café",
        "causal_organism": {"scientific_name": "Hemileia vastatrix",
                            "type": "fungus", "kingdom": "Fungi",
                            "phylum": "Basidiomycota"},
        "category": "fungal",
        "affected_crops": ["coffee"],
        "symptoms": ["manchas amarillo-naranja en el envés",
                     "defoliación", "muerte de ramas en ataques severos"],
        "favorable_conditions": ("humedad de hoja prolongada y temperaturas "
                                 "moderadas; sombra densa y dosel húmedo"),
        "environmental_windows": [
            {"variable": "temperature_mean_c", "min": 20.0, "max": 25.0,
             "source": CABI, "status": "literature_uncalibrated"},
        ],
        "transmission": ["esporas por viento y salpicadura de lluvia"],
        "seasonal_behavior": ("brotes asociados al inicio de la estación "
                              "lluviosa y a periodos húmedos"),
        "diagnostics": ["identificación de signos en el envés",
                        "confirmación fitopatológica en laboratorio"],
        "prevention": ["manejo de sombra", "nutrición equilibrada",
                       "podas sanitarias"],
        "management": ["variedades resistentes", "fungicidas según registro",
                       "monitoreo de incidencia"],
        "sources": [
            _src(CABI, "Hemileia vastatrix datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(IICA, "Roya del café en Centroamérica", "https://promecafe.net/"),
        ],
        "evidence_quality": "high",
        "uncertainty": ("presencia nacional documentada; incidencia local y "
                        "razas del patógeno no verificadas"),
        "distribution": {"presence_scope": "national_confirmed",
                         "countries": ["El Salvador", "Centroamérica"],
                         "note": _SCOPE_NOTE},
    },
    "bean_common_bacterial_blight": {
        "disease_id": "bean_common_bacterial_blight",
        "name": "añublo bacteriano común del frijol",
        "causal_organism": {
            "scientific_name": "Xanthomonas axonopodis pv. phaseoli",
            "type": "bacterium", "kingdom": "Bacteria",
            "phylum": "Pseudomonadota"},
        "category": "bacterial",
        "affected_crops": ["beans"],
        "symptoms": ["lesiones necróticas con halo amarillo",
                     "marchitez de plántulas", "reducción del rendimiento"],
        "favorable_conditions": ("lluvia y humedad alta; semilla contaminada "
                                 "y temperaturas cálidas"),
        "environmental_windows": [],
        "transmission": ["semilla contaminada", "salpicadura de lluvia",
                         "restos de cultivo"],
        "seasonal_behavior": "más severo en periodos húmedos",
        "diagnostics": ["síntomas en hoja", "aislamiento bacteriano en laboratorio"],
        "prevention": ["semilla certificada", "rotación", "evitar riego por "
                       "aspersión sobre follaje"],
        "management": ["variedades tolerantes", "manejo de residuos",
                       "productos autorizados según etiqueta"],
        "sources": [
            _src(CABI, "Xanthomonas axonopodis pv. phaseoli datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(CENTA, "Recomendaciones para el cultivo de frijol",
                 "https://www.centa.gob.sv/"),
        ],
        "evidence_quality": "moderate",
        "uncertainty": "presencia regional documentada; cepas locales no verificadas",
        "distribution": {"presence_scope": "regional_confirmed",
                         "countries": ["Centroamérica"], "note": _SCOPE_NOTE},
    },
    "bean_golden_yellow_mosaic": {
        "disease_id": "bean_golden_yellow_mosaic",
        "name": "mosaico dorado del frijol",
        "causal_organism": {"scientific_name": "Bean golden yellow mosaic virus",
                            "type": "virus", "genus": "Begomovirus"},
        "category": "viral",
        "affected_crops": ["beans"],
        "symptoms": ["mosaico amarillo", "enanismo", "vainas deformes"],
        "favorable_conditions": ("poblaciones altas de mosca blanca y clima "
                                 "cálido"),
        "environmental_windows": [],
        "transmission": ["Bemisia tabaci (vector)"],
        "seasonal_behavior": "asociado a la época cálida y a mosca blanca",
        "diagnostics": ["síntomas", "serología o PCR en laboratorio"],
        "prevention": ["variedades resistentes", "manejo del vector",
                       "siembra limpia"],
        "management": ["control integrado de mosca blanca",
                       "eliminación de plantas enfermas"],
        "sources": [
            _src(CABI, "Bean golden yellow mosaic virus datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(IPPC, "Normas fitosanitarias y diagnósticos",
                 "https://www.ippc.int/"),
        ],
        "evidence_quality": "moderate",
        "uncertainty": "presencia regional; incidencia salvadoreña no verificada",
        "distribution": {"presence_scope": "regional_confirmed",
                         "countries": ["Centroamérica"], "note": _SCOPE_NOTE},
    },
    "banana_black_sigatoka": {
        "disease_id": "banana_black_sigatoka",
        "name": "sigatoka negra",
        "causal_organism": {
            "scientific_name": "Pseudocorynespora fijiensis",
            "synonym": "Mycosphaerella fijiensis",
            "type": "fungus", "kingdom": "Fungi", "phylum": "Ascomycota"},
        "category": "fungal",
        "affected_crops": ["banana", "plantain"],
        "symptoms": ["estrías oscuras en hojas", "necrosis extensa",
                     "reducción del área fotosintética"],
        "favorable_conditions": ("alta humedad, lluvia frecuente y temperaturas "
                                 "cálidas"),
        "environmental_windows": [],
        "transmission": ["esporas por viento y agua"],
        "seasonal_behavior": "mayor severidad en la estación lluviosa",
        "diagnostics": ["síntomas foliares", "confirmación micológica"],
        "prevention": ["material de siembra limpio", "manejo de densidad",
                       "drenaje"],
        "management": ["deshoje sanitario", "fungicidas según registro",
                       "variedades con resistencia parcial"],
        "sources": [
            _src(CABI, "Pseudocorynespora fijiensis datasheet",
                 "https://www.cabidigitallibrary.org/product/qi"),
            _src(OIRSA, "Programa regional de musáceas", "https://www.oirsa.org/"),
        ],
        "evidence_quality": "moderate",
        "uncertainty": ("presencia nacional citada en reportes regionales; no "
                        "verificada con un registro primario en este repositorio"),
        "distribution": {"presence_scope": "national_confirmed",
                         "countries": ["El Salvador", "Centroamérica"],
                         "note": _SCOPE_NOTE},
    },
}


def validate_catalog() -> None:
    """Integridad mínima del catálogo; se ejecuta al importar."""
    problems: list[str] = []
    for kind, catalog in (("pest", PESTS), ("disease", DISEASES)):
        for key, record in catalog.items():
            if record.get(f"{kind}_id") != key:
                problems.append(f"{kind} {key}: id inconsistente")
            name = (record.get("scientific_name")
                    or (record.get("causal_organism") or {}).get("scientific_name"))
            if not name or len(str(name).split()) < 2:
                problems.append(f"{kind} {key}: nombre científico no binomial")
            if not record.get("sources"):
                problems.append(f"{kind} {key}: sin fuentes")
            scope = (record.get("distribution") or {}).get("presence_scope")
            if scope not in PRESENCE_SCOPES:
                problems.append(f"{kind} {key}: ámbito de presencia inválido")
            if record.get("evidence_quality") not in EVIDENCE_QUALITY:
                problems.append(f"{kind} {key}: calidad de evidencia inválida")
            for window in record.get("environmental_windows") or []:
                if not window.get("source"):
                    problems.append(f"{kind} {key}: ventana sin fuente")
    if problems:
        raise ValueError("catálogo fitosanitario inválido: " + "; ".join(problems))


validate_catalog()
