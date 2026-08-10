import pytest

from app.security import create_access_token, decode_access_token, get_secret_key


def test_get_secret_key_rejects_missing_value(monkeypatch):
    monkeypatch.delenv("DEPOSITA_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="must be configured"):
        get_secret_key()


@pytest.mark.parametrize("secret_key", ["", "   "])
def test_get_secret_key_rejects_empty_or_whitespace_value(monkeypatch, secret_key):
    monkeypatch.setenv("DEPOSITA_SECRET_KEY", secret_key)

    with pytest.raises(RuntimeError, match="must not be empty"):
        get_secret_key()


def test_get_secret_key_rejects_value_shorter_than_32_characters(monkeypatch):
    monkeypatch.setenv("DEPOSITA_SECRET_KEY", "short-secret-key")

    with pytest.raises(RuntimeError, match="at least 32 characters"):
        get_secret_key()


@pytest.mark.parametrize(
    "secret_key",
    [
        "secret",
        "password",
        "changeme",
        "change-me",
        "deposita",
        "your-secret-key",
        "your-secret-key-here",
        "  SeCrEt  ",
    ],
)
def test_get_secret_key_rejects_common_insecure_values(monkeypatch, secret_key):
    monkeypatch.setenv("DEPOSITA_SECRET_KEY", secret_key)

    with pytest.raises(RuntimeError, match="common insecure value"):
        get_secret_key()


def test_valid_secret_key_allows_jwt_creation_and_reading(monkeypatch):
    secret_key = "valid-test-secret-key-with-at-least-32-characters"
    monkeypatch.setenv("DEPOSITA_SECRET_KEY", secret_key)

    assert get_secret_key() == secret_key
    assert decode_access_token(create_access_token("test-user")) == "test-user"
