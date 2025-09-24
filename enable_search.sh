#!/bin/bash
# Enable search functionality for ai-service

echo "🔧 Enabling search functionality..."

# Set environment variables
export ENABLE_SEARCH=true
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_HOSTS=localhost:9200
export WATCHLIST_INDEX=watchlist
export WATCHLIST_AC_INDEX=watchlist_ac
export WATCHLIST_VECTOR_INDEX=watchlist_vector

echo "✅ Search environment variables set:"
echo "  ENABLE_SEARCH=$ENABLE_SEARCH"
echo "  ELASTICSEARCH_URL=$ELASTICSEARCH_URL"
echo "  ELASTICSEARCH_HOSTS=$ELASTICSEARCH_HOSTS"

# Check if Elasticsearch is running
if curl -s "$ELASTICSEARCH_URL/_cluster/health" > /dev/null 2>&1; then
    echo "✅ Elasticsearch is running at $ELASTICSEARCH_URL"
else
    echo "⚠️  Elasticsearch is not running at $ELASTICSEARCH_URL"
    echo "   Please start Elasticsearch or update ELASTICSEARCH_URL"
fi

echo "🔍 Search functionality should now be enabled!"
echo "   Restart the ai-service to apply changes."
