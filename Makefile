# ─── AI Product Analytics Copilot — Developer Makefile ───────────────────────
# Usage: make <target>

.PHONY: help dev dev-backend dev-frontend test test-unit test-integration lint \
        type-check migrate seed docker-up docker-down docker-logs clean format

.DEFAULT_GOAL := help

# Colors
CYAN  := \033[36m
RESET := \033[0m
BOLD  := \033[1m

help: ## Show this help
	@echo ""
	@echo "$(BOLD)AI Product Analytics Copilot$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-22s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ── Development ────────────────────────────────────────────────────────────────

dev: ## Start both backend + frontend in development mode
	@echo "Starting development servers..."
	@make -j2 dev-backend dev-frontend

dev-backend: ## Start FastAPI backend with hot reload
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Start Next.js frontend
	cd frontend && npm run dev

worker: ## Start Celery worker
	cd backend && celery -A app.tasks.celery_app worker \
		--loglevel=info \
		--concurrency=2 \
		--queues=investigations,default

beat: ## Start Celery beat scheduler
	cd backend && celery -A app.tasks.celery_app beat \
		--loglevel=info

flower: ## Start Flower (Celery monitor UI)
	cd backend && celery -A app.tasks.celery_app flower \
		--port=5555

# ── Testing ────────────────────────────────────────────────────────────────────

test: ## Run all tests
	cd backend && pytest tests/ -v --tb=short

test-unit: ## Run unit tests only
	cd backend && pytest tests/unit/ -v --tb=short --cov=app --cov-report=term-missing

test-integration: ## Run integration tests only
	cd backend && pytest tests/integration/ -v --tb=short

test-watch: ## Run tests in watch mode
	cd backend && pytest-watch tests/unit/ -- -v

coverage: ## Generate HTML coverage report
	cd backend && pytest tests/ --cov=app --cov-report=html
	@echo "Coverage report: backend/htmlcov/index.html"

# ── Code Quality ───────────────────────────────────────────────────────────────

lint: ## Lint Python with Ruff
	cd backend && ruff check app/ tests/

lint-fix: ## Auto-fix lint issues
	cd backend && ruff check --fix app/ tests/

format: ## Format Python with Ruff formatter
	cd backend && ruff format app/ tests/

type-check: ## Type-check with mypy
	cd backend && mypy app/ --ignore-missing-imports

frontend-lint: ## Lint TypeScript/React with ESLint
	cd frontend && npm run lint

frontend-type-check: ## TypeScript type check
	cd frontend && npm run type-check

# ── Database ───────────────────────────────────────────────────────────────────

migrate: ## Run Alembic database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new Alembic migration (name=<name>)
	cd backend && alembic revision --autogenerate -m "$(name)"

migrate-down: ## Rollback last migration
	cd backend && alembic downgrade -1

migrate-status: ## Show migration status
	cd backend && alembic current

seed: ## Seed database with realistic test data
	cd backend && python ../scripts/seed_data.py

seed-large: ## Seed with larger dataset (50K users)
	cd backend && SEED_USERS=50000 python ../scripts/seed_data.py

# ── Docker ─────────────────────────────────────────────────────────────────────

docker-up: ## Start all Docker services
	docker-compose up -d --build

docker-up-full: ## Start with monitoring (Prometheus + Grafana)
	docker-compose --profile monitoring up -d --build

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Follow all service logs
	docker-compose logs -f

docker-logs-backend: ## Follow backend logs only
	docker-compose logs -f backend

docker-shell: ## Open shell in backend container
	docker-compose exec backend /bin/bash

docker-psql: ## Connect to PostgreSQL in Docker
	docker-compose exec postgres psql -U postgres analytics_copilot

docker-clean: ## Remove all containers, volumes, and images
	docker-compose down -v --rmi all --remove-orphans

# ── Setup ──────────────────────────────────────────────────────────────────────

install: ## Install all dependencies (backend + frontend)
	cd backend && pip install poetry && poetry install --with dev
	cd frontend && npm install

setup: install ## Full project setup
	cp -n .env.example .env || true
	@echo "✅ .env created from .env.example"
	@echo "👉 Edit .env and add your GEMINI_API_KEY"

# ── Utilities ──────────────────────────────────────────────────────────────────

clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

health: ## Check service health
	@curl -sf http://localhost:8000/health | python -m json.tool || echo "Backend not running"
	@curl -sf http://localhost:3000 > /dev/null && echo "Frontend: OK" || echo "Frontend not running"
