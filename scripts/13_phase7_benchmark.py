#!/usr/bin/env python3
"""Benchmark reproducible de la Fase 7 (monitorización agrícola).

Mide cálculo de índices, cambio, series, riesgo, alertas y latencia de API con
datos sintéticos declarados. No mide precisión científica: mide tiempo,
memoria y latencia en este entorno.

Uso:
    PYTHONPATH=backend .venv/bin/python scripts/13_phase7_benchmark.py
    ... --json /tmp/phase7_benchmark.json
"""
from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.monitoring.alerts import AgriculturalAlertEngine  # noqa: E402
from agrosv.monitoring.change import CropChangeDetectionEngine  # noqa: E402
from agrosv.monitoring.indices import VegetationIndexEngine  # noqa: E402
from agrosv.monitoring.risks import AgriculturalRiskEngine  # noqa: E402
from agrosv.monitoring.timeseries import SatelliteTimeSeriesEngine  # noqa: E402


def _timed(fn, repeat: int = 3) -> dict:
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000.0)
    return {"median_ms": round(statistics.median(times), 3),
            "min_ms": round(min(times), 3), "max_ms": round(max(times), 3),
            "repeats": repeat}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    rng = np.random.default_rng(7)
    size = 1000
    nir = rng.uniform(0.15, 0.6, (size, size)).astype("float32")
    red = rng.uniform(0.05, 0.3, (size, size)).astype("float32")
    before = rng.uniform(0.2, 0.7, (size, size)).astype("float32")
    after = before - 0.12

    indices = VegetationIndexEngine()
    change = CropChangeDetectionEngine()
    series = SatelliteTimeSeriesEngine()
    risk = AgriculturalRiskEngine()
    alerts = AgriculturalAlertEngine()

    records = []
    for year in range(2014, 2024):
        for month, day in ((6, 15), (6, 25), (7, 5), (7, 15)):
            records.append({"date": f"{year}-{month:02d}-{day:02d}",
                            "value": 0.55 + 0.02 * rng.standard_normal()})

    results = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "index_ndvi_1000x1000": _timed(
            lambda: indices.compute("ndvi", {"nir": nir, "red": red})),
        "change_1000x1000": _timed(
            lambda: change.compare(before, after, threshold=0.1)),
        "timeseries_anomaly_40_obs": _timed(
            lambda: series.anomaly(records, target_date="2023-07-15",
                                   min_obs=6), repeat=5),
        "risk_assess_x10000": _timed(
            lambda: [risk.assess(hazard=0.7, exposure=0.5,
                                 vulnerability=0.4) for _ in range(10_000)],
            repeat=2),
    }

    def _create_alerts() -> None:
        engine = AgriculturalAlertEngine()
        for i in range(2000):
            engine.create(
                category="drought",
                geographic_scope={"scale": "municipal", "name": f"m{i}"},
                observation_period={"start": "2024-01-01", "end": "2024-03-31"},
                detection_method="benchmark", risk_level="moderate",
                evidence=[{"i": i}], confidence="medium",
                source_datasets=["benchmark"])

    results["alert_create_x2000"] = _timed(_create_alerts, repeat=1)

    try:
        from fastapi.testclient import TestClient

        from agrosv.api import app

        client = TestClient(app)
        payload = {"name": "ndvi", "bands": {"nir": [0.5, 0.2],
                                             "red": [0.1, 0.4]}}

        def _api_index() -> None:
            assert client.post("/api/monitoring/indices",
                               json=payload).status_code == 200

        def _api_meta() -> None:
            assert client.get("/api/monitoring/meta").status_code == 200

        results["api_index_post"] = _timed(_api_index, repeat=20)
        results["api_meta_get"] = _timed(_api_meta, repeat=20)
    except Exception as exc:  # noqa: BLE001 — se declara el fallo
        results["api"] = {"error": f"{type(exc).__name__}: {exc}"}

    # ru_maxrss es el pico del proceso: se lee al final, no al inicio.
    results["environment"]["max_rss_mb"] = round(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    if args.json:
        args.json.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                             encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
