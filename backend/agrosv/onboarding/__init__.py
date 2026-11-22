"""AGROSV — incorporación controlada de datos externos (Fase 7).

No adquiere datos por sí mismo. Verifica archivos aportados por el usuario con
reglas estrictas y publica qué falta, sin imputar valores.

Solo la correspondencia municipal 2023 está adquirida; las series de estación,
muestras CENTA, cuencas, aforos y puntos GNSS siguen pendientes.
"""
from __future__ import annotations

__all__ = ["registry", "validators", "municipalities", "dem", "api"]

from . import dem, municipalities, registry, validators  # noqa: F401
