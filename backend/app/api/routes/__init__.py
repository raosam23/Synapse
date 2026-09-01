"""API routes."""

from app.api.routes.auth import router as AuthRouter
from app.api.routes.task_dependencies import router as TaskDependenciesRouter
from app.api.routes.tasks import router as TaskRouter
from app.api.routes.team_members import router as TeamMembersRouter
from app.api.routes.projects import router as ProjectsRouter

__all__ = [
    "AuthRouter",
    "TaskDependenciesRouter",
    "TaskRouter",
    "TeamMembersRouter",
    "ProjectsRouter",
]
