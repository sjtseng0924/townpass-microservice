FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

CMD exec uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
