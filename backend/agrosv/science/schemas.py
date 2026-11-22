"""Contrato de todo resultado científico de AGROSV.

Regla (PROJECT_VISION.md §5.2): una cifra sin procedencia, resolución e
incertidumbre no es publicable. Este módulo hace esa regla ejecutable: si un
motor intenta devolver un resultado sin `provenance_id`, sin limitaciones o
declarando una predicción sin método de incertidumbre, la validación falla.

Las etiquetas separan clases de dato y no son intercambiables:

    observado  medido o registrado (estación, censo, campo)
    derivado   calculado de forma determinista a partir de observaciones
    estimado   inferido con un modelo estadístico o de calibración
    predicho   pronóstico con horizonte temporal
    simulado   resultado de un modelo de proceso bajo supuestos declarados
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Label = Literal["observado", "derivado", "estimado", "predicho", "simulado"]
Confidence = Literal["alta", "media", "baja"]

# Etiquetas que obligan a declarar cómo se propaga la incertidumbre y que nunca
# pueden presentarse como medición.
NON_OBSERVED: frozenset[str] = frozenset({"estimado", "predicho", "simulado"})


class Uncertainty(BaseModel):
    """Incertidumbre declarada, no decorativa.

    `method` debe nombrar el procedimiento real (cuantiles de entrada, Monte
    Carlo, intervalo de confianza, rango de modelos). No se admiten valores
    «desconocida» sin `note` que explique por qué.
    """

    method: str = Field(min_length=3)
    quantiles: dict[str, float] | None = None
    n_samples: int | None = Field(default=None, ge=0)
    seed: int | None = None
    note: str = ""

    @model_validator(mode="after")
    def _quantiles_ordered(self) -> "Uncertainty":
        if self.quantiles:
            values = list(self.quantiles.values())
            if values != sorted(values):
                raise ValueError(
                    "los cuantiles deben declararse en orden creciente "
                    "(p10 <= p50 <= p90) para que no se puedan intercambiar"
                )
        return self


class ScientificResult(BaseModel):
    """Envoltura obligatoria de una salida de motor.

    `resolution` describe la resolución *real* del dato (la del insumo más
    grueso), nunca la de visualización. `limitations` debe tener al menos una
    entrada: un resultado sin limitaciones declaradas es un error de diseño.
    """

    value: Any
    label: Label
    unit: str | None = None
    method: str = Field(min_length=3)
    model_version: str | None = None
    resolution: str = Field(min_length=2)
    confidence: Confidence
    uncertainty: Uncertainty
    limitations: list[str] = Field(min_length=1)
    provenance_id: str = Field(min_length=3)
    sources: list[str] = Field(default_factory=list)
    derived_at: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _non_observed_declares_uncertainty(self) -> "ScientificResult":
        if self.label in NON_OBSERVED:
            if not self.uncertainty.method:
                raise ValueError(f"label={self.label} exige método de incertidumbre")
            if self.confidence == "alta" and not self.uncertainty.quantiles:
                raise ValueError(
                    "confianza 'alta' en una salida no observada exige cuantiles "
                    "declarados; de lo contrario debe declararse 'media' o 'baja'"
                )
        if self.label == "observado" and self.confidence == "alta" and not self.sources:
            raise ValueError("una observación con confianza alta debe citar su fuente")
        return self

    def as_response(self) -> dict[str, Any]:
        """Serialización estable para la API (sin alias ni campos privados)."""
        return self.model_dump(mode="json")


def wrap(
    value: Any,
    *,
    label: Label,
    method: str,
    resolution: str,
    confidence: Confidence,
    provenance_id: str,
    uncertainty: Uncertainty | None = None,
    limitations: list[str],
    unit: str | None = None,
    sources: list[str] | None = None,
    model_version: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye y valida un resultado publicable en un solo paso."""
    result = ScientificResult(
        value=value,
        label=label,
        unit=unit,
        method=method,
        model_version=model_version,
        resolution=resolution,
        confidence=confidence,
        uncertainty=uncertainty or Uncertainty(
            method="no cuantificada en esta ejecución", note="ver limitations"
        ),
        limitations=limitations,
        provenance_id=provenance_id,
        sources=sources or [],
        extra=extra or {},
    )
    return result.as_response()
