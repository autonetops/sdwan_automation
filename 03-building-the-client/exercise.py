"""Module 3 — From functions to a client (35 min)

Run:    python exercise.py
Check:  python -m pytest ../tests/test_client.py -q
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Any

import requests
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sdwan_toolkit.vault import ManagerCredentials, load_credentials  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ─────────────────────────────────────────────────────────────────────
# WHAT YOU WROTE IN MODULE 2 — working, and about to become methods.
#
# Read them once more with a different question in mind: what does every
# caller have to remember, and what should the object remember instead?
# ─────────────────────────────────────────────────────────────────────


def authenticate(base_url: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    session.verify = False

    resp = session.post(
        f"{base_url}/j_security_check",
        data={"j_username": username, "j_password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    resp.raise_for_status()

    if "<html" in resp.text[:512].lower():
        raise RuntimeError(
            "Invalid username or password (the Manager returned the login page)."
        )

    if "JSESSIONID" not in session.cookies:
        raise RuntimeError("Login did not return JSESSIONID.")

    token = session.get(f"{base_url}/dataservice/client/token", timeout=60)
    token.raise_for_status()
    session.headers.update({"X-XSRF-TOKEN": token.text.strip()})

    return session


def list_devices(session: requests.Session, base_url: str) -> list[dict]:
    resp = session.get(f"{base_url}/dataservice/device", timeout=60)
    resp.raise_for_status()
    return resp.json()["data"]


# ─────────────────────────────────────────────────────────────────────
# GIVEN — the rate limiter. Nothing to do here.
#
# This is threading, not SD-WAN, so it's written for you. But understand WHY
# it exists: `/dataservice/device/*` endpoints are real-time — the Manager
# queries the device across the control plane to answer. One Manager, twenty
# students, tight loops, and the class becomes an incident.
#
# A floor on the interval between calls fixes it. 0.34s ≈ 3 calls/second.
# ─────────────────────────────────────────────────────────────────────


class RateLimiter:
    """Call spacer. Simple, thread-safe, good enough."""

    def __init__(self, min_interval: float = 0.34) -> None:
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_call = time.monotonic()


class SDWANError(RuntimeError):
    """Generic failure talking to the Manager."""


class AuthenticationError(SDWANError):
    """Username or password rejected by the Manager."""


# ─────────────────────────────────────────────────────────────────────
# TASK 1 — State: what the object holds so the caller doesn't
#
# In module 2 the caller carried `session` and `base_url` to every call. The
# client carries them instead. That's the whole idea; everything else follows.
# ─────────────────────────────────────────────────────────────────────


class SDWANClient:
    """An authenticated session against the Manager."""

    def __init__(
        self,
        credentials: ManagerCredentials,
        *,
        verify: bool = False,
        timeout: int = 60,
        min_interval: float = 0.34,
    ) -> None:
        # TASK 1.1: store what every method will need:
        #             self.base_url   — credentials.url with any trailing "/" removed
        #             self._credentials
        #             self.timeout
        #             self.session    — a requests.Session with .verify = verify
        #             self.limiter    — a RateLimiter(min_interval)
        #             self._token     — None for now
        #
        #           Note `verify` is a parameter with a default, not a
        #           hardcoded False. The lab needs False; production needs
        #           True; the same class serves both.
        raise NotImplementedError("TASK 1.1")

    # ── constructors ────────────────────────────────────────────────

    @classmethod
    def from_vault(cls, **kwargs: Any) -> "SDWANClient":
        """Load credentials, authenticate, return a ready client."""
        # TASK 1.2: build the client with load_credentials(), call .login()
        #           on it, and return it.
        #
        #           Why a classmethod and not a flag on __init__? Because
        #           "construct" and "perform network I/O" are different jobs.
        #           Tests build SDWANClient(fake_creds) with no Vault and no
        #           Manager anywhere — look at tests/test_client.py.
        raise NotImplementedError("TASK 1.2")

    # ─────────────────────────────────────────────────────────────────
    # TASK 2 — Lifecycle: login, logout, and the `with` that guarantees it
    # ─────────────────────────────────────────────────────────────────

    def login(self) -> "SDWANClient":
        """The two-step handshake. Same as module 2, now on self."""
        # TASK 2.1: port `authenticate()` above into this method.
        #           - use self.session, self.base_url, self.timeout
        #           - credentials come from self._credentials
        #           - store the token in self._token AND in the session headers
        #           - raise AuthenticationError (not RuntimeError) on the HTML
        #             trap and the missing cookie — a caller can now catch the
        #             specific failure instead of every RuntimeError in Python
        #           - return self, so `SDWANClient(creds).login()` chains
        raise NotImplementedError("TASK 2.1")

    def logout(self) -> None:
        """Hand the session back. Manager sessions are a finite resource."""
        # TASK 2.2: POST to {base_url}/logout?nocache=true, then close the
        #           session.
        #
        #           ⚠️ Best effort: wrap the POST in try/except
        #              requests.RequestException and swallow it, but close the
        #              session in a `finally`. If logout fails you don't want
        #              to mask the real exception that got you here — and the
        #              session will expire on its own anyway.
        raise NotImplementedError("TASK 2.2")

    # TASK 2.3: implement __enter__ and __exit__ so this works:
    #
    #               with SDWANClient.from_vault() as mgr:
    #                   ...
    #
    #           __enter__ returns self; __exit__ calls self.logout().
    #
    #           This is the reason the class earns its keep. Leaked sessions
    #           are the single most common cause of "I can't log in any more"
    #           by the end of a workshop day, and `with` makes forgetting
    #           impossible — including when the body raises.

    # ─────────────────────────────────────────────────────────────────
    # TASK 3 — One request method every call goes through
    #
    # In module 2, every call had to remember raise_for_status() and
    # ["data"]. Here it happens once, and the things that MUST always happen
    # — spacing, error context, unwrapping — happen whether the caller
    # remembers or not.
    # ─────────────────────────────────────────────────────────────────

    def request(
        self, method: str, path: str, *, unwrap: bool = True, **kwargs: Any
    ) -> Any:
        """Call the Manager with rate limiting, error handling and unwrapping.

        Args:
            unwrap: when True (default) return only the contents of `data`.
                Pass False when the response has sibling fields you need —
                module 4 needs exactly that.
        """
        # TASK 3.1: make the /dataservice prefix optional. If `path` doesn't
        #           start with "/dataservice", prepend it. Callers should be
        #           able to write "/device" or "/dataservice/device" and get
        #           the same result.

        # TASK 3.2: self.limiter.wait() — BEFORE the call, always. Not in
        #           get() only: a deploy loop hammers POST just as hard.

        # TASK 3.3: perform the call with self.session.request(method, url,
        #           timeout=self.timeout, **kwargs).

        # TASK 3.4: a 403 whose body mentions XSRF gets its own message —
        #           "the X-XSRF-TOKEN expired, call login() again". It is a
        #           different problem from "you lack permission", and the
        #           generic message sends people down the wrong path.

        # TASK 3.5: any other non-ok status → raise SDWANError including the
        #           method, the path, the status code and the first ~300 chars
        #           of the body. The body is where the Manager says what it
        #           actually disliked.

        # TASK 3.6: return the payload:
        #             - empty body            → None
        #             - not JSON              → resp.text
        #             - JSON, unwrap=True     → self._unwrap(payload)
        #             - JSON, unwrap=False    → payload
        raise NotImplementedError("TASK 3.1–3.6")

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        """Strip the `{"data": ...}` envelope when it is present."""
        # TASK 3.7: if payload is a dict containing "data", return payload["data"].
        #           Otherwise return it untouched — not every endpoint wraps,
        #           and assuming they all do is how you get a KeyError in the
        #           one place you didn't test.
        raise NotImplementedError("TASK 3.7")

    # ─────────────────────────────────────────────────────────────────
    # TASK 4 — The verbs
    #
    # Four one-liners. They exist so calling code reads like intent
    # (`mgr.get("/device")`) instead of plumbing.
    # ─────────────────────────────────────────────────────────────────

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        # TASK 4.1
        raise NotImplementedError("TASK 4.1")

    def post(self, path: str, json: Any = None) -> Any:
        # TASK 4.2
        raise NotImplementedError("TASK 4.2")

    def put(self, path: str, json: Any = None) -> Any:
        # TASK 4.3
        raise NotImplementedError("TASK 4.3")

    def delete(self, path: str) -> Any:
        # TASK 4.4
        raise NotImplementedError("TASK 4.4")


# ─────────────────────────────────────────────────────────────────────
# TASK 5 — Use it, and see what the refactor bought you
# ─────────────────────────────────────────────────────────────────────


def main() -> None:
    with SDWANClient.from_vault() as mgr:
        # Compare this with module 2's main(). Same result, no session and no
        # base_url in sight, and the logout is guaranteed by the `with`.
        devices = mgr.get("/device")

        print(f"{'HOSTNAME':<20} {'SYSTEM-IP':<16} {'TYPE':<10} {'SITE':<6} REACHABLE")
        print("-" * 68)
        for d in devices:
            print(
                f"{d.get('host-name', '?'):<20} "
                f"{d.get('system-ip', '?'):<16} "
                f"{d.get('personality', '?'):<10} "
                f"{str(d.get('site-id', '?')):<6} "
                f"{d.get('reachability', '?')}"
            )

        # TASK 5.1: call the SAME endpoint with unwrap=False:
        #
        #               raw = mgr.request("GET", "/device", unwrap=False)
        #
        #           and print raw.keys(). Look at what unwrapping threw away.
        #           Module 4 depends on this: the task-status endpoint returns
        #           `summary` alongside `data`, and `summary` is the only place
        #           the task state lives. Unwrap it and you lose the answer.

        # TASK 5.2: the configuration-database view, for your answer below:
        #               controllers = mgr.get("/system/device/controllers")
        #           Each row carries a `version`. Which release is the lab
        #           Manager running?


if __name__ == "__main__":
    main()
