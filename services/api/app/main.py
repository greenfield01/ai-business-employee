from fastapi import FastAPI

from services.api.app.api.routes.auth import router as auth_router
from services.api.app.api.routes.businesses import router as businesses_router
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

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

app.include_router(
    businesses_router,
    prefix="/businesses",
    tags=["Businesses"],
)
