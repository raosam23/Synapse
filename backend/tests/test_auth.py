"""Unit + integration tests for the auth routes (register, login, me)
and the get_current_user dependency."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.routes.auth import get_me, login, register
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.session import get_session
from app.main import app
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead


def _execute_result(*, scalar: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    return result


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success() -> None:
    payload = RegisterRequest(
        email="new.user@example.com", password="supersecret123", name="New User"
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    created_id = uuid4()

    async def fake_refresh(user: object) -> None:
        user.id = created_id

    session.refresh = AsyncMock(side_effect=fake_refresh)

    result = await register(payload, session)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    assert isinstance(result, UserRead)
    assert result.id == created_id
    assert result.email == "new.user@example.com"
    assert result.name == "New User"

    # The stored user must have a real bcrypt hash, not the raw password.
    stored_user: User = session.add.call_args[0][0]
    assert stored_user.password_hash != payload.password
    assert verify_password(payload.password, stored_user.password_hash)


def test_password_too_short() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            email="short.password@example.com",
            password="it",
            name="Short Password User",
        )

    assert exc_info.value.errors()[0]["type"] == "string_too_short"


def test_password_too_long() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            email="long.password@example.com",
            password="abittoomanycharactersthatisgoingtobreakthecodeandthrowanvalidationerrorforsure",
            name="Long Password User",
        )

    assert exc_info.value.errors()[0]["type"] == "string_too_long"


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict() -> None:
    payload = RegisterRequest(email="taken@example.com", password="supersecret123")
    session = AsyncMock()
    session.add = MagicMock()
    session.rollback = AsyncMock()
    session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))

    with pytest.raises(HTTPException) as exc_info:
        await register(payload, session)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_unexpected_error() -> None:
    payload = RegisterRequest(email="broken@example.com", password="supersecret123")
    session = AsyncMock()
    session.add = MagicMock()
    session.rollback = AsyncMock()
    session.commit = AsyncMock(side_effect=RuntimeError("db is on fire"))

    with pytest.raises(HTTPException) as exc_info:
        await register(payload, session)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    session.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success() -> None:
    user_id = uuid4()
    db_user = User(
        id=user_id,
        email="jennie@example.com",
        password_hash=hash_password("correct-password"),
        name="Jennie",
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_user))

    result = await login(
        LoginRequest(email="jennie@example.com", password="correct-password"),
        session,
    )

    assert isinstance(result, TokenResponse)
    assert result.token_type == "bearer"

    decoded = jwt.decode(
        result.access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert decoded["sub"] == str(user_id)


@pytest.mark.asyncio
async def test_login_user_not_found() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await login(
            LoginRequest(email="ghost@example.com", password="whatever123"), session
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_wrong_password() -> None:
    db_user = User(
        id=uuid4(),
        email="jennie@example.com",
        password_hash=hash_password("correct-password"),
        name="Jennie",
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_user))

    with pytest.raises(HTTPException) as exc_info:
        await login(
            LoginRequest(email="jennie@example.com", password="wrong-password"),
            session,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# get_me()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_me_success(current_user: User) -> None:
    result = await get_me(current_user)

    assert isinstance(result, UserRead)
    assert result.id == current_user.id
    assert result.email == current_user.email
    assert result.name == current_user.name


# ---------------------------------------------------------------------------
# Integration tests: real HTTP requests through the FastAPI app, so the
# actual get_current_user dependency (JWT decode + DB lookup) is exercised
# instead of being bypassed like the direct function-call tests above.
# ---------------------------------------------------------------------------


@pytest.fixture
def http_client():
    """A TestClient with get_session overridden so no real DB is needed."""
    mock_session = AsyncMock()

    async def fake_get_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_session

    app.dependency_overrides[get_session] = fake_get_session
    client = TestClient(app)
    yield client, mock_session
    app.dependency_overrides.pop(get_session, None)


def test_protected_route_without_token_returns_401(http_client) -> None:
    client, _ = http_client

    response = client.get("/api/v1/tasks/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_protected_route_with_garbage_token_returns_401(http_client) -> None:
    client, _ = http_client

    response = client.get(
        "/api/v1/tasks/", headers={"Authorization": "Bearer not-a-real-jwt"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"


def test_me_endpoint_with_valid_token_returns_user(http_client) -> None:
    client, mock_session = http_client
    user_id = uuid4()
    db_user = User(
        id=user_id,
        email="valid.user@example.com",
        password_hash="irrelevant-hash",
        name="Valid User",
    )
    mock_session.execute = AsyncMock(return_value=_execute_result(scalar=db_user))

    token = jwt.encode(
        {"sub": str(user_id)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == str(user_id)
    assert body["email"] == "valid.user@example.com"
    assert body["name"] == "Valid User"
