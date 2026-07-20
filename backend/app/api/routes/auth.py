from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import current_user_dependency, user_repository_dependency
from app.domain.auth.repository import UserRepository
from app.domain.auth.service import (
    AuthService,
    DuplicateUserError,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.models.user import User
from app.schemas.auth import RefreshTokenRequest, TokenPair, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def read_user(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    users: Annotated[UserRepository, Depends(user_repository_dependency)],
) -> UserRead:
    try:
        user = await AuthService(users).register(payload)
    except DuplicateUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from exc

    return read_user(user)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: UserLogin,
    users: Annotated[UserRepository, Depends(user_repository_dependency)],
) -> TokenPair:
    try:
        return await AuthService(users).login(payload)
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshTokenRequest,
    users: Annotated[UserRepository, Depends(user_repository_dependency)],
) -> TokenPair:
    try:
        return await AuthService(users).refresh(payload.refresh_token)
    except (jwt.PyJWTError, InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc


@router.get("/me", response_model=UserRead)
async def me(
    current_user: Annotated[User, Depends(current_user_dependency)],
) -> UserRead:
    return read_user(current_user)

