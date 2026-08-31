"""Módulo 3 — Config Groups e o modelo assíncrono (50 min)

Aqui você escreve no fabric pela primeira vez. Três disciplinas entram junto:

  1. **Preview antes de deploy.** Sempre. É grátis e é a única resposta
     honesta para "o que exatamente vai mudar?".
  2. **Esperar a tarefa.** O Manager devolve um id e vai embora. Script que
     não espera mente sobre o próprio resultado.
  3. **Namespace.** O lab é compartilhado. Tudo que você criar leva o seu
     prefixo `ws<NN>-`. Sem isso, vocês pisam no pé uns dos outros.

Rode com:   export WS_ALUNO=07          # o número que o instrutor te deu
            python exercicio.py --listar
            python exercicio.py --preview
            python exercicio.py --deploy

Confira:    python -m pytest ../tests/test_tasks.py -q
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        raise SystemExit("Defina WS_ALUNO com o número que o instrutor te deu. Ex: export WS_ALUNO=07")
    return f"ws{aluno}-"


# ─────────────────────────────────────────────────────────────────────
# TAREFA 1 — Achar o seu config group
# ─────────────────────────────────────────────────────────────────────

def meu_config_group(client: SDWANClient):
    """Devolve o ConfigGroup cujo nome começa com o seu prefixo."""
    # TODO 1.1: liste os config groups e devolva o primeiro cujo `name`
    #           comece com meu_prefixo(). Se não achar, levante SystemExit
    #           com uma mensagem útil.
    return None


# ─────────────────────────────────────────────────────────────────────
# TAREFA 2 — Preview: ver antes de fazer
#
# `preview_device_config` devolve a CLI que *seria* empurrada, sem empurrar.
# É o `terraform plan` do Manager, e quase ninguém usa.
# ─────────────────────────────────────────────────────────────────────

def mostrar_preview(client: SDWANClient, group_id: str, device_uuid: str) -> None:
    # TODO 2.1: chame preview_device_config e imprima o resultado.
    #           Leia a saída: você consegue apontar a linha que vai mudar?
    pass


# ─────────────────────────────────────────────────────────────────────
# TAREFA 3 — Deploy com espera
#
# O POST devolve {"parentTaskId": "..."}. A mudança acontece DEPOIS.
# Sem polling você não sabe se deu certo — só sabe que foi aceita.
# ─────────────────────────────────────────────────────────────────────

def fazer_deploy(client: SDWANClient, group_id: str, device_uuids: list[str]):
    """Dispara o deploy e espera terminar. Devolve o TaskResult."""
    # TODO 3.1: POST em /v1/config-group/{group_id}/device/deploy
    #           com {"devices": [{"id": uuid}, ...]}
    resposta = None

    # TODO 3.2: extraia o id da tarefa (chave "parentTaskId", com "id" de reserva).
    #           Se não vier nada, levante RuntimeError — falhar alto é melhor
    #           do que devolver sucesso silencioso.
    task_id = None

    # TODO 3.3: chame wait_for_task(). Escolha um timeout realista:
    #           deploy em vários sites passa fácil de 5 minutos.
    return None


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
        if grupo is None:
            return
        print(f"Config group: {grupo.name} ({grupo.id})")

        associados = [d.get("id") for d in get_associated_devices(client, grupo.id)]
        if not associados:
            print("Nenhum device associado a este grupo. Fale com o instrutor.")
            return

        if args.preview:
            mostrar_preview(client, grupo.id, associados[0])
        elif args.deploy:
            resultado = fazer_deploy(client, grupo.id, associados)
            if resultado:
                print(resultado.summary())


if __name__ == "__main__":
    main()
