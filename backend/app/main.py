from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.instances import router as instances_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.workflows import router as workflows_router
from app.core.config import settings
from app.core.rate_limit import close_redis_client
from app.db.mongo import close_database, ensure_indexes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await ensure_indexes()
    try:
        yield
    finally:
        await close_database()
        await close_redis_client()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": "Route not found",
                "path": request.url.path,
            },
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(organizations_router, prefix="/api")
    app.include_router(workflows_router, prefix="/api")
    app.include_router(instances_router, prefix="/api")
    app.include_router(tasks_router, prefix="/api")
    return app


app = create_app()
