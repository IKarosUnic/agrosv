"""Ráster por ventanas y estándar temporal."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.data import raster as R  # noqa: E402
from agrosv.data import temporal as T  # noqa: E402


def write_raster(path: Path, *, nodata=None, shift=0.0, size=20) -> Path:
    data = np.arange(size * size, dtype="float32").reshape(size, size)
    data[0:2, 0:2] = -9999.0
    profile = {
        "driver": "GTiff", "width": size, "height": size, "count": 1,
        "dtype": "float32", "crs": "EPSG:4326",
        "transform": from_origin(-89.5 + shift, 14.0, 0.01, 0.01),
        "nodata": nodata, "tiled": False, "compress": "lzw",
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)
    return path


def test_perfil_lee_cabecera(tmp_path):
    path = write_raster(tmp_path / "r.tif", nodata=-9999.0)
    profile = R.profile_raster(path)
    assert profile.width == 20
    assert profile.crs == "EPSG:4326"
    assert profile.nodata == -9999.0
    assert profile.res[0] == pytest.approx(0.01)
    assert profile.pixel_area_m2 and profile.pixel_area_m2 > 0


def test_nodata_no_declarado_detecta_centinela(tmp_path):
    path = write_raster(tmp_path / "r.tif", nodata=None)
    candidates = R.undeclared_nodata_candidates(path)
    assert candidates["declared"] is False
    assert any(c["value"] == -9999.0 for c in candidates["suspicious"])


def test_no_se_puede_aumentar_resolucion(tmp_path):
    path = write_raster(tmp_path / "r.tif", nodata=-9999.0)
    with pytest.raises(R.ResolutionInflationError):
        R.plan_reproject(path, "EPSG:32616", target_res=0.001)
    coarser = R.plan_reproject(path, "EPSG:32616", target_res=1000.0,
                               method="average", reason="prueba")
    assert coarser.degraded is True
    assert "remuestreado" in coarser.effective_resolution


def test_remuestreo_exige_metodo_valido(tmp_path):
    path = write_raster(tmp_path / "r.tif", nodata=-9999.0)
    with pytest.raises(ValueError):
        R.plan_reproject(path, "EPSG:32616", method="magia")


def test_recorte_conserva_resolucion(tmp_path):
    path = write_raster(tmp_path / "r.tif", nodata=-9999.0)
    out = tmp_path / "clip.tif"
    info = R.clip_to_file(path, out, (-89.48, 13.96, -89.44, 14.0))
    assert info["resampling"] == "none"
    clipped = R.profile_raster(out)
    assert clipped.res[0] == pytest.approx(0.01)
    assert clipped.width < 20 and clipped.height < 20
    assert out.exists()


def test_ventana_no_carga_todo_el_archivo(tmp_path):
    path = write_raster(tmp_path / "r.tif", nodata=-9999.0, size=200)
    data, _ = R.read_window(path, (-89.49, 13.96, -89.45, 14.0))
    assert data.shape[0] < 200 and data.shape[1] < 200
    stats = R.window_stats(path, (-89.49, 13.96, -89.45, 14.0))
    assert stats["cells"] > 0


def test_iteracion_por_bloques(tmp_path):
    path = write_raster(tmp_path / "r.tif", nodata=-9999.0, size=200)
    blocks = list(R.iter_blocks(path))
    assert len(blocks) >= 1
    assert sum(int(w.height * w.width) for w, _ in blocks) == 200 * 200


def test_rejilla_incompatible_se_detecta(tmp_path):
    a = write_raster(tmp_path / "a.tif", nodata=-9999.0)
    b = write_raster(tmp_path / "b.tif", nodata=-9999.0, shift=0.5)
    report = R.assert_same_grid([a, b])
    assert report["ok"] is False
    assert report["problems"]
    assert R.assert_same_grid([a, a])["ok"] is True


def test_muestreo_puntual(tmp_path):
    path = write_raster(tmp_path / "r.tif", nodata=-9999.0)
    values = R.sample_points(path, [-89.45, -80.0], [13.90, 10.0])
    assert values[0] is not None
    assert values[1] is None


def test_contenedor_se_elige_con_criterio():
    assert R.choose_container(temporal=False, variables=1)["container"] == "cog"
    assert R.choose_container(temporal=True, variables=3,
                              access="parallel")["container"] == "zarr"
    assert R.choose_container(temporal=True, variables=3)["container"] == "netcdf"


# --- Temporal ----------------------------------------------------------------
def daily_spec(**over) -> T.TimeSeriesSpec:
    base = dict(variable="precipitation", unit="mm",
                evidence_class=T.EvidenceClass.OBSERVATION,
                frequency=T.Frequency.DAILY, time_basis="local",
                aggregation=T.Aggregation.SUM, dataset_id="ds",
                source_id="src")
    base.update(over)
    return T.TimeSeriesSpec(**base)


def test_huecos_y_duplicados_se_enumeran():
    times = ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-05"]
    report = T.validate_series(times, [1.0, 2.0, 3.0, 4.0], daily_spec())
    codes = {f["code"] for f in report.findings}
    assert "periodos_duplicados" in codes
    assert "periodos_faltantes" in codes
    gap = next(f for f in report.findings if f["code"] == "periodos_faltantes")
    assert gap["count"] == 2  # faltan el 3 y el 4 de enero


def test_centinela_no_es_dato():
    report = T.validate_series(["2024-01-01", "2024-01-02"],
                               [0.0, -999.0], daily_spec())
    assert any(f["code"] == "centinela_como_dato" and f["severity"] == "error"
               for f in report.findings)


def test_frecuencia_declarada_debe_coincidir():
    monthly = T.validate_series(
        ["2024-01", "2024-02", "2024-03"], [1.0, 2.0, 3.0], daily_spec())
    assert any(f["code"] == "frecuencia_inconsistente" for f in monthly.findings)


def test_no_se_mezclan_observacion_y_pronostico():
    with pytest.raises(T.MixedEvidenceError):
        T.assert_comparable([T.EvidenceClass.OBSERVATION,
                             T.EvidenceClass.FORECAST])
    T.assert_comparable([T.EvidenceClass.REANALYSIS,
                         T.EvidenceClass.OBSERVATION])


def test_clase_no_observacional_exige_incertidumbre():
    with pytest.raises(T.TemporalError):
        T.TimeSeriesSpec(variable="precipitation", unit="mm",
                         evidence_class=T.EvidenceClass.FORECAST,
                         frequency=T.Frequency.DAILY, time_basis="UTC",
                         aggregation=T.Aggregation.SUM, dataset_id="ds",
                         source_id="src")


def test_conversion_local_utc():
    utc = T.to_utc("2024-05-01T00:00:00", time_basis="local")
    assert utc.hour == 6
    local = T.to_local("2024-05-01T06:00:00Z", time_basis="UTC")
    assert local.hour == 0
    report = T.time_basis_report()
    assert report["utc_offset_hours"] == -6
    assert report["dst"] is False


def test_ano_hidrologico_y_temporadas():
    assert T.hydrological_year("2025-03-15") == "HY2024/2025"
    assert T.hydrological_year("2025-05-01") == "HY2025/2026"
    assert "primera" in T.season_of("2025-06-01")
    assert "postrera" in T.season_of("2025-10-01")
    calendar = T.season_calendar_report()
    assert calendar["status"] == "REFERENCE_ONLY"
    assert "no es un calendario oficial" in calendar["limitation"]


def test_agregacion_declara_cobertura_incompleta():
    times = [f"2024-11-{d:02d}" for d in range(1, 6)]
    values = [1.0] * 5
    out = T.aggregate_periods(times, values, spec=daily_spec(),
                              target=T.Frequency.MONTHLY)
    period = out["periods"][0]
    assert period["value"] == pytest.approx(5.0)
    assert period["complete"] is False
    assert period["quality_flag"] == "incomplete_period"


def test_fechas_invalidas_se_reportan():
    report = T.validate_series(["2024-01-01", "no-es-fecha"],
                               [1.0, 2.0], daily_spec())
    assert any(f["code"] == "fechas_invalidas" for f in report.findings)
