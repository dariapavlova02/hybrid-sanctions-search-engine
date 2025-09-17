#!/bin/bash
# Local validation script for parity and performance gates

set -e  # Exit on any error

echo "🚀 Starting Local Validation (Shadow Mode)"
echo "=========================================="

# Set environment variables for shadow mode
export SHADOW_MODE=true
export USE_FACTORY_NORMALIZER=true
export FIX_INITIALS_DOUBLE_DOT=true
export PRESERVE_HYPHENATED_CASE=true
export STRICT_STOPWORDS=true
export ENABLE_SPACY_NER=true
export ENABLE_NAMEPARSER_EN=true
export ENHANCED_DIMINUTIVES=true
export ENHANCED_GENDER_RULES=true
export ASCII_FASTPATH=true
export ENABLE_AC_TIER0=true
export ENABLE_VECTOR_FALLBACK=true
export DEBUG_TRACE=true

echo "📋 Environment Variables Set:"
echo "  SHADOW_MODE=$SHADOW_MODE"
echo "  USE_FACTORY_NORMALIZER=$USE_FACTORY_NORMALIZER"
echo "  FIX_INITIALS_DOUBLE_DOT=$FIX_INITIALS_DOUBLE_DOT"
echo "  PRESERVE_HYPHENATED_CASE=$PRESERVE_HYPHENATED_CASE"
echo "  STRICT_STOPWORDS=$STRICT_STOPWORDS"
echo "  ENABLE_SPACY_NER=$ENABLE_SPACY_NER"
echo "  ENABLE_NAMEPARSER_EN=$ENABLE_NAMEPARSER_EN"
echo "  ENHANCED_DIMINUTIVES=$ENHANCED_DIMINUTIVES"
echo "  ENHANCED_GENDER_RULES=$ENHANCED_GENDER_RULES"
echo "  ASCII_FASTPATH=$ASCII_FASTPATH"
echo "  ENABLE_AC_TIER0=$ENABLE_AC_TIER0"
echo "  ENABLE_VECTOR_FALLBACK=$ENABLE_VECTOR_FALLBACK"
echo "  DEBUG_TRACE=$DEBUG_TRACE"
echo ""

# Create artifacts directory
mkdir -p artifacts

echo "📊 Running Golden Parity Tests (legacy vs factory-all-flags)"
echo "------------------------------------------------------------"
pytest tests/parity -q \
  --parity-compare=legacy,factory_flags_on \
  --parity-threshold=1.0 \
  --parity-report=artifacts/parity_report.json

echo ""
echo "⚡ Running Performance Gates (Micro-benchmarks)"
echo "-----------------------------------------------"
pytest -q -m perf_micro tests/performance \
  --perf-p95-max=0.010 \
  --perf-p99-max=0.020 \
  --perf-report=artifacts/perf.json

echo ""
echo "🔍 Running Search Integration Tests (AC tier0/1 + vector fallback)"
echo "------------------------------------------------------------------"
pytest -q tests/integration/search \
  -k "ac_tier or knn or hybrid" \
  --maxfail=1

echo ""
echo "🧪 Running Property Tests"
echo "-------------------------"
pytest -q tests/property --hypothesis-profile=ci

echo ""
echo "💨 Running Smoke Tests"
echo "----------------------"
pytest -q tests/smoke

echo ""
echo "🌍 Running E2E Tests (Sanctions)"
echo "--------------------------------"
pytest -q tests/e2e -k "sanctions"

echo ""
echo "📝 Building Acceptance Summary"
echo "------------------------------"
python scripts/acceptance_summary.py \
  --parity artifacts/parity_report.json \
  --perf artifacts/perf.json \
  --out artifacts/ACCEPTANCE_GATES_STATUS.md

echo ""
echo "✅ Local Validation Completed!"
echo "=============================="
echo ""
echo "📁 Artifacts generated:"
echo "  - artifacts/parity_report.json"
echo "  - artifacts/perf.json"
echo "  - artifacts/ACCEPTANCE_GATES_STATUS.md"
echo ""
echo "📋 Summary:"
cat artifacts/ACCEPTANCE_GATES_STATUS.md

echo ""
echo "🎯 Validation Status:"
if grep -q "✅ \*\*ACCEPTED\*\*" artifacts/ACCEPTANCE_GATES_STATUS.md; then
    echo "✅ ACCEPTED - All gates passed! This PR is ready for merge! 🚀"
    exit 0
else
    echo "❌ REJECTED - One or more gates failed. This PR should NOT be merged."
    exit 1
fi
