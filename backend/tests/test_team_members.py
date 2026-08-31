"""Unit tests for team members CRUD routes"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

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
from app.models.team_member import TeamMember
from app.models.user import User
from app.schemas.team_member import TeamMemberCreate, TeamMemberRead, TeamMemberUpdate


@pytest.mark.asyncio
async def test_create_team_member_success(current_user: User) -> None:
    """Test creating a team member successfully"""
    payload = TeamMemberCreate(
        name="John Doe",
        skills=["Python", "SQL", "Docker"],
        user_id=current_user.id,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=current_user),
            _execute_result(scalar=None),
        ]
    )

    created_id = uuid4()

    async def fake_refresh(member: object) -> None:
        member.id = created_id

    session.refresh.side_effect = fake_refresh

    result = await create_team_member(payload, session, current_user)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    assert isinstance(result, TeamMemberRead)
    assert result.id == created_id
    assert result.name == "John Doe"
    assert result.skills == ["Python", "SQL", "Docker"]
    assert result.user_id == current_user.id


def _execute_result(*, scalar: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    return result


@pytest.mark.asyncio
async def test_create_team_member_missing_user_returns_404(
    current_user: User,
) -> None:
    payload = TeamMemberCreate(
        name="Missing User",
        skills=["Python"],
        user_id=uuid4(),
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
async def test_create_team_member_duplicate_user_returns_409(
    current_user: User,
) -> None:
    existing_team_member = TeamMember(
        id=uuid4(),
        name="Existing Member",
        skills=["Python"],
        user_id=current_user.id,
    )
    payload = TeamMemberCreate(
        name="Duplicate Member",
        skills=["SQL"],
        user_id=current_user.id,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=current_user),
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
    payload = TeamMemberCreate(
        name="Race Condition Member",
        skills=["SQL"],
        user_id=current_user.id,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock(side_effect=IntegrityError("", "", Exception()))
    session.rollback = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=current_user),
            _execute_result(scalar=None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_team_member(payload, session, current_user)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_team_member_by_id_success(current_user: User) -> None:
    member_id = uuid4()
    db_member = TeamMember(
        id=member_id,
        name="Ada Lovelace",
        skills=["Python", "SQL", "Docker"],
        user_id=current_user.id,
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_member))

    result = await get_team_member(member_id, session, current_user)

    session.execute.assert_awaited_once()
    assert result.id == member_id
    assert result.name == "Ada Lovelace"
    assert result.skills == ["Python", "SQL", "Docker"]
    assert result.user_id == current_user.id


@pytest.mark.asyncio
async def test_get_team_member_by_id_allows_legacy_unlinked_member(
    current_user: User,
) -> None:
    member_id = uuid4()
    db_member = TeamMember(
        id=member_id,
        name="Legacy Member",
        skills=["Python"],
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_member))

    result = await get_team_member(member_id, session, current_user)

    assert result.id == member_id
    assert result.name == "Legacy Member"
    assert result.user_id is None


@pytest.mark.asyncio
async def test_get_team_member_by_id_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))
    with pytest.raises(HTTPException) as exc_info:
        await get_team_member(uuid4(), session, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def _scalars_result(*, scalars: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars
    return result


@pytest.mark.asyncio
async def test_get_team_members_success(current_user: User) -> None:
    db_members = [
        TeamMember(
            id=uuid4(),
            name="Ada Lovelace",
            skills=["Python", "SQL", "Docker"],
            user_id=uuid4(),
        ),
        TeamMember(
            id=uuid4(),
            name="Grace Hopper",
            skills=["Assembly", "COBOL"],
            user_id=uuid4(),
        ),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_scalars_result(scalars=db_members))

    result = await get_team_members(session, current_user)

    session.execute.assert_awaited_once()
    assert len(result) == 2
    assert result[0].id == db_members[0].id
    assert result[0].name == db_members[0].name
    assert result[0].skills == db_members[0].skills
    assert result[0].user_id == db_members[0].user_id
    assert result[1].id == db_members[1].id
    assert result[1].name == db_members[1].name
    assert result[1].skills == db_members[1].skills
    assert result[1].user_id == db_members[1].user_id


@pytest.mark.asyncio
async def test_update_team_member_success(current_user: User) -> None:
    member_id = uuid4()
    db_member = TeamMember(
        id=member_id,
        name="Alan Turing",
        skills=["Python", "SQL", "Docker"],
        user_id=current_user.id,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=db_member))

    payload = TeamMemberUpdate(
        name="Alan Mathison Turing",
    )
    result = await update_team_member(member_id, payload, session, current_user)

    assert db_member.name == "Alan Mathison Turing"
    session.add.assert_called_once_with(db_member)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()
    assert result.name == "Alan Mathison Turing"
    assert result.skills == db_member.skills
    assert result.id == member_id
    assert result.user_id == current_user.id


@pytest.mark.asyncio
async def test_update_team_member_not_found(current_user: User) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    with pytest.raises(HTTPException) as exc_info:
        await update_team_member(
            uuid4(), TeamMemberUpdate(name="Nope"), session, current_user
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
    db_member = TeamMember(
        id=member_id,
        name="Ada Lovelace",
        skills=[],
        user_id=current_user.id,
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
    db_member = TeamMember(
        id=member_id,
        name="Ada Lovelace",
        skills=["Python", "SQL", "Docker"],
        user_id=current_user.id,
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
