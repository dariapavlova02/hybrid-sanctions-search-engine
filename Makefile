.PHONY: help install install-dev test test-cov lint clean docker-build docker-run docker-dev docker-stop

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $1, $2}'

install: ## Install production dependencies
	poetry install --no-dev

install-dev: ## Install all dependencies including development
	poetry install

test: ## Run tests
	poetry run pytest -v

test-cov: ## Run tests with coverage
	poetry run pytest --cov=src --cov-report=html --cov-report=term

lint: ## Run linting checks
	poetry run flake8 src/ tests/
	poetry run black --check src/ tests/
	poetry run isort --check-only src/ tests/

format: ## Format code
	poetry run black src/ tests/
	poetry run isort src/ tests/

clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

docker-build: ## Build Docker image
	docker build -t ai-service .

docker-run: ## Run production Docker container
	docker run -d --name ai-service -p 8000:8000 ai-service

docker-dev: ## Run development Docker container
	docker-compose --profile dev up --build ai-service-dev

docker-stop: ## Stop all Docker containers
	docker-compose down
	docker stop ai-service || true
	docker rm ai-service || true

start: ## Start the service locally
	poetry run python run_local.py

start-prod: ## Start the service in production mode
	APP_ENV=production poetry run uvicorn src.ai_service.main:app --host 0.0.0.0 --port 8000 --workers 2
