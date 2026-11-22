"""Pruebas de incorporación de datos externos (Fase 7).

Verifican validadores, la correspondencia municipal 2023 y los contratos de la
API. No validan datos que aún no existen: las series, muestras, cuencas,
aforos y puntos GNSS siguen pendientes.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agrosv import config as C
from agrosv.api import app
from agrosv.onboarding import dem, municipalities, registry, validators


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return path


# --- registro ---------------------------------------------------------------
def test_registry_has_six_sources_with_only_crosswalk_acquired():
    payload = registry.sources()
    assert payload["count"] == 6
    assert payload["acquired"] == ["municipality_crosswalk_2023"]
    assert set(payload["not_acquired"]) == {
        "snet_marn_stations", "centa_soil_lab", "marn_basins",
        "marn_gauging", "gnss_control_points"}


def test_each_source_declares_access_schema_and_fallback():
    for source in registry.SOURCES.values():
        assert source.access_url.startswith("https://")
        assert source.required_fields
        assert source.validator in validators.VALIDATORS
        assert source.unlocks
        assert source.fallback
        assert source.evidence_class


def test_unknown_source_raises():
    with pytest.raises(KeyError):
        registry.source("hyperlocal_weather")


# --- correspondencia municipal ---------------------------------------------
def test_bundled_crosswalk_has_official_counts():
    path = municipalities.CROSSWALK_PATH
    report = validators.validate_crosswalk(path)
    assert report["valid"] is True
    assert report["summary"]["departments"] == 14
    assert report["summary"]["municipalities"] == 44
    assert report["summary"]["districts"] == 262
    assert report["summary"]["effective_dates"] == ["2024-05-01"]


def test_crosswalk_provenance_checksum_matches_file():
    meta = json.loads(municipalities.PROVENANCE_PATH.read_text(encoding="utf-8"))
    digest = hashlib.sha256(municipalities.CROSSWALK_PATH.read_bytes()).hexdigest()
    assert meta["sha256"] == digest
    assert meta["legal_instrument"].startswith("Decreto Legislativo N.° 762")
    assert meta["counts"] == {"departments": 14, "municipalities": 44,
                              "districts": 262}


def test_crosswalk_lookup_and_ambiguity():
    assert municipalities.municipality_of("Ilopango")["municipality"] == \
        "San Salvador Este"
    ambiguous = municipalities.municipality_of("El Rosario")
    assert ambiguous["found"] is False and ambiguous["ambiguous"] is True
    resolved = municipalities.municipality_of("El Rosario",
                                             department="La Paz")
    assert resolved["found"] is True
    assert resolved["municipality"] == "La Paz Centro"


def test_crosswalk_districts_of_acajutla():
    payload = municipalities.districts_of("Sonsonate Oeste")
    assert payload["found"] is True
    assert [d["district"] for d in payload["districts"]] == ["Acajutla"]


def test_crosswalk_normalizes_ocr_spelling():
    rows = municipalities.load_crosswalk()
    names = {row["district"] for row in rows}
    assert "Ilopango" in names and "llopango" not in names
    assert "Ilobasco" in names and "llobasco" not in names
    assert "Intipucá" in names


def test_aggregate_requires_department_for_repeated_district():
    payload = municipalities.aggregate_rows([
        {"district": "Ilopango"},
        {"district": "Santa Tecla"},
        {"district": "El Rosario", "department": "La Paz"},
        {"district": "El Rosario"},
    ])
    assert "San Salvador Este" in payload["municipalities"]
    assert "La Libertad Sur" in payload["municipalities"]
    assert "La Paz Centro" in payload["municipalities"]
    assert len(payload["unmapped"]) == 1
    assert payload["unmapped"][0]["reason"].startswith("nombre ambiguo")


# --- estaciones -------------------------------------------------------------
def test_station_series_accepts_valid_long_csv(tmp_path):
    path = write_csv(tmp_path / "s.csv",
                     ["station_id", "date", "variable", "value", "unit",
                      "latitude", "longitude", "source"],
                     [["A-01", "2024-01-01", "precipitation", "0.0", "mm",
                       "13.7", "-89.2", "MARN"],
                      ["A-01", "2024-01-02", "precipitation", "12.4", "mm",
                       "13.7", "-89.2", "MARN"]])
    report = validators.validate_station_series(path)
    assert report["valid"] is True
    assert report["summary"]["stations"] == 1
    assert report["summary"]["variables"] == {"precipitation": 2}


def test_station_series_rejects_missing_column_and_bad_unit(tmp_path):
    missing = write_csv(tmp_path / "m.csv", ["station_id", "date"],
                        [["A", "2024-01-01"]])
    assert validators.validate_station_series(missing)["valid"] is False
    bad = write_csv(tmp_path / "b.csv",
                    ["station_id", "date", "variable", "value", "unit",
                     "latitude", "longitude", "source"],
                    [["A", "2024-01-01", "precipitation", "1", "degC",
                      "13.7", "-89.2", "MARN"]])
    report = validators.validate_station_series(bad)
    assert report["valid"] is False
    assert any("unidad" in e for e in report["errors"])


def test_station_series_rejects_duplicates_and_foreign_coordinates(tmp_path):
    path = write_csv(tmp_path / "d.csv",
                     ["station_id", "date", "variable", "value", "unit",
                      "latitude", "longitude", "source"],
                     [["A", "2024-01-01", "precipitation", "1", "mm",
                       "13.7", "-89.2", "MARN"],
                      ["A", "2024-01-01", "precipitation", "1", "mm",
                       "13.7", "-89.2", "MARN"],
                      ["B", "2024-01-01", "precipitation", "1", "mm",
                       "0", "0", "MARN"]])
    report = validators.validate_station_series(path)
    assert report["valid"] is False
    assert any("duplicado" in e for e in report["errors"])
    assert any("fuera" in e for e in report["errors"])


# --- CENTA ------------------------------------------------------------------
def test_centa_samples_accepts_valid_and_rejects_out_of_range(tmp_path):
    header = ["sample_id", "date", "latitude", "longitude", "depth_cm",
              "variable", "value", "unit", "lab_method", "source"]
    good = write_csv(tmp_path / "g.csv", header,
                     [["S1", "2024-02-01", "13.7", "-89.2", "15", "ph",
                       "6.5", "pH", "1:2.5 H2O", "CENTA"]])
    assert validators.validate_centa_samples(good)["valid"] is True
    bad = write_csv(tmp_path / "b.csv", header,
                    [["S1", "2024-02-01", "13.7", "-89.2", "15", "ph",
                      "14", "pH", "1:2.5 H2O", "CENTA"]])
    report = validators.validate_centa_samples(bad)
    assert report["valid"] is False


# --- cuencas ----------------------------------------------------------------
def test_basins_validates_geojson_and_duplicate_codes(tmp_path):
    feature = {
        "type": "Feature",
        "properties": {"basin_code": "B-01", "name": "Cuenca de prueba",
                       "area_km2": 120.0},
        "geometry": {"type": "Polygon", "coordinates": [[
            [-89.3, 13.6], [-89.2, 13.6], [-89.2, 13.7], [-89.3, 13.7],
            [-89.3, 13.6]]]},
    }
    path = tmp_path / "b.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection",
                                "features": [feature]}), encoding="utf-8")
    report = validators.validate_basins(path)
    assert report["valid"] is True
    assert report["summary"]["unique_codes"] == 1
    path.write_text(json.dumps({"type": "FeatureCollection",
                                "features": [feature, feature]}),
                    encoding="utf-8")
    report = validators.validate_basins(path)
    assert report["valid"] is False
    assert any("duplicado" in e for e in report["errors"])


# --- aforos -----------------------------------------------------------------
def test_gauging_rejects_negative_discharge(tmp_path):
    path = write_csv(tmp_path / "q.csv",
                     ["station_id", "date", "discharge_m3s", "basin_code",
                      "source"],
                     [["H-01", "2024-01-01", "-1", "B-01", "MARN"]])
    report = validators.validate_gauging(path)
    assert report["valid"] is False
    assert any("negativo" in e for e in report["errors"])


# --- GNSS y DEM -------------------------------------------------------------
def _gnss_file(path: Path) -> Path:
    return write_csv(
        path,
        ["point_id", "latitude", "longitude", "orthometric_height_m",
         "horizontal_accuracy_m", "vertical_accuracy_m", "date", "source"],
        [["P1", "13.70", "-89.20", "500.0", "0.01", "0.02", "2024-01-01",
          "CNR"],
         ["P2", "13.80", "-89.30", "800.0", "0.01", "0.02", "2024-01-01",
          "CNR"]])


def test_gnss_requires_height_or_undulation(tmp_path):
    path = write_csv(
        tmp_path / "g.csv",
        ["point_id", "latitude", "longitude", "date", "source",
         "horizontal_accuracy_m", "vertical_accuracy_m"],
        [["P1", "13.7", "-89.2", "2024-01-01", "CNR", "0.01", "0.02"]])
    report = validators.validate_gnss(path)
    assert report["valid"] is False
    assert any("orthometric" in e for e in report["errors"])


def test_dem_error_metrics_with_control_points(tmp_path):
    if not Path(C.DEM_WGS84).exists():
        pytest.skip("DEM no generado")
    path = _gnss_file(tmp_path / "ok.csv")
    assert validators.validate_gnss(path)["valid"] is True
    report = dem.dem_error(path)
    assert report["available"] is True
    assert report["metrics"]["n"] == 2
    assert report["metrics"]["rmse_m"] >= 0
    assert report["dem_vertical_datum"] == "EGM2008"
    assert report["is_official_dem_accuracy"] is False


# --- API --------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_meta_and_sources(client):
    assert client.get("/api/onboarding/meta").status_code == 200
    sources = client.get("/api/onboarding/sources").json()
    assert sources["count"] == 6
    detail = client.get("/api/onboarding/sources/gnss_control_points").json()
    assert detail["acquired"] is False
    assert client.get("/api/onboarding/sources/nope").status_code == 404


def test_api_municipalities(client):
    summary = client.get("/api/onboarding/municipalities/summary").json()
    assert summary["counts"] == {"departments": 14, "municipalities": 44,
                                 "districts": 262}
    lookup = client.get(
        "/api/onboarding/municipalities/lookup?district=Ilopango").json()
    assert lookup["municipality"] == "San Salvador Este"


def test_api_validates_bundled_crosswalk(client):
    response = client.post("/api/onboarding/validate", json={
        "kind": "crosswalk",
        "path": "data/reference/municipality_crosswalk_2023.csv"})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_api_rejects_traversal_and_unknown_kind(client):
    traversal = client.post("/api/onboarding/validate", json={
        "kind": "crosswalk", "path": "../../etc/passwd"})
    assert traversal.status_code == 400
    unknown = client.post("/api/onboarding/validate", json={
        "kind": "teleport", "path": "data/reference/municipality_crosswalk_2023.csv"})
    assert unknown.status_code == 400
    missing = client.post("/api/onboarding/validate", json={"kind": "crosswalk"})
    assert missing.status_code == 400
