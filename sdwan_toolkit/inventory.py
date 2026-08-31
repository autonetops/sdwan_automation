"""Fabric inventory.

Modelling lesson: the Manager has *two* views of inventory and they are not
interchangeable.

- `/dataservice/device` is **real-time**: the Manager answers about who is
  connected to the control plane right now. It has `reachability`; it does not
  have devices that are registered but never came up.
- `/dataservice/system/device/{vedges,controllers}` is the **configuration
  database**: everything registered, including what is offline. It has
  `validity` (certificate state) but no operational state.

Mature automation knows which of the two it is asking.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

from .client import SDWANClient

CONTROLLER_PERSONALITIES = {"vmanage", "vsmart", "vbond"}


@dataclass
class Device:
    """A fabric node, normalized.

    The API returns hyphenated keys (`host-name`, `system-ip`) and values that
    are inconsistent between endpoints. Normalizing at the edge — the moment
    data comes in — keeps `d.get("host-name") or d.get("hostName")` from
    spreading through the whole codebase.
    """

    system_ip: str
    hostname: str
    personality: str
    site_id: str | None = None
    reachability: str | None = None
    state: str | None = None
    uuid: str | None = None
    device_model: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_controller(self) -> bool:
        return self.personality in CONTROLLER_PERSONALITIES

    @property
    def is_edge(self) -> bool:
        return not self.is_controller

    @property
    def is_reachable(self) -> bool:
        return self.reachability == "reachable"

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "Device":
        return cls(
            system_ip=payload.get("system-ip") or payload.get("deviceId") or "",
            hostname=payload.get("host-name") or payload.get("hostName") or "",
            personality=(payload.get("personality") or payload.get("deviceType") or "").lower(),
            site_id=payload.get("site-id") or payload.get("siteId"),
            reachability=payload.get("reachability"),
            state=payload.get("state"),
            uuid=payload.get("uuid") or payload.get("chasisNumber"),
            device_model=payload.get("device-model") or payload.get("deviceModel"),
            raw=payload,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw", None)
        return data


def get_devices(client: SDWANClient) -> list[Device]:
    """Every device seen by the control plane (the real-time view)."""
    return [Device.from_api(d) for d in client.get("/device") or []]


def get_edges(client: SDWANClient) -> list[Device]:
    """WAN Edges only — these are what configuration automation acts on."""
    return [d for d in get_devices(client) if d.is_edge]


def get_controllers(client: SDWANClient) -> list[Device]:
    return [d for d in get_devices(client) if d.is_controller]


def find_by_hostname(devices: Iterable[Device], hostname: str) -> Device | None:
    target = hostname.lower()
    return next((d for d in devices if d.hostname.lower() == target), None)


def unreachable(devices: Iterable[Device]) -> list[Device]:
    """Shortcut for the most common pre-change check."""
    return [d for d in devices if not d.is_reachable]
