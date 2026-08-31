"""Credenciais do Catalyst SD-WAN Manager, lidas do HashiCorp Vault.

Regra número um de automação: credencial não mora no código, não mora no
histórico do Git e não mora no seu `~/.bash_history`. Neste bootcamp elas
moram no Vault (`https://vault.autonetops.com`) e chegam ao seu script por
uma única função: `load_credentials()`.

Autenticação: token. Você recebe um token de leitura no início do bootcamp e
o exporta como `VAULT_TOKEN`.

    export VAULT_ADDR=https://vault.autonetops.com
    export VAULT_TOKEN=hvs.XXXXXXXXXXXX

Fallback: se `VAULT_TOKEN` não estiver definido, caímos para as variáveis
`VMANAGE_URL` / `VMANAGE_USERNAME` / `VMANAGE_PASSWORD`. Isso existe para
desenvolvimento offline e para o pipeline de CI — nunca para o seu laptop.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_VAULT_ADDR = "https://vault.autonetops.com"
DEFAULT_MOUNT = "secret"
DEFAULT_PATH = "sdwan/manager"


class CredentialsError(RuntimeError):
    """Não foi possível obter credenciais nem do Vault nem do ambiente."""


@dataclass(frozen=True)
class ManagerCredentials:
    """Endereço e login do Manager. Imutável de propósito."""

    url: str
    username: str
    password: str

    def __repr__(self) -> str:  # pragma: no cover - conveniência de debug
        # Nunca deixe a senha vazar num traceback ou num log.
        return f"ManagerCredentials(url={self.url!r}, username={self.username!r}, password='***')"


def _from_env() -> ManagerCredentials | None:
    url = os.getenv("VMANAGE_URL")
    username = os.getenv("VMANAGE_USERNAME")
    password = os.getenv("VMANAGE_PASSWORD")
    if url and username and password:
        return ManagerCredentials(url=url.rstrip("/"), username=username, password=password)
    return None


def _from_vault() -> ManagerCredentials | None:
    token = os.getenv("VAULT_TOKEN")
    if not token:
        return None

    try:
        import hvac
    except ImportError as exc:  # pragma: no cover
        raise CredentialsError(
            "VAULT_TOKEN está definido mas o pacote 'hvac' não está instalado. "
            "Rode: uv pip install hvac"
        ) from exc

    addr = os.getenv("VAULT_ADDR", DEFAULT_VAULT_ADDR)
    mount = os.getenv("VAULT_SDWAN_MOUNT", DEFAULT_MOUNT)
    path = os.getenv("VAULT_SDWAN_PATH", DEFAULT_PATH)

    client = hvac.Client(url=addr, token=token)
    if not client.is_authenticated():
        raise CredentialsError(
            f"Token rejeitado por {addr}. Ele expirou? Peça um novo ao instrutor."
        )

    # KV v2: o payload útil fica em data["data"]["data"].
    secret = client.secrets.kv.v2.read_secret_version(
        path=path, mount_point=mount, raise_on_deleted_version=True
    )
    data = secret["data"]["data"]

    missing = {"url", "username", "password"} - data.keys()
    if missing:
        raise CredentialsError(
            f"O segredo {mount}/{path} não tem as chaves: {', '.join(sorted(missing))}"
        )

    return ManagerCredentials(
        url=data["url"].rstrip("/"),
        username=data["username"],
        password=data["password"],
    )


def load_credentials() -> ManagerCredentials:
    """Devolve as credenciais do Manager: Vault primeiro, ambiente depois.

    Raises:
        CredentialsError: se nenhuma das duas fontes estiver utilizável.
    """
    creds = _from_vault() or _from_env()
    if creds is None:
        raise CredentialsError(
            "Sem credenciais. Exporte VAULT_TOKEN (recomendado) ou o trio "
            "VMANAGE_URL / VMANAGE_USERNAME / VMANAGE_PASSWORD."
        )
    return creds
