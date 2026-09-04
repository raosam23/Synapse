"""Team members routes endpoints"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import get_current_user
from app.db.session import get_session
from app.models import Project, User
from app.models.task import Task
from app.models.team_member import TeamMember
from app.schemas.team_member import TeamMemberCreate, TeamMemberRead, TeamMemberUpdate

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]

router = APIRouter()


@router.post("/", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
async def create_team_member(
    team_member: TeamMemberCreate, session: Session, current_user: CurrentUser
) -> TeamMemberRead:
    """
    Create a new team member
    Args:
        team_member: TeamMemberCreate
        session: Session
        current_user: CurrentUser
    Returns:
        TeamMemberRead
    """
    user_proxy = await session.execute(
        select(User).where(User.id == team_member.user_id)
    )
    user = user_proxy.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    project_proxy = await session.execute(
        select(Project).where(Project.id == team_member.project_id)
    )
    project = project_proxy.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    team_member_proxy = await session.execute(
        select(TeamMember).where(
            TeamMember.user_id == team_member.user_id,
            TeamMember.project_id == team_member.project_id,
        )
    )
    team_member_db = team_member_proxy.scalar_one_or_none()

    if team_member_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team member for this project already exists",
        )

    db_team_member = TeamMember(
        skills=team_member.skills,
        user_id=team_member.user_id,
        project_id=team_member.project_id,
    )
    try:
        session.add(db_team_member)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Team member already exists"
        ) from exc
    await session.refresh(db_team_member)
    return TeamMemberRead.model_validate(
        {
            **db_team_member.model_dump(),
            "name": user.name or user.email,
        }
    )


@router.get("/", response_model=list[TeamMemberRead], status_code=status.HTTP_200_OK)
async def get_team_members(
    session: Session,
    current_user: CurrentUser,
    project_id_filter: Annotated[UUID | None, Query(alias="project_id")] = None,
) -> list[TeamMemberRead]:
    """
    Get all team members
    Args:
        session: Session
        current_user: CurrentUser
        project_id_filter: Annotated[UUID | None, Query(alias="project_id")] = None
    Returns:
        list[TeamMemberRead]
    """
    statement = select(TeamMember, User).join(User, TeamMember.user_id == User.id)
    if project_id_filter is not None:
        statement = statement.where(TeamMember.project_id == project_id_filter)
    statement = statement.order_by(User.name, User.email)
    result_proxy = await session.execute(statement)
    team_members = result_proxy.all()

    team_members_read: list[TeamMemberRead] = []
    for team_member, user in team_members:
        team_members_read.append(
            TeamMemberRead.model_validate(
                {
                    **team_member.model_dump(),
                    "name": user.name or user.email,
                }
            )
        )
    return team_members_read


@router.get(
    "/{team_member_id}", response_model=TeamMemberRead, status_code=status.HTTP_200_OK
)
async def get_team_member(
    team_member_id: UUID, session: Session, current_user: CurrentUser
) -> TeamMemberRead:
    """
    Get a team member by ID
    Args:
        team_member_id: UUID
        session: Session
        current_user: CurrentUser
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

    user_proxy = await session.execute(
        select(User).where(User.id == team_member.user_id)
    )
    user = user_proxy.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return TeamMemberRead.model_validate(
        {
            **team_member.model_dump(),
            "name": user.name or user.email,
        }
    )


@router.put(
    "/{team_member_id}", response_model=TeamMemberRead, status_code=status.HTTP_200_OK
)
async def update_team_member(
    team_member_id: UUID,
    team_member: TeamMemberUpdate,
    session: Session,
    current_user: CurrentUser,
) -> TeamMemberRead:
    """
    Update a team member
    Args:
        team_member_id: UUID
        team_member: TeamMemberUpdate
        session: Session
        current_user: CurrentUser
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
    user_proxy = await session.execute(
        select(User).where(User.id == db_team_member.user_id)
    )
    user = user_proxy.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return TeamMemberRead.model_validate(
        {
            **db_team_member.model_dump(),
            "name": user.name or user.email,
        }
    )


@router.delete("/{team_member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_member(
    team_member_id: UUID, session: Session, current_user: CurrentUser
) -> None:
    """
    Delete a team member
    Args:
        team_member_id: UUID
        session: Session
        current_user: CurrentUser
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

    assigned_task = await session.execute(
        select(Task.id).where(Task.assignee_id == team_member_id).limit(1)
    )
    if assigned_task.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete team member while they are assigned to tasks",
        )

    try:
        await session.delete(db_team_member)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete team member while they are assigned to tasks",
        ) from exc
