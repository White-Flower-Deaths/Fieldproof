from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import settings
from .database import init_db
from .enums import CONCENTRATION_NOT_DETERMINABLE, DISCLAIMER
from .routers import analysis, auth, imaging, meta, records, samples
from .seed import seed_demo
from .database import SessionFactory


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.seed_demo:
        with SessionFactory() as db:
            seed_demo(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="FieldProof API",
        description=(
            "Decision support for colorimetric field testing. "
            + DISCLAIMER
            + " "
            + CONCENTRATION_NOT_DETERMINABLE
        ),
        version=settings.engine_version,
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api")
    app.include_router(meta.router, prefix="/api")
    app.include_router(meta.admin_router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(samples.router, prefix="/api")
    app.include_router(records.router, prefix="/api")
    app.include_router(records.verify_router, prefix="/api")
    app.include_router(records.images_router, prefix="/api")
    app.include_router(imaging.router, prefix="/api")

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "app": settings.app_name,
            "api": "/api",
            "docs": "/docs",
            "disclaimer": DISCLAIMER,
        }

    return app


app = create_app()
