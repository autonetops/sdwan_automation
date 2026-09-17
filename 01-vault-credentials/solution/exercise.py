"""Module 1 — annotated solution.

The reference implementation lives in `sdwan_toolkit/vault.py`; this file is
the same code with the reasoning left on show.
"""

from __future__ import annotations

import os

import hvac
from pydantic import BaseModel, Field, field_validator

DEFAULT_VAULT_ADDR = "https://vault.autonetops.com"
DEFAULT_MOUNT = "workshop"
DEFAULT_PATH = "sdwan"


class CredentialsError(RuntimeError):
    """Credentials could not be obtained from Vault."""


class ManagerCredentials(BaseModel):
    url: str = Field(..., description="Manager address, e.g. 'https://manager.lab'")
    username: str
    password: str

    @field_validator("url")
    def url_must_be_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"Manager URL must start with https://, got {v!r}")
        return v.strip().rstrip("/")

    def __repr__(self) -> str:
        # The whole job of this method is to be boring and safe. Pydantic's
        # default repr prints every field, password included — and that repr
        # is what appears in tracebacks, log lines and pytest failure output.
        return f"ManagerCredentials(url={self.url!r}, username={self.username!r}, password='***')"

    # Without this, print(creds) uses the default __str__ and leaks anyway.
    __str__ = __repr__


def _from_vault() -> ManagerCredentials | None:
    username = os.getenv("VAULT_USERNAME")
    password = os.getenv("VAULT_PASSWORD")

    # "Not configured" is not "broken". Returning None lets load_credentials()
    # produce the message that actually helps: which variables to export.
    if not password:
        return None

    addr = os.getenv("VAULT_ADDR", DEFAULT_VAULT_ADDR)
    mount = os.getenv("VAULT_SDWAN_MOUNT", DEFAULT_MOUNT)
    path = os.getenv("VAULT_SDWAN_PATH", DEFAULT_PATH)

    client = hvac.Client(url=addr, verify=False)

    try:
        client.auth.userpass.login(username=username, password=password)
    except Exception as exc:
        # Re-raise with context. A raw hvac traceback ("InvalidRequest") tells
        # a student nothing; the address and the username tell them everything.
        raise CredentialsError(
            f"Vault login failed at {addr} as {username!r}: {exc}"
        ) from exc

    # Belt and braces: hvac does not raise on every rejection path.
    if not client.is_authenticated():
        raise CredentialsError(
            f"Vault at {addr} rejected the login for {username!r}. "
            "Check VAULT_USERNAME / VAULT_PASSWORD, or ask the instructor."
        )

    # KV v2 wraps the secret twice: the API response envelope, then the
    # version wrapper. secret["data"]["data"] is the payload you stored.
    secret = client.secrets.kv.v2.read_secret_version(
        path=path, mount_point=mount, raise_on_deleted_version=True
    )
    data = secret["data"]["data"]

    # Validate the shape and name what is missing. Set arithmetic reads better
    # than three ifs, and the error tells the instructor what to fix in Vault.
    missing = {"url", "username", "password"} - data.keys()
    if missing:
        raise CredentialsError(
            f"Secret {mount}/{path} is missing the keys: {', '.join(sorted(missing))}"
        )

    return ManagerCredentials(
        # A stored "https://manager.lab/" would otherwise become
        # "https://manager.lab//dataservice/device" — which some proxies
        # answer with a 404 and no explanation at all.
        url=data["url"].strip().rstrip("/"),
        username=data["username"],
        password=data["password"],
    )


def load_credentials() -> ManagerCredentials:
    """The single entry point. Every module calls this and nothing else."""
    creds = _from_vault()
    if creds is None:
        raise CredentialsError(
            "No credentials. Export VAULT_USERNAME and VAULT_PASSWORD "
            "(and VAULT_ADDR if your Vault is not the bootcamp default)."
        )
    return creds


def main() -> None:
    creds = load_credentials()

    print("Credentials loaded from Vault:")
    print(f"  url      : {creds.url}")
    print(f"  username : {creds.username}")
    print(f"  password : {'*' * 8}")
    print(f"\n  repr()   : {creds!r}")
    print(f"\n>>> TASK 3 ANSWER: {creds.url} as {creds.username}")


if __name__ == "__main__":
    main()
