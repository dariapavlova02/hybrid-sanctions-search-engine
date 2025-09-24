#!/bin/bash
set -e

# AI Service Production Deployment Script
# =======================================

echo "🚀 AI Service Production Deployment"
echo "===================================="

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
SERVICE_NAME="ai-service-prod"
ES_CONTAINER="elasticsearch-prod"

# Functions
log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1"
    exit 1
}

log_warning() {
    echo "⚠️  $1"
}

check_requirements() {
    log_info "Checking deployment requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
    fi

    # Check files
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Docker Compose file not found: $COMPOSE_FILE"
    fi

    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found: $ENV_FILE"
    fi

    log_success "Requirements check passed"
}

setup_environment() {
    log_info "Setting up environment..."

    # Create necessary directories
    mkdir -p logs data ssl

    # Set permissions
    chmod 755 logs data

    # Generate secrets if needed
    if [[ ! -f ".env.secrets" ]]; then
        log_info "Generating secrets..."
        cat > .env.secrets << EOF
# Generated secrets - DO NOT COMMIT
ELASTICSEARCH_PASSWORD=$(openssl rand -base64 32)
DATABASE_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 64)
EOF
        chmod 600 .env.secrets
        log_success "Secrets generated"
    fi

    log_success "Environment setup complete"
}

health_check() {
    local service=$1
    local max_attempts=${2:-30}
    local wait_time=${3:-10}

    log_info "Health checking $service..."

    for ((i=1; i<=max_attempts; i++)); do
        if docker-compose -f "$COMPOSE_FILE" exec -T "$service" curl -f http://localhost:8000/health &>/dev/null; then
            log_success "$service is healthy"
            return 0
        fi

        log_info "Attempt $i/$max_attempts - waiting ${wait_time}s..."
        sleep "$wait_time"
    done

    log_error "$service health check failed after $max_attempts attempts"
}

elasticsearch_health_check() {
    log_info "Checking Elasticsearch health..."

    for ((i=1; i<=30; i++)); do
        if docker-compose -f "$COMPOSE_FILE" exec -T "$ES_CONTAINER" curl -f http://localhost:9200/_cluster/health &>/dev/null; then
            log_success "Elasticsearch is healthy"
            return 0
        fi

        log_info "ES health check attempt $i/30 - waiting 10s..."
        sleep 10
    done

    log_error "Elasticsearch health check failed"
}

load_data() {
    log_info "Loading initial data..."

    # Check if sanctions data exists
    if [[ -f "src/ai_service/data/sanctioned_persons.json" ]]; then
        log_info "Found sanctions data ($(wc -l < src/ai_service/data/sanctioned_persons.json) records)"

        # TODO: Add data loading script
        # docker-compose -f "$COMPOSE_FILE" exec "$SERVICE_NAME" python scripts/load_sanctions_data.py

        log_success "Data loading skipped (implement as needed)"
    else
        log_warning "No sanctions data found - will use MockSearchService"
    fi
}

verify_search_escalation() {
    log_info "Verifying search escalation configuration..."

    # Test that search is enabled
    docker-compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" python -c "
import os
print(f'ENABLE_SEARCH: {os.getenv(\"ENABLE_SEARCH\", \"not set\")}')
print(f'SEARCH_ESCALATION_THRESHOLD: {os.getenv(\"SEARCH_ESCALATION_THRESHOLD\", \"not set\")}')
print(f'VECTOR_SEARCH_THRESHOLD: {os.getenv(\"VECTOR_SEARCH_THRESHOLD\", \"not set\")}')
" || log_warning "Could not verify search configuration"

    log_success "Search escalation configuration checked"
}

# Main deployment steps
main() {
    log_info "Starting AI Service production deployment..."

    check_requirements
    setup_environment

    # Stop existing containers
    log_info "Stopping existing containers..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans

    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull

    # Build AI service
    log_info "Building AI service..."
    docker-compose -f "$COMPOSE_FILE" build ai-service

    # Start Elasticsearch first
    log_info "Starting Elasticsearch..."
    docker-compose -f "$COMPOSE_FILE" up -d elasticsearch
    elasticsearch_health_check

    # Start AI service
    log_info "Starting AI service..."
    docker-compose -f "$COMPOSE_FILE" up -d ai-service
    health_check ai-service

    # Start Nginx (if enabled)
    if docker-compose -f "$COMPOSE_FILE" config --services | grep -q nginx; then
        log_info "Starting Nginx..."
        docker-compose -f "$COMPOSE_FILE" up -d nginx
    fi

    # Load initial data
    load_data

    # Verify configuration
    verify_search_escalation

    # Show status
    log_info "Deployment status:"
    docker-compose -f "$COMPOSE_FILE" ps

    log_success "🎉 AI Service deployed successfully!"
    log_info "Service URL: http://localhost:8000"
    log_info "Health check: http://localhost:8000/health"
    log_info "Elasticsearch: http://localhost:9200"

    # Test search escalation
    log_info "Testing search escalation with Poroshenko query..."

    curl -X POST http://localhost:8000/api/v1/process \
         -H "Content-Type: application/json" \
         -d '{"text": "Порошенк Петро", "language": "uk", "enable_search": true}' \
         --silent --show-error || log_warning "Could not test search escalation"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log_info "Stopping services..."
        docker-compose -f "$COMPOSE_FILE" down
        log_success "Services stopped"
        ;;
    "restart")
        log_info "Restarting services..."
        docker-compose -f "$COMPOSE_FILE" restart
        log_success "Services restarted"
        ;;
    "logs")
        docker-compose -f "$COMPOSE_FILE" logs -f "${2:-ai-service}"
        ;;
    "status")
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
    "health")
        health_check ai-service 5 5
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|health}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - Show logs (optional service name)"
        echo "  status  - Show container status"
        echo "  health  - Quick health check"
        exit 1
        ;;
esac