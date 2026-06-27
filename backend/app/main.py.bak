"""FastAPI application entrypoint.

Wires up the application factory, middlewares, routers, and lifecycle
events.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.seed import seed_admin_user, seed_shift_types
from app.db.session import SessionLocal

logger = get_logger(__name__)

# Resolve paths relative to the backend package so static/template
# lookups work both locally and inside the container.
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Application startup / shutdown lifecycle."""
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)
    logger.info("Database: %s", settings.postgres_host)

    # Seed default data (idempotent — safe on every start)
    db = SessionLocal()
    try:
        seed_shift_types(db)
        seed_admin_user(db)
    except Exception:
        logger.warning("Seed data could not be applied (tables may not exist yet)")
    finally:
        db.close()

    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory."""
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files (served by backend too, in case nginx is bypassed)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Routers
    app.include_router(api_router, prefix="/api")

    logger.info("%s application created", settings.app_name)
    return app


app = create_app()
