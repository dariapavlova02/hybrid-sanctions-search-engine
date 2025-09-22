#!/bin/bash
# Script to upload data to AI service via API

set -e

BASE_URL="${AI_SERVICE_URL:-http://localhost:8000}"
DATA_DIR="${DATA_DIR:-data/templates}"

echo "🚀 Uploading data to AI service at $BASE_URL"

# Function to check service health
check_service() {
    echo "🔍 Checking service health..."
    if curl -s "$BASE_URL/health" > /dev/null; then
        echo "✅ Service is healthy"
    else
        echo "❌ Service is not available at $BASE_URL"
        exit 1
    fi
}

# Function to upload AC patterns
upload_ac_patterns() {
    echo "📤 Uploading AC patterns..."

    # Upload person patterns
    if [ -f "$DATA_DIR/person_ac_export.json" ]; then
        echo "📋 Uploading person AC patterns..."
        curl -X POST "$BASE_URL/admin/ac-patterns/upload" \
            -F "file=@$DATA_DIR/person_ac_export.json" \
            -F "category=person" \
            -F "batch_size=1000"
        echo ""
    else
        echo "⚠️ Person AC patterns file not found: $DATA_DIR/person_ac_export.json"
    fi

    # Upload company patterns
    if [ -f "$DATA_DIR/company_ac_export.json" ]; then
        echo "📋 Uploading company AC patterns..."
        curl -X POST "$BASE_URL/admin/ac-patterns/upload" \
            -F "file=@$DATA_DIR/company_ac_export.json" \
            -F "category=company" \
            -F "batch_size=1000"
        echo ""
    else
        echo "⚠️ Company AC patterns file not found: $DATA_DIR/company_ac_export.json"
    fi

    # Upload terrorism patterns
    if [ -f "$DATA_DIR/terrorism_ac_export.json" ]; then
        echo "📋 Uploading terrorism AC patterns..."
        curl -X POST "$BASE_URL/admin/ac-patterns/upload" \
            -F "file=@$DATA_DIR/terrorism_ac_export.json" \
            -F "category=terrorism" \
            -F "batch_size=1000"
        echo ""
    else
        echo "⚠️ Terrorism AC patterns file not found: $DATA_DIR/terrorism_ac_export.json"
    fi
}

# Function to upload vectors
upload_vectors() {
    echo "🧠 Uploading vectors..."

    # Upload person vectors (if available)
    if [ -f "$DATA_DIR/person_vectors.json" ]; then
        echo "📋 Uploading person vectors..."
        curl -X POST "$BASE_URL/admin/vectors/upload" \
            -F "file=@$DATA_DIR/person_vectors.json" \
            -F "category=person" \
            -F "model_name=sentence-transformers/paraphrase-multilingual-mpnet-base-v2" \
            -F "batch_size=500"
        echo ""
    else
        echo "⚠️ Person vectors file not found: $DATA_DIR/person_vectors.json"
        echo "💡 You can generate vectors using the Python script"
    fi

    # Upload company vectors (if available)
    if [ -f "$DATA_DIR/company_vectors.json" ]; then
        echo "📋 Uploading company vectors..."
        curl -X POST "$BASE_URL/admin/vectors/upload" \
            -F "file=@$DATA_DIR/company_vectors.json" \
            -F "category=company" \
            -F "model_name=sentence-transformers/paraphrase-multilingual-mpnet-base-v2" \
            -F "batch_size=500"
        echo ""
    else
        echo "⚠️ Company vectors file not found: $DATA_DIR/company_vectors.json"
        echo "💡 You can generate vectors using the Python script"
    fi
}

# Function to check loading status
check_status() {
    echo "📊 Checking loading status..."
    curl -s "$BASE_URL/admin/loading-status" | python3 -m json.tool
    echo ""
}

# Function to list indices
list_indices() {
    echo "📋 Listing Elasticsearch indices..."
    curl -s "$BASE_URL/admin/indices" | python3 -m json.tool
    echo ""
}

# Function to wait for completion
wait_for_completion() {
    echo "⏳ Waiting for operations to complete..."
    for i in {1..60}; do
        sleep 5
        status=$(curl -s "$BASE_URL/admin/loading-status")

        # Check if both operations are completed or idle
        ac_status=$(echo "$status" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('ac_patterns', {}).get('status', 'unknown'))")
        vectors_status=$(echo "$status" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('vectors', {}).get('status', 'unknown'))")

        echo "⏰ Status - AC patterns: $ac_status, Vectors: $vectors_status"

        if [[ "$ac_status" == "completed" || "$ac_status" == "idle" ]] && [[ "$vectors_status" == "completed" || "$vectors_status" == "idle" ]]; then
            echo "✅ All operations completed!"
            break
        fi

        if [[ "$ac_status" == "error" ]] || [[ "$vectors_status" == "error" ]]; then
            echo "❌ Some operations failed!"
            break
        fi
    done
}

# Main script logic
case "${1:-all}" in
    "health")
        check_service
        ;;
    "ac-patterns")
        check_service
        upload_ac_patterns
        wait_for_completion
        ;;
    "vectors")
        check_service
        upload_vectors
        wait_for_completion
        ;;
    "status")
        check_status
        ;;
    "indices")
        list_indices
        ;;
    "all")
        check_service
        upload_ac_patterns
        upload_vectors
        wait_for_completion
        list_indices
        ;;
    *)
        echo "Usage: $0 [health|ac-patterns|vectors|status|indices|all]"
        echo ""
        echo "Commands:"
        echo "  health       - Check service health"
        echo "  ac-patterns  - Upload AC patterns only"
        echo "  vectors      - Upload vectors only"
        echo "  status       - Check loading status"
        echo "  indices      - List Elasticsearch indices"
        echo "  all          - Upload everything (default)"
        echo ""
        echo "Environment variables:"
        echo "  AI_SERVICE_URL - Service URL (default: http://localhost:8000)"
        echo "  DATA_DIR       - Data directory (default: data/templates)"
        exit 1
        ;;
esac

echo "🎉 Script completed!"