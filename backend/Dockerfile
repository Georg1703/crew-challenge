# Backend image: the same image runs locally (target "dev") and in production (target "prod").
# Build: docker build -t crew-backend --target prod backend/
# Works on amd64 and arm64 (the Lightsail instance and Apple silicon).

ARG PYTHON_VERSION=3.13

# ---------------------------------------------------------------- base
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app

# ---------------------------------------------------------------- dependencies
FROM base AS deps-prod
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM base AS deps-dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project

# ---------------------------------------------------------------- dev (make dev mounts the code)
FROM deps-dev AS dev
ENV DJANGO_SETTINGS_MODULE=config.settings.local
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------- prod
FROM python:${PYTHON_VERSION}-slim AS prod
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production
# A fixed id, so the host can hand files to it (the CloudFront key: chown 10001, chmod 400).
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home /app app
WORKDIR /app
COPY --from=deps-prod /opt/venv /opt/venv
COPY --chown=app:app . .
# collectstatic needs a placeholder secret; the real one comes from the environment at runtime.
RUN DJANGO_SECRET_KEY=build-only-placeholder-$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n') \
    python manage.py collectstatic --noinput
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", \
     "--access-logfile", "-", "--forwarded-allow-ips", "*"]
