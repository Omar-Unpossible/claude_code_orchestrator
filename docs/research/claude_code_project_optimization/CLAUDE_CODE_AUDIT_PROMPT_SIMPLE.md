# READY-TO-PASTE CLAUDE CODE AUDIT PROMPT
## Copy everything below the line and paste into Claude Code

---

You are an expert Claude Code optimizer conducting a comprehensive audit of this project.

CONTEXT:
I need you to analyze this project's Claude Code configuration against the optimization best practices and provide a detailed audit report with actionable fixes.

ANALYSIS TASKS:

**TASK 1: PROJECT STRUCTURE INVENTORY**

Examine the current project and document:
1. Does CLAUDE.md exist? Where? How many lines? Estimate tokens (words × 1.3)?
2. Does .claude/PROJECT.md exist? Lines? Tokens?
3. Does .claude/RULES.md exist? Tokens?
4. Does .claude/skills/ exist? How many Skills?
5. What other documentation files exist?
6. Is .claude/settings.local.json in .gitignore?

Use bash to check:
```bash
ls -la CLAUDE.md 2>/dev/null && wc -l CLAUDE.md && wc -w CLAUDE.md
ls -la .claude/PROJECT.md 2>/dev/null && wc -l .claude/PROJECT.md && wc -w .claude/PROJECT.md
ls -la .claude/RULES.md 2>/dev/null && wc -l .claude/RULES.md && wc -w .claude/RULES.md
ls -la .claude/skills/ 2>/dev/null && ls -1 .claude/skills/ | wc -l
cat .gitignore | grep -i "settings.local"
```

**TASK 2: RULE COMPLIANCE CHECK**

Check against these critical rules:

FILE SIZE RULES:
- RULE 1: CLAUDE.md MUST be 300-400 lines, 3,000-5,000 tokens
- RULE 2: PROJECT.md MUST be 400-700 lines, 5,000-9,000 tokens
- RULE 4: Total startup MUST be <15,000 tokens

Scan files for violations:
```bash
# Check for soft language (RULE 12 violation)
grep -n "should\|consider\|recommend\|might want" CLAUDE.md .claude/*.md 2>/dev/null

# Check for long code blocks (RULE 13 violation)
awk '/```/,/```/ {count++} /```/ && count%2==0 {if(NR-start>10) print "Long example at line " start; count=0} /```/ && count%2==1 {start=NR}' CLAUDE.md
```

CONTENT RULES:
- RULE 10: NO redundancy across files
- RULE 11: Use BULLETS, not prose paragraphs
- RULE 12: Use MUST/NEVER/ALWAYS (not "should"/"consider")
- RULE 13: Examples MUST be ≤10 lines

Read CLAUDE.md and check:
1. Are there prose paragraphs instead of bullets?
2. Is "should" or "consider" used instead of "MUST"?
3. Are there code examples >10 lines?
4. Is content duplicated with PROJECT.md?

**TASK 3: TOKEN BUDGET ANALYSIS**

Calculate total startup context:
```bash
echo "=== TOKEN BUDGET ANALYSIS ==="
CLAUDE_WORDS=$(wc -w < CLAUDE.md 2>/dev/null || echo "0")
PROJECT_WORDS=$(wc -w < .claude/PROJECT.md 2>/dev/null || echo "0")
RULES_WORDS=$(wc -w < .claude/RULES.md 2>/dev/null || echo "0")

CLAUDE_TOKENS=$(echo "$CLAUDE_WORDS * 1.3" | bc | cut -d'.' -f1)
PROJECT_TOKENS=$(echo "$PROJECT_WORDS * 1.3" | bc | cut -d'.' -f1)
RULES_TOKENS=$(echo "$RULES_WORDS * 1.3" | bc | cut -d'.' -f1)
TOTAL=$(echo "$CLAUDE_TOKENS + $PROJECT_TOKENS + $RULES_TOKENS" | bc)

echo "CLAUDE.md:     $CLAUDE_TOKENS tokens"
echo "PROJECT.md:    $PROJECT_TOKENS tokens"
echo "RULES.md:      $RULES_TOKENS tokens"
echo "TOTAL:         $TOTAL tokens (target: <15,000)"
echo ""
if [ $TOTAL -gt 15000 ]; then
  OVER=$(echo "$TOTAL - 15000" | bc)
  echo "❌ OVER BUDGET by $OVER tokens"
else
  UNDER=$(echo "15000 - $TOTAL" | bc)
  echo "✅ WITHIN BUDGET ($UNDER tokens remaining)"
fi
```

**TASK 4: CONTENT PLACEMENT AUDIT**

Read CLAUDE.md and identify:
- Specialized content that should be in Skills (>500 tokens, used <50% of time)
- Implementation details that should be in PROJECT.md
- Examples >10 lines that need compression
- Missing critical rules that should be in CLAUDE.md

Read .claude/PROJECT.md (if exists) and identify:
- Critical rules that should be in CLAUDE.md
- Specialized content that should be Skills

**DELIVERABLES:**

Generate a comprehensive report with:

## 1. EXECUTIVE SUMMARY
- Current status (compliant/needs work/critical issues)
- Total token count vs. target (<15K)
- Top 3 issues requiring immediate attention

## 2. RULE COMPLIANCE MATRIX

| Rule | Status | Details |
|------|--------|---------|
| RULE 1: CLAUDE.md size | ✅/⚠️/❌ | X lines, Y tokens (target: 300-400 lines, 3K-5K tokens) |
| RULE 2: PROJECT.md size | ✅/⚠️/❌ | X lines, Y tokens (target: 400-700 lines, 5K-9K tokens) |
| RULE 4: Total startup | ✅/⚠️/❌ | X tokens (target: <15K) |
| RULE 10: No redundancy | ✅/⚠️/❌ | [Found/None found] |
| RULE 11: Bullet format | ✅/⚠️/❌ | [X prose paragraphs found] |
| RULE 12: Directive language | ✅/⚠️/❌ | [X instances of "should"] |
| RULE 13: Example size | ✅/⚠️/❌ | [X examples >10 lines] |

## 3. DETAILED FINDINGS

List specific violations with:
- File path and line number
- Current state (quote)
- Required fix
- Estimated token savings

Example:
```
❌ CLAUDE.md:45-52 - Prose paragraph (RULE 11)
Current: "When working with the API, you should consider using..."
Fix: Convert to bullets with MUST/NEVER
Savings: ~30 tokens
```

## 4. PRIORITIZED ACTION PLAN

### P0 - CRITICAL (Fix Today)
- [ ] Issue with specific action

### P1 - HIGH IMPACT (Fix This Week)
- [ ] Issue with specific action

### P2 - OPTIMIZATION (Fix This Month)
- [ ] Issue with specific action

## 5. QUICK FIXES (Automated Scripts)

Generate these scripts:

### validate-tokens.sh
```bash
#!/bin/bash
# Token validation script
```

### find-violations.sh
```bash
#!/bin/bash
# Find common violations
```

EXECUTION INSTRUCTIONS:

1. START with bash commands to gather file metrics
2. READ all documentation files (CLAUDE.md, PROJECT.md, RULES.md)
3. ANALYZE against rules using grep/awk where helpful
4. CALCULATE token budgets using word count × 1.3
5. GENERATE the complete report above
6. PROVIDE specific, actionable fixes with file:line references

CRITICAL: Be SPECIFIC. Always include:
- Exact file paths
- Line numbers for violations
- Before/after examples
- Token impact estimates

Begin the audit now. Start with TASK 1: PROJECT STRUCTURE INVENTORY.
