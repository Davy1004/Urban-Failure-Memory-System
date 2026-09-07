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
