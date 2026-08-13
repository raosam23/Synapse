"""API router"""

from fastapi import APIRouter

from app.api.routes import TaskDependenciesRouter, TaskRouter, TeamMembersRouter

router = APIRouter(prefix="/api/v1")
router.include_router(TeamMembersRouter, prefix="/team-members", tags=["Team Members"])
router.include_router(TaskRouter, prefix="/tasks", tags=["Tasks"])
router.include_router(
    TaskDependenciesRouter, prefix="/task-dependencies", tags=["Task Dependencies"]
)
