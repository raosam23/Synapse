"""Routes for comments."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import get_current_user
from app.db.session import get_session
from app.models import Comment, Task, User
from app.schemas.comment import CommentCreate, CommentRead, CommentUpdate

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment: CommentCreate,
    session: Session,
    current_user: CurrentUser,
) -> CommentRead:
    """Route to POST a new comment.
    Args:
        comment: The comment to create.
        session: The database session.
        current_user: The current user.
    Returns:
        The created comment object.
    """
    task_proxy = await session.execute(select(Task).where(Task.id == comment.task_id))
    task = task_proxy.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    db_comment = Comment(
        task_id=comment.task_id,
        body=comment.body,
        user_id=current_user.id,
        is_ai=False,
    )
    session.add(db_comment)
    await session.commit()
    await session.refresh(db_comment)

    return CommentRead.model_validate(db_comment)


@router.get("/", response_model=list[CommentRead], status_code=status.HTTP_200_OK)
async def get_all_comments(
    session: Session,
    current_user: CurrentUser,
    task_id_filter: Annotated[UUID | None, Query(alias="task_id")] = None,
) -> list[CommentRead]:
    """Route to GET all comments.
    Args:
        session: The database session.
        current_user: The current user.
        task_id_filter: The task ID filter.
    Returns:
        list[CommentRead]: The list of comments.
    """
    statement = select(Comment)
    if task_id_filter is not None:
        statement = statement.where(Comment.task_id == task_id_filter)
    statement = statement.order_by(desc(Comment.created_at))
    comment_proxy = await session.execute(statement)
    comments = comment_proxy.scalars().all()

    return [CommentRead.model_validate(comment) for comment in comments]


@router.get("/{comment_id}", response_model=CommentRead, status_code=status.HTTP_200_OK)
async def get_comment_by_id(
    comment_id: UUID,
    session: Session,
    current_user: CurrentUser,
) -> CommentRead:
    """Route to GET a comment by its ID.
    Args:
        comment_id: The comment ID.
        session: The database session.
        current_user: The current user.
    Returns:
        CommentRead: The comment object.
    """

    comment_proxy = await session.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = comment_proxy.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    return CommentRead.model_validate(comment)


@router.put("/{comment_id}", response_model=CommentRead, status_code=status.HTTP_200_OK)
async def update_comment_by_id(
    comment_id: UUID,
    comment_update: CommentUpdate,
    session: Session,
    current_user: CurrentUser,
) -> CommentRead:
    """Route to PUT a comment by its ID.
    Args:
        comment_id: The comment ID.
        comment_update: The comment update.
        session: The database session.
        current_user: The current user.
    Returns:
        CommentRead: The updated comment object.
    """
    comment_proxy = await session.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = comment_proxy.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    updates = comment_update.model_dump(exclude_unset=True)
    if "body" in updates and updates["body"] is not None:
        comment.body = updates["body"]

    comment.updated_at = datetime.now()  # noqa: DTZ005 — column is TIMESTAMP WITHOUT TIME ZONE
    session.add(comment)

    await session.commit()
    await session.refresh(comment)

    return CommentRead.model_validate(comment)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment_by_id(
    comment_id: UUID,
    session: Session,
    current_user: CurrentUser,
) -> None:
    """Route to DELETE a comment by its ID.
    Args:
        comment_id: The comment ID.
        session: The database session.
        current_user: The current user.
    Returns:
        None
    """
    comment_proxy = await session.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = comment_proxy.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    await session.delete(comment)
    await session.commit()
