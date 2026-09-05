"""API router"""

from fastapi import APIRouter

from app.api.routes import (
    AuthRouter,
    ProjectsRouter,
    SprintsRouter,
    TaskDependenciesRouter,
    TaskRouter,
    TeamMembersRouter,
)

router = APIRouter(prefix="/api/v1")
router.include_router(TeamMembersRouter, prefix="/team-members", tags=["Team Members"])
router.include_router(TaskRouter, prefix="/tasks", tags=["Tasks"])
router.include_router(
    TaskDependenciesRouter, prefix="/task-dependencies", tags=["Task Dependencies"]
)
router.include_router(AuthRouter, prefix="/auth", tags=["Auth"])
router.include_router(ProjectsRouter, prefix="/projects", tags=["Projects"])
router.include_router(SprintsRouter, prefix="/sprints", tags=["Sprints"])
