#!/bin/bash
# Hook for automatic INN cache regeneration when sanctions data is updated

echo "🔄 INN Cache Update Hook triggered..."

# Check if sanctions data files exist
DATA_DIR="$(dirname "$0")/../src/ai_service/data"
PERSONS_FILE="$DATA_DIR/sanctioned_persons.json"
ORGS_FILE="$DATA_DIR/sanctioned_companies.json"
CACHE_FILE="$DATA_DIR/sanctioned_inns_cache.json"

if [[ ! -f "$PERSONS_FILE" ]] || [[ ! -f "$ORGS_FILE" ]]; then
    echo "❌ Sanctions data files not found, skipping cache regeneration"
    exit 0
fi

# Get modification times
PERSONS_MTIME=$(stat -c %Y "$PERSONS_FILE" 2>/dev/null || stat -f %m "$PERSONS_FILE" 2>/dev/null)
ORGS_MTIME=$(stat -c %Y "$ORGS_FILE" 2>/dev/null || stat -f %m "$ORGS_FILE" 2>/dev/null)
CACHE_MTIME=$(stat -c %Y "$CACHE_FILE" 2>/dev/null || stat -f %m "$CACHE_FILE" 2>/dev/null || echo "0")

# Find the newest modification time
NEWEST_DATA_MTIME=$((PERSONS_MTIME > ORGS_MTIME ? PERSONS_MTIME : ORGS_MTIME))

if [[ $NEWEST_DATA_MTIME -gt $CACHE_MTIME ]]; then
    echo "📋 Sanctions data updated, regenerating INN cache..."
    
    if python3 "$(dirname "$0")/generate_inn_cache_simple.py"; then
        echo "✅ INN cache successfully regenerated"
        
        # Optionally restart the service to pick up new cache
        if command -v docker-compose &> /dev/null; then
            echo "🔄 Restarting AI service to pick up new cache..."
            docker-compose restart ai-service
            echo "✅ Service restarted"
        fi
    else
        echo "❌ Failed to regenerate INN cache"
        exit 1
    fi
else
    echo "✅ INN cache is up to date"
fi