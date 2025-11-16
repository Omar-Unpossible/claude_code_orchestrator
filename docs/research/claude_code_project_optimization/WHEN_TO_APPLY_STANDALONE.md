# WHEN TO APPLY: Situation-Based Rule Mapping
## Quick Reference for Context-Specific Rule Application

**Version**: 2.0.1-LLM  
**Last Updated**: November 15, 2025  
**Format**: Situation → Rule mappings for LLM decision-making

---

## SITUATION INDEX

1. [During Initial Project Setup](#1-during-initial-project-setup)
2. [When Creating New Documentation](#2-when-creating-new-documentation)
3. [When Optimizing Existing Project](#3-when-optimizing-existing-project)
4. [When Creating a Skill](#4-when-creating-a-skill)
5. [When Starting a Session](#5-when-starting-a-session)
6. [When Choosing a Model](#6-when-choosing-a-model)
7. [During Long Sessions](#7-during-long-sessions)
8. [When Refactoring Documentation](#8-when-refactoring-documentation)
9. [When Files Grow Too Large](#9-when-files-grow-too-large)
10. [When Experiencing Performance Issues](#10-when-experiencing-performance-issues)
11. [When Setting Up Automation](#11-when-setting-up-automation)
12. [When Migrating from Old Structure](#12-when-migrating-from-old-structure)
13. [Before Git Commit](#13-before-git-commit)
14. [When Context Warning Appears](#14-when-context-warning-appears)
15. [When Confusion Signals Detected](#15-when-confusion-signals-detected)
16. [When Adding New Features](#16-when-adding-new-features)
17. [During Code Review](#17-during-code-review)
18. [When Onboarding New Team Members](#18-when-onboarding-new-team-members)

---

## 1. During Initial Project Setup

### Apply These Rules:
- **RULE 1**: CLAUDE.md SIZE LIMIT
- **RULE 2**: PROJECT.md SIZE LIMIT
- **RULE 18**: CONFIGURATION FILE LOCATIONS
- **RULE 19**: GIT TRACKING

### Actions:
1. Create CLAUDE.md (300-400 lines, 3K-5K tokens)
2. Create .claude/PROJECT.md (400-700 lines, 5K-9K tokens)
3. Set up directory structure:
   ```
   .claude/
   ├─ settings.json
   ├─ settings.local.json  # git-ignore this
   ├─ skills/
   └─ PROJECT.md
   ```
4. Configure .gitignore for .claude/settings.local.json
5. Initialize with core rules in CLAUDE.md
6. Document architecture in PROJECT.md

### Validation:
- [ ] CLAUDE.md exists and meets token limits
- [ ] PROJECT.md exists and meets token limits
- [ ] .gitignore configured correctly
- [ ] Directory structure matches RULE 18

---

## 2. When Creating New Documentation

### Apply These Rules:
- **RULE 8**: 4-TIER CONTENT DISTRIBUTION
- **RULE 9**: CONTENT PLACEMENT DECISION TREE
- **RULE 14**: SKILL CREATION CRITERIA

### Decision Flow:
```
1. Does this affect EVERY task?
   YES → Add to CLAUDE.md
   NO → Continue to 2

2. Does this affect MULTIPLE modules/workflows?
   YES → Add to PROJECT.md
   NO → Continue to 3

3. Is this content >500 tokens AND used <50% of time?
   YES → Create Skill
   NO → Add to PROJECT.md or source code comments
```

### Actions:
- Evaluate content against decision tree
- Check token count if creating Skill
- Validate tier assignment
- Ensure no duplication with existing docs

### Validation:
- [ ] Content placed in correct tier
- [ ] No duplication across files
- [ ] Token budgets not exceeded
- [ ] Skill criteria met (if creating Skill)

---

## 3. When Optimizing Existing Project

### Apply These Rules:
- **RULE 4**: TOTAL STARTUP CONTEXT
- **RULE 10**: ELIMINATE REDUNDANCY
- **RULE 11**: BULLET-FIRST FORMATTING
- **RULE 12**: DIRECTIVE LANGUAGE

### Actions:
1. **Measure current state**:
   ```bash
   # Count tokens in all config files
   wc -w CLAUDE.md .claude/PROJECT.md .claude/RULES.md
   # Multiply by 1.3 for rough token estimate
   ```

2. **Identify redundancy**:
   - Search for duplicated concepts across files
   - Look for repeated examples
   - Find overlapping rules

3. **Convert prose to bullets**:
   - Replace paragraphs with imperative bullets
   - Remove narrative exposition
   - Keep only actionable directives

4. **Change language**:
   - "should" → MUST
   - "consider" → ALWAYS/NEVER
   - "it's good to" → MUST
   - "we recommend" → MUST

5. **Compress examples**:
   - Maximum 10 lines per example
   - Remove boilerplate
   - Use comments for explanation

### Validation:
- [ ] Total startup <15K tokens
- [ ] No redundancy detected
- [ ] All prose converted to bullets
- [ ] All soft language replaced with imperatives

---

## 4. When Creating a Skill

### Apply These Rules:
- **RULE 14**: SKILL CREATION CRITERIA
- **RULE 15**: SKILL STRUCTURE
- **RULE 16**: SKILL METADATA FORMAT
- **RULE 17**: SKILL INVOCATION SIGNALS

### Decision Checklist:
- [ ] Content >500 tokens?
- [ ] Used <50% of sessions?
- [ ] Self-contained domain?
- [ ] Does NOT depend heavily on other content?

If all YES → Create Skill. Otherwise, add to PROJECT.md or CLAUDE.md.

### Actions:
1. **Create directory structure**:
   ```
   .claude/skills/[skill-name]/
   ├─ SKILL.md          # Required
   ├─ instructions.md   # Optional
   ├─ examples/         # Optional
   └─ scripts/          # Optional
   ```

2. **Write SKILL.md header** (MUST include):
   ```markdown
   # [Skill Name]
   
   **Description**: [1-2 sentences, 30-50 tokens]
   **Triggers**: [When to invoke: keywords, task types, file patterns]
   **Token Cost**: ~[estimated] tokens when loaded
   ```

3. **Define invocation signals**:
   - Keywords (e.g., "docker", "containerization")
   - Task types (e.g., "deployment", "CI/CD setup")
   - File patterns (e.g., "Dockerfile", "docker-compose.yml")
   - Technologies (e.g., "kubernetes", "helm")

4. **Add detailed content** (instructions.md):
   - Can be longer since loaded on-demand
   - Include procedures, examples, references

### Validation:
- [ ] Meets creation criteria
- [ ] SKILL.md has required metadata
- [ ] Description 30-50 tokens
- [ ] Clear invocation signals
- [ ] Directory structure correct

---

## 5. When Starting a Session

### Apply These Rules:
- **RULE 6**: LOADING HIERARCHY
- **RULE 7**: PROGRESSIVE DISCLOSURE PATTERN
- **RULE 22**: CONTEXT WINDOW ALLOCATION

### Understand What Loads:
```
ALWAYS LOADED:
├─ Global config (~/.claude/)
├─ Project config (.claude/)
├─ CLAUDE.md
├─ PROJECT.md
└─ Skills metadata (descriptions only)

LOADED ON-DEMAND:
├─ Skill content (when Claude invokes)
├─ Source files (when read)
└─ MCP results (when queried)
```

### Actions:
- Know what's already in context vs. on-demand
- Monitor initial context usage
- Understand progressive disclosure benefit

### Validation:
- [ ] Session startup <2 seconds
- [ ] Total startup context <15K tokens
- [ ] Skills metadata loaded, content not loaded

---

## 6. When Choosing a Model

### Apply These Rules:
- **RULE 20**: MODEL CHOICE DECISION TREE
- **RULE 21**: EXTENDED THINKING TRIGGERS

### Decision Tree:
```
Task Type                          → Model
───────────────────────────────────────────────────
Complex reasoning                  → claude-sonnet-4-5-20250929
Novel architecture design          → claude-sonnet-4-5-20250929
Standard CRUD operations           → claude-sonnet-4-20250514
Well-defined implementation        → claude-sonnet-4-20250514
Simple refactoring                 → claude-haiku-4-5-20250919
Style formatting                   → claude-haiku-4-5-20250919
Maximum quality critical           → claude-opus-4-20241113
```

### Extended Thinking (--mode plan):
**USE for**:
- Novel architectural decisions
- Multiple solution path evaluation
- Complex security/compliance analysis
- Deep trade-off analysis

**NEVER use for**:
- Standard CRUD
- Formatting/linting
- Simple refactors
- Well-documented patterns

### Actions:
- Evaluate task complexity
- Select appropriate model
- Enable extended thinking only if needed
- Consider cost vs. quality trade-offs

### Validation:
- [ ] Model matches task complexity
- [ ] Extended thinking justified (if enabled)
- [ ] Cost-quality trade-off acceptable

---

## 7. During Long Sessions

### Apply These Rules:
- **RULE 23**: SESSION REFRESH TRIGGERS
- **RULE 24**: CONTEXT COMPACTION

### Monitor:
- Context usage percentage
- Task type changes
- Confusion signals

### Trigger Refresh When:
- Context >80% capacity
- Task types changed significantly
- Previous task complete AND new task unrelated
- Confusion signals detected (wrong assumptions, outdated info)

### Compact Context When >60% Full:
```bash
# If /compact command available:
/compact

# Manual compaction:
- Summarize completed subtasks
- Remove outdated tool results
- Keep active context
```

### Actions:
1. Check context percentage regularly
2. Compact at >60%
3. Refresh at >80% or task change
4. Start new session if confusion detected

### Validation:
- [ ] Context never exceeds 90%
- [ ] Compaction removes >10% tokens when triggered
- [ ] No confusion signals ignored

---

## 8. When Refactoring Documentation

### Apply These Rules:
- **RULE 25**: FORBIDDEN PATTERNS
- **RULE 26**: FORBIDDEN IN CLAUDE.md
- **RULE 27**: FORBIDDEN IN SKILLS

### Review Against Forbidden Patterns:
**NEVER**:
- [x] Duplicate content between files
- [x] Put implementation details in CLAUDE.md
- [x] Put critical rules in Skills
- [x] Create Skills for frequently-used content
- [x] Exceed token budgets
- [x] Use narrative prose
- [x] Explain rationale unnecessarily

### Check CLAUDE.md for Forbidden Content:
**NEVER include**:
- [x] Examples >10 lines
- [x] Technology-specific tutorials
- [x] Detailed API documentation
- [x] Procedures >5 steps
- [x] Historical context
- [x] Aspirational content

### Check Skills for Forbidden Content:
**NEVER include**:
- [x] Rules for >50% of tasks
- [x] Core project identity
- [x] Security constraints
- [x] Absolute prohibitions

### Actions:
1. Audit all documentation files
2. Check against forbidden patterns
3. Move misplaced content to correct tier
4. Remove or compress verbose content

### Validation:
- [ ] No forbidden patterns present
- [ ] CLAUDE.md clean of forbidden content
- [ ] Skills appropriate for on-demand loading

---

## 9. When Files Grow Too Large

### Apply These Rules:
- **RULE 1**: CLAUDE.md SIZE LIMIT
- **RULE 2**: PROJECT.md SIZE LIMIT
- **RULE 3**: RULES.md SIZE LIMIT
- **RULE 4**: TOTAL STARTUP CONTEXT
- **RULE 8**: 4-TIER CONTENT DISTRIBUTION

### Diagnosis:
```bash
# Check file sizes
wc -l CLAUDE.md                    # Should be 300-400 lines
wc -l .claude/PROJECT.md           # Should be 400-700 lines
wc -l .claude/RULES.md             # Should be reasonable

# Estimate tokens
wc -w CLAUDE.md | awk '{print $1 * 1.3}'  # Should be 3K-5K
wc -w .claude/PROJECT.md | awk '{print $1 * 1.3}'  # Should be 5K-9K
```

### Actions:
1. **Identify candidates for extraction**:
   - Content >500 tokens
   - Used <50% of time
   - Self-contained

2. **Move to Skills**:
   - Create new Skill
   - Move specialized content
   - Replace with reference in original file

3. **Compress remaining content**:
   - Convert prose to bullets
   - Compress examples to ≤10 lines
   - Remove redundancy
   - Eliminate rationale

4. **Validate tier placement**:
   - Every task content → CLAUDE.md
   - Multiple workflow content → PROJECT.md
   - Specialized content → Skills

### Validation:
- [ ] CLAUDE.md: 300-400 lines, 3K-5K tokens
- [ ] PROJECT.md: 400-700 lines, 5K-9K tokens
- [ ] Total startup: <15K tokens
- [ ] Extracted content now in appropriate Skills

---

## 10. When Experiencing Performance Issues

### Apply These Rules:
- **RULE 4**: TOTAL STARTUP CONTEXT
- **RULE 10**: ELIMINATE REDUNDANCY
- **RULE 13**: EXAMPLE COMPACTNESS
- **RULE 22**: CONTEXT WINDOW ALLOCATION
- **RULE 23**: SESSION REFRESH TRIGGERS

### Symptoms:
- Slow session startup (>2 seconds)
- Frequent context capacity warnings
- Tasks require refresh after <10 iterations
- Confusion signals (outdated assumptions)

### Diagnostic Steps:
1. **Measure startup tokens**:
   ```python
   import tiktoken
   encoding = tiktoken.encoding_for_model("gpt-4")
   
   def count_file(path):
       with open(path) as f:
           return len(encoding.encode(f.read()))
   
   total = (
       count_file("CLAUDE.md") +
       count_file(".claude/PROJECT.md") +
       count_file(".claude/RULES.md")
   )
   print(f"Startup tokens: {total} (target: <15,000)")
   ```

2. **Identify redundancy**:
   - Grep for duplicate concepts
   - Find repeated examples
   - Locate overlapping rules

3. **Check example length**:
   - Find code blocks >10 lines
   - Identify verbose examples

4. **Monitor context allocation**:
   - Check context usage percentage
   - Verify reserve buffer adequate

### Actions:
1. **Reduce startup tokens**: Target <15K
2. **Remove redundancy**: Eliminate duplicates
3. **Compress examples**: Max 10 lines each
4. **Refresh sessions**: Don't wait for 90%
5. **Validate allocation**: Adjust if needed

### Validation:
- [ ] Startup tokens <15K
- [ ] Session startup <2 seconds
- [ ] >10 tasks before refresh
- [ ] No redundancy detected
- [ ] All examples ≤10 lines

---

## 11. When Setting Up Automation

### Apply These Patterns:
- **PATTERN 7**: Subagent Delegation
- **PATTERN 8**: Hook Automation
- **PATTERN 9**: MCP Server Integration

### Subagent Decision:
**Create subagent IF**:
- Specialized task domain (testing, docs, deployment)
- Different tool permissions needed
- Isolated context beneficial
- Parallel work possible

**Example**: Test agent, docs agent, deployment agent

### Hook Decision:
**Use hooks for**:
- Pre/post edit validation
- Automated linting
- Test running
- Build triggers

**Available hooks**:
- before_edit
- after_edit
- before_session
- after_session

### MCP Integration:
**Use MCP for**:
- External tool access
- API integrations
- Database queries
- File system operations outside repo

### Actions:
1. Evaluate automation needs
2. Choose appropriate mechanism
3. Configure with minimal overhead
4. Test automation triggers

### Validation:
- [ ] Subagents configured if needed
- [ ] Hooks trigger correctly
- [ ] MCP servers accessible
- [ ] Automation doesn't slow workflow

---

## 12. When Migrating from Old Structure

### Apply This Pattern:
- **PATTERN 4**: Migration Sequence

### Migration Steps:

**STEP 1: Measure Current State**
```bash
# Count current tokens
wc -w CLAUDE.md .claude/*.md | awk '{print $1 * 1.3}'
# Note which rules are currently duplicated
# Identify specialized content candidates
```

**STEP 2: Split Content**
```
FOR each section in current docs:
  IF section >500 tokens AND used <50% of time:
    → Create new Skill
  ELSE IF section affects multiple workflows:
    → Move to PROJECT.md
  ELSE IF section critical to all tasks:
    → Keep in CLAUDE.md
```

**STEP 3: Compress Remaining**
- Remove prose, keep bullets
- Remove examples >10 lines
- Remove rationale, keep rules
- Convert "should" to "MUST"

**STEP 4: Validate**
- Check token counts
- Test session startup time
- Verify Skill invocation
- Confirm no duplication

### Actions:
1. Backup current documentation
2. Measure baseline performance
3. Execute migration sequence
4. Validate improvements
5. Iterate if needed

### Validation:
- [ ] Token reduction >40%
- [ ] Startup time <2 seconds
- [ ] All rules preserved
- [ ] Skills invoke correctly
- [ ] No content lost

---

## 13. Before Git Commit

### Apply These Rules:
- **RULE 1-5**: File size limits
- **RULE 10**: No redundancy
- **RULE 12**: Directive language
- **RULE 19**: Git tracking

### Pre-Commit Checklist:
- [ ] CLAUDE.md: 300-400 lines, 3K-5K tokens
- [ ] PROJECT.md: 400-700 lines, 5K-9K tokens
- [ ] RULES.md: 2K-4K tokens (if exists)
- [ ] Total startup: <15K tokens (excluding Skills content)
- [ ] Skills metadata: 30-50 tokens each
- [ ] No content duplication between files
- [ ] All prose converted to bullets
- [ ] All "should/consider" → "MUST/NEVER/ALWAYS"
- [ ] Examples ≤10 lines each
- [ ] Skills have descriptions + triggers + token cost
- [ ] .claude/settings.local.json in .gitignore
- [ ] No sensitive credentials in committed files

### Actions:
1. Run token counting script
2. Scan for redundancy
3. Validate directive language
4. Check .gitignore
5. Review forbidden patterns
6. Verify Skills metadata

### Validation:
Script-based validation recommended:
```bash
#!/bin/bash
# pre-commit-check.sh

# Check CLAUDE.md size
CLAUDE_LINES=$(wc -l < CLAUDE.md)
if [ $CLAUDE_LINES -gt 400 ]; then
  echo "ERROR: CLAUDE.md exceeds 400 lines ($CLAUDE_LINES)"
  exit 1
fi

# Check for "should" (soft language)
if grep -q "should\|consider\|recommend" CLAUDE.md .claude/*.md; then
  echo "WARNING: Soft language detected, use MUST/NEVER/ALWAYS"
fi

# Check for duplicates
# ... additional checks ...

echo "Pre-commit validation passed"
```

---

## 14. When Context Warning Appears

### Apply These Rules:
- **RULE 23**: SESSION REFRESH TRIGGERS
- **RULE 24**: CONTEXT COMPACTION

### Immediate Actions:
1. **Check context percentage**:
   - If >80% → Start new session
   - If 60-80% → Compact context
   - If <60% → Continue (warning may be temporary)

2. **Compact if 60-80%**:
   ```bash
   /compact  # If command available
   
   # Or manually:
   # - Summarize completed work
   # - Remove old tool results
   # - Start fresh with summary
   ```

3. **Refresh if >80%**:
   - Save current state/checkpoint
   - Start new session
   - Reference previous session if needed

### Validation:
- [ ] Context reduced to <60%
- [ ] No active context lost
- [ ] Work can continue smoothly

---

## 15. When Confusion Signals Detected

### Confusion Signals:
- Claude makes incorrect assumptions about project
- References outdated information
- Contradicts previous guidance
- Asks for information already provided
- Suggests patterns that don't match project

### Apply These Rules:
- **RULE 23**: SESSION REFRESH TRIGGERS (start new session)
- **RULE 8**: Check tier placement (may be misconfigured)

### Actions:
1. **Immediate**: Start new session
2. **Review**: Check if critical rules in CLAUDE.md
3. **Validate**: Ensure PROJECT.md has clear architecture
4. **Update**: Add missing critical context
5. **Verify**: Test with similar task

### Validation:
- [ ] New session started
- [ ] Critical rules verified in CLAUDE.md
- [ ] Architecture clear in PROJECT.md
- [ ] Confusion signals resolved

---

## 16. When Adding New Features

### Apply These Rules:
- **RULE 8**: 4-TIER CONTENT DISTRIBUTION
- **RULE 9**: CONTENT PLACEMENT DECISION TREE
- **RULE 14**: SKILL CREATION CRITERIA

### Decision Process:
```
1. Does this feature affect ALL existing tasks?
   YES → Update CLAUDE.md with new constraints/rules
   NO → Continue to 2

2. Does this feature add new workflow/architecture?
   YES → Update PROJECT.md with new patterns
   NO → Continue to 3

3. Is this feature specialized (>500 tokens, <50% usage)?
   YES → Create Skill for feature-specific guidance
   NO → Document in source code comments

4. Does this feature change any critical rules?
   YES → Update CLAUDE.md immediately
   NO → Document in appropriate tier
```

### Actions:
1. Analyze feature impact
2. Apply decision tree
3. Update appropriate documentation tier
4. Validate token budgets not exceeded
5. Add tests/examples if needed

### Validation:
- [ ] Documentation updated in correct tier
- [ ] Critical rules updated if needed
- [ ] Token budgets maintained
- [ ] No duplication created

---

## 17. During Code Review

### Apply These Rules:
- **RULE 8**: Content placement
- **RULE 25-27**: Anti-patterns

### Review Checklist for Documentation Changes:
- [ ] Content in correct tier?
- [ ] No forbidden patterns introduced?
- [ ] Token budgets maintained?
- [ ] Examples compressed (≤10 lines)?
- [ ] Directive language used?
- [ ] No duplication created?
- [ ] Skills metadata correct?
- [ ] Git tracking configured?

### Actions:
1. Review documentation changes
2. Validate against rules
3. Check tier placement
4. Verify no anti-patterns
5. Request changes if needed

### Validation:
- [ ] All checklist items pass
- [ ] Documentation optimized
- [ ] Ready for commit

---

## 18. When Onboarding New Team Members

### Apply These Rules:
- **RULE 6**: Explain loading hierarchy
- **RULE 8**: Explain 4-tier structure
- **RULE 20**: Model selection guidance

### Onboarding Actions:
1. **Show file structure**:
   ```
   CLAUDE.md           → Core rules (read first)
   .claude/PROJECT.md  → Architecture/workflows
   .claude/skills/     → Specialized guidance (on-demand)
   ```

2. **Explain loading**:
   - What's always loaded
   - What loads on-demand
   - Why this matters

3. **Demonstrate workflow**:
   - Session startup
   - Model selection
   - Skill invocation
   - Context management

4. **Share guidelines**:
   - Token budgets
   - Placement decision tree
   - Forbidden patterns
   - Validation checklist

### Validation:
- [ ] Team member understands structure
- [ ] Can identify correct tier for new content
- [ ] Knows when to create Skills
- [ ] Aware of token budgets

---

## QUICK SITUATION LOOKUP

| Situation | Primary Rules | Action |
|-----------|---------------|--------|
| New project | 1, 2, 18, 19 | Create CLAUDE.md, PROJECT.md, configure git |
| New docs | 8, 9, 14 | Use placement decision tree |
| Optimization | 4, 10, 11, 12 | Measure, dedupe, compress, directive language |
| New Skill | 14, 15, 16, 17 | Check criteria, use structure, add metadata |
| Session start | 6, 7, 22 | Understand loading, monitor context |
| Model choice | 20, 21 | Match complexity, extended thinking sparingly |
| Long session | 23, 24 | Monitor, compact at 60%, refresh at 80% |
| Refactor docs | 25, 26, 27 | Check forbidden patterns |
| Files too large | 1, 2, 3, 4, 8 | Extract to Skills, compress |
| Performance | 4, 10, 13, 22, 23 | Measure, eliminate waste, refresh |
| Automation | Pattern 7, 8, 9 | Subagents, hooks, MCP |
| Migration | Pattern 4 | Measure, split, compress, validate |
| Pre-commit | 1-5, 10, 12, 19 | Run checklist |
| Context warning | 23, 24 | Compact or refresh |
| Confusion | 23, 8 | New session, check config |
| New feature | 8, 9, 14 | Placement decision tree |
| Code review | 8, 25-27 | Validate placement, anti-patterns |
| Onboarding | 6, 8, 20 | Explain structure, loading, models |

---

## DOCUMENT METADATA

**Version**: 2.0.1-LLM  
**Format**: Situation-Based Rule Mapping  
**Total Situations**: 18 common scenarios  
**Usage**: Quick lookup for "what rules apply right now"  
**References**: See RULE_INDEX_STANDALONE.md for full rule details
