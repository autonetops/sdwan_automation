"""The Manager's asynchronous task model.

This is *the* automation lesson of module 3. Writing to the Manager is almost
never synchronous: you POST, you receive an `id`, and the change happens
later. If your script doesn't wait, it lies — it reports success before the
fabric has changed (or before it has failed).

Waiting properly means four things: an interval between polls, a timeout,
telling "finished successfully" apart from "finished in error", and returning
enough context for someone to debug at 3am.
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
    """The task did not finish within the deadline."""


class TaskFailed(SDWANError):
    """The task finished, but in error."""


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
        head = f"Task {self.task_id}: {self.status} in {self.elapsed_seconds:.1f}s"
        if not self.failed_devices:
            return head
        details = "\n".join(
            f"  ✗ {d.get('host-name', d.get('deviceID', '?'))}: "
            f"{d.get('currentActivity') or d.get('activity') or d.get('statusType', '')}"
            for d in self.failed_devices
        )
        return f"{head}\n{details}"


def get_task_status(client: SDWANClient, task_id: str) -> dict[str, Any]:
    """Raw state of a task.

    Mind the shape: this endpoint returns `{"summary": {...}, "data": [...]}`.
    The client's default unwrapping would hand back only `data` and throw away
    `summary` — which is exactly where the task state lives. So here, and only
    here, we ask for `unwrap=False`.
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
    """Poll until the task finishes.

    Args:
        timeout: ceiling in seconds. A multi-site config group deployment
            easily passes 5 minutes; don't set 30.
        interval: spacing between polls. Below ~3s you only add load to the
            Manager without gaining information.
        raise_on_failure: when False, return the TaskResult with
            `succeeded=False` instead of raising. The pipeline passes False so
            it can roll back.

    Raises:
        TaskTimeout: the deadline passed.
        TaskFailed: the task finished in error (unless raise_on_failure=False).
    """
    started = time.monotonic()
    last_status = "unknown"

    while True:
        elapsed = time.monotonic() - started
        payload = get_task_status(client, task_id)
        summary = payload.get("summary") or {}
        devices = payload.get("data") or []

        # The reliable status is in summary; the per-device rows feed the report.
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
                f"Task {task_id} still '{last_status}' after {timeout}s. "
                "It may still be running on the Manager — check the GUI before retrying."
            )

        logger.info("Task %s: %s (%.0fs)", task_id, last_status or "in_progress", elapsed)
        time.sleep(interval)
