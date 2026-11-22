"""Orquestador de procesamiento por lotes.

Diseño deliberado (SYSTEM_ARCHITECTURE.md §12.4): un proceso por lotes, sin
cola distribuida, sin daemon. Hace lo que un DAG pequeño necesita:

  * dependencias explícitas y detección de ciclos;
  * reintentos con número declarado y backoff opcional;
  * estado persistido en JSON para reanudar sin repetir trabajo ya hecho;
  * traza de error completa por tarea, no solo el mensaje;
  * ejecución secuencial por defecto: el límite real de esta máquina es la
    memoria, y paralelizar dos tareas de 300 MB la agota antes de acelerar nada.

Lo que no hace: distribuir, programar en el tiempo ni gestionar workers. Si un
día hace falta, el mismo grafo se ejecuta bajo Prefect sin reescribir tareas.
"""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

Status = str  # "pending" | "running" | "ok" | "failed" | "skipped"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Task:
    """Una unidad de trabajo con nombre estable (el nombre es la clave de estado)."""

    name: str
    fn: Callable[[], Any]
    depends_on: tuple[str, ...] = ()
    retries: int = 0
    description: str = ""


@dataclass
class PlanResult:
    run_id: str
    states: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(s["status"] == "ok" for s in self.states.values())

    @property
    def failed(self) -> list[str]:
        return [n for n, s in self.states.items() if s["status"] == "failed"]

    def as_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "ok": self.ok, "failed": self.failed,
                "tasks": self.states}


def topological_order(tasks: list[Task]) -> list[Task]:
    """Ordena por dependencias; lanza ValueError si hay nombre duplicado o ciclo."""
    by_name: dict[str, Task] = {}
    for task in tasks:
        if task.name in by_name:
            raise ValueError(f"tarea duplicada: {task.name}")
        by_name[task.name] = task

    for task in tasks:
        for dep in task.depends_on:
            if dep not in by_name:
                raise ValueError(f"{task.name} depende de '{dep}', que no existe")

    order: list[Task] = []
    state: dict[str, int] = {}  # 1 = visitando, 2 = hecho

    def visit(name: str, trail: tuple[str, ...]) -> None:
        if state.get(name) == 2:
            return
        if state.get(name) == 1:
            cycle = " -> ".join(trail + (name,))
            raise ValueError(f"ciclo de dependencias: {cycle}")
        state[name] = 1
        for dep in by_name[name].depends_on:
            visit(dep, trail + (name,))
        state[name] = 2
        order.append(by_name[name])

    for task in tasks:
        visit(task.name, ())
    return order


def run_plan(
    tasks: list[Task],
    *,
    state_path: Path | None = None,
    resume: bool = False,
    retry_delay_s: float = 0.0,
    run_id: str | None = None,
) -> PlanResult:
    """Ejecuta el grafo. Con `resume`, omite tareas ya completadas con éxito."""
    ordered = topological_order(tasks)
    run_id = run_id or _utcnow().replace(":", "").replace("-", "")

    previous: dict[str, Any] = {}
    if resume and state_path and state_path.exists():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8")).get("tasks", {})
        except (OSError, json.JSONDecodeError):
            previous = {}

    result = PlanResult(run_id=run_id)

    def persist() -> None:
        if not state_path:
            return
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(
            {"run_id": run_id, "updated_at": _utcnow(), "tasks": result.states},
            indent=2, ensure_ascii=False), encoding="utf-8")

    for task in ordered:
        prior = previous.get(task.name, {})
        if resume and prior.get("status") == "ok":
            result.states[task.name] = {**prior, "status": "ok",
                                        "resumed": True}
            persist()
            continue

        blocked = [d for d in task.depends_on
                   if result.states.get(d, {}).get("status") != "ok"]
        if blocked:
            result.states[task.name] = {
                "status": "skipped", "blocked_by": blocked,
                "detail": "dependencia no completada",
            }
            persist()
            continue

        attempts = 0
        started = time.perf_counter()
        while True:
            attempts += 1
            result.states[task.name] = {"status": "running", "attempts": attempts}
            try:
                output = task.fn()
                result.states[task.name] = {
                    "status": "ok",
                    "attempts": attempts,
                    "duration_s": round(time.perf_counter() - started, 3),
                    "output": output if _jsonable(output) else str(output),
                }
                break
            except Exception as exc:  # noqa: BLE001 — se registra y se decide
                error = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(limit=8),
                }
                if attempts > task.retries:
                    result.states[task.name] = {
                        "status": "failed", "attempts": attempts, "error": error,
                        "duration_s": round(time.perf_counter() - started, 3),
                    }
                    break
                result.states[task.name] = {
                    "status": "retrying", "attempts": attempts, "error": error,
                }
                if retry_delay_s:
                    time.sleep(retry_delay_s)
        persist()

    return result


def _jsonable(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False
