"""Unit tests for task CRUD routes."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.routes.tasks import (
    create_task,
    delete_task,
    get_all_tasks,
    get_task_by_id,
    update_task,
)
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate


@pytest.mark.asyncio
async def test_create_task_success_without_assignee(current_user: User) -> None:
    payload = TaskCreate(
        title="Write unit tests",
        description="Write unit tests for the task",
        status=TaskStatus.BACKLOG,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    created_id = uuid4()

    async def fake_refresh(task: object) -> None:
        task.id = created_id

    session.refresh = AsyncMock(side_effect=fake_refresh)

    result = await create_task(payload, session, current_user)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    assert isinstance(result, TaskRead)
    assert result.title == "Write unit tests"
    assert result.description == "Write unit tests for the task"
    assert result.status == TaskStatus.BACKLOG
    assert result.id == created_id
    assert result.assignee_id is None


def _execute_result(*, scalar: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    return result


@pytest.mark.asyncio
async def test_create_task_assignee_not_found(current_user: User) -> None:
    payload = TaskCreate(
        title="Write unit tests",
        description="Write unit tests for the task",
        status=TaskStatus.BACKLOG,
        assignee_id=uuid4(),
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await create_task(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.add.assert_not_called()
    session.commit.assert_not_called()


def _scalars_result(items: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


@pytest.mark.asyncio
async def test_get_all_tasks_success(current_user: User) -> None:
    tasks = [
        Task(
            id=uuid4(),
            title="Write unit tests",
            description="Write unit tests for the task",
            status=TaskStatus.TODO,
        ),
        Task(
            id=uuid4(),
            title="Refactor code",
            description="Refactor code for the task",
            status=TaskStatus.BACKLOG,
        ),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(items=tasks))

    result = await get_all_tasks(session, current_user)

    session.execute.assert_called_once()
    assert len(result) == 2
    assert all(isinstance(task, TaskRead) for task in result)
    assert result[0].title == "Write unit tests"
    assert result[0].description == "Write unit tests for the task"
    assert result[0].status == TaskStatus.TODO
    assert result[1].title == "Refactor code"
    assert result[1].description == "Refactor code for the task"
    assert result[1].status == TaskStatus.BACKLOG


@pytest.mark.asyncio
async def test_get_all_tasks_no_tasks(current_user: User) -> None:
    tasks = [
        Task(
            id=uuid4(),
            title="Write unit tests",
            description="Write unit tests for the task",
            status=TaskStatus.TODO,
        ),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(items=tasks))

    result = await get_all_tasks(session, current_user, status_filter=TaskStatus.TODO)

    session.execute.assert_awaited_once()
    assert len(result) == 1
    assert result[0].status == TaskStatus.TODO


@pytest.mark.asyncio
async def test_get_task_by_id_success(current_user: User) -> None:
    task_id = uuid4()
    db_task = Task(
        id=task_id,
        title="Write unit tests",
        description="Write unit tests for the task",
        status=TaskStatus.TODO,
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_task))

    result = await get_task_by_id(db_task.id, session, current_user)

    session.execute.assert_awaited_once()
    assert result.id == task_id
    assert result.title == "Write unit tests"
    assert result.description == "Write unit tests for the task"
    assert result.status == TaskStatus.TODO


@pytest.mark.asyncio
async def test_get_task_by_id_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await get_task_by_id(uuid4(), session, current_user)

    session.execute.assert_awaited_once()
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_task_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await delete_task(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_task_success(current_user: User) -> None:
    task_id = uuid4()
    db_task = Task(
        id=task_id,
        title="Write unit tests",
        description="Write unit tests for the task",
        status=TaskStatus.TODO,
    )
    session = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_task))

    result = await delete_task(task_id, session, current_user)

    assert result is None
    session.delete.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_task_conflict_when_dependencies_exist(current_user: User) -> None:
    task_id = uuid4()
    db_task = Task(
        id=task_id,
        title="Write unit tests",
        status=TaskStatus.TODO,
    )
    session = AsyncMock()
    session.delete = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_task))
    session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))

    with pytest.raises(HTTPException) as exc_info:
        await delete_task(task_id, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_task_success(current_user: User) -> None:
    task_id = uuid4()
    db_task = Task(id=task_id, title="Old", status=TaskStatus.BACKLOG)
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_task))

    result = await update_task(
        task_id, TaskUpdate(title="New", status=TaskStatus.TODO), session, current_user
    )

    assert db_task.title == "New"
    assert db_task.status == TaskStatus.TODO
    session.add.assert_called_once_with(db_task)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()
    assert result.title == "New"
    assert result.status == TaskStatus.TODO
    assert result.id == task_id


@pytest.mark.asyncio
async def test_update_task_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await update_task(uuid4(), TaskUpdate(title="Nope"), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_update_task_assignee_not_found(current_user: User) -> None:
    task_id = uuid4()
    db_task = Task(id=task_id, title="Old", status=TaskStatus.BACKLOG)
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_task),
            _execute_result(scalar=None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_task(
            task_id, TaskUpdate(assignee_id=uuid4()), session, current_user
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.commit.assert_not_called()


def test_task_update_rejects_null_title() -> None:
    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({"title": None})


def test_task_update_rejects_null_status() -> None:
    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({"status": None})


def test_task_update_allows_omitted_title_and_status() -> None:
    payload = TaskUpdate(description="only this")
    dumped = payload.model_dump(exclude_unset=True)
    assert dumped == {"description": "only this"}
    assert "title" not in dumped
    assert "status" not in dumped
