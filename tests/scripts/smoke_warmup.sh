#!/bin/bash
# Smoke test warmup script with correct flags

set -e

echo "=== AI Service Smoke Warmup ==="

# Set environment variables for optimal performance
export NORM_CACHE_LRU=8192
export MORPH_CACHE_LRU=8192
export DISABLE_DEBUG_TRACING=true

echo "Environment variables set:"
echo "  NORM_CACHE_LRU=$NORM_CACHE_LRU"
echo "  MORPH_CACHE_LRU=$MORPH_CACHE_LRU"
echo "  DISABLE_DEBUG_TRACING=$DISABLE_DEBUG_TRACING"

# Change to project directory
cd "$(dirname "$0")/.."

echo "Running warmup with 200 requests..."
poetry run python tools/warmup.py --n 200 --verbose

echo "✓ Warmup completed successfully!"
