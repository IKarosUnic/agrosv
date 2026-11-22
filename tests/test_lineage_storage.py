"""Linaje verificable y arquitectura de almacenamiento."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.data import lineage as LIN  # noqa: E402
from agrosv.data import storage as S  # noqa: E402


def test_nombres_de_artefacto_normalizados():
    name = S.artifact_name(source_id="chirps3", variable="precipitation",
                           resolution="0.05 deg", version="v3.0",
                           date="2026-01-15", ext="tif")
    assert name == "chirps3_precipitation_0p05deg_2026-01-15_v3.0.tif"
    assert S.encode_resolution("250 m") == "250m"
    assert S.encode_resolution("1 km") == "1km"
    with pytest.raises(ValueError):
        S.encode_resolution("muy fino")
    with pytest.raises(ValueError):
        S.artifact_name(source_id="", variable="x", resolution="1 m",
                        version="v1", date="2026-01-01", ext="tif")
    assert S.slug("Cañas Dulces") == "canas-dulces"


def test_politica_git_por_zona(tmp_path):
    lay = S.DataLayout(root=tmp_path / "data")
    S.ensure_layout(lay)
    raw = lay.raw / "x.tif"
    raw.write_bytes(b"0")
    decision = S.git_tracking_decision(raw, lay)
    assert decision["track"] is False
    assert decision["zone"] == "raw"

    small = lay.validated / "small.json"
    small.write_text("{}", encoding="utf-8")
    assert S.git_tracking_decision(small, lay)["track"] is True

    big = lay.validated / "big.tif"
    big.write_bytes(b"0" * (26 * 1024 * 1024))
    decision = S.git_tracking_decision(big, lay)
    assert decision["track"] is False
    assert "límite" in decision["reason"]


def test_almacen_por_contenido_no_duplica(tmp_path):
    lay = S.DataLayout(root=tmp_path / "data")
    S.ensure_layout(lay)
    first = tmp_path / "a.bin"
    first.write_bytes(b"mismo contenido")
    second = tmp_path / "b.bin"
    second.write_bytes(b"mismo contenido")
    path_a, sha_a, new_a = S.store_object(lay, first)
    path_b, sha_b, new_b = S.store_object(lay, second)
    assert new_a is True and new_b is False
    assert path_a == path_b
    assert sha_a == sha_b


def test_promocion_verifica_hash_y_no_sobrescribe(tmp_path):
    lay = S.DataLayout(root=tmp_path / "data")
    S.ensure_layout(lay)
    staged = lay.staging / "x.json"
    staged.write_text('{"a": 1}', encoding="utf-8")
    result = S.promote(lay, staged, dataset_id="ds", filename="x.json")
    assert result["promoted"] is True
    again = S.promote(lay, staged, dataset_id="ds", filename="x.json")
    assert again["duplicate"] is True

    staged.write_text('{"a": 2}', encoding="utf-8")
    with pytest.raises(FileExistsError):
        S.promote(lay, staged, dataset_id="ds", filename="x.json")


def test_manifiesto_de_ejecucion_es_reproducible(tmp_path):
    source = tmp_path / "in.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")
    output = tmp_path / "out.csv"
    output.write_text("a,b\n1,2\n", encoding="utf-8")
    manifests = tmp_path / "manifests"
    first = LIN.record_derivation(
        dataset_id="ds", name="prueba", version="1.0",
        steps=[LIN.Step("copia", "test", "1.0", {"x": 1})],
        input_paths=[source], output_paths=[output],
        manifests_dir=manifests, validation_state="VALIDATED")
    second = LIN.record_derivation(
        dataset_id="ds", name="prueba", version="1.0",
        steps=[LIN.Step("copia", "test", "1.0", {"x": 1})],
        input_paths=[source], output_paths=[output],
        manifests_dir=manifests, validation_state="VALIDATED")
    assert first.run_id == second.run_id, "misma receta e insumos, mismo run_id"
    assert Path(first.manifest_path).exists()

    graph = LIN.LineageGraph(tmp_path / "lineage.json")
    graph.add(first)
    graph.save()
    info = graph.explain(output)
    assert info["sha256"]
    assert info["reconstructable"] is True
    assert info["root_inputs"][0]["sha256"]
    assert graph.datasets_for(output) == ["ds"]
    assert graph.verify()["ok"] is True


def test_manifiesto_detecta_archivo_alterado(tmp_path):
    source = tmp_path / "in.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    output = tmp_path / "out.csv"
    output.write_text("a\n1\n", encoding="utf-8")
    record = LIN.record_derivation(
        dataset_id="ds", name="prueba", version="1.0",
        steps=[LIN.Step("copia", "test", "1.0", {})],
        input_paths=[source], output_paths=[output],
        manifests_dir=tmp_path / "manifests")
    graph = LIN.LineageGraph(tmp_path / "lineage.json", [record])
    assert graph.verify()["ok"] is True
    output.write_text("a\n2\n", encoding="utf-8")
    result = graph.verify()
    assert result["ok"] is False
    assert any("hash distinto" in p for p in result["results"][0]["problems"])


def test_artefacto_sin_linaje_no_es_trazable(tmp_path):
    orphan = tmp_path / "huerfano.csv"
    orphan.write_text("x\n1\n", encoding="utf-8")
    graph = LIN.LineageGraph(tmp_path / "lineage.json")
    with pytest.raises(LIN.UntraceableArtifact):
        graph.explain(orphan)
    with pytest.raises(LIN.UntraceableArtifact):
        graph.assert_traceable(orphan)


def test_derivacion_sin_pasos_o_salidas_se_rechaza(tmp_path):
    source = tmp_path / "in.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(LIN.LineageError):
        LIN.record_derivation(dataset_id="ds", name="x", version="1",
                             steps=[], input_paths=[source],
                             output_paths=[source],
                             manifests_dir=tmp_path / "m")
    with pytest.raises(LIN.LineageError):
        LIN.record_derivation(dataset_id="ds", name="x", version="1",
                             steps=[LIN.Step("s", "t", "1")],
                             input_paths=[source], output_paths=[],
                             manifests_dir=tmp_path / "m")


def test_grafo_real_verificado():
    from conftest import require

    path = require(S.layout().lineage_path)
    graph = LIN.LineageGraph.load(path)
    assert graph.records
    verification = graph.verify()
    assert verification["ok"], verification["results"]
    assert graph.summary()["datasets"]


def test_politica_de_zonas_completa():
    manifest = S.zone_manifest()
    assert set(manifest["zones"]) == set(S.ZONES)
    assert manifest["zones"]["staging"]["git"] is False
    assert manifest["zones"]["manifests"]["git"] is True
