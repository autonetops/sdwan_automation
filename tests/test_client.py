"""The handshake with the Manager — including the HTTP 200 trap."""

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
def test_login_stores_cookie_and_token(credentials):
    _mock_login_ok()
    client = SDWANClient(credentials).login()
    assert "JSESSIONID" in client.session.cookies
    assert client.session.headers["X-XSRF-TOKEN"] == "TOKEN-XSRF-123"


@responses.activate
def test_bad_credentials_return_200_with_html(credentials):
    """The classic trap: the Manager returns the login page, not a 401."""
    responses.add(responses.POST, f"{BASE_URL}/j_security_check",
                  body=LOGIN_HTML, status=200)
    with pytest.raises(AuthenticationError, match="login page"):
        SDWANClient(credentials).login()


@responses.activate
def test_get_unwraps_the_data_envelope(credentials, device_payload):
    _mock_login_ok()
    responses.add(responses.GET, f"{BASE_URL}/dataservice/device",
                  json={"header": {}, "data": device_payload}, status=200)
    client = SDWANClient(credentials, min_interval=0).login()
    assert [d["host-name"] for d in client.get("/device")][0] == "Manager-1"


@responses.activate
def test_the_dataservice_prefix_is_optional(credentials):
    _mock_login_ok()
    responses.add(responses.GET, f"{BASE_URL}/dataservice/device/counters",
                  json={"data": [{"ok": True}]}, status=200)
    client = SDWANClient(credentials, min_interval=0).login()
    assert client.get("/device/counters") == client.get("/dataservice/device/counters")


@responses.activate
def test_http_errors_become_exceptions_with_context(credentials):
    _mock_login_ok()
    responses.add(responses.GET, f"{BASE_URL}/dataservice/device",
                  json={"error": {"message": "forbidden"}}, status=500)
    client = SDWANClient(credentials, min_interval=0).login()
    with pytest.raises(SDWANError, match="HTTP 500"):
        client.get("/device")


@responses.activate
def test_an_expired_xsrf_token_gets_its_own_message(credentials):
    _mock_login_ok()
    responses.add(responses.POST, f"{BASE_URL}/dataservice/device/action/deploy",
                  body="Invalid XSRF token", status=403)
    client = SDWANClient(credentials, min_interval=0).login()
    with pytest.raises(SDWANError, match="X-XSRF-TOKEN expired"):
        client.post("/device/action/deploy", {})


def test_repr_does_not_leak_the_password(credentials):
    assert "s3cr3t" not in repr(credentials)
    assert "***" in repr(credentials)
