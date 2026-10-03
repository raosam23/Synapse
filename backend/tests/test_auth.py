"""Unit + integration tests for the auth routes (register, login, logout, me)
and the get_current_user dependency."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.routes.auth import get_me, login, logout, register
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.main import app
from app.models import RevokedToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead


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
    response = MagicMock()

    result = await register(payload, session, response)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    assert isinstance(result, UserRead)
    assert result.id == created_id
    assert result.email == "new.user@example.com"
    assert result.name == "New User"
    response.set_cookie.assert_called_once()

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
    response = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await register(payload, session, response)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.rollback.assert_awaited_once()
    response.set_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_register_unexpected_error() -> None:
    payload = RegisterRequest(email="broken@example.com", password="supersecret123")
    session = AsyncMock()
    session.add = MagicMock()
    session.rollback = AsyncMock()
    session.commit = AsyncMock(side_effect=RuntimeError("db is on fire"))
    response = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await register(payload, session, response)

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
        email="example_name@example.com",
        password_hash=hash_password("correct-password"),
        name="Jennie",
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_user))
    response = MagicMock()

    result = await login(
        LoginRequest(email="example_name@example.com", password="correct-password"),
        session,
        response,
    )

    assert isinstance(result, UserRead)
    assert result.id == user_id
    assert result.email == "example_name@example.com"

    response.set_cookie.assert_called_once()
    cookie_kwargs = response.set_cookie.call_args.kwargs
    assert cookie_kwargs["key"] == "access_token"
    assert cookie_kwargs["httponly"] is True

    decoded = jwt.decode(
        cookie_kwargs["value"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert decoded["sub"] == str(user_id)


@pytest.mark.asyncio
async def test_login_user_not_found() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))
    response = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await login(
            LoginRequest(email="ghost@example.com", password="whatever123"),
            session,
            response,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    response.set_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_login_wrong_password() -> None:
    db_user = User(
        id=uuid4(),
        email="example_name@example.com",
        password_hash=hash_password("correct-password"),
        name="Jennie",
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_user))
    response = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await login(
            LoginRequest(email="example_name@example.com", password="wrong-password"),
            session,
            response,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    response.set_cookie.assert_not_called()


# ---------------------------------------------------------------------------
# logout()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_without_token_returns_401() -> None:
    session = AsyncMock()
    response = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await logout(session, response)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    session.execute.assert_not_called()
    session.commit.assert_not_called()
    response.delete_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_logout_with_garbage_token_returns_401() -> None:
    session = AsyncMock()
    response = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await logout(session, response, "not-a-real-jwt")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    session.commit.assert_not_called()
    response.delete_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_logout_success() -> None:
    user_id = uuid4()
    token = create_access_token({"sub": str(user_id)})
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    response = MagicMock()

    result = await logout(session, response, token)

    assert result is None

    # Lazy-delete of expired blocklist rows must run before the new row is added.
    session.execute.assert_awaited_once()
    session.add.assert_called_once()

    stored_revoked_token: RevokedToken = session.add.call_args[0][0]
    assert stored_revoked_token.jti == decoded["jti"]
    # expires_at is stored as a naive UTC datetime (the DB column is
    # TIMESTAMP WITHOUT TIME ZONE), so tzinfo must be stripped to match.
    assert stored_revoked_token.expires_at == datetime.fromtimestamp(
        decoded["exp"], UTC
    ).replace(tzinfo=None)

    session.commit.assert_awaited_once()
    response.delete_cookie.assert_called_once_with("access_token")


@pytest.mark.asyncio
async def test_logout_twice_with_same_token_returns_401() -> None:
    """The second /logout call with an already-revoked jti hits the
    RevokedToken primary-key uniqueness constraint (IntegrityError) instead
    of crashing with a 500."""
    token = create_access_token({"sub": str(uuid4())})

    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))
    session.rollback = AsyncMock()
    response = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await logout(session, response, token)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    session.rollback.assert_awaited_once()
    response.delete_cookie.assert_not_called()


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

    response = client.get("/api/v1/tasks/", cookies={"access_token": "not-a-real-jwt"})

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
    # get_current_user makes two DB calls: one to load the User (by sub),
    # then one to check the RevokedToken blocklist (by jti). The second
    # must resolve to "no row found" so the token isn't treated as revoked.
    mock_session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_user),
            _execute_result(scalar=None),
        ]
    )

    token = jwt.encode(
        {"sub": str(user_id), "jti": str(uuid4())},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = client.get("/api/v1/auth/me", cookies={"access_token": token})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == str(user_id)
    assert body["email"] == "valid.user@example.com"
    assert body["name"] == "Valid User"


def test_logout_endpoint_revokes_token_and_clears_cookie(http_client) -> None:
    client, mock_session = http_client
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    token = create_access_token({"sub": str(uuid4())})

    response = client.post("/api/v1/auth/logout", cookies={"access_token": token})

    assert response.status_code == status.HTTP_200_OK
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()

    set_cookie_header = response.headers["set-cookie"]
    assert 'access_token=""' in set_cookie_header
    assert "Max-Age=0" in set_cookie_header


def test_logout_endpoint_without_token_returns_401(http_client) -> None:
    client, _ = http_client

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_endpoint_twice_with_same_token_returns_401(http_client) -> None:
    client, mock_session = http_client
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))
    mock_session.rollback = AsyncMock()

    token = create_access_token({"sub": str(uuid4())})

    response = client.post("/api/v1/auth/logout", cookies={"access_token": token})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    mock_session.rollback.assert_awaited_once()
