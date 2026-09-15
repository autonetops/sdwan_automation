"""Module 3 — annotated solution.

The reference implementation lives in `sdwan_toolkit/client.py`; this file is
the same class with the reasoning left on show.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Any

import requests
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sdwan_toolkit.vault import ManagerCredentials, load_credentials  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class SDWANError(RuntimeError):
    """Generic failure talking to the Manager."""


class AuthenticationError(SDWANError):
    """Username or password rejected by the Manager."""


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
        # Everything the caller used to carry from call to call now lives here.
        # That is the entire justification for the class — the rest is what
        # becomes *possible* once one object owns the session.
        self.base_url = credentials.url.rstrip("/")
        self._credentials = credentials
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify
        self.limiter = RateLimiter(min_interval)
        self._token: str | None = None

        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("TLS verification disabled — acceptable in the lab only.")

    # ── constructors ────────────────────────────────────────────────

    @classmethod
    def from_vault(cls, **kwargs: Any) -> "SDWANClient":
        """Load credentials, authenticate, return a ready client.

        A separate constructor because "build the object" and "do network
        I/O" are different jobs. Tests construct SDWANClient(fake_creds) with
        no Vault and no Manager in sight — see tests/test_client.py.
        """
        client = cls(load_credentials(), **kwargs)
        client.login()
        return client

    # ── lifecycle ───────────────────────────────────────────────────

    def login(self) -> "SDWANClient":
        """The two-step handshake — module 2's authenticate(), now on self."""
        resp = self.session.post(
            f"{self.base_url}/j_security_check",
            data={
                "j_username": self._credentials.username,
                "j_password": self._credentials.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )
        resp.raise_for_status()

        # The trap: invalid credentials return 200 + the login page HTML.
        # AuthenticationError, not RuntimeError: a caller can now catch this
        # one failure instead of every RuntimeError in the language.
        if resp.text.strip().startswith("<html") or "<html" in resp.text[:512].lower():
            raise AuthenticationError(
                "The Manager returned the login page instead of a session. "
                "Invalid username or password."
            )
        if "JSESSIONID" not in self.session.cookies:
            raise AuthenticationError("Login did not return a JSESSIONID cookie.")

        # Step 2: the anti-CSRF token, required on every write since 19.2.
        # Harmless on GET, so we pin it to the session headers once.
        token_resp = self.session.get(
            f"{self.base_url}/dataservice/client/token", timeout=self.timeout
        )
        token_resp.raise_for_status()
        self._token = token_resp.text.strip()
        self.session.headers.update({"X-XSRF-TOKEN": self._token})

        logger.info("Authenticated to %s as %s", self.base_url, self._credentials.username)
        return self  # so SDWANClient(creds).login() chains

    def logout(self) -> None:
        # Best effort by design. If the logout call fails we do NOT want to
        # raise: we are usually on the way out of a `with` that is already
        # unwinding a real exception, and masking it would hide the actual
        # problem. The Manager expires the session on its own anyway.
        try:
            self.session.post(f"{self.base_url}/logout?nocache=true", timeout=10)
        except requests.RequestException:
            logger.debug("Logout failed; the session will expire on its own.")
        finally:
            # The `finally` matters: the socket gets closed either way.
            self.session.close()

    def __enter__(self) -> "SDWANClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        # This is where the class pays for itself. Manager sessions are a
        # finite resource; leaked ones are the usual cause of "I can't log in
        # any more" by mid-afternoon. `with` makes forgetting impossible.
        self.logout()

    # ── HTTP verbs ──────────────────────────────────────────────────

    def request(self, method: str, path: str, *, unwrap: bool = True, **kwargs: Any) -> Any:
        """Every call goes through here. That's the point.

        Rate limiting, error context and unwrapping stop being things each
        caller must remember and become things that simply happen.
        """
        # Callers may write "/device" or "/dataservice/device". Both work.
        if not path.startswith("/dataservice"):
            path = f"/dataservice{path if path.startswith('/') else '/' + path}"

        # Before the call, and in request() rather than get(): a deploy loop
        # hammers POST just as hard as a polling loop hammers GET.
        self.limiter.wait()
        resp = self.session.request(
            method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs
        )

        # An expired XSRF token is a different problem from "you lack
        # permission", and deserves a different sentence. The generic 403
        # message sends people to check user roles for twenty minutes.
        if resp.status_code == 403 and "XSRF" in resp.text.upper():
            raise SDWANError(
                f"403 on {path}: the X-XSRF-TOKEN expired. Call login() again."
            )
        if not resp.ok:
            # The body is where the Manager says what it actually disliked.
            # Truncated, because some error pages are the whole GUI.
            raise SDWANError(f"{method} {path} → HTTP {resp.status_code}: {resp.text[:300]}")

        if not resp.content:
            return None
        try:
            payload = resp.json()
        except ValueError:
            # /client/token answers plain text. Not everything is JSON.
            return resp.text
        return self._unwrap(payload) if unwrap else payload

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        """Strip the `{"data": ...}` envelope when it is present."""
        # "when it is present" is load-bearing. Not every endpoint wraps, and
        # assuming they all do produces a KeyError in the one you didn't test.
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, json: Any = None) -> Any:
        return self.request("POST", path, json=json)

    def put(self, path: str, json: Any = None) -> Any:
        return self.request("PUT", path, json=json)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)


def main() -> None:
    with SDWANClient.from_vault() as mgr:
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

        # What unwrapping throws away. Harmless on /device — fatal on the
        # task-status endpoint in module 4, where `summary` holds the state.
        raw = mgr.request("GET", "/device", unwrap=False)
        print(f"\nunwrap=False keys: {list(raw)}")

        controllers = mgr.get("/system/device/controllers") or []
        versions = sorted({c.get("version", "?") for c in controllers})
        print(f"\n>>> TASK 5 ANSWER: Manager release {', '.join(versions)}")


if __name__ == "__main__":
    main()
