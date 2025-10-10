#!/bin/bash
set -e

# Docker Entrypoint Script for AI Service
# Automatic Elasticsearch initialization and service startup

echo "=================================================="
echo "AI Service - Docker Entrypoint"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ES_HOST="${ES_HOSTS:-elasticsearch:9200}"
ES_TIMEOUT="${ES_STARTUP_TIMEOUT:-60}"
INDEX_PREFIX="${ES_INDEX_PREFIX:-sanctions}"
SKIP_ES_INIT="${SKIP_ES_INIT:-false}"

# Extract first host from list
ES_FIRST_HOST=$(echo "$ES_HOST" | cut -d',' -f1)

echo ""
echo "Configuration:"
echo "  Elasticsearch: $ES_FIRST_HOST"
echo "  Index Prefix: $INDEX_PREFIX"
echo "  Skip Init: $SKIP_ES_INIT"
echo ""

# Function to wait for Elasticsearch
wait_for_elasticsearch() {
    echo "Waiting for Elasticsearch to be ready..."

    local counter=0
    local max_attempts=$((ES_TIMEOUT / 3))

    while [ $counter -lt $max_attempts ]; do
        if curl -sf "http://$ES_FIRST_HOST/_cluster/health" > /dev/null 2>&1; then
            echo -e "${GREEN}[OK] Elasticsearch is ready${NC}"
            return 0
        fi

        counter=$((counter + 1))
        echo "  Attempt $counter/$max_attempts..."
        sleep 3
    done

    echo -e "${RED}[ERROR] Elasticsearch not ready after ${ES_TIMEOUT}s${NC}"
    return 1
}

# Function to check indices
check_indices() {
    local ac_index="${INDEX_PREFIX}_ac_patterns"
    local vector_index="${INDEX_PREFIX}_vectors"

    echo "Checking indices..."

    local ac_exists=$(curl -sf "http://$ES_FIRST_HOST/$ac_index/_count" > /dev/null 2>&1 && echo "true" || echo "false")
    local vector_exists=$(curl -sf "http://$ES_FIRST_HOST/$vector_index/_count" > /dev/null 2>&1 && echo "true" || echo "false")
    local ac_doc_count=0
    local vector_count=0

    if [ "$ac_exists" = "true" ]; then
        ac_doc_count=$(curl -sf "http://$ES_FIRST_HOST/$ac_index/_count" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "0")
        echo -e "${GREEN}  [OK] $ac_index: $ac_doc_count documents${NC}"
    else
        echo -e "${YELLOW}  [WARN] $ac_index: does not exist${NC}"
    fi

    if [ "$vector_exists" = "true" ]; then
        vector_count=$(curl -sf "http://$ES_FIRST_HOST/$vector_index/_count" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "0")
        echo -e "${GREEN}  [OK] $vector_index: $vector_count documents${NC}"
    else
        echo -e "${YELLOW}  [WARN] $vector_index: does not exist${NC}"
    fi

    # Return true if at least AC index exists with data
    if [ "$ac_exists" = "true" ] && [ "${ac_doc_count:-0}" -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Function to initialize Elasticsearch
initialize_elasticsearch() {
    echo "Initializing Elasticsearch..."

    # Check for patterns file
    local patterns_dir="/app/output/sanctions"

    if [ ! -d "$patterns_dir" ]; then
        echo -e "${YELLOW}[WARN] Directory $patterns_dir does not exist${NC}"
        echo "[INFO] Creating indices without loading data..."

        # Create empty indices via Python script
        python3 /app/scripts/create_empty_indices.py \
            --es-host "$ES_FIRST_HOST" \
            --index-prefix "$INDEX_PREFIX"

        return $?
    fi

    # Find patterns file
    local patterns_file=$(find "$patterns_dir" -name "ac_patterns_*.json" -type f | sort -r | head -n1)

    if [ -z "$patterns_file" ]; then
        echo -e "${YELLOW}[WARN] AC patterns file not found${NC}"
        echo "[INFO] Creating indices without loading data..."

        python3 /app/scripts/create_empty_indices.py \
            --es-host "$ES_FIRST_HOST" \
            --index-prefix "$INDEX_PREFIX"

        return $?
    fi

    echo "[INFO] Found patterns file: $(basename $patterns_file)"

    # Find vectors file
    local vectors_file=$(find "$patterns_dir" -name "vectors_*.json" -type f | sort -r | head -n1)

    # Run deployment script
    if [ -n "$vectors_file" ]; then
        echo "[INFO] Found vectors file: $(basename $vectors_file)"
        python3 /app/scripts/deploy_to_elasticsearch.py \
            --es-host "$ES_FIRST_HOST" \
            --index-prefix "$INDEX_PREFIX" \
            --patterns-file "$patterns_file" \
            --vectors-file "$vectors_file" \
            --create-vector-indices
    else
        echo "[WARN] Vectors file not found, creating AC index only"
        python3 /app/scripts/deploy_to_elasticsearch.py \
            --es-host "$ES_FIRST_HOST" \
            --index-prefix "$INDEX_PREFIX" \
            --patterns-file "$patterns_file"
    fi

    return $?
}

# Main logic
main() {
    # 1. Wait for Elasticsearch
    if ! wait_for_elasticsearch; then
        echo -e "${RED}[ERROR] Could not wait for Elasticsearch${NC}"
        echo "[INFO] Starting service without Elasticsearch..."
        echo "[WARN] Search features may not work!"
    else
        # 2. Check indices
        if check_indices; then
            echo -e "${GREEN}[OK] Indices already exist with data${NC}"
        else
            if [ "$SKIP_ES_INIT" = "true" ]; then
                echo -e "${YELLOW}[WARN] Skipping initialization (SKIP_ES_INIT=true)${NC}"
            else
                # 3. Initialize Elasticsearch
                if initialize_elasticsearch; then
                    echo -e "${GREEN}[OK] Elasticsearch initialized successfully${NC}"
                    check_indices
                else
                    echo -e "${YELLOW}[WARN] Initialization completed with errors${NC}"
                    echo "[INFO] Service will continue, but search features may be unavailable"
                fi
            fi
        fi
    fi

    echo ""
    echo "=================================================="
    echo "Starting AI Service"
    echo "=================================================="
    echo ""

    # Set environment variables to match created indices
    export ES_AC_INDEX="${INDEX_PREFIX}_ac_patterns"
    export ES_VECTOR_INDEX="${INDEX_PREFIX}_vectors"

    # Start main application
    exec "$@"
}

# Run
main "$@"
