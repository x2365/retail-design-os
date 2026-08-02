"""FastAPI application entrypoint.

Stateless by design: any number of identical workers can run behind a load
balancer. State lives only in the database.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import get_settings
from .database import Base, SessionLocal, engine
from .rate_limit import limiter
from .routers import (
    approvals,
    assistant,
    auth,
    brands,
    contractors,
    dashboard,
    deliveries,
    documents,
    equipment,
    export,
    finance,
    internal,
    nomenclature,
    reference,
    tasks,
    users,
)
from .seed import seed

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    settings.validate_runtime()  # fail fast on insecure prod config
    os.makedirs(settings.upload_dir, exist_ok=True)
    # In production, prefer Alembic migrations over create_all.
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Backend for the RetailDesign OS equipment-tracking dashboard.",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Bearer tokens are sent in the Authorization header, not cookies, so we do
    # NOT enable credentials — this keeps a wildcard origin safe.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (currently applied to POST /auth/login — see routers/auth.py).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Never leak stack traces / internals to clients.
    import logging

    logging.getLogger("uvicorn.error").exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


for r in (
    auth.router,
    dashboard.router,
    reference.router,
    brands.router,
    tasks.router,
    approvals.router,
    assistant.router,
    finance.router,
    deliveries.router,
    documents.router,
    equipment.router,
    export.router,
    nomenclature.router,
    internal.router,
    users.router,
    contractors.router,
):
    app.include_router(r, prefix=settings.api_prefix)


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "env": settings.environment}
