"""
Авторизация: регистрация, логин, профиль, смена пароля.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_user
from app.core.security import create_access_token
from app.database import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserMe,
)
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Создаёт нового пользователя и возвращает JWT-токен.
    Email должен быть уникальным, пароль ≥ 8 символов.
    """
    service = AuthService(db)
    try:
        user = await service.register(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            city=body.city,
            preferred_language=body.preferred_language or "ru",
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    token = create_access_token(user_id=user["id"])
    return TokenResponse(access_token=token, user=UserMe(**user))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Логин",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Возвращает JWT-токен при успешной проверке email + пароль."""
    service = AuthService(db)
    try:
        user = await service.login(email=body.email, password=body.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    token = create_access_token(user_id=user["id"])
    return TokenResponse(access_token=token, user=UserMe(**user))


@router.get(
    "/me",
    response_model=UserMe,
    summary="Текущий пользователь",
)
async def get_me(
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> UserMe:
    """Профиль текущего пользователя."""
    service = AuthService(db)
    full = await service.get_me(user.id)
    return UserMe(**full)


@router.put(
    "/me",
    response_model=UserMe,
    summary="Обновить профиль",
)
async def update_me(
    body: UpdateProfileRequest,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> UserMe:
    """
    Обновить любое из полей профиля. Передавай только те что хочешь поменять.
    """
    service = AuthService(db)
    try:
        updated = await service.update_profile(
            user.id,
            display_name=body.display_name,
            city=body.city,
            preferred_language=body.preferred_language,
            avatar_url=body.avatar_url,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return UserMe(**updated)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Сменить пароль",
)
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Требует знания старого пароля для безопасности."""
    service = AuthService(db)
    try:
        await service.change_password(
            user.id, old_password=body.old_password, new_password=body.new_password,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
