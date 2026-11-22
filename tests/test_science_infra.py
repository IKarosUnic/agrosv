"""Infraestructura científica transversal: contrato, QC, incertidumbre,
validación, reproducibilidad, versionado y orquestación.

Estas pruebas son la evidencia de que las reglas de Fase 2 no son prosa: si el
contrato deja pasar un resultado sin procedencia, o el manifiesto no detecta un
archivo alterado, la prueba falla.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv import config as C  # noqa: E402
from agrosv.science import (  # noqa: E402
    orchestrator,
    qc,
    registry,
    reproducibility,
    schemas,
    uncertainty,
    validation,
)
from conftest import require  # noqa: E402


# --- Contrato de publicación --------------------------------------------------
def test_resultado_valido_se_publica():
    out = schemas.wrap(
        {"rendimiento": 3.2}, label="simulado", method="AquaCrop 7.3",
        resolution="250 m (SoilGrids)", confidence="baja",
        provenance_id="dem30_wgs84@abc123",
        limitations=["sin calibración local"],
        uncertainty=schemas.Uncertainty(
            method="Monte Carlo de entradas de suelo", n_samples=100,
            seed=7, quantiles={"p10": 2.1, "p50": 3.2, "p90": 4.4}),
    )
    assert out["label"] == "simulado"
    assert out["uncertainty"]["seed"] == 7


def test_resultado_sin_limitaciones_es_invalido():
    with pytest.raises(Exception):
        schemas.ScientificResult(
            value=1, label="derivado", method="D8", resolution="30 m",
            confidence="media", provenance_id="x", limitations=[],
            uncertainty=schemas.Uncertainty(method="ninguna"),
        )


def test_prediccion_con_confianza_alta_exige_cuantiles():
    with pytest.raises(Exception):
        schemas.ScientificResult(
            value=1, label="predicho", method="modelo", resolution="30 m",
            confidence="alta", provenance_id="x", limitations=["a"],
            uncertainty=schemas.Uncertainty(method="intervalo declarado"),
        )


def test_observacion_alta_sin_fuente_es_invalida():
    with pytest.raises(Exception):
        schemas.ScientificResult(
            value=1, label="observado", method="estación", resolution="punto",
            confidence="alta", provenance_id="x", limitations=["a"],
            uncertainty=schemas.Uncertainty(method="instrumental"),
        )


def test_cuantiles_fuera_de_orden_son_rechazados():
    with pytest.raises(Exception):
        schemas.Uncertainty(method="Monte Carlo",
                            quantiles={"p10": 9, "p50": 5, "p90": 1})


# --- Incertidumbre ------------------------------------------------------------
def test_monte_carlo_exige_semilla():
    with pytest.raises(ValueError):
        uncertainty.monte_carlo(
            lambda a: a,
            {"a": uncertainty.Distribution("uniform", {"low": 0, "high": 1})},
            n=100, seed=None,
        )


def test_monte_carlo_es_determinista_con_la_misma_semilla():
    inputs = {"x": uncertainty.Distribution("normal", {"mean": 10, "sd": 2})}
    fn = lambda x: x * 2  # noqa: E731
    a = uncertainty.monte_carlo(fn, inputs, n=500, seed=42)
    b = uncertainty.monte_carlo(fn, inputs, n=500, seed=42)
    assert a["quantiles"] == b["quantiles"]
    c = uncertainty.monte_carlo(fn, inputs, n=500, seed=43)
    assert c["quantiles"] != a["quantiles"]


def test_monte_carlo_rechaza_muestras_insuficientes():
    with pytest.raises(ValueError):
        uncertainty.monte_carlo(
            lambda x: x,
            {"x": uncertainty.Distribution("uniform", {"low": 0, "high": 1})},
            n=5, seed=1,
        )


def test_distribucion_sin_parametros_falla():
    with pytest.raises(ValueError):
        uncertainty.Distribution("normal", {"mean": 1}).validate()


def test_robust_z_y_linea_base_constante():
    base = np.arange(1, 10)
    assert uncertainty.robust_z(5, base) == pytest.approx(0.0)
    assert np.isnan(uncertainty.robust_z(5, [3, 3, 3, 3]))


def test_cobertura_de_intervalos():
    out = uncertainty.coverage([(0, 1), (0, 1), (0, 1)], [0.5, 2.0, 0.2])
    assert out["inside"] == 2
    assert out["coverage"] == pytest.approx(2 / 3)


def test_summarize_cuantiles_crecientes():
    out = uncertainty.summarize(np.arange(100))
    q = out["quantiles"]
    assert q["p10"] < q["p50"] < q["p90"]


# --- Validación ---------------------------------------------------------------
def test_metricas_perfectas():
    y = [1.0, 2.0, 3.0, 4.0]
    m = validation.metrics(y, y)
    assert m["bias"] == pytest.approx(0)
    assert m["rmse"] == pytest.approx(0)
    assert m["r2"] == pytest.approx(1)
    assert m["nse"] == pytest.approx(1)
    assert m["kge"] == pytest.approx(1)


def test_metricas_con_sesgo_conocido():
    m = validation.metrics([1, 2, 3, 4], [2, 3, 4, 5])
    assert m["bias"] == pytest.approx(1)
    assert m["mae"] == pytest.approx(1)
    assert m["rmse"] == pytest.approx(1)


def test_metricas_exigen_pares_suficientes():
    with pytest.raises(ValueError):
        validation.metrics([1, 2], [1, 2])


def test_niveles_de_evidencia_no_se_inflan():
    assert validation.evidence_level(2)["level"] == "V1"
    assert validation.evidence_level(50, reference_scale="department")["level"] == "V1"
    assert validation.evidence_level(
        20, reference_scale="department", observation_source="BCR"
    )["level"] == "V2"
    assert validation.evidence_level(
        40, reference_scale="point", observation_source="SNET", independent=True
    )["level"] == "V4"


def test_informe_advierte_sin_validacion_externa():
    rep = validation.report([1, 2, 3, 4], [1.1, 2.1, 2.9, 4.2])
    assert rep["evidence"]["level"] in {"V0", "V1"}
    assert any("validación externa" in w for w in rep["warnings"])


# --- Reproducibilidad ---------------------------------------------------------
def test_manifest_determinista_y_verificable(tmp_path):
    src = tmp_path / "entrada.txt"
    src.write_text("datos", encoding="utf-8")
    out = tmp_path / "salida.txt"
    out.write_text("resultado", encoding="utf-8")

    a = reproducibility.build_manifest(name="prueba", inputs=[src],
                                       params={"cultivo": "maiz"}, seed=11,
                                       outputs=[out])
    b = reproducibility.build_manifest(name="prueba", inputs=[src],
                                       params={"cultivo": "maiz"}, seed=11,
                                       outputs=[out])
    assert a.run_id == b.run_id, "el run_id no debe depender de la fecha"
    assert a.payload["created_at"]  # pero sí se registra la fecha de ejecución

    path = a.write(tmp_path / "run.json")
    assert reproducibility.verify_manifest(path)["reproducible"] is True

    out.write_text("resultado alterado", encoding="utf-8")
    check = reproducibility.verify_manifest(path)
    assert check["reproducible"] is False
    assert any("hash distinto" in p for p in check["problems"])


def test_run_id_cambia_con_los_parametros(tmp_path):
    src = tmp_path / "e.txt"
    src.write_text("x", encoding="utf-8")
    a = reproducibility.build_manifest(name="p", inputs=[src], params={"v": 1}, seed=1)
    b = reproducibility.build_manifest(name="p", inputs=[src], params={"v": 2}, seed=1)
    assert a.run_id != b.run_id


# --- Versionado ---------------------------------------------------------------
def test_catalogo_deriva_de_los_manifiestos():
    catalog = registry.catalog()
    if not catalog:
        pytest.skip("sin artefactos procesados")
    for ds in catalog:
        assert ds.provenance_id, f"{ds.layer} sin provenance_id"
        assert ds.dataset_version.startswith(ds.layer)
        assert ds.sha256


def test_hash_de_un_dataset_coincide():
    target = [d for d in registry.catalog() if d.layer == "relief_class"]
    if not target:
        pytest.skip("relief_class no generado")
    result = registry.verify(target[0])
    assert result["hash_matches"] is True, result


def test_ledger_y_licencias():
    ledger = registry.ledger()
    assert ledger["count"] == len(ledger["datasets"])
    lic = registry.licenses()
    assert isinstance(lic, dict)


# --- QC -----------------------------------------------------------------------
def test_qc_raster_valido():
    path = require(C.RELIEF_CLASS)
    rep = qc.qc_raster(path).as_dict()
    assert rep["ok"] is True, rep


def test_qc_vector_territorio():
    path = require(C.TERRITORY_GPKG)
    rep = qc.qc_vector(path, "adm1", expected_crs=C.CRS_STORAGE,
                       bounds=C.SV_BOUNDS).as_dict()
    assert rep["ok"] is True, rep


def test_qc_detecta_raster_vacio(tmp_path):
    import rasterio
    from rasterio.transform import from_origin

    path = tmp_path / "vacio.tif"
    with rasterio.open(path, "w", driver="GTiff", width=8, height=8, count=1,
                       dtype="float32", crs="EPSG:4326",
                       transform=from_origin(-89, 14, 0.01, 0.01),
                       nodata=-9999.0) as ds:
        ds.write(np.full((8, 8), -9999.0, dtype="float32"), 1)

    rep = qc.qc_raster(path).as_dict()
    assert rep["ok"] is False
    assert any("válidas" in c["check"] for c in rep["failed"])


def test_qc_detecta_geometria_duplicada(tmp_path):
    import geopandas as gpd
    from shapely.geometry import box

    gdf = gpd.GeoDataFrame({"id": [1, 2]},
                           geometry=[box(0, 0, 1, 1), box(0, 0, 1, 1)],
                           crs="EPSG:4326")
    path = tmp_path / "dup.gpkg"
    gdf.to_file(path, layer="dup")
    rep = qc.qc_vector(path, "dup").as_dict()
    assert any("duplicadas" in w["check"] for w in rep["warnings"])


def test_qc_artefacto_ausente(tmp_path):
    rep = qc.qc_raster(tmp_path / "no_existe.tif").as_dict()
    assert rep["ok"] is False


# --- Orquestador --------------------------------------------------------------
def test_orden_topologico_y_ciclo():
    t1 = orchestrator.Task("a", lambda: 1)
    t2 = orchestrator.Task("b", lambda: 2, depends_on=("a",))
    assert [t.name for t in orchestrator.topological_order([t2, t1])] == ["a", "b"]

    with pytest.raises(ValueError):
        orchestrator.topological_order([
            orchestrator.Task("x", lambda: 1, depends_on=("y",)),
            orchestrator.Task("y", lambda: 1, depends_on=("x",)),
        ])
    with pytest.raises(ValueError):
        orchestrator.topological_order([orchestrator.Task("z", lambda: 1,
                                                          depends_on=("falta",))])


def test_reintentos_y_fallo_registrado(tmp_path):
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("fallo transitorio")
        return "ok"

    result = orchestrator.run_plan([
        orchestrator.Task("flaky", flaky, retries=1),
        orchestrator.Task("roto", lambda: (_ for _ in ()).throw(ValueError("x"))),
    ], state_path=tmp_path / "state.json")

    assert result.states["flaky"]["status"] == "ok"
    assert result.states["flaky"]["attempts"] == 2
    assert result.states["roto"]["status"] == "failed"
    assert "ValueError" in result.states["roto"]["error"]["type"]
    assert result.ok is False


def test_dependencia_fallida_bloquea_y_reanudar_no_reejecuta(tmp_path):
    state = tmp_path / "state.json"
    ejecutadas = {"n": 0}

    def cuenta():
        ejecutadas["n"] += 1
        return "hecho"

    plan = [
        orchestrator.Task("base", cuenta),
        orchestrator.Task("hija", lambda: "no debería correr", depends_on=("base",)),
    ]
    r1 = orchestrator.run_plan(plan, state_path=state)
    assert r1.ok is True
    assert ejecutadas["n"] == 1

    r2 = orchestrator.run_plan(plan, state_path=state, resume=True)
    assert r2.ok is True
    assert ejecutadas["n"] == 1, "resume no debe repetir trabajo completado"
    assert r2.states["base"]["resumed"] is True

    r3 = orchestrator.run_plan(
        [orchestrator.Task("falla", lambda: 1 / 0),
         orchestrator.Task("dependiente", lambda: 1, depends_on=("falla",))],
        state_path=tmp_path / "s2.json")
    assert r3.states["dependiente"]["status"] == "skipped"
