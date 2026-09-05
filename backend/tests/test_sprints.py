"""Unit tests for sprint routes."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.routes.sprints import (
    create_sprints,
    delete_sprint_by_id,
    get_sprint_by_id,
    get_sprints,
)
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.user import User
from app.schemas.sprint import SprintCreate, SprintRead


def _execute_result(*, scalar: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    return result


def _scalars_result(items: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _project(
    *,
    project_id: UUID | None = None,
    owner_id: UUID | None = None,
    duration_weeks: int = 8,
    sprint_length_weeks: int = 2,
) -> Project:
    return Project(
        id=project_id or uuid4(),
        name="Synapse v1",
        requirements="Build a backlog.",
        duration_weeks=duration_weeks,
        sprint_length_weeks=sprint_length_weeks,
        created_by_id=owner_id or uuid4(),
    )


def _sprint(*, project_id: UUID, **overrides: object) -> Sprint:
    values = {
        "id": uuid4(),
        "project_id": project_id,
        "index": 1,
        "start_date": date(2026, 4, 6),
        "end_date": date(2026, 4, 19),
    }
    values.update(overrides)
    return Sprint(**values)


@pytest.mark.asyncio
async def test_create_sprints_success(current_user: User) -> None:
    project = _project(owner_id=current_user.id)
    payload = SprintCreate(project_id=project.id, start_date=date(2026, 4, 6))
    session = AsyncMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=project))

    result = await create_sprints(payload, session, current_user)

    added = session.add_all.call_args[0][0]
    assert len(added) == 4
    assert [sprint.index for sprint in added] == [1, 2, 3, 4]
    assert added[0].start_date == date(2026, 4, 6)
    assert added[0].end_date == date(2026, 4, 19)
    assert added[1].start_date == date(2026, 4, 20)
    assert added[3].end_date == date(2026, 5, 31)
    assert all(sprint.project_id == project.id for sprint in added)
    session.commit.assert_awaited_once()
    assert len(result) == 4
    assert all(isinstance(sprint, SprintRead) for sprint in result)
    assert result[0].index == 1
    assert result[0].start_date == date(2026, 4, 6)
    assert result[0].end_date == date(2026, 4, 19)


@pytest.mark.asyncio
async def test_create_sprints_missing_project_returns_404(
    current_user: User,
) -> None:
    payload = SprintCreate(project_id=uuid4(), start_date=date(2026, 4, 6))
    session = AsyncMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await create_sprints(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.add_all.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_sprints_duration_shorter_than_sprint_returns_400(
    current_user: User,
) -> None:
    project = _project(
        owner_id=current_user.id, duration_weeks=1, sprint_length_weeks=2
    )
    payload = SprintCreate(project_id=project.id, start_date=date(2026, 4, 6))
    session = AsyncMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=project))

    with pytest.raises(HTTPException) as exc_info:
        await create_sprints(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    session.add_all.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_sprints_duplicate_returns_409(current_user: User) -> None:
    project = _project(owner_id=current_user.id)
    payload = SprintCreate(project_id=project.id, start_date=date(2026, 4, 6))
    session = AsyncMock()
    session.add_all = MagicMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=project))
    session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))

    with pytest.raises(HTTPException) as exc_info:
        await create_sprints(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert exc_info.value.detail == "Sprints already exist for this project"
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_sprints_success(current_user: User) -> None:
    project_id = uuid4()
    sprints = [
        _sprint(project_id=project_id, index=1),
        _sprint(
            project_id=project_id,
            index=2,
            start_date=date(2026, 4, 20),
            end_date=date(2026, 5, 3),
        ),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(items=sprints))

    result = await get_sprints(session, current_user)

    session.execute.assert_awaited_once()
    assert len(result) == 2
    assert result[0].id == sprints[0].id
    assert result[0].index == 1
    assert result[1].index == 2


@pytest.mark.asyncio
async def test_get_sprint_by_id_success(current_user: User) -> None:
    db_sprint = _sprint(project_id=uuid4())
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_sprint))

    result = await get_sprint_by_id(db_sprint.id, session, current_user)

    session.execute.assert_awaited_once()
    assert result.id == db_sprint.id
    assert result.index == db_sprint.index
    assert result.project_id == db_sprint.project_id


@pytest.mark.asyncio
async def test_get_sprint_by_id_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await get_sprint_by_id(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Sprint not found"


@pytest.mark.asyncio
async def test_delete_sprint_success(current_user: User) -> None:
    db_sprint = _sprint(project_id=uuid4())
    session = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_sprint),
            _execute_result(scalar=None),
        ]
    )

    result = await delete_sprint_by_id(db_sprint.id, session, current_user)

    assert result is None
    session.delete.assert_awaited_once_with(db_sprint)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_sprint_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await delete_sprint_by_id(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_sprint_with_tasks_returns_409(current_user: User) -> None:
    db_sprint = _sprint(project_id=uuid4())
    session = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_sprint),
            _execute_result(scalar=uuid4()),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await delete_sprint_by_id(db_sprint.id, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_sprint_integrity_error_returns_409(
    current_user: User,
) -> None:
    db_sprint = _sprint(project_id=uuid4())
    session = AsyncMock()
    session.delete = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_sprint),
            _execute_result(scalar=None),
        ]
    )
    session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception()))

    with pytest.raises(HTTPException) as exc_info:
        await delete_sprint_by_id(db_sprint.id, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.rollback.assert_awaited_once()
