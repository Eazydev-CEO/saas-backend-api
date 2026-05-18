# syntax=docker/dockerfile:1.6
# ----------------------------------------------------------------------------
# Stage 1: builder — installs deps into a virtualenv we can copy out
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ARG REQUIREMENTS=development
COPY requirements/ /app/requirements/
RUN pip install --upgrade pip && pip install -r /app/requirements/${REQUIREMENTS}.txt

# ----------------------------------------------------------------------------
# Stage 2: runtime — slim image, non-root user, just the venv + code
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.development

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system --gid 1000 app \
    && adduser --system --uid 1000 --gid 1000 app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . /app

RUN chmod +x /app/scripts/entrypoint.sh /app/scripts/start-prod.sh
USER app

EXPOSE 8001
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]
