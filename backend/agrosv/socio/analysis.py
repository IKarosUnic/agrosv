"""AGROSV — SocioAgriculturalAnalysisEngine (§7.4).

Analiza resultados de simulación y declara que **no** son hallazgos empíricos.
Cada conclusión lleva `evidence_class: simulation` y
`empirical_conclusion: false`; la validación socioeconómica está en
`SOCIO_AGRICULTURAL_VALIDATION.md` y no se infiere de aquí.
"""
from __future__ import annotations

from typing import Any

from ..social import governance as SG

ENGINE = "socio_agricultural_analysis"
ENGINE_VERSION = SG.ENGINE_VERSION

RESEARCH_QUESTIONS = (
    ("R1", "¿Qué restricciones de recursos afectan más una estrategia productiva?"),
    ("R2", "¿Qué perfiles tienen acceso limitado a riego?"),
    ("R3", "¿Cómo responden distintos sistemas productivos a una sequía?"),
    ("R4", "¿Qué barreras condicionan la adopción tecnológica?"),
    ("R5", "¿Cómo influyen los choques de mercado en las decisiones simuladas?"),
    ("R6", "¿Qué intervenciones de apoyo podrían explorarse?"),
)

METRICS = ("decision_distribution", "adoption", "mean_impact_index",
           "economic", "decisions_count")


class AnalysisError(ValueError):
    pass


def _metrics(run: dict[str, Any]) -> dict[str, Any]:
    result = run.get("result", run)
    return result.get("metrics", {})


class SocioAgriculturalAnalysisEngine:
    engine = ENGINE
    version = ENGINE_VERSION

    def research_questions(self) -> dict[str, Any]:
        return {
            "questions": [{"id": i, "question": q,
                           "evidence_available": "simulation_only"}
                          for i, q in RESEARCH_QUESTIONS],
            "note": ("las preguntas se responden con simulación; no hay "
                     "validación empírica en Fase 6"),
        }

    def compare(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        if not runs:
            raise AnalysisError("se requiere al menos una corrida")
        rows = []
        for run in runs:
            scenario = run.get("scenario_id") or \
                run.get("result", {}).get("scenario_id")
            metrics = _metrics(run)
            adoption = metrics.get("adoption") or {}
            rows.append({
                "scenario_id": scenario,
                "n_agents": metrics.get("n_agents"),
                "decisions_count": metrics.get("decisions_count"),
                "fraction_considering_adoption":
                    adoption.get("fraction_considering"),
                "mean_impact_index": metrics.get("mean_impact_index"),
                "decision_distribution": metrics.get("decision_distribution"),
                "economic": metrics.get("economic"),
            })
        baseline = rows[0]
        for row in rows[1:]:
            if row["fraction_considering_adoption"] is not None and \
                    baseline["fraction_considering_adoption"] is not None:
                row["delta_adoption_vs_baseline"] = round(
                    row["fraction_considering_adoption"]
                    - baseline["fraction_considering_adoption"], 3)
            if row["mean_impact_index"] is not None and \
                    baseline["mean_impact_index"] is not None:
                row["delta_impact_vs_baseline"] = round(
                    row["mean_impact_index"] - baseline["mean_impact_index"], 3)
        return SG.synthetic_envelope(
            ENGINE,
            result={"baseline": baseline["scenario_id"], "rows": rows},
            assumptions=["las corridas comparadas usan la misma semilla y "
                         "ubicación salvo que se indique lo contrario"],
            limitations=["comparar escenarios no valida ninguno de ellos",
                         "las diferencias son sensibles a supuestos y semilla"],
            sources=["agrosv_scenario"],
            scenario_id=None,
            query={"n_runs": len(runs)})

    def constraints(self, population: dict[str, Any]) -> dict[str, Any]:
        result = population.get("result", population)
        agents = result.get("agents", [])
        if not agents:
            raise AnalysisError("la población no contiene agentes")
        payloads = [a["state"]["payload"] for a in agents]
        n = len(payloads)

        def frac(pred) -> float:
            return round(sum(1 for p in payloads if pred(p)) / n, 3)

        return SG.synthetic_envelope(
            ENGINE,
            result={
                "n": n,
                "no_irrigation": frac(lambda p: not p.get("irrigated")),
                "credit_below_0_3": frac(lambda p: float(
                    p.get("credit_access", 0)) < 0.3),
                "capital_below_1000": frac(lambda p: float(
                    p.get("capital_usd", 0)) < 1000),
                "market_below_0_4": frac(lambda p: float(
                    p.get("market_access", 0)) < 0.4),
                "single_crop": frac(lambda p: len(p.get("crops", [])) <= 1),
                "low_digital_literacy": frac(lambda p: float(
                    p.get("digital_literacy", 0)) < 0.3),
            },
            assumptions=["los umbrales son cortes de análisis, no normas"],
            limitations=["no son prevalencias poblacionales: describen la "
                         "muestra sintética generada"],
            sources=["agrosv_scenario"],
            query={"n": n})

    def findings(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        comparison = self.compare(runs)["result"]
        rows = comparison["rows"]
        findings = []
        if len(rows) >= 2:
            findings.append({
                "id": "F1",
                "evidence_class": "simulation",
                "empirical_conclusion": False,
                "statement": (
                    "En la simulación, la fracción que consideraría adoptar la "
                    "práctica cambia entre escenarios; el signo y la magnitud "
                    "dependen de los supuestos, no de una tasa observada."),
                "support": [{"scenario_id": r["scenario_id"],
                             "fraction": r["fraction_considering_adoption"]}
                            for r in rows],
            })
            with_impact = [r for r in rows if r["mean_impact_index"] is not None]
            if with_impact:
                findings.append({
                    "id": "F2",
                    "evidence_class": "simulation",
                    "empirical_conclusion": False,
                    "statement": (
                        "El índice de impacto simulado varía entre escenarios; "
                        "no se interpreta como pérdida esperada."),
                    "support": [{"scenario_id": r["scenario_id"],
                                 "mean_impact": r["mean_impact_index"]}
                                for r in with_impact],
                })
        return {
            "findings": findings,
            "comparison": comparison,
            "validation_status": "no validado empíricamente",
            "warning": ("un hallazgo de simulación no es una conclusión sobre "
                        "El Salvador ni sobre personas reales"),
        }


__all__ = ["SocioAgriculturalAnalysisEngine", "AnalysisError",
           "RESEARCH_QUESTIONS", "METRICS"]
