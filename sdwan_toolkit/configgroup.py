"""Config Groups — o modelo de configuração da era UX 2.0.

Se você vem de feature templates + device templates, o mapa mental é:

    feature template   →  parcel (dentro de um feature profile)
    device template    →  config group
    attach             →  associate + deploy
    variáveis do CSV   →  device variables

A diferença que importa para automação: config group é **hierárquico e
declarativo**. Você descreve o grupo, associa dispositivos, preenche
variáveis e manda fazer deploy. O Manager calcula o diff e empurra.

⚠️ Versão: config groups exigem Manager 20.12+ / IOS-XE 17.12+. O formato
exato de alguns payloads mudou entre releases — se um POST vier com 400,
abra as Ferramentas de Desenvolvedor na GUI, faça a mesma ação clicando e
compare o corpo da requisição. Essa é a técnica, não a gambiarra.
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
    """Dispositivos já associados ao grupo."""
    payload = client.get(f"/v1/config-group/{group_id}/device/associate") or []
    if isinstance(payload, dict):
        payload = payload.get("devices", [])
    return payload


def associate_devices(
    client: SDWANClient, group_id: str, device_uuids: list[str]
) -> None:
    """Associa dispositivos ao grupo.

    Idempotência: a API não reclama de reassociar, mas nós filtramos o que já
    está lá. Reenviar a lista inteira em alguns releases *substitui* a
    associação — e desassociar um dispositivo por engano é exatamente o tipo
    de acidente que a automação deveria impedir.
    """
    already = {d.get("id") for d in get_associated_devices(client, group_id)}
    novos = [uuid for uuid in device_uuids if uuid not in already]
    if not novos:
        return
    client.post(
        f"/v1/config-group/{group_id}/device/associate",
        {"devices": [{"id": uuid} for uuid in novos]},
    )


def get_device_variables(client: SDWANClient, group_id: str) -> dict[str, Any]:
    """Variáveis por dispositivo — o equivalente ao CSV do device template."""
    return client.get(f"/v1/config-group/{group_id}/device/variables") or {}


def set_device_variables(
    client: SDWANClient, group_id: str, payload: dict[str, Any]
) -> None:
    """Grava as variáveis. Faça GET, altere, PUT — nunca monte do zero.

    O payload traz campos internos que o Manager espera de volta intactos.
    Reconstruir à mão é como fazer `write erase` para mudar um hostname.
    """
    client.put(f"/v1/config-group/{group_id}/device/variables", payload)


def preview_device_config(client: SDWANClient, group_id: str, device_uuid: str) -> str:
    """CLI que *seria* aplicada, sem aplicar. O `terraform plan` dos pobres.

    Use isto antes de todo deploy. É grátis, é seguro, e é a única forma de
    responder "o que exatamente vai mudar?" antes de descobrir na marra.
    """
    result = client.get(f"/v1/config-group/{group_id}/device/{device_uuid}/preview")
    if isinstance(result, dict):
        return result.get("config") or result.get("deviceConfigurationPreview") or str(result)
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
    """Dispara o deploy e (por padrão) espera terminar.

    Devolve o `TaskResult` quando `wait=True`, ou o id da tarefa quando False.
    """
    response = client.post(
        f"/v1/config-group/{group_id}/device/deploy",
        {"devices": [{"id": uuid} for uuid in device_uuids]},
    )

    task_id = None
    if isinstance(response, dict):
        task_id = response.get("parentTaskId") or response.get("id")
    if not task_id:
        raise RuntimeError(f"Deploy não devolveu id de tarefa. Resposta: {response!r}")

    if not wait:
        return task_id
    return wait_for_task(
        client, task_id, timeout=timeout, raise_on_failure=raise_on_failure
    )
