"""Smoke tests that need no database."""
import pytest

from app.core.security import (
    create_access_token, decode_access_token, hash_password, verify_password,
)


def test_password_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_long_password_does_not_crash():
    """bcrypt caps at 72 bytes; we truncate rather than raise."""
    long_pw = "x" * 200
    assert verify_password(long_pw, hash_password(long_pw))


def test_bad_hash_returns_false_not_exception():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_token_roundtrip():
    token = create_access_token(subject="42", role="admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_tampered_token_rejected():
    import jwt
    token = create_access_token(subject="42", role="officer")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "tamper")


# ---------------------------------------------------------------------------
# The production configuration guard.
#
# A deployed instance signing tokens with the placeholder SECRET_KEY would let
# anyone mint an admin token, and the placeholder is committed to a public
# repository in .env.example. The guard raises at import time so the process
# dies on boot; these tests are what stop someone "simplifying" it away.
# ---------------------------------------------------------------------------
import pydantic  # noqa: E402

from app.core.config import DEFAULT_SECRET, Settings  # noqa: E402

GOOD_SECRET = "s" * 48


def _settings(**kw):
    """Build Settings from explicit values only.

    `_env_file=None` matters: without it pydantic-settings reads the developer's
    real .env, which has a valid SECRET_KEY, and every one of these tests passes
    for the wrong reason.
    """
    base = {"environment": "production", "debug": False, "secret_key": GOOD_SECRET}
    return Settings(_env_file=None, **{**base, **kw})


def test_production_boots_with_a_real_secret():
    s = _settings()
    assert s.is_production


def test_production_refuses_the_placeholder_secret():
    with pytest.raises(pydantic.ValidationError, match="placeholder"):
        _settings(secret_key=DEFAULT_SECRET)


def test_production_refuses_a_short_secret():
    with pytest.raises(pydantic.ValidationError, match="at least 32"):
        _settings(secret_key="short")


def test_production_refuses_debug():
    with pytest.raises(pydantic.ValidationError, match="DEBUG"):
        _settings(debug=True)


def test_development_is_left_alone():
    """`docker compose up` and `uvicorn` must work with no configuration."""
    s = Settings(_env_file=None, environment="development", debug=True,
                 secret_key=DEFAULT_SECRET)
    assert not s.is_production
    assert s.secret_key == DEFAULT_SECRET
