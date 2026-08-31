"""Módulo 2 — solução comentada.

A implementação de referência vive em `sdwan_toolkit/state.py`; este arquivo
é a mesma lógica escrita passo a passo, com o raciocínio à mostra.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdwan_toolkit import SDWANClient, compare, get_devices  # noqa: E402
from sdwan_toolkit.state import (  # noqa: E402
    DeviceState,
    FabricSnapshot,
    get_bfd_sessions,
    get_control_connections,
    get_omp_peers,
)


def contar_up(linhas: list[dict], *campos: str) -> int:
    total = 0
    for linha in linhas:
        for campo in campos:
            if str(linha.get(campo, "")).lower() in {"up", "ok"}:
                total += 1
                break  # o break evita contar a mesma linha duas vezes
    return total


def coletar(client: SDWANClient, device) -> DeviceState:
    estado = DeviceState(
        system_ip=device.system_ip,
        hostname=device.hostname,
        reachable=device.is_reachable,
    )

    # Saída antecipada: device fora do ar não responde, só consome timeout.
    if not device.is_reachable:
        return estado

    estado.control_connections_up = contar_up(
        get_control_connections(client, device.system_ip), "state", "status"
    )

    # BFD só existe entre edges. Perguntar a um controlador é chamada jogada fora.
    if device.is_edge:
        bfd = get_bfd_sessions(client, device.system_ip)
        estado.bfd_sessions_up = contar_up(bfd, "state", "status")
        estado.bfd_peers = sorted(
            {
                linha.get("system-ip", "")
                for linha in bfd
                if str(linha.get("state", "")).lower() == "up"
            }
            - {""}
        )

    estado.omp_peers_up = contar_up(
        get_omp_peers(client, device.system_ip), "state", "status"
    )

    return estado


def tirar_retrato(client: SDWANClient) -> FabricSnapshot:
    retrato = FabricSnapshot(taken_at=datetime.now(timezone.utc).isoformat())
    for device in get_devices(client):
        if device.system_ip:
            retrato.devices[device.system_ip] = coletar(client, device)
    return retrato


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrato operacional do fabric")
    parser.add_argument("--salvar", metavar="ARQUIVO")
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
            f"{estado.hostname:<20} {estado.control_connections_up:>8} "
            f"{estado.bfd_sessions_up:>6} {estado.omp_peers_up:>6}"
        )

    if args.salvar:
        print(f"\nRetrato gravado em {retrato.save(args.salvar)}")

    edges = [e for e in retrato.devices.values() if e.bfd_sessions_up]
    if edges:
        campeao = max(edges, key=lambda e: e.bfd_sessions_up)
        print(f"\n>>> RESPOSTA: {campeao.hostname} com {campeao.bfd_sessions_up} sessões BFD up")


if __name__ == "__main__":
    main()
