"""Operational state collection — the "before" and "after" of every change.

The central idea of this bootcamp: **a change is only safe if you can prove
the fabric came out the same or better.** Proving it requires a comparable
snapshot, as data — not a `show` command pasted into a chat window.

`FabricSnapshot` is that snapshot: BFD sessions, control connections, OMP
peers and app-route SLA, per device, with a timestamp.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import SDWANClient
from .inventory import Device, get_devices


# ── individual collectors ───────────────────────────────────────────
# All real-time: they query the device across the control plane.
# They are expensive. That is why the client has a rate limiter.

def get_control_connections(client: SDWANClient, system_ip: str) -> list[dict[str, Any]]:
    """Control connections (DTLS/TLS) from the device to the controllers."""
    return client.get("/device/control/connections", {"deviceId": system_ip}) or []


def get_bfd_sessions(client: SDWANClient, system_ip: str) -> list[dict[str, Any]]:
    """BFD sessions — the data tunnels between TLOCs. The fabric's vital sign."""
    return client.get("/device/bfd/sessions", {"deviceId": system_ip}) or []


def get_omp_peers(client: SDWANClient, system_ip: str) -> list[dict[str, Any]]:
    """OMP peers — the routing adjacency with the Controllers."""
    return client.get("/device/omp/peers", {"deviceId": system_ip}) or []


def get_approute_stats(client: SDWANClient, system_ip: str) -> list[dict[str, Any]]:
    """Latency/loss/jitter per tunnel, as app-route sees it."""
    return client.get("/device/app-route/statistics", {"deviceId": system_ip}) or []


# ── the snapshot ────────────────────────────────────────────────────

@dataclass
class DeviceState:
    """One device's operational state, reduced to what is worth comparing."""

    system_ip: str
    hostname: str
    reachable: bool
    control_connections_up: int = 0
    bfd_sessions_up: int = 0
    bfd_peers: list[str] = field(default_factory=list)
    omp_peers_up: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_ip": self.system_ip,
            "hostname": self.hostname,
            "reachable": self.reachable,
            "control_connections_up": self.control_connections_up,
            "bfd_sessions_up": self.bfd_sessions_up,
            "bfd_peers": sorted(self.bfd_peers),
            "omp_peers_up": self.omp_peers_up,
        }


@dataclass
class FabricSnapshot:
    """The fabric at one instant. Serializable, comparable, versionable."""

    taken_at: str
    devices: dict[str, DeviceState] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "taken_at": self.taken_at,
            "devices": {ip: st.to_dict() for ip, st in sorted(self.devices.items())},
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "FabricSnapshot":
        payload = json.loads(Path(path).read_text())
        return cls(
            taken_at=payload["taken_at"],
            devices={
                ip: DeviceState(
                    system_ip=d["system_ip"],
                    hostname=d["hostname"],
                    reachable=d["reachable"],
                    control_connections_up=d["control_connections_up"],
                    bfd_sessions_up=d["bfd_sessions_up"],
                    bfd_peers=d["bfd_peers"],
                    omp_peers_up=d["omp_peers_up"],
                )
                for ip, d in payload["devices"].items()
            },
        )


def _count_up(rows: list[dict[str, Any]], *keys: str) -> int:
    """Count rows whose state field says 'up'.

    The API is not consistent: sometimes the field is `state`, sometimes
    `status`, sometimes `operstate`. Rather than guessing, we check every
    candidate.
    """
    total = 0
    for row in rows:
        for key in keys:
            value = str(row.get(key, "")).lower()
            if value in {"up", "ok"}:
                total += 1
                break
    return total


def collect_device_state(client: SDWANClient, device: Device) -> DeviceState:
    """Collect one device's state. Does not raise if the device is down."""
    state = DeviceState(
        system_ip=device.system_ip,
        hostname=device.hostname,
        reachable=device.is_reachable,
    )
    if not device.is_reachable:
        # Querying an unreachable device only burns time and timeouts.
        return state

    control = get_control_connections(client, device.system_ip)
    state.control_connections_up = _count_up(control, "state", "status")

    if device.is_edge:
        bfd = get_bfd_sessions(client, device.system_ip)
        state.bfd_sessions_up = _count_up(bfd, "state", "status")
        state.bfd_peers = sorted(
            {r.get("system-ip", "") for r in bfd if str(r.get("state", "")).lower() == "up"} - {""}
        )

    omp = get_omp_peers(client, device.system_ip)
    state.omp_peers_up = _count_up(omp, "state", "status")

    return state


def take_snapshot(client: SDWANClient, devices: list[Device] | None = None) -> FabricSnapshot:
    """A full snapshot of the fabric. The pipeline calls this twice."""
    devices = devices if devices is not None else get_devices(client)
    snapshot = FabricSnapshot(taken_at=datetime.now(timezone.utc).isoformat())
    for device in devices:
        if not device.system_ip:
            continue
        snapshot.devices[device.system_ip] = collect_device_state(client, device)
    return snapshot
