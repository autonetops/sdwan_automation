"""HTTP client for the Catalyst SD-WAN Manager `/dataservice` API.

This is the foundation for everything else in the bootcamp. It solves four
problems everyone hits on their first script against the Manager:

1. **The two-step handshake.** The Manager doesn't use bearer tokens. You POST
   to `/j_security_check` to earn the `JSESSIONID` cookie, then GET
   `/dataservice/client/token` to earn the `X-XSRF-TOKEN` header, required on
   every write (POST/PUT/DELETE) since 19.2.
2. **The silent failure.** A bad login does not return 401. It returns
   **HTTP 200 with the login page HTML**. People who don't test for this spend
   an hour debugging a `KeyError` when the answer was "wrong password".
3. **The envelope.** Almost every response is wrapped in `{"data": [...]}`.
4. **The lab is shared.** A whole class hammering real-time endpoints will take
   the Manager down. Hence the rate limiter.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import requests
import urllib3

from .vault import ManagerCredentials, load_credentials

logger = logging.getLogger(__name__)


class SDWANError(RuntimeError):
    """Generic failure talking to the Manager."""


class AuthenticationError(SDWANError):
    """Username or password rejected by the Manager."""


class RateLimiter:
    """Call spacer. Simple, thread-safe, good enough.

    The lab has ONE Manager for the whole class. Real-time endpoints
    (`/dataservice/device/*`) query the device across the control plane;
    twenty people in a tight loop turn the lab into an incident. A floor on
    the interval between calls fixes it.
    """

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
    """An authenticated session against the Manager.

    Normal use:

        with SDWANClient.from_vault() as mgr:
            for device in mgr.get("/device"):
                print(device["host-name"], device["system-ip"])

    The `with` guarantees logout — Manager sessions are a finite resource, and
    leaked sessions are the most common cause of "I can't log in any more" by
    the end of the day.
    """

    def __init__(
        self,
        credentials: ManagerCredentials,
        *,
        verify: bool = False,
        timeout: int = 60,
        min_interval: float = 0.34,
    ) -> None:
        self.base_url = credentials.url.rstrip("/")
        self._credentials = credentials
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify
        self.limiter = RateLimiter(min_interval)
        self._token: str | None = None

        if not verify:
            # The lab uses a self-signed certificate. In production this is a
            # security bug, not a convenience: you lose any guarantee that you
            # are actually talking to the Manager.
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("TLS verification disabled — acceptable in the lab only.")

    # ── constructors ────────────────────────────────────────────────

    @classmethod
    def from_vault(cls, **kwargs: Any) -> "SDWANClient":
        """Load credentials (Vault → environment), authenticate, return the client."""
        client = cls(load_credentials(), **kwargs)
        client.login()
        return client

    # ── lifecycle ───────────────────────────────────────────────────

    def login(self) -> "SDWANClient":
        """Perform the two-step handshake."""
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
        if resp.text.strip().startswith("<html") or "<html" in resp.text[:512].lower():
            raise AuthenticationError(
                "The Manager returned the login page instead of a session. "
                "Invalid username or password."
            )
        if "JSESSIONID" not in self.session.cookies:
            raise AuthenticationError("Login did not return a JSESSIONID cookie.")

        # Step 2: the anti-CSRF token, required on every write.
        token_resp = self.session.get(
            f"{self.base_url}/dataservice/client/token", timeout=self.timeout
        )
        token_resp.raise_for_status()
        self._token = token_resp.text.strip()
        self.session.headers.update({"X-XSRF-TOKEN": self._token})

        logger.info("Authenticated to %s as %s", self.base_url, self._credentials.username)
        return self

    def logout(self) -> None:
        try:
            self.session.post(f"{self.base_url}/logout?nocache=true", timeout=10)
        except requests.RequestException:  # pragma: no cover - best effort
            logger.debug("Logout failed; the session will expire on its own.")
        finally:
            self.session.close()

    def __enter__(self) -> "SDWANClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.logout()

    # ── HTTP verbs ──────────────────────────────────────────────────

    def request(self, method: str, path: str, *, unwrap: bool = True, **kwargs: Any) -> Any:
        """Call with rate limiting, error handling and (optional) unwrapping.

        Args:
            unwrap: when True (default) return only the contents of `data`.
                Pass False when the response has sibling fields you need — the
                classic case is `/device/action/status/{id}`, which returns
                `summary` **alongside** `data`; unwrapping there throws away
                the very thing that holds the task state.
        """
        if not path.startswith("/dataservice"):
            path = f"/dataservice{path if path.startswith('/') else '/' + path}"

        self.limiter.wait()
        resp = self.session.request(
            method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs
        )

        if resp.status_code == 403 and "XSRF" in resp.text.upper():
            raise SDWANError(
                f"403 on {path}: the X-XSRF-TOKEN expired. Call login() again."
            )
        if not resp.ok:
            raise SDWANError(f"{method} {path} → HTTP {resp.status_code}: {resp.text[:300]}")

        if not resp.content:
            return None
        try:
            payload = resp.json()
        except ValueError:
            return resp.text
        return self._unwrap(payload) if unwrap else payload

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        """Strip the `{"data": ...}` envelope when it is present."""
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
