# [Epic/Story ID] Machine-Optimized Implementation Spec

**Target**: Claude Code LLM (autonomous execution)
**Format**: Directive commands, validation steps

## Validation Scripts

CHECK before starting:
```bash
# Verification commands
ls [required-file]
grep [pattern] [file]
```

## Phase 1: [Name]

STEP 1.1: [Action]
```bash
# Exact command
```

VALIDATE:
```bash
# Check command
[command] | grep [expected-output]
```

IF validation FAILS → STOP, report error

STEP 1.2: [Next action]
```bash
# Exact command
```

VALIDATE:
```bash
# Check command
```

## Phase 2: [Name]

STEP 2.1: [Action]
...

## Phase 3: [Name]

STEP 3.1: [Action]
...

## Error Handling

IF [condition]:
1. STOP immediately
2. REPORT: [what to show]
3. WAIT for intervention

IF [other-condition]:
1. [Remediation step]
2. RETRY from STEP [X.Y]
