"""Cliente HTTP para a API `/dataservice` do Catalyst SD-WAN Manager.

Este é o alicerce de todo o resto do bootcamp. Ele resolve quatro problemas
que todo mundo enfrenta no primeiro script contra o Manager:

1. **O aperto de mão de duas etapas.** O Manager não usa Bearer token. Você
   faz POST em `/j_security_check` para ganhar o cookie `JSESSIONID` e depois
   GET em `/dataservice/client/token` para ganhar o header `X-XSRF-TOKEN`,
   obrigatório em toda escrita (POST/PUT/DELETE) desde a 19.2.
2. **A falha silenciosa.** Login errado no Manager não devolve 401. Devolve
   **HTTP 200 com a página HTML de login**. Quem não testa isso passa uma hora
   debugando um `KeyError` em vez de ler "senha errada".
3. **O envelope.** Quase toda resposta vem embrulhada em `{"data": [...]}`.
4. **O laboratório é compartilhado.** Uma turma inteira batendo em endpoints
   real-time derruba o Manager. Por isso este cliente tem rate limit.
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
    """Erro genérico de conversa com o Manager."""


class AuthenticationError(SDWANError):
    """Usuário ou senha rejeitados pelo Manager."""


class RateLimiter:
    """Espaçador de chamadas. Simples, thread-safe, suficiente.

    O laboratório tem UM Manager para a turma inteira. Endpoints real-time
    (`/dataservice/device/*`) consultam o equipamento pelo plano de controle;
    vinte pessoas em laço fechado transformam o lab num incidente. Um piso de
    intervalo entre chamadas resolve.
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
    """Sessão autenticada contra o Manager.

    Uso normal:

        with SDWANClient.from_vault() as mgr:
            for device in mgr.get("/device"):
                print(device["host-name"], device["system-ip"])

    O `with` garante logout — sessão do Manager é um recurso finito, e sessão
    pendurada é a causa mais comum de "não consigo mais logar" no fim do dia.
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
            # O lab usa certificado self-signed. Em produção isto é um bug de
            # segurança, não uma conveniência: você perde a garantia de estar
            # falando com o Manager de verdade.
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("Verificação de TLS desabilitada — aceitável apenas no lab.")

    # ── construtores ────────────────────────────────────────────────

    @classmethod
    def from_vault(cls, **kwargs: Any) -> "SDWANClient":
        """Carrega credenciais (Vault → ambiente), autentica e devolve o cliente."""
        client = cls(load_credentials(), **kwargs)
        client.login()
        return client

    # ── ciclo de vida ───────────────────────────────────────────────

    def login(self) -> "SDWANClient":
        """Executa o aperto de mão de duas etapas."""
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

        # A armadilha: credencial inválida devolve 200 + HTML da tela de login.
        if resp.text.strip().startswith("<html") or "<html" in resp.text[:512].lower():
            raise AuthenticationError(
                "O Manager devolveu a página de login em vez de uma sessão. "
                "Usuário ou senha inválidos."
            )
        if "JSESSIONID" not in self.session.cookies:
            raise AuthenticationError("Login não retornou cookie JSESSIONID.")

        # Etapa 2: o token anti-CSRF, exigido em toda escrita.
        token_resp = self.session.get(
            f"{self.base_url}/dataservice/client/token", timeout=self.timeout
        )
        token_resp.raise_for_status()
        self._token = token_resp.text.strip()
        self.session.headers.update({"X-XSRF-TOKEN": self._token})

        logger.info("Autenticado em %s como %s", self.base_url, self._credentials.username)
        return self

    def logout(self) -> None:
        try:
            self.session.post(f"{self.base_url}/logout?nocache=true", timeout=10)
        except requests.RequestException:  # pragma: no cover - best effort
            logger.debug("Logout falhou; a sessão vai expirar sozinha.")
        finally:
            self.session.close()

    def __enter__(self) -> "SDWANClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.logout()

    # ── verbos HTTP ─────────────────────────────────────────────────

    def request(self, method: str, path: str, *, unwrap: bool = True, **kwargs: Any) -> Any:
        """Chamada com rate limit, tratamento de erro e (opcionalmente) desembrulho.

        Args:
            unwrap: quando True (padrão) devolve só o conteúdo de `data`. Passe
                False quando a resposta tiver campos irmãos que você precisa —
                o caso clássico é `/device/action/status/{id}`, que traz
                `summary` **ao lado** de `data`; desembrulhar ali joga fora
                justamente o estado da tarefa.
        """
        if not path.startswith("/dataservice"):
            path = f"/dataservice{path if path.startswith('/') else '/' + path}"

        self.limiter.wait()
        resp = self.session.request(
            method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs
        )

        if resp.status_code == 403 and "XSRF" in resp.text.upper():
            raise SDWANError(
                f"403 em {path}: o X-XSRF-TOKEN expirou. Refaça o login()."
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
        """Tira o envelope `{"data": ...}` quando ele existe."""
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
