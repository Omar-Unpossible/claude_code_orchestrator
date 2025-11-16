# Test Fixtures

Reusable test fixtures and utilities for Obra testing infrastructure.

## Files

### `nl_variation_generator.py`

**NL Variation Generator** - Generates semantic variations of natural language commands for stress testing.

**Purpose**: Validate NL parsing robustness by testing 100+ variations per command with different phrasings, synonyms, case, typos, and verbosity.

**Usage**:
```python
from tests.fixtures.nl_variation_generator import NLVariationGenerator

# Create generator with real LLM
generator = NLVariationGenerator(llm_plugin)

# Generate 100 variations
variations = generator.generate_variations(
    "create epic for user authentication",
    count=100
)

# Generate specific categories only
variations = generator.generate_variations(
    "create epic for auth",
    count=50,
    categories=['synonyms', 'typos']
)

# Validate semantic equivalence
result = generator.validate_variation(
    base_command="create epic for auth",
    variation="add an epic for authentication"
)
print(result['is_valid'])  # True
```

**Variation Categories**:
1. **Synonyms** (20%) - Replace verbs (create→add, make, build)
2. **Phrasings** (25%) - Rephrase structure (create X → I need X)
3. **Case** (15%) - Vary capitalization (lowercase, UPPERCASE, Title Case)
4. **Typos** (15%) - Inject misspellings (create→crete, epic→epik)
5. **Verbose** (25%) - Add politeness (please, can you, I would like)

### `generate_failure_report.py`

**Failure Analysis Tool** - Analyzes test failures and generates comprehensive reports.

**Purpose**: Categorize failures by root cause and provide actionable recommendations.

**Usage**:
```bash
# Generate report from pytest log
python tests/fixtures/generate_failure_report.py \
    --test-log tests/test_run.log \
    --output tests/reports/nl_variation_failures.md

# Also output JSON stats
python tests/fixtures/generate_failure_report.py \
    --test-log tests/test_run.log \
    --output tests/reports/nl_variation_failures.md \
    --json
```

**Programmatic Usage**:
```python
from tests.fixtures.generate_failure_report import FailureAnalyzer

analyzer = FailureAnalyzer()
analyzer.add_failure(
    test_name="test_create_epic_variations",
    variation="crete epic for auth",
    error="Low confidence: 0.45"
)

# Generate report
report = analyzer.generate_report()
print(report)

# Get stats
stats = analyzer.get_stats()
print(f"Total failures: {stats['total_failures']}")
```

**Failure Categories**:
- Low Confidence
- Wrong Operation Type
- Missing Entity Type
- Identifier Extraction Failure
- Typo Tolerance
- Unknown

## Integration with Pytest

All fixtures are automatically available in pytest via `conftest.py`:

```python
def test_variations(variation_generator, real_nl_processor_with_llm):
    """Variation generator is auto-injected."""
    variations = variation_generator.generate_variations("create epic", count=10)
    # ... test variations
```

## See Also

- **Phase 3 Tests**: `tests/integration/test_nl_variations.py`
- **Performance Benchmarks**: `tests/performance/test_nl_performance.py`
- **Phase 3 Documentation**: See session summary for complete guide
