"""Motor de índices espectrales (Módulo A, aritmética de bandas).

Contiene solo el cálculo, declarado por fórmula y por resolución nativa. La
adquisición de imágenes (STAC/CDSE), el enmascarado de nubes y los compuestos
temporales quedan fuera de este módulo: aquí no se inventa ninguna escena.

Reglas aplicadas:

  * cada índice declara la resolución de las bandas que usa; NDMI/NBR en
    Sentinel-2 son 20 m aunque se visualicen sobre 10 m;
  * un denominador nulo o un píxel sin dato produce NaN, no cero (un cero es
    un valor de índice válido y no debe confundirse con ausencia);
  * los índices se recortan a [−1, 1] porque fuera de ese rango la fórmula ya
    no describe una razón normalizada.

Advertencia: un índice de vegetación **no** identifica un cultivo ni diagnostica
una plaga. Es una señal de vigor/agua a la resolución del píxel.
"""
from __future__ import annotations

from typing import Any

import numpy as np

INDEX_SPECS: dict[str, dict[str, Any]] = {
    "ndvi": {
        "name": "NDVI",
        "formula": "(NIR - R) / (NIR + R)",
        "bands": ["nir", "red"],
        "sentinel2_bands": ["B08", "B04"],
        "resolution_m": 10,
        "measures": "vigor y fenología de la vegetación",
        "limitations": [
            "satura en dosel denso (café bajo sombra, bosque cerrado)",
            "píxeles mixtos: 10 m puede contener cultivo, suelo y sombra",
            "no distingue cultivo de maleza ni de vegetación natural",
        ],
    },
    "evi": {
        "name": "EVI",
        "formula": "2.5·(NIR - R) / (NIR + 6R - 7.5B + 1)",
        "bands": ["nir", "red", "blue"],
        "sentinel2_bands": ["B08", "B04", "B02"],
        "resolution_m": 10,
        "measures": "biomasa en coberturas densas",
        "limitations": [
            "sensible a aerosoles y a la corrección atmosférica",
            "requiere banda azul despejada",
        ],
    },
    "ndwi": {
        "name": "NDWI (McFeeters)",
        "formula": "(G - NIR) / (G + NIR)",
        "bands": ["green", "nir"],
        "sentinel2_bands": ["B03", "B08"],
        "resolution_m": 10,
        "measures": "agua superficial",
        "limitations": [
            "no mide humedad del suelo",
            "confunde agua somera con sombra en relieve abrupto",
        ],
    },
    "ndmi": {
        "name": "NDMI",
        "formula": "(NIR - SWIR1) / (NIR + SWIR1)",
        "bands": ["nir", "swir1"],
        "sentinel2_bands": ["B08", "B11"],
        "resolution_m": 20,
        "measures": "contenido de agua de la vegetación",
        "limitations": [
            "en Sentinel-2 la banda SWIR1 es de 20 m: la resolución efectiva "
            "del índice es 20 m, no 10 m",
        ],
    },
    "nbr": {
        "name": "NBR",
        "formula": "(NIR - SWIR2) / (NIR + SWIR2)",
        "bands": ["nir", "swir2"],
        "sentinel2_bands": ["B08", "B12"],
        "resolution_m": 20,
        "measures": "severidad de incendio y cobertura post-fuego",
        "limitations": [
            "resolución efectiva 20 m en Sentinel-2",
            "no sustituye la verificación de campo del daño",
        ],
    },
}


def to_reflectance(dn: np.ndarray, *, scale: float = 1e-4,
                   offset: float = 0.0) -> np.ndarray:
    """Convierte entero digital a reflectancia.

    Sentinel-2 L2A desde la línea de base 04.00 usa `offset = -1000` además de
    `scale = 1e-4`. El valor por defecto replica el producto anterior; usar el
    offset correcto es responsabilidad del pipeline y debe declararse.
    """
    arr = np.asarray(dn, dtype=np.float32)
    out = arr * scale + offset * scale
    return np.where(np.isfinite(out), out, np.nan).astype(np.float32)


def _normalized(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    n = np.asarray(num, dtype=np.float32)
    d = np.asarray(den, dtype=np.float32)
    if n.shape != d.shape:
        raise ValueError(f"bandas de distinta forma: {n.shape} vs {d.shape}")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = n / d
    out = np.where(np.abs(d) < 1e-6, np.nan, out)
    out = np.where(np.isfinite(out), out, np.nan)
    return np.clip(out, -1.0, 1.0).astype(np.float32)


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    return _normalized(np.asarray(nir, np.float32) - red, np.asarray(nir, np.float32) + red)


def evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    nir = np.asarray(nir, np.float32)
    red = np.asarray(red, np.float32)
    blue = np.asarray(blue, np.float32)
    den = nir + 6.0 * red - 7.5 * blue + 1.0
    return _normalized(2.5 * (nir - red), den)


def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    g = np.asarray(green, np.float32)
    return _normalized(g - nir, g + np.asarray(nir, np.float32))


def ndmi(nir: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    n = np.asarray(nir, np.float32)
    return _normalized(n - swir1, n + np.asarray(swir1, np.float32))


def nbr(nir: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    n = np.asarray(nir, np.float32)
    return _normalized(n - swir2, n + np.asarray(swir2, np.float32))


def compute(name: str, bands: dict[str, np.ndarray]) -> np.ndarray:
    """Calcula un índice por nombre, exigiendo las bandas que declara su ficha."""
    key = name.lower()
    if key not in INDEX_SPECS:
        raise KeyError(f"índice desconocido: {name}; use {sorted(INDEX_SPECS)}")
    required = INDEX_SPECS[key]["bands"]
    missing = [b for b in required if b not in bands]
    if missing:
        raise KeyError(f"{key} requiere las bandas {missing}")
    if key == "ndvi":
        return ndvi(bands["nir"], bands["red"])
    if key == "evi":
        return evi(bands["nir"], bands["red"], bands["blue"])
    if key == "ndwi":
        return ndwi(bands["green"], bands["nir"])
    if key == "ndmi":
        return ndmi(bands["nir"], bands["swir1"])
    return nbr(bands["nir"], bands["swir2"])


def change_mask(before: np.ndarray, after: np.ndarray, *,
                threshold: float) -> dict[str, Any]:
    """Diferencia entre dos fechas con umbral explícito y declarado.

    Devuelve «cambio detectado», no «deforestación» ni «pérdida»: atribuir una
    causa exige datos que un índice no contiene.
    """
    if threshold <= 0:
        raise ValueError("threshold debe ser positivo y estar justificado")
    b = np.asarray(before, dtype=np.float32)
    a = np.asarray(after, dtype=np.float32)
    if b.shape != a.shape:
        raise ValueError("las dos fechas deben tener la misma rejilla")
    delta = a - b
    valid = np.isfinite(delta)
    changed = valid & (np.abs(delta) >= threshold)
    return {
        "delta": np.where(valid, delta, np.nan),
        "changed": changed,
        "decrease": changed & (delta < 0),
        "increase": changed & (delta > 0),
        "threshold": threshold,
        "valid_pixels": int(valid.sum()),
        "changed_pixels": int(changed.sum()),
        "changed_pct": round(100.0 * changed.sum() / max(int(valid.sum()), 1), 3),
    }


def series_anomaly(series: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    """Anomalía robusta (mediana/MAD) de una serie contra su línea base."""
    from .uncertainty import robust_z

    return np.asarray(robust_z(np.asarray(series, dtype=float),
                              np.asarray(baseline, dtype=float)), dtype=float)


def specs() -> dict[str, dict[str, Any]]:
    """Fichas de los índices, para documentación y API."""
    return {k: dict(v) for k, v in INDEX_SPECS.items()}
