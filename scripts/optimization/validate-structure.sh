#!/bin/bash
# validate-structure.sh
# Pre-commit validation for Claude Code documentation structure
# Checks all 27 optimization rules
# Usage: ./scripts/optimization/validate-structure.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}CLAUDE CODE STRUCTURE VALIDATOR${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
pass() {
    echo -e "${GREEN}✅ $1${NC}"
    PASSED=$((PASSED + 1))
}

fail() {
    echo -e "${RED}❌ $1${NC}"
    FAILED=$((FAILED + 1))
}

warn() {
    echo -e "${YELLOW}⚠️ $1${NC}"
    WARNINGS=$((WARNINGS + 1))
}

info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Token calculation
calc_tokens() {
    local file=$1
    if [ ! -f "$file" ]; then echo "0"; return; fi
    local words=$(wc -w < "$file" 2>/dev/null || echo "0")
    echo "$words * 1.3" | bc | cut -d'.' -f1
}

count_lines() {
    local file=$1
    if [ ! -f "$file" ]; then echo "0"; return; fi
    wc -l < "$file" 2>/dev/null || echo "0"
}

echo "=== FILE STRUCTURE CHECKS ==="
echo ""

# RULE 1: CLAUDE.md size
info "RULE 1: CLAUDE.md size (300-400 lines, 3K-5K tokens)"
if [ -f "CLAUDE.md" ]; then
    CLAUDE_LINES=$(count_lines "CLAUDE.md")
    CLAUDE_TOKENS=$(calc_tokens "CLAUDE.md")

    if [ "$CLAUDE_LINES" -lt 300 ] || [ "$CLAUDE_LINES" -gt 400 ]; then
        warn "CLAUDE.md has $CLAUDE_LINES lines (target: 300-400)"
    else
        pass "CLAUDE.md lines: $CLAUDE_LINES"
    fi

    if [ "$CLAUDE_TOKENS" -lt 3000 ] || [ "$CLAUDE_TOKENS" -gt 5000 ]; then
        warn "CLAUDE.md has $CLAUDE_TOKENS tokens (target: 3K-5K)"
    else
        pass "CLAUDE.md tokens: $CLAUDE_TOKENS"
    fi
else
    fail "CLAUDE.md not found"
fi
echo ""

# RULE 2: PROJECT.md size
info "RULE 2: PROJECT.md size (400-700 lines, 5K-9K tokens)"
if [ -f ".claude/PROJECT.md" ]; then
    PROJECT_LINES=$(count_lines ".claude/PROJECT.md")
    PROJECT_TOKENS=$(calc_tokens ".claude/PROJECT.md")

    if [ "$PROJECT_LINES" -lt 400 ] || [ "$PROJECT_LINES" -gt 700 ]; then
        warn "PROJECT.md has $PROJECT_LINES lines (target: 400-700)"
    else
        pass "PROJECT.md lines: $PROJECT_LINES"
    fi

    if [ "$PROJECT_TOKENS" -lt 5000 ] || [ "$PROJECT_TOKENS" -gt 9000 ]; then
        warn "PROJECT.md has $PROJECT_TOKENS tokens (target: 5K-9K)"
    else
        pass "PROJECT.md tokens: $PROJECT_TOKENS"
    fi
else
    fail "PROJECT.md not found"
fi
echo ""

# RULE 3: RULES.md size (if exists)
info "RULE 3: RULES.md size (2K-4K tokens)"
if [ -f ".claude/RULES.md" ]; then
    RULES_TOKENS=$(calc_tokens ".claude/RULES.md")
    if [ "$RULES_TOKENS" -lt 2000 ] || [ "$RULES_TOKENS" -gt 4000 ]; then
        warn "RULES.md has $RULES_TOKENS tokens (target: 2K-4K)"
    else
        pass "RULES.md tokens: $RULES_TOKENS"
    fi
else
    info "RULES.md not found (optional)"
fi
echo ""

# RULE 4: Total startup context
info "RULE 4: Total startup context (<15K tokens)"
TOTAL_STARTUP=$((CLAUDE_TOKENS + PROJECT_TOKENS + RULES_TOKENS + 100))

# Add Skills metadata if exists
SKILLS_META=0
if [ -d ".claude/skills" ]; then
    for skill in .claude/skills/*/SKILL.md; do
        if [ -f "$skill" ]; then
            meta=$(head -15 "$skill" | wc -w | awk '{print int($1 * 1.3)}')
            SKILLS_META=$((SKILLS_META + meta))
        fi
    done
fi
TOTAL_STARTUP=$((TOTAL_STARTUP + SKILLS_META))

if [ "$TOTAL_STARTUP" -gt 15000 ]; then
    fail "Total startup: $TOTAL_STARTUP tokens (exceeds 15K)"
else
    pass "Total startup: $TOTAL_STARTUP tokens (within 15K budget)"
fi
echo ""

# RULE 5: Skills metadata budget
info "RULE 5: Skills metadata (300-500 tokens for 10-15 Skills)"
if [ -d ".claude/skills" ]; then
    SKILLS_COUNT=$(find .claude/skills -type d -mindepth 1 -maxdepth 1 | wc -l)
    if [ "$SKILLS_COUNT" -eq 0 ]; then
        warn "No Skills found (recommended: 10-15 Skills)"
    elif [ "$SKILLS_META" -lt 300 ] || [ "$SKILLS_META" -gt 500 ]; then
        warn "Skills metadata: $SKILLS_META tokens (target: 300-500)"
    else
        pass "Skills: $SKILLS_COUNT Skills, $SKILLS_META tokens metadata"
    fi
else
    warn "Skills directory not found"
fi
echo ""

echo "=== CONTENT QUALITY CHECKS ==="
echo ""

# RULE 12: Soft language check
info "RULE 12: Directive language (no 'should'/'consider')"
SOFT_LANG=$(grep -c -i "should\|consider\|recommend\|might want" \
    CLAUDE.md .claude/PROJECT.md .claude/RULES.md 2>/dev/null || echo "0")
if [ "$SOFT_LANG" -eq 0 ]; then
    pass "No soft language found"
else
    warn "Found $SOFT_LANG instance(s) of soft language"
fi
echo ""

# RULE 13: Long examples check
info "RULE 13: Example compactness (≤10 lines)"
LONG_EXAMPLES=0
for file in CLAUDE.md .claude/PROJECT.md .claude/RULES.md; do
    if [ -f "$file" ]; then
        LONG=$(awk '/```/,/```/ {if(/```/) {if(start) {if(NR-start>11) count++; start=0} else {start=NR}}} END {print count+0}' "$file")
        LONG_EXAMPLES=$((LONG_EXAMPLES + LONG))
    fi
done

if [ "$LONG_EXAMPLES" -eq 0 ]; then
    pass "All examples ≤10 lines"
else
    warn "Found $LONG_EXAMPLES example(s) >10 lines"
fi
echo ""

# RULE 19: .gitignore configuration
info "RULE 19: Git tracking configuration"
if [ -f ".gitignore" ]; then
    if grep -q "^\.claude/$" .gitignore; then
        fail ".gitignore blocks ALL .claude/ files (should be selective)"
    elif grep -q "\.claude/settings\.local\.json" .gitignore; then
        pass ".gitignore selectively ignores .claude/ files"
    else
        warn ".gitignore doesn't ignore .claude/settings.local.json"
    fi
else
    warn ".gitignore not found"
fi
echo ""

echo "=== STRUCTURE CHECKS ==="
echo ""

# Check Skills structure if exists
info "RULE 14-17: Skills architecture"
if [ -d ".claude/skills" ]; then
    for skill_dir in .claude/skills/*/; do
        if [ -d "$skill_dir" ]; then
            skill_name=$(basename "$skill_dir")
            skill_file="${skill_dir}SKILL.md"

            if [ -f "$skill_file" ]; then
                # Check for required metadata
                if ! grep -q "^\*\*Description\*\*:" "$skill_file"; then
                    warn "$skill_name missing Description metadata"
                fi
                if ! grep -q "^\*\*Triggers\*\*:" "$skill_file"; then
                    warn "$skill_name missing Triggers metadata"
                fi
                if ! grep -q "^\*\*Token Cost\*\*:" "$skill_file"; then
                    warn "$skill_name missing Token Cost metadata"
                fi

                # Check size
                skill_tokens=$(calc_tokens "$skill_file")
                if [ "$skill_tokens" -lt 500 ]; then
                    warn "$skill_name is $skill_tokens tokens (recommended: >500 for Skills)"
                fi
            else
                warn "$skill_name missing SKILL.md file"
            fi
        fi
    done
    pass "Skills directory structure exists"
else
    warn "No .claude/skills/ directory found"
fi
echo ""

# Check for required files
info "Required files check"
REQUIRED_FILES=("CLAUDE.md" ".claude/PROJECT.md")
for req_file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$req_file" ]; then
        pass "$req_file exists"
    else
        fail "$req_file missing"
    fi
done
echo ""

echo "=== VALIDATION SUMMARY ==="
echo ""
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

TOTAL_CHECKS=$((PASSED + WARNINGS + FAILED))
SUCCESS_RATE=$(echo "scale=1; $PASSED * 100 / $TOTAL_CHECKS" | bc)

echo "Success Rate: ${SUCCESS_RATE}%"
echo ""

# Exit code
if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo "Fix critical failures before committing."
    echo ""
    echo "For detailed guidance:"
    echo "  - Audit Report: docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_AUDIT_REPORT.md"
    echo "  - Action Plan: docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_ACTION_PLAN.md"
    echo "  - Optimization Rules: docs/research/claude_code_project_optimization/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md"
    exit 1
elif [ "$WARNINGS" -gt 5 ]; then
    echo -e "${YELLOW}⚠️ VALIDATION PASSED WITH WARNINGS${NC}"
    echo "Consider addressing warnings to improve compliance."
    exit 0
else
    echo -e "${GREEN}✅ VALIDATION PASSED${NC}"
    echo "Documentation structure meets optimization standards."
    exit 0
fi
