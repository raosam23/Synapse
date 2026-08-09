"""API router"""

from fastapi import APIRouter

from app.api.routes import TeamMembersRouter

router = APIRouter(prefix="/api/v1")
router.include_router(TeamMembersRouter, prefix="/team-members", tags=["Team Members"])
