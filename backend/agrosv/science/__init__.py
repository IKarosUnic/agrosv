"""AGROSV — infraestructura científica transversal (Fase 2).

Estos módulos existen para que ningún resultado de AGROSV pueda publicarse sin
fuente, clase de modelo, resolución real, incertidumbre y limitaciones. No son
utilidades de conveniencia: son las condiciones de publicación de la Fase 2
(ver `docs/SCIENTIFIC_VALIDATION_PROTOCOL.md` y `PROJECT_VISION.md` §5).

Mapa de responsabilidades:

    schemas          contrato ScientificResult (etiqueta, resolución, incertidumbre)
    registry         catálogo y versionado de datasets a partir de los manifiestos
    qc               control de calidad geoespacial
    uncertainty      cuantiles, propagación Monte Carlo, anomalía robusta
    validation       métricas observado-vs-modelado y niveles de evidencia V0–V4
    reproducibility  manifiestos de ejecución verificables por hash
    orchestrator     ejecución por lotes con dependencias, reintentos y reanudación
    hydrology        D8, relleno de sumideros, acumulación, cuenca, LS
    indices          índices espectrales (NDVI, EVI, NDWI, NDMI, NBR)
"""
from __future__ import annotations

__all__ = [
    "schemas",
    "registry",
    "qc",
    "uncertainty",
    "validation",
    "reproducibility",
    "orchestrator",
    "hydrology",
    "indices",
]
