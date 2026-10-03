FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app

COPY services/data/pyproject.toml services/data/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY services/data/ .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "liqi_data.main:app", "--host", "0.0.0.0", "--port", "8000"]
