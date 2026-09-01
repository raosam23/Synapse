"""API routes."""

from app.api.routes.auth import router as AuthRouter
from app.api.routes.projects import router as ProjectsRouter
from app.api.routes.task_dependencies import router as TaskDependenciesRouter
from app.api.routes.tasks import router as TaskRouter
from app.api.routes.team_members import router as TeamMembersRouter

__all__ = [
    "AuthRouter",
    "ProjectsRouter",
    "TaskDependenciesRouter",
    "TaskRouter",
    "TeamMembersRouter",
]
