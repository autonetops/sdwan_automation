from __future__ import annotations

import os

import hvac
from pydantic import BaseModel

# The bootcamp defaults. Overridable by environment variable so the same code
# runs against the instructor's Vault, yours, and CI, with no edit.
DEFAULT_VAULT_ADDR = "https://vault.autonetops.com"
DEFAULT_MOUNT = "workshop"
DEFAULT_PATH = "sdwan"


class CredentialsError(RuntimeError):
    """Credentials could not be obtained from Vault."""


# ─────────────────────────────────────────────────────────────────────
# TASK 1 — Model the secret
#
# A dict would work. A model is better for one reason worth more than the
# typing: pydantic validates at the boundary. If Vault ever hands back a
# secret with a missing field, you find out HERE — with a clear error — and
# not four calls later, inside an HTTP request, as a KeyError.
# ─────────────────────────────────────────────────────────────────────

class ManagerCredentials(BaseModel):
    """Manager address and login."""

    # TODO 1.1: declare three required fields — url, username, password —
    #           all `str`. Pydantic makes them mandatory by default; that is
    #           the point.

    # TODO 1.2: override __repr__ so the password NEVER appears.
    #           Return something like:
    #               ManagerCredentials(url='https://…', username='admin', password='***')
    #
    #           This is not paranoia. `print(creds)` while debugging is
    #           exactly how secrets end up pasted into a chat window, and a
    #           pytest failure report prints the repr of everything it holds.
    #
    #           Hint: also assign `__str__ = __repr__`, or print() will happily
    #           use the default and undo your work.


# ─────────────────────────────────────────────────────────────────────
# TASK 2 — Read the secret from Vault
#
# Auth method: userpass. You log in with a username and password and Vault
# hands your client a short-lived token, which hvac stores for you.
#
# ─────────────────────────────────────────────────────────────────────

def _from_vault() -> ManagerCredentials | None:
    """Log in to Vault and read the Manager secret.

    Returns None when Vault is not configured at all — that is "not set up",
    not "failed", and the caller turns it into a useful message.
    """
    username = os.getenv("VAULT_USERNAME")
    password = os.getenv("VAULT_PASSWORD")

    # TODO 2.1: if there is no password in the environment, return None.
    #           Don't raise here — "unconfigured" and "broken" are different
    #           conditions and deserve different messages.

    addr = os.getenv("VAULT_ADDR", DEFAULT_VAULT_ADDR)
    mount = os.getenv("VAULT_SDWAN_MOUNT", DEFAULT_MOUNT)
    path = os.getenv("VAULT_SDWAN_PATH", DEFAULT_PATH)

    # verify=False: the lab Vault has a self-signed certificate. In production
    # this is a security bug, not a convenience — you lose any guarantee that
    # you are talking to the real Vault.
    client = hvac.Client(url=addr, verify=False)

    # TODO 2.2: log in with userpass:
    #               client.auth.userpass.login(username=..., password=...)
    #           Wrap it in try/except and re-raise as CredentialsError with
    #           the address and username in the message. A bare hvac traceback
    #           tells a student nothing; "Vault at X rejected ws07" tells them
    #           everything.

    # TODO 2.3: hvac does not always raise on a bad login. Confirm with
    #           client.is_authenticated() and raise CredentialsError if False.

    # TODO 2.4: we are already using KV v2. Inspect the secret and store in data
    secret = client.secrets.kv.v2.read_secret_version(
            path=path, mount_point=mount, raise_on_deleted_version=True
        )
    data: dict = {}

    # TODO 2.5: check that url, username and password are all present.
    #           If any is missing, raise CredentialsError naming WHICH ones.
    #           "Something went wrong" costs the next person twenty minutes.

    # TODO 2.6: return a ManagerCredentials. Strip whitespace from the url and
    #           drop any trailing "/" — a stored "https://mgr.lab/" would
    #           otherwise produce "https://mgr.lab//dataservice/device".
    return None


# ─────────────────────────────────────────────────────────────────────
# TASK 3 — The one entry point
#
# Every module from here on calls this and nothing else. One function is the
# whole security model: there is exactly one place to audit, and exactly one
# place to change when the lab moves.
# ─────────────────────────────────────────────────────────────────────

def load_credentials() -> ManagerCredentials:
    """Return the Manager credentials from Vault."""
    # TODO 3.1: call _from_vault(). If it returns None, raise CredentialsError
    #           telling the student exactly which variables to export.
    #           Otherwise return the credentials.
    raise NotImplementedError("TODO 3.1")


def main() -> None:
    creds = load_credentials()

    print("Credentials loaded from Vault:")
    print(f"  url      : {creds.url}")
    print(f"  username : {creds.username}")
    print(f"  password : {'*' * 8}")
    print(f"\n  repr()   : {creds!r}")

    if "***" not in repr(creds):
        print("\n⚠️  Your __repr__ is leaking the password. Back to TODO 1.2.")

if __name__ == "__main__":
    main()
