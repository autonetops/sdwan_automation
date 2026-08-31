"""O aperto de mão com o Manager — incluindo a armadilha do HTTP 200."""

import pytest
import responses

from sdwan_toolkit.client import AuthenticationError, SDWANClient, SDWANError
from tests.conftest import BASE_URL

LOGIN_HTML = "<html><head><title>Cisco Catalyst SD-WAN</title></head><body>login</body></html>"


def _mock_login_ok():
    responses.add(
        responses.POST, f"{BASE_URL}/j_security_check", body="",
        status=200, headers={"Set-Cookie": "JSESSIONID=abc123; Path=/; HttpOnly"},
    )
    responses.add(
        responses.GET, f"{BASE_URL}/dataservice/client/token",
        body="TOKEN-XSRF-123", status=200,
    )


@responses.activate
def test_login_guarda_cookie_e_token(credentials):
    _mock_login_ok()
    client = SDWANClient(credentials).login()
    assert "JSESSIONID" in client.session.cookies
    assert client.session.headers["X-XSRF-TOKEN"] == "TOKEN-XSRF-123"


@responses.activate
def test_credencial_errada_devolve_200_com_html(credentials):
    """A armadilha clássica: o Manager não devolve 401, devolve a tela de login."""
    responses.add(responses.POST, f"{BASE_URL}/j_security_check",
                  body=LOGIN_HTML, status=200)
    with pytest.raises(AuthenticationError, match="página de login"):
        SDWANClient(credentials).login()


@responses.activate
def test_get_desembrulha_o_envelope_data(credentials, device_payload):
    _mock_login_ok()
    responses.add(responses.GET, f"{BASE_URL}/dataservice/device",
                  json={"header": {}, "data": device_payload}, status=200)
    client = SDWANClient(credentials, min_interval=0).login()
    assert [d["host-name"] for d in client.get("/device")][0] == "Manager-1"


@responses.activate
def test_prefixo_dataservice_e_opcional(credentials):
    _mock_login_ok()
    responses.add(responses.GET, f"{BASE_URL}/dataservice/device/counters",
                  json={"data": [{"ok": True}]}, status=200)
    client = SDWANClient(credentials, min_interval=0).login()
    assert client.get("/device/counters") == client.get("/dataservice/device/counters")


@responses.activate
def test_erro_http_vira_excecao_com_contexto(credentials):
    _mock_login_ok()
    responses.add(responses.GET, f"{BASE_URL}/dataservice/device",
                  json={"error": {"message": "sem permissão"}}, status=500)
    client = SDWANClient(credentials, min_interval=0).login()
    with pytest.raises(SDWANError, match="HTTP 500"):
        client.get("/device")


@responses.activate
def test_xsrf_expirado_tem_mensagem_propria(credentials):
    _mock_login_ok()
    responses.add(responses.POST, f"{BASE_URL}/dataservice/device/action/deploy",
                  body="Invalid XSRF token", status=403)
    client = SDWANClient(credentials, min_interval=0).login()
    with pytest.raises(SDWANError, match="X-XSRF-TOKEN expirou"):
        client.post("/device/action/deploy", {})


def test_repr_nao_vaza_senha(credentials):
    assert "s3nh4" not in repr(credentials)
    assert "***" in repr(credentials)
