"""Módulo 3 — solução comentada."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdwan_toolkit import SDWANClient  # noqa: E402
from sdwan_toolkit.configgroup import (  # noqa: E402
    get_associated_devices,
    list_config_groups,
    preview_device_config,
)
from sdwan_toolkit.tasks import wait_for_task  # noqa: E402


def meu_prefixo() -> str:
    aluno = os.getenv("WS_ALUNO")
    if not aluno:
        raise SystemExit("Defina WS_ALUNO. Ex: export WS_ALUNO=07")
    return f"ws{aluno}-"


def meu_config_group(client: SDWANClient):
    prefixo = meu_prefixo()
    grupo = next((g for g in list_config_groups(client) if g.name.startswith(prefixo)), None)
    if grupo is None:
        raise SystemExit(
            f"Nenhum config group começando com '{prefixo}'. "
            f"Confira o WS_ALUNO ou rode --listar para ver o que existe."
        )
    return grupo


def mostrar_preview(client: SDWANClient, group_id: str, device_uuid: str) -> None:
    print("\n─── CLI que SERIA aplicada (nada foi empurrado) ───")
    print(preview_device_config(client, group_id, device_uuid))
    print("───────────────────────────────────────────────────\n")


def fazer_deploy(client: SDWANClient, group_id: str, device_uuids: list[str]):
    resposta = client.post(
        f"/v1/config-group/{group_id}/device/deploy",
        {"devices": [{"id": uuid} for uuid in device_uuids]},
    )

    # O nome da chave mudou entre releases; aceitamos as duas.
    task_id = None
    if isinstance(resposta, dict):
        task_id = resposta.get("parentTaskId") or resposta.get("id")
    if not task_id:
        # Falhar alto. O pior resultado possível seria devolver "ok" aqui.
        raise RuntimeError(f"Deploy não devolveu id de tarefa. Resposta: {resposta!r}")

    print(f"Tarefa {task_id} aceita. Acompanhe na GUI em Monitor → Tasks.")

    # 15 min: deploy multi-site é lento. Timeout curto gera falso negativo,
    # e falso negativo faz gente repetir deploy — que é pior que esperar.
    return wait_for_task(client, task_id, timeout=900, interval=5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Config groups via API")
    parser.add_argument("--listar", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--deploy", action="store_true")
    args = parser.parse_args()

    with SDWANClient.from_vault() as client:
        if args.listar:
            for grupo in list_config_groups(client):
                marca = "→" if grupo.name.startswith(meu_prefixo()) else " "
                print(f"{marca} {grupo.name:<40} {grupo.id}")
            return

        grupo = meu_config_group(client)
        print(f"Config group: {grupo.name} ({grupo.id})")

        associados = [d.get("id") for d in get_associated_devices(client, grupo.id)]
        if not associados:
            print("Nenhum device associado. Fale com o instrutor.")
            return

        if args.preview:
            mostrar_preview(client, grupo.id, associados[0])
        elif args.deploy:
            print(fazer_deploy(client, grupo.id, associados).summary())


if __name__ == "__main__":
    main()
