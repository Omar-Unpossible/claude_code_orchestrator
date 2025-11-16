#!/bin/bash
# find-soft-language.sh
# Finds soft language violations (RULE 12: should use MUST/NEVER/ALWAYS)
# Usage: ./scripts/optimization/find-soft-language.sh

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== SOFT LANGUAGE DETECTOR (RULE 12) ===${NC}"
echo ""
echo "Searching for forbidden soft language..."
echo "  - 'should' → Use 'MUST' or 'NEVER'"
echo "  - 'consider' → Use 'MUST' or 'ALWAYS'"
echo "  - 'recommend' → Use 'MUST' or 'SHOULD BE'"
echo "  - 'might want' → Use 'MUST' or directive"
echo "  - 'it's good to' → Use 'MUST' or 'ALWAYS'"
echo "  - 'we suggest' → Use 'MUST'"
echo ""

FILES=(
    "CLAUDE.md"
    ".claude/PROJECT.md"
    ".claude/RULES.md"
)

# Add Skills if they exist
if [ -d ".claude/skills" ]; then
    for skill in .claude/skills/*/SKILL.md; do
        if [ -f "$skill" ]; then
            FILES+=("$skill")
        fi
    done
fi

VIOLATIONS_FOUND=0

for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        continue
    fi

    echo -e "${BLUE}Checking: $file${NC}"

    # Search for patterns
    MATCHES=$(grep -n -i \
        -e "should" \
        -e "consider" \
        -e "recommend" \
        -e "might want" \
        -e "it's good to" \
        -e "we suggest" \
        -e "you may want" \
        -e "it would be" \
        "$file" 2>/dev/null || true)

    if [ -n "$MATCHES" ]; then
        echo "$MATCHES" | while IFS= read -r line; do
            LINE_NUM=$(echo "$line" | cut -d: -f1)
            CONTENT=$(echo "$line" | cut -d: -f2-)

            # Highlight the soft language
            HIGHLIGHTED=$(echo "$CONTENT" | sed -E \
                -e "s/(should)/${RED}\1${NC}/gi" \
                -e "s/(consider)/${RED}\1${NC}/gi" \
                -e "s/(recommend)/${RED}\1${NC}/gi" \
                -e "s/(might want)/${RED}\1${NC}/gi" \
                -e "s/(it's good to)/${RED}\1${NC}/gi" \
                -e "s/(we suggest)/${RED}\1${NC}/gi" \
                -e "s/(you may want)/${RED}\1${NC}/gi" \
                -e "s/(it would be)/${RED}\1${NC}/gi")

            echo -e "  ${YELLOW}Line $LINE_NUM:${NC} $HIGHLIGHTED"
            VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
        done
        echo ""
    else
        echo -e "  ${GREEN}✅ No soft language found${NC}"
        echo ""
    fi
done

# Summary
echo -e "${BLUE}=== SUMMARY ===${NC}"
if [ "$VIOLATIONS_FOUND" -eq 0 ]; then
    echo -e "${GREEN}✅ No violations found - RULE 12 compliant${NC}"
else
    echo -e "${YELLOW}⚠️ Found $VIOLATIONS_FOUND soft language instance(s)${NC}"
    echo ""
    echo "Recommended fixes:"
    echo "  - 'should do X' → 'MUST do X'"
    echo "  - 'you should' → 'MUST' or 'ALWAYS'"
    echo "  - 'consider using' → 'MUST use' or 'USE'"
    echo "  - 'recommended' → 'MUST use' or 'required'"
    echo "  - 'it's good to' → 'ALWAYS' or 'MUST'"
    echo ""
    echo "Exception: Soft language is OK in:"
    echo "  - Examples showing user input"
    echo "  - Quotes from external sources"
    echo "  - Describing optional features (use 'CAN' instead)"
fi

exit 0
