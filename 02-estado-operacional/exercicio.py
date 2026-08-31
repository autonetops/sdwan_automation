"""Módulo 2 — Estado operacional como dado (50 min)

Objetivo: produzir um retrato do fabric que possa ser salvo, versionado e
comparado. Sem isso, "a mudança deu certo" é opinião.

Rode com:   python exercicio.py --salvar antes.json
            python exercicio.py --salvar depois.json
            python exercicio.py --comparar antes.json depois.json

Confira:    python -m pytest ../tests/test_diff.py -q
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit import SDWANClient, compare, get_devices  # noqa: E402
from sdwan_toolkit.state import (  # noqa: E402
    DeviceState,
    FabricSnapshot,
    get_bfd_sessions,
    get_control_connections,
    get_omp_peers,
)
from datetime import datetime, timezone  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# TAREFA 1 — Contar o que está "up"
#
# A API do Manager não é consistente: dependendo do endpoint o campo de
# estado se chama `state`, `status` ou `operstate`, e o valor pode vir
# "up", "Up" ou "UP". Escrever `if row["state"] == "up"` funciona hoje e
# quebra no próximo endpoint.
# ─────────────────────────────────────────────────────────────────────

def contar_up(linhas: list[dict], *campos: str) -> int:
    """Conta linhas cujo campo de estado indica 'up' (ou 'ok')."""
    # TODO 1.1: para cada linha, olhe cada campo candidato em `campos`.
    #           Normalize com str(...).lower() antes de comparar.
    #           Conte a linha UMA vez só, mesmo que dois campos batam.
    return 0


# ─────────────────────────────────────────────────────────────────────
# TAREFA 2 — Coletar o estado de um dispositivo
#
# ⚠️ CUSTO: estes endpoints são real-time. O Manager vai consultar o
#    equipamento pelo plano de controle. São caros e o lab é compartilhado
#    com a turma inteira. Não colete o que você não vai comparar, e nunca
#    consulte um device que já sabe estar inalcançável.
# ─────────────────────────────────────────────────────────────────────

def coletar(client: SDWANClient, device) -> DeviceState:
    estado = DeviceState(
        system_ip=device.system_ip,
        hostname=device.hostname,
        reachable=device.is_reachable,
    )

    # TODO 2.1: se o device NÃO estiver alcançável, devolva `estado` agora.
    #           Consultar um device fora do ar só gasta timeout.

    # TODO 2.2: conexões de controle → get_control_connections(client, system_ip)
    #           Conte as que estão up e guarde em estado.control_connections_up.

    # TODO 2.3: SÓ para edges (device.is_edge), colete as sessões BFD.
    #           Guarde a contagem em estado.bfd_sessions_up e a lista de
    #           system-ip dos peers que estão up em estado.bfd_peers.
    #           Controladores não têm BFD — perguntar devolve lista vazia
    #           e gasta uma chamada à toa.

    # TODO 2.4: peers OMP → get_omp_peers(client, system_ip)

    return estado


def tirar_retrato(client: SDWANClient) -> FabricSnapshot:
    retrato = FabricSnapshot(taken_at=datetime.now(timezone.utc).isoformat())
    for device in get_devices(client):
        if device.system_ip:
            retrato.devices[device.system_ip] = coletar(client, device)
    return retrato


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrato operacional do fabric")
    parser.add_argument("--salvar", metavar="ARQUIVO", help="tira um retrato e grava")
    parser.add_argument("--comparar", nargs=2, metavar=("ANTES", "DEPOIS"))
    args = parser.parse_args()

    if args.comparar:
        antes = FabricSnapshot.load(args.comparar[0])
        depois = FabricSnapshot.load(args.comparar[1])
        print(compare(antes, depois).report())
        return

    with SDWANClient.from_vault() as client:
        retrato = tirar_retrato(client)

    print(f"{'HOSTNAME':<20} {'CONTROL':>8} {'BFD':>6} {'OMP':>6}")
    print("-" * 44)
    for estado in retrato.devices.values():
        print(
            f"{estado.hostname:<20} "
            f"{estado.control_connections_up:>8} "
            f"{estado.bfd_sessions_up:>6} "
            f"{estado.omp_peers_up:>6}"
        )

    if args.salvar:
        caminho = retrato.save(args.salvar)
        print(f"\nRetrato gravado em {caminho}")

    # TODO 3.1: rode contra o lab e anote — qual edge tem MAIS sessões BFD up?
    #           Essa é a sua resposta do módulo 2.


if __name__ == "__main__":
    main()
