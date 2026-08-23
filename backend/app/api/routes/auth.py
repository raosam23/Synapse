"""Routes for the authentication API."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from app.core.config import settings
from app.core.security import (
    AccessToken,
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_session
from app.models import RevokedToken, User
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest, session: Session, response: Response
) -> UserRead:
    """
    Register a new user
    Args:
        request: RegisterRequest
        session: Session
    Returns:
        UserRead: The registered user
    Raises:
        HTTPException: If the email is already registered or an unexpected error occurs
    """
    try:
        user = User(
            email=request.email,
            password_hash=hash_password(request.password),
            name=request.name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        access_token = create_access_token({"sub": str(user.id)})
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return UserRead.model_validate(user)
    except IntegrityError as integ_err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from integ_err
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from exc


@router.post("/login", response_model=UserRead, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest, session: Session, response: Response
) -> UserRead:
    """
    Endpoint for user login
    Args:
        request: LoginRequest
        session: Session
        response: Response
    Returns:
        UserRead: The current user
    Raises:
        HTTPException: If the email or password is incorrect
    """
    user_proxy = await session.execute(select(User).where(User.email == request.email))
    user = user_proxy.scalar_one_or_none()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    session: Session, response: Response, access_token: AccessToken = None
) -> None:
    """
    Endpoint for user logout
    Args:
        session: Session
        response: Response
        access_token: AccessToken
    Returns:
        None
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    try:
        payload = decode_access_token(access_token)
    except JWTError as jwt_error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        ) from jwt_error
    jti = payload.get("jti")
    exp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp, UTC).replace(tzinfo=None)
    await session.execute(
        delete(RevokedToken).where(
            RevokedToken.expires_at < datetime.now(UTC).replace(tzinfo=None)
        )
    )
    revoked_token = RevokedToken(
        jti=jti,
        expires_at=expires_at,
    )
    try:
        session.add(revoked_token)
        await session.commit()
    except IntegrityError as integ_err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        ) from integ_err
    response.delete_cookie("access_token")


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_me(current_user: CurrentUser) -> UserRead:
    """
    Get the current user
    Args:
        current_user: CurrentUser
    Returns:
        UserRead: The current user
    """
    return UserRead.model_validate(current_user)
