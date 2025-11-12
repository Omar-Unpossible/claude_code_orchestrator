#!/bin/bash
#
# NL Command Test Runner
#
# Usage:
#   ./scripts/run_nl_tests.sh [mock|real|both|coverage]
#
# Examples:
#   ./scripts/run_nl_tests.sh mock      # Run mock tests only (fast)
#   ./scripts/run_nl_tests.sh real      # Run real LLM tests only
#   ./scripts/run_nl_tests.sh both      # Run all tests
#   ./scripts/run_nl_tests.sh coverage  # Run with coverage report

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}\n"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_ollama() {
    if ! curl -s http://172.29.144.1:11434/api/tags > /dev/null 2>&1; then
        print_error "Ollama is not running on http://172.29.144.1:11434"
        echo "Start Ollama with: docker run -d -p 11434:11434 ollama/ollama"
        echo "Then pull model: docker exec ollama ollama pull qwen2.5-coder:32b"
        return 1
    fi
    return 0
}

run_mock_tests() {
    print_header "Running Mock LLM Tests (Fast - ~31s)"

    pytest tests/test_nl_*.py \
        --ignore=tests/test_nl_real_llm_integration.py \
        -v \
        -m "not integration" \
        "$@"

    if [ $? -eq 0 ]; then
        print_success "Mock tests passed!"
    else
        print_error "Mock tests failed!"
        exit 1
    fi
}

run_real_tests() {
    print_header "Running Real LLM Tests (Slow - ~5-10min)"

    # Check Ollama is running
    if ! check_ollama; then
        exit 1
    fi

    print_warning "This will take 5-10 minutes..."

    pytest tests/test_nl_real_llm_integration.py \
        -v \
        -m integration \
        "$@"

    if [ $? -eq 0 ]; then
        print_success "Real LLM tests passed!"
    else
        print_error "Real LLM tests failed!"
        exit 1
    fi
}

run_coverage() {
    print_header "Running Tests with Coverage"

    pytest tests/test_nl_*.py \
        --ignore=tests/test_nl_real_llm_integration.py \
        --cov=src/nl \
        --cov-report=term \
        --cov-report=html \
        -v \
        -m "not integration"

    if [ $? -eq 0 ]; then
        print_success "Coverage report generated!"
        echo "Open htmlcov/index.html to view report"
    else
        print_error "Tests failed!"
        exit 1
    fi
}

# Main
MODE=${1:-both}

case "$MODE" in
    mock)
        run_mock_tests
        ;;
    real)
        run_real_tests
        ;;
    both)
        run_mock_tests
        echo ""
        run_real_tests
        ;;
    coverage)
        run_coverage
        ;;
    *)
        echo "Usage: $0 [mock|real|both|coverage]"
        echo ""
        echo "Options:"
        echo "  mock     - Run mock LLM tests only (fast, ~31s)"
        echo "  real     - Run real LLM tests only (slow, ~5-10min)"
        echo "  both     - Run all tests (default)"
        echo "  coverage - Run mock tests with coverage report"
        exit 1
        ;;
esac

print_success "All requested tests completed successfully!"
