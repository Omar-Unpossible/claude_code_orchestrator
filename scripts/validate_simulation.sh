#!/bin/bash
# Obra Simulation Test - Validation Script
# Automatically checks success criteria and generates report

set -e

echo "==================================================="
echo "Obra Simulation Test - Validation Script"
echo "==================================================="
echo ""

# Configuration
PROJECT_DIR="${1:-/home/omarwsl/projects/json2md}"
OBRA_DIR="/home/omarwsl/projects/claude_code_orchestrator"
PROD_LOG="$HOME/obra-runtime/logs/production.jsonl"
REPORT_FILE="$OBRA_DIR/simulation_report.txt"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
FAIL_COUNT=0

# Helper function for checks
check_requirement() {
    local name="$1"
    local command="$2"

    echo -n "Checking: $name ... "

    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASS_COUNT++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAIL_COUNT++))
        return 1
    fi
}

# Start report
{
    echo "==================================================="
    echo "OBRA SIMULATION TEST - VALIDATION REPORT"
    echo "==================================================="
    echo "Date: $(date)"
    echo "Project Directory: $PROJECT_DIR"
    echo ""
    echo "==================================================="
    echo "SUCCESS CRITERIA VALIDATION"
    echo "==================================================="
    echo ""
} > "$REPORT_FILE"

# P0 Requirements
echo "==================================================="
echo "P0 Requirements (Must Have)"
echo "==================================================="
echo ""

# P0.1: Working CLI tool
check_requirement \
    "P0.1 - CLI tool exists" \
    "test -f $PROJECT_DIR/json2md.py || test -f $PROJECT_DIR/json2md/cli.py"

# P0.2: Templates exist
check_requirement \
    "P0.2 - Templates exist (≥2)" \
    "test $(find $PROJECT_DIR -name '*.md.j2' -o -name '*.jinja2' | wc -l) -ge 2"

# P0.3: Tests exist
check_requirement \
    "P0.3 - Tests exist" \
    "test -d $PROJECT_DIR/tests"

# P0.4: Error handling
check_requirement \
    "P0.4 - Error handling present" \
    "grep -r 'try:\\|except\\|raise' $PROJECT_DIR --include='*.py' | grep -v tests | grep -q ."

# P0.5: README exists
check_requirement \
    "P0.5 - README exists" \
    "test -f $PROJECT_DIR/README.md"

# P0.6: Tests pass (if pytest available)
if command -v pytest &>/dev/null && [ -d "$PROJECT_DIR/tests" ]; then
    echo -n "Checking: P0.6 - All tests passing ... "
    cd "$PROJECT_DIR"
    if pytest -v &>/tmp/pytest_output.txt; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASS_COUNT++))
        TEST_RESULTS=$(cat /tmp/pytest_output.txt)
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAIL_COUNT++))
        TEST_RESULTS="Tests failed. See /tmp/pytest_output.txt"
    fi
else
    echo -e "${YELLOW}⚠️  SKIP - pytest not available${NC}"
    TEST_RESULTS="Pytest not available"
fi

echo ""

# P1 Requirements
echo "==================================================="
echo "P1 Requirements (Should Have)"
echo "==================================================="
echo ""

# P1.7: Custom template support
check_requirement \
    "P1.7 - Template system (Jinja2)" \
    "grep -r 'jinja2\\|Template' $PROJECT_DIR --include='*.py' | grep -v tests | grep -q ."

# P1.8: Output file writing
check_requirement \
    "P1.8 - File output support" \
    "grep -r 'open(.*[\"']w[\"'])\\|Path.*write' $PROJECT_DIR --include='*.py' | grep -v tests | grep -q ."

# P1.9: Integration tests
check_requirement \
    "P1.9 - Integration tests exist" \
    "find $PROJECT_DIR/tests -name '*integration*.py' -o -name '*e2e*.py' | grep -q ."

# P1.10: Type hints
check_requirement \
    "P1.10 - Type hints present" \
    "grep -r '->\\|: str\\|: int\\|: dict\\|: List' $PROJECT_DIR --include='*.py' | grep -v tests | grep -q ."

echo ""

# Production Log Analysis
echo "==================================================="
echo "Production Log Analysis"
echo "==================================================="
echo ""

if [ -f "$PROD_LOG" ]; then
    echo "Analyzing production log: $PROD_LOG"
    echo ""

    # Count events
    TOTAL_EVENTS=$(jq -s 'length' "$PROD_LOG" 2>/dev/null || echo "0")
    NL_RESULTS=$(jq -s '[.[] | select(.event_type=="nl_result")] | length' "$PROD_LOG" 2>/dev/null || echo "0")
    EXEC_RESULTS=$(jq -s '[.[] | select(.event_type=="execution_result")] | length' "$PROD_LOG" 2>/dev/null || echo "0")
    ERRORS=$(jq -s '[.[] | select(.event_type=="error")] | length' "$PROD_LOG" 2>/dev/null || echo "0")

    echo "Total events: $TOTAL_EVENTS"
    echo "NL results: $NL_RESULTS"
    echo "Execution results: $EXEC_RESULTS"
    echo "Errors: $ERRORS"
    echo ""

    # Average quality and confidence
    AVG_QUALITY=$(jq -s '[.[] | select(.quality_score != null) | .quality_score] | if length > 0 then add / length else 0 end' "$PROD_LOG" 2>/dev/null || echo "0")
    AVG_CONFIDENCE=$(jq -s '[.[] | select(.confidence != null) | .confidence] | if length > 0 then add / length else 0 end' "$PROD_LOG" 2>/dev/null || echo "0")

    echo "Average quality score: $AVG_QUALITY"
    echo "Average confidence: $AVG_CONFIDENCE"
    echo ""

    # Check quality threshold
    echo -n "Checking: Production quality ≥0.7 ... "
    if (( $(echo "$AVG_QUALITY >= 0.7" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASS_COUNT++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAIL_COUNT++))
    fi
else
    echo -e "${YELLOW}⚠️  Production log not found: $PROD_LOG${NC}"
fi

echo ""

# Test Coverage (if available)
echo "==================================================="
echo "Test Coverage Analysis"
echo "==================================================="
echo ""

if command -v pytest &>/dev/null && command -v coverage &>/dev/null && [ -d "$PROJECT_DIR/tests" ]; then
    cd "$PROJECT_DIR"
    pytest --cov=json2md --cov-report=term --cov-report=json &>/tmp/coverage_output.txt || true

    if [ -f "coverage.json" ]; then
        COVERAGE=$(jq '.totals.percent_covered' coverage.json 2>/dev/null || echo "0")
        echo "Coverage: ${COVERAGE}%"
        echo ""

        echo -n "Checking: Coverage ≥80% ... "
        if (( $(echo "$COVERAGE >= 80" | bc -l 2>/dev/null || echo "0") )); then
            echo -e "${GREEN}✅ PASS${NC}"
            ((PASS_COUNT++))
        else
            echo -e "${RED}❌ FAIL${NC}"
            ((FAIL_COUNT++))
        fi
    else
        echo -e "${YELLOW}⚠️  Coverage data not available${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Coverage tools not available${NC}"
fi

echo ""

# Summary
echo "==================================================="
echo "SUMMARY"
echo "==================================================="
echo ""
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo ""

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=2; $PASS_COUNT * 100 / $TOTAL" | bc)
    echo "Success rate: ${SUCCESS_RATE}%"
else
    SUCCESS_RATE=0
    echo "Success rate: N/A"
fi

echo ""

# Overall result
if [ $FAIL_COUNT -eq 0 ] && [ $PASS_COUNT -ge 6 ]; then
    echo -e "${GREEN}==================================================="
    echo "🎉 SIMULATION TEST PASSED!"
    echo "===================================================${NC}"
    OVERALL_STATUS="PASSED"
elif [ $FAIL_COUNT -le 2 ] && [ $PASS_COUNT -ge 6 ]; then
    echo -e "${YELLOW}==================================================="
    echo "⚠️  SIMULATION TEST PARTIALLY PASSED"
    echo "===================================================${NC}"
    OVERALL_STATUS="PARTIAL"
else
    echo -e "${RED}==================================================="
    echo "❌ SIMULATION TEST FAILED"
    echo "===================================================${NC}"
    OVERALL_STATUS="FAILED"
fi

echo ""

# Append summary to report
{
    echo ""
    echo "==================================================="
    echo "VALIDATION SUMMARY"
    echo "==================================================="
    echo ""
    echo "Passed: $PASS_COUNT"
    echo "Failed: $FAIL_COUNT"
    echo "Success rate: ${SUCCESS_RATE}%"
    echo ""
    echo "Overall status: $OVERALL_STATUS"
    echo ""

    if [ -f "$PROD_LOG" ]; then
        echo "==================================================="
        echo "PRODUCTION LOG METRICS"
        echo "==================================================="
        echo ""
        echo "Total events: $TOTAL_EVENTS"
        echo "NL results: $NL_RESULTS"
        echo "Execution results: $EXEC_RESULTS"
        echo "Errors: $ERRORS"
        echo "Average quality: $AVG_QUALITY"
        echo "Average confidence: $AVG_CONFIDENCE"
        echo ""
    fi

    if [ -n "$TEST_RESULTS" ]; then
        echo "==================================================="
        echo "TEST RESULTS"
        echo "==================================================="
        echo ""
        echo "$TEST_RESULTS"
        echo ""
    fi

    if [ -f /tmp/coverage_output.txt ]; then
        echo "==================================================="
        echo "COVERAGE REPORT"
        echo "==================================================="
        echo ""
        cat /tmp/coverage_output.txt
        echo ""
    fi
} >> "$REPORT_FILE"

echo "Full report saved to: $REPORT_FILE"
echo ""

# Exit code
if [ "$OVERALL_STATUS" = "PASSED" ]; then
    exit 0
elif [ "$OVERALL_STATUS" = "PARTIAL" ]; then
    exit 1
else
    exit 2
fi
