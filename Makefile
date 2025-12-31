.PHONY: install locally run test lint format format-check check ci clean

install:
	@echo "📦 Installing dependencies..."
	uv sync --all-groups

# Setup for local development: install deps, fix linting, and format code
locally: install lint-fix format
	@echo "✅ Local setup complete!"

# Run the real-time ingestion service
run:
	@bash -c '\
	if [ -f .env ]; then \
		set -a; \
		source .env; \
		set +a; \
	fi; \
	if [ -z "$$COINBASE_CDP_KEY_FILE" ] && ! ls cdp_api_key-*.json 1>/dev/null 2>&1; then \
		echo "⚠️  Warning: CDP API key file not found"; \
		echo "   Place a cdp_api_key-*.json file in the current directory, or"; \
		echo "   set COINBASE_CDP_KEY_FILE to the path of your CDP key file"; \
	fi; \
	echo "🚀 Starting real-time Coinbase SPOT ingestion service..."; \
	uv run python -m src.main'

test:
	@if [ -d tests ] && [ -n "$$(find tests -name 'test_*.py' 2>/dev/null)" ]; then \
		uv run python -m pytest tests/ -v; \
	else \
		echo "⚠️  No tests found. Skipping tests."; \
	fi

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

