"""Módulo 1 — Conectando ao Manager (45 min)

Você vai escrever o aperto de mão à mão, com `requests` puro. Depois disso o
`sdwan_toolkit` faz por você para sempre — mas só depois de você ter sentido
por que ele existe.

Rode com:   python exercicio.py
Confira:    python -m pytest ../tests/test_client.py -q
"""

import os
import sys

import requests
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sdwan_toolkit.vault import load_credentials  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ─────────────────────────────────────────────────────────────────────
# TAREFA 1 — Autenticar
#
# O Manager não usa Bearer token. São dois passos:
#
#   1. POST {base_url}/j_security_check
#      corpo form-encoded: j_username / j_password
#      → devolve o cookie JSESSIONID
#
#   2. GET {base_url}/dataservice/client/token
#      → devolve, em texto puro, o valor do header X-XSRF-TOKEN
#
# ⚠️ A ARMADILHA: senha errada NÃO devolve 401. Devolve HTTP 200 com o HTML
#    da tela de login. Se você não checar isso, vai debugar um KeyError por
#    uma hora quando a resposta certa era "sua senha está errada".
# ─────────────────────────────────────────────────────────────────────

def autenticar(base_url: str, usuario: str, senha: str) -> requests.Session:
    """Devolve uma requests.Session autenticada e pronta para escrever."""
    session = requests.Session()
    session.verify = False  # lab com certificado self-signed

    # TODO 1.1: faça o POST em /j_security_check com os dados do formulário.
    #           Dica: data={"j_username": ..., "j_password": ...}

    # TODO 1.2: detecte a armadilha. Se "<html" aparecer no início do corpo
    #           da resposta, levante RuntimeError("usuário ou senha inválidos").

    # TODO 1.3: confirme que o cookie JSESSIONID entrou em session.cookies.

    # TODO 1.4: pegue o token em /dataservice/client/token e coloque-o
    #           em session.headers como "X-XSRF-TOKEN".

    return session


# ─────────────────────────────────────────────────────────────────────
# TAREFA 2 — Listar o fabric
#
# GET /dataservice/device devolve {"header": {...}, "data": [...]}.
# O que interessa está sempre dentro de "data" — este envelope vai te
# perseguir por toda a API.
# ─────────────────────────────────────────────────────────────────────

def listar_dispositivos(session: requests.Session, base_url: str) -> list[dict]:
    """Devolve a lista de dispositivos já desembrulhada de 'data'."""
    # TODO 2.1: faça o GET e devolva resp.json()["data"].
    return []


# ─────────────────────────────────────────────────────────────────────
# TAREFA 3 — Responder à pergunta do instrutor
#
# Rode contra o lab e anote a resposta. Ela só existe no fabric de verdade.
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    creds = load_credentials()
    print(f"Conectando em {creds.url} como {creds.username}…")

    session = autenticar(creds.url, creds.username, creds.password)
    dispositivos = listar_dispositivos(session, creds.url)

    if not dispositivos:
        print("Nenhum dispositivo. As TODOs ainda estão em aberto?")
        return

    print(f"\n{'HOSTNAME':<20} {'SYSTEM-IP':<16} {'TIPO':<10} {'SITE':<6} ALCANÇÁVEL")
    print("-" * 68)
    for d in dispositivos:
        print(
            f"{d.get('host-name', '?'):<20} "
            f"{d.get('system-ip', '?'):<16} "
            f"{d.get('personality', '?'):<10} "
            f"{str(d.get('site-id', '?')):<6} "
            f"{d.get('reachability', '?')}"
        )

    # TODO 3.1: quantos WAN Edges (personality != vmanage/vsmart/vbond)
    #           estão 'reachable'? Guarde o número — é a sua resposta.
    edges = [
        d for d in dispositivos
        if d.get("personality") not in ("vmanage", "vsmart", "vbond")
    ]
    print(f"\nTotal de dispositivos: {len(dispositivos)}")
    print(f"WAN Edges: {len(edges)}")


if __name__ == "__main__":
    main()
