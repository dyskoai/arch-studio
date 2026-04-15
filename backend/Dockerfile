FROM python:3.12-slim
WORKDIR /app

RUN pip install uv

# Install dependencies first (layer cache)
COPY backend/pyproject.toml .
RUN uv pip install --system --no-cache .

# Copy application code
COPY backend/ .

# best-practices.md lives at repo root; pipeline.py resolves it via parents[3]
# (/app/app/agents/pipeline.py → parents[3] = / → /best-practices.md)
COPY best-practices.md /best-practices.md

ENV PORT=8080
CMD ["python", "main.py"]
