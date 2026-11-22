"""AGROSV Fase 5 — banco de medición de rendimiento de los motores.

Mide, con los artefactos reales del repositorio y sin red:

* latencia por motor (mínimo, mediana, máximo de N repeticiones);
* latencia en frío (``use_cache=False``) y en caliente (caché derivado);
* memoria: RSS máximo del proceso (``ru_maxrss``) y pico de asignaciones
  Python (``tracemalloc``) durante la llamada más pesada;
* coste de una intersección con las 287 unidades territoriales.

No es una prueba de unidad: es una medición reproducible que se guarda en
``docs/phase5/benchmark_phase5.json`` para que las cifras del informe no sean
una impresión.

Uso:
    .venv/bin/python scripts/09_phase5_benchmark.py [--repeats 3]
"""
from __future__ import annotations

import argparse
import json
import resource
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv import config as C  # noqa: E402
from agrosv.engines import climate as CL  # noqa: E402
from agrosv.engines import environmental as EN  # noqa: E402
from agrosv.engines import governance as G  # noqa: E402
from agrosv.engines import hydrology as HY  # noqa: E402
from agrosv.engines import soil as SL  # noqa: E402
from agrosv.engines import terrain as TM  # noqa: E402
from agrosv.engines import territorial as TR  # noqa: E402

POINT = (-89.2, 13.7)
OUTPUT = ROOT / "docs" / "phase5" / "benchmark_phase5.json"


def rss_mb() -> float:
    """RSS máximo del proceso en MiB (Linux: ru_maxrss en KiB)."""
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def measure(label: str, call, repeats: int) -> dict:
    times: list[float] = []
    last = None
    for _ in range(repeats):
        start = time.perf_counter()
        last = call()
        times.append(time.perf_counter() - start)
    return {
        "label": label,
        "repeats": repeats,
        "min_s": round(min(times), 4),
        "median_s": round(statistics.median(times), 4),
        "max_s": round(max(times), 4),
        "rss_mb_after": rss_mb(),
        "result_ok": last is not None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AGROSV Fase 5 — benchmarks")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats debe ser ≥ 1")

    missing = [str(p.relative_to(ROOT)) for p in
               (C.DEM_WGS84, C.SLOPE, C.ASPECT, C.TERRITORY_GPKG, C.INFRA_GPKG,
                CL.DB_PATH) if not p.exists()]
    if missing:
        print(json.dumps({"ok": False, "missing": missing}, indent=2))
        return 2

    territorial = TR.TerritorialEngine()
    soil = SL.SoilEngine()
    hydro = HY.HydrologyEngine()
    climate = CL.ClimateEngine()
    environmental = EN.EnvironmentalInteractionEngine()

    rows = [
        measure("territorial.profile", lambda: territorial.profile(*POINT),
                args.repeats),
        measure("terrain.terrain_metrics",
                lambda: TM.terrain_metrics(*POINT), args.repeats),
        measure("soil.sample", lambda: soil.sample(*POINT), args.repeats),
        measure("hydrology.watershed (3 km)",
                lambda: hydro.watershed(*POINT, size_m=3000), args.repeats),
        measure("hydrology.profile (3 km, sin caché)",
                lambda: hydro.profile(*POINT, size_m=3000, use_cache=False),
                args.repeats),
        measure("climate.profile", lambda: climate.profile(*POINT),
                args.repeats),
        measure("environmental.profile (3 km, sin caché)",
                lambda: environmental.profile(*POINT, size_m=3000,
                                              use_cache=False),
                args.repeats),
        measure("territorial.territories_in_bbox (nacional)",
                lambda: TR.territories_in_bbox(*C.SV_BOUNDS), args.repeats),
        measure("governance.availability_report",
                lambda: G.availability_report(), args.repeats),
    ]

    # Memoria del perfil más pesado, medida por separado.
    tracemalloc.start()
    before_rss = rss_mb()
    environmental.profile(*POINT, size_m=6000, use_cache=False)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Caché: primera llamada (miss) y segunda (hit) sobre el mismo estado.
    cache_dir = C.DATA / "derived" / "cache"
    before = set(cache_dir.glob("environmental.*.json")) if cache_dir.exists() else set()
    started = time.perf_counter()
    environmental.profile(*POINT, size_m=6000, use_cache=True)
    cold = time.perf_counter() - started
    started = time.perf_counter()
    warm_payload = environmental.profile(*POINT, size_m=6000, use_cache=True)
    warm = time.perf_counter() - started
    after = set(cache_dir.glob("environmental.*.json")) if cache_dir.exists() else set()

    payload = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine_version": G.ENGINE_VERSION,
        "point": {"lon": POINT[0], "lat": POINT[1]},
        "repeats": args.repeats,
        "python": sys.version.split()[0],
        "environment": "local, sin red, artefactos de Fase 1/4",
        "measurements": rows,
        "memory": {
            "rss_before_profile_mb": before_rss,
            "rss_after_profile_mb": rss_mb(),
            "tracemalloc_peak_mb": round(peak / 1e6, 2),
            "note": ("tracemalloc mide asignaciones Python; las reservas de "
                     "rasterio/GDAL no las contabiliza, por eso se informa "
                     "también el RSS del proceso"),
        },
        "cache": {
            "first_call_s": round(cold, 4),
            "second_call_s": round(warm, 4),
            "second_call_hit": bool(warm_payload.get("cache", {}).get("hit")),
            "new_files": len(after - before),
        },
        "notes": [
            "tiempos de una sola máquina; no son un SLA",
            "la ventana hidrológica se lee por bloques: no se carga el DEM nacional",
            "el perfil ambiental incluye clima de reanálisis desde SQLite",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
