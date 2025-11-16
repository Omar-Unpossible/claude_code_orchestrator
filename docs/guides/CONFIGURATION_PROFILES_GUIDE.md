# Configuration Profiles Guide

**Obra v1.2+ (M9)**

## Overview

Configuration profiles provide pre-configured settings optimized for different project types. Instead of manually configuring every option, you can select a profile that matches your project and customize only what you need.

**Benefits:**
- **Fast setup** - Get started in seconds with sensible defaults
- **Best practices** - Profiles embody proven configurations for each project type
- **Easy customization** - Override specific settings without losing profile defaults
- **Consistency** - Standardize configuration across similar projects

## Available Profiles

Obra includes 6 built-in profiles:

| Profile | Use Case | Key Features |
|---------|----------|--------------|
| `python_project` | Python development | pytest integration, Python-specific prompts, strict linting |
| `web_app` | Web applications | Node.js/React setup, shorter timeouts, rapid iteration |
| `ml_project` | Machine learning | Extended timeouts, GPU-aware, notebook support |
| `microservice` | Microservices | Docker integration, API-focused, dependency tracking |
| `minimal` | Minimal overhead | Fast, lean, minimal validation, quick tasks |
| `production` | Production deployment | High quality thresholds, extensive validation, git auto-commit |

## Profile Configuration

### Profile Location

Profiles are stored in `config/profiles/`:

```
config/
├── default_config.yaml      # Base configuration
├── config.yaml              # User overrides
└── profiles/
    ├── python_project.yaml
    ├── web_app.yaml
    ├── ml_project.yaml
    ├── microservice.yaml
    ├── minimal.yaml
    └── production.yaml
```

### Profile Inheritance

Profiles **extend** the default configuration:

```
┌─────────────────────┐
│ default_config.yaml │  ← Base settings
└──────────┬──────────┘
           │ extends
┌──────────▼──────────┐
│  Profile YAML       │  ← Profile-specific overrides
└──────────┬──────────┘
           │ extends
┌──────────▼──────────┐
│  config.yaml        │  ← User-specific overrides
└──────────┬──────────┘
           │ extends
┌──────────▼──────────┐
│  CLI Arguments      │  ← Runtime overrides (highest priority)
└─────────────────────┘
```

## Using Profiles

### Basic Usage

**Via CLI:**
```bash
# Create project with profile
obra project create "My Python App" --profile python_project

# Execute task with profile
obra --profile python_project task execute 1

# Interactive mode with profile
obra --profile ml_project interactive
```

**Via Configuration:**
```yaml
# config.yaml
profiles:
  default_profile: python_project  # Use profile by default
```

**Via Environment Variable:**
```bash
export OBRA_PROFILE=python_project
obra task execute 1
```

### Overriding Profile Settings

**CLI Override:**
```bash
# Use profile but override specific settings
obra --profile python_project \
     --set agent.response_timeout=3600 \
     --set retry.max_retries=5 \
     task execute 1

# Multiple overrides
obra --profile production \
     --set git.enabled=false \
     --set orchestration.breakpoints.confidence_threshold=0.85 \
     task execute 1
```

**Config Override:**
```yaml
# config.yaml
profiles:
  default_profile: python_project

# Override specific profile settings
agent:
  response_timeout: 3600  # Override profile's timeout

git:
  enabled: false  # Disable git even if profile enables it
```

## Profile Descriptions

### 1. Python Project (`python_project.yaml`)

**Optimized for:** Python development with pytest, type hints, and linting

**Key Settings:**
```yaml
agent:
  type: local
  response_timeout: 3600  # 1 hour (moderate tasks)

llm:
  temperature: 0.1  # Low temperature for deterministic output

orchestration:
  breakpoints:
    confidence_threshold: 0.75
  quality:
    min_quality_score: 0.80

git:
  enabled: true
  auto_commit: true
  commit_strategy: per_task

max_turns:
  default: 12
  by_task_type:
    testing: 10  # Python tests usually quick
    code_generation: 15  # Allow more iterations
```

**Use When:**
- Developing Python libraries or applications
- Using pytest for testing
- Following Python best practices (type hints, linting)
- Want moderate quality thresholds

**Example:**
```bash
obra --profile python_project project create "FastAPI Backend"
```

---

### 2. Web App (`web_app.yaml`)

**Optimized for:** Web development with Node.js, React, rapid iteration

**Key Settings:**
```yaml
agent:
  response_timeout: 2400  # 40 minutes (shorter for quick iteration)

orchestration:
  breakpoints:
    confidence_threshold: 0.70  # Lower threshold for rapid development
  quality:
    min_quality_score: 0.75

max_turns:
  default: 10
  by_task_type:
    code_generation: 12
    refactoring: 8  # Web refactoring usually straightforward

git:
  branch_per_task: true  # Feature branches
  create_pr: false  # Manual PR review common in web dev
```

**Use When:**
- Building web applications (frontend or backend)
- Using JavaScript/TypeScript, Node.js, React, Vue, etc.
- Rapid prototyping and iteration
- Shorter task cycles

**Example:**
```bash
obra --profile web_app project create "E-commerce Dashboard"
```

---

### 3. Machine Learning Project (`ml_project.yaml`)

**Optimized for:** ML/AI development with long-running experiments

**Key Settings:**
```yaml
agent:
  response_timeout: 14400  # 4 hours (long-running experiments)

orchestration:
  breakpoints:
    confidence_threshold: 0.80  # Higher threshold for critical ML code
  quality:
    min_quality_score: 0.85  # High quality for reproducibility

max_turns:
  default: 20  # ML tasks often complex
  by_task_type:
    code_generation: 25
    testing: 15
    debugging: 30  # ML debugging is hard

retry:
  max_retries: 5  # ML tasks may hit GPU/memory limits

git:
  enabled: true
  auto_commit: true
  commit_strategy: per_task  # Track experiments
```

**Use When:**
- Training machine learning models
- Data science workflows
- Jupyter notebook development
- GPU-intensive tasks
- Long-running experiments

**Example:**
```bash
obra --profile ml_project project create "Image Classification Model"
```

---

### 4. Microservice (`microservice.yaml`)

**Optimized for:** Microservice architectures with Docker, APIs

**Key Settings:**
```yaml
agent:
  type: local
  response_timeout: 3600

orchestration:
  breakpoints:
    confidence_threshold: 0.80
  quality:
    min_quality_score: 0.85  # High quality for production services

task_dependencies:
  enabled: true  # Microservices often have dependencies
  max_depth: 10
  cascade_failures: true

git:
  enabled: true
  branch_per_task: true  # Feature branches
  create_pr: true  # Automated PR workflow

max_turns:
  by_task_type:
    api_integration: 15  # API work needs iterations
    testing: 12
```

**Use When:**
- Building microservices
- Working with Docker/Kubernetes
- API-first development
- Service dependencies
- Production-grade code

**Example:**
```bash
obra --profile microservice project create "User Authentication Service"
```

---

### 5. Minimal (`minimal.yaml`)

**Optimized for:** Quick tasks, prototyping, minimal overhead

**Key Settings:**
```yaml
agent:
  response_timeout: 1800  # 30 minutes (short tasks)

orchestration:
  breakpoints:
    confidence_threshold: 0.60  # Low threshold (fast feedback)
  quality:
    min_quality_score: 0.70  # Lower quality bar

max_turns:
  default: 5  # Few iterations
  by_task_type:
    code_generation: 8
    testing: 3

retry:
  enabled: false  # No retries (fail fast)

git:
  enabled: false  # No git automation
  auto_commit: false
```

**Use When:**
- Quick experiments
- Throwaway prototypes
- Learning/exploration
- Scripts and one-offs
- Speed over quality

**Example:**
```bash
obra --profile minimal task create "Test API endpoint" --execute
```

---

### 6. Production (`production.yaml`)

**Optimized for:** Production-ready code with maximum quality

**Key Settings:**
```yaml
agent:
  response_timeout: 7200  # 2 hours (thorough work)

orchestration:
  breakpoints:
    confidence_threshold: 0.85  # High confidence required
  quality:
    min_quality_score: 0.90  # Maximum quality

max_turns:
  default: 15
  by_task_type:
    code_generation: 20
    testing: 15
    refactoring: 18

retry:
  enabled: true
  max_retries: 5

git:
  enabled: true
  auto_commit: true
  commit_strategy: per_task
  branch_per_task: true
  create_pr: true  # Automated PR workflow

task_dependencies:
  enabled: true
  cascade_failures: true  # Block dependents on failure
```

**Use When:**
- Production deployments
- Mission-critical code
- High-quality requirements
- Comprehensive testing needed
- Strict validation

**Example:**
```bash
obra --profile production project create "Payment Processing System"
```

## Creating Custom Profiles

### Step 1: Copy Base Profile

```bash
cd config/profiles/
cp python_project.yaml my_custom_profile.yaml
```

### Step 2: Edit Profile

```yaml
# my_custom_profile.yaml
# Custom profile for Django projects

# Extend from python_project
_extends: python_project  # Optional: base profile to extend

# Override settings
agent:
  response_timeout: 5400  # 1.5 hours

orchestration:
  quality:
    min_quality_score: 0.82  # Custom threshold

max_turns:
  by_task_type:
    code_generation: 14
    database_migration: 20  # Django migrations can be complex

# Add custom settings
custom:
  framework: django
  database: postgresql
```

### Step 3: Use Custom Profile

```bash
obra --profile my_custom_profile project create "Django Blog"
```

## Profile Selection Strategy

### Decision Tree

```
Start
  │
  ├─ Quick experiment? ────────────> minimal
  │
  ├─ Production deployment? ───────> production
  │
  ├─ Python project?
  │   ├─ ML/Data Science? ─────────> ml_project
  │   └─ Standard Python ───────────> python_project
  │
  ├─ Web application?
  │   ├─ Microservice? ────────────> microservice
  │   └─ Full-stack app ────────────> web_app
  │
  └─ Other ─────────────────────────> python_project (general purpose)
```

### Comparison Matrix

| Feature | minimal | python_project | web_app | ml_project | microservice | production |
|---------|---------|----------------|---------|------------|--------------|------------|
| **Quality Threshold** | Low (0.70) | Medium (0.80) | Medium (0.75) | High (0.85) | High (0.85) | Very High (0.90) |
| **Response Timeout** | 30 min | 1 hour | 40 min | 4 hours | 1 hour | 2 hours |
| **Max Turns** | 5 | 12 | 10 | 20 | 12 | 15 |
| **Retry Logic** | ❌ Disabled | ✅ Enabled | ✅ Enabled | ✅ Enabled (5×) | ✅ Enabled | ✅ Enabled (5×) |
| **Git Auto-Commit** | ❌ Disabled | ✅ Enabled | ✅ Enabled | ✅ Enabled | ✅ Enabled | ✅ Enabled |
| **Branch Per Task** | ❌ No | ❌ No | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| **Auto PR Creation** | ❌ No | ❌ No | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Task Dependencies** | ❌ Disabled | ❌ Disabled | ❌ Disabled | ❌ Disabled | ✅ Enabled | ✅ Enabled |
| **Best For** | Prototypes | Python libs | Web apps | ML/AI | Microservices | Production |

---

## Max_Turns Configuration (v1.8.1 Updates)

**Important Changes in v1.8.1**: Default max_turns values have been significantly increased based on production testing.

### New Defaults (v1.8.1)

```yaml
max_turns:
  # Fallback value if adaptive calculation fails
  default: 50  # Increased from 10 (5× increase)

  # Task-type specific overrides
  by_task_type:
    validation: 5
    code_generation: 12
    refactoring: 15
    debugging: 20
    error_analysis: 8
    planning: 5
    documentation: 3
    testing: 8

  # NEW: Obra task type specific limits
  by_obra_task_type:
    TASK: 30        # Simple technical tasks
    STORY: 50       # User stories (default)
    EPIC: 100       # Large epics (batch execution)
    SUBTASK: 20     # Granular subtasks

  # Safety bounds
  min: 3          # Never less than 3 turns
  max: 150        # Increased from 30 (5× increase)

  # Retry behavior when max_turns limit hit
  auto_retry: true
  max_retries: 1           # Number of retry attempts
  retry_multiplier: 3      # Increased from 2 (50% increase)
```

### How Max_Turns is Calculated

**Priority Order** (highest to lowest):
1. **obra_task_type** - Based on TaskType enum (TASK, STORY, EPIC, SUBTASK)
2. **task_type** - Based on specific work type (validation, code_generation, etc.)
3. **adaptive** - Based on estimated complexity (if enabled)
4. **default** - Fallback value (50)

**Example Calculation**:
```python
# Story with code_generation task_type
Task type: STORY
Work type: code_generation
Result: max_turns = 50  # Uses STORY from by_obra_task_type (higher priority)

# Task with debugging work type
Task type: TASK
Work type: debugging
Result: max_turns = 30  # Uses TASK from by_obra_task_type
```

### Retry Behavior

When a task hits the max_turns limit:

1. **First Attempt**: Uses calculated max_turns (e.g., 50 for STORY)
2. **Retry Attempt**: Multiplies by retry_multiplier (e.g., 50 × 3 = 150)
3. **Safety Limit**: Never exceeds max (150)

**Example Flow**:
```
Story task execution:
- Attempt 1: max_turns = 50
- If exceeded: Retry with max_turns = 150 (50 × 3)
- If still exceeded: Deliverable assessment runs
- Outcome: SUCCESS_WITH_LIMITS or PARTIAL (not FAILED if deliverables exist)
```

### Deliverable-Based Success (v1.8.1)

**New Feature**: When max_turns is exhausted, Obra assesses deliverables before marking task as FAILED.

**Assessment Criteria**:
- Files created/modified during task execution
- Syntax validation (Python, JSON, YAML)
- Quality heuristics (file size, content patterns)
- Overall quality score (0.0-1.0)

**Possible Outcomes**:
- **SUCCESS_WITH_LIMITS** (quality ≥ 0.7): Working code delivered, hit turn limit
- **PARTIAL** (quality ≥ 0.5): Incomplete but valuable work
- **FAILED** (quality < 0.5 or no files): Legitimate failure

**Example**:
```bash
# Task hits max_turns=150 but creates 7 valid Python files
# Old behavior: FAILED
# New behavior: SUCCESS_WITH_LIMITS (quality_score=0.82)
```

### Migration Guide for Custom Profiles

If you have **custom max_turns settings** in your profiles:

**Action Required**: Review and potentially increase your limits

**Recommended Increases**:
- **default**: Increase by 5× (e.g., 10 → 50)
- **max**: Increase by 5× (e.g., 30 → 150)
- **retry_multiplier**: Increase to 3 (from 2)

**Example Migration**:
```yaml
# Before (v1.8.0)
max_turns:
  default: 12
  max: 30
  retry_multiplier: 2

# After (v1.8.1)
max_turns:
  default: 60      # 12 × 5
  max: 150         # 30 × 5
  retry_multiplier: 3
```

**Backward Compatibility**: All changes are backward compatible. Existing configurations will continue to work, but may benefit from increased limits.

---

## Advanced Usage

### Combining Profiles with Overrides

**Scenario:** Use `python_project` profile but with production-level quality

```bash
obra --profile python_project \
     --set orchestration.quality.min_quality_score=0.90 \
     --set orchestration.breakpoints.confidence_threshold=0.85 \
     --set git.create_pr=true \
     task execute 1
```

### Profile Switching Mid-Project

```bash
# Development phase: Use web_app profile
obra --profile web_app task create "Build user dashboard" --execute

# Testing phase: Use production profile for high quality
obra --profile production task create "Add integration tests" --execute
```

### Environment-Specific Profiles

```bash
# Development
export OBRA_PROFILE=web_app
obra task execute 1

# Staging
export OBRA_PROFILE=microservice
obra task execute 1

# Production
export OBRA_PROFILE=production
obra task execute 1
```

## Troubleshooting

### Profile Not Found

**Error:**
```
ProfileNotFoundError: Profile 'my_profile' not found in config/profiles/
```

**Solution:**
```bash
# List available profiles
ls config/profiles/

# Create missing profile
cp config/profiles/python_project.yaml config/profiles/my_profile.yaml
```

### Profile Conflicts

**Problem:** Settings from profile conflict with config.yaml

**Solution:** Check inheritance order:
1. CLI arguments (highest priority)
2. Environment variables
3. config.yaml
4. Profile YAML
5. default_config.yaml (lowest priority)

**Debug:**
```bash
# Show effective configuration
obra --profile python_project config show

# Show configuration with overrides
obra --profile python_project --set agent.timeout=5000 config show
```

### Profile Performance Issues

**Problem:** Profile settings cause timeouts

**Solution:** Override response_timeout:
```bash
# Increase timeout for complex tasks
obra --profile python_project --set agent.response_timeout=7200 task execute 1

# Or modify profile permanently
vim config/profiles/python_project.yaml
# Change: response_timeout: 7200
```

## Best Practices

### 1. Choose Profile by Project Type
- Don't overthink it - profiles are starting points
- Can always override specific settings
- Start with closest match, customize as needed

### 2. Create Custom Profiles for Teams
- Standardize team workflows
- Share profiles via git
- Document profile purpose in comments

### 3. Use Overrides for Experimentation
- Don't modify profiles for one-off changes
- Use `--set` for temporary adjustments
- Create new profile if changes are permanent

### 4. Monitor Performance Metrics
- Track quality scores per profile
- Adjust thresholds based on results
- Log profile usage for analysis

### 5. Document Profile Rationale
```yaml
# my_django_profile.yaml
# Purpose: Django projects with Celery and PostgreSQL
# Maintainer: Team Backend
# Last Updated: 2025-11-04

# Settings rationale:
# - Extended timeout: Celery tasks can take time
# - High quality: Production database code
# - Git auto-commit: Track migrations carefully
```

## Examples

### Example 1: Python Library Development

```bash
# Create project with python_project profile
obra --profile python_project project create "awesome-lib"

# Create tasks
obra task create "Implement core API" --project 1
obra task create "Write comprehensive tests" --project 1 --depends-on 1
obra task create "Add type hints and docstrings" --project 1 --depends-on 2

# Execute milestone
obra milestone execute 1
```

### Example 2: ML Experiment with High Quality

```bash
# Use ml_project profile with production-level quality
obra --profile ml_project \
     --set orchestration.quality.min_quality_score=0.90 \
     project create "Text Classification Model"

# Long-running task with extended timeout
obra --profile ml_project \
     --set agent.response_timeout=21600 \  # 6 hours
     task create "Train BERT model" --execute
```

### Example 3: Rapid Web Prototyping

```bash
# Minimal profile for fast iteration
obra --profile minimal project create "Landing Page Prototype"

# Quick tasks
obra task create "Create React components" --execute
obra task create "Add basic styling" --execute
obra task create "Connect to mock API" --execute
```

### Example 4: Microservice with Dependencies

```bash
# Microservice profile with dependencies enabled
obra --profile microservice project create "User Service"

# Create dependent tasks
obra task create "Design service interface" --id 1
obra task create "Implement gRPC endpoints" --depends-on 1
obra task create "Add authentication middleware" --depends-on 2
obra task create "Write integration tests" --depends-on 2,3
obra task create "Dockerize service" --depends-on 4

# Execute in dependency order
obra milestone execute 1
```

## Profile Configuration Reference

### Full Profile Schema

```yaml
# Profile template (all sections optional)

# Agent configuration
agent:
  type: local  # or ssh
  response_timeout: 3600  # seconds
  local:
    working_directory: ./workspace

# LLM configuration
llm:
  provider: ollama
  model: qwen2.5-coder:32b
  base_url: http://localhost:11434
  temperature: 0.1

# Orchestration settings
orchestration:
  breakpoints:
    confidence_threshold: 0.75
    on_error: true
  quality:
    min_quality_score: 0.80
    validation_required: true
  decision:
    high_confidence: 0.85
    medium_confidence: 0.65

# Max turns per task type
max_turns:
  default: 12
  auto_retry: true
  max_retries: 1
  retry_multiplier: 2
  by_task_type:
    validation: 5
    code_generation: 12
    refactoring: 15
    debugging: 20
    error_analysis: 8
    planning: 5
    documentation: 3
    testing: 8

# Context window management
context_window:
  limit: 200000
  thresholds:
    warning: 0.70
    refresh: 0.80
    critical: 0.95

# Retry logic (M9)
retry:
  enabled: true
  max_retries: 3
  base_delay: 1.0
  max_delay: 60.0
  backoff_factor: 2.0
  jitter: true

# Task dependencies (M9)
task_dependencies:
  enabled: false
  max_depth: 10
  allow_cycles: false
  cascade_failures: true

# Git integration (M9)
git:
  enabled: false
  auto_commit: false
  commit_strategy: per_task
  branch_per_task: false
  branch_prefix: "obra/task-"
  create_pr: false

# Custom metadata
custom:
  profile_name: "My Custom Profile"
  profile_version: "1.0"
  description: "Profile for ..."
```

## Related Documentation

- [M9 Implementation Plan](../development/M9_IMPLEMENTATION_PLAN.md) - Full M9 roadmap
- [QUICK_START.md](../../QUICK_START.md) - Getting started guide
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - System architecture
- [Session Management Guide](SESSION_MANAGEMENT_GUIDE.md) - Context window and max turns

---

**Last Updated:** 2025-11-04
**Obra Version:** v1.2 (M9)
**Status:** Phase 1 - Documentation Complete
