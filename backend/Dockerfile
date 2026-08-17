# --- RetailDesign OS API image ---------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# pg_dump/pg_restore — used by services/snapshot.py for the demo data reset
# point (see routers/internal.py's /internal/snapshot/* endpoints). Not
# needed at all when DATABASE_URL is SQLite (dev) — snapshot.py just raises
# a clear error there instead of failing at import time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY alembic.ini .
COPY migrations ./migrations

# Non-root runtime user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# Gunicorn manages a pool of Uvicorn workers — the unit of horizontal scaling.
# Tune WEB_CONCURRENCY per CPU; run multiple replicas behind a load balancer.
#
# Migrations are NOT auto-run here yet: existing deployments were bootstrapped
# via create_all() (see main.py's lifespan), so they have no alembic_version
# row, and `alembic upgrade head` against an unstamped DB would try to replay
# every migration from scratch against tables that already exist. Once a
# database has been stamped at its current revision (one-time:
# `alembic stamp <rev> && alembic upgrade head`), it's safe to switch this
# CMD to `alembic upgrade head && gunicorn ...` so future migrations apply
# automatically on deploy.
ENV WEB_CONCURRENCY=4 PORT=8000
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY} -b 0.0.0.0:${PORT} --access-logfile -"]
