"""
FastAPI application entry point.

Startup order:
  1. Register exception handlers
  2. Add correlation ID middleware
  3. Mount API routers
  4. Startup event: verify DB connection
"""

import uuid
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import memory as memory_router
from app.api import search as search_router
from app.api import query as query_router
from app.config import get_settings
from app.db.session import engine
from app.exceptions.handlers import register_exception_handlers
from app.logging.logger import get_correlation_id, logger, set_correlation_id

settings = get_settings()

app = FastAPI(
    title="AI Person — Bộ Não Thứ 2",
    description="Memory-First Personal AI System",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Correlation ID Middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    set_correlation_id(cid)
    request.state.correlation_id = cid
    start = time.monotonic()
    response = await call_next(request)
    latency = int((time.monotonic() - start) * 1000)
    response.headers["X-Correlation-ID"] = cid
    logger.info(
        "http_request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency,
        },
    )
    return response

# ─── Exception Handlers ───────────────────────────────────────────────────────
register_exception_handlers(app)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(memory_router.router)
app.include_router(search_router.router)
app.include_router(query_router.router)

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "version": app.version}

# ─── Startup / Shutdown ───────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("app_startup", extra={"version": app.version, "debug": settings.debug})
    # Verify DB is reachable
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("db_connection_ok")
    except Exception as exc:
        logger.error("db_connection_failed", extra={"error": str(exc)})


@app.on_event("shutdown")
async def on_shutdown():
    await engine.dispose()
    logger.info("app_shutdown")
