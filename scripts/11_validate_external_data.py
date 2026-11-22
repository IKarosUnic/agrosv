#!/usr/bin/env python3
"""Valida un archivo externo y, opcionalmente, calcula el error del DEM.

No descarga, no imputa y no modifica el archivo. Devuelve JSON y código 1 si el
archivo es inválido.

Ejemplos:
    PYTHONPATH=backend .venv/bin/python scripts/11_validate_external_data.py \\
        --kind station_series --path data/external/estaciones.csv
    PYTHONPATH=backend .venv/bin/python scripts/11_validate_external_data.py \\
        --kind gnss --path data/external/gnss.csv --dem-error
    PYTHONPATH=backend .venv/bin/python scripts/11_validate_external_data.py \\
        --kind crosswalk --path data/reference/municipality_crosswalk_2023.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agrosv.onboarding import dem, validators  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True,
                        choices=sorted(validators.VALIDATORS))
    parser.add_argument("--path", required=True)
    parser.add_argument("--dem-error", action="store_true",
                        help="solo para --kind gnss: comparar con Copernicus DEM")
    args = parser.parse_args()
    report = validators.validate(args.kind, Path(args.path))
    if report["n_rows"] == 0 and report["valid"]:
        report["valid"] = False
        report["errors"].append("el archivo no contiene filas")
        report["error_count"] = 1
    if args.dem_error:
        if args.kind != "gnss":
            report["valid"] = False
            report["errors"].append("--dem-error requiere --kind gnss")
            report["error_count"] = len(report["errors"])
        elif report["valid"]:
            report["dem_error"] = dem.dem_error(args.path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
