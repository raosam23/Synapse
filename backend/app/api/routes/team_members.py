"""Team members routes endpoints"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.models.team_member import TeamMember
from app.schemas.team_member import TeamMemberCreate, TeamMemberRead, TeamMemberUpdate

Session = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter()


@router.post("/", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
async def create_team_member(
    team_member: TeamMemberCreate, session: Session
) -> TeamMemberRead:
    """
    Create a new team member
    Args:
        team_member: TeamMemberCreate
        session: Session
    Returns:
        TeamMemberRead
    """
    db_team_member = TeamMember(
        name=team_member.name,
        skills=team_member.skills,
    )
    session.add(db_team_member)
    await session.commit()
    await session.refresh(db_team_member)
    return TeamMemberRead.model_validate(db_team_member)


@router.get("/", response_model=list[TeamMemberRead], status_code=status.HTTP_200_OK)
async def get_team_members(session: Session):
    """
    Get all team members
    Args:
        session: Session
    Returns:
        list[TeamMemberRead]
    """
    result_proxy = await session.execute(select(TeamMember).order_by(TeamMember.name))
    team_members = result_proxy.scalars().all()
    return [TeamMemberRead.model_validate(team_member) for team_member in team_members]


@router.get(
    "/{team_member_id}", response_model=TeamMemberRead, status_code=status.HTTP_200_OK
)
async def get_team_member(team_member_id: UUID, session: Session):
    """
    Get a team member by ID
    Args:
        team_member_id: UUID
        session: Session
    Returns:
        TeamMemberRead
    """
    result_proxy = await session.execute(
        select(TeamMember).where(TeamMember.id == team_member_id)
    )
    team_member = result_proxy.scalar_one_or_none()
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found"
        )
    return TeamMemberRead.model_validate(team_member)


@router.put(
    "/{team_member_id}", response_model=TeamMemberRead, status_code=status.HTTP_200_OK
)
async def update_team_member(
    team_member_id: UUID,
    team_member: TeamMemberUpdate,
    session: Session,
) -> TeamMemberRead:
    """
    Update a team member
    Args:
        team_member_id: UUID
        team_member: TeamMemberUpdate
        session: Session
    Returns:
        TeamMemberRead
    """
    result_proxy = await session.execute(
        select(TeamMember).where(TeamMember.id == team_member_id)
    )
    db_team_member = result_proxy.scalar_one_or_none()
    if not db_team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found"
        )
    for key, value in team_member.model_dump(exclude_unset=True).items():
        setattr(db_team_member, key, value)
    session.add(db_team_member)
    await session.commit()
    await session.refresh(db_team_member)
    return TeamMemberRead.model_validate(db_team_member)


@router.delete("/{team_member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_member(
    team_member_id: UUID,
    session: Session,
) -> None:
    """
    Delete a team member
    Args:
        team_member_id: UUID
        session: Session
    Returns:
        None
    """
    result_proxy = await session.execute(
        select(TeamMember).where(TeamMember.id == team_member_id)
    )
    db_team_member = result_proxy.scalar_one_or_none()
    if not db_team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found"
        )
    await session.delete(db_team_member)
    await session.commit()
