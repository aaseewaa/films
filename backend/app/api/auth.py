"""
Авторизация: регистрация, логин, профиль, смена пароля.
"""
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.deps import CurrentUser, get_auth_service, require_user
from app.services.auth_service import AuthService
from app.core.security import create_access_token
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserMe,
)
from app.config import settings
from app.services.auth_service import AuthError

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
AVATAR_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _avatar_max_size_label() -> str:
    mb = settings.avatar_max_bytes / (1024 * 1024)
    return f"{int(mb)} MB" if mb.is_integer() else f"{mb:.1f} MB"


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Создаёт нового пользователя и возвращает JWT-токен.
    Email должен быть уникальным, пароль ≥ 8 символов.
    """
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
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Возвращает JWT-токен при успешной проверке email + пароль."""
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
    service: AuthService = Depends(get_auth_service),
) -> UserMe:
    """Профиль текущего пользователя."""
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
    service: AuthService = Depends(get_auth_service),
) -> UserMe:
    """
    Обновить любое из полей профиля. Передавай только те что хочешь поменять.
    """
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
    "/me/avatar",
    response_model=UserMe,
    summary="Загрузить аватар с компьютера",
)
async def upload_avatar(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_user),
    service: AuthService = Depends(get_auth_service),
) -> UserMe:
    """Принимает JPEG/PNG/WebP/GIF, сохраняет в uploads/avatars/."""
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимы только JPEG, PNG, WebP или GIF",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Пустой файл")
    if len(raw) > settings.avatar_max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Файл больше {_avatar_max_size_label()}",
        )

    ext = AVATAR_EXT[file.content_type]
    avatars_dir = Path(settings.uploads_dir) / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    for old in avatars_dir.glob(f"user_{user.id}.*"):
        old.unlink(missing_ok=True)

    filename = f"user_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    dest = avatars_dir / filename
    dest.write_bytes(raw)

    avatar_url = f"/uploads/avatars/{filename}"
    try:
        updated = await service.update_profile(user.id, avatar_url=avatar_url)
    except AuthError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))
    return UserMe(**updated)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Сменить пароль",
)
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser = Depends(require_user),
    service: AuthService = Depends(get_auth_service),
) -> None:
    """Требует знания старого пароля для безопасности."""
    try:
        await service.change_password(
            user.id, old_password=body.old_password, new_password=body.new_password,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
