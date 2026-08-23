"""Security utilities for the application."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

from bcrypt import checkpw, gensalt, hashpw
from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.session import get_session
from app.models import RevokedToken, User

Session = Annotated[AsyncSession, Depends(get_session)]
AccessToken = Annotated[str | None, Cookie(alias="access_token")]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The password to hash.

    Returns:
        The hashed password.
    """
    return hashpw(password.encode("utf-8"), gensalt(settings.SALT_ROUNDS)).decode(
        "utf-8"
    )


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hashed password.

    Args:
        password: The password to verify.
        hashed_password: The hashed password to verify against.

    Returns:
        True if the password is correct, False if password is incorrect.
    """
    return checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict[str, Any]) -> str:
    """Create an access token for the given data.

    Args:
        data: The data to encode in the token.

    Returns:
        The access token.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": str(uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(session: Session, access_token: AccessToken = None) -> User:
    """Decode the JWT token and return the current user information.

    Args:
        session: The database session.
        access_token: The access token to decode.

    Returns:
        The current user information.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        if not access_token:
            raise credentials_exception
        payload = decode_access_token(access_token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise credentials_exception
        try:
            user_uuid = UUID(user_id)
        except ValueError as exc:
            raise credentials_exception from exc
        user_proxy = await session.execute(select(User).where(User.id == user_uuid))
        user = user_proxy.scalar_one_or_none()
        if not user:
            raise credentials_exception
        jti: str | None = payload.get("jti")
        if not jti:
            raise credentials_exception
        revoked_token_proxy = await session.execute(
            select(RevokedToken).where(RevokedToken.jti == jti)
        )
        revoked_token = revoked_token_proxy.scalar_one_or_none()
        if revoked_token:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception from JWTError


def decode_access_token(access_token: str) -> dict[str, Any]:
    """Decode an access token.

    Args:
        access_token: The access token to decode.

    Returns:
        The decoded access token.
    """
    return jwt.decode(
        access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
