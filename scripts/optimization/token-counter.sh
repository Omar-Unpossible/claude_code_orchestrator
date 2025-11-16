#!/bin/bash
# token-counter.sh
# Measures token counts for all Claude Code documentation files
# Usage: ./scripts/optimization/token-counter.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Token calculation function (words × 1.3 approximation)
calculate_tokens() {
    local file=$1
    if [ ! -f "$file" ]; then
        echo "0"
        return
    fi
    local words=$(wc -w < "$file" 2>/dev/null || echo "0")
    echo "$words * 1.3" | bc | cut -d'.' -f1
}

# Line count function
count_lines() {
    local file=$1
    if [ ! -f "$file" ]; then
        echo "0"
        return
    fi
    wc -l < "$file" 2>/dev/null || echo "0"
}

# Status indicator
status_indicator() {
    local current=$1
    local min=$2
    local max=$3

    if [ "$current" -lt "$min" ]; then
        echo -e "${YELLOW}⚠️ Below target${NC}"
    elif [ "$current" -gt "$max" ]; then
        echo -e "${RED}❌ Exceeds target${NC}"
    else
        echo -e "${GREEN}✅ Within target${NC}"
    fi
}

echo -e "${BLUE}=== CLAUDE CODE TOKEN COUNTER ===${NC}"
echo ""
echo "Token calculation: words × 1.3 (approximation)"
echo ""

# CLAUDE.md
CLAUDE_LINES=$(count_lines "CLAUDE.md")
CLAUDE_TOKENS=$(calculate_tokens "CLAUDE.md")
CLAUDE_STATUS=$(status_indicator "$CLAUDE_TOKENS" 3000 5000)
echo -e "${BLUE}CLAUDE.md:${NC}"
echo "  Lines: $CLAUDE_LINES (target: 300-400)"
echo "  Tokens: $CLAUDE_TOKENS (target: 3,000-5,000)"
echo "  Status: $CLAUDE_STATUS"
echo ""

# PROJECT.md
PROJECT_LINES=$(count_lines ".claude/PROJECT.md")
PROJECT_TOKENS=$(calculate_tokens ".claude/PROJECT.md")
PROJECT_STATUS=$(status_indicator "$PROJECT_TOKENS" 5000 9000)
echo -e "${BLUE}.claude/PROJECT.md:${NC}"
echo "  Lines: $PROJECT_LINES (target: 400-700)"
echo "  Tokens: $PROJECT_TOKENS (target: 5,000-9,000)"
echo "  Status: $PROJECT_STATUS"
echo ""

# RULES.md
RULES_LINES=$(count_lines ".claude/RULES.md")
RULES_TOKENS=$(calculate_tokens ".claude/RULES.md")
RULES_STATUS=$(status_indicator "$RULES_TOKENS" 2000 4000)
echo -e "${BLUE}.claude/RULES.md:${NC}"
echo "  Lines: $RULES_LINES"
echo "  Tokens: $RULES_TOKENS (target: 2,000-4,000)"
echo "  Status: $RULES_STATUS"
echo ""

# Skills metadata (if exists)
SKILLS_METADATA_TOKENS=0
SKILLS_COUNT=0
if [ -d ".claude/skills" ]; then
    echo -e "${BLUE}.claude/skills/ (Metadata):${NC}"
    for skill_dir in .claude/skills/*/; do
        if [ -d "$skill_dir" ]; then
            skill_name=$(basename "$skill_dir")
            skill_file="${skill_dir}SKILL.md"
            if [ -f "$skill_file" ]; then
                # Count only metadata (first ~10 lines typically)
                metadata_words=$(head -15 "$skill_file" | wc -w)
                metadata_tokens=$(echo "$metadata_words * 1.3" | bc | cut -d'.' -f1)
                SKILLS_METADATA_TOKENS=$((SKILLS_METADATA_TOKENS + metadata_tokens))
                SKILLS_COUNT=$((SKILLS_COUNT + 1))
                echo "  - $skill_name: ~$metadata_tokens tokens (metadata)"
            fi
        fi
    done
    SKILLS_STATUS=$(status_indicator "$SKILLS_METADATA_TOKENS" 300 500)
    echo "  Total Skills: $SKILLS_COUNT"
    echo "  Total Metadata: $SKILLS_METADATA_TOKENS tokens (target: 300-500)"
    echo "  Status: $SKILLS_STATUS"
else
    echo -e "${YELLOW}.claude/skills/:${NC} ❌ Directory not found"
    echo "  Recommendation: Create Skills architecture"
fi
echo ""

# Config overhead estimate
CONFIG_OVERHEAD=100
echo -e "${BLUE}Config Overhead:${NC} ~$CONFIG_OVERHEAD tokens (estimated)"
echo ""

# Total startup context
TOTAL_STARTUP=$((CLAUDE_TOKENS + PROJECT_TOKENS + RULES_TOKENS + SKILLS_METADATA_TOKENS + CONFIG_OVERHEAD))
echo -e "${BLUE}=== TOTAL STARTUP CONTEXT ===${NC}"
echo "├─ CLAUDE.md:       $CLAUDE_TOKENS tokens"
echo "├─ PROJECT.md:      $PROJECT_TOKENS tokens"
echo "├─ RULES.md:        $RULES_TOKENS tokens"
echo "├─ Skills metadata: $SKILLS_METADATA_TOKENS tokens"
echo "├─ Config:          ~$CONFIG_OVERHEAD tokens"
echo "└─ TOTAL:           $TOTAL_STARTUP tokens"
echo ""

# Budget analysis
TARGET_MAX=15000
if [ "$TOTAL_STARTUP" -gt "$TARGET_MAX" ]; then
    OVER=$((TOTAL_STARTUP - TARGET_MAX))
    echo -e "${RED}❌ OVER BUDGET by $OVER tokens${NC}"
    echo "  Action required: Reduce documentation or extract Skills"
else
    UNDER=$((TARGET_MAX - TOTAL_STARTUP))
    UTILIZATION=$(echo "scale=1; $TOTAL_STARTUP * 100 / $TARGET_MAX" | bc)
    echo -e "${GREEN}✅ WITHIN BUDGET${NC}"
    echo "  Remaining: $UNDER tokens"
    echo "  Utilization: ${UTILIZATION}%"

    if [ "$TOTAL_STARTUP" -lt 8000 ]; then
        echo -e "  ${YELLOW}Note: Files are underutilized - consider expanding to target ranges${NC}"
    fi
fi
echo ""

# Skills on-demand content (if exists)
if [ -d ".claude/skills" ] && [ "$SKILLS_COUNT" -gt 0 ]; then
    SKILLS_CONTENT_TOKENS=0
    echo -e "${BLUE}=== SKILLS ON-DEMAND CONTENT ===${NC}"
    for skill_dir in .claude/skills/*/; do
        if [ -d "$skill_dir" ]; then
            skill_name=$(basename "$skill_dir")
            skill_file="${skill_dir}SKILL.md"
            if [ -f "$skill_file" ]; then
                skill_tokens=$(calculate_tokens "$skill_file")
                # Subtract metadata (already counted)
                metadata_words=$(head -15 "$skill_file" | wc -w)
                metadata_tokens=$(echo "$metadata_words * 1.3" | bc | cut -d'.' -f1)
                content_tokens=$((skill_tokens - metadata_tokens))
                SKILLS_CONTENT_TOKENS=$((SKILLS_CONTENT_TOKENS + content_tokens))
                echo "  - $skill_name: ~$content_tokens tokens (content only)"
            fi
        fi
    done
    echo ""
    echo "Total on-demand content: $SKILLS_CONTENT_TOKENS tokens"
    echo "Total managed (startup + on-demand): $((TOTAL_STARTUP + SKILLS_CONTENT_TOKENS)) tokens"
    echo ""
fi

# Summary recommendations
echo -e "${BLUE}=== RECOMMENDATIONS ===${NC}"
if [ "$CLAUDE_TOKENS" -lt 3000 ]; then
    echo "- Expand CLAUDE.md to reach 3K-5K token target"
fi
if [ "$PROJECT_TOKENS" -lt 5000 ]; then
    echo "- Expand PROJECT.md to reach 5K-9K token target OR extract Skills"
fi
if [ "$RULES_TOKENS" -lt 2000 ]; then
    echo "- Expand RULES.md to reach 2K-4K token target"
fi
if [ ! -d ".claude/skills" ]; then
    echo "- Create .claude/skills/ directory for progressive disclosure"
fi
if [ "$SKILLS_COUNT" -eq 0 ] && [ -d ".claude/skills" ]; then
    echo "- Extract specialized content to Skills (>500 tokens, <50% usage)"
fi

echo ""
echo "For detailed optimization guidance, see:"
echo "  docs/research/claude_code_project_optimization/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md"
