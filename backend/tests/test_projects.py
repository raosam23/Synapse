"""Unit tests for project CRUD routes."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.routes.projects import (
    create_project,
    delete_project,
    get_all_projects,
    get_project_by_id,
    update_project,
)
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate


def _execute_result(*, scalar: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    return result


def _scalars_result(*, scalars: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars
    return result


def _project(*, owner_id: object, **overrides: object) -> Project:
    values = {
        "id": uuid4(),
        "name": "Synapse v1",
        "requirements": "Paste requirements and get a backlog.",
        "duration_weeks": 8,
        "sprint_length_weeks": 2,
        "status": ProjectStatus.PLANNING,
        "ai_opinion": None,
        "created_by_id": owner_id,
    }
    values.update(overrides)
    return Project(**values)


@pytest.mark.asyncio
async def test_create_project_success(current_user: User) -> None:
    payload = ProjectCreate(
        name="Synapse v1",
        requirements="Paste requirements and get a backlog.",
        duration_weeks=8,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    created_id = uuid4()

    async def fake_refresh(project: object) -> None:
        project.id = created_id

    session.refresh = AsyncMock(side_effect=fake_refresh)

    result = await create_project(payload, session, current_user)

    added = session.add.call_args[0][0]
    assert added.created_by_id == current_user.id
    assert added.sprint_length_weeks == 2
    assert added.ai_opinion is None
    session.commit.assert_awaited_once()
    assert isinstance(result, ProjectRead)
    assert result.id == created_id
    assert result.name == "Synapse v1"
    assert result.duration_weeks == 8
    assert result.status == ProjectStatus.PLANNING
    assert result.created_by_id == current_user.id
    assert result.sprint_length_weeks == 2
    assert result.ai_opinion is None


@pytest.mark.asyncio
async def test_get_all_projects_success(current_user: User) -> None:
    db_projects = [
        _project(owner_id=current_user.id, name="First"),
        _project(owner_id=current_user.id, name="Second"),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(scalars=db_projects))

    result = await get_all_projects(session, current_user)

    session.execute.assert_awaited_once()
    assert len(result) == 2
    assert result[0].id == db_projects[0].id
    assert result[0].name == "First"
    assert result[1].id == db_projects[1].id
    assert result[1].name == "Second"


@pytest.mark.asyncio
async def test_get_project_by_id_success(current_user: User) -> None:
    db_project = _project(owner_id=current_user.id)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_project))

    result = await get_project_by_id(db_project.id, session, current_user)

    session.execute.assert_awaited_once()
    assert result.id == db_project.id
    assert result.name == db_project.name
    assert result.created_by_id == current_user.id


@pytest.mark.asyncio
async def test_get_project_by_id_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await get_project_by_id(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_project_success(current_user: User) -> None:
    db_project = _project(owner_id=current_user.id, name="Old name")
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_project))

    result = await update_project(
        db_project.id,
        ProjectUpdate(name="New name", status=ProjectStatus.ACTIVE),
        session,
        current_user,
    )

    assert db_project.name == "New name"
    assert db_project.status == ProjectStatus.ACTIVE
    session.add.assert_called_once_with(db_project)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()
    assert result.name == "New name"
    assert result.status == ProjectStatus.ACTIVE
    assert result.id == db_project.id


@pytest.mark.asyncio
async def test_update_project_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await update_project(uuid4(), ProjectUpdate(name="Nope"), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_project_success(current_user: User) -> None:
    db_project = _project(owner_id=current_user.id)
    session = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_project))

    result = await delete_project(db_project.id, session, current_user)

    assert result is None
    session.delete.assert_awaited_once_with(db_project)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_project_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await delete_project(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_project_integrity_error_returns_409(current_user: User) -> None:
    db_project = _project(owner_id=current_user.id)
    session = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock(side_effect=IntegrityError("", "", Exception()))
    session.rollback = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_project))

    with pytest.raises(HTTPException) as exc_info:
        await delete_project(db_project.id, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.rollback.assert_awaited_once()


def test_project_update_rejects_null_name() -> None:
    with pytest.raises(ValidationError):
        ProjectUpdate.model_validate({"name": None})


def test_project_update_rejects_null_requirements() -> None:
    with pytest.raises(ValidationError):
        ProjectUpdate.model_validate({"requirements": None})


def test_project_update_rejects_null_duration_weeks() -> None:
    with pytest.raises(ValidationError):
        ProjectUpdate.model_validate({"duration_weeks": None})


def test_project_update_allows_omitted_fields() -> None:
    payload = ProjectUpdate(ai_opinion="Looks feasible.")
    dumped = payload.model_dump(exclude_unset=True)
    assert dumped == {"ai_opinion": "Looks feasible."}
    assert "name" not in dumped
    assert "status" not in dumped
