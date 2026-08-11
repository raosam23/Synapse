"""API router"""

from fastapi import APIRouter

from app.api.routes import TaskRouter, TeamMembersRouter

router = APIRouter(prefix="/api/v1")
router.include_router(TeamMembersRouter, prefix="/team-members", tags=["Team Members"])
router.include_router(TaskRouter, prefix="/tasks", tags=["Tasks"])
