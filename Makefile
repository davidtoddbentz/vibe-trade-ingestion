.PHONY: install locally run test lint format format-check check ci clean batch-job scheduler \
	setup-clickhouse clickhouse-status clickhouse-stop init-db

install:
	@echo "📦 Installing dependencies..."
	uv sync --all-groups

# Setup for local development: install deps, fix linting, and format code
locally: install lint-fix format
	@echo "✅ Local setup complete!"

# Setup ClickHouse using Docker
setup-clickhouse:
	@bash -c '\
	if [ -f .env ]; then \
		set -a; \
		source .env; \
		set +a; \
	fi; \
	if [ -z "$$CLICKHOUSE_DATABASE" ] && [ -z "$$CLICKHOUSE_DB" ]; then \
		CLICKHOUSE_DB="default"; \
	elif [ -n "$$CLICKHOUSE_DATABASE" ]; then \
		CLICKHOUSE_DB="$$CLICKHOUSE_DATABASE"; \
	else \
		CLICKHOUSE_DB="$$CLICKHOUSE_DB"; \
	fi; \
	if [ -z "$$CLICKHOUSE_USERNAME" ] && [ -z "$$CLICKHOUSE_USER" ]; then \
		CLICKHOUSE_USER="default"; \
	elif [ -n "$$CLICKHOUSE_USERNAME" ]; then \
		CLICKHOUSE_USER="$$CLICKHOUSE_USERNAME"; \
	else \
		CLICKHOUSE_USER="$$CLICKHOUSE_USER"; \
	fi; \
	CLICKHOUSE_PASS="$$CLICKHOUSE_PASSWORD"; \
	echo "🐳 Setting up ClickHouse in Docker..."; \
	if docker ps -a --format "{{.Names}}" | grep -q "^clickhouse$$"; then \
		echo "   ClickHouse container already exists"; \
		if docker ps --format "{{.Names}}" | grep -q "^clickhouse$$"; then \
			echo "   ✅ ClickHouse is already running"; \
		else \
			echo "   Starting existing ClickHouse container..."; \
			docker start clickhouse; \
			echo "   ✅ ClickHouse started"; \
		fi; \
	else \
		echo "   Creating new ClickHouse container..."; \
		docker run -d \
			--name clickhouse \
			-p 8123:8123 \
			-p 9000:9000 \
			clickhouse/clickhouse-server:latest; \
		echo "   ✅ ClickHouse container created and started"; \
		echo "   Waiting for ClickHouse to be ready..."; \
		sleep 5; \
		for i in 1 2 3 4 5; do \
			if curl -s http://localhost:8123/ping > /dev/null 2>&1; then \
				echo "   ✅ ClickHouse is ready!"; \
				break; \
			fi; \
			echo "   Waiting... (attempt $$i/5)"; \
			sleep 2; \
		done; \
	fi; \
	echo "   Configuring database and user..."; \
	if [ "$$CLICKHOUSE_DB" != "default" ]; then \
		echo "   Creating database: $$CLICKHOUSE_DB"; \
		docker exec clickhouse clickhouse-client --query "CREATE DATABASE IF NOT EXISTS $$CLICKHOUSE_DB" 2>/dev/null || \
		echo "   ⚠️  Could not create database (may already exist)"; \
	fi; \
	if [ "$$CLICKHOUSE_USER" != "default" ]; then \
		echo "   Creating user: $$CLICKHOUSE_USER"; \
		if [ -n "$$CLICKHOUSE_PASS" ]; then \
			docker exec clickhouse clickhouse-client --query "CREATE USER IF NOT EXISTS $$CLICKHOUSE_USER IDENTIFIED BY '\''$$CLICKHOUSE_PASS'\''" 2>/dev/null || \
			docker exec clickhouse clickhouse-client --query "ALTER USER IF EXISTS $$CLICKHOUSE_USER IDENTIFIED BY '\''$$CLICKHOUSE_PASS'\''" 2>/dev/null || \
			echo "   ⚠️  Could not configure user (trying to grant permissions anyway)"; \
		else \
			docker exec clickhouse clickhouse-client --query "CREATE USER IF NOT EXISTS $$CLICKHOUSE_USER" 2>/dev/null || \
			echo "   ⚠️  Could not create user"; \
		fi; \
		if [ "$$CLICKHOUSE_DB" != "default" ]; then \
			echo "   Granting permissions on $$CLICKHOUSE_DB to $$CLICKHOUSE_USER"; \
			docker exec clickhouse clickhouse-client --query "GRANT ALL ON $$CLICKHOUSE_DB.* TO $$CLICKHOUSE_USER" 2>/dev/null || \
			echo "   ⚠️  Could not grant permissions"; \
		fi; \
	fi; \
	echo "   ✅ ClickHouse setup complete!"'

# Check ClickHouse status
clickhouse-status:
	@echo "🔍 Checking ClickHouse status..."
	@if docker ps --format '{{.Names}}' | grep -q '^clickhouse$$'; then \
		echo "   ✅ ClickHouse container is running"; \
		if curl -s http://localhost:8123/ping > /dev/null 2>&1; then \
			echo "   ✅ ClickHouse is responding to requests"; \
		else \
			echo "   ⚠️  ClickHouse container is running but not responding"; \
		fi; \
	else \
		echo "   ❌ ClickHouse container is not running"; \
		echo "   Run 'make setup-clickhouse' to start it"; \
	fi

# Stop ClickHouse
clickhouse-stop:
	@echo "🛑 Stopping ClickHouse..."
	@if docker ps --format '{{.Names}}' | grep -q '^clickhouse$$'; then \
		docker stop clickhouse; \
		echo "   ✅ ClickHouse stopped"; \
	else \
		echo "   ⚠️  ClickHouse is not running"; \
	fi

# Initialize database tables
init-db:
	@bash -c '\
	if [ -f .env ]; then \
		set -a; \
		source .env; \
		set +a; \
	fi; \
	echo "🗄️  Initializing ClickHouse database..."; \
	uv run python init_db.py'

# Run the ingestion service (sets up ClickHouse, initializes DB, then runs batch job)
run: setup-clickhouse init-db batch-job

# Run batch job once
batch-job:
	@bash -c '\
	if [ -f .env ]; then \
		set -a; \
		source .env; \
		set +a; \
	fi; \
	if [ -z "$$CLICKHOUSE_HOST" ]; then \
		echo "⚠️  Warning: CLICKHOUSE_HOST not set"; \
		echo "   Set it in .env file or export CLICKHOUSE_HOST=localhost"; \
	fi; \
	if [ -z "$$COINBASE_API_KEY" ]; then \
		echo "⚠️  Warning: COINBASE_API_KEY not set"; \
		echo "   Set it in .env file"; \
	fi; \
	echo "🚀 Running batch ingestion job..."; \
	uv run python batch_job.py'

# Run scheduler (runs batch job periodically)
scheduler:
	@bash -c '\
	if [ -f .env ]; then \
		set -a; \
		source .env; \
		set +a; \
	fi; \
	echo "🚀 Starting ingestion scheduler..."; \
	uv run python scheduler.py'

test:
	uv run python -m pytest tests/ -v

test-cov:
	uv run python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=60

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

check: lint format-check test-cov
	@echo "✅ All checks passed!"

ci: lint-fix format-check test-cov
	@echo "✅ CI checks passed!"

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/ coverage.xml
	rm -rf *.egg-info build/ dist/

