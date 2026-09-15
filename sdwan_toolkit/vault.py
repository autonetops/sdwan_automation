"""Catalyst SD-WAN Manager credentials, read from HashiCorp Vault.

Rule number one of automation: credentials don't live in code, don't live in
Git history, and don't live in your `~/.bash_history`. In this bootcamp they
live in Vault (`https://vault.autonetops.com`) and reach your script through
exactly one function: `load_credentials()`.

Auth method: **userpass**. You get a personal, read-only Vault login at the
start of the bootcamp:

    export VAULT_ADDR=https://vault.autonetops.com
    export VAULT_USERNAME=ws07
    export VAULT_PASSWORD=...

Note what is *not* here: no fallback to `VMANAGE_URL` / `VMANAGE_USERNAME` /
`VMANAGE_PASSWORD`. A fallback is a door, and a door people use once in CI is
a door someone eventually uses on a laptop. One source of truth, or none.

This module is module 1's deliverable — you build it before anything else,
because every other module starts by calling `load_credentials()`.
"""

from __future__ import annotations

import os

import hvac
from pydantic import BaseModel

DEFAULT_VAULT_ADDR = "https://vault.autonetops.com"
DEFAULT_MOUNT = "workshop"
DEFAULT_PATH = "sdwan"


class CredentialsError(RuntimeError):
    """Credentials could not be obtained from Vault."""


class ManagerCredentials(BaseModel):
    """Manager address and login.

    A model rather than a dict, for one reason worth more than the typing:
    pydantic validates at the boundary. If Vault ever hands back a secret with
    a missing or wrongly-typed field, you find out *here*, with a clear error,
    and not four calls later inside an HTTP request.
    """

    url: str
    username: str
    password: str

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        # Never let the password leak into a traceback, a log line or a
        # pytest failure report. This is not paranoia: `print(creds)` during
        # debugging is how secrets end up pasted into chat.
        return f"ManagerCredentials(url={self.url!r}, username={self.username!r}, password='***')"

    __str__ = __repr__


def _from_vault() -> ManagerCredentials | None:
    """Log in to Vault with userpass and read the Manager secret.

    Returns None when there is no `VAULT_PASSWORD` in the environment — that
    is "not configured", not "failed", and `load_credentials()` turns it into
    the error message the student actually needs.
    """
    username = os.getenv("VAULT_USERNAME")
    password = os.getenv("VAULT_PASSWORD")
    if not password:
        return None

    addr = os.getenv("VAULT_ADDR", DEFAULT_VAULT_ADDR)
    mount = os.getenv("VAULT_SDWAN_MOUNT", DEFAULT_MOUNT)
    path = os.getenv("VAULT_SDWAN_PATH", DEFAULT_PATH)

    # verify=False: the lab Vault uses a self-signed certificate. In
    # production this is a security bug, not a convenience.
    client = hvac.Client(url=addr, verify=False)
    try:
        client.auth.userpass.login(username=username, password=password)
    except Exception as exc:
        raise CredentialsError(f"Vault login failed at {addr} as {username!r}: {exc}") from exc

    if not client.is_authenticated():
        raise CredentialsError(
            f"Vault at {addr} rejected the login for {username!r}. "
            "Check VAULT_USERNAME / VAULT_PASSWORD, or ask the instructor."
        )

    # KV v2: the useful payload sits at data["data"]["data"]. The outer
    # envelope is the API response, the inner one is the secret's own version
    # wrapper. Everyone trips over this exactly once.
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
        url=data["url"].strip().rstrip("/"),
        username=data["username"],
        password=data["password"],
    )


def load_credentials() -> ManagerCredentials:
    """Return the Manager credentials from Vault.

    The single entry point every module uses. Nothing else in the toolkit
    reads a credential environment variable.

    Raises:
        CredentialsError: when Vault is not configured or not usable.
    """
    creds = _from_vault()
    if creds is None:
        raise CredentialsError(
            "No credentials. Export VAULT_USERNAME and VAULT_PASSWORD "
            "(and VAULT_ADDR if your Vault is not the bootcamp default)."
        )
    return creds
