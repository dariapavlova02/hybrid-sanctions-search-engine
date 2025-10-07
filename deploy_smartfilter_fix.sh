#!/bin/bash

# Deploy SmartFilter Fix Script
# This script deploys the smartfilter fix that resolves the issue with Ukrainian names being skipped

set -e

echo "=========================================="
echo "Deploying SmartFilter Fix"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running in Docker
if [ -f /.dockerenv ]; then
    DEPLOY_MODE="docker"
    print_status "Detected Docker environment"
elif [ -n "$KUBERNETES_SERVICE_HOST" ]; then
    DEPLOY_MODE="kubernetes"
    print_status "Detected Kubernetes environment"
else
    DEPLOY_MODE="local"
    print_status "Detected local/systemd environment"
fi

# Backup current configuration
print_status "Creating backup..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup modified files
cp src/ai_service/layers/smart_filter/name_detector.py "$BACKUP_DIR/" 2>/dev/null || true
cp src/ai_service/layers/smart_filter/confidence_scorer.py "$BACKUP_DIR/" 2>/dev/null || true
cp src/ai_service/data/dicts/smart_filter_patterns.py "$BACKUP_DIR/" 2>/dev/null || true
print_status "Backup created in $BACKUP_DIR"

# Apply the fix (already done in the code)
print_status "SmartFilter fix already applied in code:"
echo "  - name_detector.py: Increased name confidence (0.3→0.8, 0.7→0.9)"
echo "  - confidence_scorer.py: Increased name weight (0.4→0.8)"
echo "  - smart_filter_patterns.py: Updated patterns"

# Test the fix locally first
print_status "Testing fix locally..."
python -c "
from src.ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
service = SmartFilterService()
result = service.should_process_text('Петро Порошенко')
if result.should_process:
    print('  ✓ Test passed: Петро Порошенко -> should_process=True')
else:
    print('  ✗ Test failed: Петро Порошенко -> should_process=False')
    exit(1)
" || { print_error "Local test failed!"; exit 1; }

# Deploy based on environment
case $DEPLOY_MODE in
    docker)
        print_status "Rebuilding Docker image..."
        docker-compose build --no-cache ai-service
        
        print_status "Restarting Docker container..."
        docker-compose restart ai-service
        
        print_status "Waiting for service to be ready..."
        sleep 10
        
        # Health check
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            print_status "Service is healthy"
        else
            print_error "Service health check failed"
            exit 1
        fi
        ;;
        
    kubernetes)
        print_status "Building and pushing Docker image..."
        docker build -t ai-service:latest .
        # Assuming you have a registry configured
        # docker tag ai-service:latest your-registry/ai-service:latest
        # docker push your-registry/ai-service:latest
        
        print_status "Rolling out Kubernetes deployment..."
        kubectl rollout restart deployment/ai-service -n default
        
        print_status "Waiting for rollout to complete..."
        kubectl rollout status deployment/ai-service -n default
        
        print_status "Checking pod status..."
        kubectl get pods -l app=ai-service -n default
        ;;
        
    local)
        print_status "Restarting local service..."
        
        # Try systemd first
        if systemctl is-active --quiet ai-service; then
            print_status "Restarting systemd service..."
            sudo systemctl restart ai-service
            sleep 5
            if systemctl is-active --quiet ai-service; then
                print_status "Service restarted successfully"
            else
                print_error "Service restart failed"
                exit 1
            fi
        else
            # Try to find and restart uvicorn/gunicorn
            print_status "Looking for running Python service..."
            PID=$(ps aux | grep -E "uvicorn.*ai_service|gunicorn.*ai_service" | grep -v grep | awk '{print $2}' | head -1)
            
            if [ -n "$PID" ]; then
                print_status "Found service with PID $PID, restarting..."
                kill -HUP $PID 2>/dev/null || kill -TERM $PID
                sleep 2
                
                # Restart the service
                nohup python -m uvicorn src.ai_service.main:app --host 0.0.0.0 --port 8000 > service.log 2>&1 &
                print_status "Service restarted"
            else
                print_warning "No running service found. Starting new instance..."
                nohup python -m uvicorn src.ai_service.main:app --host 0.0.0.0 --port 8000 > service.log 2>&1 &
                print_status "Service started"
            fi
        fi
        ;;
esac

# Final verification
print_status "Verifying deployment..."
sleep 5

# Test via API
python -c "
import requests
import sys

try:
    response = requests.post('http://localhost:8000/process', 
                            json={'text': 'Петро Порошенко'},
                            timeout=10)
    if response.status_code == 200:
        data = response.json()
        decision = data.get('decision', {})
        risk_level = decision.get('risk_level', '')
        
        if risk_level == 'skip':
            print('  ✗ Verification failed: Still returning SKIP')
            sys.exit(1)
        else:
            print(f'  ✓ Verification passed: risk_level={risk_level} (not skip)')
    else:
        print(f'  ✗ API returned status {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'  ✗ API test failed: {e}')
    sys.exit(1)
" || { print_error "Deployment verification failed!"; exit 1; }

echo
print_status "Deployment completed successfully!"
echo
echo "Summary:"
echo "  - SmartFilter now processes Ukrainian names correctly"
echo "  - 'Петро Порошенко' and similar names won't be skipped"
echo "  - Name confidence increased: single (0.3→0.8), multiple (0.7→0.9)"
echo "  - Name weight increased: 0.4→0.8"
echo
echo "To rollback if needed:"
echo "  cp $BACKUP_DIR/*.py src/ai_service/layers/smart_filter/"
echo "  Then restart the service"