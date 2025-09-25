#!/bin/bash

# Docker Build Fix Script for AI Service
# Resolves registry authentication and caching issues

echo "🔧 AI SERVICE DOCKER BUILD FIX SCRIPT"
echo "======================================"

# Check Docker is running
echo "1. Checking Docker daemon..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker daemon is not running. Please start Docker first:"
    echo "   sudo systemctl start docker"
    echo "   sudo systemctl enable docker"
    exit 1
fi
echo "✅ Docker daemon is running"

# Clean up Docker cache and dangling images
echo "2. Cleaning Docker cache..."
docker system prune -f
docker builder prune -f
echo "✅ Docker cache cleaned"

# Remove any existing containers and images
echo "3. Removing existing AI service containers..."
docker-compose -f docker-compose.prod.yml down --remove-orphans
docker rmi $(docker images | grep ai-service | awk '{print $3}') 2>/dev/null || echo "No existing AI service images to remove"
echo "✅ Existing containers removed"

# Alternative registry options
echo "4. Testing registry connectivity..."

# Test Docker Hub connectivity
if curl -s --max-time 10 https://registry-1.docker.io/v2/ >/dev/null; then
    echo "✅ Docker Hub accessible"
    REGISTRY_OK=true
else
    echo "⚠️ Docker Hub access issues detected"
    REGISTRY_OK=false
fi

# Configure registry mirrors if needed
if [ "$REGISTRY_OK" = false ]; then
    echo "5. Configuring registry mirrors..."
    sudo mkdir -p /etc/docker
    cat << EOF | sudo tee /etc/docker/daemon.json
{
    "registry-mirrors": [
        "https://mirror.gcr.io",
        "https://docker.mirrors.ustc.edu.cn",
        "https://reg-mirror.qiniu.com"
    ],
    "dns": ["8.8.8.8", "1.1.1.1"]
}
EOF
    sudo systemctl reload docker
    echo "✅ Registry mirrors configured"
fi

# Try building with the new production Dockerfile
echo "6. Building AI service with production Dockerfile..."
echo "   Using: docker-compose -f docker-compose.prod.yml build --no-cache ai-service"

if docker-compose -f docker-compose.prod.yml build --no-cache ai-service; then
    echo "✅ Docker build successful!"

    echo "7. Running quick verification..."
    if docker-compose -f docker-compose.prod.yml up -d elasticsearch; then
        sleep 10  # Wait for Elasticsearch to start

        if docker-compose -f docker-compose.prod.yml up -d ai-service; then
            echo "✅ Services started successfully!"

            echo "8. Health check..."
            sleep 15  # Wait for service to initialize

            if curl -f http://localhost:8000/health 2>/dev/null; then
                echo "✅ AI Service is healthy and responding!"
            else
                echo "⚠️ AI Service started but health check failed. Check logs:"
                echo "   docker-compose -f docker-compose.prod.yml logs ai-service"
            fi
        else
            echo "❌ Failed to start AI service. Check logs:"
            echo "   docker-compose -f docker-compose.prod.yml logs"
        fi
    else
        echo "❌ Failed to start Elasticsearch. Check logs:"
        echo "   docker-compose -f docker-compose.prod.yml logs elasticsearch"
    fi
else
    echo "❌ Docker build failed. Trying alternative approaches..."

    # Try with different base images
    echo "7. Trying with alternative base image..."

    # Create emergency fallback Dockerfile
    cat << 'EOF' > Dockerfile.emergency
# Emergency fallback using Alpine Linux
FROM alpine:3.18

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    gcc \
    musl-dev \
    linux-headers \
    curl

# Create app directory
WORKDIR /app
COPY . .

# Install minimal Python dependencies
RUN pip3 install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pydantic \
    pydantic-settings \
    requests \
    pyyaml

# Expose port
EXPOSE 8000

# Simple health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run service
CMD ["python3", "-m", "uvicorn", "src.ai_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

    echo "   Created emergency Dockerfile"
    echo "   To use: docker build -f Dockerfile.emergency -t ai-service-emergency ."
fi

echo ""
echo "======================================"
echo "🎯 NEXT STEPS:"
echo "1. If build successful: docker-compose -f docker-compose.prod.yml up -d"
echo "2. Check logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "3. Test API: curl http://localhost:8000/health"
echo "4. Monitor: docker-compose -f docker-compose.prod.yml ps"
echo ""
echo "🚨 TROUBLESHOOTING:"
echo "- For registry issues: Check internet connection and DNS"
echo "- For build failures: Review Dockerfile and dependencies"
echo "- For runtime issues: Check environment variables and ports"
echo "======================================"