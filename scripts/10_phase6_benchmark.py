#!/usr/bin/env python3
"""Benchmark de Fase 6: población sintética, escenarios y motores agrícolas.

Mide tiempo de pared (mediana de `--repeats`) y memoria pico con tracemalloc.
No mide calidad científica ni precisión: solo costo de ejecución local.

Uso:
    PYTHONPATH=backend .venv/bin/python scripts/10_phase6_benchmark.py --repeats 3
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402

from agrosv.agriculture.phenology import CropPhenologyEngine  # noqa: E402
from agrosv.agriculture.suitability import CropSuitabilityEngine  # noqa: E402
from agrosv.agriculture.water_nutrient import CropWaterNutrientEngine  # noqa: E402
from agrosv.social.multiagent import AgriculturalMultiAgentEngine  # noqa: E402
from agrosv.social.population import AgriculturalPopulationEngine  # noqa: E402
from agrosv.socio.scenario import AgriculturalScenarioEngine  # noqa: E402

OUT = ROOT / "docs/phase6/benchmark_phase6.json"
LON, LAT = -89.45, 13.85


def measure(fn, repeats: int) -> dict:
    times = []
    peak = 0
    value = None
    for _ in range(repeats):
        tracemalloc.start()
        start = time.perf_counter()
        value = fn()
        elapsed = time.perf_counter() - start
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        times.append(elapsed)
        peak = max(peak, peak_bytes)
    return {
        "median_s": round(statistics.median(times), 4),
        "min_s": round(min(times), 4),
        "max_s": round(max(times), 4),
        "peak_memory_mb": round(peak / (1024 * 1024), 2),
        "repeats": repeats,
        "_value": value,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    repeats = max(1, args.repeats)

    population = AgriculturalPopulationEngine()
    scenario = AgriculturalScenarioEngine()
    multiagent = AgriculturalMultiAgentEngine()
    suitability = CropSuitabilityEngine()
    phenology = CropPhenologyEngine()
    water = CropWaterNutrientEngine()

    results: dict[str, dict] = {}
    for size in (100, 1000, 5000):
        results[f"population_{size}"] = measure(
            lambda n=size: population.generate(n, seed=42), repeats)
        results[f"population_{size}"].pop("_value")

    for size in (100, 1000):
        generated = population.generate(size, seed=42)["result"]["agents"]
        results[f"multiagent_{size}_steps10"] = measure(
            lambda a=generated: multiagent.run(a, steps=10, seed=7,
                                               practice="improved_seed"),
            repeats)
        results[f"multiagent_{size}_steps10"].pop("_value")

    def suitability_once():
        return suitability.evaluate("coffee", LON, LAT)

    results["suitability_coffee"] = measure(suitability_once, repeats)
    results["suitability_coffee"].pop("_value")

    results["phenology_maize"] = measure(
        lambda: phenology.run("maize", "2024-05-15"), repeats)
    results["phenology_maize"].pop("_value")

    results["water_balance_maize"] = measure(
        lambda: water.water_balance(
            crop_id="maize", planting_date="2024-05-15", awc_mm_per_m=150,
            root_depth_cm=60, allow_reference_kc=True), repeats)
    results["water_balance_maize"].pop("_value")

    for size in (10, 25, 50):
        entry = measure(
            lambda n=size: scenario.run("A_drought", lon=LON, lat=LAT,
                                        size=n, seed=42), max(1, repeats - 1))
        entry.pop("_value")
        results[f"scenario_drought_{size}"] = entry

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
        },
        "notes": [
            "tiempo de pared en un proceso local; no es un SLA",
            "memoria pico de tracemalloc, no RSS del proceso",
            "la primera corrida incluye importaciones perezosas",
            "no se mide precisión científica, solo costo de ejecución",
        ],
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps(payload["results"], indent=2, ensure_ascii=False))
    print(f"\nEscrito: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
