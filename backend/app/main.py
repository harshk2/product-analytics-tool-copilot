"""FastAPI application entry point."""
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.config import settings
from app.db.session import init_db, close_db

logger = structlog.get_logger(__name__)

# ─── Prometheus Metrics ───────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)

INVESTIGATION_COUNT = Counter(
    "investigations_total",
    "Total investigations started",
)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logger.info("Starting AI Product Analytics Copilot", version=settings.APP_VERSION)

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down")
    await close_db()


# ─── Application ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=settings.API_DOCS_URL,
        redoc_url=settings.API_REDOC_URL,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Request logging & metrics
    @app.middleware("http")
    async def request_middleware(request: Request, call_next) -> Response:
        start_time = time.monotonic()

        # Add correlation ID to all responses
        response = await call_next(request)

        elapsed = time.monotonic() - start_time
        path = request.url.path

        # Track metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=path,
            status_code=response.status_code,
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=path,
        ).observe(elapsed)

        # Log request
        logger.info(
            "Request",
            method=request.method,
            path=path,
            status=response.status_code,
            duration_ms=round(elapsed * 1000, 2),
        )

        return response

    # ── Routes ─────────────────────────────────────────────────────────────────

    # API v1 router
    from app.api.v1 import chat, query, memory, dashboard
    from fastapi import APIRouter

    api_v1 = APIRouter(prefix=settings.API_V1_PREFIX)
    api_v1.include_router(chat.router, prefix="/chat", tags=["Chat"])
    api_v1.include_router(query.router, prefix="/query", tags=["Query"])
    api_v1.include_router(memory.router, prefix="/memory", tags=["Memory"])
    api_v1.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

    app.include_router(api_v1)

    # Health check
    @app.get("/health", tags=["System"])
    async def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}

    # Metrics endpoint
    if settings.ENABLE_METRICS:
        @app.get(settings.METRICS_PATH, tags=["System"])
        async def metrics():
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST,
            )

    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1 if settings.DEBUG else 4,
    )