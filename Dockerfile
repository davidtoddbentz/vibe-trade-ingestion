FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Copy dependency files and source code
# vibe-trade-shared will be installed from GCP Artifact Registry
COPY pyproject.toml ./
COPY uv.lock ./
COPY src/ ./src/

# Install dependencies excluding vibe-trade-shared first
# For Docker build, we need to authenticate with Artifact Registry
# At runtime in Cloud Run, service account credentials work automatically
RUN cp pyproject.toml pyproject.toml.bak && \
    sed -i 's/"vibe-trade-shared>=0.1.1",//' pyproject.toml && \
    sed -i 's/, "vibe-trade-shared>=0.1.1"//' pyproject.toml && \
    sed -i '/\[\[tool.uv.index\]\]/,/explicit = true/d' pyproject.toml && \
    uv sync --no-dev --frozen && \
    mv pyproject.toml.bak pyproject.toml

# Install vibe-trade-shared from Artifact Registry using build-time authentication
# ARTIFACT_REGISTRY_ACCESS_TOKEN is required (provided by make docker-build)
ARG ARTIFACT_REGISTRY_ACCESS_TOKEN
RUN if [ -z "$ARTIFACT_REGISTRY_ACCESS_TOKEN" ]; then \
        echo "❌ ARTIFACT_REGISTRY_ACCESS_TOKEN is required for build"; \
        exit 1; \
    fi && \
    uv pip install --python .venv/bin/python \
        --index-url "https://oauth2accesstoken:$ARTIFACT_REGISTRY_ACCESS_TOKEN@us-central1-python.pkg.dev/vibe-trade-475704/vibe-trade-python/simple/" \
        --extra-index-url https://pypi.org/simple/ \
        "vibe-trade-shared>=0.1.1" && \
    .venv/bin/python -c "import vibe_trade_shared; print('✅ vibe_trade_shared installed and importable')"

# Expose port (Cloud Run requires this, even for background jobs)
ENV PORT=8080
EXPOSE 8080

# Run the continuous ingestion service (do NOT use `uv run` at runtime)
CMD ["sh", "-c", ".venv/bin/python -m src.main"]


