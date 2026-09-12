from fastapi import FastAPI

from services.api.app.api.routes.health import router as health_router
from services.api.app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)
