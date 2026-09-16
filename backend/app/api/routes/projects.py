"""Routes for projects."""

import asyncio
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.agents.graph import run_analyze_requirements
from app.core.security import get_current_user
from app.db.session import get_session
from app.models import Project, Task, TeamMember, User
from app.models.task import TaskStatus
from app.schemas.project import AgentRunRead, ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    session: Session,
    current_user: CurrentUser,
) -> ProjectRead:
    """Create a new project.
    Args:
        project: The project to create.
        session: The database session.
        current_user: The current user.
    Returns:
        The created project.
    """
    new_project = Project(
        name=project.name,
        requirements=project.requirements,
        duration_weeks=project.duration_weeks,
        status=project.status,
        created_by_id=current_user.id,
        sprint_length_weeks=2,
        ai_opinion=None,
    )
    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)
    return ProjectRead.model_validate(new_project)


@router.get("/", response_model=list[ProjectRead], status_code=status.HTTP_200_OK)
async def get_all_projects(
    session: Session,
    current_user: CurrentUser,
) -> list[ProjectRead]:
    """Get all projects.
    Args:
        session: The database session.
        current_user: The current user.
    Returns:
        A list of all projects.
    """
    projects_proxy = await session.execute(
        select(Project).where(Project.created_by_id == current_user.id)
    )
    projects = projects_proxy.scalars().all()
    return [ProjectRead.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectRead, status_code=status.HTTP_200_OK)
async def get_project_by_id(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
) -> ProjectRead:
    """Get a project by id.
    Args:
        project_id: The id of the project to get.
        session: The database session.
        current_user: The current user.
    Returns:
        The project.
    """
    project_proxy = await session.execute(
        select(Project).where(
            Project.created_by_id == current_user.id,
            Project.id == project_id,
        )
    )
    project = project_proxy.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found.",
        )
    return ProjectRead.model_validate(project)


@router.put("/{project_id}", response_model=ProjectRead, status_code=status.HTTP_200_OK)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    session: Session,
    current_user: CurrentUser,
) -> ProjectRead:
    """Update a project.
    Args:
        project_id: The id of the project to update.
        project_update: The data of the project to be updated.
        session: The database session.
        current_user: The current user.
    Returns:
        The updated project.
    """
    project_proxy = await session.execute(
        select(Project).where(
            Project.created_by_id == current_user.id,
            Project.id == project_id,
        )
    )
    project = project_proxy.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found.",
        )

    updates = project_update.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(project, key, value)
    project.updated_at = datetime.now()  # noqa: DTZ005 — column is TIMESTAMP WITHOUT TIME ZONE

    session.add(project)
    await session.commit()
    await session.refresh(project)
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
) -> None:
    """Delete a project.
    Args:
        project_id: The id of the project to delete.
        session: The database session.
        current_user: The current user.
    Returns:
        None.
    """
    project_proxy = await session.execute(
        select(Project).where(
            Project.created_by_id == current_user.id,
            Project.id == project_id,
        )
    )
    project = project_proxy.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found.",
        )
    try:
        await session.delete(project)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete project while it has tasks, team members, or sprints",
        ) from exc


@router.post(
    "/{project_id}/agents/run",
    status_code=status.HTTP_200_OK,
    response_model=AgentRunRead,
)
async def run_agents(
    project_id: UUID,
    session: Session,
    current_user: CurrentUser,
) -> AgentRunRead:
    """Run the Requirement Analyzer for a project.
    Args:
        project_id: The id of the project to analyze.
        session: The database session.
        current_user: The current user.
    Returns:
        AgentRunRead: How many backlog tasks were created.
    """
    project_proxy = await session.execute(
        select(Project).where(
            Project.created_by_id == current_user.id,
            Project.id == project_id,
        )
    )
    project = project_proxy.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found.",
        )

    if project.ai_opinion is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project has already been analyzed.",
        )

    members_proxy = await session.execute(
        select(TeamMember).where(TeamMember.project_id == project.id)
    )
    team_skills: list[str] = []
    for member in members_proxy.scalars().all():
        for skill in member.skills or []:
            if skill not in team_skills:
                team_skills.append(skill)

    project_name = project.name
    result = await asyncio.to_thread(
        run_analyze_requirements,
        project.id,
        project.requirements,
        project.duration_weeks,
        team_skills,
    )

    project.ai_opinion = result["opinion"]
    session.add(project)

    for draft in result["tasks"]:
        session.add(
            Task(
                title=draft["title"],
                description=draft["description"],
                status=TaskStatus.BACKLOG,
                sprint_id=None,
                story_points=draft.get("story_points"),
                project_id=project.id,
                created_by_id=current_user.id,
            )
        )

    await session.commit()

    return AgentRunRead(
        project_id=project.id,
        message=(
            f"Created {len(result['tasks'])} backlog tasks "
            f"for the project {project_name}."
        ),
    )
