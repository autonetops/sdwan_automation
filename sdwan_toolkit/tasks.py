"""O modelo de tarefa assíncrona do Manager.

Esta é *a* lição de automação do módulo 3. Escrever no Manager quase nunca é
síncrono: você faz o POST, recebe um `id`, e a mudança acontece depois. Se o
seu script não espera, ele mente — reporta sucesso antes de o fabric ter
mudado (ou antes de ter falhado).

Esperar direito significa quatro coisas: intervalo entre consultas, timeout,
distinguir "terminou com sucesso" de "terminou com erro", e devolver contexto
suficiente para alguém debugar às 3 da manhã.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .client import SDWANClient, SDWANError

logger = logging.getLogger(__name__)

SUCCESS_STATES = {"success", "done"}
FAILURE_STATES = {"failure", "failed", "error", "tear_down"}


class TaskTimeout(SDWANError):
    """A tarefa não terminou dentro do prazo."""


class TaskFailed(SDWANError):
    """A tarefa terminou, mas em erro."""


@dataclass
class TaskResult:
    task_id: str
    status: str
    succeeded: bool
    elapsed_seconds: float
    devices: list[dict[str, Any]] = field(default_factory=list)

    @property
    def failed_devices(self) -> list[dict[str, Any]]:
        return [
            d for d in self.devices
            if str(d.get("status", "")).lower() in FAILURE_STATES
        ]

    def summary(self) -> str:
        head = f"Tarefa {self.task_id}: {self.status} em {self.elapsed_seconds:.1f}s"
        if not self.failed_devices:
            return head
        detalhes = "\n".join(
            f"  ✗ {d.get('host-name', d.get('deviceID', '?'))}: "
            f"{d.get('currentActivity') or d.get('activity') or d.get('statusType', '')}"
            for d in self.failed_devices
        )
        return f"{head}\n{detalhes}"


def get_task_status(client: SDWANClient, task_id: str) -> dict[str, Any]:
    """Estado bruto de uma tarefa.

    Atenção ao formato: este endpoint devolve `{"summary": {...}, "data": [...]}`.
    O desembrulho padrão do cliente devolveria só o `data` e jogaria fora o
    `summary` — que é exatamente onde mora o estado da tarefa. Por isso aqui,
    e só aqui, pedimos `unwrap=False`.
    """
    raw = client.request("GET", f"/device/action/status/{task_id}", unwrap=False)
    if isinstance(raw, dict):
        return {"summary": raw.get("summary") or {}, "data": raw.get("data") or []}
    if isinstance(raw, list):
        return {"summary": {}, "data": raw}
    return {"summary": {}, "data": []}


def wait_for_task(
    client: SDWANClient,
    task_id: str,
    *,
    timeout: int = 600,
    interval: int = 5,
    raise_on_failure: bool = True,
) -> TaskResult:
    """Faz polling até a tarefa terminar.

    Args:
        timeout: teto em segundos. Deploy de config group em vários sites
            passa fácil de 5 minutos; não coloque 30.
        interval: espaçamento entre consultas. Abaixo de ~3s você só gera
            carga no Manager sem ganhar informação.
        raise_on_failure: se False, devolve o TaskResult com `succeeded=False`
            em vez de levantar. O pipeline usa False para poder fazer rollback.

    Raises:
        TaskTimeout: estourou o prazo.
        TaskFailed: terminou em erro (a menos que raise_on_failure=False).
    """
    started = time.monotonic()
    last_status = "unknown"

    while True:
        elapsed = time.monotonic() - started
        payload = get_task_status(client, task_id)
        summary = payload.get("summary") or {}
        devices = payload.get("data") or []

        # O status confiável está no summary; o por-device serve para o relatório.
        last_status = str(summary.get("status", "")).lower()
        if not last_status and devices:
            statuses = {str(d.get("status", "")).lower() for d in devices}
            if statuses <= SUCCESS_STATES:
                last_status = "success"
            elif statuses & FAILURE_STATES:
                last_status = "failure"
            else:
                last_status = "in_progress"

        if last_status in SUCCESS_STATES or last_status in FAILURE_STATES:
            result = TaskResult(
                task_id=task_id,
                status=last_status,
                succeeded=last_status in SUCCESS_STATES,
                elapsed_seconds=elapsed,
                devices=devices,
            )
            if not result.succeeded and raise_on_failure:
                raise TaskFailed(result.summary())
            return result

        if elapsed > timeout:
            raise TaskTimeout(
                f"Tarefa {task_id} ainda em '{last_status}' após {timeout}s. "
                "Ela pode continuar rodando no Manager — confira na GUI antes de repetir."
            )

        logger.info("Tarefa %s: %s (%.0fs)", task_id, last_status or "in_progress", elapsed)
        time.sleep(interval)
