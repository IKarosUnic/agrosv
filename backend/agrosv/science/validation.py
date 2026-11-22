"""Motor de validación científica.

Calcula métricas de concordancia entre observado y modelado y asigna un nivel
de evidencia V0–V4. El nivel no se elige: se deduce de la evidencia disponible.

    V0  sin validación externa (solo ejecución)
    V1  consistencia interna (rangos, balance, monotonía)
    V2  comparación con referencia agregada (departamento, municipio)
    V3  comparación con serie o estación de referencia en el punto
    V4  validación independiente contra campo o censo no usado en calibración

Regla dura: V2 o superior exige al menos `MIN_V2_PAIRS` pares y una fuente de
observación declarada. Sin eso, la función devuelve V1 como máximo y explica
por qué. No existe un camino para «ascender» un nivel por decisión del usuario.
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np

MIN_PAIRS = 3
MIN_V2_PAIRS = 10
MIN_V3_PAIRS = 30


def metrics(observed: Sequence[float], modeled: Sequence[float],
            *, n_params: int = 1) -> dict[str, Any]:
    """Bias, MAE, RMSE, R², NSE, PBIAS y KGE entre observado y modelado."""
    o = np.asarray(observed, dtype=float)
    m = np.asarray(modeled, dtype=float)
    if o.shape != m.shape:
        raise ValueError(f"formas distintas: observado {o.shape} vs modelado {m.shape}")
    mask = np.isfinite(o) & np.isfinite(m)
    o, m = o[mask], m[mask]
    n = int(o.size)
    if n < MIN_PAIRS:
        raise ValueError(f"se requieren al menos {MIN_PAIRS} pares válidos; hay {n}")

    err = m - o
    bias = float(err.mean())
    mae = float(np.abs(err).mean())
    rmse = float(np.sqrt(np.mean(err ** 2)))
    denom = float(np.sum((o - o.mean()) ** 2))
    nse = float(1 - np.sum(err ** 2) / denom) if denom > 0 else float("nan")
    r = float(np.corrcoef(o, m)[0, 1]) if n > 1 and o.std() > 0 and m.std() > 0 \
        else float("nan")
    r2 = float(r ** 2) if np.isfinite(r) else float("nan")
    pbias = float(100.0 * err.sum() / o.sum()) if o.sum() != 0 else float("nan")

    # KGE (Gupta et al. 2009): descompone en correlación, sesgo y variabilidad.
    sd_ratio = float(m.std(ddof=0) / o.std(ddof=0)) if o.std(ddof=0) > 0 else float("nan")
    beta = float(m.mean() / o.mean()) if o.mean() != 0 else float("nan")
    kge = (float(1 - np.sqrt((r - 1) ** 2 + (beta - 1) ** 2 + (sd_ratio - 1) ** 2))
           if all(np.isfinite(v) for v in (r, beta, sd_ratio)) else float("nan"))

    return {
        "n": n,
        "bias": bias,
        "mae": mae,
        "rmse": rmse,
        "r": r,
        "r2": r2,
        "nse": nse,
        "pbias_pct": pbias,
        "kge": kge,
        "sd_ratio": sd_ratio,
        "beta": beta,
        "n_params": n_params,
        "caveat": ("métricas agregadas: no demuestran validez por parcela"
                   if n < MIN_V3_PAIRS else ""),
    }


def evidence_level(
    n: int,
    *,
    reference_scale: str | None = None,
    observation_source: str | None = None,
    independent: bool = False,
) -> dict[str, Any]:
    """Determina el nivel V0–V4 alcanzable con la evidencia disponible."""
    if n <= 0:
        level, why = "V0", "sin pares observado-modelado"
    elif n < MIN_V2_PAIRS:
        level, why = "V1", f"solo {n} pares (< {MIN_V2_PAIRS})"
    elif not observation_source:
        level, why = "V1", "no se declaró la fuente de observación"
    elif reference_scale in {"department", "municipality", "national"}:
        if independent and n >= MIN_V3_PAIRS:
            level, why = "V4", "comparación independiente no usada en calibración"
        elif n >= MIN_V3_PAIRS:
            level, why = "V3", "referencia agregada con n suficiente"
        else:
            level, why = "V2", f"referencia {reference_scale} agregada"
    elif reference_scale == "point":
        if independent and n >= MIN_V3_PAIRS:
            level, why = "V4", "validación puntual independiente de la calibración"
        elif n >= MIN_V3_PAIRS:
            level, why = "V3", "referencia puntual con n suficiente"
        else:
            level, why = "V2", "referencia puntual con n insuficiente para V3"
    else:
        level, why = "V1", "escala de referencia no declarada"
    return {"level": level, "n": n, "reason": why,
            "independent": independent, "reference_scale": reference_scale}


def report(observed: Sequence[float], modeled: Sequence[float], *,
           reference_scale: str | None = None,
           observation_source: str | None = None,
           independent: bool = False) -> dict[str, Any]:
    """Informe completo: métricas + nivel de evidencia + advertencias."""
    m = metrics(observed, modeled)
    level = evidence_level(m["n"], reference_scale=reference_scale,
                           observation_source=observation_source,
                           independent=independent)
    warnings = []
    if m["n"] < MIN_V3_PAIRS:
        warnings.append(
            f"n={m['n']}: insuficiente para validación por punto (V3 exige "
            f"{MIN_V3_PAIRS}); el resultado es agregado"
        )
    if level["level"] in {"V0", "V1"}:
        warnings.append(
            "sin validación externa: el resultado no debe presentarse como "
            "«validado» ni como rendimiento real esperado"
        )
    if np.isfinite(m["nse"]) and m["nse"] < 0:
        warnings.append("NSE < 0: el modelo es peor que usar la media observada")
    return {"metrics": m, "evidence": level, "warnings": warnings}
