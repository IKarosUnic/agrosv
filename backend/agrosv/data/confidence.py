"""AGROSV — modelo de incertidumbre y confianza (Fase 4, §10).

Este módulo existe para impedir dos atajos frecuentes:

1. **Un índice de confianza inventado.** No hay una puntuación única por
   defecto. Un compuesto solo se calcula si el modelo declara componentes,
   método, pesos y metodología; si falta un componente, no se calcula.
2. **Confundir resolución con precisión.** `assert_resolution_is_not_accuracy`
   rechaza afirmaciones que deduzcan exactitud de la resolución espacial. Un
   ráster de 10 m puede tener un error de 30 m; un mapa a 250 m puede tener un
   sesgo de 5 cm de textura.

Componentes separados (no intercambiables):

    measurement    error de instrumento, muestreo y laboratorio
    model          error estructural/paramétrico del modelo
    spatial        soporte espacial, agregación, desplazamiento de píxel
    temporal       fecha de observación, agregación, desfase
    classification error de clase (cobertura, suelo, cultivo)
    provenance     fiabilidad de la fuente y de su cadena de custodia

Una etiqueta `alta` exige que **todos** los componentes estén cuantificados y
un compuesto relativo por debajo del umbral declarado. Sin eso, `media` o
`baja`. La etiqueta sirve para no publicar de más; no para comparar datasets de
distinta naturaleza.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Sequence

from . import temporal as T


class UncertaintyError(ValueError):
    pass


class UncertaintyComponent(str, Enum):
    MEASUREMENT = "measurement"
    MODEL = "model"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    CLASSIFICATION = "classification"
    PROVENANCE = "provenance"


COMPONENT_LABELS = {
    UncertaintyComponent.MEASUREMENT: "error de medición",
    UncertaintyComponent.MODEL: "incertidumbre del modelo",
    UncertaintyComponent.SPATIAL: "incertidumbre espacial",
    UncertaintyComponent.TEMPORAL: "incertidumbre temporal",
    UncertaintyComponent.CLASSIFICATION: "incertidumbre de clasificación",
    UncertaintyComponent.PROVENANCE: "incertidumbre de procedencia",
}


@dataclass
class ComponentStatement:
    component: UncertaintyComponent
    quantified: bool
    method: str = ""
    standard_uncertainty: float | None = None  # en la unidad de la variable
    relative_uncertainty: float | None = None  # fracción (0,16 = 16 %)
    interval: tuple[float, float] | None = None
    basis: str = ""
    not_quantified_reason: str = ""

    def __post_init__(self) -> None:
        if self.quantified:
            if not self.method.strip():
                raise UncertaintyError(
                    f"{self.component.value}: cuantificado sin método declarado")
            if (self.standard_uncertainty is None
                    and self.relative_uncertainty is None
                    and self.interval is None):
                raise UncertaintyError(
                    f"{self.component.value}: cuantificado sin valor ni intervalo")
        else:
            if not self.not_quantified_reason.strip():
                raise UncertaintyError(
                    f"{self.component.value}: no cuantificado exige explicar por qué")

    def as_dict(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "label": COMPONENT_LABELS[self.component],
            "quantified": self.quantified,
            "method": self.method,
            "standard_uncertainty": self.standard_uncertainty,
            "relative_uncertainty": self.relative_uncertainty,
            "interval": list(self.interval) if self.interval else None,
            "basis": self.basis,
            "not_quantified_reason": self.not_quantified_reason,
        }


@dataclass
class ConfidencePolicy:
    """Umbrales declarados del proyecto. Se documentan, no se ajustan por caso."""

    high_max_relative: float = 0.10
    medium_max_relative: float = 0.30
    require_all_quantified_for_high: bool = True

    def label(self, relative: float | None, *,
              all_quantified: bool) -> str:
        if relative is None:
            return "baja"
        if (relative <= self.high_max_relative
                and (all_quantified or not self.require_all_quantified_for_high)):
            return "alta"
        if relative <= self.medium_max_relative:
            return "media"
        return "baja"

    def as_dict(self) -> dict[str, Any]:
        return {
            "high_max_relative": self.high_max_relative,
            "medium_max_relative": self.medium_max_relative,
            "require_all_quantified_for_high": self.require_all_quantified_for_high,
            "note": ("umbrales de publicación de AGROSV; no son una propiedad "
                     "del dato y no sirven para comparar fuentes entre sí"),
        }


@dataclass
class UncertaintyModel:
    dataset_id: str
    variable: str
    unit: str
    components: dict[UncertaintyComponent, ComponentStatement]
    methodology: str
    policy: ConfidencePolicy = field(default_factory=ConfidencePolicy)
    evidence_class: T.EvidenceClass = T.EvidenceClass.OBSERVATION
    reference_value: float | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.methodology.strip():
            raise UncertaintyError(
                "un modelo de incertidumbre sin metodología no es publicable")
        missing = [c.value for c in UncertaintyComponent
                   if c not in self.components]
        if missing:
            raise UncertaintyError(
                f"faltan componentes de incertidumbre: {missing}. Omitir una "
                "componente no la elimina; la oculta")

    def component(self, which: UncertaintyComponent | str) -> ComponentStatement:
        return self.components[UncertaintyComponent(str(which))]

    @property
    def all_quantified(self) -> bool:
        return all(c.quantified for c in self.components.values())

    def relative_uncertainty(self, *, aggregation: str = "rss") -> float | None:
        """Compuesto relativo solo si todos los componentes están cuantificados."""
        if not self.all_quantified:
            return None
        values = []
        for comp in self.components.values():
            if comp.relative_uncertainty is not None:
                values.append(comp.relative_uncertainty)
            elif (comp.standard_uncertainty is not None
                  and self.reference_value not in (None, 0)):
                values.append(comp.standard_uncertainty / abs(self.reference_value))
            else:
                return None
        if aggregation == "rss":
            return math.sqrt(sum(v * v for v in values))
        if aggregation == "linear":
            return sum(values)
        raise UncertaintyError(f"agregación desconocida: {aggregation}")

    def composite(self, *, weights: dict[str, float] | None = None,
                  aggregation: str = "rss") -> dict[str, Any]:
        """Compuesto explícito. Sin pesos declarados no se inventan."""
        if weights is None:
            raise UncertaintyError(
                "no se calcula un compuesto sin pesos declarados: un índice "
                "arbitrario oculta más de lo que informa. Declare `weights` y "
                "justifíquelo en `methodology`.")
        unknown = set(weights) - {c.value for c in UncertaintyComponent}
        if unknown:
            raise UncertaintyError(f"pesos para componentes desconocidos: {unknown}")
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise UncertaintyError(f"los pesos deben sumar 1 (suman {total})")
        unquantified = [c.component.value for c in self.components.values()
                        if not c.quantified]
        if unquantified:
            raise UncertaintyError(
                f"no se compone con componentes sin cuantificar: {unquantified}")
        rel = self.relative_uncertainty(aggregation=aggregation)
        return {
            "dataset_id": self.dataset_id,
            "variable": self.variable,
            "unit": self.unit,
            "aggregation": aggregation,
            "weights": weights,
            "relative_uncertainty": rel,
            "confidence": self.policy.label(rel or 1.0,
                                            all_quantified=self.all_quantified),
            "methodology": self.methodology,
            "components": [c.as_dict() for c in self.components.values()],
            "policy": self.policy.as_dict(),
            "limits": [
                "el compuesto supone independencia entre componentes; con "
                "correlación debe declararse y no se usa 'rss'",
                "un intervalo compuesto no es una distribución completa",
            ],
        }

    def confidence_label(self) -> dict[str, Any]:
        """Etiqueta cualitativa con su justificación, sin compuesto numérico."""
        rel = self.relative_uncertainty()
        missing = [c.component.value for c in self.components.values()
                   if not c.quantified]
        label = self.policy.label(rel, all_quantified=self.all_quantified)
        return {
            "confidence": label,
            "relative_uncertainty": rel,
            "unquantified_components": missing,
            "reason": (
                "todos los componentes cuantificados y compuesto bajo el umbral"
                if self.all_quantified and label == "alta" else
                f"componentes sin cuantificar: {missing}" if missing else
                "compuesto por encima del umbral de confianza alta"
            ),
            "policy": self.policy.as_dict(),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "variable": self.variable,
            "unit": self.unit,
            "evidence_class": self.evidence_class.value,
            "methodology": self.methodology,
            "reference_value": self.reference_value,
            "components": [c.as_dict() for c in self.components.values()],
            "all_quantified": self.all_quantified,
            "confidence": self.confidence_label(),
            "notes": self.notes,
        }


def unquantified_template(*, dataset_id: str, variable: str, unit: str,
                          methodology: str = "",
                          evidence_class: T.EvidenceClass = T.EvidenceClass.OBSERVATION,
                          reasons: dict[UncertaintyComponent, str] | None = None
                          ) -> UncertaintyModel:
    """Plantilla honesta: todo sin cuantificar hasta que exista evidencia.

    Se usa al registrar un dataset nuevo. Completar componentes es un acto
    científico, no un formulario: cada uno exige método y base.
    """
    reasons = reasons or {}
    components = {
        c: ComponentStatement(
            component=c, quantified=False,
            not_quantified_reason=reasons.get(
                c, "no cuantificada en esta fase; requiere datos de referencia "
                   "o repeticiones que aún no están disponibles"),
        )
        for c in UncertaintyComponent
    }
    return UncertaintyModel(
        dataset_id=dataset_id, variable=variable, unit=unit,
        components=components,
        methodology=methodology or (
            "modelo declarativo: componentes identificados pero no cuantificados "
            "con los datos disponibles"),
        evidence_class=evidence_class,
    )


def assert_resolution_is_not_accuracy(claim: dict[str, Any]) -> dict[str, Any]:
    """Rechaza afirmaciones que deduzcan exactitud de la resolución.

    `claim` puede declarar `resolution` y `accuracy` como campos separados. Si
    solo hay resolución, no se puede afirmar exactitud.
    """
    resolution = claim.get("resolution")
    accuracy = claim.get("accuracy")
    if resolution and not accuracy:
        raise UncertaintyError(
            f"resolución declarada ({resolution}) sin exactitud verificada: la "
            "resolución espacial no es una medida de precisión. Declare "
            "`accuracy` con su método de validación.")
    if accuracy and not claim.get("accuracy_method"):
        raise UncertaintyError(
            "exactitud sin método de validación: declare cómo se obtuvo")
    return {
        "resolution": resolution,
        "accuracy": accuracy,
        "accuracy_method": claim.get("accuracy_method"),
        "rule": "resolución ≠ precisión; jerarquía nacional ≠ superioridad científica",
    }


def compare_source_uncertainty(models: Sequence[UncertaintyModel]) -> dict[str, Any]:
    """Compara incertidumbre declarada entre fuentes, sin ordenar por país."""
    rows = []
    for model in models:
        label = model.confidence_label()
        rows.append({
            "dataset_id": model.dataset_id,
            "evidence_class": model.evidence_class.value,
            "confidence": label["confidence"],
            "relative_uncertainty": label["relative_uncertainty"],
            "unquantified": label["unquantified_components"],
        })
    return {
        "sources": rows,
        "comparable": all(r["relative_uncertainty"] is not None for r in rows),
        "note": ("una fuente nacional no es superior por ser nacional: la "
                 "comparación exige metodología y validación equivalentes"),
    }


def provenance_penalty(source_class: str) -> ComponentStatement:
    """Declaración de incertidumbre de procedencia por clase de fuente.

    Es una plantilla, no una medición: el valor cuantificado debe venir de la
    auditoría de la cadena de custodia.
    """
    classes = {
        "official_measured": "fuente oficial con metodología publicada",
        "official_aggregate": "agregado oficial sin microdato accesible",
        "global_model": "producto global modelado, no medido en el país",
        "third_party": "fuente secundaria sin cadena de custodia verificada",
        "community": "reporte comunitario sin verificación independiente",
        "synthetic": "dato sintético, no observado",
    }
    if source_class not in classes:
        raise UncertaintyError(
            f"clase de procedencia desconocida: {source_class}; use {sorted(classes)}")
    return ComponentStatement(
        component=UncertaintyComponent.PROVENANCE, quantified=False,
        not_quantified_reason=(f"{classes[source_class]}: falta auditoría "
                              "cuantitativa de la cadena de custodia"),
        basis=classes[source_class],
    )


def component_summary(model: UncertaintyModel) -> dict[str, Any]:
    return {
        "dataset_id": model.dataset_id,
        "by_component": {c.value: s.as_dict() for c, s in model.components.items()},
        "quantified": sum(1 for s in model.components.values() if s.quantified),
        "total_components": len(model.components),
        "confidence": model.confidence_label(),
    }


def required_components_for(evidence_class: T.EvidenceClass) -> set[UncertaintyComponent]:
    """Componentes mínimos según la clase de evidencia declarada."""
    base = {UncertaintyComponent.PROVENANCE, UncertaintyComponent.TEMPORAL}
    if evidence_class is T.EvidenceClass.OBSERVATION:
        return base | {UncertaintyComponent.MEASUREMENT, UncertaintyComponent.SPATIAL}
    if evidence_class is T.EvidenceClass.REANALYSIS:
        return base | {UncertaintyComponent.MODEL, UncertaintyComponent.SPATIAL}
    if evidence_class is T.EvidenceClass.FORECAST:
        return base | {UncertaintyComponent.MODEL, UncertaintyComponent.TEMPORAL}
    if evidence_class is T.EvidenceClass.CLIMATE_PROJECTION:
        return base | {UncertaintyComponent.MODEL}
    if evidence_class is T.EvidenceClass.SIMULATION:
        return base | {UncertaintyComponent.MODEL}
    return base | {UncertaintyComponent.CLASSIFICATION}


def validate_model_completeness(model: UncertaintyModel) -> list[str]:
    """Devuelve componentes exigidos que están sin cuantificar."""
    required: Iterable[UncertaintyComponent] = required_components_for(
        model.evidence_class)
    return [c.value for c in required
            if not model.components[c].quantified]
