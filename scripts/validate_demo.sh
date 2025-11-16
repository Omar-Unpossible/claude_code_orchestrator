#!/bin/bash
# Pre-demo validation script - RUN BEFORE EVERY DEMO
# Validates that demo workflows work before presenting to audience

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Pre-Demo Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Check LLM connectivity
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Checking LLM Connectivity"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v codex &> /dev/null; then
    echo "✓ Codex CLI found"
else
    echo "❌ Codex CLI not found!"
    echo "   Install: npm install -g @anthropic/codex"
    exit 1
fi

# Run demo scenario tests
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Running Demo Scenario Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run with timeout=0 (demo tests can be slow)
pytest tests/integration/test_demo_scenarios.py \
    -v \
    -m "real_llm and demo_scenario" \
    --timeout=0 \
    --tb=short \
    -ra

RESULT=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $RESULT -eq 0 ]; then
    echo "✅ All demo tests PASSED - SAFE TO DEMO"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo "❌ Demo tests FAILED - FIX BEFORE DEMO!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "What to do:"
    echo "1. Review test failures above"
    echo "2. Fix the underlying issues"
    echo "3. Re-run: ./scripts/validate_demo.sh"
    echo "4. Only demo when tests pass"
    echo ""
    exit 1
fi
