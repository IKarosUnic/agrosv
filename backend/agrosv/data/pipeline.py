"""AGROSV — pipeline automatizado y monitoreo (Fase 4, §15).

Sin servicios de pago, sin daemon y sin scraping no autorizado. Tres funciones:
detectar lo que envejeció, detectar lo que cambió y dejar registro de lo que
falló. La ejecución por lotes reutiliza `agrosv.science.orchestrator`
(dependencias, reintentos, estado en disco): no hay un segundo motor.

Uso local:

    python -m agrosv.data.pipeline --monitor
    python -m agrosv.data.pipeline --monitor --out data/manifests/monitoring.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..science.orchestrator import Task, run_plan
from . import storage as S
from .catalog import Catalog, DatasetRecord, DatasetState
from .store import DataStore

#: Vigencia por dominio. Son **políticas de operación**, no propiedades del
#: dato: un DEM de 2011 sigue siendo válido aunque tenga 15 años, mientras que un
#: precio de hace 40 días ya no describe el mercado. Revisar cada fase.
FRESHNESS_DAYS: dict[str, int] = {
    "TERRITORY": 730,
    "SOILS": 1825,
    "HYDROLOGY": 365,
    "CLIMATE": 60,
    "AGRICULTURE": 400,
    "ECONOMY": 45,
    "PHYTOSANITARY": 30,
    "BIODIVERSITY": 365,
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt, slice_to in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(str(text)[:slice_to], fmt).replace(
                tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def freshness(record: DatasetRecord, *, now: datetime | None = None,
              max_age_days: int | None = None) -> dict[str, Any]:
    """Antigüedad del dato frente a la política del dominio."""
    now = now or datetime.now(timezone.utc)
    limit = max_age_days or FRESHNESS_DAYS.get(record.domain, 365)
    stamp = _parse_date(record.download_date) or _parse_date(record.publication_date)
    if stamp is None:
        return {"dataset_id": record.dataset_id, "status": "UNKNOWN",
                "max_age_days": limit,
                "detail": "sin fecha de descarga ni de publicación verificable"}
    age_days = (now - stamp).days
    status = "FRESH" if age_days <= limit else "STALE"
    return {
        "dataset_id": record.dataset_id,
        "status": status,
        "age_days": age_days,
        "max_age_days": limit,
        "dated_by": "download_date" if _parse_date(record.download_date)
        else "publication_date",
        "detail": (f"{age_days} días desde la fecha registrada; política "
                   f"{limit} días para {record.domain}"),
    }


def detect_coverage_change(previous: dict[str, Any], current: dict[str, Any],
                           *, threshold_pct: float = 5.0) -> dict[str, Any]:
    """Compara dos informes de cobertura y señala cambios numéricos."""
    changes = []
    for key, new_value in current.items():
        if not isinstance(new_value, (int, float)):
            continue
        old_value = previous.get(key)
        if not isinstance(old_value, (int, float)) or old_value == 0:
            continue
        delta = new_value - old_value
        pct = 100 * delta / old_value
        if abs(pct) >= threshold_pct:
            changes.append({"metric": key, "previous": old_value,
                            "current": new_value, "delta": delta,
                            "pct": round(pct, 3)})
    return {
        "changed": bool(changes),
        "changes": changes,
        "threshold_pct": threshold_pct,
        "note": ("un cambio de cobertura no es un error: se registra para revisar "
                 "si la fuente cambió de versión o de método"),
    }


def detect_new_version(previous_manifest: dict[str, Any] | None,
                       probe: dict[str, Any]) -> dict[str, Any]:
    """Detecta si una fuente publicó otro archivo (hash, ETag o tamaño)."""
    if not previous_manifest:
        return {"changed": True, "reason": "sin manifiesto previo: primera versión",
                "reasons": ["sin manifiesto previo"]}
    reasons = []
    if previous_manifest.get("sha256") and probe.get("sha256") \
            and previous_manifest["sha256"] != probe["sha256"]:
        reasons.append("hash distinto")
    if previous_manifest.get("etag") and probe.get("etag") \
            and previous_manifest["etag"] != probe["etag"]:
        reasons.append("ETag distinto")
    if (previous_manifest.get("bytes") and probe.get("bytes")
            and int(previous_manifest["bytes"]) != int(probe["bytes"])):
        reasons.append("tamaño distinto")
    return {
        "changed": bool(reasons),
        "reasons": reasons,
        "requires_revalidation": bool(reasons),
        "note": ("una versión nueva exige revalidar: el estado anterior del "
                 "catálogo no se hereda automáticamente"),
    }


#: Estados en los que el dato se supone vigente y debe refrescarse. Un dataset
#: RESTRICTED o UNAVAILABLE no envejece: nunca estuvo disponible.
ACTIVE_STATES: frozenset[DatasetState] = frozenset({
    DatasetState.DOWNLOADED, DatasetState.PARSED,
    DatasetState.VALIDATED, DatasetState.INTEGRATED,
})


def missing_artifacts(record: DatasetRecord) -> list[str]:
    from .catalog import _resolve

    return [p for p in record.artifacts if not _resolve(p).exists()]


def revalidation_queue(catalog: Catalog, *, now: datetime | None = None
                       ) -> list[dict[str, Any]]:
    """Datasets que necesitan revalidación: viejos, sin hash o con artefactos ausentes."""
    queue = []
    for record in catalog:
        problems = []
        if record.state in {DatasetState.VALIDATED, DatasetState.INTEGRATED}:
            fresh = freshness(record, now=now)
            if fresh["status"] in {"STALE", "UNKNOWN"}:
                problems.append(f"vigencia {fresh['status']}")
        missing = missing_artifacts(record)
        if missing:
            problems.append(f"{len(missing)} artefactos ausentes")
        if record.state in {DatasetState.VALIDATED, DatasetState.INTEGRATED} \
                and not record.transitions:
            problems.append("sin historial de evidencia")
        if problems:
            queue.append({"dataset_id": record.dataset_id,
                          "state": record.state.value,
                          "reasons": problems})
    return queue


def _read_errors(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def monitoring_report(*, catalog_path: Path | None = None,
                      layout: S.DataLayout | None = None,
                      previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Informe operativo: vigencia, artefactos, calidad y errores."""
    lay = layout or S.layout()
    path = Path(catalog_path) if catalog_path else lay.catalog_path
    if not path.exists():
        return {"ok": False, "generated_at": utcnow(),
                "error": f"catálogo no encontrado: {path}",
                "hint": "ejecute scripts/08_build_phase4_integration.py"}
    catalog = Catalog.load(path)
    store = DataStore(lay.store_path)

    fresh = [freshness(r) for r in catalog if r.state in ACTIVE_STATES]
    stale = [f for f in fresh if f["status"] in {"STALE", "UNKNOWN"}]
    inactive = sorted(r.dataset_id for r in catalog if r.state not in ACTIVE_STATES)
    missing = {r.dataset_id: missing_artifacts(r) for r in catalog
               if missing_artifacts(r)}
    reports = store.quality_reports(limit=500) if store.exists else []
    failing = [{"dataset_id": r["dataset_id"], "report_id": r["report_id"],
                "errors": r.get("errors", 0)}
               for r in reports if r["status"] == "FAIL"]

    counts = store.counts_by_dataset() if store.exists else {}
    payload = {
        "ok": not stale and not missing and not failing,
        "generated_at": utcnow(),
        "catalog": catalog.summary(),
        "audit": catalog.audit(),
        "store": store.summary(),
        "freshness": {"stale_or_unknown": stale,
                      "fresh": sum(1 for f in fresh if f["status"] == "FRESH"),
                      "not_evaluated": inactive,
                      "policy_days": FRESHNESS_DAYS,
                      "note": ("solo se evalúa vigencia en estados activos: un "
                               "dataset RESTRICTED o UNAVAILABLE no envejece")},
        "missing_artifacts": missing,
        "quality": {"reports": len(reports), "failing": failing,
                    "latest_by_dataset": {
                        r["dataset_id"]: {"status": r["status"],
                                         "report_id": r["report_id"]}
                        for r in reports}},
        "revalidation_queue": revalidation_queue(catalog),
        "errors": _read_errors(lay.manifests / "pipeline_errors.jsonl"),
        "observations_by_dataset": counts,
        "note": ("el monitoreo detecta envejecimiento y fallos operativos; no "
                 "certifica calidad científica"),
    }
    if previous:
        payload["coverage_change"] = detect_coverage_change(
            previous.get("observations_by_dataset", {}), counts)
        payload["state_change"] = detect_coverage_change(
            {k: v for k, v in previous.get("catalog", {}).get("by_state", {}).items()},
            catalog.summary()["by_state"], threshold_pct=1.0)
    return payload


def write_monitoring(payload: dict[str, Any], out: Path | str) -> Path:
    """Escribe el informe y conserva el anterior para comparar cobertura."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        try:
            previous = json.loads(out.read_text(encoding="utf-8"))
            out.with_suffix(".previous.json").write_text(
                json.dumps(previous, indent=2, ensure_ascii=False),
                encoding="utf-8")
        except json.JSONDecodeError:
            pass
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    return out


def monitoring_plan(catalog_path: Path | None = None,
                    layout: S.DataLayout | None = None) -> dict[str, Any]:
    """Ejecuta el monitoreo como plan del orquestador (reutiliza Fase 2)."""
    lay = layout or S.layout()
    path = Path(catalog_path) if catalog_path else lay.catalog_path
    out = lay.manifests / "monitoring.json"
    captured: dict[str, Any] = {}

    def load_catalog() -> dict[str, Any]:
        captured["catalog"] = Catalog.load(path).summary()
        return captured["catalog"]

    def audit() -> dict[str, Any]:
        captured["audit"] = Catalog.load(path).audit()
        return captured["audit"]

    def report() -> dict[str, Any]:
        previous_path = out.with_suffix(".previous.json")
        previous = None
        if previous_path.exists():
            try:
                previous = json.loads(previous_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                previous = None
        payload = monitoring_report(catalog_path=path, layout=lay,
                                    previous=previous)
        write_monitoring(payload, out)
        return {"path": str(out), "ok": payload["ok"],
                "stale": len(payload["freshness"]["stale_or_unknown"])}

    tasks = [
        Task(name="catalog_load", fn=load_catalog,
             description="cargar el catálogo nacional"),
        Task(name="catalog_audit", fn=audit, depends_on=("catalog_load",),
             description="auditar coherencia del catálogo"),
        Task(name="monitoring_report", fn=report,
             depends_on=("catalog_audit",),
             description="vigencia, calidad, errores y cobertura"),
    ]
    result = run_plan(tasks, state_path=lay.manifests / "monitoring_state.json",
                      resume=False)
    return {"plan": result.as_dict(), "output": str(out),
            "ok": result.ok, "catalog": captured.get("catalog")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AGROSV — monitoreo del pipeline de datos")
    parser.add_argument("--monitor", action="store_true",
                        help="ejecutar el plan de monitoreo")
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.monitor:
        parser.print_help()
        return 0
    lay = S.layout()
    if args.out:
        payload = monitoring_report(catalog_path=args.catalog, layout=lay)
        path = write_monitoring(payload, args.out)
        print(json.dumps({"written": str(path), "ok": payload["ok"]},
                         ensure_ascii=False))
        return 0 if payload["ok"] else 1
    result = monitoring_plan(catalog_path=args.catalog, layout=lay)
    print(json.dumps({"ok": result["ok"], "output": result["output"],
                      "failed": result["plan"]["failed"]}, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
