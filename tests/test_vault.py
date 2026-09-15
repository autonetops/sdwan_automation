"""Module 1 — credentials from Vault, tested with no Vault anywhere.

Everything here runs against a fake hvac client. That is the point: the code
that fetches your secrets should be testable without handing a secret to the
test suite.
"""

from types import SimpleNamespace

import pytest

from sdwan_toolkit import vault
from sdwan_toolkit.vault import CredentialsError, ManagerCredentials, load_credentials

SECRET = {
    "url": "https://manager.example.lab",
    "username": "automation",
    "password": "s3cr3t",
}


def fake_hvac(secret=SECRET, *, authenticated=True, login_raises=None):
    """Build a stand-in for hvac.Client that records how it was called."""
    calls = {}

    def login(username=None, password=None):
        calls["login"] = (username, password)
        if login_raises is not None:
            raise login_raises

    def read_secret_version(path, mount_point, raise_on_deleted_version):
        calls["read"] = (mount_point, path)
        # KV v2 wraps twice: response envelope, then version wrapper.
        return {"data": {"data": secret, "metadata": {"version": 1}}}

    def factory(url, verify):
        calls["client"] = (url, verify)
        return SimpleNamespace(
            auth=SimpleNamespace(userpass=SimpleNamespace(login=login)),
            is_authenticated=lambda: authenticated,
            secrets=SimpleNamespace(
                kv=SimpleNamespace(
                    v2=SimpleNamespace(read_secret_version=read_secret_version)
                )
            ),
        )

    factory.calls = calls
    return factory


@pytest.fixture
def vault_env(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://vault.example.lab")
    monkeypatch.setenv("VAULT_USERNAME", "ws07")
    monkeypatch.setenv("VAULT_PASSWORD", "student-pw")
    monkeypatch.delenv("VAULT_SDWAN_MOUNT", raising=False)
    monkeypatch.delenv("VAULT_SDWAN_PATH", raising=False)


def test_unconfigured_is_not_an_error(monkeypatch):
    """No VAULT_PASSWORD means 'not set up', which is not the same as 'broken'."""
    monkeypatch.delenv("VAULT_PASSWORD", raising=False)
    assert vault._from_vault() is None


def test_load_credentials_says_what_to_export(monkeypatch):
    monkeypatch.delenv("VAULT_PASSWORD", raising=False)
    with pytest.raises(CredentialsError, match="VAULT_USERNAME"):
        load_credentials()


def test_the_kv_v2_double_envelope_is_unwrapped(monkeypatch, vault_env):
    monkeypatch.setattr(vault.hvac, "Client", fake_hvac())
    creds = load_credentials()
    assert creds.url == "https://manager.example.lab"
    assert creds.username == "automation"
    assert creds.password == "s3cr3t"


def test_it_logs_in_with_userpass_at_the_right_address(monkeypatch, vault_env):
    factory = fake_hvac()
    monkeypatch.setattr(vault.hvac, "Client", factory)
    load_credentials()
    assert factory.calls["client"] == ("https://vault.example.lab", False)
    assert factory.calls["login"] == ("ws07", "student-pw")
    assert factory.calls["read"] == ("workshop", "sdwan")


def test_mount_and_path_are_overridable(monkeypatch, vault_env):
    monkeypatch.setenv("VAULT_SDWAN_MOUNT", "kv")
    monkeypatch.setenv("VAULT_SDWAN_PATH", "team/sdwan")
    factory = fake_hvac()
    monkeypatch.setattr(vault.hvac, "Client", factory)
    load_credentials()
    assert factory.calls["read"] == ("kv", "team/sdwan")


def test_a_rejected_login_gets_context(monkeypatch, vault_env):
    monkeypatch.setattr(
        vault.hvac, "Client", fake_hvac(login_raises=RuntimeError("permission denied"))
    )
    with pytest.raises(CredentialsError, match="ws07"):
        load_credentials()


def test_a_silent_rejection_is_caught_too(monkeypatch, vault_env):
    """hvac does not raise on every rejection path — is_authenticated() does."""
    monkeypatch.setattr(vault.hvac, "Client", fake_hvac(authenticated=False))
    with pytest.raises(CredentialsError, match="rejected"):
        load_credentials()


def test_a_malformed_secret_names_the_missing_keys(monkeypatch, vault_env):
    monkeypatch.setattr(
        vault.hvac, "Client", fake_hvac({"url": "https://manager.example.lab"})
    )
    with pytest.raises(CredentialsError, match="password, username"):
        load_credentials()


def test_a_trailing_slash_in_the_url_is_removed(monkeypatch, vault_env):
    """Otherwise every path becomes https://manager.lab//dataservice/…"""
    monkeypatch.setattr(
        vault.hvac, "Client", fake_hvac({**SECRET, "url": "  https://manager.example.lab/  "})
    )
    assert load_credentials().url == "https://manager.example.lab"


def test_repr_does_not_leak_the_password():
    creds = ManagerCredentials(url="https://manager.example.lab", username="a", password="s3cr3t")
    assert "s3cr3t" not in repr(creds)
    assert "s3cr3t" not in str(creds)
    assert "***" in repr(creds)
