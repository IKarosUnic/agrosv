"""Motor de calidad e incertidumbre: lo que debe fallar, falla."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.data import confidence as CONF  # noqa: E402
from agrosv.data import quality as Q  # noqa: E402
from agrosv.data import temporal as T  # noqa: E402


def codes(findings) -> set[str]:
    return {f.code for f in findings}


def test_precipitacion_negativa_es_error():
    findings = Q.check_numeric([0.0, 2.5, -4.0], "precipitation",
                               declared_unit="mm")
    assert "fuera_de_dominio" in codes(findings)
    assert any(f.code == "fuera_de_dominio" and f.severity == "error"
               for f in findings)


def test_ph_imposible_es_error():
    findings = Q.check_numeric([6.4, 95.0], "ph", declared_unit="")
    assert any(f.code == "fuera_de_dominio" and f.severity == "error"
               for f in findings)


def test_unidad_incompatible_es_error():
    findings = Q.check_numeric([1.0, 2.0], "precipitation",
                               declared_unit="degC")
    assert "unidad_incompatible" in codes(findings)


def test_serie_constante_es_sospechosa():
    findings = Q.check_numeric([5.0] * 20, "temperature", declared_unit="degC")
    assert "serie_constante" in codes(findings)
    assert all(f.severity != "error" for f in findings
               if f.code == "serie_constante")


def test_centinela_no_se_interpreta_como_medicion():
    findings = Q.check_numeric([1.0, -999.0, 2.0], "precipitation",
                               declared_unit="mm")
    assert "centinela_como_dato" in codes(findings)
    assert any(f.code == "centinela_como_dato" and f.severity == "error"
               for f in findings)


def test_ausencia_y_cero_se_distinguen():
    counts = Q.check_missing_vs_zero([0.0, 0.0, None, -999.0])
    assert counts["zeros"] == 2
    assert counts["missing"] == 1
    assert counts["sentinels"] == 1
    assert counts["distinct"] is True


def test_suma_textural_fuera_de_cien_se_informa():
    findings = Q.check_texture([30.0, 40.0], [60.0, 50.0], [30.0, 20.0])
    assert "suma_textural" in codes(findings)
    finding = next(f for f in findings if f.code == "suma_textural")
    assert finding.count == 2
    assert "no se renormaliza" in str(finding.detail)


def test_coordenadas_fuera_de_rango_y_de_cobertura():
    findings = Q.check_spatial_points([-89.2, 200.0], [13.7, 13.8])
    assert "coordenadas_fuera_de_rango" in codes(findings)
    findings = Q.check_spatial_points(
        [-89.2, -70.0], [13.7, 5.0], bounds=(-90.2, 12.9, -87.6, 14.5))
    assert "fuera_de_cobertura" in codes(findings)


def test_serie_temporal_se_valida_en_el_motor():
    spec = T.TimeSeriesSpec(
        variable="precipitation", unit="mm",
        evidence_class=T.EvidenceClass.OBSERVATION,
        frequency=T.Frequency.DAILY, time_basis="local",
        aggregation=T.Aggregation.SUM, dataset_id="ds", source_id="src")
    findings = Q.check_temporal(
        ["2024-01-01", "2024-01-01", "2024-01-04"],
        [1.0, 2.0, 3.0], spec)
    assert "periodos_duplicados" in codes(findings)
    assert "periodos_faltantes" in codes(findings)


def test_intercomparacion_no_eleva_nivel_de_validacion():
    result = Q.compare_sources(
        "nasa_power", [25.0, 26.0, 27.0, 28.0] * 10,
        "open_meteo", [25.5, 26.5, 27.5, 28.5] * 10,
        variable="temperature", unit="degC",
        evidence_a=T.EvidenceClass.REANALYSIS,
        evidence_b=T.EvidenceClass.REANALYSIS,
        tolerance_pct=5.0)
    assert result["comparison_class"] == "intercomparison"
    assert result["evidence"] is None
    assert "NO incrementa" in result["evidence_use"]
    assert result["metrics"]["n"] == 40


def test_validacion_contra_observacion_si_genera_nivel():
    observed = [10.0 + i * 0.1 for i in range(40)]
    modeled = [10.2 + i * 0.1 for i in range(40)]
    result = Q.compare_sources(
        "modelo", modeled, "estacion", observed,
        variable="temperature", unit="degC",
        evidence_a=T.EvidenceClass.SIMULATION,
        evidence_b=T.EvidenceClass.OBSERVATION,
        observation_source="SNET estación piloto",
        reference_scale="point")
    assert result["comparison_class"] == "comparison"
    assert result["evidence"]["level"] in {"V2", "V3"}
    assert result["evidence"]["n"] == 40


def test_informe_resume_estado_y_sirve_de_evidencia(tmp_path):
    report = Q.QualityReport("ds", "artefacto", checks_run=3)
    report.add(Q.Finding("x", "warning", "aviso"))
    assert report.status == "PASS_WITH_WARNINGS"
    report.add(Q.Finding("y", "error", "error"))
    assert report.status == "FAIL"
    path = report.save(tmp_path)
    assert path.exists()
    assert report.report_id in path.name


def test_modelo_sin_cuantificar_no_produce_confianza_alta():
    model = CONF.unquantified_template(dataset_id="ds", variable="precipitation",
                                       unit="mm")
    label = model.confidence_label()
    assert label["confidence"] == "baja"
    assert len(label["unquantified_components"]) == 6
    assert model.relative_uncertainty() is None


def test_compuesto_sin_pesos_se_rechaza():
    model = CONF.unquantified_template(dataset_id="ds", variable="ph", unit="")
    with pytest.raises(CONF.UncertaintyError):
        model.composite()


def test_compuesto_con_pesos_pero_sin_cuantificar_se_rechaza():
    model = CONF.unquantified_template(dataset_id="ds", variable="ph", unit="")
    weights = {c.value: 1 / 6 for c in CONF.UncertaintyComponent}
    with pytest.raises(CONF.UncertaintyError):
        model.composite(weights=weights)


def test_modelo_completo_produce_etiqueta_y_compuesto():
    components = {
        c: CONF.ComponentStatement(
            component=c, quantified=True, method="prueba declarada",
            relative_uncertainty=0.02, basis="repeticiones")
        for c in CONF.UncertaintyComponent
    }
    model = CONF.UncertaintyModel(
        dataset_id="ds", variable="precipitation", unit="mm",
        components=components, methodology="propagación de cuadratura declarada",
        reference_value=100.0)
    label = model.confidence_label()
    assert label["confidence"] == "alta"
    assert model.relative_uncertainty() == pytest.approx(
        0.02 * (6 ** 0.5), rel=1e-6)
    weights = {
        "measurement": 0.4, "model": 0.1, "spatial": 0.2,
        "temporal": 0.1, "classification": 0.1, "provenance": 0.1,
    }
    composite = model.composite(weights=weights)
    assert composite["confidence"] == "alta"
    assert composite["weights"] == weights


def test_componente_no_cuantificado_exige_motivo():
    with pytest.raises(CONF.UncertaintyError):
        CONF.ComponentStatement(
            component=CONF.UncertaintyComponent.MEASUREMENT, quantified=False)


def test_resolucion_no_es_precision():
    with pytest.raises(CONF.UncertaintyError):
        CONF.assert_resolution_is_not_accuracy({"resolution": "10 m"})
    with pytest.raises(CONF.UncertaintyError):
        CONF.assert_resolution_is_not_accuracy(
            {"resolution": "10 m", "accuracy": "5 m"})
    ok = CONF.assert_resolution_is_not_accuracy(
        {"resolution": "10 m", "accuracy": "5 m",
         "accuracy_method": "RMSE contra 30 puntos GNSS"})
    assert "resolución ≠ precisión" in ok["rule"]


def test_clase_de_procedencia_no_conocida_falla():
    with pytest.raises(CONF.UncertaintyError):
        CONF.provenance_penalty("oficial_porque_si")
