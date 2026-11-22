"""Pruebas de la arquitectura documental de la Fase 2.

No prueban que los módulos funcionen (no están implementados): prueban que el
diseño está completo, enlazado y sin integraciones ficticias declaradas.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "verify_phase2", ROOT / "scripts" / "05_verify_phase2_docs.py"
)
verify_phase2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_phase2)


def test_verificacion_documental_sin_problemas():
    problems = verify_phase2.verify()
    assert problems == [], "problemas de documentación:\n" + "\n".join(problems)


def test_los_18_documentos_existen():
    missing = [n for n in verify_phase2.NEW_DOCS if not (DOCS / n).exists()]
    assert missing == []
    assert len(verify_phase2.NEW_DOCS) == 18


def test_los_7_documentos_raiz_conservan_y_amplian():
    for name, marker in verify_phase2.ROOT_DOCS.items():
        text = (ROOT / name).read_text(encoding="utf-8")
        assert marker in text, f"{name} no fue ampliado"
        assert verify_phase2.ROOT_DOC_ANCHORS[name] in text, f"{name} perdió contenido"


MODULE_DOCS = [n for n in verify_phase2.NEW_DOCS if n not in (
    "COMPUTATIONAL_RESOURCE_ESTIMATES.md",
    "MODULE_DEPENDENCY_GRAPH.md",
    "PHASE_2_IMPLEMENTATION_ROADMAP.md",
)]


def test_todo_modulo_declara_estado_y_prioridad():
    assert len(MODULE_DOCS) == 15
    for name in verify_phase2.NEW_DOCS:
        text = (DOCS / name).read_text(encoding="utf-8")
        assert "**Estado:**" in text, name
    for name in MODULE_DOCS:
        text = (DOCS / name).read_text(encoding="utf-8")
        assert re.search(r"Prioridad|Dependencias|Requiere", text, re.IGNORECASE), name


def test_ninguna_fuente_satelital_sin_resolucion():
    """Regla del usuario: no confundir resolución de visualización con real."""
    text = (DOCS / "SATELLITE_MONITORING_ENGINE.md").read_text(encoding="utf-8")
    assert "10 m" in text and "250 m" in text
    assert "resolución" in text.lower()


def test_agentes_no_calculan_variables_cientificas():
    text = (DOCS / "SCIENTIFIC_VALIDATION_PROTOCOL.md").read_text(encoding="utf-8")
    assert "V0" in text and "V4" in text
    twin = (DOCS / "AGRICULTURAL_DIGITAL_TWIN.md").read_text(encoding="utf-8")
    # El gemelo debe exigir sincronización, no ser un visor.
    assert "Sincronización" in twin or "sincronización" in twin


def test_aquacrop_ya_no_es_bsd3():
    text = (ROOT / "DATA_SOURCE_REGISTRY.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        low = line.lower()
        if "aquacrop" in low and "bsd-3" in low:
            assert "no es bsd-3" in low, line
    assert "All rights reserved" in text


def test_estimaciones_computacionales_marcadas_como_estimacion():
    text = (DOCS / "COMPUTATIONAL_RESOURCE_ESTIMATES.md").read_text(encoding="utf-8")
    assert "no medida" in text.lower() or "no medidas" in text.lower()
    assert "209,7 Mpx" in text


def test_api_existente_no_se_elimina():
    """Fase 2 no reemplaza los 13 endpoints de Fase 1."""
    api = (ROOT / "backend" / "agrosv" / "api.py").read_text(encoding="utf-8")
    routes = (
        "/api/health",
        "/api/meta",
        "/api/limitations",
        "/api/territory/departments",
        "/api/topography/elevation",
        "/api/infrastructure/summary",
        "/api/soils/point",
        "/api/tiles/",
    )
    for route in routes:
        assert route in api, f"se eliminó {route}"
    assert len(re.findall(r"@app\.get\(", api)) == 13
