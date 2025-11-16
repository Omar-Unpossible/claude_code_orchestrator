#!/bin/bash
# find-long-examples.sh
# Finds code examples exceeding 10-line limit (RULE 13)
# Usage: ./scripts/optimization/find-long-examples.sh [max_lines]

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Max lines allowed (default 10)
MAX_LINES=${1:-10}

echo -e "${BLUE}=== LONG CODE EXAMPLE DETECTOR (RULE 13) ===${NC}"
echo ""
echo "Searching for code examples exceeding $MAX_LINES lines..."
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
TOTAL_EXAMPLES=0

for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        continue
    fi

    echo -e "${BLUE}Checking: $file${NC}"

    # Use awk to find code blocks and count lines
    VIOLATIONS=$(awk -v max="$MAX_LINES" '
        /```/ {
            if (in_block) {
                # Ending block
                lines = NR - start - 1
                total_examples++
                if (lines > max) {
                    print start ":" lines
                    violations++
                }
                in_block = 0
            } else {
                # Starting block
                start = NR
                in_block = 1
            }
        }
        END {
            print "TOTAL:" total_examples
            print "VIOLATIONS:" violations
        }
    ' "$file")

    # Parse results
    TOTAL=$(echo "$VIOLATIONS" | grep "^TOTAL:" | cut -d: -f2)
    VIOLS=$(echo "$VIOLATIONS" | grep "^VIOLATIONS:" | cut -d: -f2)
    EXAMPLES=$(echo "$VIOLATIONS" | grep -v "^TOTAL:" | grep -v "^VIOLATIONS:" || true)

    TOTAL_EXAMPLES=$((TOTAL_EXAMPLES + TOTAL))

    if [ "$VIOLS" -gt 0 ]; then
        echo -e "  ${YELLOW}Found $VIOLS long example(s):${NC}"
        echo "$EXAMPLES" | while IFS=: read -r start_line length; do
            if [ -n "$start_line" ] && [ -n "$length" ]; then
                end_line=$((start_line + length + 1))
                echo -e "    ${RED}Lines $start_line-$end_line: $length lines${NC} (exceeds $MAX_LINES)"

                # Show snippet
                echo "    Preview:"
                sed -n "${start_line},$((start_line + 3))p" "$file" | sed 's/^/      /'
                echo "      ..."
                VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
            fi
        done
        echo ""
    else
        echo -e "  ${GREEN}✅ All $TOTAL examples ≤$MAX_LINES lines${NC}"
        echo ""
    fi
done

# Summary
echo -e "${BLUE}=== SUMMARY ===${NC}"
echo "Total examples found: $TOTAL_EXAMPLES"
echo "Examples exceeding $MAX_LINES lines: $VIOLATIONS_FOUND"
echo ""

if [ "$VIOLATIONS_FOUND" -eq 0 ]; then
    echo -e "${GREEN}✅ All examples comply with RULE 13 (≤$MAX_LINES lines)${NC}"
else
    echo -e "${YELLOW}⚠️ Found $VIOLATIONS_FOUND violation(s) - RULE 13${NC}"
    echo ""
    echo "Recommended fixes:"
    echo "  1. Compress examples by removing boilerplate"
    echo "  2. Use comments to explain, not prose"
    echo "  3. Show only key parts, use '...' for omitted code"
    echo "  4. Extract detailed examples to Skills"
    echo ""
    echo "Example compression:"
    echo "  BEFORE (13 lines):"
    echo "    def test_example():"
    echo "        # Setup"
    echo "        config = load_config()"
    echo "        orchestrator = Orchestrator(config)"
    echo "        ..."
    echo ""
    echo "  AFTER (8 lines):"
    echo "    def test_example():"
    echo "        orch = Orchestrator(load_config())"
    echo "        ..."
    echo ""
    echo "See: docs/research/claude_code_project_optimization/OBRA_OPTIMIZATION_ACTION_PLAN.md"
fi

exit 0
