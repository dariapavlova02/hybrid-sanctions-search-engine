#!/bin/bash
# Deploy decision engine fix to production

PROD_HOST="95.217.84.234"
PROD_USER="root"
PROD_PATH="/root/ai-service"
LOCAL_FILE="src/ai_service/core/decision_engine.py"

echo "🚀 Deploying decision engine fix to production..."

# Check if local file has the fix
if ! grep -q "search=inp.search" "$LOCAL_FILE"; then
    echo "❌ Local file doesn't contain the search fix!"
    exit 1
fi

echo "✅ Local file contains the search fix"

# Create backup on production
echo "💾 Creating backup on production..."
ssh $PROD_USER@$PROD_HOST "cd $PROD_PATH && cp $LOCAL_FILE ${LOCAL_FILE}.backup.\$(date +%Y%m%d_%H%M%S)"

# Upload the fixed file
echo "📤 Uploading fixed decision_engine.py..."
scp "$LOCAL_FILE" "$PROD_USER@$PROD_HOST:$PROD_PATH/$LOCAL_FILE"

if [ $? -eq 0 ]; then
    echo "✅ File uploaded successfully"

    # Restart AI service
    echo "🔄 Restarting AI service..."
    ssh $PROD_USER@$PROD_HOST "cd $PROD_PATH && docker-compose restart ai-service"

    echo "✅ Decision engine fix deployed successfully!"
    echo ""
    echo "🧪 Test with:"
    echo "curl -X POST http://95.217.84.234:8002/process -H 'Content-Type: application/json' -d '{\"text\": \"Петро Порошенко\"}'"
else
    echo "❌ Failed to upload file"
    exit 1
fi