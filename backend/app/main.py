"""FastAPI application entrypoint.

Wires up the application factory, middlewares, routers, and lifecycle
events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.seed import seed_admin_user, seed_shift_types
from app.db.session import SessionLocal

logger = get_logger(__name__)


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
    except Exception as exc:  # noqa: BLE001
        # Tables may not exist yet (e.g. when running locally without
        # running migrations first). Log the cause for diagnosability.
        logger.warning("Seed data could not be applied: %s", exc)
    finally:
        db.close()

    yield
    logger.info("Shutting down %s", settings.app_name)


def _format_validation_errors(exc: RequestValidationError) -> str:
    """Convert a RequestValidationError into a single human-readable string."""
    errors = exc.errors()
    if not errors:
        return "Invalid input"
    first = errors[0]
    loc = [str(p) for p in first.get("loc", []) if p not in ("body", "query", "path")]
    msg = first.get("msg", "Invalid input")
    if loc:
        return f"{'.'.join(loc)}: {msg}"
    return msg


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

    # CORS — explicit origins only. Wildcard is not combined with
    # allow_credentials=True (browsers reject that combination per the
    # CORS spec). In the standard nginx-served deployment, frontend and
    # backend are on the same origin so CORS is never triggered.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Validation error handler — return a single readable message
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": _format_validation_errors(exc)},
        )

    # Routers
    app.include_router(api_router, prefix="/api")

    logger.info("%s application created", settings.app_name)
    return app


app = create_app()
