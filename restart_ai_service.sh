#!/bin/bash

echo "🔄 RESTARTING AI SERVICE TO APPLY METRICS FIXES"
echo "================================================"

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: docker-compose.prod.yml not found!"
    echo "   Please run this script from the ai-service root directory"
    exit 1
fi

# Step 1: Stop the current services
echo "1. Stopping current AI service containers..."
docker-compose -f docker-compose.prod.yml down

# Step 2: Remove the old AI service image to force rebuild
echo "2. Removing old AI service image..."
docker rmi $(docker images | grep "ai-service" | awk '{print $3}') 2>/dev/null || echo "   No existing AI service images to remove"

# Step 3: Rebuild the service with latest code changes
echo "3. Rebuilding AI service with metrics fixes..."
docker-compose -f docker-compose.prod.yml build --no-cache ai-service

# Step 4: Start the services
echo "4. Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Step 5: Wait for services to be ready
echo "5. Waiting for services to start..."
sleep 20

# Step 6: Check service health
echo "6. Checking service health..."
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "✅ AI Service is healthy and running!"

    # Test the API
    echo "7. Testing API with a simple request..."
    echo "   Making request to /api/normalize..."

    response=$(curl -s -X POST http://localhost:8000/api/normalize \
        -H "Content-Type: application/json" \
        -d '{"text": "Іванов Іван Іванович"}' || echo "curl failed")

    if echo "$response" | grep -q '"success"'; then
        if echo "$response" | grep -q "metrics.*not defined"; then
            echo "❌ STILL HAS METRICS ERROR:"
            echo "$response" | jq '.' || echo "$response"
        else
            echo "✅ API working correctly!"
            echo "   Response preview:"
            echo "$response" | jq '.' || echo "$response"
        fi
    else
        echo "⚠️ API response unclear:"
        echo "$response"
    fi

else
    echo "❌ Service health check failed!"
    echo "   Checking service logs..."
    docker-compose -f docker-compose.prod.yml logs --tail=20 ai-service
fi

echo ""
echo "================================================"
echo "RESTART COMPLETE"
echo ""
echo "📋 Next steps:"
echo "   - Check logs: docker-compose -f docker-compose.prod.yml logs -f ai-service"
echo "   - Check status: docker-compose -f docker-compose.prod.yml ps"
echo "   - Test API: curl http://localhost:8000/health"
echo "================================================"