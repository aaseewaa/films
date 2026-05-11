"""
Безопасность: хеширование паролей (bcrypt) и JWT-токены.

Использование:
    from app.core.security import hash_password, verify_password, create_access_token

    # При регистрации:
    h = hash_password("plain_text")
    # сохраняем h в БД

    # При логине:
    if verify_password("plain_text", user.password_hash):
        token = create_access_token(user_id=user.id)

    # При защищённых эндпоинтах:
    user_id = decode_access_token(token)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# bcrypt — стандарт хеширования паролей. Медленный нарочно — защищает от
# brute-force атак. ~0.3 сек на хеш — это нормально.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# JWT-настройки. Секрет берём из .env, чтобы можно было подменить
# в продакшене. Для дипломного проекта подойдёт любая случайная строка.
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 24 * 7  # неделя — пользователь не должен заново логиниться часто


def hash_password(plain: str) -> str:
    """Хешировать пароль для хранения в БД."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Проверить что введённый пароль соответствует хешу."""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(*, user_id: int, extra: dict[str, Any] | None = None) -> str:
    """
    Создать JWT токен.

    `sub` (subject) — стандартное поле JWT для идентификатора пользователя.
    `exp` — время истечения. После этой даты токен невалиден.
    """
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_HOURS),
    }
    if extra:
        payload.update(extra)

    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """
    Раскодировать токен. Возвращает user_id или None если токен невалидный
    (истёк, подделан, испорчен).
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub)
    except (JWTError, ValueError):
        return None
