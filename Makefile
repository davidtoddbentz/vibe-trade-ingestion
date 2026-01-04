.PHONY: install locally run test lint format format-check check ci clean \
	docker-build docker-push docker-build-push deploy deploy-image force-revision

install:
	@echo "📦 Installing dependencies..."
	@echo "   Step 1: Installing other dependencies (excluding vibe-trade-shared)..."
	@cp pyproject.toml pyproject.toml.bak && \
	sed -i.bak2 's/"vibe-trade-shared>=0.1.1",//' pyproject.toml && \
	sed -i.bak2 's/, "vibe-trade-shared>=0.1.1"//' pyproject.toml && \
	sed -i.bak2 's/"vibe-trade-shared"//' pyproject.toml && \
	sed -i.bak2 '/\[\[tool.uv.index\]\]/,/explicit = true/d' pyproject.toml && \
	uv sync --all-groups --python 3.11 && \
	mv pyproject.toml.bak pyproject.toml && \
	rm -f pyproject.toml.bak2 || \
	(mv pyproject.toml.bak pyproject.toml; rm -f pyproject.toml.bak2; exit 1)
	@echo "   Step 2: Installing vibe-trade-shared from Artifact Registry..."
	@if [ -z "$$ARTIFACT_REGISTRY_ACCESS_TOKEN" ] && [ -f .env ]; then \
		export $$(grep -v '^#' .env | grep '^ARTIFACT_REGISTRY_ACCESS_TOKEN=' | xargs) 2>/dev/null || true; \
	fi; \
	if [ -z "$$ARTIFACT_REGISTRY_ACCESS_TOKEN" ]; then \
		ARTIFACT_REGISTRY_ACCESS_TOKEN=$$(gcloud auth print-access-token 2>/dev/null) || (echo "❌ Failed to get access token. Run: gcloud auth login"; exit 1); \
	fi; \
	uv pip install --python .venv/bin/python \
		--index-url "https://oauth2accesstoken:$$ARTIFACT_REGISTRY_ACCESS_TOKEN@us-central1-python.pkg.dev/vibe-trade-475704/vibe-trade-python/simple/" \
		--extra-index-url https://pypi.org/simple/ \
		"vibe-trade-shared>=0.1.1" || (echo "❌ Failed to install vibe-trade-shared"; exit 1)
	@echo "✅ All dependencies installed successfully!"

# Setup for local development: install deps, fix linting, and format code
locally: install lint-fix format
	@echo "✅ Local setup complete!"

# Run the real-time ingestion service
# Uses .env file (loaded by Python's load_dotenv in main.py)
# Environment variables must be set in .env file or as shell environment variables
run:
	@if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi; \
	@echo "🚀 Starting real-time ingestion service..."
	@.venv/bin/python -m src.main

test:
	@bash -c '\
	if [ ! -d "tests" ] || [ -z "$$(find tests -name \"test_*.py\" 2>/dev/null | head -1)" ]; then \
		echo "⚠️  No tests found. Skipping."; \
		exit 0; \
	fi; \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi; \
	echo "🧪 Running tests..."; \
	.venv/bin/python -m pytest tests/ -v'

test-cov:
	@bash -c '\
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi; \
	.venv/bin/python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=60'

lint:
	@if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi; \
	.venv/bin/python -m ruff check .

lint-fix:
	@if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi; \
	.venv/bin/python -m ruff check . --fix

format:
	@if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi; \
	.venv/bin/python -m ruff format .

format-check:
	@if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi; \
	.venv/bin/python -m ruff format --check .

check: lint format-check test-cov
	@echo "✅ All checks passed!"

ci: lint-fix format-check test-cov
	@echo "✅ CI checks passed!"

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/ coverage.xml
	rm -rf *.egg-info build/ dist/

# Docker commands - use environment variable or default
# Set ARTIFACT_REGISTRY_URL env var or it will use the default
ARTIFACT_REGISTRY_URL ?= us-central1-docker.pkg.dev/vibe-trade-475704/vibe-trade-ingestion
IMAGE_TAG := $(ARTIFACT_REGISTRY_URL)/vibe-trade-ingestion:latest

docker-build:
	@echo "🏗️  Building Docker image..."
	@echo "   Image: $(IMAGE_TAG)"
	@echo "   vibe-trade-shared will be installed from Artifact Registry in Docker"
	@echo "   Getting GCP access token for build..."
	@bash -c '\
		ACCESS_TOKEN=$$(gcloud auth print-access-token 2>/dev/null) || (echo "❌ Failed to get access token. Run: gcloud auth login"; exit 1); \
		cd .. && DOCKER_BUILDKIT=1 docker build --platform linux/amd64 \
			--build-arg ARTIFACT_REGISTRY_ACCESS_TOKEN="$$ACCESS_TOKEN" \
			-f vibe-trade-ingestion/Dockerfile \
			-t $(IMAGE_TAG) \
			.'
	@echo "✅ Build complete"

docker-push:
	@echo "📤 Pushing Docker image..."
	@echo "   Image: $(IMAGE_TAG)"
	docker push $(IMAGE_TAG)
	@echo "✅ Push complete"

docker-build-push: docker-build docker-push

# Deployment workflow
# Step 1: Build and push Docker image
# Step 2: Force Cloud Run to use the new image
# For infrastructure changes, run 'terraform apply' in vibe-trade-terraform separately
deploy: docker-build-push force-revision
	@echo ""
	@echo "✅ Code deployment complete!"

# Force Cloud Run to create a new revision with the latest image
# Uses environment variables or defaults
force-revision:
	@echo "🔄 Forcing Cloud Run to use latest image..."
	@SERVICE_NAME=$${SERVICE_NAME:-vibe-trade-ingestion} && \
		REGION=$${REGION:-us-central1} && \
		PROJECT_ID=$${PROJECT_ID:-vibe-trade-475704} && \
		IMAGE_REPO=$${ARTIFACT_REGISTRY_URL:-us-central1-docker.pkg.dev/vibe-trade-475704/vibe-trade-ingestion} && \
		echo "   Service: $$SERVICE_NAME" && \
		echo "   Region: $$REGION" && \
		echo "   Image: $$IMAGE_REPO/vibe-trade-ingestion:latest" && \
		gcloud run services update $$SERVICE_NAME \
			--region=$$REGION \
			--project=$$PROJECT_ID \
			--image=$$IMAGE_REPO/vibe-trade-ingestion:latest \
			2>&1 | grep -E "(Deploying|revision|Service URL|Done)" || (echo "⚠️  Update may have failed or no changes needed" && exit 1)

deploy-image: docker-build-push
	@echo ""
	@echo "✅ Image deployed!"
	@echo "📋 Run 'make force-revision' to update Cloud Run, or 'terraform apply' in vibe-trade-terraform for infrastructure changes"

