"""
This module creates and configures the FastAPI application.

The application registers API routers and provides the central
entry point for the AI Business Employee backend service.
"""

from fastapi import FastAPI

from services.api.app.api.routes.auth import router as auth_router
from services.api.app.api.routes.businesses import router as businesses_router
from services.api.app.api.routes.conversations import (
    router as conversations_router,
)
from services.api.app.api.routes.customers import router as customers_router
from services.api.app.api.routes.health import router as health_router
from services.api.app.api.routes.leads import router as leads_router
from services.api.app.api.routes.messages import router as messages_router
from services.api.app.api.routes.products import router as products_router
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

app.include_router(
    products_router,
    prefix="/businesses",
    tags=["Products"],
)

app.include_router(
    customers_router,
    prefix="/businesses",
    tags=["Customers"],
)

app.include_router(
    leads_router,
    prefix="/businesses",
    tags=["Leads"],
)

app.include_router(
    conversations_router,
    prefix="/businesses",
    tags=["Conversations"],
)

app.include_router(
    messages_router,
    prefix="/businesses",
    tags=["Messages"],
)
