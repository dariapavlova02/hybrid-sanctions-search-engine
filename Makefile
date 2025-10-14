.PHONY: help build run test clean deploy update logs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker image
	docker build -t ai-service:latest .

run: ## Run container locally
	docker-compose up -d

stop: ## Stop container
	docker-compose down

test: ## Run tests
	poetry run python -m pytest tests/ -v

test-micro: ## Run micro-benchmarks
	poetry run python -m pytest tests/performance/test_micro_benchmarks.py -v -m perf_micro

test-perf: ## Run all performance tests
	poetry run python -m pytest tests/ -v -m "performance or perf_micro"

test-ascii: ## Run ASCII fastpath tests
	poetry run python -m pytest tests/integration/test_ascii_fastpath_equivalence.py tests/integration/test_ascii_fastpath_golden_integration.py -v

test-ascii-perf: ## Run ASCII fastpath performance tests
	poetry run python -m pytest tests/performance/test_ascii_fastpath_performance.py -v -m performance

ascii-parity: ## Run ASCII fastpath parity job
	poetry run python scripts/ascii_fastpath_parity.py

clean: ## Clean up containers and images
	docker-compose down -v
	docker rmi ai-service:latest || true

deploy: ## Deploy to server
	@echo "Deploying to server..."
	git push origin main
	ssh user@server "cd /path/to/project && git pull && make update"

update: ## Update running container
	@echo "Updating container..."
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

logs: ## Show container logs
	docker-compose logs -f ai-service

status: ## Show container status
	docker-compose ps

health: ## Check service health
	curl -f http://localhost:8000/health || echo "Service not healthy"

install-deps: ## Install dependencies
	poetry install

download-models: ## Download SpaCy models
	poetry run python -m spacy download en_core_web_sm
	poetry run python -m spacy download ru_core_news_sm
	poetry run python -m spacy download uk_core_news_sm

setup: install-deps download-models ## Setup development environment
	@echo "Development environment ready!"

dev: ## Run in development mode
	docker-compose --profile dev up -d ai-service-dev

prod: ## Run in production mode
	docker-compose up -d ai-service

restart: ## Restart service
	docker-compose restart ai-service

shell: ## Access container shell
	docker-compose exec ai-service /bin/bash

backup: ## Backup data directory
	tar -czf backup-$(shell date +%Y%m%d-%H%M%S).tar.gz data/

restore: ## Restore from backup (usage: make restore BACKUP_FILE=backup-20231201-120000.tar.gz)
	tar -xzf $(BACKUP_FILE) -C ./

# PROJECT_IP Configuration Commands
deploy-prod: ## Deploy to production with PROJECT_IP=192.168.6.11
	PROJECT_IP=192.168.6.11 APP_ENV=production ./scripts/quick-deploy.sh

deploy-local: ## Deploy locally with PROJECT_IP=127.0.0.1
	PROJECT_IP=127.0.0.1 APP_ENV=development ./scripts/quick-deploy.sh

deploy-dev: ## Deploy for development with PROJECT_IP=0.0.0.0
	PROJECT_IP=0.0.0.0 APP_ENV=development ./scripts/quick-deploy.sh

generate-nginx: ## Generate nginx configuration with current PROJECT_IP
	./scripts/generate-nginx-config.sh

quick-deploy: ## Interactive quick deployment
	./scripts/quick-deploy.sh