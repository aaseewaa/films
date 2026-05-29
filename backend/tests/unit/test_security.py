"""Тесты хеширования паролей и JWT (без БД)."""
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    hashed = hash_password("secret-pass-123")
    assert hashed != "secret-pass-123"
    assert verify_password("secret-pass-123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip_uses_config_expire():
    token = create_access_token(user_id=42)
    assert decode_access_token(token) == 42

    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    exp = payload["exp"]
    if isinstance(exp, datetime):
        exp_dt = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
    else:
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
    iat = payload["iat"]
    if isinstance(iat, datetime):
        iat_dt = iat if iat.tzinfo else iat.replace(tzinfo=timezone.utc)
    else:
        iat_dt = datetime.fromtimestamp(iat, tz=timezone.utc)

    delta_minutes = (exp_dt - iat_dt).total_seconds() / 60
    assert abs(delta_minutes - settings.jwt_expire_minutes) < 2


def test_decode_invalid_token_returns_none():
    assert decode_access_token("not-a-jwt") is None
