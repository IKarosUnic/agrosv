"""API `/api/data`: consultas reales, estados y errores explícitos."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv.data import storage as S  # noqa: E402
from conftest import require  # noqa: E402


def test_catalogo_expone_estados_y_auditoria(client):
    require(S.layout().catalog_path)
    r = client.get("/api/data/catalog")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 10
    assert body["audit"]["ok"] is True
    states = {d["state"] for d in body["datasets"]}
    assert {"INTEGRATED", "VALIDATED", "RESTRICTED", "UNAVAILABLE",
            "REJECTED"} <= states
    assert r.headers["X-AGROSV-Version"].startswith("4.")


def test_catalogo_filtra_por_dominio_y_estado(client):
    require(S.layout().catalog_path)
    r = client.get("/api/data/catalog", params={"domain": "CLIMATE"})
    assert r.status_code == 200
    assert all(d["domain"] == "CLIMATE" for d in r.json()["datasets"])
    r = client.get("/api/data/catalog", params={"state": "INTEGRATED"})
    assert all(d["state"] == "INTEGRATED" for d in r.json()["datasets"])
    assert client.get("/api/data/catalog",
                      params={"state": "INVENTADO"}).status_code == 400


def test_ficha_de_dataset_y_404(client):
    require(S.layout().catalog_path)
    r = client.get("/api/data/datasets/copdem30")
    assert r.status_code == 200
    body = r.json()
    assert body["dataset"]["state"] == "INTEGRATED"
    assert body["dataset"]["integration_scope"]
    assert body["served"] is True
    assert client.get("/api/data/datasets/no-existe").status_code == 404


def test_dataset_no_integrado_no_sirve_observaciones(client):
    require(S.layout().store_path)
    r = client.get("/api/data/observations", params={"dataset_id": "chirps3"})
    assert r.status_code == 409
    assert "no hay observaciones" in r.json()["detail"]


def test_observaciones_con_filtros(client):
    require(S.layout().store_path)
    r = client.get("/api/data/observations",
                   params={"dataset_id": "nasa_power_point",
                           "variable": "precipitation", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 5
    assert body["total"] == 2557
    row = body["rows"][0]
    assert row["unit"] == "mm"
    assert row["evidence_class"] == "reanalysis"
    assert row["quality_flag"] == "ok"

    r = client.get("/api/data/observations",
                   params={"dataset_id": "nasa_power_point",
                           "variable": "precipitation",
                           "start": "2020-01-01", "end": "2020-12-31",
                           "limit": 1000})
    assert r.json()["total"] == 366

    r = client.get("/api/data/observations",
                   params={"dataset_id": "nasa_power_point",
                           "bbox": "-89.3,13.6,-89.1,13.8", "limit": 3})
    assert r.json()["total"] > 0
    r = client.get("/api/data/observations",
                   params={"dataset_id": "nasa_power_point",
                           "bbox": "-85,10,-84,11"})
    assert r.json()["total"] == 0


def test_bbox_invalido_es_400(client):
    require(S.layout().store_path)
    for bbox in ("1,2,3", "a,b,c,d", "10,10,9,9"):
        r = client.get("/api/data/observations", params={"bbox": bbox})
        assert r.status_code == 400, bbox


def test_territorio_y_niveles(client):
    require(S.layout().store_path)
    r = client.get("/api/data/territory/SV")
    assert r.status_code == 200
    body = r.json()["territory"]
    assert body["level"] == "country"
    assert len(body["children"]) == 14
    assert body["geometry"] is not None

    r = client.get("/api/data/territories", params={"level": "department"})
    assert r.json()["total"] == 14
    r = client.get("/api/data/territories",
                   params={"level": "municipality_2023"})
    assert r.json()["total"] == 0
    assert "no se sintetizan límites" in r.json()["note"]
    assert client.get("/api/data/territory/SV-ADM1-NO").status_code == 404


def test_ocurrencias_por_bbox(client):
    require(S.layout().store_path)
    r = client.get("/api/data/occurrences", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 300
    assert "sesgo de muestreo" in body["note"]
    r = client.get("/api/data/occurrences",
                   params={"bbox": "-89.3,13.6,-89.1,13.8", "limit": 50})
    assert r.json()["total"] < 300


def test_metadata_raster_declara_nativa_y_efectiva(client):
    require(S.layout().raster_catalog)
    r = client.get("/api/data/raster/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 10
    for entry in body["rasters"]:
        assert entry["crs"]
        assert entry["res"]
        assert "cog_heuristic" in entry
        assert entry["container_recommendation"]["container"] in {
            "cog", "netcdf", "zarr"}


def test_informes_de_calidad(client):
    require(S.layout().store_path)
    r = client.get("/api/data/quality/reports")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 8
    assert "PASS no significa" in body["note"]
    one = client.get("/api/data/quality/reports/nasa_power_point")
    assert one.status_code == 200
    assert one.json()["reports"][0]["checks_run"] >= 3
    assert client.get("/api/data/quality/reports/inexistente").status_code == 404


def test_dominios_a_h(client):
    r = client.get("/api/data/domains")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 8
    keys = {d["domain"] for d in body["domains"]}
    assert {"TERRITORY", "SOILS", "HYDROLOGY", "CLIMATE", "AGRICULTURE",
            "ECONOMY", "PHYTOSANITARY", "BIODIVERSITY"} == keys
    r = client.get("/api/data/domains", params={"code": "B"})
    assert r.json()["domain"]["domain"] == "SOILS"
    assert r.json()["table_contract"]["primary_key"]


def test_almacenamiento(client):
    require(S.layout().store_path)
    r = client.get("/api/data/storage")
    body = r.json()
    assert body["store"]["exists"] is True
    assert body["store"]["observations"] > 1000
    assert body["layout"]["zones"]["raw"]["git"] is False
    assert body["layout"]["zones"]["validated"]["git"] is True


def test_lineaje_de_dataset(client):
    require(S.layout().lineage_path)
    r = client.get("/api/data/datasets/chirps3/lineage")
    assert r.status_code == 200
    assert r.json()["derivations"]
    r = client.get("/api/data/datasets/copdem30/lineage")
    assert r.status_code == 200
    assert r.json()["derivations"] == []


def _informe(dataset_id: str, report_id: str, status_value: str,
             generated_at: str, artifact: str = "data/samples/prueba.json") -> dict:
    return {"report_id": report_id, "dataset_id": dataset_id,
            "artifact": artifact, "scope": "prueba de respaldo",
            "status": status_value, "checks_run": 3,
            "errors": 1 if status_value == "FAIL" else 0, "warnings": 0,
            "findings": [], "generated_at": generated_at}


def test_fallback_de_calidad_omite_informes_fallidos_superados(tmp_path, monkeypatch):
    """Sin base SQLite, el respaldo no publica un FAIL que ya fue reemplazado."""
    import json

    from fastapi.testclient import TestClient

    from agrosv.api import app

    lay = S.DataLayout(root=tmp_path)
    directory = lay.quality_dir
    directory.mkdir(parents=True)
    informes = [
        # Mismo artefacto: el FAIL de las 04:10 quedó superado por el de 04:19.
        _informe("gbif_sv", "ffff0001", "FAIL", "2026-11-22T04:10:19Z"),
        _informe("gbif_sv", "ffff0002", "PASS_WITH_WARNINGS",
                 "2026-11-22T04:19:48Z"),
        # Este FAIL sí es el informe vigente de su dataset y debe verse.
        _informe("soilgrids_2", "ffff0003", "FAIL", "2026-11-22T04:19:51Z"),
    ]
    for informe in informes:
        (directory / f"{informe['dataset_id']}.{informe['report_id']}.json"
         ).write_text(json.dumps(informe), encoding="utf-8")
    assert not lay.store_path.exists()

    monkeypatch.setattr(S, "layout", lambda root=None: lay)
    client = TestClient(app)

    body = client.get("/api/data/quality/reports").json()
    assert body["count"] == 2
    assert {r["report_id"] for r in body["reports"]} == {"ffff0002", "ffff0003"}

    solo_fallidos = client.get("/api/data/quality/reports",
                               params={"status": "FAIL"}).json()
    assert solo_fallidos["count"] == 1
    assert solo_fallidos["reports"][0]["dataset_id"] == "soilgrids_2"

    detalle = client.get("/api/data/quality/reports/gbif_sv").json()
    assert [r["report_id"] for r in detalle["reports"]] == ["ffff0002"]
