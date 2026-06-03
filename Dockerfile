FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

FROM python:3.11-slim AS runner

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY .entrypoints/*.sh /
RUN chmod +x /*.sh

COPY ./src ./src
COPY ./data ./data

EXPOSE 8000
ENTRYPOINT ["sh", "/django-entrypoint.sh"]
