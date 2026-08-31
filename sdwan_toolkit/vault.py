"""Catalyst SD-WAN Manager credentials, read from HashiCorp Vault.

Rule number one of automation: credentials don't live in code, don't live in
Git history, and don't live in your `~/.bash_history`. In this bootcamp they
live in Vault (`https://vault.autonetops.com`) and reach your script through
exactly one function: `load_credentials()`.

Auth method: token. You get a read-only token at the start of the bootcamp
and export it as `VAULT_TOKEN`.

    export VAULT_ADDR=https://vault.autonetops.com
    export VAULT_TOKEN=hvs.XXXXXXXXXXXX

Fallback: if `VAULT_TOKEN` is unset, we fall back to `VMANAGE_URL` /
`VMANAGE_USERNAME` / `VMANAGE_PASSWORD`. That exists for offline development
and for the CI pipeline — never for your laptop.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_VAULT_ADDR = "https://vault.autonetops.com"
DEFAULT_MOUNT = "secret"
DEFAULT_PATH = "sdwan/manager"


class CredentialsError(RuntimeError):
    """Credentials could not be obtained from Vault or from the environment."""


@dataclass(frozen=True)
class ManagerCredentials:
    """Manager address and login. Immutable on purpose."""

    url: str
    username: str
    password: str

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        # Never let the password leak into a traceback or a log line.
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
            "VAULT_TOKEN is set but the 'hvac' package is not installed. "
            "Run: pip install hvac"
        ) from exc

    addr = os.getenv("VAULT_ADDR", DEFAULT_VAULT_ADDR)
    mount = os.getenv("VAULT_SDWAN_MOUNT", DEFAULT_MOUNT)
    path = os.getenv("VAULT_SDWAN_PATH", DEFAULT_PATH)

    client = hvac.Client(url=addr, token=token)
    if not client.is_authenticated():
        raise CredentialsError(
            f"Token rejected by {addr}. Has it expired? Ask the instructor for a new one."
        )

    # KV v2: the useful payload sits at data["data"]["data"].
    secret = client.secrets.kv.v2.read_secret_version(
        path=path, mount_point=mount, raise_on_deleted_version=True
    )
    data = secret["data"]["data"]

    missing = {"url", "username", "password"} - data.keys()
    if missing:
        raise CredentialsError(
            f"Secret {mount}/{path} is missing the keys: {', '.join(sorted(missing))}"
        )

    return ManagerCredentials(
        url=data["url"].rstrip("/"),
        username=data["username"],
        password=data["password"],
    )


def load_credentials() -> ManagerCredentials:
    """Return the Manager credentials: Vault first, environment second.

    Raises:
        CredentialsError: when neither source is usable.
    """
    creds = _from_vault() or _from_env()
    if creds is None:
        raise CredentialsError(
            "No credentials. Export VAULT_TOKEN (recommended) or the trio "
            "VMANAGE_URL / VMANAGE_USERNAME / VMANAGE_PASSWORD."
        )
    return creds
