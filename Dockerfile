FROM python:3.11-slim

WORKDIR /app

# Install git (needed for Git-based dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Copy dependency files and source code
COPY pyproject.toml ./
COPY uv.lock ./
COPY src/ ./src/

# Install dependencies (vibe-trade-shared from Git)
# GITHUB_TOKEN is optional - only needed for private repos
ARG GITHUB_TOKEN
RUN if [ -n "$GITHUB_TOKEN" ]; then \
        git config --global url."https://$GITHUB_TOKEN@github.com/".insteadOf "https://github.com/"; \
    fi && \
    uv sync --no-dev --frozen --python 3.11 && \
    if [ -n "$GITHUB_TOKEN" ]; then \
        git config --global --unset url."https://$GITHUB_TOKEN@github.com/".insteadOf; \
    fi

# Expose port (Cloud Run requires this, even for background jobs)
ENV PORT=8080
EXPOSE 8080

# Run the continuous ingestion service (do NOT use `uv run` at runtime)
CMD ["sh", "-c", ".venv/bin/python -m src.main"]


