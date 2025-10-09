#!/bin/bash
#
# Deploy INN cache fix to production
# This script ensures the sanctioned_inns_cache.json is deployed and the code fix is applied
#

set -e

echo "========================================"
echo "DEPLOYING INN CACHE FIX TO PRODUCTION"
echo "========================================"

# Configuration
PRODUCTION_HOST="${PROD_HOST:-95.217.84.234}"
PRODUCTION_USER="${PROD_USER:-root}"
PRODUCTION_PATH="${PROD_PATH:-/opt/ai-service}"

echo ""
echo "Target: ${PRODUCTION_USER}@${PRODUCTION_HOST}:${PRODUCTION_PATH}"
echo ""

# 1. Check local files
echo "1. CHECKING LOCAL FILES..."
if [ -f "src/ai_service/data/sanctioned_inns_cache.json" ]; then
    echo "   ✅ sanctioned_inns_cache.json exists locally"
    echo "   Size: $(wc -c < src/ai_service/data/sanctioned_inns_cache.json) bytes"
else
    echo "   ❌ sanctioned_inns_cache.json NOT FOUND locally!"
    exit 1
fi

# 2. Copy cache file to production
echo ""
echo "2. COPYING CACHE FILE TO PRODUCTION..."
echo "   Uploading sanctioned_inns_cache.json..."

scp src/ai_service/data/sanctioned_inns_cache.json \
    ${PRODUCTION_USER}@${PRODUCTION_HOST}:${PRODUCTION_PATH}/src/ai_service/data/

if [ $? -eq 0 ]; then
    echo "   ✅ Cache file uploaded successfully"
else
    echo "   ❌ Failed to upload cache file"
    exit 1
fi

# 3. Copy fixed signals_service.py to production
echo ""
echo "3. DEPLOYING CODE FIX..."
echo "   Uploading fixed signals_service.py..."

scp src/ai_service/layers/signals/signals_service.py \
    ${PRODUCTION_USER}@${PRODUCTION_HOST}:${PRODUCTION_PATH}/src/ai_service/layers/signals/

if [ $? -eq 0 ]; then
    echo "   ✅ Code fix uploaded successfully"
else
    echo "   ❌ Failed to upload code fix"
    exit 1
fi

# 4. Copy the cache module
echo ""
echo "4. DEPLOYING CACHE MODULE..."
echo "   Uploading sanctioned_inn_cache.py..."

scp src/ai_service/layers/search/sanctioned_inn_cache.py \
    ${PRODUCTION_USER}@${PRODUCTION_HOST}:${PRODUCTION_PATH}/src/ai_service/layers/search/

if [ $? -eq 0 ]; then
    echo "   ✅ Cache module uploaded successfully"
else
    echo "   ❌ Failed to upload cache module"
    exit 1
fi

# 5. Restart service on production
echo ""
echo "5. RESTARTING SERVICE..."
ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << 'EOF'
    cd /opt/ai-service

    # Check if cache file exists
    if [ -f "src/ai_service/data/sanctioned_inns_cache.json" ]; then
        echo "   ✅ Cache file verified on server"
    else
        echo "   ❌ Cache file not found on server!"
        exit 1
    fi

    # Restart the service
    echo "   Restarting AI service..."

    # Try systemctl first
    if command -v systemctl &> /dev/null; then
        sudo systemctl restart ai-service || true
    fi

    # Try docker-compose
    if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
        docker-compose restart ai-service || true
    fi

    # Try supervisorctl
    if command -v supervisorctl &> /dev/null; then
        supervisorctl restart ai-service || true
    fi

    echo "   ✅ Service restart command executed"
EOF

# 6. Run diagnostic on production
echo ""
echo "6. RUNNING PRODUCTION DIAGNOSTIC..."

# Copy diagnostic script
scp diagnose_production_inn_cache.py \
    ${PRODUCTION_USER}@${PRODUCTION_HOST}:${PRODUCTION_PATH}/

ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << 'EOF'
    cd /opt/ai-service
    echo "   Running diagnostic..."
    python diagnose_production_inn_cache.py || true
EOF

echo ""
echo "========================================"
echo "DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Test the /model endpoint with: \"Дарья ПАвлова ИНН 2839403975\""
echo "2. Verify risk_level is now \"high\" with sanctioned INN detected"
echo ""