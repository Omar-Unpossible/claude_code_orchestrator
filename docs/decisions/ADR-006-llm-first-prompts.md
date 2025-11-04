# ADR-006: LLM-First Prompt Engineering Framework

**Status**: Accepted
**Date**: 2025-11-03
**Deciders**: Claude Code Assistant, User
**Phase**: PHASE_6 - Migration & Validation

## Context

The Obra orchestration system uses natural language prompts to communicate with Claude Code CLI and local LLM validation. The original implementation used Jinja2 templates with natural language formatting, which worked but had efficiency concerns:

1. **Token inefficiency**: Natural language prompts are verbose and consume more tokens
2. **Parsing unreliability**: Free-form responses are harder to parse consistently
3. **Validation complexity**: Rule compliance checking requires fragile regex or heuristics
4. **Maintenance burden**: Template changes risk breaking response parsing

We needed a more machine-optimized approach that maintains human readability while improving efficiency and reliability.

## Decision

We will adopt a **hybrid prompt engineering framework** that combines:
- **JSON metadata section** with structured task context, rules, and expectations
- **Natural language instruction section** for clear task description
- **Per-template migration** allowing gradual adoption without breaking existing code

### Key Architectural Changes (PHASE_1-6)

#### PHASE_1: Infrastructure Foundation
- Created `config/prompt_rules.yaml` - 400 lines, 7 domains (code, docs, testing, etc.)
- Created `config/response_schemas.yaml` - 300 lines, 5 response types
- Created `config/complexity_thresholds.yaml` - 200 lines, decomposition heuristics
- Added database models: `PromptRuleViolation`, `ComplexityEstimate`, `ParallelAgentAttempt`

#### PHASE_2: Prompt Rule Engine
- Implemented `PromptRuleEngine` - Loads rules from YAML, applies to prompts
- Implemented `PromptRule` data class - Represents individual rules
- Implemented AST-based code validators - Detect stubs, hardcoded values, missing docstrings

#### PHASE_3: Structured Prompt System
- Implemented `StructuredPromptBuilder` - Generates hybrid prompts (JSON + NL)
- Implemented `StructuredResponseParser` - Parses and validates LLM responses
- Updated `PromptGenerator` for dual-mode support (structured/unstructured)
- Created hybrid prompt templates for all prompt types

#### PHASE_4: Complexity Estimation
- Implemented `TaskComplexityEstimator` - Heuristic + LLM complexity analysis
- Implemented `ComplexityEstimate` data class - Stores complexity metrics
- Parallelization analysis - Identifies independent subtasks

#### PHASE_5: Integration & Orchestration
- Integrated `StructuredResponseParser` into `QualityController`
- Integrated `TaskComplexityEstimator` into `Orchestrator`
- Enhanced quality scoring: 30% schema + 30% completeness + 40% rules

#### PHASE_5B: Claude-Driven Parallelization
- Revised architecture to enforce "only Claude touches code" principle
- Changed `ComplexityEstimator` to provide **suggestions** (not commands)
- Deprecated `ParallelAgentCoordinator` (Obra-level parallelization)
- Claude decides whether to parallelize using Task tool
- See ADR-005 for detailed rationale

#### PHASE_6: Migration & Validation (This ADR)
- Created `ABTestingFramework` for empirical comparison
- Ran A/B tests showing **35.2% token efficiency improvement**
- Migrated validation prompts to structured format (TASK_6.1)
- Migrated task_execution prompts to structured format (TASK_6.4)
- Created `hybrid_prompt_templates.yaml` for per-template configuration

## Alternatives Considered

### Alternative 1: Pure JSON Prompts
**Pros**:
- Maximum machine optimization
- Easiest to parse
- Most token-efficient

**Cons**:
- Poor human readability
- Harder to debug
- Less flexible for complex instructions
- Requires significant prompt changes

**Decision**: Rejected - Loss of human readability too severe

### Alternative 2: Pure Natural Language
**Pros**:
- Maximum human readability
- Flexible and expressive
- Easy to modify

**Cons**:
- Token inefficient (~50% more tokens)
- Parsing unreliable
- Hard to validate programmatically

**Decision**: Rejected - Efficiency and reliability concerns

### Alternative 3: Hybrid Format (Selected)
**Pros**:
- Balances machine optimization with human readability
- 35% token efficiency improvement (validated)
- Reliable parsing with schema validation
- Gradual migration path
- Backward compatible

**Cons**:
- More complex implementation
- Requires maintaining two code paths during migration

**Decision**: **ACCEPTED** - Best balance of tradeoffs

## Implementation Details

### Hybrid Prompt Format

```
<METADATA>
{
  "prompt_type": "validation",
  "task_id": 123,
  "rules": [
    {
      "id": "CODE_001",
      "name": "NO_STUBS",
      "severity": "critical",
      "description": "Never generate stub functions"
    }
  ],
  "expectations": {
    "detailed_violations": true,
    "location_info": true
  }
}
</METADATA>

<INSTRUCTION>
Validate the following code against the specified rules:

[code here]

For each violation, provide:
1. Rule ID
2. Location (file, line)
3. Fix suggestion
</INSTRUCTION>
```

### Expected Response Format

```
<METADATA>
{
  "is_valid": false,
  "quality_score": 45,
  "violations": [
    {
      "rule_id": "CODE_001",
      "file": "auth.py",
      "line": 2,
      "severity": "critical",
      "message": "Function contains only TODO comment",
      "suggestion": "Implement complete login logic"
    }
  ]
}
</METADATA>

<CONTENT>
[Natural language explanation]
</CONTENT>
```

### Per-Template Migration Configuration

**File**: `config/hybrid_prompt_templates.yaml`

```yaml
global:
  template_modes:
    validation: "structured"       # Migrated in TASK_6.1
    task_execution: "structured"   # Migrated in TASK_6.4
    error_analysis: "unstructured" # Future
    decision: "unstructured"       # Future
    planning: "unstructured"       # Future
```

### PromptGenerator Changes

```python
def _is_structured_mode(self, template_name: Optional[str] = None) -> bool:
    """Check if structured mode enabled for template."""
    if template_name and self.template_modes:
        template_mode = self.template_modes.get(template_name, 'unstructured')
        return template_mode == 'structured'
    return self._structured_mode

def generate_validation_prompt(self, task, work_output, context) -> str:
    """Generate validation prompt (auto-switches to structured if configured)."""
    if self._is_structured_mode(template_name='validation'):
        # Use StructuredPromptBuilder
        return self._structured_builder.build_validation_prompt(
            code=work_output,
            rules=context.get('rules', [])
        )
    else:
        # Use Jinja2 templates
        return self.generate_prompt('validation', variables)
```

## Consequences

### Positive

1. **Token Efficiency**: 35.2% reduction in tokens (validated via A/B testing)
   - Structured: 733 tokens average
   - Unstructured: 1130 tokens average
   - Statistically significant (p < 0.001)

2. **Latency Improvement**: 22.6% faster responses (validated)
   - Structured: 1910 ms average
   - Unstructured: 2469 ms average
   - Statistically significant (p < 0.001)

3. **Parsing Reliability**: 100% success rate with schema validation
   - JSON extraction always succeeds
   - Field validation catches errors early
   - Type safety with schema checking

4. **Maintainability**: Clear separation of concerns
   - Metadata changes don't affect instructions
   - Response schema changes isolated
   - Rule definitions centralized in YAML

5. **Gradual Migration**: No breaking changes
   - Templates migrate one at a time
   - Both modes supported simultaneously
   - Can rollback individual templates if needed

### Negative

1. **Increased Complexity**: Two code paths to maintain
   - StructuredPromptBuilder for new templates
   - Jinja2 templates for legacy
   - Configuration complexity with template modes

2. **Learning Curve**: Developers must understand hybrid format
   - More complex than pure Jinja2
   - Need to maintain response schemas
   - ADR-006 and documentation mitigate this

3. **Migration Effort**: Requires updating all templates
   - ~5 templates to migrate (2 done, 3 remaining)
   - Testing required for each migration
   - Estimated 8-10 hours remaining

### Neutral

1. **Quality**: No significant difference in validation quality
   - Structured: 0.61 average quality score
   - Unstructured: 0.60 average quality score
   - Both detect same number of violations

## Metrics & Validation

### A/B Testing Results (TASK_6.3)

**Test**: 25 validation prompts, structured vs unstructured

| Metric | Structured | Unstructured | Improvement | Significant? |
|--------|-----------|--------------|-------------|--------------|
| Tokens | 733 avg | 1130 avg | **35.2%** | ✅ p < 0.001 |
| Latency | 1910 ms | 2469 ms | **22.6%** | ✅ p < 0.001 |
| Success Rate | 100% | 100% | 0% | N/A |
| Quality Score | 0.61 | 0.60 | 1.7% | ❌ p > 0.05 |
| Rule Violations | 1.4 | 1.4 | 0% | N/A |

**Conclusion**: Structured format provides significant efficiency gains without sacrificing quality.

### Migration Status

| Template | Status | Date | Notes |
|----------|--------|------|-------|
| validation | ✅ Migrated | 2025-11-03 | TASK_6.1 |
| task_execution | ✅ Migrated | 2025-11-03 | TASK_6.4 |
| error_analysis | ⏳ Pending | - | Future |
| decision | ⏳ Pending | - | Future |
| planning | ⏳ Pending | - | Future |

## Future Considerations

1. **Full Migration**: Complete migration of all 5 templates
   - Estimated effort: 4-6 hours
   - Same A/B testing methodology
   - Expected similar efficiency gains

2. **Template Versioning**: Support multiple schema versions
   - Allow gradual schema evolution
   - Backward compatibility for old responses

3. **Dynamic Schema Generation**: Generate schemas from type hints
   - Reduce duplication between code and config
   - Auto-generate response validators

4. **Performance Monitoring**: Track efficiency in production
   - Compare actual vs predicted token savings
   - Monitor parsing success rates
   - Adjust thresholds based on real data

## References

- **Design Document**: `docs/design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md`
- **Implementation Plan**: `docs/development/LLM_FIRST_IMPLEMENTATION_PLAN.yaml`
- **PHASE_3 Summary**: `/tmp/PHASE_3_COMPLETION_SUMMARY.md`
- **PHASE_6 Summary**: `/tmp/PHASE_6_COMPLETION_SUMMARY.md` (to be created)
- **A/B Test Results**: `evaluation_results/ab_test_validation_prompts.json`
- **ADR-005**: `docs/decisions/ADR-005-claude-driven-parallelization.md`

## Approval

**Status**: Accepted and Implemented
**Phase**: PHASE_6 Complete
**Next Steps**: Document in ARCHITECTURE.md, create PROMPT_ENGINEERING_GUIDE.md
