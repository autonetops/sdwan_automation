"""Coleta de estado operacional — o "antes" e o "depois" de toda mudança.

A ideia central do bootcamp: **uma mudança só é segura se você consegue provar
que o fabric ficou igual ou melhor depois dela.** Para provar, você precisa de
um retrato comparável, em formato de dado — não de um `show` colado num chat.

`FabricSnapshot` é esse retrato: sessões BFD, conexões de controle, peers OMP
e SLA de app-route, por dispositivo, com timestamp.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import SDWANClient
from .inventory import Device, get_devices


# ── coletores individuais ───────────────────────────────────────────
# Todos são real-time: consultam o equipamento pelo plano de controle.
# São caros. É por isso que o cliente tem rate limit.

def get_control_connections(client: SDWANClient, system_ip: str) -> list[dict[str, Any]]:
    """Conexões de controle (DTLS/TLS) do dispositivo para os controladores."""
    return client.get("/device/control/connections", {"deviceId": system_ip}) or []


def get_bfd_sessions(client: SDWANClient, system_ip: str) -> list[dict[str, Any]]:
    """Sessões BFD — os túneis de dados entre TLOCs. O sinal vital do fabric."""
    return client.get("/device/bfd/sessions", {"deviceId": system_ip}) or []


def get_omp_peers(client: SDWANClient, system_ip: str) -> list[dict[str, Any]]:
    """Peers OMP — a adjacência de roteamento com os Controllers."""
    return client.get("/device/omp/peers", {"deviceId": system_ip}) or []


def get_approute_stats(client: SDWANClient, system_ip: str) -> list[dict[str, Any]]:
    """Latência/perda/jitter por túnel, como o app-route enxerga."""
    return client.get("/device/app-route/statistics", {"deviceId": system_ip}) or []


# ── o retrato ───────────────────────────────────────────────────────

@dataclass
class DeviceState:
    """Estado operacional de um dispositivo, reduzido ao que importa comparar."""

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
    """Retrato do fabric num instante. Serializável, comparável, versionável."""

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
    """Conta linhas cujo campo de estado diz 'up'.

    A API não é consistente: umas vezes o campo é `state`, outras `status`,
    outras `operstate`. Em vez de adivinhar, olhamos todos os candidatos.
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
    """Coleta o estado de um dispositivo. Não levanta erro se ele estiver fora."""
    state = DeviceState(
        system_ip=device.system_ip,
        hostname=device.hostname,
        reachable=device.is_reachable,
    )
    if not device.is_reachable:
        # Consultar um device inalcançável só gasta tempo e timeout.
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
    """Retrato completo do fabric. É a função que o pipeline chama duas vezes."""
    devices = devices if devices is not None else get_devices(client)
    snapshot = FabricSnapshot(taken_at=datetime.now(timezone.utc).isoformat())
    for device in devices:
        if not device.system_ip:
            continue
        snapshot.devices[device.system_ip] = collect_device_state(client, device)
    return snapshot
