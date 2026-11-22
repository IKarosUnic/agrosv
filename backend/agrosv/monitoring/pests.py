"""AGROSV — motores de plagas y enfermedades (Fase 7, §6).

`PestKnowledgeEngine` y `PlantDiseaseKnowledgeEngine` exponen el catálogo
trazable de `knowledge.py`. `PestRiskEngine` y `DiseaseRiskEngine` separan:

    presencia documentada  ≠  idoneidad ambiental  ≠  exposición del cultivo
    ≠  daño potencial  ≠  diagnóstico

La idoneidad se calcula **solo** con ventanas cuantitativas que declaran fuente,
o con reglas aportadas por el llamador con `rules_source`. Si no hay ventana, el
resultado es `None` + GAP: no se inventa un umbral.

`AgriculturalPhytosanitaryEngine` conserva la procedencia de cada registro y no
permite etiquetar un reporte comunitario como comunicado oficial.
"""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Any, Iterable

from . import governance as G
from .knowledge import DISEASES, EVIDENCE_QUALITY, PESTS, PRESENCE_SCOPES

PEST_ENGINE = "pest_knowledge"
DISEASE_ENGINE = "plant_disease_knowledge"
PEST_RISK_ENGINE = "pest_risk"
DISEASE_RISK_ENGINE = "disease_risk"
PHYTO_ENGINE = "agricultural_phytosanitary"
ENGINE_VERSION = G.ENGINE_VERSION

#: Tipos de registro fitosanitario admitidos.
PHYTO_KINDS = ("official_notice", "scientific_publication", "extension_report",
               "community_report", "algorithmic_risk_estimate")


def _require_rule_source(source: str | None) -> str:
    if not source or len(str(source).strip()) < 3:
        raise G.MonitoringError(
            "las reglas de riesgo exigen `rules_source`; no se inventan umbrales")
    return str(source)


class _Catalog:
    catalog: dict[str, dict] = {}
    engine = ""
    id_key = ""

    def list(self, *, crop: str | None = None,
             presence: str | None = None) -> dict[str, Any]:
        items = []
        for key in sorted(self.catalog):
            record = self.catalog[key]
            if crop and crop.lower() not in record.get("affected_crops", []):
                continue
            scope = (record.get("distribution") or {}).get("presence_scope")
            if presence and scope != presence:
                continue
            items.append(self._brief(record))
        return {"count": len(items), "items": items,
                "presence_scopes": list(PRESENCE_SCOPES)}

    def get(self, record_id: str) -> dict[str, Any]:
        key = record_id.lower()
        if key not in self.catalog:
            raise KeyError(f"registro desconocido: {record_id}; "
                           f"use {sorted(self.catalog)}")
        return dict(self.catalog[key])

    def search(self, query: str) -> dict[str, Any]:
        needle = query.strip().lower()
        if len(needle) < 3:
            raise G.MonitoringError("la búsqueda requiere ≥ 3 caracteres")
        hits = []
        for key, record in self.catalog.items():
            haystack = " ".join([
                key,
                str(record.get("scientific_name") or ""),
                str((record.get("causal_organism") or {}).get("scientific_name") or ""),
                " ".join(record.get("common_names") or []),
                " ".join(record.get("local_names") or []),
                str(record.get("name") or ""),
            ]).lower()
            if needle in haystack:
                hits.append(self._brief(record))
        return {"query": query, "count": len(hits), "items": hits}

    def audit(self) -> dict[str, Any]:
        by_scope: dict[str, int] = {k: 0 for k in PRESENCE_SCOPES}
        by_quality: dict[str, int] = {k: 0 for k in EVIDENCE_QUALITY}
        without_windows = 0
        for record in self.catalog.values():
            scope = (record.get("distribution") or {}).get("presence_scope")
            by_scope[scope] = by_scope.get(scope, 0) + 1
            by_quality[record["evidence_quality"]] += 1
            if not record.get("environmental_windows"):
                without_windows += 1
        return {
            "engine": self.engine, "count": len(self.catalog),
            "by_presence_scope": by_scope, "by_evidence_quality": by_quality,
            "without_quantitative_window": without_windows,
            "note": ("un registro sin ventana cuantitativa no permite calcular "
                     "idoneidad ambiental; se publica GAP"),
        }

    def _brief(self, record: dict[str, Any]) -> dict[str, Any]:
        out = {
            "id": record[self.id_key],
            "scientific_name": (record.get("scientific_name")
                                or (record.get("causal_organism") or {}
                                    ).get("scientific_name")),
            "common_names": record.get("common_names") or [record.get("name")],
            "affected_crops": record.get("affected_crops", []),
            "presence_scope": (record.get("distribution") or {}
                               ).get("presence_scope"),
            "evidence_quality": record.get("evidence_quality"),
        }
        return out


class PestKnowledgeEngine(_Catalog):
    engine = PEST_ENGINE
    id_key = "pest_id"
    catalog = PESTS

    def for_crop(self, crop_id: str) -> dict[str, Any]:
        return self.list(crop=crop_id)


class PlantDiseaseKnowledgeEngine(_Catalog):
    engine = DISEASE_ENGINE
    id_key = "disease_id"
    catalog = DISEASES

    def categories(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for record in DISEASES.values():
            out[record["category"]] = out.get(record["category"], 0) + 1
        return out


def _evaluate_rules(conditions: dict[str, float | None],
                    rules: Iterable[dict[str, Any]],
                    source: str) -> dict[str, Any]:
    """Idoneidad = proporción ponderada de ventanas cumplidas."""
    components: dict[str, float | None] = {}
    weights: dict[str, float] = {}
    detail = []
    for rule in rules:
        variable = rule.get("variable")
        if not variable:
            raise G.MonitoringError("regla sin `variable`")
        low, high = rule.get("min"), rule.get("max")
        if not (G.is_number(low) and G.is_number(high)) or float(low) > float(high):
            raise G.MonitoringError(f"ventana inválida para {variable}")
        if not rule.get("source"):
            raise G.MonitoringError(f"ventana de {variable} sin fuente")
        value = conditions.get(variable)
        weight = float(rule.get("weight", 1.0))
        weights[variable] = weight
        if value is None or not G.is_number(value):
            components[variable] = None
            detail.append({"variable": variable, "value": None,
                           "window": [float(low), float(high)],
                           "inside": None, "weight": weight})
            continue
        inside = 1.0 if float(low) <= float(value) <= float(high) else 0.0
        components[variable] = inside
        detail.append({"variable": variable, "value": float(value),
                       "window": [float(low), float(high)],
                       "inside": bool(inside), "weight": weight})
    score = G.weighted_score(components, weights)
    return {"suitability": score["value"], "components": components,
            "detail": detail, "weight_used": score["weight_used"],
            "missing": score["missing"], "rules_source": source,
            "method": "proporción ponderada de ventanas ambientales cumplidas",
            "note": ("idoneidad ambiental no es probabilidad de presencia ni "
                     "diagnóstico")}


class PestRiskEngine:
    engine = PEST_RISK_ENGINE
    version = ENGINE_VERSION

    def __init__(self, catalog: PestKnowledgeEngine | None = None) -> None:
        self.catalog = catalog or PestKnowledgeEngine()

    def assess(self, pest_id: str, *,
               conditions: dict[str, float | None] | None = None,
               crop_id: str | None = None,
               stage: str | None = None,
               rules: list[dict[str, Any]] | None = None,
               rules_source: str | None = None) -> dict[str, Any]:
        record = self.catalog.get(pest_id)
        conditions = conditions or {}
        rules = rules if rules is not None else record.get("environmental_windows") or []
        suitability = None
        gap = None
        detail: dict[str, Any] | None = None
        if rules:
            source = _require_rule_source(
                rules_source or (rules[0].get("source") if rules else None))
            detail = _evaluate_rules(conditions, rules, source)
            suitability = detail["suitability"]
        else:
            gap = ("sin ventana ambiental cuantitativa con fuente: idoneidad "
                   "no evaluada")
        present = record["distribution"]["presence_scope"]
        exposure = None
        if crop_id is not None:
            exposure = 1.0 if crop_id.lower() in record["affected_crops"] else 0.0
        stage_factor = 1.0
        if stage:
            from .crop_health import STAGE_SENSITIVITY

            stage_factor = STAGE_SENSITIVITY.get(stage, 1.0)
        risk = None
        if suitability is not None and exposure is not None:
            risk = round(float(suitability) * float(exposure) * stage_factor, 6)
        return {
            "engine": self.engine, "engine_version": self.version,
            "evidence_class": "model_estimate",
            "pest_id": pest_id,
            "scientific_name": record["scientific_name"],
            "presence_evidence": {
                "scope": present,
                "confirmed_national": present == "national_confirmed",
                "evidence_quality": record["evidence_quality"],
                "note": ("la presencia documentada no prueba presencia actual "
                         "en el municipio o parcela consultados"),
            },
            "crop_exposure": {
                "crop_id": crop_id, "documented_host": exposure,
                "note": (None if exposure is None else
                         "cultivo en la lista de hospederos documentados"
                         if exposure else
                         "cultivo no documentado como hospedero en el registro"),
            },
            "environmental_suitability": suitability,
            "suitability_detail": detail,
            "stage_factor": stage_factor if stage else None,
            "potential_damage": record["economic_importance"],
            "risk_index": risk,
            "gap": gap,
            "method": "producto declarado de idoneidad × exposición × etapa",
            "assumptions": ["las ventanas provienen de literatura y no están "
                            "calibradas para El Salvador"],
            "limitations": [
                "idoneidad ambiental ≠ presencia de la plaga",
                "el índice no es una probabilidad ni una pérdida esperada",
                "no sustituye muestreo de campo",
            ],
            "uncertainty": {"level": record["uncertainty"]},
            "note": "una plaga documentada en el país no está necesariamente "
                    "en el cultivo consultado",
        }


class DiseaseRiskEngine:
    engine = DISEASE_RISK_ENGINE
    version = ENGINE_VERSION

    def __init__(self, catalog: PlantDiseaseKnowledgeEngine | None = None) -> None:
        self.catalog = catalog or PlantDiseaseKnowledgeEngine()

    def assess(self, disease_id: str, *,
               conditions: dict[str, float | None] | None = None,
               crop_id: str | None = None,
               stage: str | None = None,
               rules: list[dict[str, Any]] | None = None,
               rules_source: str | None = None) -> dict[str, Any]:
        record = self.catalog.get(disease_id)
        conditions = conditions or {}
        rules = rules if rules is not None else record.get("environmental_windows") or []
        suitability = None
        gap = None
        detail = None
        if rules:
            source = _require_rule_source(
                rules_source or (rules[0].get("source") if rules else None))
            detail = _evaluate_rules(conditions, rules, source)
            suitability = detail["suitability"]
        else:
            gap = ("sin ventana ambiental cuantitativa con fuente: condiciones "
                   "favorables no evaluadas")
        exposure = None
        if crop_id is not None:
            exposure = 1.0 if crop_id.lower() in record["affected_crops"] else 0.0
        risk = None
        if suitability is not None and exposure is not None:
            factor = 1.0
            if stage:
                from .crop_health import STAGE_SENSITIVITY
                factor = STAGE_SENSITIVITY.get(stage, 1.0)
            risk = round(float(suitability) * float(exposure) * factor, 6)
        return {
            "engine": self.engine, "engine_version": self.version,
            "evidence_class": "model_estimate",
            "disease_id": disease_id, "name": record["name"],
            "causal_organism": record["causal_organism"],
            "category": record["category"],
            "presence_evidence": record["distribution"],
            "environmental_suitability": suitability,
            "suitability_detail": detail,
            "crop_exposure": exposure,
            "favorable_conditions": record["favorable_conditions"],
            "risk_index": risk,
            "diagnosis": None,
            "gap": gap,
            "infection_model": {
                "implemented": False,
                "reason": ("no hay modelo epidemiológico validado para el "
                           "patosistema salvadoreño en este repositorio"),
            },
            "method": "idoneidad ambiental declarada × exposición del cultivo",
            "limitations": [
                "condiciones favorables no son infección",
                "el motor no emite diagnóstico",
                "los síntomas requieren confirmación fitopatológica",
            ],
            "note": "un riesgo calculado no es un caso confirmado",
        }


class AgriculturalPhytosanitaryEngine:
    """Registro de evidencia fitosanitaria con procedencia explícita."""

    engine = PHYTO_ENGINE
    version = ENGINE_VERSION

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def add(self, *, kind: str, statement: str, crop_id: str | None,
            geographic_scope: str, source: str, observed_on: str,
            official: bool = False,
            confidence: float | None = None) -> dict[str, Any]:
        if kind not in PHYTO_KINDS:
            raise G.MonitoringError(f"tipo no admitido: {kind}; use {list(PHYTO_KINDS)}")
        if official and kind != "official_notice":
            raise G.MonitoringError(
                "solo un `official_notice` puede marcarse como oficial")
        if not source or len(source.strip()) < 3:
            raise G.MonitoringError("todo registro exige fuente")
        try:
            date.fromisoformat(observed_on[:10])
        except ValueError:
            raise G.MonitoringError("observed_on debe ser YYYY-MM-DD") from None
        if confidence is not None:
            confidence = G.clamp01(confidence)
        fingerprint = hashlib.sha256(
            f"{kind}|{statement}|{crop_id}|{geographic_scope}|{source}|"
            f"{observed_on}".encode("utf-8")).hexdigest()[:16]
        record = {
            "record_id": f"PHY-{fingerprint}",
            "kind": kind,
            "official": bool(official and kind == "official_notice"),
            "statement": statement,
            "crop_id": crop_id,
            "geographic_scope": geographic_scope,
            "source": source,
            "observed_on": observed_on,
            "confidence": confidence,
            "evidence_class": kind,
            "registered_at": G.utcnow(),
            "note": ("un reporte comunitario o una estimación algorítmica no "
                     "es un comunicado oficial"),
        }
        self._records[record["record_id"]] = record
        return dict(record)

    def list(self, *, kind: str | None = None,
             crop_id: str | None = None) -> dict[str, Any]:
        items = [dict(r) for r in self._records.values()
                 if (kind is None or r["kind"] == kind)
                 and (crop_id is None or r["crop_id"] == crop_id.lower())]
        items.sort(key=lambda r: r["observed_on"], reverse=True)
        return {"count": len(items), "records": items,
                "official_count": sum(1 for r in items if r["official"])}

    def summary(self) -> dict[str, Any]:
        by_kind = {k: 0 for k in PHYTO_KINDS}
        for record in self._records.values():
            by_kind[record["kind"]] += 1
        return {"total": len(self._records), "by_kind": by_kind,
                "official": sum(1 for r in self._records.values() if r["official"]),
                "note": "la evidencia se clasifica por procedencia; no se agrega"}

    def threat_catalog(self, crop_id: str) -> dict[str, Any]:
        pests = PestKnowledgeEngine().for_crop(crop_id)
        diseases = PlantDiseaseKnowledgeEngine().for_crop(crop_id)
        return {
            "crop_id": crop_id,
            "pests": pests["items"], "diseases": diseases["items"],
            "registered_reports": self.list(crop_id=crop_id)["count"],
            "note": ("catálogo de amenazas documentadas; la presencia en el "
                     "cultivo no está verificada por este listado"),
        }
