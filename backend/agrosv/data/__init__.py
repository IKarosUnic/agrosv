"""AGROSV — infraestructura de datos nacionales (Fase 4).

Capa que convierte datasets heterogéneos en datos consultables sin perder
procedencia, resolución, unidades ni incertidumbre. Se apoya en
`agrosv.science` (Fase 2) y no duplica sus motores: reutiliza el contrato
`ScientificResult`, el catálogo de manifiestos, el QC de Fase 2, la propagación
de incertidumbre, los niveles de evidencia V0–V4, los manifiestos de ejecución y
el orquestador de lotes.

Mapa de responsabilidades:

    storage      zonas de datos, política Git, nombres, deduplicación por hash
    catalog      catálogo nacional con 9 estados y puertas de evidencia
    units        unidades canónicas, conversiones y dominios de error grosero
    ingest       ingesta multi-formato, integridad, reanudación por lotes
    geo          CRS, transformaciones, diagnóstico y reparación registrada
    territory    sistema de referencia territorial con ids estables
    raster       perfiles, ventanas, remuestreo declarado, contenedores
    temporal     base temporal, clase de evidencia, frecuencias y calendarios
    quality      motor de calidad espacial, temporal, numérico y científico
    confidence   modelo de incertidumbre por componentes (sin índice arbitrario)
    lineage      grafo de derivaciones y reconstrucción de productos
    domains      contratos de datos por dominio (A–H)
    store        SQLite: series normalizadas, ocurrencias y territorios
    api          endpoints `/api/data`
    pipeline     monitoreo, vigencia y detección de versiones nuevas
"""
from __future__ import annotations

__all__ = [
    "storage",
    "catalog",
    "units",
    "ingest",
    "geo",
    "territory",
    "raster",
    "temporal",
    "quality",
    "confidence",
    "lineage",
    "domains",
    "store",
    "api",
    "pipeline",
]
