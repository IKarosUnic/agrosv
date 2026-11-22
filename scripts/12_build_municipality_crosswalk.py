#!/usr/bin/env python3
"""Construye la correspondencia oficial municipio → distrito (Decreto 762, 2023).

Fuente: Asamblea Legislativa de El Salvador, distribución publicada el
2023-06-08 (https://www.asamblea.gob.sv/node/12806), derivada de la Ley Especial
para la Reestructuración Municipal (Decreto Legislativo N.° 762, publicado el
2023-06-14).

La página oficial tiene errores de digitalización en seis nombres
(`llopango`, `llobasco`, `lntipucá`, `lzalco`, `lshuatán`, `lstepeque`,
`Menendez`, `Umana`, `Bolivar`). Se corrigen a la grafía oficial conocida y se
registran en la procedencia. No se añaden códigos oficiales porque la fuente no
los publica.

Salida:
    data/reference/municipality_crosswalk_2023.csv
    data/reference/municipality_crosswalk_2023.provenance.json

Uso:
    .venv/bin/python scripts/12_build_municipality_crosswalk.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/reference"
CSV_PATH = OUT_DIR / "municipality_crosswalk_2023.csv"
PROVENANCE_PATH = OUT_DIR / "municipality_crosswalk_2023.provenance.json"

SOURCE_URL = "https://www.asamblea.gob.sv/node/12806"
LEGAL_INSTRUMENT = ("Decreto Legislativo N.° 762, Ley Especial para la "
                    "Reestructuración Municipal")
PUBLISHED = "2023-06-14"
EFFECTIVE = "2024-05-01"
RETRIEVED = date.today().isoformat()

#: department -> municipality -> districts (official distribution).
DISTRIBUTION: dict[str, dict[str, list[str]]] = {
    "Ahuachapán": {
        "Ahuachapán Norte": ["Atiquizaya", "El Refugio", "San Lorenzo", "Turín"],
        "Ahuachapán Centro": ["Ahuachapán", "Apaneca",
                              "Concepción de Ataco", "Tacuba"],
        "Ahuachapán Sur": ["Guaymango", "Jujutla", "San Francisco Menéndez",
                           "San Pedro Puxtla"],
    },
    "San Salvador": {
        "San Salvador Norte": ["Aguilares", "El Paisnal", "Guazapa"],
        "San Salvador Oeste": ["Apopa", "Nejapa"],
        "San Salvador Este": ["Ilopango", "San Martín", "Soyapango",
                              "Tonacatepeque"],
        "San Salvador Centro": ["Ayutuxtepeque", "Mejicanos", "San Salvador",
                                "Cuscatancingo", "Ciudad Delgado"],
        "San Salvador Sur": ["Panchimalco", "Rosario de Mora", "San Marcos",
                             "Santo Tomás", "Santiago Texacuangos"],
    },
    "La Libertad": {
        "La Libertad Norte": ["Quezaltepeque", "San Matías",
                              "San Pablo Tacachico"],
        "La Libertad Centro": ["San Juan Opico", "Ciudad Arce"],
        "La Libertad Oeste": ["Colón", "Jayaque", "Sacacoyo", "Tepecoyo",
                              "Talnique"],
        "La Libertad Este": ["Antiguo Cuscatlán", "Huizúcar",
                             "Nuevo Cuscatlán", "San José Villanueva",
                             "Zaragoza"],
        "La Libertad Costa": ["Chiltiupán", "Jicalapa", "La Libertad",
                              "Tamanique", "Teotepeque"],
        "La Libertad Sur": ["Comasagua", "Santa Tecla"],
    },
    "Chalatenango": {
        "Chalatenango Norte": ["La Palma", "Citalá", "San Ignacio"],
        "Chalatenango Centro": ["Nueva Concepción", "Tejutla", "La Reina",
                                "Agua Caliente", "Dulce Nombre de María",
                                "El Paraíso", "San Francisco Morazán",
                                "San Rafael", "Santa Rita", "San Fernando"],
        "Chalatenango Sur": ["Chalatenango", "Arcatao", "Azacualpa", "Comalapa",
                             "Concepción Quezaltepeque", "El Carrizal",
                             "La Laguna", "Las Vueltas", "Nombre de Jesús",
                             "Nueva Trinidad", "Ojos de Agua", "Potonico",
                             "San Antonio de la Cruz", "San Antonio Los Ranchos",
                             "San Francisco Lempa", "San Isidro Labrador",
                             "San José Cancasque", "San Miguel de Mercedes",
                             "San José Las Flores", "San Luis del Carmen"],
    },
    "Cuscatlán": {
        "Cuscatlán Norte": ["Suchitoto", "San José Guayabal",
                            "Oratorio de Concepción",
                            "San Bartolomé Perulapán", "San Pedro Perulapán"],
        "Cuscatlán Sur": ["Cojutepeque", "San Rafael Cedros", "Candelaria",
                          "Monte San Juan", "El Carmen", "San Cristóbal",
                          "Santa Cruz Michapa", "San Ramón", "El Rosario",
                          "Santa Cruz Analquito", "Tenancingo"],
    },
    "Cabañas": {
        "Cabañas Este": ["Sensuntepeque", "Victoria", "Dolores", "Guacotecti",
                         "San Isidro"],
        "Cabañas Oeste": ["Ilobasco", "Tejutepeque", "Jutiapa", "Cinquera"],
    },
    "La Paz": {
        "La Paz Oeste": ["Cuyultitán", "Olocuilta", "San Juan Talpa",
                         "San Luis Talpa", "San Pedro Masahuat", "Tapalhuaca",
                         "San Francisco Chinameca"],
        "La Paz Centro": ["El Rosario", "Jerusalén", "Mercedes La Ceiba",
                          "Paraíso de Osorio", "San Antonio Masahuat",
                          "San Emigdio", "San Juan Tepezontes",
                          "San Luis La Herradura", "San Miguel Tepezontes",
                          "San Pedro Nonualco", "Santa María Ostuma",
                          "Santiago Nonualco"],
        "La Paz Este": ["San Juan Nonualco", "San Rafael Obrajuelo",
                        "Zacatecoluca"],
    },
    "La Unión": {
        "La Unión Norte": ["Anamorós", "Bolívar", "Concepción de Oriente",
                           "El Sauce", "Lislique", "Nueva Esparta", "Pasaquina",
                           "Polorós", "San José La Fuente",
                           "Santa Rosa de Lima"],
        "La Unión Sur": ["Conchagua", "El Carmen", "Intipucá", "La Unión",
                         "Meanguera del Golfo", "San Alejo", "Yayantique",
                         "Yucuaiquín"],
    },
    "Usulután": {
        "Usulután Norte": ["Santiago de María", "Alegría", "Berlín",
                           "Mercedes Umaña", "Jucuapa", "El Triunfo",
                           "Estanzuelas", "San Buenaventura", "Nueva Granada"],
        "Usulután Este": ["Usulután", "Jucuarán", "San Dionisio",
                          "Concepción Batres", "Santa María", "Ozatlán",
                          "Tecapán", "Santa Elena", "California",
                          "Ereguayquín"],
        "Usulután Oeste": ["Jiquilisco", "Puerto El Triunfo", "San Agustín",
                           "San Francisco Javier"],
    },
    "Sonsonate": {
        "Sonsonate Norte": ["Juayúa", "Nahuizalco", "Salcoatitán",
                            "Santa Catarina Masahuat"],
        "Sonsonate Centro": ["Sonsonate", "Sonzacate", "Nahulingo",
                             "San Antonio del Monte",
                             "Santo Domingo de Guzmán"],
        "Sonsonate Este": ["Izalco", "Armenia", "Caluco", "San Julián",
                           "Cuisnahuat", "Santa Isabel Ishuatán"],
        "Sonsonate Oeste": ["Acajutla"],
    },
    "Santa Ana": {
        "Santa Ana Norte": ["Masahuat", "Metapán",
                            "Santa Rosa Guachipilín", "Texistepeque"],
        "Santa Ana Centro": ["Santa Ana"],
        "Santa Ana Este": ["Coatepeque", "El Congo"],
        "Santa Ana Oeste": ["Candelaria de la Frontera", "Chalchuapa",
                            "El Porvenir", "San Antonio Pajonal",
                            "San Sebastián Salitrillo",
                            "Santiago de la Frontera"],
    },
    "San Vicente": {
        "San Vicente Norte": ["Apastepeque", "Santa Clara", "San Ildefonso",
                              "San Esteban Catarina", "San Sebastián",
                              "San Lorenzo", "Santo Domingo"],
        "San Vicente Sur": ["San Vicente", "Guadalupe", "Verapaz", "Tepetitán",
                            "Tecoluca", "San Cayetano Istepeque"],
    },
    "San Miguel": {
        "San Miguel Norte": ["Ciudad Barrios", "Sesori",
                             "Nuevo Edén de San Juan", "San Gerardo",
                             "San Luis de la Reina", "Carolina",
                             "San Antonio del Mosco", "Chapeltique"],
        "San Miguel Centro": ["San Miguel", "Comacarán", "Uluazapa", "Moncagua",
                              "Quelepa", "Chirilagua"],
        "San Miguel Oeste": ["Chinameca", "Nueva Guadalupe", "Lolotique",
                             "San Jorge", "San Rafael Oriente", "El Tránsito"],
    },
    "Morazán": {
        "Morazán Norte": ["Arambala", "Cacaopera", "Corinto", "El Rosario",
                          "Joateca", "Jocoaitique", "Meanguera", "Perquín",
                          "San Fernando", "San Isidro", "Torola"],
        "Morazán Sur": ["Chilanga", "Delicias de Concepción", "El Divisadero",
                        "Gualococti", "Guatajiagua", "Jocoro",
                        "Lolotiquillo", "Osicala", "San Carlos",
                        "San Francisco Gotera", "San Simón", "Sensembra",
                        "Sociedad", "Yamabal", "Yoloaiquín"],
    },
}

CORRECTIONS = [
    {"source": "llopango", "normalized": "Ilopango"},
    {"source": "llobasco", "normalized": "Ilobasco"},
    {"source": "lntipucá", "normalized": "Intipucá"},
    {"source": "lzalco", "normalized": "Izalco"},
    {"source": "lshuatán", "normalized": "Santa Isabel Ishuatán"},
    {"source": "lstepeque", "normalized": "San Cayetano Istepeque"},
    {"source": "San Francisco Menendez", "normalized": "San Francisco Menéndez"},
    {"source": "Mercedes Umana", "normalized": "Mercedes Umaña"},
    {"source": "Bolivar", "normalized": "Bolívar"},
    {"source": "Huizucar", "normalized": "Huizúcar"},
    {"source": "Chiltuipán", "normalized": "Chiltiupán"},
]


def slug(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    ascii_text = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return "-".join(part for part in
                    "".join(c if c.isalnum() else " " for c in ascii_text).split())


def main() -> int:
    rows = []
    for department, municipalities in DISTRIBUTION.items():
        for municipality, districts in municipalities.items():
            for district in districts:
                rows.append({
                    "department": department,
                    "municipality": municipality,
                    "district": district,
                    "municipality_id": f"SV-MUN-{slug(municipality)}",
                    "district_id": (f"SV-DIS-{slug(department)}-"
                                    f"{slug(municipality)}-{slug(district)}"),
                    "legal_instrument": LEGAL_INSTRUMENT,
                    "effective_date": EFFECTIVE,
                    "source": SOURCE_URL,
                    "official_code": "",
                })
    municipalities = {r["municipality"] for r in rows}
    departments = {r["department"] for r in rows}
    assert len(departments) == 14, len(departments)
    assert len(municipalities) == 44, len(municipalities)
    assert len(rows) == 262, len(rows)
    assert len({r["district_id"] for r in rows}) == 262
    assert len({(r["department"], r["district"]) for r in rows}) == 262

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    checksum = hashlib.sha256(CSV_PATH.read_bytes()).hexdigest()

    provenance = {
        "dataset_id": "municipality_crosswalk_2023",
        "name": "Correspondencia municipio → distrito (reestructuración 2023)",
        "legal_instrument": LEGAL_INSTRUMENT,
        "published": PUBLISHED,
        "effective_date": EFFECTIVE,
        "effective_note": ("la ley rigió las elecciones del 2024-03-03; los "
                           "nuevos concejos asumieron el 2024-05-01"),
        "source": SOURCE_URL,
        "retrieved": RETRIEVED,
        "license": ("Información pública oficial; se atribuye a la Asamblea "
                    "Legislativa de El Salvador"),
        "counts": {"departments": 14, "municipalities": 44, "districts": 262},
        "fields": {
            "department": "departamento",
            "municipality": "municipio nuevo",
            "district": "distrito (antiguo municipio)",
            "municipality_id": "identificador AGROSV, no código oficial",
            "district_id": "identificador AGROSV, no código oficial",
            "official_code": "vacío: la fuente no publica códigos",
        },
        "transformations": [
            "transcripción de la distribución publicada por la Asamblea",
            "normalización de tildes y mayúsculas",
            "identificadores AGROSV derivados del nombre (no oficiales)",
            "verificación de 14 departamentos, 44 municipios y 262 distritos",
        ],
        "corrections": CORRECTIONS,
        "validation_status": ("conteos, unicidad y pertenencia verificados; "
                              "sin validación catastral ni geográfica"),
        "notes": [
            "la fuente es una página legislativa, no un archivo catastral",
            "no se incluyen códigos históricos porque no fueron publicados",
            "los distritos conservan el nombre del municipio histórico",
        ],
        "sha256": checksum,
    }
    PROVENANCE_PATH.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"{CSV_PATH.relative_to(ROOT)}: {len(rows)} filas")
    print(f"{PROVENANCE_PATH.relative_to(ROOT)}: sha256 {checksum[:16]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
