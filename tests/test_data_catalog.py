"""Catálogo nacional: máquina de estados, evidencia y auditoría.

La prueba central es que no se pueda declarar un dataset VALIDATED o INTEGRATED
sin la evidencia correspondiente. Si estas pruebas pasan, el estado del catálogo
es una afirmación verificable y no una etiqueta.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv.data.catalog import (  # noqa: E402
    ALLOWED_TRANSITIONS,
    Catalog,
    CatalogError,
    DatasetRecord,
    DatasetState,
    Evidence,
    EvidenceType,
)
from conftest import require  # noqa: E402

ALL_STATES = {s.value for s in DatasetState}


def record(**overrides) -> DatasetRecord:
    base = dict(
        dataset_id="test_ds",
        name="Dataset de prueba",
        description="Descripción suficientemente larga para el contrato.",
        institution="Institución de prueba",
        source_url="https://example.org/data",
        license="CC BY 4.0",
        redistribution_allowed=True,
        derived_use_allowed=True,
        geographic_coverage="prueba",
        temporal_coverage="2020",
        crs="EPSG:4326",
        spatial_resolution="1 m",
        temporal_resolution="diaria",
        variables=["precipitation"],
        units={"precipitation": "mm"},
        format="GeoJSON",
        size="1 kB",
        methodology="metodología de prueba",
        limitations=["limitación declarada"],
        uncertainty="no cuantificada en la prueba",
        usage_restrictions="ninguna",
        domain="CLIMATE",
    )
    base.update(overrides)
    return DatasetRecord(**base)


def discovery(tmp_path: Path) -> list[Evidence]:
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    return [Evidence.from_file(source, EvidenceType.URL_PROBE, passed=True)]


def test_estados_permitidos_son_los_nueve():
    assert ALL_STATES == {
        "DISCOVERED", "ACCESS_PENDING", "DOWNLOADED", "PARSED", "VALIDATED",
        "INTEGRATED", "RESTRICTED", "UNAVAILABLE", "REJECTED",
    }
    assert ALLOWED_TRANSITIONS[DatasetState.REJECTED] == frozenset()


def test_alta_exige_estado_inicial_y_evidencia(tmp_path):
    cat = Catalog(tmp_path / "catalog.json")
    with pytest.raises(CatalogError):
        cat.add(record(state=DatasetState.VALIDATED), discovery(tmp_path))
    with pytest.raises(CatalogError):
        cat.add(record(), [])
    cat.add(record(), discovery(tmp_path))
    assert cat.get("test_ds").state is DatasetState.DISCOVERED


def test_no_se_puede_saltar_de_descubierto_a_validado(tmp_path):
    cat = Catalog(tmp_path / "catalog.json")
    cat.add(record(), discovery(tmp_path))
    with pytest.raises(CatalogError) as exc:
        cat.transition("test_ds", DatasetState.VALIDATED, discovery(tmp_path))
    assert "no permitida" in str(exc.value)


def test_descargado_exige_artefacto_hash_y_fecha(tmp_path):
    cat = Catalog(tmp_path / "catalog.json")
    cat.add(record(), discovery(tmp_path))
    with pytest.raises(CatalogError):
        cat.transition("test_ds", DatasetState.DOWNLOADED,
                       [Evidence(evidence_type=EvidenceType.FILE_HASH,
                                 reference="ref", passed=True)])
    artifact = tmp_path / "copia.json"
    artifact.write_text('{"a": 1}', encoding="utf-8")
    cat.patch("test_ds", artifacts=[str(artifact)])
    with pytest.raises(CatalogError) as exc:
        cat.transition("test_ds", DatasetState.DOWNLOADED,
                       [Evidence.from_file(artifact, EvidenceType.FILE_HASH)])
    assert "download_date" in str(exc.value)
    cat.patch("test_ds", download_date="2026-01-01")
    updated = cat.transition(
        "test_ds", DatasetState.DOWNLOADED,
        [Evidence.from_file(artifact, EvidenceType.FILE_HASH)])
    assert updated.state is DatasetState.DOWNLOADED


def test_validado_exige_informe_aprobado_y_campos_criticos(tmp_path):
    cat = Catalog(tmp_path / "catalog.json")
    cat.add(record(), discovery(tmp_path))
    artifact = tmp_path / "copia.json"
    artifact.write_text('{"a": 1}', encoding="utf-8")
    cat.patch("test_ds", artifacts=[str(artifact)], download_date="2026-01-01")
    cat.transition("test_ds", DatasetState.DOWNLOADED,
                   [Evidence.from_file(artifact, EvidenceType.FILE_HASH)])
    cat.transition("test_ds", DatasetState.PARSED,
                   [Evidence.from_file(artifact, EvidenceType.PARSE_RESULT,
                                       passed=True)])
    with pytest.raises(CatalogError) as exc:
        cat.transition("test_ds", DatasetState.VALIDATED,
                       [Evidence(evidence_type=EvidenceType.VALIDATION_REPORT,
                                 reference="informe", passed=True,
                                 payload={"status": "PASS", "checks_run": 5})])
    assert "validation_scope" in str(exc.value)

    cat.patch("test_ds", validation_scope="muestra de prueba")
    with pytest.raises(CatalogError) as exc:
        cat.transition("test_ds", DatasetState.VALIDATED,
                       [Evidence(evidence_type=EvidenceType.VALIDATION_REPORT,
                                 reference="informe", passed=True,
                                 payload={"status": "PASS", "checks_run": 2})])
    assert "3 comprobaciones" in str(exc.value)

    ok = cat.transition("test_ds", DatasetState.VALIDATED,
                        [Evidence(evidence_type=EvidenceType.VALIDATION_REPORT,
                                  reference="informe", passed=True,
                                  payload={"status": "PASS_WITH_WARNINGS",
                                           "checks_run": 5})])
    assert ok.state is DatasetState.VALIDATED


def test_integrado_exige_consulta_verificable(tmp_path):
    cat = Catalog(tmp_path / "catalog.json")
    cat.add(record(), discovery(tmp_path))
    artifact = tmp_path / "copia.json"
    artifact.write_text('{"a": 1}', encoding="utf-8")
    cat.patch("test_ds", artifacts=[str(artifact)], download_date="2026-01-01",
              validation_scope="muestra", integration_scope="muestra")
    cat.transition("test_ds", DatasetState.DOWNLOADED,
                   [Evidence.from_file(artifact, EvidenceType.FILE_HASH)])
    cat.transition("test_ds", DatasetState.PARSED,
                   [Evidence.from_file(artifact, EvidenceType.PARSE_RESULT,
                                       passed=True)])
    cat.transition("test_ds", DatasetState.VALIDATED,
                   [Evidence(evidence_type=EvidenceType.VALIDATION_REPORT,
                             reference="informe", passed=True,
                             payload={"status": "PASS", "checks_run": 4})])
    with pytest.raises(CatalogError) as exc:
        cat.transition(
            "test_ds", DatasetState.INTEGRATED,
            [Evidence(evidence_type=EvidenceType.INTEGRATION_RECORD,
                      reference="registro", passed=True,
                      payload={"queryable": False})])
    assert "queryable" in str(exc.value)
    cat.transition(
        "test_ds", DatasetState.INTEGRATED,
        [Evidence(evidence_type=EvidenceType.INTEGRATION_RECORD,
                  reference="registro", passed=True,
                  payload={"queryable": True})])
    assert cat.get("test_ds").integration_scope == "muestra"


def test_rechazado_es_terminal_y_exige_fallo_documentado(tmp_path):
    cat = Catalog(tmp_path / "catalog.json")
    cat.add(record(), discovery(tmp_path))
    with pytest.raises(CatalogError):
        cat.transition("test_ds", DatasetState.REJECTED,
                       [Evidence(evidence_type=EvidenceType.MANUAL_REVIEW,
                                 reference="revisión", passed=True)])
    cat.transition("test_ds", DatasetState.REJECTED,
                   [Evidence(evidence_type=EvidenceType.MANUAL_REVIEW,
                             reference="revisión", passed=False,
                             note="fuente sin datos")])
    with pytest.raises(CatalogError):
        cat.transition("test_ds", DatasetState.DISCOVERED, discovery(tmp_path))


def test_patch_no_modifica_estado(tmp_path):
    cat = Catalog(tmp_path / "catalog.json")
    cat.add(record(), discovery(tmp_path))
    with pytest.raises(CatalogError):
        cat.patch("test_ds", state=DatasetState.VALIDATED)
    cat.patch("test_ds", license="CC BY-SA 4.0")
    assert cat.get("test_ds").license == "CC BY-SA 4.0"
    assert cat.get("test_ds").state is DatasetState.DISCOVERED


def test_campos_criticos_detectan_unidades_y_crs():
    r = record(variables=["precipitation", "ph"],
               units={"precipitation": "mm"}, crs=None)
    missing = r.missing_fields()
    assert "units[ph]" in missing
    assert "crs" in missing
    assert record(units={"ph": ""}, variables=["ph"]).missing_fields() == []


def test_persistencia_y_auditoria(tmp_path):
    path = tmp_path / "catalog.json"
    cat = Catalog(path)
    cat.add(record(), discovery(tmp_path))
    cat.save()
    reloaded = Catalog.load(path)
    assert len(reloaded) == 1
    audit = reloaded.audit()
    assert audit["ok"], audit["problems"]
    assert reloaded.summary()["by_state"]["DISCOVERED"] == 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 4
    assert payload["datasets"][0]["missing_fields"] is not None


def test_doble_alta_falla(tmp_path):
    cat = Catalog(tmp_path / "catalog.json")
    cat.add(record(), discovery(tmp_path))
    with pytest.raises(CatalogError):
        cat.add(record(), discovery(tmp_path))


def test_catalogo_real_auditado_y_con_todos_los_estados():
    from agrosv.data import storage as S

    path = require(S.layout().catalog_path)
    cat = Catalog.load(path)
    audit = cat.audit()
    assert audit["ok"], audit["problems"]
    assert audit["transitions"] >= 20
    states = {r.state.value for r in cat}
    assert states == ALL_STATES, f"faltan estados: {ALL_STATES - states}"
    for r in cat:
        if r.state is DatasetState.VALIDATED:
            assert r.validation_scope
        if r.state is DatasetState.INTEGRATED:
            assert r.integration_scope
        assert r.transitions, f"{r.dataset_id} sin historial de evidencia"
