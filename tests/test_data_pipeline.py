"""Monitoreo: vigencia, cambios de cobertura y versiones nuevas."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tests"))

from agrosv.data import pipeline as P  # noqa: E402
from agrosv.data import storage as S  # noqa: E402
from agrosv.data.catalog import Catalog, DatasetRecord, DatasetState  # noqa: E402
from conftest import require  # noqa: E402


def record(state=DatasetState.INTEGRATED, **over) -> DatasetRecord:
    base = dict(
        dataset_id="ds", name="Dataset de prueba",
        description="Descripción suficientemente larga.",
        institution="Institución", source_url="https://example.org",
        download_date="2026-01-01", license="CC BY 4.0",
        geographic_coverage="prueba", temporal_coverage="2026",
        crs="EPSG:4326", spatial_resolution="1 m",
        temporal_resolution="diaria", variables=["precipitation"],
        units={"precipitation": "mm"}, format="JSON", methodology="prueba",
        limitations=["prueba"], uncertainty="no cuantificada",
        domain="CLIMATE", state=state)
    base.update(over)
    return DatasetRecord(**base)


def test_vigencia_fresca_y_caducada():
    now = datetime(2026, 11, 22, tzinfo=timezone.utc)
    fresh = P.freshness(record(download_date="2026-11-01"), now=now)
    assert fresh["status"] == "FRESH"
    stale = P.freshness(record(download_date="2024-01-01"), now=now)
    assert stale["status"] == "STALE"
    assert stale["age_days"] > 365
    unknown = P.freshness(record(download_date=None, publication_date=None),
                          now=now)
    assert unknown["status"] == "UNKNOWN"


def test_vigencia_por_dominio():
    now = datetime(2026, 11, 22, tzinfo=timezone.utc)
    old = "2026-06-01"
    assert P.freshness(record(dataset_id="economy_ds", domain="ECONOMY",
                              download_date=old), now=now)["status"] == "STALE"
    assert P.freshness(record(dataset_id="soils_ds", domain="SOILS",
                              download_date=old), now=now)["status"] == "FRESH"


def test_cambio_de_cobertura_se_detecta_por_umbral():
    result = P.detect_coverage_change({"cells": 1000, "area": 500.0},
                                      {"cells": 1200, "area": 500.0})
    assert result["changed"] is True
    assert result["changes"][0]["metric"] == "cells"
    assert result["changes"][0]["pct"] == 20.0
    assert P.detect_coverage_change({"cells": 1000},
                                    {"cells": 1010})["changed"] is False


def test_version_nueva_exige_revalidacion():
    previous = {"sha256": "a" * 64, "bytes": 100, "etag": '"v1"'}
    same = P.detect_new_version(previous, {"sha256": "a" * 64, "bytes": 100,
                                           "etag": '"v1"'})
    assert same["changed"] is False
    changed = P.detect_new_version(previous, {"sha256": "b" * 64, "bytes": 120,
                                              "etag": '"v2"'})
    assert changed["changed"] is True
    assert changed["requires_revalidation"] is True
    assert set(changed["reasons"]) == {"hash distinto", "ETag distinto",
                                       "tamaño distinto"}
    assert P.detect_new_version(None, {})["changed"] is True


def test_artefacto_ausente_entra_en_cola():
    missing = record(artifacts=["data/no/existe.tif"],
                     state=DatasetState.VALIDATED)
    assert P.missing_artifacts(missing)
    catalog = Catalog(Path("unused.json"))
    catalog._records = {"ds": missing}
    queue = P.revalidation_queue(catalog)
    assert queue
    assert any("artefactos ausentes" in r
               for r in queue[0]["reasons"])


def test_monitoreo_real():
    lay = S.layout()
    require(lay.catalog_path)
    require(lay.store_path)
    payload = P.monitoring_report(layout=lay)
    assert payload["ok"] is True, payload
    assert payload["catalog"]["count"] >= 20
    assert payload["store"]["observations"] > 1000
    assert payload["audit"]["ok"] is True
    assert isinstance(payload["revalidation_queue"], list)
    assert "not_evaluated" in payload["freshness"]
    assert payload["freshness"]["stale_or_unknown"] == []


def test_monitoreo_sin_catalogo_no_finge(tmp_path):
    payload = P.monitoring_report(catalog_path=tmp_path / "no.json",
                                  layout=S.DataLayout(root=tmp_path))
    assert payload["ok"] is False
    assert "catálogo no encontrado" in payload["error"]


def test_monitoreo_escribe_y_conserva_anterior(tmp_path):
    lay = S.layout()
    if not lay.catalog_path.exists():
        import pytest

        pytest.skip("catálogo no construido")
    payload = P.monitoring_report(layout=lay)
    out = tmp_path / "monitoring.json"
    P.write_monitoring(payload, out)
    assert out.exists()
    P.write_monitoring(payload, out)
    assert out.with_suffix(".previous.json").exists()
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["catalog"]["count"] == payload["catalog"]["count"]
