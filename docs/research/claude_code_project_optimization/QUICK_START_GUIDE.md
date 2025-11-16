# QUICK START GUIDE: Claude Code Project Audit

## 🚀 3-Minute Setup

### Step 1: Navigate to Your Project
```bash
cd /path/to/your/project
```

### Step 2: Copy the Optimization Rules to Your Project
```bash
# Copy the LLM-optimized rules document to your project root or .claude/ directory
cp /path/to/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md .claude/
```

### Step 3: Start Claude Code
```bash
claude
```

### Step 4: Paste This Exact Prompt

Copy everything between the === lines and paste into Claude Code:

===COPY FROM HERE===

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

===COPY TO HERE===

---

## What Happens Next

Claude Code will:
1. ✅ Run bash commands to analyze your project structure
2. ✅ Read all documentation files
3. ✅ Calculate token counts
4. ✅ Check against 27 optimization rules
5. ✅ Generate a comprehensive audit report
6. ✅ Provide a prioritized action plan
7. ✅ Create validation scripts

**Expected time**: 5-10 minutes

---

## After the Audit

### Option 1: Fix Issues Manually

Review the audit report and implement fixes one by one:

```
Claude, implement the first P0 critical fix from your audit report.
Show me the before/after and verify the token savings.
```

### Option 2: Let Claude Code Fix Everything

```
Based on your audit report, implement all P0 and P1 fixes automatically.
For each fix:
1. Show me what you're changing
2. Apply the change
3. Verify compliance
4. Report token savings

Start with P0 issues.
```

### Option 3: Focus on Specific Issues

```
From your audit report, focus only on:
- Eliminating redundancy (RULE 10)
- Converting prose to bullets (RULE 11)

Fix these issues now and show me the token savings.
```

---

## Common Follow-Up Prompts

### To Create Missing Skills:
```
Based on your audit, create Skills for all content that meets the criteria:
- >500 tokens
- Used <50% of time
- Self-contained domain

For each Skill, show me the content you'll extract before creating it.
```

### To Compress Examples:
```
Find all code examples >10 lines in CLAUDE.md.
For each one, show me:
1. Current example (with line count)
2. Compressed version (≤10 lines)
3. Token savings

Then apply the changes.
```

### To Generate Validation Scripts:
```
Create a comprehensive pre-commit validation script that checks:
- File size limits (RULE 1-2)
- Token budgets (RULE 4)
- No soft language (RULE 12)
- No long examples (RULE 13)

Save to .git/hooks/pre-commit and make executable.
```

### To Fix Redundancy:
```
You identified redundancy in your audit. For each instance:
1. Show me both duplicates
2. Determine the correct location
3. Remove the duplicate
4. Add a reference if needed

Apply all redundancy fixes now.
```

---

## Measuring Success

After implementing fixes, verify improvements:

```
Re-run the audit to verify improvements.

Compare:
- Previous token count vs. new token count
- Previous violations vs. current violations
- Provide a before/after summary

Expected improvements:
- Total startup tokens reduced by 40-75%
- All P0 violations resolved
- File sizes within targets
```

---

## Troubleshooting

### "I don't see CLAUDE.md or .claude/ directory"

Your project may not be set up for Claude Code yet. Run:

```
Create a new Claude Code configuration for this project following best practices:

1. Create CLAUDE.md with:
   - Project identity
   - Core rules
   - Forbidden operations
   Target: 300-400 lines, 3K-5K tokens

2. Create .claude/ directory structure:
   - .claude/PROJECT.md (architecture, workflows)
   - .claude/settings.json
   - .claude/skills/

3. Configure .gitignore properly

Use the optimization rules as your guide.
```

### "Token counts seem off"

```
Install tiktoken for accurate token counting:

pip install tiktoken anthropic

Then create a Python script to count tokens accurately:

```python
import tiktoken

def count_tokens(filepath):
    encoding = tiktoken.encoding_for_model("gpt-4")
    with open(filepath) as f:
        return len(encoding.encode(f.read()))

print(f"CLAUDE.md: {count_tokens('CLAUDE.md')} tokens")
```

### "Claude Code can't access files"

Make sure you're running from the project root:

```bash
pwd  # Should show your project directory
ls -la  # Should show CLAUDE.md and .claude/
```

If files are missing, check the current directory and navigate correctly.

---

## Pro Tips

1. **Back up first**: `git commit -am "Before optimization"`
2. **Iterate**: Fix P0, re-audit, fix P1, re-audit
3. **Measure**: Track token counts before/after each change
4. **Automate**: Use generated scripts for ongoing validation
5. **Commit atomic changes**: One fix per commit
6. **Test**: Verify Claude Code still works after each major change

---

## Success Checklist

After optimization, you should have:

- [ ] CLAUDE.md: 300-400 lines, 3K-5K tokens
- [ ] .claude/PROJECT.md: 400-700 lines, 5K-9K tokens  
- [ ] Total startup: <15K tokens
- [ ] Zero redundancy across files
- [ ] All prose converted to bullets
- [ ] All directive language (no "should")
- [ ] All examples ≤10 lines
- [ ] Skills created for specialized content
- [ ] Pre-commit validation script in place
- [ ] .gitignore configured correctly
- [ ] 40-75% token reduction achieved

---

## Files You've Received

All available in `/mnt/user-data/outputs/`:

1. **CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md** - The complete optimization rules
2. **RULE_INDEX_STANDALONE.md** - All 27 rules in detail
3. **WHEN_TO_APPLY_STANDALONE.md** - Situation-based rule lookup
4. **CLAUDE_CODE_AUDIT_PROMPT.md** - Comprehensive prompt with instructions
5. **CLAUDE_CODE_AUDIT_PROMPT_SIMPLE.md** - Simplified ready-to-paste prompt
6. **QUICK_START_GUIDE.md** (this file) - Step-by-step instructions
7. **TRANSFORMATION_SUMMARY.md** - Details of the optimization process

---

## Need Help?

If you get stuck or want to customize the audit:

```
I need help with [specific issue from the audit report].

Current state: [describe]
Desired state: [describe]
Rule reference: RULE [number]

How should I fix this?
```

---

Good luck with your optimization! 🚀
