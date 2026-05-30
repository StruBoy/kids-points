# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app


FROM base AS deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*
COPY requirements-prod.txt .
RUN pip install -r requirements-prod.txt


FROM base AS runtime
ENV DJANGO_DB_PATH=/data/db.sqlite3
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 1000 app

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY --chown=app:app . /app
RUN chmod +x scripts/docker-entrypoint.sh \
 && mkdir -p /data /app/media /app/staticfiles \
 && chown -R app:app /data /app/media /app/staticfiles

USER app
EXPOSE 8000
CMD ["./scripts/docker-entrypoint.sh"]
