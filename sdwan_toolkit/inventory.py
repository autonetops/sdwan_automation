"""Inventário do fabric.

Lição de modelagem: o Manager tem *duas* visões de inventário e elas não são
intercambiáveis.

- `/dataservice/device` é **real-time**: o Manager responde sobre quem está
  conectado ao plano de controle agora. Tem `reachability`, não tem quem está
  cadastrado mas nunca subiu.
- `/dataservice/system/device/{vedges,controllers}` é o **banco de configuração**:
  tudo que foi cadastrado, incluindo o que está offline. Tem `validity`
  (estado do certificado), não tem estado operacional.

Automação madura sabe qual das duas está perguntando.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

from .client import SDWANClient

CONTROLLER_PERSONALITIES = {"vmanage", "vsmart", "vbond"}


@dataclass
class Device:
    """Um nó do fabric, normalizado.

    A API devolve chaves com hífen (`host-name`, `system-ip`) e valores
    inconsistentes entre endpoints. Normalizar na borda — assim que o dado
    entra — evita espalhar `d.get("host-name") or d.get("hostName")` pelo
    código inteiro.
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
    """Todos os dispositivos vistos pelo plano de controle (visão real-time)."""
    return [Device.from_api(d) for d in client.get("/device") or []]


def get_edges(client: SDWANClient) -> list[Device]:
    """Só os WAN Edges — é neles que a automação de configuração atua."""
    return [d for d in get_devices(client) if d.is_edge]


def get_controllers(client: SDWANClient) -> list[Device]:
    return [d for d in get_devices(client) if d.is_controller]


def find_by_hostname(devices: Iterable[Device], hostname: str) -> Device | None:
    target = hostname.lower()
    return next((d for d in devices if d.hostname.lower() == target), None)


def unreachable(devices: Iterable[Device]) -> list[Device]:
    """Atalho para o check mais comum de pré-mudança."""
    return [d for d in devices if not d.is_reachable]
