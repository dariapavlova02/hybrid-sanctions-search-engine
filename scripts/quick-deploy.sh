#!/bin/bash
# Quick deployment script with PROJECT_IP configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================="
echo "AI Service - Quick Deployment Script"
echo "==================================================${NC}"

# Default configuration
DEFAULT_PROJECT_IP="192.168.6.11"
DEFAULT_ENV="production"

# Get PROJECT_IP from user or use default
if [ -z "$PROJECT_IP" ]; then
    echo -e "${YELLOW}Enter PROJECT_IP (default: $DEFAULT_PROJECT_IP):${NC}"
    read -r input_ip
    PROJECT_IP="${input_ip:-$DEFAULT_PROJECT_IP}"
fi

# Get environment from user or use default
if [ -z "$APP_ENV" ]; then
    echo -e "${YELLOW}Enter APP_ENV (development/production, default: $DEFAULT_ENV):${NC}"
    read -r input_env
    APP_ENV="${input_env:-$DEFAULT_ENV}"
fi

echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  PROJECT_IP: $PROJECT_IP"
echo "  APP_ENV: $APP_ENV"
echo ""

# Export environment variables
export PROJECT_IP
export APP_ENV

# Generate nginx configuration if needed
if [ "$APP_ENV" = "production" ]; then
    echo -e "${BLUE}Generating nginx configuration...${NC}"
    chmod +x scripts/generate-nginx-config.sh
    ./scripts/generate-nginx-config.sh
fi

# Choose docker-compose file based on environment
if [ "$APP_ENV" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    echo -e "${BLUE}Using production configuration${NC}"
else
    COMPOSE_FILE="docker-compose.yml"
    echo -e "${BLUE}Using development configuration${NC}"
fi

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose -f "$COMPOSE_FILE" down || true

# Build and start containers
echo -e "${BLUE}Building and starting containers...${NC}"
docker-compose -f "$COMPOSE_FILE" up --build -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check service health
echo -e "${BLUE}Checking service health...${NC}"
if curl -sf "http://$PROJECT_IP:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ AI Service is running on http://$PROJECT_IP:8000${NC}"
else
    echo -e "${RED}❌ AI Service health check failed${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    docker-compose -f "$COMPOSE_FILE" logs ai-service
fi

# Show service URLs
echo ""
echo -e "${GREEN}Service URLs:${NC}"
echo "  AI Service: http://$PROJECT_IP:8000"
echo "  Health Check: http://$PROJECT_IP:8000/health"
echo "  API Docs: http://$PROJECT_IP:8000/docs"

if [ "$APP_ENV" = "production" ]; then
    echo "  Elasticsearch: http://$PROJECT_IP:9200"
    echo "  Kibana: http://$PROJECT_IP:5601"
fi

echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${BLUE}Use 'docker-compose -f $COMPOSE_FILE logs -f' to view logs${NC}"
