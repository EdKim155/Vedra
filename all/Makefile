# Cars Bot - Makefile
# Quick commands for development and deployment

.PHONY: help install dev-install test lint format run-bot run-monitor create-session setup clean docker-build docker-up docker-down migrate

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Cars Bot - Available Commands"
	@echo "=============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov pytest-mock httpx black ruff mypy

# Development
test: ## Run tests
	pytest tests/ -v --cov=src/cars_bot --cov-report=html --cov-report=term

lint: ## Run linters
	ruff check src/ tests/
	mypy src/

format: ## Format code
	black src/ tests/ scripts/
	ruff check --fix src/ tests/ scripts/

# Running services
run-bot: ## Run Telegram bot
	python scripts/run_bot.py

run-monitor: ## Run channel monitor
	python -m cars_bot.monitor.monitor

# Celery services
run-celery-worker: ## Run Celery worker
	./scripts/start_celery_worker.sh

run-celery-beat: ## Run Celery Beat scheduler
	./scripts/start_celery_beat.sh

stop-celery: ## Stop all Celery processes
	./scripts/stop_celery.sh

celery-status: ## Show Celery worker status
	celery -A cars_bot.celery_app inspect active

celery-stats: ## Show Celery statistics
	celery -A cars_bot.celery_app inspect stats

celery-purge: ## Purge all Celery queues (use with caution!)
	celery -A cars_bot.celery_app purge -f

# Setup
create-session: ## Create Telegram user session for monitoring
	python scripts/create_session.py

test-session: ## Test existing Telegram session
	python scripts/create_session.py test

setup-sheets: ## Create Google Sheets template
	python scripts/create_sheets_template.py

# Database
migrate: ## Run database migrations
	alembic upgrade head

migrate-down: ## Rollback one migration
	alembic downgrade -1

migrate-create: ## Create new migration (use NAME=migration_name)
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME is required. Usage: make migrate-create NAME=migration_name"; \
		exit 1; \
	fi
	alembic revision --autogenerate -m "$(NAME)"

# Docker
docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start all services in Docker
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-restart: ## Restart Docker services
	docker-compose restart

# Cleanup
clean: ## Clean temporary files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

clean-logs: ## Clean log files
	rm -rf logs/*.log

# Environment
check-env: ## Check if required environment variables are set
	@echo "Checking environment variables..."
	@python -c "from cars_bot.config import get_settings; s = get_settings(); print('✅ Environment OK')" || echo "❌ Environment setup failed"

# Development helpers
shell: ## Open Python shell with project context
	python -c "from cars_bot.config import get_settings; from cars_bot.database.session import init_database; init_database(get_settings().database_url); print('✅ Ready. Use get_settings() and db functions.'); import code; code.interact(local=locals())"

# Production
deploy: ## Deploy to production (placeholder)
	@echo "Deploying to production..."
	@echo "This should be implemented based on your deployment strategy"

# Monitoring
logs: ## Show monitor logs (today)
	tail -f logs/monitor_$$(date +%Y-%m-%d).log

logs-bot: ## Show bot logs (today)
	tail -f logs/bot_$$(date +%Y-%m-%d).log

# Quick start
quickstart: install migrate create-session ## Quick setup for new installation
	@echo ""
	@echo "✅ Quick start completed!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env file with your credentials"
	@echo "2. Run: make run-monitor  (in one terminal)"
	@echo "3. Run: make run-bot      (in another terminal)"
	@echo ""
