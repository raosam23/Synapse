"""Unit tests for team members CRUD routes"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.routes.team_members import (
    create_team_member,
    delete_team_member,
    get_team_member,
    get_team_members,
    update_team_member,
)
from app.models.project import Project
from app.models.team_member import TeamMember
from app.models.user import User
from app.schemas.team_member import TeamMemberCreate, TeamMemberRead, TeamMemberUpdate


def _execute_result(*, scalar: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    return result


def _rows_result(rows: list[tuple[object, object]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


def _project(
    *, project_id: UUID | None = None, owner_id: UUID | None = None
) -> Project:
    return Project(
        id=project_id or uuid4(),
        name="Synapse v1",
        requirements="Build a backlog.",
        duration_weeks=8,
        created_by_id=owner_id or uuid4(),
    )


def _member(*, user_id: UUID, project_id: UUID, **overrides: object) -> TeamMember:
    values = {
        "id": uuid4(),
        "skills": ["Python"],
        "user_id": user_id,
        "project_id": project_id,
    }
    values.update(overrides)
    return TeamMember(**values)


def _linked_user(member: TeamMember, *, name: str | None, email: str) -> User:
    return User(
        id=member.user_id,
        email=email,
        password_hash="not-a-real-hash",
        name=name,
    )


@pytest.mark.asyncio
async def test_create_team_member_success(current_user: User) -> None:
    """Test creating a team member successfully"""
    project = _project(owner_id=current_user.id)
    payload = TeamMemberCreate(
        skills=["Python", "SQL", "Docker"],
        user_id=current_user.id,
        project_id=project.id,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=current_user),
            _execute_result(scalar=project),
            _execute_result(scalar=None),
        ]
    )

    created_id = uuid4()

    async def fake_refresh(member: object) -> None:
        member.id = created_id

    session.refresh.side_effect = fake_refresh

    result = await create_team_member(payload, session, current_user)

    added = session.add.call_args[0][0]
    assert added.project_id == project.id
    session.commit.assert_awaited_once()
    assert isinstance(result, TeamMemberRead)
    assert result.id == created_id
    assert result.name == current_user.name
    assert result.skills == ["Python", "SQL", "Docker"]
    assert result.user_id == current_user.id
    assert result.project_id == project.id


@pytest.mark.asyncio
async def test_create_team_member_display_name_falls_back_to_email(
    current_user: User,
) -> None:
    nameless = User(
        id=uuid4(),
        email="no.name@example.com",
        password_hash="not-a-real-hash",
        name=None,
    )
    project = _project(owner_id=current_user.id)
    payload = TeamMemberCreate(
        skills=["Python"],
        user_id=nameless.id,
        project_id=project.id,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=nameless),
            _execute_result(scalar=project),
            _execute_result(scalar=None),
        ]
    )

    result = await create_team_member(payload, session, current_user)

    assert result.name == "no.name@example.com"


@pytest.mark.asyncio
async def test_create_team_member_missing_user_returns_404(
    current_user: User,
) -> None:
    payload = TeamMemberCreate(
        skills=["Python"],
        user_id=uuid4(),
        project_id=uuid4(),
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await create_team_member(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_team_member_missing_project_returns_404(
    current_user: User,
) -> None:
    payload = TeamMemberCreate(
        skills=["Python"],
        user_id=current_user.id,
        project_id=uuid4(),
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=current_user),
            _execute_result(scalar=None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_team_member(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_team_member_duplicate_user_returns_409(
    current_user: User,
) -> None:
    project = _project(owner_id=current_user.id)
    existing_team_member = _member(
        user_id=current_user.id,
        project_id=project.id,
        skills=["Python"],
    )
    payload = TeamMemberCreate(
        skills=["SQL"],
        user_id=current_user.id,
        project_id=project.id,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=current_user),
            _execute_result(scalar=project),
            _execute_result(scalar=existing_team_member),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_team_member(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_team_member_integrity_error_returns_409(
    current_user: User,
) -> None:
    project = _project(owner_id=current_user.id)
    payload = TeamMemberCreate(
        skills=["SQL"],
        user_id=current_user.id,
        project_id=project.id,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock(side_effect=IntegrityError("", "", Exception()))
    session.rollback = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=current_user),
            _execute_result(scalar=project),
            _execute_result(scalar=None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_team_member(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_team_member_by_id_success(current_user: User) -> None:
    project_id = uuid4()
    member_id = uuid4()
    db_member = _member(
        user_id=current_user.id,
        project_id=project_id,
        id=member_id,
        skills=["Python", "SQL", "Docker"],
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_member),
            _execute_result(scalar=current_user),
        ]
    )

    result = await get_team_member(member_id, session, current_user)

    assert session.execute.await_count == 2
    assert result.id == member_id
    assert result.name == current_user.name
    assert result.skills == ["Python", "SQL", "Docker"]
    assert result.user_id == current_user.id
    assert result.project_id == project_id


@pytest.mark.asyncio
async def test_get_team_member_by_id_missing_user_returns_404(
    current_user: User,
) -> None:
    project_id = uuid4()
    member_id = uuid4()
    db_member = _member(
        user_id=current_user.id,
        project_id=project_id,
        id=member_id,
        skills=["Python"],
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_member),
            _execute_result(scalar=None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_team_member(member_id, session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_team_member_by_id_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))
    with pytest.raises(HTTPException) as exc_info:
        await get_team_member(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_team_members_success(current_user: User) -> None:
    project_id = uuid4()
    ada = _member(
        user_id=uuid4(),
        project_id=project_id,
        skills=["Python", "SQL", "Docker"],
    )
    grace = _member(
        user_id=uuid4(),
        project_id=project_id,
        skills=["Assembly", "COBOL"],
    )
    ada_user = _linked_user(ada, name="Ada Lovelace", email="ada@example.com")
    grace_user = _linked_user(grace, name="Grace Hopper", email="grace@example.com")
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=_rows_result([(ada, ada_user), (grace, grace_user)])
    )

    result = await get_team_members(session, current_user)

    session.execute.assert_awaited_once()
    assert len(result) == 2
    assert result[0].id == ada.id
    assert result[0].name == "Ada Lovelace"
    assert result[0].skills == ada.skills
    assert result[0].user_id == ada.user_id
    assert result[0].project_id == project_id
    assert result[1].id == grace.id
    assert result[1].name == "Grace Hopper"
    assert result[1].skills == grace.skills
    assert result[1].user_id == grace.user_id


@pytest.mark.asyncio
async def test_update_team_member_success(current_user: User) -> None:
    project_id = uuid4()
    member_id = uuid4()
    db_member = _member(
        user_id=current_user.id,
        project_id=project_id,
        id=member_id,
        skills=["Python", "SQL", "Docker"],
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_member),
            _execute_result(scalar=current_user),
        ]
    )

    payload = TeamMemberUpdate(skills=["Math"])
    result = await update_team_member(member_id, payload, session, current_user)

    assert db_member.skills == ["Math"]
    session.add.assert_called_once_with(db_member)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()
    assert result.name == current_user.name
    assert result.skills == ["Math"]
    assert result.id == member_id
    assert result.user_id == current_user.id
    assert result.project_id == project_id


@pytest.mark.asyncio
async def test_update_team_member_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await update_team_member(
            uuid4(), TeamMemberUpdate(skills=["Nope"]), session, current_user
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_team_member_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await delete_team_member(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_team_member_conflict_when_assigned(current_user: User) -> None:
    member_id = uuid4()
    db_member = _member(
        user_id=current_user.id,
        project_id=uuid4(),
        id=member_id,
        skills=[],
    )

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=db_member),
            _execute_result(scalar=uuid4()),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await delete_team_member(member_id, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_team_member_success(current_user: User) -> None:
    member_id = uuid4()
    db_member = _member(
        user_id=current_user.id,
        project_id=uuid4(),
        id=member_id,
        skills=["Python", "SQL", "Docker"],
    )
    session = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[_execute_result(scalar=db_member), _execute_result(scalar=None)]
    )
    result = await delete_team_member(member_id, session, current_user)

    assert result is None
    session.delete.assert_awaited_once()
    session.commit.assert_awaited_once()
