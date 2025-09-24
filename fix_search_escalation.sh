#!/bin/bash
# Fix search escalation for production server

echo "🚨 CRITICAL: SEARCH IS DISABLED ON PRODUCTION"
echo "Server: 95.217.84.234:8000"
echo "=" * 60

echo "📊 CURRENT PROBLEM ANALYSIS:"
echo "❌ search_contribution: 0.0 (should be > 0)"
echo "❌ total_hits: 0 (should find 'Порошенк' -> 'Порошенко')"
echo "❌ Elasticsearch appears disconnected or no data"
echo ""

echo "🔍 DIAGNOSIS COMMANDS:"
echo "Run these on the production server:"
echo ""

echo "# 1. Check Elasticsearch status"
echo "curl -s http://localhost:9200/_cluster/health"
echo ""

echo "# 2. Check if ai-service can connect to Elasticsearch"
echo "export ENABLE_SEARCH=true"
echo "export ELASTICSEARCH_URL=http://localhost:9200"
echo ""

echo "# 3. Check indices"
echo "curl -s http://localhost:9200/_cat/indices"
echo ""

echo "# 4. Search for Poroshenko in any index"
echo "curl -X POST 'http://localhost:9200/_search' -H 'Content-Type: application/json' -d '{"query": {"multi_match": {"query": "Порошенк", "fields": ["*"]}}'"
echo ""

echo "# 5. Load sample sanctions data if missing"
cat << 'DATA' > /tmp/sample_poroshenko.json
{
  "index": { "_index": "watchlist", "_id": "poroshenko_1" }
}
{
  "name": "Петро Олексійович Порошенко",
  "aliases": ["Petro Poroshenko", "Порошенко П.О.", "Poroshenko Petro", "Порошенк Петро"],
  "dob": "1965-09-26",
  "nationality": "Ukraine",
  "sanctions": ["EU", "UK"],
  "type": "person",
  "status": "active"
}
DATA

echo "# 6. Load the data"
echo "curl -X POST 'http://localhost:9200/_bulk' -H 'Content-Type: application/json' --data-binary @/tmp/sample_poroshenko.json"
echo ""

echo "# 7. Refresh index"
echo "curl -X POST 'http://localhost:9200/watchlist/_refresh'"
echo ""

echo "# 8. Test search again"
echo "curl -X POST 'http://localhost:9200/watchlist/_search' -H 'Content-Type: application/json' -d '{\"query\": {\"match\": {\"aliases\": \"Порошенк Петро\"}}}'"
echo ""

echo "# 9. Restart ai-service"
echo "# sudo systemctl restart ai-service"
echo "# OR kill and restart the Python process"
echo ""

echo "🧪 VERIFICATION TEST:"
echo "After fixing Elasticsearch, test with:"
echo "curl -X POST 'http://95.217.84.234:8000/process' -H 'Content-Type: application/json' -d '{\"text\": \"Порошенк Петро\"}'"
echo ""
echo "Expected results:"
echo "  - search_contribution > 0"
echo "  - total_hits > 0"
echo "  - risk_level: HIGH (if found in sanctions)"
echo ""

echo "⚠️  IMMEDIATE ACTIONS REQUIRED:"
echo "1. Start Elasticsearch: sudo systemctl start elasticsearch"
echo "2. Load sanctions data into watchlist index"
echo "3. Set ENABLE_SEARCH=true environment variable"
echo "4. Restart ai-service"
echo ""

echo "📞 ESCALATION PATH:"
echo "If search still fails after fixing Elasticsearch:"
echo "1. Check ai-service logs for search errors"
echo "2. Verify HybridSearchService initialization"
echo "3. Test search service endpoints directly"
echo "4. Consider emergency fallback to local indices"