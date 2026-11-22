#!/usr/bin/env python3
"""Verifica la entrega documental de la Fase 2 de AGROSV.

Comprueba, sin red:
  1. Los 18 documentos nuevos existen y tienen las secciones obligatorias.
  2. Los 7 documentos raíz conservan su contenido y añaden la sección de Fase 2.
  3. Todos los enlaces internos a documentos existentes resuelven.
  4. Los 13 módulos A–M están referenciados en el grafo de dependencias.
  5. El registro de fuentes ya no atribuye BSD-3 a AquaCrop.

Uso:
    python scripts/05_verify_phase2_docs.py            # informe
    python scripts/05_verify_phase2_docs.py --quiet     # solo exit code
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

NEW_DOCS = [
    "SATELLITE_MONITORING_ENGINE.md",
    "CROP_HEALTH_AND_PEST_SURVEILLANCE.md",
    "CROP_SIMULATION_ENGINE.md",
    "FARM_AND_PARCEL_MANAGEMENT.md",
    "AGRICULTURAL_ECONOMIC_INTELLIGENCE.md",
    "AGROCLIMATIC_EARLY_WARNING.md",
    "URBAN_AGRICULTURE_ENGINE.md",
    "AGRICULTURAL_DIGITAL_TWIN.md",
    "CLIMATE_CHANGE_SCENARIOS.md",
    "HYDROLOGICAL_SIMULATION.md",
    "BIODIVERSITY_AND_ECOSYSTEM_SERVICES.md",
    "COMMUNITY_DATA_CONTRIBUTION.md",
    "SCIENTIFIC_EXPERIMENT_PLATFORM.md",
    "OPEN_DATA_AND_PUBLIC_API.md",
    "SCIENTIFIC_VALIDATION_PROTOCOL.md",
    "COMPUTATIONAL_RESOURCE_ESTIMATES.md",
    "MODULE_DEPENDENCY_GRAPH.md",
    "PHASE_2_IMPLEMENTATION_ROADMAP.md",
]

# Cada documento debe declarar su alcance negativo (qué no hace / qué no puede)
# y su posición en la arquitectura. Los documentos transversales usan
# "Incertidumbre" o "Riesgos" donde un módulo usa "Limitaciones".
LIMIT_SECTIONS = ("Limitaciones", "Incertidumbre", "Riesgos")
DEPENDENCY_SECTIONS = ("Dependencias", "Prioridad", "Priorización")

ROOT_DOCS = {
    "PROJECT_VISION.md": "## 10. Ampliación de visión",
    "SYSTEM_ARCHITECTURE.md": "## 12. Arquitectura de Fase 2",
    "DATA_SOURCE_REGISTRY.md": "## 8. Ampliación Fase 2",
    "DATA_PIPELINE.md": "## 12. Pipeline de Fase 2",
    "SCIENTIFIC_VALIDATION.md": "## 12. Validación de Fase 2",
    "IMPLEMENTATION_ROADMAP.md": "## 13. Fase 2",
    "RISKS_AND_LIMITATIONS.md": "## 11. Riesgos de la Fase 2",
}

# Secciones mínimas que la Fase 1 ya tenía y no deben desaparecer.
ROOT_DOC_ANCHORS = {
    "PROJECT_VISION.md": "## 1. Qué es AGROSV",
    "SYSTEM_ARCHITECTURE.md": "## 1. Principio rector",
    "DATA_SOURCE_REGISTRY.md": "## 2. Tabla maestra",
    "DATA_PIPELINE.md": "## 2. Flujo por etapas",
    "SCIENTIFIC_VALIDATION.md": "## 1. Qué se valida",
    "IMPLEMENTATION_ROADMAP.md": "## 1. Mapa de fases",
    "RISKS_AND_LIMITATIONS.md": "## 1. Riesgos técnicos",
}

MODULES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]

LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?:|#|mailto:)([^)#]+\.md)(?:#[^)]*)?\)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_new_docs() -> list[str]:
    problems: list[str] = []
    for name in NEW_DOCS:
        path = DOCS / name
        if not path.exists():
            problems.append(f"falta el documento docs/{name}")
            continue
        text = _read(path)
        if not text.startswith("# "):
            problems.append(f"docs/{name}: no empieza con un título H1")
        if "**Estado:**" not in text:
            problems.append(f"docs/{name}: falta la línea **Estado:**")
        low = text.lower()
        if not any(s.lower() in low for s in LIMIT_SECTIONS):
            problems.append(f"docs/{name}: no declara limitaciones ni incertidumbre")
        if not any(s.lower() in low for s in DEPENDENCY_SECTIONS):
            problems.append(f"docs/{name}: no declara dependencias ni prioridad")
        if len(text.splitlines()) < 40:
            problems.append(f"docs/{name}: demasiado corto para ser un diseño")
    return problems


def check_root_docs() -> list[str]:
    problems: list[str] = []
    for name, marker in ROOT_DOCS.items():
        path = ROOT / name
        if not path.exists():
            problems.append(f"falta {name}")
            continue
        text = _read(path)
        if marker not in text:
            problems.append(f"{name}: no contiene '{marker}'")
        anchor = ROOT_DOC_ANCHORS[name]
        if anchor not in text:
            problems.append(f"{name}: se perdió la sección original '{anchor}'")
    return problems


def check_links() -> list[str]:
    problems: list[str] = []
    files = sorted(DOCS.glob("*.md")) + [ROOT / n for n in ROOT_DOCS]
    for path in files:
        if not path.exists():
            continue
        for target in LINK_RE.findall(_read(path)):
            target = target.strip()
            if target.startswith("/"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                problems.append(f"{path.name}: enlace roto -> {target}")
    return problems


def check_dependency_graph() -> list[str]:
    path = DOCS / "MODULE_DEPENDENCY_GRAPH.md"
    if not path.exists():
        return ["falta docs/MODULE_DEPENDENCY_GRAPH.md"]
    text = _read(path)
    problems = []
    for letter in MODULES:
        if not re.search(rf"\b{letter} (Satélite|Fitosanitario|Simulación|Parcelas|"
                         rf"Economía|Alertas|Urbano|Gemelo digital|Cambio climático|"
                         rf"Hidrología|Biodiversidad|Comunidad|Experimentos)\b", text) and \
           not re.search(rf"\| {letter} ", text):
            problems.append(f"grafo: el módulo {letter} no aparece en la matriz")
    if "P1" not in text or "P4" not in text:
        problems.append("grafo: falta la priorización P1–P4")
    return problems


def check_licence_correction() -> list[str]:
    text = _read(ROOT / "DATA_SOURCE_REGISTRY.md")
    problems = []
    if "AquaCrop" not in text:
        problems.append("registro: no menciona AquaCrop")
    for line in text.splitlines():
        low = line.lower()
        if "aquacrop" in low and "bsd-3" in low and "no es bsd-3" not in low:
            problems.append("registro: AquaCrop sigue atribuido a BSD-3")
    if "All rights reserved" not in text:
        problems.append("registro: falta la corrección de licencia de AquaCrop")
    return problems


def check_no_placeholders() -> list[str]:
    problems: list[str] = []
    for path in sorted(DOCS.glob("*.md")):
        text = _read(path)
        for token in ("TODO", "TBD", "lorem ipsum", "XXX"):
            if token in text:
                problems.append(f"docs/{path.name}: contiene marcador '{token}'")
    return problems


def verify() -> list[str]:
    problems: list[str] = []
    problems += check_new_docs()
    problems += check_root_docs()
    problems += check_links()
    problems += check_dependency_graph()
    problems += check_licence_correction()
    problems += check_no_placeholders()
    return problems


def main() -> int:
    problems = verify()
    quiet = "--quiet" in sys.argv
    if problems:
        print(f"FASE 2 — {len(problems)} problema(s):")
        for item in problems:
            print(f"  - {item}")
        return 1
    if not quiet:
        print("FASE 2 — verificación documental OK")
        print(f"  documentos nuevos: {len(NEW_DOCS)}")
        print(f"  documentos raíz actualizados: {len(ROOT_DOCS)}")
        print(f"  módulos en el grafo: {len(MODULES)}")
        print(f"  documentos en docs/: {len(list(DOCS.glob('*.md')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
