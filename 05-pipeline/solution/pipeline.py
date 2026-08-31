"""Módulo 5 — solução comentada do pipeline de mudança validada."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sdwan_toolkit import SDWANClient, compare, take_snapshot  # noqa: E402
from sdwan_toolkit.inventory import unreachable  # noqa: E402
from sdwan_toolkit.state import FabricSnapshot  # noqa: E402

RETRATOS = Path("snapshots")
TERRAFORM_DIR = Path(__file__).resolve().parents[2] / "04-terraform"

# BFD e OMP levam tempo para reconvergir depois de um push. Verificar cedo
# demais acusa uma regressão que não existe — e um pipeline que grita lobo
# é um pipeline que as pessoas desligam.
ESPERA_CONVERGENCIA = 60


def precheck(client: SDWANClient) -> FabricSnapshot:
    print("── PRECHECK ──")
    retrato = take_snapshot(client)

    fora = [e for e in retrato.devices.values() if not e.reachable]
    if fora:
        # Não abortamos: num lab compartilhado sempre tem alguém com um device
        # derrubado de propósito. Mas registramos, porque o `compare` só olha
        # a DIFERENÇA — um device que já estava fora antes e depois não gera
        # achado nenhum, e sem esta linha ninguém perceberia.
        nomes = ", ".join(e.hostname for e in fora)
        print(f"  ⚠ Já estavam inalcançáveis ANTES da mudança: {nomes}")

    caminho = retrato.save(RETRATOS / "antes.json")
    print(f"  Retrato salvo em {caminho} ({len(retrato.devices)} dispositivos)")
    return retrato


def aplicar() -> bool:
    print("── APPLY ──")
    # Lista de argumentos, nunca shell=True com string montada.
    resultado = subprocess.run(
        ["terraform", "apply", "-auto-approve", "-input=false"],
        cwd=TERRAFORM_DIR,
        text=True,
    )
    return resultado.returncode == 0


def postcheck(client: SDWANClient, antes: FabricSnapshot) -> bool:
    print("── POSTCHECK ──")
    print(f"  Aguardando {ESPERA_CONVERGENCIA}s de convergência…")
    time.sleep(ESPERA_CONVERGENCIA)

    depois = take_snapshot(client)
    depois.save(RETRATOS / "depois.json")

    diferenca = compare(antes, depois)
    print(diferenca.report())
    return diferenca.ok


def rollback() -> None:
    print("── ROLLBACK ──")
    # Escolha: `terraform apply` com o valor default da variável, em vez de
    # `destroy`. Destruir o config group inteiro é mais violento que a mudança
    # que estamos desfazendo — e rollback que causa mais impacto que o
    # problema original não é rollback, é um segundo incidente.
    resultado = subprocess.run(
        ["terraform", "apply", "-auto-approve", "-input=false",
         "-var", "banner_motd=ROLLBACK - estado anterior restaurado"],
        cwd=TERRAFORM_DIR,
        text=True,
    )
    if resultado.returncode == 0:
        print("  Rollback aplicado.")
    else:
        # Rollback que falha é a pior situação possível: escalar, não repetir.
        print("  ✗ ROLLBACK FALHOU — intervenção manual necessária.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline de mudança validada")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    RETRATOS.mkdir(exist_ok=True)

    with SDWANClient.from_vault() as client:
        antes = precheck(client)

        if args.dry_run:
            print("\n[dry-run] Nenhuma mudança aplicada.")
            return 0 if postcheck(client, antes) else 1

        if not aplicar():
            print("Apply falhou. Nada a verificar.")
            return 1

        if postcheck(client, antes):
            print("\n✓ Fabric íntegro. Mudança mantida.")
            return 0

        print("\n✗ Regressão detectada.")
        rollback()
        return 1


if __name__ == "__main__":
    sys.exit(main())
