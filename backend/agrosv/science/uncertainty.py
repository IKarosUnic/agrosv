"""Gestión de incertidumbre.

Tres operaciones, todas deterministas dado un `seed` explícito:

1. `summarize`: cuantiles P10/P50/P90 de una muestra, con aviso si n es bajo.
2. `monte_carlo`: propagación de distribuciones de entrada declaradas.
3. `robust_z`: anomalía respecto a una línea base usando mediana/MAD.

Ninguna función acepta un seed implícito. Si no se pasa `seed`, se lanza
`ValueError`: un resultado de incertidumbre no reproducible no es publicable
(PROJECT_VISION.md §5.6).

Límite declarado: la propagación Monte Carlo asume independencia entre
entradas salvo que se pase una matriz de correlación. Ignorar la correlación
entre, por ejemplo, temperatura y ET0 subestima el intervalo real.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

import numpy as np


@dataclass(frozen=True)
class Distribution:
    """Distribución declarada de una entrada incierta.

    `kind` ∈ {"uniform", "normal", "lognormal", "triangular"}. Los parámetros
    son los de numpy, sin reinterpretación (`loc`/`scale` son los de la
    distribución nombrada, no media/desviación en todos los casos).
    """

    kind: str
    params: dict[str, float]

    def sample(self, rng: np.random.Generator, n: int) -> np.ndarray:
        k = self.kind.lower()
        if k == "uniform":
            return rng.uniform(self.params["low"], self.params["high"], n)
        if k == "normal":
            return rng.normal(self.params["mean"], self.params["sd"], n)
        if k == "lognormal":
            return rng.lognormal(self.params["mean_log"], self.params["sigma_log"], n)
        if k == "triangular":
            return rng.triangular(self.params["left"], self.params["mode"],
                                  self.params["right"], n)
        raise ValueError(f"distribución no soportada: {self.kind}")

    def validate(self) -> None:
        k = self.kind.lower()
        need = {
            "uniform": ("low", "high"),
            "normal": ("mean", "sd"),
            "lognormal": ("mean_log", "sigma_log"),
            "triangular": ("left", "mode", "right"),
        }
        if k not in need:
            raise ValueError(f"distribución no soportada: {self.kind}")
        missing = [p for p in need[k] if p not in self.params]
        if missing:
            raise ValueError(f"{k}: faltan parámetros {missing}")


def summarize(values: Any, quantiles: tuple[float, ...] = (0.1, 0.5, 0.9)) -> dict[str, Any]:
    """Resumen de una muestra con cuantiles nombrados p10/p50/p90…."""
    arr = np.asarray(values, dtype=float).ravel()
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"n": 0, "quantiles": {}, "note": "muestra vacía"}
    labels = {0.05: "p05", 0.1: "p10", 0.25: "p25", 0.5: "p50",
              0.75: "p75", 0.9: "p90", 0.95: "p95"}
    q = {labels.get(x, f"p{int(round(x * 100)):02d}"): float(np.quantile(arr, x))
         for x in quantiles}
    note = ("n<30: los cuantiles son indicativos" if arr.size < 30 else "")
    return {"n": int(arr.size), "mean": float(arr.mean()),
            "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
            "min": float(arr.min()), "max": float(arr.max()),
            "quantiles": q, "note": note}


def monte_carlo(
    fn: Callable[..., np.ndarray | float],
    inputs: Mapping[str, Distribution],
    *,
    n: int,
    seed: int,
    correlated: np.ndarray | None = None,
) -> dict[str, Any]:
    """Propaga incertidumbre de entrada a través de `fn`.

    `fn` recibe arrays de tamaño `n` con el nombre de cada entrada y devuelve
    un array de tamaño `n`. Debe ser vectorizado: llamar a un modelo escalar
    n veces queda fuera de este helper para que nadie propague 10.000
    simulaciones por bucle inadvertidamente.
    """
    if seed is None:
        raise ValueError("monte_carlo exige seed explícito (reproducibilidad)")
    if n < 10:
        raise ValueError("n < 10 no permite estimar cuantiles: use summarize()")
    for dist in inputs.values():
        dist.validate()

    rng = np.random.default_rng(seed)
    if correlated is not None:
        corr = np.asarray(correlated, dtype=float)
        k = len(inputs)
        if corr.shape != (k, k):
            raise ValueError(f"matriz de correlación debe ser {k}x{k}")
        # Copula gaussiana: preserva rangos de cada marginal y aplica la
        # dependencia declarada entre entradas.
        normals = rng.multivariate_normal(np.zeros(k), corr, size=n)
        ranks = np.argsort(np.argsort(normals, axis=0), axis=0) / (n - 1)
        u = np.clip((ranks + 0.5 / n), 1e-6, 1 - 1e-6)
        # Transformada inversa aproximada por cuantiles empíricos de la
        # marginal: no requiere scipy y conserva la distribución declarada.
        draws = {}
        for j, (name, dist) in enumerate(inputs.items()):
            sample = np.sort(dist.sample(rng, n))
            idx = np.clip((u[:, j] * (n - 1)).round().astype(int), 0, n - 1)
            draws[name] = sample[idx]
    else:
        draws = {name: dist.sample(rng, n) for name, dist in inputs.items()}

    out = np.asarray(fn(**draws), dtype=float).ravel()
    if out.size != n:
        raise ValueError(f"fn devolvió {out.size} valores; se esperaban {n}")
    summary = summarize(out, (0.05, 0.1, 0.5, 0.9, 0.95))
    summary.update({"method": "Monte Carlo", "n_samples": n, "seed": seed,
                    "correlated": correlated is not None})
    return summary


def robust_z(value: float | np.ndarray, baseline: Any) -> float | np.ndarray:
    """Anomalía robusta (mediana/MAD) frente a una línea base declarada.

    MAD escalado por 1,4826 para ser comparable con una desviación estándar.
    Si la línea base es constante (MAD = 0) devuelve NaN en lugar de infinito:
    una anomalía infinita no es información.
    """
    base = np.asarray(baseline, dtype=float).ravel()
    base = base[np.isfinite(base)]
    if base.size < 3:
        raise ValueError("línea base con menos de 3 observaciones válidas")
    med = float(np.median(base))
    mad = float(np.median(np.abs(base - med))) * 1.4826
    if mad == 0:
        return np.full_like(np.asarray(value, dtype=float), np.nan)
    return (np.asarray(value, dtype=float) - med) / mad


def coverage(intervals: list[tuple[float, float]], observed: list[float]) -> dict[str, float]:
    """Cobertura empírica de intervalos: ¿cuántas observaciones caen dentro?

    Se usa para validar la incertidumbre declarada, no solo el valor central.
    Un P10–P90 que contiene el 40 % de las observaciones está mal calibrado
    aunque la media sea correcta.
    """
    if len(intervals) != len(observed):
        raise ValueError("intervals y observed deben tener igual longitud")
    if not intervals:
        raise ValueError("sin intervalos que evaluar")
    inside = sum(1 for (lo, hi), o in zip(intervals, observed) if lo <= o <= hi)
    n = len(intervals)
    return {"n": n, "inside": inside, "coverage": inside / n}
