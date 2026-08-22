"""Routes for task dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.models import Task, TaskDependency, User
from app.schemas.task_dependency import TaskDependencyCreate, TaskDependencyRead
from app.core.security import get_current_user

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def _ensure_task_exists(session: AsyncSession, task_id: UUID) -> None:
    """Raise 404 if task_id is not an existing task."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.post(
    "/", response_model=TaskDependencyRead, status_code=status.HTTP_201_CREATED
)
async def create_task_dependency(
    task_dependency: TaskDependencyCreate, session: Session, current_user: CurrentUser
) -> TaskDependencyRead:
    """Create a new task dependency.

    Args:
        task_dependency: The task dependency to create.
        session: The database session.
        current_user: CurrentUser
    Returns:
        The created task dependency.
    """
    await _ensure_task_exists(session, task_dependency.from_task_id)
    await _ensure_task_exists(session, task_dependency.to_task_id)

    task_dependency_obj = TaskDependency(
        from_task_id=task_dependency.from_task_id,
        to_task_id=task_dependency.to_task_id,
    )
    session.add(task_dependency_obj)
    try:
        await session.commit()
        await session.refresh(task_dependency_obj)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task dependency already exists",
        ) from exc
    return TaskDependencyRead.model_validate(task_dependency_obj)


@router.get(
    "/", response_model=list[TaskDependencyRead], status_code=status.HTTP_200_OK
)
async def get_all_task_dependencies(
    session: Session,
    current_user: CurrentUser,
    from_task_id: Annotated[UUID | None, Query()] = None,
    to_task_id: Annotated[UUID | None, Query()] = None,
) -> list[TaskDependencyRead]:
    """Get all task dependencies.

    Args:
        session: The database session.
        current_user: CurrentUser
        from_task_id: Optional filter by source task.
        to_task_id: Optional filter by dependent task.
    Returns:
        A list of task dependencies.
    """
    statement = select(TaskDependency)
    if from_task_id is not None:
        statement = statement.where(TaskDependency.from_task_id == from_task_id)
    if to_task_id is not None:
        statement = statement.where(TaskDependency.to_task_id == to_task_id)
    task_dependencies_proxy = await session.execute(statement)
    task_dependencies = task_dependencies_proxy.scalars().all()
    return [
        TaskDependencyRead.model_validate(task_dependency)
        for task_dependency in task_dependencies
    ]


@router.get(
    "/{task_dependency_id}",
    response_model=TaskDependencyRead,
    status_code=status.HTTP_200_OK,
)
async def get_task_dependency_by_id(
    task_dependency_id: UUID, session: Session, current_user: CurrentUser
) -> TaskDependencyRead:
    """Get a task dependency by its ID.

    Args:
        task_dependency_id: The ID of the task dependency to get.
        session: The database session.
        current_user: CurrentUser
    Returns:
        The task dependency.
    """
    task_dependency_proxy = await session.execute(
        select(TaskDependency).where(TaskDependency.id == task_dependency_id)
    )
    task_dependency = task_dependency_proxy.scalar_one_or_none()
    if not task_dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task dependency not found",
        )
    return TaskDependencyRead.model_validate(task_dependency)


@router.delete("/{task_dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_dependency(task_dependency_id: UUID, session: Session, current_user: CurrentUser) -> None:
    """Delete a task dependency.

    Args:
        task_dependency_id: The ID of the task dependency to delete.
        session: The database session.
        current_user: CurrentUser
    Returns:
        None.
    """
    task_dependency_proxy = await session.execute(
        select(TaskDependency).where(TaskDependency.id == task_dependency_id)
    )
    task_dependency = task_dependency_proxy.scalar_one_or_none()
    if not task_dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task dependency not found",
        )
    await session.delete(task_dependency)
    await session.commit()
