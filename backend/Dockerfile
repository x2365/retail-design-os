# --- RetailDesign OS API image ---------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Non-root runtime user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# Gunicorn manages a pool of Uvicorn workers — the unit of horizontal scaling.
# Tune WEB_CONCURRENCY per CPU; run multiple replicas behind a load balancer.
ENV WEB_CONCURRENCY=4
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY} -b 0.0.0.0:8000 --access-logfile -"]
