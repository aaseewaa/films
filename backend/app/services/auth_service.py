"""
Сервис авторизации: регистрация, логин, профиль.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password


class AuthError(Exception):
    """Ошибки уровня бизнес-логики авторизации."""
    pass


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        city: str | None = None,
        preferred_language: str = "ru",
    ) -> dict:
        """
        Зарегистрировать нового пользователя. Возвращает данные созданного
        пользователя готовые для UserMe схемы.
        """
        # Проверка что email свободен
        existing = await self.db.execute(
            text("SELECT id FROM app_user WHERE email = :email"),
            {"email": email},
        )
        if existing.first():
            raise AuthError("Пользователь с таким email уже существует")

        # role_id — берём 'user' (обычный пользователь)
        role_row = await self.db.execute(
            text("SELECT id FROM app_role WHERE code = 'user'")
        )
        role_id = role_row.scalar_one_or_none()
        if role_id is None:
            # Если нет роли user — создадим её, чтобы регистрация работала
            await self.db.execute(text("""
                INSERT INTO app_role (code, name, description, priority)
                VALUES ('user', 'Пользователь', 'Обычный пользователь', 100)
                ON CONFLICT (code) DO NOTHING
            """))
            role_id = (await self.db.execute(
                text("SELECT id FROM app_role WHERE code = 'user'")
            )).scalar_one()

        lang_row = await self.db.execute(
            text("SELECT id FROM language WHERE code = :code"),
            {"code": preferred_language},
        )
        lang_id = lang_row.scalar_one_or_none()

        extra: dict = {}
        if city:
            extra["city"] = city.strip()

        try:
            new_id = (await self.db.execute(
                text("""
                    INSERT INTO app_user
                        (role_id, email, password_hash, display_name,
                         preferred_language_id, extra_metadata)
                    VALUES (:role_id, :email, :pwd, :name, :lang_id,
                            CAST(:extra AS jsonb))
                    RETURNING id
                """),
                {
                    "role_id": role_id,
                    "email": email.lower().strip(),
                    "pwd": hash_password(password),
                    "name": display_name.strip(),
                    "lang_id": lang_id,
                    "extra": json.dumps(extra),
                },
            )).scalar_one()
        except IntegrityError:
            await self.db.rollback()
            raise AuthError("Пользователь с таким email уже существует")

        await self.db.commit()
        return await self.get_me(new_id)

    async def login(self, *, email: str, password: str) -> dict:
        """Проверить пароль и вернуть данные пользователя."""
        sql = text("""
            SELECT u.id, u.email::text AS email, u.password_hash, u.display_name,
                   u.is_active, u.is_verified, u.preferred_language_id,
                   u.avatar_url, u.registered_at, u.extra_metadata,
                   r.code::text AS role
            FROM app_user u
            JOIN app_role r ON r.id = u.role_id
            WHERE u.email = :email
        """)
        row = (await self.db.execute(sql, {"email": email.lower().strip()})).mappings().first()

        if not row:
            raise AuthError("Неверный email или пароль")
        if not row["is_active"]:
            raise AuthError("Аккаунт деактивирован")
        if not verify_password(password, row["password_hash"]):
            raise AuthError("Неверный email или пароль")

        # Обновляем last_login_at
        await self.db.execute(
            text("UPDATE app_user SET last_login_at = now() WHERE id = :id"),
            {"id": row["id"]},
        )
        await self.db.commit()

        return await self.get_me(row["id"])

    async def get_me(self, user_id: int) -> dict:
        """Возвращает полный профиль пользователя для UserMe-схемы."""
        sql = text("""
            SELECT u.id, u.email::text AS email, u.display_name, u.avatar_url,
                   u.is_verified, u.registered_at, u.extra_metadata,
                   r.code::text AS role,
                   l.code AS preferred_language
            FROM app_user u
            JOIN app_role r ON r.id = u.role_id
            LEFT JOIN language l ON l.id = u.preferred_language_id
            WHERE u.id = :id
        """)
        row = (await self.db.execute(sql, {"id": user_id})).mappings().first()
        if not row:
            raise AuthError("Пользователь не найден")

        extra = row["extra_metadata"] or {}
        return {
            "id": row["id"],
            "email": row["email"],
            "display_name": row["display_name"],
            "role": row["role"],
            "avatar_url": row["avatar_url"],
            "city": extra.get("city"),
            "preferred_language": row["preferred_language"],
            "is_verified": row["is_verified"],
            "registered_at": row["registered_at"],
        }

    async def update_profile(
        self,
        user_id: int,
        *,
        display_name: str | None = None,
        city: str | None = None,
        preferred_language: str | None = None,
        avatar_url: str | None = None,
    ) -> dict:
        """Обновить профиль. Передавай только те поля что хочешь поменять."""
        # Получаем текущие extra_metadata для merge
        cur = (await self.db.execute(
            text("SELECT extra_metadata FROM app_user WHERE id = :id"),
            {"id": user_id},
        )).mappings().first()
        if not cur:
            raise AuthError("Пользователь не найден")

        extra = dict(cur["extra_metadata"] or {})
        if city is not None:
            if city.strip():
                extra["city"] = city.strip()
            else:
                extra.pop("city", None)

        # Динамически собираем UPDATE с теми полями что переданы
        sets: list[str] = []
        params: dict = {"id": user_id}

        if display_name is not None:
            sets.append("display_name = :display_name")
            params["display_name"] = display_name.strip()

        if avatar_url is not None:
            sets.append("avatar_url = :avatar_url")
            params["avatar_url"] = avatar_url or None

        if preferred_language is not None:
            sets.append(
                "preferred_language_id = (SELECT id FROM language WHERE code = :lang)"
            )
            params["lang"] = preferred_language

        sets.append("extra_metadata = CAST(:extra AS jsonb)")
        params["extra"] = json.dumps(extra)

        sql = f"UPDATE app_user SET {', '.join(sets)} WHERE id = :id"
        await self.db.execute(text(sql), params)
        await self.db.commit()

        return await self.get_me(user_id)

    async def change_password(
        self, user_id: int, *, old_password: str, new_password: str
    ) -> None:
        """Сменить пароль (требует знания старого)."""
        row = (await self.db.execute(
            text("SELECT password_hash FROM app_user WHERE id = :id"),
            {"id": user_id},
        )).mappings().first()
        if not row:
            raise AuthError("Пользователь не найден")

        if not verify_password(old_password, row["password_hash"]):
            raise AuthError("Старый пароль неверен")

        await self.db.execute(
            text("UPDATE app_user SET password_hash = :h WHERE id = :id"),
            {"h": hash_password(new_password), "id": user_id},
        )
        await self.db.commit()
