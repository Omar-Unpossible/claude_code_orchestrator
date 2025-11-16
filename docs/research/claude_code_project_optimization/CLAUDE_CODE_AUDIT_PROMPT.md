# CLAUDE CODE PROJECT OPTIMIZATION PROMPT

**Purpose**: Systematic review and optimization of current project against Claude Code best practices  
**Output**: Detailed audit report + prioritized action plan + implementation scripts

---

## PROMPT FOR CLAUDE CODE CLI

```
You are an expert Claude Code optimizer conducting a comprehensive audit of this project.

CONTEXT:
I have loaded the Claude Code optimization rules into this conversation. Your task is to:
1. Analyze the current project structure
2. Measure against the 27 optimization rules
3. Identify violations and inefficiencies
4. Provide a prioritized action plan
5. Generate implementation scripts where applicable

RULES REFERENCE:
Review the project against these critical rules (from CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md):

FILE SIZE RULES:
- RULE 1: CLAUDE.md MUST be 300-400 lines, 3K-5K tokens
- RULE 2: .claude/PROJECT.md MUST be 400-700 lines, 5K-9K tokens
- RULE 3: .claude/RULES.md MUST be 2K-4K tokens (if exists)
- RULE 4: Total startup context MUST be <15K tokens
- RULE 5: Skills metadata MUST be 30-50 tokens each, 300-500 total

CONTENT RULES:
- RULE 8: Apply 4-tier distribution (CLAUDE.md → PROJECT.md → Skills → Code)
- RULE 9: Use content placement decision tree
- RULE 10: ELIMINATE all redundancy across files
- RULE 11: Use BULLETS over prose
- RULE 12: Use MUST/NEVER/ALWAYS (not "should"/"consider")
- RULE 13: Examples MUST be ≤10 lines

SKILLS RULES:
- RULE 14: Create Skills ONLY IF: >500 tokens AND <50% usage AND self-contained
- RULE 15-17: Follow Skill structure and metadata format

ANTI-PATTERNS:
- RULE 25-27: Check forbidden patterns in CLAUDE.md and Skills

ANALYSIS TASKS:

TASK 1: PROJECT STRUCTURE INVENTORY
Examine the current project and document:
- Does CLAUDE.md exist? Location? Line count? Estimated token count?
- Does .claude/PROJECT.md exist? Line count? Token count?
- Does .claude/RULES.md exist? Token count?
- Does .claude/skills/ directory exist? How many Skills?
- What other documentation files exist?
- Current .gitignore configuration for .claude/?

TASK 2: TOKEN MEASUREMENT
For each documentation file, calculate:
- Actual line count
- Word count
- Estimated token count (use: words × 1.3 as approximation, or tiktoken if available)
- Total startup context (sum of always-loaded files)
- Skill metadata token count (if Skills exist)

TASK 3: RULE VIOLATION DETECTION
For each of the 27 rules, check compliance and report:
- ✅ PASS: Rule is followed
- ⚠️ WARNING: Minor deviation
- ❌ FAIL: Clear violation

Specific checks:
- RULE 1: Is CLAUDE.md 300-400 lines and 3K-5K tokens?
- RULE 2: Is PROJECT.md 400-700 lines and 5K-9K tokens?
- RULE 4: Is total startup <15K tokens?
- RULE 10: Are there duplicated concepts across files?
- RULE 11: Is prose converted to bullets?
- RULE 12: Are "should/consider" present (forbidden soft language)?
- RULE 13: Are any examples >10 lines?
- RULE 25-27: Are forbidden patterns present?

TASK 4: CONTENT PLACEMENT AUDIT
Review all documentation content and identify:
- Content in CLAUDE.md that should be in PROJECT.md (affects multiple workflows, not all tasks)
- Content in CLAUDE.md that should be in Skills (specialized, infrequent)
- Content in PROJECT.md that should be in Skills (>500 tokens, <50% usage)
- Content that should be in CLAUDE.md but isn't (critical rules missing)
- Opportunities to create new Skills based on RULE 14 criteria

TASK 5: OPTIMIZATION OPPORTUNITIES
Identify specific optimization opportunities:
- Redundant content that can be eliminated
- Prose that should be converted to bullets
- Soft language that should be directive (should → MUST)
- Examples that need compression (>10 lines → ≤10 lines)
- Missing invocation triggers in Skill metadata
- Token-heavy sections that could be split

DELIVERABLES:

OUTPUT 1: AUDIT REPORT
Generate a comprehensive markdown report with these sections:

## Executive Summary
- Current state (line counts, token counts, compliance percentage)
- Critical violations requiring immediate attention
- Overall health score (0-100)

## Detailed Findings

### File Structure Analysis
[Table of all doc files with metrics]

### Rule Compliance Matrix
[27 rows, one per rule, with status and details]

### Token Budget Analysis
```
Current Startup Context:
├─ CLAUDE.md:           X tokens
├─ PROJECT.md:          X tokens
├─ RULES.md:            X tokens
├─ Skills metadata:     X tokens
├─ Config overhead:     ~X tokens
└─ TOTAL:               X tokens (target: <15,000)

Status: [OVER BUDGET / WITHIN BUDGET]
Overage: [X tokens to cut]
```

### Content Placement Issues
- [List of misplaced content with recommendations]

### Anti-Pattern Violations
- [List of forbidden patterns found]

### Optimization Opportunities
- [Prioritized list with estimated token savings]

OUTPUT 2: PRIORITIZED ACTION PLAN

Generate an action plan with 3 priority levels:

### P0 - CRITICAL (Do Immediately)
- Fix violations of RULE 1-5 (size limits)
- Remove forbidden patterns (RULE 25-27)
- Address total startup context >15K tokens

### P1 - HIGH IMPACT (Do This Week)
- Eliminate redundancy (RULE 10)
- Convert prose to bullets (RULE 11)
- Change soft language to directives (RULE 12)
- Compress examples to ≤10 lines (RULE 13)

### P2 - OPTIMIZATION (Do This Month)
- Create Skills for qualified content (RULE 14)
- Improve Skill metadata (RULE 15-17)
- Optimize content placement (RULE 8-9)

For each action, include:
- Specific file and line numbers (if applicable)
- Before/after example
- Estimated token savings
- Implementation steps

OUTPUT 3: IMPLEMENTATION SCRIPTS

Generate executable scripts to automate fixes where possible:

### Script 1: token-counter.sh
```bash
# Script to measure all documentation file tokens
```

### Script 2: find-soft-language.sh
```bash
# Script to find "should", "consider", "recommend" etc.
```

### Script 3: find-long-examples.sh
```bash
# Script to find code blocks >10 lines
```

### Script 4: validate-structure.sh
```bash
# Pre-commit validation script
```

OUTPUT 4: MIGRATION PLAN (if major restructuring needed)

If current structure deviates significantly, provide:
- Step-by-step migration sequence
- Backup strategy
- Rollback plan
- Validation checkpoints

EXECUTION INSTRUCTIONS:

1. START by reading all documentation files in the project
2. MEASURE token counts using word count × 1.3 approximation
3. ANALYZE against all 27 rules systematically
4. IDENTIFY specific violations with file locations
5. PRIORITIZE actions by impact and effort
6. GENERATE actionable outputs (reports, scripts, plans)

CRITICAL REQUIREMENTS:
- Be SPECIFIC: Always include file paths and line numbers
- Be MEASURABLE: Include exact token counts and percentages
- Be ACTIONABLE: Every finding must have a concrete fix
- Be COMPLETE: Check ALL 27 rules, no shortcuts
- Use DIRECTIVE language in recommendations (MUST/NEVER/ALWAYS)

Begin the audit now. Start with TASK 1: PROJECT STRUCTURE INVENTORY.
```

---

## HOW TO USE THIS PROMPT

### Method 1: Copy-Paste (Recommended for First Use)

1. **Navigate to your project directory**:
   ```bash
   cd /path/to/your/project
   ```

2. **Start Claude Code**:
   ```bash
   claude
   ```

3. **Load the optimization rules first**:
   ```
   Please read and analyze the file at [path-to]/CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md
   ```

4. **Then paste the prompt above** (the entire prompt between the ``` markers)

5. **Wait for complete analysis** - Claude Code will work through all tasks

6. **Review outputs and execute action plan**

### Method 2: Create a Slash Command (For Repeated Use)

Create `.claude/commands/audit-optimization.md`:

```markdown
# Audit Project Against Claude Code Best Practices

[Insert the full prompt from above]
```

Then run:
```bash
claude
/audit-optimization
```

### Method 3: Create a Shell Script Wrapper

Save as `optimize-project.sh`:

```bash
#!/bin/bash

echo "Starting Claude Code optimization audit..."
echo ""
echo "Step 1: Loading optimization rules..."

claude -p "Please read and analyze CLAUDE_CODE_OPTIMIZATION_LLM_OPTIMIZED.md and summarize the 27 rules briefly."

echo ""
echo "Step 2: Starting project audit..."
echo "This will analyze your project structure and generate a comprehensive report."
echo ""

claude <<EOF
[Insert the full prompt from above]
EOF
```

Make executable and run:
```bash
chmod +x optimize-project.sh
./optimize-project.sh
```

---

## EXPECTED OUTPUT STRUCTURE

After running this prompt, Claude Code will produce:

```
📊 AUDIT REPORT
├─ Executive Summary
├─ File Structure Analysis
├─ Rule Compliance Matrix (27 rules × status)
├─ Token Budget Analysis
├─ Content Placement Issues
├─ Anti-Pattern Violations
└─ Optimization Opportunities

📋 ACTION PLAN
├─ P0 - Critical (immediate fixes)
├─ P1 - High Impact (this week)
└─ P2 - Optimization (this month)

🔧 IMPLEMENTATION SCRIPTS
├─ token-counter.sh
├─ find-soft-language.sh
├─ find-long-examples.sh
└─ validate-structure.sh

📈 MIGRATION PLAN (if needed)
├─ Step-by-step sequence
├─ Backup strategy
└─ Validation checkpoints
```

---

## FOLLOW-UP PROMPTS

After receiving the audit report, use these follow-up prompts:

### To Execute P0 Critical Fixes:
```
Based on your audit report, implement all P0 critical fixes now. 
For each fix:
1. Show me the current state
2. Apply the fix
3. Verify the result
Start with the highest token-saving opportunities.
```

### To Create Missing Skills:
```
Based on your content placement audit, create Skills for all qualified content.
For each Skill:
1. Extract the content
2. Create the .claude/skills/[name]/ directory structure
3. Write the SKILL.md with proper metadata (30-50 tokens)
4. Move content from CLAUDE.md/PROJECT.md
5. Update references
Show me each Skill before creating it.
```

### To Compress Examples:
```
Find all code examples >10 lines in CLAUDE.md and PROJECT.md.
For each example:
1. Show me the current example
2. Compress to ≤10 lines (remove boilerplate, keep essentials)
3. Apply the change
4. Verify token savings
```

### To Eliminate Redundancy:
```
Based on your redundancy analysis, eliminate all duplicated content.
For each duplication:
1. Show me both instances
2. Determine the correct location (using RULE 8-9)
3. Keep one, replace the other with a reference
4. Verify no information lost
```

### To Generate Pre-Commit Hook:
```
Create a comprehensive pre-commit git hook that validates:
- CLAUDE.md: 300-400 lines, <5K tokens
- PROJECT.md: 400-700 lines, <9K tokens
- Total startup: <15K tokens
- No soft language (should/consider)
- No examples >10 lines
- No forbidden patterns

Save it to .git/hooks/pre-commit and make it executable.
```

---

## OPTIMIZATION LOOP

For best results, iterate through this cycle:

```
1. RUN AUDIT
   └─> Use the main prompt above

2. REVIEW FINDINGS
   └─> Understand violations and opportunities

3. IMPLEMENT P0 FIXES
   └─> Critical violations first

4. IMPLEMENT P1 FIXES
   └─> High-impact optimizations

5. RE-RUN AUDIT
   └─> Verify improvements

6. IMPLEMENT P2 OPTIMIZATIONS
   └─> Continue refinement

7. VALIDATE PERFORMANCE
   └─> Measure startup time, tasks before refresh

8. MAINTAIN
   └─> Use pre-commit hooks to prevent regression
```

---

## TROUBLESHOOTING

### If Claude Code says it can't access files:
```
Please use the bash tool to list all files in the current directory and subdirectories:
ls -la
ls -la .claude/
find . -name "*.md" -type f
```

### If token counting is unavailable:
```
For each file, count words and multiply by 1.3:
wc -w CLAUDE.md
wc -w .claude/PROJECT.md
wc -w .claude/RULES.md
```

### If the output is too long:
```
Generate the audit report in sections. Start with:
1. Executive Summary only
Then I'll ask for each section individually.
```

### If you want to focus on specific rules:
```
Focus your audit on RULE 1-5 (file size limits) and RULE 10 (redundancy) only.
Provide detailed findings just for these rules.
```

---

## TIPS FOR BEST RESULTS

1. **Run from project root**: Ensure Claude Code can see all files
2. **Load rules first**: Reference the LLM-optimized doc before the audit
3. **Be patient**: Comprehensive audit takes time
4. **Iterate**: Don't try to fix everything at once
5. **Validate**: Re-run audit after major changes
6. **Automate**: Use generated scripts for ongoing validation
7. **Commit frequently**: Make atomic commits during optimization
8. **Backup first**: Keep a copy before major restructuring

---

## SUCCESS METRICS

After optimization, you should achieve:

✅ **Token Efficiency**:
- CLAUDE.md: 3K-5K tokens (not 15K+)
- Total startup: <15K tokens (not 20K+)
- 40-75% token reduction

✅ **Performance**:
- Session startup: <2 seconds (not 4+ seconds)
- Tasks before refresh: >10 (not <6)
- Context confusion: <5% of sessions

✅ **Maintainability**:
- Zero redundancy across files
- All prose converted to bullets
- All directive language (no "should")
- Pre-commit validation in place

✅ **Compliance**:
- 27/27 rules passing
- No forbidden patterns
- Proper tier placement
- Skills properly structured

---

## DOCUMENT METADATA

**Version**: 1.0  
**Purpose**: Optimal prompt for Claude Code project optimization  
**Input**: Current project with documentation  
**Output**: Audit report + action plan + scripts  
**Estimated Time**: 10-20 minutes for audit, 1-4 hours for implementation  
**Difficulty**: Intermediate (requires understanding of project structure)
