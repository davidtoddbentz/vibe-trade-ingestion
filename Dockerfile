FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Copy dependency files and source code
COPY pyproject.toml ./
COPY uv.lock ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --no-dev --frozen

# Expose port (Cloud Run requires this, even for background jobs)
ENV PORT=8080
EXPOSE 8080

# Run the continuous ingestion service
CMD ["uv", "run", "python", "-m", "src.main"]

