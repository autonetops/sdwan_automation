"""Módulo 1 — solução comentada."""

import os
import sys

import requests
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sdwan_toolkit.vault import load_credentials  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def autenticar(base_url: str, usuario: str, senha: str) -> requests.Session:
    session = requests.Session()
    session.verify = False

    # Passo 1 — a sessão. Note o form-encoded: este endpoint é herança de
    # Java EE (j_security_check é do Servlet spec), não é uma API REST.
    resp = session.post(
        f"{base_url}/j_security_check",
        data={"j_username": usuario, "j_password": senha},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    resp.raise_for_status()

    # A armadilha. 200 + HTML = falha de login disfarçada de sucesso.
    if "<html" in resp.text[:512].lower():
        raise RuntimeError("Usuário ou senha inválidos (o Manager devolveu a tela de login).")

    if "JSESSIONID" not in session.cookies:
        raise RuntimeError("Login não devolveu JSESSIONID.")

    # Passo 2 — o token anti-CSRF. Obrigatório em POST/PUT/DELETE desde a 19.2.
    # Em GET ele é inofensivo, então deixamos fixo no header da sessão.
    token = session.get(f"{base_url}/dataservice/client/token", timeout=60)
    token.raise_for_status()
    session.headers.update({"X-XSRF-TOKEN": token.text.strip()})

    return session


def listar_dispositivos(session: requests.Session, base_url: str) -> list[dict]:
    resp = session.get(f"{base_url}/dataservice/device", timeout=60)
    resp.raise_for_status()
    # O envelope onipresente da API do Manager.
    return resp.json()["data"]


def main() -> None:
    creds = load_credentials()
    print(f"Conectando em {creds.url} como {creds.username}…")

    session = autenticar(creds.url, creds.username, creds.password)
    dispositivos = listar_dispositivos(session, creds.url)

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

    controladores = {"vmanage", "vsmart", "vbond"}
    edges = [d for d in dispositivos if d.get("personality") not in controladores]
    edges_up = [e for e in edges if e.get("reachability") == "reachable"]

    print(f"\nTotal de dispositivos: {len(dispositivos)}")
    print(f"WAN Edges: {len(edges)}  |  alcançáveis: {len(edges_up)}")
    print(f"\n>>> RESPOSTA DA TAREFA 3: {len(edges_up)} WAN Edges alcançáveis")


if __name__ == "__main__":
    main()
