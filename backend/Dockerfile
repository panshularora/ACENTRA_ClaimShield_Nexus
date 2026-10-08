FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Install pinned dependencies from the committed lock first so this layer caches across source edits.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project

COPY src ./src
RUN uv sync --frozen

EXPOSE 8000
CMD ["uvicorn", "claimshield.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
