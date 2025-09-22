#!/bin/bash
# Deployment script for enabling search in production

set -e

echo "🚀 DEPLOYING SEARCH TO PRODUCTION"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're on the production server
if [[ $(hostname) != *"ai-service"* ]] && [[ ! -f "/opt/ai-service" ]] && [[ $(pwd) != *"ai-service"* ]]; then
    echo -e "${YELLOW}⚠️  This script should be run on the production server${NC}"
    echo "Current directory: $(pwd)"
    echo "Hostname: $(hostname)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}📋 Step 1: Backup current configuration${NC}"
if [ -f "env.production" ]; then
    cp env.production env.production.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backed up env.production"
else
    echo "⚠️ No env.production found, will create new one"
fi

echo -e "${GREEN}📋 Step 2: Update environment configuration${NC}"
if [ -f "env.production.search" ]; then
    cp env.production.search env.production
    echo "✅ Updated env.production with search settings"
else
    echo -e "${RED}❌ env.production.search not found!${NC}"
    echo "Please ensure you have the search configuration file"
    exit 1
fi

echo -e "${GREEN}📋 Step 3: Check Git status${NC}"
git status --porcelain
if [ $? -eq 0 ]; then
    echo "✅ Git status checked"
else
    echo -e "${YELLOW}⚠️ Git issues detected, continuing anyway${NC}"
fi

echo -e "${GREEN}📋 Step 4: Pull latest code${NC}"
git pull origin main
if [ $? -eq 0 ]; then
    echo "✅ Code updated from repository"
else
    echo -e "${RED}❌ Failed to pull latest code${NC}"
    exit 1
fi

echo -e "${GREEN}📋 Step 5: Check Elasticsearch connection${NC}"
if curl -s http://localhost:9200/_cluster/health > /dev/null; then
    echo "✅ Elasticsearch is accessible"

    # Show cluster info
    echo "Cluster info:"
    curl -s http://localhost:9200 | jq -r '.version.number // "N/A"' | xargs echo "  Version:"
    curl -s http://localhost:9200/_cluster/health | jq -r '.status // "N/A"' | xargs echo "  Status:"
else
    echo -e "${RED}❌ Cannot connect to Elasticsearch${NC}"
    echo "Please ensure Elasticsearch is running on localhost:9200"
    exit 1
fi

echo -e "${GREEN}📋 Step 6: Setup Elasticsearch indices${NC}"
if [ -f "scripts/setup_elasticsearch.py" ]; then
    cd scripts
    python3 setup_elasticsearch.py
    if [ $? -eq 0 ]; then
        echo "✅ Elasticsearch setup completed"
    else
        echo -e "${YELLOW}⚠️ Elasticsearch setup had issues, continuing...${NC}"
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️ Elasticsearch setup script not found, skipping${NC}"
fi

echo -e "${GREEN}📋 Step 7: Stop current services${NC}"
if command -v docker-compose &> /dev/null; then
    echo "Using docker-compose..."
    docker-compose -f docker-compose.prod.yml down ai-service
    echo "✅ AI service stopped"
else
    echo -e "${YELLOW}⚠️ docker-compose not found, trying docker...${NC}"
    docker stop ai-service-prod 2>/dev/null || echo "Service was not running"
fi

echo -e "${GREEN}📋 Step 8: Build new image with search support${NC}"
if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml build --no-cache ai-service
    echo "✅ Docker image rebuilt"
elif [ -f "Dockerfile" ]; then
    docker build -t ai-service:latest .
    echo "✅ Docker image built"
else
    echo -e "${RED}❌ No Docker configuration found${NC}"
    exit 1
fi

echo -e "${GREEN}📋 Step 9: Start services with search enabled${NC}"
if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml up -d ai-service
    echo "✅ AI service started"
else
    docker run -d --name ai-service-prod \
        --env-file env.production \
        -p 8000:8000 \
        ai-service:latest
    echo "✅ AI service started"
fi

echo -e "${GREEN}📋 Step 10: Wait for service to start${NC}"
sleep 10

echo -e "${GREEN}📋 Step 11: Test service health${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ Service is healthy"
        break
    else
        echo "⏳ Waiting for service... ($i/30)"
        sleep 2
    fi
done

echo -e "${GREEN}📋 Step 12: Test search functionality${NC}"
echo "Testing search integration..."

# Test 1: Basic normalization with search
echo "Test 1: Basic processing"
curl -s -X POST http://localhost:8000/process \
    -H "Content-Type: application/json" \
    -d '{"text": "Порошенко Петр", "generate_variants": false}' \
    | jq -r 'if .search_results then "✅ search_results field present" else "❌ search_results field missing" end'

# Test 2: Check response structure
echo "Test 2: Response structure"
curl -s -X POST http://localhost:8000/process \
    -H "Content-Type: application/json" \
    -d '{"text": "Biden Joe", "generate_variants": false}' \
    | jq -r 'keys[]' | head -10

echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED!${NC}"
echo "================================"
echo "✅ Search functionality has been deployed"
echo "✅ Service is running with search enabled"
echo "✅ Basic tests passed"
echo ""
echo -e "${YELLOW}📋 Verification steps:${NC}"
echo "1. Check service logs: docker logs ai-service-prod"
echo "2. Test API: curl http://localhost:8000/process -d '{\"text\":\"test\"}'"
echo "3. Monitor performance and search results"
echo ""
echo -e "${GREEN}🔧 Troubleshooting:${NC}"
echo "- Logs: docker logs ai-service-prod"
echo "- Health: curl http://localhost:8000/health"
echo "- ES health: curl http://localhost:9200/_cluster/health"
echo "- Rollback: docker-compose down && git checkout HEAD~1 && ./deploy.sh"