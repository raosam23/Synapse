"""Routes for sprints."""

from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import get_current_user
from app.db.session import get_session
from app.models import Project, Sprint, Task, User
from app.schemas.sprint import SprintCreate, SprintRead

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/", response_model=list[SprintRead], status_code=status.HTTP_201_CREATED)
async def create_sprints(
    sprint_create: SprintCreate,
    session: Session,
    current_user: CurrentUser,
) -> list[SprintRead]:
    """Create sprints for a project.

    Args:
        sprint_create: The sprint to create.
        session: The database session.
        current_user: The current user.

    Returns:
        The created sprints.
    """
    project_proxy = await session.execute(
        select(Project).where(Project.id == sprint_create.project_id)
    )
    project = project_proxy.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    sprint_count = project.duration_weeks // project.sprint_length_weeks

    if sprint_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project duration is less than sprint length",
        )

    sprints: list[Sprint] = []

    for index in range(1, sprint_count + 1):
        start_date = sprint_create.start_date + timedelta(
            weeks=project.sprint_length_weeks * (index - 1)
        )
        end_date = (
            start_date
            + timedelta(weeks=project.sprint_length_weeks)
            - timedelta(days=1)
        )

        sprints.append(
            Sprint(
                project_id=sprint_create.project_id,
                index=index,
                start_date=start_date,
                end_date=end_date,
            )
        )

    session.add_all(sprints)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sprints already exist for this project",
        ) from exc
    return [SprintRead.model_validate(sprint) for sprint in sprints]


@router.get("/", response_model=list[SprintRead], status_code=status.HTTP_200_OK)
async def get_sprints(
    session: Session,
    current_user: CurrentUser,
    project_id_filter: Annotated[UUID | None, Query(alias="project_id")] = None,
) -> list[SprintRead]:
    """Get sprints for a project.
    Args:
        session: The database session.
        current_user: The current user.
        project_id_filter: The id of the project to get sprints for.
    Returns:
        list[SprintRead]: The list of sprints.
    """

    statement = select(Sprint)
    if project_id_filter is not None:
        statement = statement.where(Sprint.project_id == project_id_filter)

    statement = statement.order_by(Sprint.index)

    sprint_proxy = await session.execute(statement)
    sprints = sprint_proxy.scalars().all()

    return [SprintRead.model_validate(sprint) for sprint in sprints]


@router.get("/{sprint_id}", status_code=status.HTTP_200_OK, response_model=SprintRead)
async def get_sprint_by_id(
    sprint_id: UUID,
    session: Session,
    current_user: CurrentUser,
) -> SprintRead:
    """Get a sprint by id.
    Args:
        sprint_id: The id of the sprint to get.
        session: The database session.
        current_user: The current user.

    Returns:
        SprintRead: The sprint.
    """
    sprint_proxy = await session.execute(select(Sprint).where(Sprint.id == sprint_id))
    sprint = sprint_proxy.scalar_one_or_none()
    if not sprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sprint not found",
        )
    return SprintRead.model_validate(sprint)


@router.delete("/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sprint_by_id(
    sprint_id: UUID,
    session: Session,
    current_user: CurrentUser,
) -> None:
    """Delete a sprint by id.
    Args:
        sprint_id: The id of the sprint to delete.
        session: The database session.
        current_user: The current user.

    Returns:
        None
    """

    sprint_proxy = await session.execute(select(Sprint).where(Sprint.id == sprint_id))
    sprint = sprint_proxy.scalar_one_or_none()

    if not sprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sprint not found",
        )

    assigned_tasks_proxy = await session.execute(
        select(Task.id).where(Task.sprint_id == sprint_id).limit(1)
    )
    if assigned_tasks_proxy.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete sprint while it has assigned tasks",
        )
    try:
        await session.delete(sprint)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete sprint while it has assigned tasks",
        ) from exc
