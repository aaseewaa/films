"""Схемы для авторизации, профиля, изменения пароля."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Запрос регистрации нового пользователя."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Пароль, минимум 8 символов")
    display_name: str = Field(..., min_length=2, max_length=150, description="Отображаемое имя")
    city: str | None = Field(None, max_length=100, description="Город (для афиши)")
    preferred_language: Literal["ru", "en"] | None = "ru"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Ответ при успешном логине / регистрации."""
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: "UserMe"


class UserMe(BaseModel):
    """Данные о текущем пользователе для /api/auth/me."""
    id: int
    email: str
    display_name: str
    role: str
    avatar_url: str | None = None
    city: str | None = None
    preferred_language: str | None = None
    is_verified: bool = False
    registered_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UpdateProfileRequest(BaseModel):
    """Изменение профиля. Все поля необязательные."""
    display_name: str | None = Field(None, min_length=2, max_length=150)
    city: str | None = Field(None, max_length=100)
    preferred_language: Literal["ru", "en"] | None = None
    avatar_url: str | None = Field(None, max_length=500)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# Forward reference: UserMe должен быть до TokenResponse, но они ссылаются
# друг на друга. Pydantic v2 обновляет автоматически если описаны в одном модуле.
TokenResponse.model_rebuild()
