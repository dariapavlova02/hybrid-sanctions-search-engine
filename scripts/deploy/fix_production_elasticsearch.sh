#!/bin/bash
# Quick fix for Elasticsearch on production server

echo "🔧 FIXING ELASTICSEARCH ON PRODUCTION SERVER"
echo "=" * 50

# Set environment variables for production
export ENABLE_SEARCH=true
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_HOSTS=localhost:9200
export WATCHLIST_INDEX=watchlist
export WATCHLIST_AC_INDEX=watchlist_ac
export WATCHLIST_VECTOR_INDEX=watchlist_vector

echo "✅ Environment variables set:"
echo "  ENABLE_SEARCH=$ENABLE_SEARCH"
echo "  ELASTICSEARCH_URL=$ELASTICSEARCH_URL"

# Check if Elasticsearch is running
echo ""
echo "🔍 Checking Elasticsearch status..."
if curl -s "$ELASTICSEARCH_URL/_cluster/health" > /dev/null 2>&1; then
    echo "✅ Elasticsearch is running at $ELASTICSEARCH_URL"

    # Get cluster health
    HEALTH=$(curl -s "$ELASTICSEARCH_URL/_cluster/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo "   Cluster health: $HEALTH"

    # Check indices
    echo ""
    echo "📊 Checking indices..."
    INDICES=$(curl -s "$ELASTICSEARCH_URL/_cat/indices?format=json")
    echo "   Available indices:"
    echo "$INDICES" | grep -o '"index":"[^"]*"' | cut -d'"' -f4 | sed 's/^/   - /'

    # Count documents in watchlist indices
    for index in watchlist watchlist_ac watchlist_vector; do
        if echo "$INDICES" | grep -q "\"index\":\"$index\""; then
            COUNT=$(curl -s "$ELASTICSEARCH_URL/$index/_count" | grep -o '"count":[0-9]*' | cut -d':' -f2)
            echo "   $index: $COUNT documents"
        else
            echo "   $index: NOT FOUND"
        fi
    done

else
    echo "❌ Elasticsearch is NOT running at $ELASTICSEARCH_URL"
    echo ""
    echo "🚀 Starting Elasticsearch..."
    echo "   Please start Elasticsearch manually:"
    echo "   sudo systemctl start elasticsearch"
    echo "   # or"
    echo "   docker run -d -p 9200:9200 -p 9300:9300 -e 'discovery.type=single-node' elasticsearch:8.8.0"
fi

echo ""
echo "📂 Sample sanctions data for testing:"
cat << 'EOF' > /tmp/sample_sanctions.json
[
  {
    "id": "poroshenko_1",
    "name": "Петро Олексійович Порошенко",
    "aliases": ["Petro Poroshenko", "Порошенко П.О.", "Poroshenko Petro", "Порошенк Петро"],
    "dob": "1965-09-26",
    "nationality": "Ukraine",
    "sanctions": ["EU", "UK"],
    "type": "person",
    "status": "active"
  },
  {
    "id": "ulianova_1",
    "name": "Людмила Ульянова",
    "aliases": ["Liudmila Ulianova", "Людмила Ульянова", "L. Ulianova"],
    "type": "person",
    "status": "active"
  }
]
EOF

echo "✅ Created sample sanctions data: /tmp/sample_sanctions.json"
echo ""
echo "📤 To load sample data into Elasticsearch:"
echo "curl -X POST '$ELASTICSEARCH_URL/watchlist/_bulk' -H 'Content-Type: application/json' --data-binary @/tmp/sample_sanctions.json"

echo ""
echo "🧪 Test search after loading data:"
echo "curl -X POST '$ELASTICSEARCH_URL/watchlist/_search' -H 'Content-Type: application/json' -d '{\"query\":{\"match\":{\"name\":\"Порошенк\"}}}'"

echo ""
echo "⚠️  NEXT STEPS:"
echo "1. Ensure Elasticsearch is running"
echo "2. Load sanctions data into indices"
echo "3. Restart ai-service with ENABLE_SEARCH=true"
echo "4. Test API endpoints"