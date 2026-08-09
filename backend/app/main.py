"""Main application"""

from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
