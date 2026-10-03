"""Unit tests for comment CRUD routes."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.api.routes.comments import (
    create_comment,
    delete_comment_by_id,
    get_all_comments,
    get_comment_by_id,
    update_comment_by_id,
)
from app.models.comment import Comment
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead, CommentUpdate


def _execute_result(*, scalar: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    return result


def _scalars_result(items: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _task(*, task_id: UUID | None = None, **overrides: object) -> Task:
    values = {
        "id": task_id or uuid4(),
        "title": "Write unit tests",
        "status": TaskStatus.BACKLOG,
        "project_id": uuid4(),
    }
    values.update(overrides)
    return Task(**values)


def _comment(*, task_id: UUID | None = None, **overrides: object) -> Comment:
    now = datetime(2026, 4, 6, 12, 0, 0)  # noqa: DTZ001 — column is TIMESTAMP WITHOUT TIME ZONE
    values = {
        "id": uuid4(),
        "task_id": task_id or uuid4(),
        "body": "Looks good.",
        "user_id": uuid4(),
        "is_ai": False,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return Comment(**values)


@pytest.mark.asyncio
async def test_create_comment_success(current_user: User) -> None:
    task = _task()
    payload = CommentCreate(task_id=task.id, body="Looks good.")
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=task))
    created_id = uuid4()

    async def fake_refresh(comment: object) -> None:
        comment.id = created_id

    session.refresh = AsyncMock(side_effect=fake_refresh)

    result = await create_comment(payload, session, current_user)

    added = session.add.call_args[0][0]
    assert added.task_id == task.id
    assert added.body == "Looks good."
    assert added.user_id == current_user.id
    assert added.is_ai is False
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()
    assert isinstance(result, CommentRead)
    assert result.id == created_id
    assert result.task_id == task.id
    assert result.body == "Looks good."
    assert result.user_id == current_user.id
    assert result.is_ai is False


@pytest.mark.asyncio
async def test_create_comment_missing_task_returns_404(current_user: User) -> None:
    payload = CommentCreate(task_id=uuid4(), body="Looks good.")
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await create_comment(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Task not found"
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_all_comments_success(current_user: User) -> None:
    task_id = uuid4()
    comments = [
        _comment(task_id=task_id, body="Newer comment"),
        _comment(task_id=task_id, body="Older comment"),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(items=comments))

    result = await get_all_comments(session, current_user)

    session.execute.assert_awaited_once()
    assert len(result) == 2
    assert all(isinstance(comment, CommentRead) for comment in result)
    assert result[0].body == "Newer comment"
    assert result[1].body == "Older comment"


@pytest.mark.asyncio
async def test_get_all_comments_filter_by_task(current_user: User) -> None:
    task_id = uuid4()
    comments = [_comment(task_id=task_id, body="On this task")]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(items=comments))

    result = await get_all_comments(session, current_user, task_id_filter=task_id)

    session.execute.assert_awaited_once()
    assert len(result) == 1
    assert result[0].task_id == task_id
    assert result[0].body == "On this task"


@pytest.mark.asyncio
async def test_get_all_comments_unknown_task_returns_empty(
    current_user: User,
) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(items=[]))

    result = await get_all_comments(session, current_user, task_id_filter=uuid4())

    session.execute.assert_awaited_once()
    assert result == []


@pytest.mark.asyncio
async def test_get_comment_by_id_success(current_user: User) -> None:
    db_comment = _comment(body="Looks good.")
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_comment))

    result = await get_comment_by_id(db_comment.id, session, current_user)

    session.execute.assert_awaited_once()
    assert result.id == db_comment.id
    assert result.body == "Looks good."
    assert result.task_id == db_comment.task_id


@pytest.mark.asyncio
async def test_get_comment_by_id_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await get_comment_by_id(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Comment not found"


@pytest.mark.asyncio
async def test_update_comment_success(current_user: User) -> None:
    db_comment = _comment(body="Old body")
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_comment))

    result = await update_comment_by_id(
        db_comment.id, CommentUpdate(body="New body"), session, current_user
    )

    assert db_comment.body == "New body"
    session.add.assert_called_once_with(db_comment)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()
    assert result.body == "New body"
    assert result.id == db_comment.id


@pytest.mark.asyncio
async def test_update_comment_omitted_body_leaves_body_unchanged(
    current_user: User,
) -> None:
    db_comment = _comment(body="Keep me")
    original_updated_at = db_comment.updated_at
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_comment))

    result = await update_comment_by_id(
        db_comment.id, CommentUpdate(), session, current_user
    )

    assert db_comment.body == "Keep me"
    assert db_comment.updated_at != original_updated_at
    assert result.body == "Keep me"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_comment_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await update_comment_by_id(
            uuid4(), CommentUpdate(body="Nope"), session, current_user
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Comment not found"
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_comment_success(current_user: User) -> None:
    db_comment = _comment()
    session = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_comment))

    result = await delete_comment_by_id(db_comment.id, session, current_user)

    assert result is None
    session.delete.assert_awaited_once_with(db_comment)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_comment_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await delete_comment_by_id(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Comment not found"
    session.delete.assert_not_called()


def test_comment_update_rejects_null_body() -> None:
    with pytest.raises(ValidationError):
        CommentUpdate.model_validate({"body": None})


def test_comment_update_rejects_empty_body() -> None:
    with pytest.raises(ValidationError):
        CommentUpdate.model_validate({"body": ""})


def test_comment_update_allows_omitted_body() -> None:
    payload = CommentUpdate()
    dumped = payload.model_dump(exclude_unset=True)
    assert dumped == {}
    assert "body" not in dumped


def test_comment_create_rejects_empty_body() -> None:
    with pytest.raises(ValidationError):
        CommentCreate.model_validate({"task_id": str(uuid4()), "body": ""})
