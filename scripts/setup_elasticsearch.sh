#!/bin/bash
# Script to setup Elasticsearch with AC patterns

set -e

echo "🚀 Setting up Elasticsearch with AC patterns"

# Change to project directory
cd "$(dirname "$0")/.."

echo "📋 Current directory: $(pwd)"

# Check if Elasticsearch is running
echo "🔍 Checking Elasticsearch status..."
if ! curl -s "http://localhost:9200/_cluster/health" > /dev/null; then
    echo "❌ Elasticsearch is not running or not accessible"
    echo "Please start Elasticsearch first:"
    echo "  docker compose -f docker-compose.prod.yml up -d elasticsearch"
    exit 1
fi

echo "✅ Elasticsearch is running"

# Wait for Elasticsearch to be ready
echo "⏳ Waiting for Elasticsearch to be ready..."
timeout=60
counter=0
while ! curl -s "http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=5s" > /dev/null; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        echo "❌ Elasticsearch did not become ready within $timeout seconds"
        exit 1
    fi
    echo "   Waiting... ($counter/$timeout seconds)"
done

echo "✅ Elasticsearch is ready"

# Load AC patterns
echo "📥 Loading AC patterns into Elasticsearch..."
python3 scripts/load_ac_patterns.py

if [ $? -eq 0 ]; then
    echo "✅ AC patterns loaded successfully"

    # Test search functionality
    echo "🧪 Testing AC pattern search..."
    python3 scripts/test_ac_search.py

    if [ $? -eq 0 ]; then
        echo "🎉 Elasticsearch setup completed successfully!"
        echo ""
        echo "📊 Ready for high-performance pattern matching:"
        echo "  - Person patterns: ac_patterns_person"
        echo "  - Company patterns: ac_patterns_company"
        echo "  - Terrorism patterns: ac_patterns_terrorism"
        echo ""
        echo "🚀 Service is ready for 100+ RPS with Elasticsearch acceleration!"
    else
        echo "⚠️  AC patterns loaded but search tests failed"
        exit 1
    fi
else
    echo "❌ Failed to load AC patterns"
    exit 1
fi