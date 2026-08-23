"""Routes for tasks."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import get_current_user
from app.db.session import get_session
from app.models import Task, TeamMember, User
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def _ensure_assignee_exists(session: AsyncSession, assignee_id: UUID) -> None:
    """Raise 404 if assignee_id is not an existing team member."""
    result = await session.execute(
        select(TeamMember).where(TeamMember.id == assignee_id)
    )
    team_member = result.scalar_one_or_none()
    if team_member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found",
        )
    if team_member.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team member is not a user",
        )


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate, session: Session, current_user: CurrentUser
) -> TaskRead:
    """Endpoint to create a new task.
    Args:
        task: TaskCreate
        session: Session
        current_user: CurrentUser
    Returns:
        TaskRead
    """
    if task.assignee_id is not None:
        await _ensure_assignee_exists(session, task.assignee_id)

    new_task = Task(
        title=task.title,
        description=task.description,
        assignee_id=task.assignee_id,
        sprint_id=task.sprint_id,
        status=task.status,
        story_points=task.story_points,
        risk_flag=task.risk_flag,
        created_by_id=current_user.id,
    )
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return TaskRead.model_validate(new_task)


@router.get("/", response_model=list[TaskRead], status_code=status.HTTP_200_OK)
async def get_all_tasks(
    session: Session,
    current_user: CurrentUser,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
) -> list[TaskRead]:
    """Endpoint to get all tasks.
    Args:
        session: Session
        current_user: CurrentUser
        status_filter: optional TaskStatus query filter (`?status=`)
    Returns:
        list[TaskRead]
    """
    statement = select(Task)
    if status_filter is not None:
        statement = statement.where(Task.status == status_filter)
    statement = statement.order_by(desc(Task.created_at))
    task_proxy = await session.execute(statement)
    tasks = task_proxy.scalars().all()
    return [TaskRead.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskRead, status_code=status.HTTP_200_OK)
async def get_task_by_id(
    task_id: UUID, session: Session, current_user: CurrentUser
) -> TaskRead:
    """Endpoint to get a task by its ID.
    Args:
        task_id: UUID
        session: Session
        current_user: CurrentUser
    Returns:
        TaskRead
    """
    task_proxy = await session.execute(select(Task).where(Task.id == task_id))
    task = task_proxy.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return TaskRead.model_validate(task)


@router.put("/{task_id}", response_model=TaskRead, status_code=status.HTTP_200_OK)
async def update_task(
    task_id: UUID, task_update: TaskUpdate, session: Session, current_user: CurrentUser
) -> TaskRead:
    """Endpoint to update a task.
    Args:
        task_id: UUID
        task_update: TaskUpdate
        session: Session
        current_user: CurrentUser
    Returns:
        TaskRead
    """
    task_proxy = await session.execute(select(Task).where(Task.id == task_id))
    task = task_proxy.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    updates = task_update.model_dump(exclude_unset=True)
    if "assignee_id" in updates and updates["assignee_id"] is not None:
        await _ensure_assignee_exists(session, updates["assignee_id"])

    for key, value in updates.items():
        setattr(task, key, value)
    task.updated_at = datetime.now()  # noqa: DTZ005 — column is TIMESTAMP WITHOUT TIME ZONE

    session.add(task)
    await session.commit()
    await session.refresh(task)
    return TaskRead.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID, session: Session, current_user: CurrentUser
) -> None:
    """Endpoint to delete a task.
    Args:
        task_id: UUID
        session: Session
        current_user: CurrentUser
    Returns:
        None
    """
    task_proxy = await session.execute(select(Task).where(Task.id == task_id))
    task = task_proxy.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    try:
        await session.delete(task)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete task while it has dependency links",
        ) from exc
