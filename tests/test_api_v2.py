"""API científica `/api/v1`: contrato, envoltura y funcionamiento real.

La prueba decisiva es que los endpoints no devuelvan cifras sueltas: toda salida
debe traer etiqueta de clase de dato, resolución real, incertidumbre,
limitaciones y procedencia.
"""
from __future__ import annotations

import io
import math
import zipfile

import pytest

REQUIRED_KEYS = {"value", "label", "resolution", "confidence",
                 "uncertainty", "limitations", "provenance_id"}


def test_meta_versionada(client):
    r = client.get("/api/v1/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["service_version"].startswith("2.")
    assert body["datasets"], "el catálogo no puede estar vacío"
    assert "ndvi" in body["indices"]
    assert r.headers["X-AGROSV-Version"].startswith("2.")


def test_sources_con_licencias(client):
    r = client.get("/api/v1/sources")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    assert body["licenses"]
    for ds in body["datasets"]:
        assert ds["license"], f"{ds['layer']} sin licencia declarada"
        assert len(ds["sha256"]) == 64


def test_provenance_resuelve_y_falla_con_desconocido(client):
    ds = client.get("/api/v1/sources").json()["datasets"][0]
    r = client.get(f"/api/v1/provenance/{ds['provenance_id']}")
    assert r.status_code == 200
    assert r.json()["manifest"]["license"]
    assert client.get("/api/v1/provenance/no-existe").status_code == 404


def test_qc_reporta_artefactos(client):
    r = client.get("/api/v1/qc")
    assert r.status_code == 200
    body = r.json()
    assert body["checked"] > 0
    assert body["ok"] is True, body["failed"]


def test_qc_con_rasters(client):
    r = client.get("/api/v1/qc", params={"include_rasters": True})
    assert r.status_code == 200
    assert r.json()["checked"] >= 4


def test_indices_declara_lo_no_implementado(client):
    body = client.get("/api/v1/indices").json()
    assert body["indices"]["ndvi"]["resolution_m"] == 10
    assert body["not_implemented"], "debe declarar la adquisición no implementada"
    assert "no se sirve" in body["note"]


def test_cuenca_hidrologica_es_una_salida_publicable(client):
    r = client.get("/api/v1/hydro/watershed",
                   params={"lat": 13.49, "lon": -88.40, "size_m": 2000})
    assert r.status_code == 200, r.text
    body = r.json()
    assert REQUIRED_KEYS <= set(body)
    assert body["label"] == "derivado"
    assert body["value"]["area_km2"] > 0
    assert body["value"]["cells"] > 0
    assert body["value"]["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert len(body["limitations"]) >= 3
    assert "no calibrado" in " ".join(body["limitations"]).lower()
    assert body["provenance_id"]


def test_cuenca_fuera_del_pais_es_rechazada(client):
    r = client.get("/api/v1/hydro/watershed",
                   params={"lat": 40.4, "lon": -3.7})
    assert r.status_code == 422


def test_diagnosticos_hidrologicos(client):
    r = client.get("/api/v1/hydro/aoi",
                   params={"lat": 13.49, "lon": -88.40, "size_m": 1200})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["value"]["slope_deg"]["mean"] >= 0
    assert body["value"]["diagnostics"]["max_accumulation"] > 0


def test_paquete_offline_contiene_manifiesto(client):
    r = client.get("/api/v1/offline/SV-SS.zip")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = set(zf.namelist())
        assert "metadata.json" in names
        assert "README.txt" in names
        assert "territory/department.geojson" in names
        meta = zf.read("metadata.json").decode("utf-8")
        assert "excluded" in meta
        assert "osm" in meta
        readme = zf.read("README.txt").decode("utf-8")
        assert "Atribución obligatoria" in readme


def test_paquete_offline_departamento_inexistente(client):
    assert client.get("/api/v1/offline/SV-ZZ.zip").status_code == 404


def test_politica_de_validacion_declara_estado_real(client):
    body = client.get("/api/v1/validation/policy").json()
    assert body["levels"]["V4"]
    assert body["current_status"]["hydrology_module"].startswith("V0")


@pytest.mark.parametrize("path", ["/api/v1/meta", "/api/v1/sources",
                                  "/api/v1/indices", "/api/v1/qc"])
def test_cabeceras_de_publicacion(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers["X-AGROSV-Version"]
    assert r.headers["X-AGROSV-License"]


def test_api_fase1_sigue_intacta(client):
    """La capa v1 no reemplaza ni rompe los endpoints de Fase 1."""
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/territory/departments").status_code == 200
    x, y = int((180 - 89.22) / 360 * 2 ** 9), int(
        (1 - math.asinh(math.tan(math.radians(13.69))) / math.pi) / 2 * 2 ** 9)
    assert client.get(f"/api/tiles/hillshade/9/{x}/{y}.png").status_code == 200
