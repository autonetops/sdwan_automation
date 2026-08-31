"""Módulo 5 — Pipeline de mudança validada (30 min)

Este é o capstone. Ele junta tudo:

    retrato ANTES  →  aplica a mudança  →  retrato DEPOIS  →  compara
                                                              ↓
                                              regrediu?  →  ROLLBACK

A ideia que o bootcamp inteiro serviu para construir: **mudança sem
verificação automática não é automação, é digitação mais rápida.**

Rode com:   python pipeline.py --dry-run     # só os retratos, não muda nada
            python pipeline.py               # o ciclo completo

Saída: código 0 se o fabric ficou igual ou melhor, 1 se regrediu.
É esse código de saída que o GitHub Actions usa para reprovar o PR.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdwan_toolkit import SDWANClient, compare, take_snapshot  # noqa: E402
from sdwan_toolkit.state import FabricSnapshot  # noqa: E402

RETRATOS = Path("snapshots")


# ─────────────────────────────────────────────────────────────────────
# TAREFA 1 — O retrato de referência
# ─────────────────────────────────────────────────────────────────────

def precheck(client: SDWANClient) -> FabricSnapshot:
    """Retrato ANTES da mudança. Também é o portão de entrada.

    Se o fabric já está quebrado antes de você mexer, a mudança não deve
    nem começar — senão você herda um problema que não era seu e não
    consegue mais distinguir a sua regressão da que já existia.
    """
    print("── PRECHECK ──")
    retrato = take_snapshot(client)

    # TODO 1.1: se algum device estiver `reachable=False`, avise na tela.
    #           Decida (e justifique no README) se isso deve abortar o
    #           pipeline. Dica: num lab compartilhado, abortar sempre é
    #           inviável; abortar quando um EDGE ALVO está fora, não.

    # TODO 1.2: salve o retrato em RETRATOS / "antes.json" e devolva-o.
    return retrato


# ─────────────────────────────────────────────────────────────────────
# TAREFA 2 — Aplicar a mudança
# ─────────────────────────────────────────────────────────────────────

def aplicar() -> bool:
    """Aplica a mudança com Terraform. Devolve True se o apply passou."""
    # TODO 2.1: rode `terraform apply -auto-approve` dentro de ../04-terraform
    #           usando subprocess.run. Devolva True se returncode == 0.
    #
    #           ⚠️ Não use shell=True com string interpolada. Passe lista de
    #              argumentos — é a diferença entre um comando e uma injeção.
    return False


# ─────────────────────────────────────────────────────────────────────
# TAREFA 3 — Verificar e decidir
# ─────────────────────────────────────────────────────────────────────

def postcheck(client: SDWANClient, antes: FabricSnapshot) -> bool:
    """Retrato DEPOIS + veredito. True = seguro manter a mudança."""
    print("── POSTCHECK ──")

    # TODO 3.1: tire o retrato depois e salve em RETRATOS / "depois.json".

    # TODO 3.2: compare(antes, depois), imprima o .report() e devolva .ok
    #
    #           ⏱️ PENSE NO TEMPO: BFD e OMP não reconvergem instantaneamente.
    #              Um postcheck imediato acusa regressão que não existe.
    #              Quanto esperar? Justifique a sua escolha.
    return False


# ─────────────────────────────────────────────────────────────────────
# TAREFA 4 — Desfazer
# ─────────────────────────────────────────────────────────────────────

def rollback() -> None:
    """Desfaz a mudança. É a parte que quase todo pipeline caseiro esquece."""
    print("── ROLLBACK ──")
    # TODO 4.1: o Terraform guarda o estado anterior. A forma mais simples
    #           de reverter no lab é `terraform apply` com o valor antigo da
    #           variável, ou `terraform destroy -target=...`.
    #           Implemente e explique no README por que escolheu essa via.
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline de mudança validada")
    parser.add_argument("--dry-run", action="store_true",
                        help="tira os dois retratos sem aplicar mudança nenhuma")
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
