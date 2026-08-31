"""Config Groups — the configuration model of the UX 2.0 era.

If you come from feature templates + device templates, the mental map is:

    feature template   →  parcel (inside a feature profile)
    device template    →  config group
    attach             →  associate + deploy
    variable CSV       →  device variables

The difference that matters for automation: a config group is **hierarchical
and declarative**. You describe the group, associate devices, fill in
variables and ask for a deployment. The Manager computes the diff and pushes.

⚠️ Version: config groups require Manager 20.12+ / IOS-XE 17.12+. The exact
shape of some payloads changed between releases — if a POST comes back 400,
open the browser Developer Tools, perform the same action by clicking in the
GUI, and compare the request body. That is the technique, not a workaround.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .client import SDWANClient
from .tasks import TaskResult, wait_for_task


@dataclass
class ConfigGroup:
    id: str
    name: str
    description: str = ""
    solution: str = "sdwan"
    raw: dict[str, Any] | None = None

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "ConfigGroup":
        return cls(
            id=payload.get("id") or payload.get("configGroupId") or "",
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            solution=payload.get("solution", "sdwan"),
            raw=payload,
        )


def list_config_groups(client: SDWANClient) -> list[ConfigGroup]:
    payload = client.get("/v1/config-group") or []
    if isinstance(payload, dict):
        payload = payload.get("configGroups", [])
    return [ConfigGroup.from_api(item) for item in payload]


def find_config_group(client: SDWANClient, name: str) -> ConfigGroup | None:
    return next((g for g in list_config_groups(client) if g.name == name), None)


def get_associated_devices(client: SDWANClient, group_id: str) -> list[dict[str, Any]]:
    """Devices already associated with the group."""
    payload = client.get(f"/v1/config-group/{group_id}/device/associate") or []
    if isinstance(payload, dict):
        payload = payload.get("devices", [])
    return payload


def associate_devices(
    client: SDWANClient, group_id: str, device_uuids: list[str]
) -> None:
    """Associate devices with the group.

    Idempotency: the API doesn't complain about re-associating, but we filter
    out what is already there. On some releases, re-sending the whole list
    *replaces* the association — and un-associating a device by accident is
    exactly the kind of mishap automation is supposed to prevent.
    """
    already = {d.get("id") for d in get_associated_devices(client, group_id)}
    new = [uuid for uuid in device_uuids if uuid not in already]
    if not new:
        return
    client.post(
        f"/v1/config-group/{group_id}/device/associate",
        {"devices": [{"id": uuid} for uuid in new]},
    )


def get_device_variables(client: SDWANClient, group_id: str) -> dict[str, Any]:
    """Per-device variables — the equivalent of the device template CSV."""
    return client.get(f"/v1/config-group/{group_id}/device/variables") or {}


def set_device_variables(
    client: SDWANClient, group_id: str, payload: dict[str, Any]
) -> None:
    """Write the variables. GET, modify, PUT — never build from scratch.

    The payload carries internal fields the Manager expects back untouched.
    Rebuilding it by hand is like doing `write erase` to change a hostname.
    """
    client.put(f"/v1/config-group/{group_id}/device/variables", payload)


def preview_device_config(client: SDWANClient, group_id: str, device_uuid: str) -> str:
    """The CLI that *would* be applied, without applying it. A poor man's plan.

    Use this before every deployment. It's free, it's safe, and it's the only
    way to answer "what exactly is going to change?" before finding out the
    hard way.

    ⚠️ This is a POST, not a GET — a GET here answers 405. The Manager treats
    the preview as a computation it runs for you, not a resource it holds. The
    CLI comes back under `newConfig` (verified on 20.15).
    """
    result = client.post(f"/v1/config-group/{group_id}/device/{device_uuid}/preview", {})
    if isinstance(result, dict):
        return result.get("newConfig") or result.get("config") or str(result)
    return str(result)


def deploy(
    client: SDWANClient,
    group_id: str,
    device_uuids: list[str],
    *,
    wait: bool = True,
    timeout: int = 900,
    raise_on_failure: bool = True,
) -> TaskResult | str:
    """Trigger the deployment and (by default) wait for it to finish.

    Returns the `TaskResult` when `wait=True`, or the task id when False.
    """
    response = client.post(
        f"/v1/config-group/{group_id}/device/deploy",
        {"devices": [{"id": uuid} for uuid in device_uuids]},
    )

    task_id = None
    if isinstance(response, dict):
        task_id = response.get("parentTaskId") or response.get("id")
    if not task_id:
        raise RuntimeError(f"Deployment returned no task id. Response: {response!r}")

    if not wait:
        return task_id
    return wait_for_task(
        client, task_id, timeout=timeout, raise_on_failure=raise_on_failure
    )
