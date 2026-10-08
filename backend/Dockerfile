FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
ENV PYTHONPATH=/app/src
RUN uv sync --no-dev
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "claimshield.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
