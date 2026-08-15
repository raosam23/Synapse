"""Unit tests for task dependency CRUD routes (mocked session)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.routes.task_dependencies import (
    create_task_dependency,
    delete_task_dependency,
    get_all_task_dependencies,
    get_task_dependency_by_id,
)
from app.models.task import Task, TaskStatus
from app.models.task_dependency import TaskDependency
from app.schemas.task_dependency import TaskDependencyCreate, TaskDependencyRead


def _execute_result(*, scalar: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    return result


def _scalars_result(items: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


@pytest.mark.asyncio
async def test_create_task_dependency_success() -> None:
    from_id = uuid4()
    to_id = uuid4()
    created_id = uuid4()
    from_task = Task(id=from_id, title="A", status=TaskStatus.BACKLOG)
    to_task = Task(id=to_id, title="B", status=TaskStatus.TODO)

    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=from_task),
            _execute_result(scalar=to_task),
        ]
    )

    async def fake_refresh(dep: object) -> None:
        dep.id = created_id

    session.refresh = AsyncMock(side_effect=fake_refresh)

    result = await create_task_dependency(
        TaskDependencyCreate(from_task_id=from_id, to_task_id=to_id),
        session,
    )

    assert session.execute.await_count == 2
    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    assert isinstance(result, TaskDependencyRead)
    assert result.from_task_id == from_id
    assert result.to_task_id == to_id
    assert result.id == created_id


@pytest.mark.asyncio
async def test_create_task_dependency_task_not_found() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await create_task_dependency(
            TaskDependencyCreate(from_task_id=uuid4(), to_task_id=uuid4()),
            session,
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_task_dependency_duplicate_conflict() -> None:
    from_id = uuid4()
    to_id = uuid4()
    session = AsyncMock()
    session.add = MagicMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(
                scalar=Task(id=from_id, title="A", status=TaskStatus.BACKLOG)
            ),
            _execute_result(scalar=Task(id=to_id, title="B", status=TaskStatus.TODO)),
        ]
    )
    session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))

    with pytest.raises(HTTPException) as exc_info:
        await create_task_dependency(
            TaskDependencyCreate(from_task_id=from_id, to_task_id=to_id),
            session,
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.rollback.assert_awaited_once()


def test_create_task_dependency_self_link_rejected() -> None:
    same_id = uuid4()
    with pytest.raises(ValidationError):
        TaskDependencyCreate(from_task_id=same_id, to_task_id=same_id)


@pytest.mark.asyncio
async def test_get_all_task_dependencies_success() -> None:
    from_id = uuid4()
    to_id = uuid4()
    deps = [
        TaskDependency(id=uuid4(), from_task_id=from_id, to_task_id=to_id),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(deps))

    result = await get_all_task_dependencies(session)

    session.execute.assert_awaited_once()
    assert len(result) == 1
    assert result[0].from_task_id == from_id
    assert result[0].to_task_id == to_id


@pytest.mark.asyncio
async def test_get_all_task_dependencies_with_filters() -> None:
    from_id = uuid4()
    to_id = uuid4()
    deps = [TaskDependency(id=uuid4(), from_task_id=from_id, to_task_id=to_id)]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(deps))

    result = await get_all_task_dependencies(
        session, from_task_id=from_id, to_task_id=to_id
    )

    session.execute.assert_awaited_once()
    assert len(result) == 1
    assert result[0].from_task_id == from_id


@pytest.mark.asyncio
async def test_get_task_dependency_by_id_success() -> None:
    dep_id = uuid4()
    from_id = uuid4()
    to_id = uuid4()
    db_dep = TaskDependency(id=dep_id, from_task_id=from_id, to_task_id=to_id)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_dep))

    result = await get_task_dependency_by_id(dep_id, session)

    session.execute.assert_awaited_once()
    assert result.id == dep_id
    assert result.from_task_id == from_id


@pytest.mark.asyncio
async def test_get_task_dependency_by_id_not_found() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await get_task_dependency_by_id(uuid4(), session)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_task_dependency_success() -> None:
    dep_id = uuid4()
    db_dep = TaskDependency(id=dep_id, from_task_id=uuid4(), to_task_id=uuid4())
    session = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_dep))

    result = await delete_task_dependency(dep_id, session)

    assert result is None
    session.delete.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_task_dependency_not_found() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await delete_task_dependency(uuid4(), session)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.delete.assert_not_called()
