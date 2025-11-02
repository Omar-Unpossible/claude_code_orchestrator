# Obra Technical Design Document
**Enterprise AI Orchestration Platform - Technical Specification**

## Terminology
- **VD (Virtual Developer):** Local LLM orchestration layer (Obra product itself)
- **rAI (Remote AI):** External LLM APIs (Claude, GPT-4, Gemini, etc.)
- **Agent:** Specialized VD instance or context for specific tasks
- **Orchestration Loop:** Complete cycle from intent → generation → validation → testing → integration
- **Context Window:** Maximum token capacity for VD or rAI model
- **Checkpoint:** Saved state snapshot enabling rollback and recovery
- **Task Graph:** Directed acyclic graph (DAG) of tasks with dependencies
- **Escalation Level:** Progressive use of more capable/expensive models when tasks fail
- **Validation Score:** 0-100 metric indicating code quality from VD analysis
- **Refinement Loop:** Iterative improvement cycle when validation fails

---

## Feature Priority Framework
- **P0 (MVP - Alpha Program):** Must-have for first customer deployments (Months 1-6)
- **P1 (Beta - Months 7-12):** Needed for paid launch and scale
- **P2 (Scale - Year 2):** Advanced features for enterprise maturity
- **P3 (Future - Year 3+):** Innovation and market differentiation

**Implementation Philosophy:** Build P0 features to 90% quality, iterate based on alpha feedback. Avoid feature creep—defer P1+ features until P0 proves value.

---

## 1. CORE ORCHESTRATION LAYER

### 1.1 Task Delegation & Routing **[P0]**
**Description:** Intelligent decision engine for optimal VD vs rAI task allocation

#### Key Capabilities:

**Task Analysis Engine:**
- **Complexity scoring algorithm:**
  - Token estimation: Count required context + expected output
  - Dependency analysis: Identify file relationships, imports, type hierarchies
  - Historical data: Compare to similar past tasks
  - Risk assessment: New vs familiar patterns, novel vs routine operations
- **Task classification:**
  - **Simple validation** (VD only): Syntax checking, linting, format compliance
  - **Pattern matching** (VD only): Compare against known codebase patterns
  - **Code generation** (rAI + VD): Remote generation with local validation
  - **Complex reasoning** (rAI only): Novel architecture decisions, creative problem-solving
  - **Hybrid workflows:** VD orchestrates multiple rAI calls with intermediate validation

**Routing Decision Framework:**
- **Cost threshold rules:**
  - Tasks <1k tokens estimated → VD first, fallback to rAI
  - Tasks 1k-10k tokens → Direct to rAI with VD validation
  - Tasks >10k tokens → Chunk and distribute across multiple calls
- **Quality requirements:**
  - Critical path code → Use premium rAI (GPT-4 Turbo, Claude Opus)
  - Test code → Standard rAI (GPT-4, Claude Sonnet)
  - Documentation → VD or basic rAI (GPT-3.5 Turbo)
- **Latency considerations:**
  - Blocking user → Prioritize fast response (local VD or cached rAI)
  - Background tasks → Optimize for cost (batch, use slower models)
- **Context availability:**
  - Full context fits in window → Single rAI call
  - Context exceeds window → VD manages hierarchical decomposition

**Performance Tracking:**
- **Routing metrics dashboard:**
  - Success rate by routing decision (% of tasks that didn't require escalation)
  - Cost efficiency: Actual cost vs estimated cost
  - Quality score: VD validation pass rate per routing type
  - Latency: Average response time by routing path
- **ML-based optimization (P1):**
  - Train lightweight classifier on historical routing decisions
  - Features: task description embeddings, project metadata, past outcomes
  - Predict optimal routing with confidence score
  - Fall back to rules-based routing if confidence <70%
  - Continuous learning: Update model weekly based on new data

**Implementation Details:**
```python
# Production-ready routing decision with circuit breaker pattern
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class Route(Enum):
    VD_ONLY = "vd_only"
    RAI_WITH_VD_VALIDATION = "rai_with_vd"
    VD_CHUNKED_RAI = "vd_chunked_rai"
    CACHED = "cached"
    ESCALATE = "escalate"

class CircuitBreaker:
    """Prevents calling failing rAI providers repeatedly"""
    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = {}
        self.threshold = failure_threshold
        self.timeout = timeout

    def is_open(self, provider: str) -> bool:
        """Check if circuit is open (too many failures)"""
        if provider not in self.failures:
            return False
        count, last_failure = self.failures[provider]
        if time.time() - last_failure > self.timeout:
            # Reset after timeout
            del self.failures[provider]
            return False
        return count >= self.threshold

    def record_failure(self, provider: str):
        if provider in self.failures:
            count, _ = self.failures[provider]
            self.failures[provider] = (count + 1, time.time())
        else:
            self.failures[provider] = (1, time.time())

circuit_breaker = CircuitBreaker()

def route_task(task, project_context, budget_constraints) -> tuple[Route, Optional[str]]:
    """
    Determine optimal routing for task execution.

    Returns:
        (route, provider): Route decision and rAI provider if applicable
    """
    try:
        # Step 1: Analyze task
        complexity_score = estimate_complexity(task)
        token_estimate = estimate_tokens(task, project_context)
        task_type = classify_task_type(task)

        logger.info(f"Routing task {task.id}: complexity={complexity_score}, "
                   f"tokens={token_estimate}, type={task_type}")

        # Step 2: Check cache first (fastest path)
        cached_result = check_cache(task, project_context)
        if cached_result and cached_result.confidence > 0.85:
            logger.info(f"Task {task.id} routed to CACHE (confidence={cached_result.confidence})")
            return Route.CACHED, None

        # Step 3: Check constraints
        remaining_budget = budget_constraints.check_remaining()
        user_blocking = task.priority == "immediate"

        # Step 4: Check circuit breakers for rAI providers
        preferred_provider = select_provider(task_type, complexity_score)
        if circuit_breaker.is_open(preferred_provider):
            logger.warning(f"Circuit breaker open for {preferred_provider}, using fallback")
            preferred_provider = get_fallback_provider(preferred_provider)
            if not preferred_provider:
                # No rAI available, force VD-only
                logger.error("All rAI providers unavailable, forcing VD-only")
                return Route.VD_ONLY, None

        # Step 5: Route decision with cost protection
        if task_type == "validation" and complexity_score < 30:
            return Route.VD_ONLY, None

        elif token_estimate > rAI_context_limit:
            logger.info(f"Task {task.id} exceeds context limit, using chunked approach")
            return Route.VD_CHUNKED_RAI, preferred_provider

        elif remaining_budget < token_estimate * cost_per_token:
            logger.warning(f"Task {task.id} exceeds budget, falling back to VD")
            return Route.VD_ONLY, None

        elif user_blocking and token_estimate < 2000:
            # Fast path for small blocking tasks
            return Route.RAI_WITH_VD_VALIDATION, preferred_provider

        else:
            return Route.RAI_WITH_VD_VALIDATION, preferred_provider

    except Exception as e:
        logger.error(f"Error routing task {task.id}: {e}", exc_info=True)
        # Safe default: VD-only on routing errors
        return Route.VD_ONLY, None

def select_provider(task_type: str, complexity: int) -> str:
    """Select optimal rAI provider based on task characteristics"""
    # Critical tasks use premium models
    if task_type in ["feature_creation", "architecture_decision"]:
        return "claude-opus" if complexity > 70 else "claude-sonnet"
    # Standard tasks use cost-effective models
    elif task_type in ["bug_fix", "refactoring"]:
        return "claude-sonnet" if complexity > 50 else "gpt-4-turbo"
    # Simple tasks use fastest models
    else:
        return "gpt-4-turbo"

def get_fallback_provider(failed_provider: str) -> Optional[str]:
    """Get fallback provider when primary fails"""
    fallback_map = {
        "claude-opus": "gpt-4-turbo",
        "claude-sonnet": "gpt-4-turbo",
        "gpt-4-turbo": "claude-sonnet",
        "gpt-4": "claude-sonnet"
    }
    return fallback_map.get(failed_provider)
```

**Circuit Breaker Benefits:**
- Prevents cascading failures when rAI provider has outage
- Automatically recovers after timeout period
- Graceful degradation to VD-only mode
- Reduces wasted API calls to failing services

---

### 1.2 Prompt Orchestration & Context Management **[P0]**
**Description:** Advanced prompt engineering and context optimization for rAI interactions

#### Context Extraction Engine:

**Codebase Analysis:**
- **Dependency graph construction:**
  - Parse imports, requires, includes across all project files
  - Build directed graph of module dependencies
  - Identify "hot paths" (most frequently used modules)
  - Calculate transitive dependencies for accurate context selection
- **Type system integration:**
  - Extract type definitions (TypeScript interfaces, Python type hints, Java classes)
  - Infer types for dynamically typed code using static analysis
  - Include relevant type hierarchies in prompts
- **Pattern library indexing:**
  - Identify recurring code patterns (e.g., error handling, logging, auth)
  - Cluster similar patterns using embeddings
  - Retrieve most relevant patterns for current task
- **Team conventions extraction:**
  - Learn naming conventions (camelCase, snake_case, etc.)
  - Extract comment/docstring styles
  - Identify preferred libraries and frameworks
  - Detect code organization patterns (file structure, module boundaries)

**Context Optimization:**
- **Token budget allocation:**
  - Reserve 20% for rAI response
  - Allocate remaining 80% across: task description (10%), relevant code (50%), examples (10%), standards (10%)
  - Dynamic adjustment based on task complexity
- **Smart truncation strategies:**
  - **Hierarchical inclusion:** Full functions > function signatures > file names
  - **Relevance ranking:** Semantic similarity to task description
  - **Recency weighting:** Prioritize recently modified files
  - **Dependency priority:** Include upstream dependencies before downstream
- **Context compression techniques:**
  - Remove comments and whitespace for context fitting (restore in final output)
  - Summarize large files (VD generates concise description)
  - Use abstract syntax trees (AST) instead of raw code where possible

**Prompt Template System:**

**Template Library (P0):**
```
Templates by task type:
- feature_creation: Detailed requirements + examples + test expectations
- bug_fix: Error description + stack trace + relevant code + similar past fixes
- refactoring: Current code + desired outcome + constraints (no behavior change)
- documentation: Code to document + existing doc style + completeness requirements
- test_generation: Code to test + coverage goals + test framework conventions
```

**Dynamic Template Composition:**
- Select base template by task type
- Inject project-specific context sections
- Add few-shot examples from project history
- Include explicit response format requirements
- Append validation criteria for VD to check

**Response Format Specification (P0):**
```json
{
  "response_format": {
    "type": "structured",
    "format": "json",
    "schema": {
      "workplan": {
        "tasks": [
          {
            "id": "string",
            "description": "string",
            "dependencies": ["task_id"],
            "estimated_complexity": "low|medium|high",
            "parallel_compatible": "boolean"
          }
        ]
      },
      "implementation": {
        "files": [
          {
            "path": "string",
            "action": "create|modify|delete",
            "content": "string",
            "rationale": "string"
          }
        ]
      },
      "tests": {
        "unit_tests": ["string"],
        "integration_tests": ["string"],
        "coverage_estimate": "number"
      },
      "error_handling": {
        "edge_cases_considered": ["string"],
        "error_scenarios": ["string"]
      }
    }
  }
}
```

**Prompt Optimization Techniques:**
- **Few-shot learning:** Include 2-3 examples of ideal responses from past successful tasks
- **Chain-of-thought:** Request step-by-step reasoning before code generation
- **Self-reflection:** Ask rAI to critique its own output before finalizing
- **Constraint specification:** Explicit requirements (e.g., "must handle null values", "prefer async/await over promises")

**Batching & Reuse Strategies:**
- **Context caching:** Store frequently-used context (project conventions, type definitions) and reuse across tasks
- **Prompt deduplication:** Identify common prompt sections, cache and reference
- **Batch API calls:** Group independent tasks into single API call with multiple prompts (where rAI API supports)
- **Streaming optimization:** Start validation on early tokens while rAI still generating

---

### 1.3 VD Validation & Quality Control **[P0]**
**Description:** Multi-dimensional quality assurance before human review

#### Validation Engine Architecture:

**Real-Time Syntax Validation:**
- **Streaming parser:** Validate syntax as tokens arrive from rAI
- **Early termination:** Stop rAI generation if syntax errors detected early
- **Language-specific parsers:**
  - Python: AST parser, PEP 8 compliance
  - TypeScript/JavaScript: TSC, ESLint integration
  - Go: go fmt, go vet integration
  - Java: javac, Checkstyle integration
  - Rust: rustc, clippy integration

**Pattern Compliance Checker:**
- **Style consistency:**
  - Compare generated code against project style guide
  - Check naming conventions, indentation, line length
  - Verify import ordering, file organization
  - Score: 0-100 based on % of style rules followed
- **Architectural patterns:**
  - Detect design patterns used (singleton, factory, observer, etc.)
  - Verify pattern is appropriate for use case
  - Check pattern implementation correctness
- **Anti-pattern detection:**
  - God objects, circular dependencies, tight coupling
  - Code smells: long methods, duplicate code, dead code
  - Security anti-patterns: SQL injection vulnerabilities, hardcoded secrets, insecure crypto
  - Flag with severity: CRITICAL, HIGH, MEDIUM, LOW

**Semantic Analysis:**
- **Type safety verification:**
  - Run static type checker (mypy, TypeScript compiler)
  - Verify all type annotations present (if project requires)
  - Check for type compatibility across function boundaries
- **Logic validation:**
  - Detect unreachable code, infinite loops, missing return statements
  - Verify null/undefined checks present where required
  - Check error handling completeness
  - Validate edge case handling (empty arrays, negative numbers, null inputs)
- **Dependency correctness:**
  - Ensure imported modules exist and are used
  - Check for circular imports
  - Verify version compatibility of external dependencies

**Test Completeness Assessment:**
- **Coverage requirements:**
  - Ensure tests generated for all public methods/functions
  - Check happy path + error cases covered
  - Verify edge cases tested (boundary values, empty inputs, large inputs)
  - Score: % of code paths with corresponding tests
- **Test quality evaluation:**
  - Check assertions present (not just calling functions)
  - Verify test isolation (no shared state between tests)
  - Ensure meaningful test names and descriptions
  - Validate test data quality (realistic, not just "test123")

**Security Scanning:**
- **OWASP Top 10 checks:**
  - SQL injection, XSS, CSRF vulnerabilities
  - Insecure deserialization, XXE
  - Broken authentication/authorization
- **Dependency vulnerability scan:**
  - Check for known CVEs in imported libraries
  - Suggest updates to vulnerable dependencies
- **Secret detection:**
  - Scan for API keys, passwords, tokens in code
  - Check for credentials in comments or variable names

#### VD Scoring System (P0):

**Multi-Dimensional Quality Score:**
```json
{
  "validation_score": {
    "correctness": {
      "score": 85,
      "max": 100,
      "components": {
        "syntax": 100,
        "types": 90,
        "logic": 80,
        "dependencies": 85
      },
      "issues": [
        {
          "severity": "medium",
          "type": "logic_error",
          "description": "Potential null pointer in line 42",
          "suggestion": "Add null check before accessing property"
        }
      ]
    },
    "quality": {
      "score": 78,
      "max": 100,
      "components": {
        "style_compliance": 85,
        "pattern_adherence": 80,
        "maintainability": 70,
        "readability": 75
      },
      "issues": [
        {
          "severity": "low",
          "type": "style_violation",
          "description": "Function exceeds 50-line limit (65 lines)",
          "suggestion": "Consider extracting helper functions"
        }
      ]
    },
    "safety": {
      "score": 92,
      "max": 100,
      "components": {
        "error_handling": 95,
        "security": 90,
        "edge_cases": 90
      },
      "issues": []
    },
    "testability": {
      "score": 88,
      "max": 100,
      "components": {
        "test_coverage": 85,
        "test_quality": 90,
        "integration_tests": 90
      },
      "issues": []
    },
    "overall_score": 85.75,
    "decision": "APPROVE_FOR_TESTING",
    "confidence": 0.92
  }
}
```

**Decision Matrix:**
```
Overall Score >= 85 + No CRITICAL issues → APPROVE_FOR_TESTING
Overall Score 70-84 + No CRITICAL issues → REFINE (Level 1 escalation)
Overall Score 50-69 OR CRITICAL issues present → REFINE (Level 2 escalation)
Overall Score < 50 OR Multiple CRITICAL issues → ESCALATE_TO_HUMAN
Validation uncertain (confidence < 0.7) → ESCALATE_TO_HUMAN
```

**Feedback Generation for Refinement:**
- **Structured feedback format:**
  - Prioritized list of issues (CRITICAL → HIGH → MEDIUM → LOW)
  - Specific file/line references
  - Actionable suggestions for fixes
  - Examples of correct patterns from codebase
- **Refinement prompt construction:**
  - Original task + previous attempt + validation feedback
  - Emphasize specific issues to address
  - Include relevant examples from project
  - Request focused fix (not complete rewrite)

---

### 1.4 Developer Workflows & Integrations **[P0 → P1]**
**Description:** Seamless integration with developer tools and workflows

#### IDE Integration **[P1]**

**Supported IDEs:**
- **VS Code Extension (Priority 1):** Most popular, large market
- **JetBrains Plugin (Priority 2):** IntelliJ, PyCharm, WebStorm, GoLand
- **Neovim/Vim Plugin (Priority 3):** Developer community preference
- **Emacs Mode (Priority 3):** Enterprise developers

**VS Code Extension Features:**

**1. Inline Task Submission:**
```typescript
// User selects code, right-clicks, "Submit to Obra"
// Or uses command palette: "Obra: Generate Tests for Selection"
// Or keyboard shortcut: Ctrl+Shift+O

interface TaskSubmission {
  type: "feature" | "bug_fix" | "refactor" | "test" | "docs";
  scope: "selection" | "file" | "project";
  intent: string;  // User-provided description
  context: {
    selectedCode?: string;
    currentFile: string;
    cursorPosition: Position;
    openFiles: string[];
    gitBranch: string;
  };
}
```

**2. Real-Time Progress Indicator:**
- Status bar shows: "Obra: Generating tests... (30%)"
- Notifications for: task queued, validation started, tests running, complete
- Click notification to view full task details

**3. Diff Preview Before Acceptance:**
```typescript
// Show side-by-side diff in editor
// Left: Current code | Right: Obra-generated code
// Bottom panel: Validation scores, test results, cost estimate

interface DiffPreview {
  files: Array<{
    path: string;
    action: "create" | "modify" | "delete";
    currentContent: string;
    proposedContent: string;
    validationScore: number;
  }>;
  summary: {
    filesChanged: number;
    linesAdded: number;
    linesRemoved: number;
    estimatedCost: number;
    validationScore: number;
    testsPassed: boolean;
  };
  actions: ["accept_all", "accept_file", "reject", "request_changes"];
}
```

**4. Inline Annotations:**
- Obra-generated code highlighted with subtle background color
- Hover to see: generation time, model used, validation score
- Click to view full task history and reasoning

**5. Chat Interface (P2):**
- Sidebar chat panel for conversational refinement
- "Obra, make this function async" → instant update
- Context-aware: knows current file, git branch, recent changes

**Implementation:**
- Extension built with TypeScript + VS Code Extension API
- Communicates with Obra via WebSocket (real-time updates)
- Uses VS Code's Diff Editor, Notification API, Status Bar API
- Stores user preferences in workspace settings

**JetBrains Plugin:**
- Similar features as VS Code
- Built with Kotlin + IntelliJ Platform SDK
- Integrates with JetBrains UI components
- Supports all JetBrains IDEs through single codebase

---

#### Git Integration **[P0]**

**Automated Branch & PR Workflow:**

**1. Branch Creation:**
```python
# When user submits task to Obra:
def create_feature_branch(task: Task) -> str:
    """
    Automatically create git branch for Obra work.

    Branch naming: obra/{task_type}/{sanitized_description}
    Example: obra/feature/add-user-authentication
    """
    base_branch = get_current_branch()  # Usually 'main' or 'develop'
    branch_name = f"obra/{task.type}/{sanitize_branch_name(task.intent)}"

    # Ensure clean working tree
    if has_uncommitted_changes():
        if task.auto_stash:
            git("stash", "push", "-m", f"Auto-stash for {task.id}")
        else:
            raise WorkingTreeDirtyError("Commit or stash changes before starting Obra task")

    # Create and checkout branch
    git("checkout", "-b", branch_name, base_branch)

    # Store branch metadata
    git("config", f"branch.{branch_name}.obra-task-id", task.id)
    git("config", f"branch.{branch_name}.obra-base-branch", base_branch)

    return branch_name
```

**2. Commit Strategy:**
- **Granular commits:** One commit per logical change (not one giant commit)
- **Conventional commits format:**
  ```
  feat(auth): add OAuth2 authentication middleware

  - Implement OAuth2 client with support for Google, GitHub
  - Add token validation and refresh logic
  - Include unit tests with 95% coverage

  Generated by Obra (task: task_xyz123)
  Validation score: 92/100
  Cost: $0.47
  ```
- **Signed commits (P1):** GPG sign with Obra's key + co-authored-by developer
- **Atomic commits:** Each commit passes tests independently

**3. Pull Request Creation:**
```python
def create_pull_request(task: Task, branch: str) -> PullRequest:
    """
    Auto-generate PR with comprehensive description.
    """
    # Get all commits on branch
    commits = git("log", f"{base_branch}..{branch}", "--oneline")

    # Generate PR description using VD
    pr_description = generate_pr_description(
        task=task,
        commits=commits,
        validation_results=task.validation_results,
        test_results=task.test_results,
        files_changed=git("diff", "--name-only", f"{base_branch}..{branch}")
    )

    # Create PR via GitHub/GitLab/Bitbucket API
    pr = github_api.create_pull_request(
        title=task.intent,
        body=pr_description,
        head=branch,
        base=base_branch,
        labels=["obra-generated", task.type],
        assignees=[task.submitted_by],
        draft=task.needs_review  # Draft if validation score < 80
    )

    # Add PR link to task for tracking
    task.metadata["pull_request_url"] = pr.html_url

    return pr
```

**Example PR Description (VD-Generated):**
```markdown
## Summary
Implements OAuth2 authentication system with support for Google and GitHub providers.

## Changes
- **Authentication Middleware** (`src/auth/oauth2.py`): New OAuth2 client with token management
- **User Model** (`src/models/user.py`): Added OAuth provider fields and token storage
- **API Endpoints** (`src/api/auth.py`): Login, logout, callback routes
- **Tests** (`tests/test_auth.py`): 47 new tests, 95% coverage

## Validation Results
- **Obra Score:** 92/100
- **Security:** ✅ No vulnerabilities detected
- **Tests:** ✅ All 47 tests passing
- **Coverage:** ✅ 95% (target: 85%)
- **Linting:** ✅ No issues

## Testing Instructions
1. Set environment variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
2. Run `python -m pytest tests/test_auth.py`
3. Test login flow at `http://localhost:8000/auth/login`

## Cost
- **Tokens:** 8,347 (remote) + 12,450 (local)
- **API Cost:** $0.47
- **Time:** 3.2 minutes

---
🤖 Generated by [Obra](https://obra.ai) (task: #task_xyz123)
```

**4. PR Review Integration:**
- Obra monitors PR comments
- If reviewer requests changes, Obra can automatically generate fixes
- Reviewer types: "@obra fix the null pointer on line 42" → Obra pushes update
- Integrates with GitHub Actions, GitLab CI for automated checks

---

#### CI/CD Integration **[P1]**

**Pre-Commit Validation:**
```yaml
# .obra/pre-commit.yaml
validation:
  required_scores:
    correctness: 85
    quality: 75
    safety: 90
    testability: 80

  required_checks:
    - syntax_valid
    - tests_pass
    - no_critical_security_issues
    - coverage_above_threshold

  actions_on_failure:
    - block_commit: true
    - notify_developer: true
    - suggest_refinement: true
```

**CI Pipeline Integration:**

**GitHub Actions Example:**
```yaml
# .github/workflows/obra-validation.yml
name: Obra Validation

on: [pull_request]

jobs:
  obra-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Obra Security Scan
        uses: obra-ai/security-scan-action@v1
        with:
          obra-api-key: ${{ secrets.OBRA_API_KEY }}
          fail-on-critical: true

      - name: Obra Quality Check
        uses: obra-ai/quality-check-action@v1
        with:
          min-score: 80
          report-format: github-check

      - name: Post Results to PR
        uses: obra-ai/pr-comment-action@v1
        with:
          include-cost-breakdown: true
          include-validation-details: true
```

**GitLab CI Example:**
```yaml
# .gitlab-ci.yml
obra:validate:
  stage: test
  image: obra/cli:latest
  script:
    - obra validate --format gitlab --min-score 80
  artifacts:
    reports:
      junit: obra-validation-report.xml
  only:
    - merge_requests
```

**Integration Benefits:**
- Catch issues before human review
- Automated code quality gates
- Cost tracking per PR
- Compliance enforcement (all Obra code must score >80)

---

#### Project Onboarding **[P0]**

**Codebase Analysis & Indexing:**
```python
def onboard_project(project_path: str) -> OnboardingReport:
    """
    Analyze existing codebase and prepare for Obra.

    Time estimate: 5-30 minutes depending on project size
    """
    report = OnboardingReport()

    # Step 1: Detect project structure
    report.language = detect_primary_language(project_path)
    report.framework = detect_framework(project_path)  # React, Django, Rails, etc.
    report.build_system = detect_build_system(project_path)  # npm, Maven, Cargo, etc.

    # Step 2: Analyze codebase statistics
    report.total_files = count_files(project_path)
    report.total_lines = count_lines_of_code(project_path)
    report.languages = detect_all_languages(project_path)

    # Step 3: Extract patterns and conventions
    report.patterns = analyze_code_patterns(project_path)
    # - Naming conventions (camelCase, snake_case, PascalCase)
    # - Indentation (spaces, tabs, size)
    # - Import styles
    # - Error handling patterns
    # - Logging patterns
    # - Test patterns

    # Step 4: Build dependency graph
    report.dependency_graph = build_dependency_graph(project_path)

    # Step 5: Extract type definitions
    report.type_definitions = extract_types(project_path)

    # Step 6: Identify test coverage
    report.test_coverage = analyze_test_coverage(project_path)
    report.test_framework = detect_test_framework(project_path)

    # Step 7: Detect potential issues
    report.warnings = detect_issues(project_path)
    # - Large files (>1000 lines) that may hit context limits
    # - Circular dependencies
    # - Missing tests
    # - Security vulnerabilities

    # Step 8: Generate recommendations
    report.recommendations = generate_recommendations(report)

    # Step 9: Create Obra configuration
    create_obra_config(project_path, report)

    return report
```

**Example Onboarding Report:**
```json
{
  "project": {
    "name": "acme-web-app",
    "language": "Python",
    "framework": "Django 4.2",
    "build_system": "pip",
    "total_files": 342,
    "total_lines": 28450,
    "languages": {"Python": 85, "JavaScript": 10, "HTML": 5}
  },
  "patterns": {
    "naming": "snake_case",
    "indentation": "4 spaces",
    "imports": "absolute imports preferred",
    "error_handling": "try-except with logging",
    "logging": "Python logging module with INFO level"
  },
  "test_coverage": {
    "overall": 73,
    "unit_tests": 512,
    "integration_tests": 43,
    "framework": "pytest",
    "untested_files": 47
  },
  "warnings": [
    "Large file detected: models/user.py (1450 lines) - consider refactoring",
    "Circular dependency: services/auth.py ↔ services/user.py",
    "18 files missing tests (below 50% coverage)"
  ],
  "recommendations": [
    "Start with small tasks (<500 tokens) to validate Obra setup",
    "Focus on untested modules first (easy wins, high value)",
    "Consider breaking up models/user.py before using Obra for refactoring",
    "Set daily budget to $50 during onboarding period"
  ],
  "estimated_context_size": "~45k tokens (fits in Llama 3.1 70B context)"
}
```

**Auto-Generated `.obra/config.yaml`:**
```yaml
project:
  name: acme-web-app
  language: python
  framework: django

# Extracted conventions
conventions:
  naming: snake_case
  indentation: 4
  max_line_length: 100
  imports: absolute_preferred

# VD model selection based on project size
vd:
  model: llama-3.1-70b  # Large enough for 45k token context
  quantization: none
  gpu_layers: -1  # Use all GPU

# rAI provider preferences
rai:
  default_provider: claude-sonnet
  fallback_provider: gpt-4-turbo
  max_tokens_per_request: 8000

# Budget controls
budget:
  daily_limit_usd: 50.00
  alert_threshold_percent: 80
  auto_pause_on_limit: true

# Quality gates
validation:
  min_overall_score: 80
  min_correctness_score: 85
  min_safety_score: 90
  block_on_critical_issues: true

# Testing
testing:
  framework: pytest
  required_coverage_percent: 75
  run_tests_before_approval: true

# Git integration
git:
  auto_create_branch: true
  auto_create_pr: true
  branch_prefix: obra
  commit_style: conventional

# Notification channels
notifications:
  slack_webhook: null  # Optional
  email: null  # Optional
```

---

#### Migration from Other Tools **[P2]**

**Copilot → Obra Migration:**
```bash
$ obra migrate --from copilot

Analyzing GitHub Copilot usage...
- Found 1,247 Copilot completions in git history (last 30 days)
- Estimated monthly cost: $39/seat × 50 developers = $1,950
- Average completions per developer: 25/day

Estimating Obra equivalent:
- Obra can handle these as background tasks (not inline completions)
- Estimated monthly cost with Obra: $750 (62% reduction)
- Setup time: ~2 hours

Proceed with migration? [y/N]:
```

**Cursor → Obra Migration:**
- Export Cursor settings and preferences
- Map Cursor keyboard shortcuts to Obra
- Import conversation history for context learning

**Aider → Obra Migration:**
- Import Aider's .aider config
- Migrate task history for pattern learning
- Preserve custom prompt templates

---

## 2. RELIABILITY & RECOVERY

### 2.1 State Management & Auto-Save **[P0]**
**Description:** Comprehensive state persistence with efficient storage and fast recovery

#### State Architecture:

**Hierarchical State Model:**
```
Project State
├── Configuration State (project settings, VD config, rAI provider settings)
├── Conversation State (VD-rAI dialogue history, context windows)
├── Code State (file system snapshot, git status)
├── Test State (test results, coverage reports, performance metrics)
├── Task State (current task queue, progress, dependencies)
└── Metrics State (costs, timings, quality scores)
```

**Auto-Save Implementation:**
- **Trigger-based saving:**
  - Time-based: Every 30 seconds (configurable)
  - Event-based: After each rAI response, after test completion, after validation
  - Manual: User-triggered save (Ctrl+S equivalent)
  - Pre-operation: Before risky operations (refactors, deletions)
- **Incremental saves:**
  - Track changed files only (not full snapshots)
  - Use git-like delta storage for efficiency
  - Compress old deltas (gzip) to reduce storage
- **Storage optimization:**
  - Hot state (last 10 saves): Uncompressed, fast access
  - Warm state (last 100 saves): Compressed, ~10s load time
  - Cold state (older): Archived to object storage (S3, GCS), slow but cheap

**Checkpoint System:**
- **Automatic checkpoint creation:**
  - After all tests pass
  - Before starting new major feature
  - After successful deployment
  - Daily at end of work session
- **Checkpoint metadata:**
  ```json
  {
    "checkpoint_id": "uuid",
    "timestamp": "ISO-8601",
    "description": "All tests passing after auth feature",
    "type": "automatic|manual",
    "quality_metrics": {
      "test_pass_rate": 100,
      "coverage": 87,
      "linting_issues": 3
    },
    "files_changed_since_last": 12,
    "total_cost_to_checkpoint": 1.24
  }
  ```
- **Rollback capabilities:**
  - One-click rollback to any checkpoint
  - Selective file rollback (not full project)
  - Preview changes before rollback
  - Retain rollback history (can undo rollback)

**State Recovery:**
- **Fast boot:** Load last state in <5 seconds
- **Integrity verification:** Checksum validation on load
- **Conflict resolution:** Handle concurrent edits (if multi-user)
- **Migration:** Auto-upgrade state format on Obra version updates

---

### 2.2 Crash & Failure Recovery **[P1]**
**Description:** Automatic fault detection and recovery with minimal data loss

#### Failure Detection:

**Health Monitoring:**
- **VD process monitoring:**
  - CPU/memory usage tracking
  - Response time monitoring (flag if >10s for simple tasks)
  - Heartbeat signals (every 5 seconds)
  - Graceful degradation detection (model running slow)
- **rAI API monitoring:**
  - HTTP status codes (track 4xx, 5xx errors)
  - Timeout detection (flag calls >60s)
  - Rate limit monitoring (track 429 responses)
  - Service availability checks (ping endpoints every minute)
- **System resource monitoring:**
  - Disk space (alert if <5GB free)
  - Memory pressure (alert if <10% free RAM)
  - GPU health (temperature, utilization)
  - Network connectivity

**Failure Classification:**
```
TRANSIENT: Temporary issues (network blip, rate limit) → Retry with backoff
RESOURCE: Out of memory, disk full → Clean up and retry
CONFIGURATION: Bad API key, invalid settings → Notify user, halt
CRITICAL: VD crash, data corruption → Emergency recovery
```

**Automatic Recovery Procedures:**

**Level 1 - Soft Recovery (No Data Loss):**
- Retry failed operation with exponential backoff
- Switch to backup rAI provider if primary fails
- Reduce batch size if memory constrained
- Flush caches and retry

**Level 2 - Process Restart (Minimal Data Loss):**
- Kill and restart VD process
- Reload from last auto-save (<30s old)
- Resume current task from last checkpoint
- Notify user of brief interruption

**Level 3 - Hard Recovery (Some Data Loss Possible):**
- Restore from last known-good checkpoint
- Discard incomplete work since checkpoint
- Prompt user to review and re-submit lost work
- Log incident for root cause analysis

**Root Cause Analysis (Automated):**
- Parse crash logs and stack traces
- Correlate with system metrics at crash time
- Identify common crash patterns
- Generate incident report with:
  - Timeline of events leading to crash
  - Suspected root cause
  - Recommended preventive measures
  - Similar past incidents

**Preventive Measures:**
- **Pre-flight checks:** Verify resources available before starting tasks
- **Circuit breakers:** Stop calling failing rAI provider after N consecutive failures
- **Resource limits:** Cap VD memory usage, kill and restart if exceeded
- **Graceful degradation:** Fall back to simpler models if advanced models unavailable

---

### 2.3 Error Recovery & Escalation **[P0]**
**Description:** Progressive escalation with cost-aware decision making

#### Escalation Framework:

**Escalation Triggers:**
```python
def should_escalate(task_attempt):
    return (
        task_attempt.failures >= 3 or
        task_attempt.time_spent > 600  # 10 minutes or
        task_attempt.validation_score < 30 or
        task_attempt.cost > task_attempt.budget * 1.5 or
        task_attempt.human_requested_escalation
    )
```

**Four-Level Escalation Hierarchy:**

**Level 0 - Normal Operation:**
- VD routes task to appropriate rAI model
- Standard prompt templates
- Default token budget
- Success rate: ~85%

**Level 1 - Enhanced Context:**
- **Trigger:** 1-2 failed attempts, validation score 50-70
- **Actions:**
  - VD adds more context to prompt (include more files, examples)
  - Add explicit instructions addressing validation failures
  - Increase token budget by 25%
  - Request chain-of-thought reasoning from rAI
- **Cost impact:** +25% tokens
- **Success rate improvement:** ~10-12%

**Level 2 - Model Upgrade:**
- **Trigger:** 2-3 failed attempts, validation score 30-50
- **Actions:**
  - Switch to more capable rAI model (GPT-4 → GPT-4 Turbo, Claude Sonnet → Opus)
  - Include full file context (no truncation)
  - Add detailed examples of correct approach
  - Increase token budget by 50%
  - Request self-critique and revision
- **Cost impact:** +2-3x tokens (larger model + more tokens)
- **Success rate improvement:** ~15-20%

**Level 3 - Expert Model + Max Context:**
- **Trigger:** 3+ failed attempts, validation score <30
- **Actions:**
  - Use most capable model available (GPT-4 Turbo, Claude Opus)
  - Maximum token budget (no limits)
  - Include entire project context (all relevant files)
  - Use multi-turn dialogue for iterative refinement
  - VD acts as interactive reviewer, guides rAI step-by-step
- **Cost impact:** +5-10x tokens
- **Success rate improvement:** ~20-25%

**Level 4 - Human Escalation:**
- **Trigger:** Level 3 failed, or validation confidence <0.5, or user-requested
- **Actions:**
  - Package complete context for human review:
    - Original intent
    - All previous attempts and validation feedback
    - Specific blocking issues
    - Estimated effort to resolve manually
  - Notify assigned developer via Slack/email
  - Pause task, mark as "Blocked - Human Review Required"
  - Provide human with option to:
    - Complete manually
    - Provide guidance and retry with VD
    - Simplify task requirements
    - Cancel task

**Cost Tracking per Escalation:**
```json
{
  "task_id": "feature_123",
  "escalation_history": [
    {
      "level": 0,
      "attempts": 2,
      "cost_usd": 0.12,
      "time_seconds": 45,
      "outcome": "failed"
    },
    {
      "level": 1,
      "attempts": 1,
      "cost_usd": 0.18,
      "time_seconds": 62,
      "outcome": "failed"
    },
    {
      "level": 2,
      "attempts": 1,
      "cost_usd": 0.47,
      "time_seconds": 95,
      "outcome": "success"
    }
  ],
  "total_cost": 0.77,
  "total_time": 202,
  "final_outcome": "success",
  "cost_vs_budget": 1.28
}
```

**Escalation Analytics:**
- Track escalation patterns by:
  - Task type (feature, bug fix, refactor)
  - Project/language
  - rAI model used
  - Developer who created task
- Identify root causes:
  - Unclear requirements (high Level 4 escalation)
  - Context limitations (frequent Level 1 escalation)
  - Model capability gaps (frequent Level 2 escalation)
- Recommend improvements:
  - Better task decomposition
  - Improved prompt templates
  - Different default model selection

---

## 3. PERFORMANCE & RESOURCE MANAGEMENT

### 3.1 Local Hardware Optimization **[P1]**
**Description:** Adaptive performance tuning for heterogeneous hardware environments

#### Hardware Detection & Profiling:

**Comprehensive System Scan:**
```python
class HardwareProfile:
    cpu: CPUInfo = {
        "vendor": "Intel|AMD|Apple",
        "model": "i9-13900K",
        "cores": 24,
        "threads": 32,
        "base_clock_ghz": 3.0,
        "boost_clock_ghz": 5.8,
        "cache_mb": 36,
        "instruction_sets": ["AVX", "AVX2", "AVX-512"]
    }
    
    gpu: List[GPUInfo] = [{
        "vendor": "NVIDIA|AMD|Apple",
        "model": "RTX 4090",
        "vram_gb": 24,
        "cuda_cores": 16384,
        "tensor_cores": 512,
        "compute_capability": "8.9",
        "power_limit_watts": 450,
        "pcie_gen": 4
    }]
    
    memory: MemoryInfo = {
        "total_gb": 64,
        "type": "DDR5",
        "speed_mhz": 6000,
        "channels": 4
    }
    
    storage: StorageInfo = {
        "boot_drive": {
            "type": "NVMe",
            "capacity_gb": 2000,
            "read_speed_mbps": 7000,
            "write_speed_mbps": 5000
        }
    }
    
    network: NetworkInfo = {
        "connection_type": "Ethernet|WiFi",
        "speed_mbps": 1000,
        "latency_ms": 2
    }
```

**Performance Benchmarking (First Run):**
- **VD model inference speed test:**
  - Load selected VD model (e.g., Llama 3.1 70B)
  - Run 100 inference passes with varying context lengths
  - Measure: tokens/second, latency, memory usage
  - Determine optimal batch size and context length
- **Disk I/O benchmark:**
  - Measure read/write speeds for project directory
  - Test file scanning performance (important for context extraction)
- **Network latency test:**
  - Ping rAI API endpoints
  - Measure round-trip times
  - Test bandwidth with sample requests

**Auto-Configuration Engine:**

**VD Model Selection:**
```
Hardware Tier → Recommended VD Model → Expected Performance

Ultra (H100, A100):
  - Llama 3.1 405B quantized
  - ~40 tokens/sec
  - 80GB VRAM required
  - Best validation quality

High (RTX 4090, RTX 3090):
  - Llama 3.1 70B
  - ~20 tokens/sec
  - 24GB VRAM required
  - Excellent validation quality

Mid (RTX 4070, RTX 3070):
  - Llama 3.1 8B
  - ~80 tokens/sec
  - 12GB VRAM required
  - Good validation quality

Low (CPU only, 32GB+ RAM):
  - Llama 3.1 8B quantized (4-bit)
  - ~5 tokens/sec
  - CPU inference
  - Acceptable validation quality

Minimal (CPU only, 16GB RAM):
  - Remote validation only
  - No local VD model
  - Higher API costs but functional
```

**Optimization Strategies by Hardware:**

**GPU-Accelerated Mode:**
- Enable FlashAttention-2 for faster inference
- Use tensor cores for matmul operations
- Batch multiple validation requests together
- Keep model weights in VRAM (no swapping)
- Reserve 10% VRAM for OS and other processes

**CPU-Only Mode:**
- Quantize model to 4-bit (reduces memory, slight quality loss)
- Enable AVX-512 instructions if available
- Set thread count = physical cores (not hyperthreads)
- Limit batch size to 1 (avoid memory thrashing)
- Consider remote-only validation if CPU too slow

**Mixed Mode (GPU + CPU):**
- Run VD model on GPU
- Use CPU for parallel tasks (file scanning, test execution)
- Optimize data transfer between CPU/GPU
- Monitor GPU utilization, offload to CPU if underutilized

**Resource Monitoring & Dynamic Adjustment:**

**Real-Time Telemetry:**
- Poll every 5 seconds:
  - CPU usage per core
  - GPU usage, VRAM usage, GPU temperature
  - System RAM usage, swap usage
  - Disk I/O rates
  - Network bandwidth usage
- Display in dashboard (P2) or CLI status bar (P0)

**Adaptive Throttling:**
```python
def adjust_workload(current_metrics):
    if current_metrics.gpu_temp > 85:
        reduce_batch_size()
        reduce_inference_frequency()
    
    if current_metrics.ram_usage > 0.9:
        clear_caches()
        reduce_context_window_size()
    
    if current_metrics.disk_io_wait > 0.5:
        reduce_file_scanning_frequency()
        enable_result_caching()
    
    if current_metrics.cpu_usage > 0.95:
        pause_background_tasks()
        reduce_agent_count()
```

**Performance Recommendations (P2):**
- Log bottlenecks with specific metrics:
  ```
  "GPU inference limited: 90% utilization during validation. 
   Upgrade to RTX 4090 for 2.5x speedup ($1,600). 
   ROI: Save 12 hours/month at $100/hr = $1,200/month."
  ```
- Suggest configuration changes:
  ```
  "Disk I/O bottleneck detected. Project on HDD (120 MB/s). 
   Move to SSD for 10x faster context loading."
  ```
- Recommend cloud alternatives if local hardware insufficient:
  ```
  "CPU-only mode running 15x slower than GPU mode. 
   Consider Obra Cloud ($50/month) for 10x speedup."
  ```

---

### 3.2 Agent Architecture & Parallelism **[P1 → P2]**
**Description:** Scalable multi-agent system with intelligent workload distribution

#### Evolution Path:

**Phase 1: Single-Instance VD (P0 - Alpha)**

**Architecture:**
- Single Python process running VD model
- Sequential task execution
- Context switching between task types (design → coding → testing)
- No true parallelism

**Advantages:**
- Simple to implement and debug
- Low resource usage
- Predictable behavior
- No inter-process communication overhead

**Limitations:**
- No parallel execution (underutilizes multi-core CPUs)
- Context switching overhead
- Blocked on long-running tasks (rAI calls, test execution)

**Use Case:** MVP validation, small projects (<10k LOC)

---

**Phase 2: Limited Multi-Agent (P1 - Beta)**

**Architecture:**
- Main VD coordinator process
- Spawn specialized agents for parallelizable tasks:
  - **Test Execution Agent:** Runs tests in isolation
  - **Static Analysis Agent:** Parallel linting, type checking
  - **Documentation Agent:** Generate docs while tests run
- Agents communicate via message queue (Redis, RabbitMQ)

**Task Distribution Logic:**
```python
def distribute_tasks(task_graph):
    # Identify independent tasks (no dependencies)
    independent_tasks = find_tasks_with_no_deps(task_graph)
    
    # Spawn agents for independent tasks
    agents = []
    for task in independent_tasks:
        if task.type == "test_execution":
            agent = spawn_test_agent(task)
        elif task.type == "static_analysis":
            agent = spawn_analysis_agent(task)
        else:
            agent = spawn_generic_agent(task)
        agents.append(agent)
    
    # Wait for completion, collect results
    results = await asyncio.gather(*[agent.complete() for agent in agents])
    
    # Merge results and proceed to dependent tasks
    return merge_results(results)
```

**Advantages:**
- 2-3x speedup for projects with parallel tasks
- Better resource utilization (use all CPU cores)
- Non-blocking test execution

**Limitations:**
- Limited parallelism (only for specific task types)
- Overhead of spawning processes
- Complexity in result aggregation

**Use Case:** Medium projects (10k-100k LOC), CI/CD integration

---

**Phase 3: Full Multi-Agent System (P2 - Scale)**

**Architecture:**
- **Project Manager Agent (Coordinator):**
  - Analyzes entire workplan
  - Identifies parallelizable tasks
  - Allocates resources to agents
  - Aggregates results
  - Handles failures and re-scheduling
  
- **Specialized Execution Agents:**
  - **Design Agent:** Breaks down features into implementation tasks
  - **Coding Agent (multiple instances):** Each generates code for a module
  - **Testing Agent (multiple instances):** Parallel test execution, result analysis
  - **Debugging Agent:** Analyzes failures, generates fixes
  - **Documentation Agent:** Generates docs, comments, API references
  - **Review Agent:** Simulates code review, suggests improvements

**Agent Pool Management:**
```python
class AgentPool:
    def __init__(self, max_agents=10):
        self.available_agents = []
        self.busy_agents = []
        self.max_agents = max_agents
    
    def acquire_agent(self, agent_type):
        # Try to reuse existing agent of same type
        for agent in self.available_agents:
            if agent.type == agent_type:
                self.available_agents.remove(agent)
                self.busy_agents.append(agent)
                return agent
        
        # Spawn new agent if under limit
        if len(self.busy_agents) < self.max_agents:
            agent = spawn_agent(agent_type)
            self.busy_agents.append(agent)
            return agent
        
        # Wait for agent to become available
        return self.wait_for_agent(agent_type)
    
    def release_agent(self, agent):
        self.busy_agents.remove(agent)
        self.available_agents.append(agent)
```

**Inter-Agent Communication:**
- **Message Broker:** Redis Pub/Sub or RabbitMQ
- **Shared State:** Distributed cache (Redis) for project state
- **File Locks:** Prevent concurrent modifications to same files
- **Event Bus:** Agents publish events (task_complete, test_failed) for coordination

**Workplan Optimization:**
- **Critical Path Analysis:** Identify longest dependency chain, prioritize
- **Resource-Aware Scheduling:** Don't over-allocate (respect CPU/GPU limits)
- **Cost-Benefit Analysis:** Parallelize only if speedup > overhead
- **Failure Handling:** If agent fails, reassign task to another agent

**Example: Parallel Feature Development:**
```
Feature: "Add user authentication system"

PM Agent decomposes into:
1. Database schema (coding agent 1) - 10 min
2. Auth middleware (coding agent 2) - 15 min  
3. Login API endpoint (coding agent 3) - 12 min
4. Logout API endpoint (coding agent 4) - 8 min
5. Password reset flow (coding agent 5) - 20 min

Dependencies:
- Tasks 2, 3, 4 depend on task 1 (schema)
- Task 5 depends on tasks 3, 4

Execution Plan:
T=0: Start task 1
T=10: Tasks 1 complete → Start tasks 2, 3, 4 in parallel
T=25: Tasks 2, 3, 4 complete → Start task 5
T=45: Task 5 complete → Run tests (testing agents in parallel)
T=50: All tests pass → Feature complete

Sequential time: 65 minutes
Parallel time: 50 minutes
Speedup: 1.3x
```

**Advantages:**
- 3-5x speedup for large projects
- Scales with available hardware
- Flexible resource allocation

**Limitations:**
- Complex coordination logic
- Higher memory usage (multiple VD models loaded)
- Debugging more difficult
- Overhead for small tasks

**Use Case:** Large projects (>100k LOC), enterprise teams

---

### 3.3 Context Window Management **[P0]**
**Description:** Strategies for handling projects larger than VD/rAI context limits

#### The Context Problem:

**Typical Limits:**
- VD models: 4k-8k tokens (Llama 3.1 8B) to 128k tokens (Llama 3.1 70B)
- rAI models: 128k tokens (GPT-4 Turbo), 200k tokens (Claude Sonnet)
- Large projects: 1M+ tokens (10k files, 500k LOC)

**Challenge:** How to provide relevant context without exceeding limits?

#### Solution 1: Hierarchical Planning (P0 - Recommended for Alpha)

**Concept:** VD operates at high level, delegates module-level work to rAI

**Implementation:**
```
Layer 1 - Project Level (VD):
- Understand overall architecture
- Decompose feature into modules
- Identify module dependencies
- No code generation at this level

Layer 2 - Module Level (rAI):
- Receive module specification from VD
- Generate code for single module (<10 files)
- Fit within rAI context window
- VD validates output

Layer 3 - Testing Level (VD + rAI):
- VD orchestrates test execution
- rAI generates tests if needed
- VD interprets results, directs debugging
```

**Example Workflow:**
```
User: "Add OAuth2 authentication"

VD Layer 1:
- Analyze project structure
- Plan: Need auth middleware module, user model updates, OAuth routes
- Dependencies: auth middleware → routes → user model

VD → rAI (Task 1: User Model):
- Context: User model file + database schema
- Task: Add OAuth provider fields
- Output: Updated user model (fits in context)

VD validates → Proceed to Task 2

VD → rAI (Task 2: Auth Middleware):
- Context: Auth middleware file + user model + OAuth library docs
- Task: Implement OAuth flow
- Output: Auth middleware (fits in context)

VD validates → Proceed to Task 3

... (repeat for remaining modules)
```

**Advantages:**
- Works with any context limit
- Maintains architectural coherence
- VD has full project view
- Each rAI call focused and manageable

**Limitations:**
- Multiple rAI calls (higher latency)
- VD must be sophisticated planner
- Context boundaries must be clean (well-modularized code)

---

#### Solution 2: Retrieval-Augmented Generation (RAG) (P1)

**Concept:** Index codebase, retrieve only relevant sections for each task

**Implementation:**

**Indexing Pipeline:**
```python
# Step 1: Parse codebase into chunks
chunks = []
for file in project.files:
    functions = extract_functions(file)
    for func in functions:
        chunk = {
            "id": hash(file.path + func.name),
            "file": file.path,
            "function": func.name,
            "code": func.body,
            "docstring": func.docstring,
            "imports": func.imports,
            "calls": func.called_functions
        }
        chunks.append(chunk)

# Step 2: Generate embeddings
embedding_model = load_model("text-embedding-ada-002")
for chunk in chunks:
    chunk["embedding"] = embedding_model.encode(
        chunk["docstring"] + " " + chunk["code"]
    )

# Step 3: Store in vector database
vector_db = ChromaDB()
vector_db.add_chunks(chunks)
```

**Retrieval Pipeline:**
```python
def get_relevant_context(task_description, max_tokens=10000):
    # Step 1: Embed task description
    task_embedding = embedding_model.encode(task_description)
    
    # Step 2: Retrieve top-k similar chunks
    similar_chunks = vector_db.search(
        query_embedding=task_embedding,
        top_k=50
    )
    
    # Step 3: Re-rank by relevance
    reranked = rerank_by_recency_and_dependencies(similar_chunks)
    
    # Step 4: Select chunks that fit in token budget
    selected_chunks = []
    token_count = 0
    for chunk in reranked:
        chunk_tokens = count_tokens(chunk["code"])
        if token_count + chunk_tokens < max_tokens:
            selected_chunks.append(chunk)
            token_count += chunk_tokens
        else:
            break
    
    return selected_chunks
```

**Advantages:**
- Efficient: Only load relevant code
- Scalable: Works for massive codebases (millions of LOC)
- Flexible: Can adjust token budget dynamically

**Limitations:**
- Requires vector database infrastructure
- Embeddings must be kept up-to-date as code changes
- May miss relevant context (retrieval not perfect)
- Additional latency for retrieval

**Use Case:** Very large projects (>100k LOC), when hierarchical planning insufficient

---

#### Solution 3: Sliding Window with Overlap (P0 - Fallback)

**Concept:** Process code in overlapping chunks, stitch results together

**Implementation:**
```python
def process_large_file(file, chunk_size=8000, overlap=1000):
    chunks = split_with_overlap(file, chunk_size, overlap)
    results = []
    
    for i, chunk in enumerate(chunks):
        context = {
            "chunk": chunk,
            "is_first": i == 0,
            "is_last": i == len(chunks) - 1,
            "previous_context": results[-1] if i > 0 else None
        }
        
        result = rAI.process(context)
        results.append(result)
    
    # Stitch together, handling overlap regions
    final_result = stitch_chunks(results, overlap)
    return final_result
```

**Advantages:**
- Simple to implement
- No additional infrastructure
- Works for any content

**Limitations:**
- Coherence issues across chunk boundaries
- Redundant processing of overlap regions
- May miss cross-chunk dependencies

**Use Case:** Emergency fallback when other methods fail

---

## 4. MONITORING & OBSERVABILITY

### 4.1 Structured Logging **[P0]**
**Description:** Enterprise-grade logging for debugging, compliance, and LLM consumption

#### Multi-Tier Logging Architecture:

**Log Levels & Routing:**
```
DEBUG (verbose, dev only):
  - Every VD decision with reasoning
  - Full rAI prompts and responses
  - Intermediate validation scores
  → File: debug.log (rotated daily, 7-day retention)

INFO (operational):
  - Task starts/completions
  - Escalations
  - Checkpoint creation
  → File: info.log (rotated daily, 30-day retention)
  → Metrics backend: Prometheus

WARNING (attention needed):
  - Validation failures
  - Budget threshold warnings
  - Performance degradation
  → File: warning.log (rotated daily, 90-day retention)
  → Alerting: PagerDuty / Slack

ERROR (requires action):
  - Crash events
  - API failures
  - Data corruption
  → File: error.log (permanent retention)
  → Alerting: PagerDuty (immediate)
  → Incident tracking: Jira

CRITICAL (system down):
  - VD process crash
  - Data loss
  - Security breach
  → File: critical.log (permanent retention)
  → Alerting: PagerDuty (immediate, escalate to on-call)
  → Incident tracking: Jira (high priority)
```

**Structured Log Format (JSON):**
```json
{
  "timestamp": "2025-11-01T14:32:45.123Z",
  "level": "INFO",
  "component": "vd_validation",
  "event": "validation_complete",
  "message": "Code validation passed with score 87/100",
  "context": {
    "project_id": "proj_abc123",
    "task_id": "task_xyz789",
    "file": "src/auth/middleware.ts",
    "user_id": "user_456"
  },
  "metrics": {
    "validation_score": 87,
    "duration_ms": 1234,
    "tokens_analyzed": 2500
  },
  "metadata": {
    "vd_model": "llama-3.1-70b",
    "hardware": "rtx_4090",
    "obra_version": "0.2.1"
  }
}
```

**Specialized Log Streams:**

**Project Logs (High-Level):**
```json
{
  "stream": "project",
  "event": "feature_completed",
  "feature": "user_authentication",
  "duration_minutes": 45,
  "files_changed": 12,
  "tests_added": 24,
  "cost_usd": 1.47
}
```

**VD Decision Logs:**
```json
{
  "stream": "vd_decision",
  "decision_type": "routing",
  "task_description": "Refactor user service",
  "decision": "route_to_rai",
  "reasoning": "Task complexity score 68 exceeds VD-only threshold of 40",
  "rai_model_selected": "claude-sonnet-4",
  "estimated_tokens": 4500,
  "estimated_cost": 0.09
}
```

**rAI Interaction Logs:**
```json
{
  "stream": "rai_interaction",
  "provider": "anthropic",
  "model": "claude-sonnet-4",
  "request": {
    "prompt_tokens": 3500,
    "max_tokens": 2000,
    "temperature": 0.3,
    "prompt_hash": "sha256:abc...",  // Full prompt in separate secure log
    "request_id": "req_123"
  },
  "response": {
    "completion_tokens": 1847,
    "total_tokens": 5347,
    "latency_ms": 8234,
    "cost_usd": 0.107,
    "response_hash": "sha256:def..."  // Full response in separate log
  }
}
```

**System Performance Logs:**
```json
{
  "stream": "system_metrics",
  "cpu_usage_percent": 45.3,
  "ram_usage_gb": 18.2,
  "gpu_usage_percent": 78.5,
  "gpu_temp_celsius": 72,
  "vram_usage_gb": 22.1,
  "disk_io_mbps": 450,
  "network_latency_ms": 12
}
```

#### Log Management:

**Rotation & Compression:**
- Rotate daily at midnight UTC
- Compress logs older than 7 days (gzip, ~10:1 ratio)
- Archive to object storage (S3/GCS) after 30 days
- Delete DEBUG logs after 7 days
- Retain ERROR/CRITICAL permanently

**Search & Query (P1):**
- Index logs in Elasticsearch / OpenSearch
- Support queries like:
  ```
  "Find all validation failures for project X in last 7 days"
  "Show escalations that resulted in human intervention"
  "List all rAI calls exceeding $0.50"
  ```
- Build dashboards in Kibana / Grafana

**Privacy & Security:**
- Sanitize PII before logging (emails, names, IP addresses)
- Encrypt logs at rest (AES-256)
- Separate sensitive logs (full prompts/responses) with restricted access
- GDPR compliance: Support data export and deletion requests

#### LLM-Optimized Logging:

**Key Principle:** Logs should be easily parseable by VD for self-diagnosis

**Log Analysis Agent (P1):**
```python
def analyze_logs_for_issue(issue_description):
    """VD analyzes logs to diagnose problems"""
    
    # Step 1: Retrieve relevant logs
    relevant_logs = query_logs(
        keywords=extract_keywords(issue_description),
        time_range="last_hour",
        log_levels=["WARNING", "ERROR", "CRITICAL"]
    )
    
    # Step 2: VD processes logs
    vd_prompt = f"""
    Analyze these logs to diagnose the issue: {issue_description}
    
    Logs:
    {json.dumps(relevant_logs, indent=2)}
    
    Provide:
    1. Root cause analysis
    2. Affected components
    3. Recommended fixes
    4. Prevention measures
    """
    
    diagnosis = vd_model.generate(vd_prompt)
    
    # Step 3: Generate actionable report
    return {
        "root_cause": diagnosis.root_cause,
        "impact": diagnosis.impact,
        "fixes": diagnosis.recommended_fixes,
        "prevention": diagnosis.prevention_measures
    }
```

**Automatic Log Summarization:**
- VD generates daily summaries of key events
- Highlights anomalies and trends
- Surfaces actionable insights
- Example:
  ```
  Daily Summary (2025-11-01):
  - 47 tasks completed (avg 12 min each)
  - 3 escalations (all resolved at Level 2)
  - API costs: $12.34 (12% under budget)
  - Notable: Validation scores declined 8% for TypeScript files
    → Recommendation: Update TypeScript linting rules
  ```

---

#### OpenTelemetry Integration **[P1]**
**Description:** Industry-standard distributed tracing and observability

**Why OpenTelemetry:**
- Vendor-neutral standard (works with Datadog, New Relic, Jaeger, Tempo, etc.)
- Unified tracing, metrics, and logs
- Automatic instrumentation for common frameworks
- Rich ecosystem and community support

**Implementation:**

```python
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

class ObservabilitySetup:
    """Initialize OpenTelemetry for Obra"""

    def __init__(self, service_name: str, otlp_endpoint: str):
        # Define service resource
        resource = Resource.create({
            "service.name": service_name,
            "service.version": get_obra_version(),
            "deployment.environment": get_environment(),  # prod, staging, dev
            "host.name": socket.gethostname()
        })

        # Set up tracing
        trace_provider = TracerProvider(resource=resource)
        trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        trace.set_tracer_provider(trace_provider)

        # Set up metrics
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=otlp_endpoint),
            export_interval_millis=60000  # Export every 60 seconds
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # Auto-instrument frameworks
        FastAPIInstrumentor().instrument()  # Instrument web API
        RequestsInstrumentor().instrument()  # Instrument HTTP clients
        Psycopg2Instrumentor().instrument()  # Instrument database

        # Create tracer and meter for custom instrumentation
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)

        # Create custom metrics
        self._create_custom_metrics()

    def _create_custom_metrics(self):
        """Define Obra-specific metrics"""
        self.task_counter = self.meter.create_counter(
            name="obra.tasks.total",
            description="Total number of tasks processed",
            unit="1"
        )

        self.task_duration = self.meter.create_histogram(
            name="obra.tasks.duration",
            description="Task execution duration",
            unit="ms"
        )

        self.validation_score = self.meter.create_histogram(
            name="obra.validation.score",
            description="Validation score distribution",
            unit="1"
        )

        self.api_cost = self.meter.create_histogram(
            name="obra.api.cost",
            description="API cost per task",
            unit="USD"
        )

        self.rai_tokens = self.meter.create_histogram(
            name="obra.rai.tokens",
            description="Remote AI tokens used",
            unit="1"
        )

# Initialize observability
observability = ObservabilitySetup(
    service_name="obra-orchestrator",
    otlp_endpoint="localhost:4317"  # Or cloud provider endpoint
)
```

**Distributed Tracing for Task Execution:**

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

def execute_task_with_tracing(task: Task):
    """Execute task with full distributed tracing"""

    # Create root span for entire task
    with tracer.start_as_current_span(
        "execute_task",
        attributes={
            "task.id": task.id,
            "task.type": task.type,
            "task.intent": task.intent[:100],  # Truncate for safety
            "project.id": task.project_id,
            "user.id": task.user_id
        }
    ) as task_span:
        try:
            # Step 1: Route task
            with tracer.start_as_current_span("route_task") as route_span:
                route, provider = route_task(task, project_context, budget)
                route_span.set_attributes({
                    "route.decision": route.value,
                    "route.provider": provider or "none"
                })

            # Step 2: Generate prompt
            with tracer.start_as_current_span("generate_prompt") as prompt_span:
                prompt = generate_prompt(task, project_context)
                prompt_span.set_attributes({
                    "prompt.length": len(prompt),
                    "prompt.tokens": estimate_tokens(prompt)
                })

            # Step 3: Call rAI
            if route in [Route.RAI_WITH_VD_VALIDATION, Route.VD_CHUNKED_RAI]:
                with tracer.start_as_current_span(
                    "rai_generation",
                    attributes={
                        "rai.provider": provider,
                        "rai.model": get_model_name(provider)
                    }
                ) as rai_span:
                    start_time = time.time()
                    response = call_rai_api(provider, prompt)
                    duration_ms = (time.time() - start_time) * 1000

                    rai_span.set_attributes({
                        "rai.tokens_used": response.usage.total_tokens,
                        "rai.cost_usd": calculate_cost(response),
                        "rai.duration_ms": duration_ms
                    })

                    # Record metrics
                    observability.rai_tokens.record(
                        response.usage.total_tokens,
                        {"provider": provider}
                    )
                    observability.api_cost.record(
                        calculate_cost(response),
                        {"provider": provider}
                    )

            # Step 4: VD validation
            with tracer.start_as_current_span("vd_validation") as validation_span:
                validation_result = validate_with_vd(response.content, task)
                validation_span.set_attributes({
                    "validation.score": validation_result.overall_score,
                    "validation.decision": validation_result.decision,
                    "validation.confidence": validation_result.confidence
                })

                # Record validation score
                observability.validation_score.record(
                    validation_result.overall_score,
                    {"task_type": task.type}
                )

            # Step 5: Run tests
            if validation_result.decision == "APPROVE_FOR_TESTING":
                with tracer.start_as_current_span("run_tests") as test_span:
                    test_results = run_tests(task)
                    test_span.set_attributes({
                        "tests.total": test_results.total,
                        "tests.passed": test_results.passed,
                        "tests.failed": test_results.failed,
                        "tests.duration_ms": test_results.duration_ms
                    })

            # Mark task as successful
            task_span.set_status(Status(StatusCode.OK))
            task_span.set_attribute("task.outcome", "success")

            # Record task completion
            observability.task_counter.add(1, {"outcome": "success", "type": task.type})
            observability.task_duration.record(
                (time.time() - task.start_time) * 1000,
                {"type": task.type}
            )

        except Exception as e:
            # Record error in span
            task_span.set_status(Status(StatusCode.ERROR, str(e)))
            task_span.record_exception(e)
            task_span.set_attribute("task.outcome", "error")

            # Record failed task
            observability.task_counter.add(1, {"outcome": "error", "type": task.type})

            raise
```

**Trace Visualization Benefits:**

When viewing in Jaeger/Tempo/Datadog, you'll see:
```
execute_task (2.3s) ──┬─── route_task (12ms)
                      ├─── generate_prompt (45ms)
                      ├─── rai_generation (1.8s) ← Identify bottleneck!
                      ├─── vd_validation (320ms)
                      └─── run_tests (450ms)
```

**Correlation with Logs:**

```python
import logging
from opentelemetry.trace import get_current_span

# Create logger that automatically includes trace context
logger = logging.getLogger(__name__)

def log_with_trace_context(message: str, level: str = "INFO"):
    """Log with trace ID for correlation"""
    span = get_current_span()
    span_context = span.get_span_context()

    extra_fields = {
        "trace_id": format(span_context.trace_id, '032x'),
        "span_id": format(span_context.span_id, '016x')
    }

    logger.log(getattr(logging, level), message, extra=extra_fields)

# Usage:
log_with_trace_context("Starting validation", "INFO")
# Log output: {"msg": "Starting validation", "trace_id": "...", "span_id": "..."}
```

Now in your observability platform, you can:
1. See a trace in Jaeger showing slow rAI call
2. Click on the span to see all logs with matching trace_id
3. Drill down into exact request/response that caused the issue

**Baggage for Cross-Service Context:**

```python
from opentelemetry.baggage import set_baggage, get_baggage

# Propagate task context across all services
set_baggage("task.id", task.id)
set_baggage("project.id", task.project_id)
set_baggage("user.id", task.user_id)

# Any downstream service can access:
task_id = get_baggage("task.id")
```

**Sampling for Cost Control:**

```python
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased

# Sample only 10% of traces in production (reduce storage costs)
sampler = ParentBasedTraceIdRatioBased(0.1)

# Always sample errors and slow requests
class SmartSampler:
    def should_sample(self, context, trace_id, name, attributes):
        # Always sample errors
        if attributes.get("error"):
            return RECORD_AND_SAMPLE

        # Always sample slow requests (>5s)
        if attributes.get("duration_ms", 0) > 5000:
            return RECORD_AND_SAMPLE

        # Otherwise use probabilistic sampling
        return sampler.should_sample(context, trace_id, name, attributes)
```

---

### 4.2 Metrics & Reporting **[P0 → P1]**
**Description:** Comprehensive metrics tracking Obra value and project health

#### Core Metrics Framework:

**Category 1: Cost Metrics (P0)**

**API Cost Tracking:**
```json
{
  "cost_metrics": {
    "total_api_spend_usd": 234.56,
    "vd_local_cost_usd": 45.20,  // Estimated based on hardware amortization
    "rai_remote_cost_usd": 189.36,
    "breakdown_by_provider": {
      "anthropic": 120.45,
      "openai": 68.91
    },
    "breakdown_by_model": {
      "claude-sonnet-4": 98.23,
      "claude-opus-4": 22.22,
      "gpt-4-turbo": 68.91
    },
    "breakdown_by_task_type": {
      "code_generation": 145.67,
      "refactoring": 23.45,
      "documentation": 11.23,
      "testing": 9.01
    },
    "cost_per_task": 2.34,
    "cost_per_loc": 0.023,
    "cost_per_feature": 23.45
  }
}
```

**Cost Savings Analysis:**
```json
{
  "savings_analysis": {
    "baseline_all_rai_cost": 756.80,  // Estimated if no VD
    "actual_cost_with_vd": 234.56,
    "absolute_savings": 522.24,
    "savings_percentage": 69,
    "roi_months": 0.5,  // Payback period for Obra subscription
    
    "breakdown": {
      "vd_validation_savings": {
        "tasks_validated_locally": 145,
        "estimated_rai_cost_if_remote": 420.30,
        "actual_vd_cost": 35.20,
        "savings": 385.10
      },
      "early_error_detection_savings": {
        "bugs_caught_by_vd": 23,
        "rai_calls_prevented": 46,  // Would have taken multiple attempts
        "estimated_cost_prevented": 137.14
      }
    }
  }
}
```

**Budget Management:**
```json
{
  "budget_status": {
    "daily_budget_usd": 50.00,
    "daily_spent": 23.45,
    "remaining": 26.55,
    "projected_end_of_day": 34.20,
    "alert": "on_track",
    
    "monthly_budget_usd": 1000.00,
    "monthly_spent": 456.78,
    "remaining": 543.22,
    "days_remaining": 16,
    "projected_end_of_month": 878.45,
    "alert": "on_track",
    
    "per_developer_budget": 50.00,
    "developers": [
      {"name": "Alice", "spent": 145.67, "status": "on_track"},
      {"name": "Bob", "spent": 234.56, "status": "over_budget"}
    ]
  }
}
```

---

**Category 2: Productivity Metrics (P0)**

**Task Completion Metrics:**
```json
{
  "productivity_metrics": {
    "tasks_completed": 187,
    "avg_task_duration_minutes": 12.5,
    "median_task_duration_minutes": 8.3,
    "tasks_in_progress": 5,
    "tasks_blocked": 2,
    
    "feature_cycle_time": {
      "avg_hours": 4.2,
      "median_hours": 3.1,
      "baseline_without_obra_hours": 7.5,
      "improvement_percentage": 44
    },
    
    "developer_idle_time": {
      "avg_minutes_per_day": 45,
      "baseline_without_obra": 120,
      "improvement_percentage": 62.5,
      "time_reclaimed_hours_per_week": 6.25
    },
    
    "prompt_iterations": {
      "avg_per_task": 2.1,
      "baseline_without_vd": 8.3,
      "improvement_percentage": 74.7
    }
  }
}
```

**Developer Activity Tracking:**
```json
{
  "developer_metrics": {
    "developer": "Alice",
    "tasks_submitted": 45,
    "tasks_approved_first_attempt": 38,
    "tasks_requiring_refinement": 7,
    "avg_approval_time_minutes": 15,
    "manual_corrections_made": 3,
    "satisfaction_score": 4.2  // /5, from surveys
  }
}
```

---

**Category 3: Quality Metrics (P1)**

**Code Quality Tracking:**
```json
{
  "quality_metrics": {
    "test_pass_rate": 96.5,
    "test_count": 1234,
    "test_coverage_percentage": 87,
    
    "code_review_metrics": {
      "rejection_rate": 8.5,  // % of PRs requiring changes
      "avg_review_comments": 2.3,
      "common_issues": [
        {"issue": "Missing edge case handling", "count": 12},
        {"issue": "Type annotation missing", "count": 8}
      ]
    },
    
    "bug_rate_per_kloc": 1.2,
    "ai_generated_bug_rate": 1.4,
    "human_written_bug_rate": 1.1,
    "relative_quality": 0.93,  // AI/human ratio, >1 is worse
    
    "production_incidents": {
      "total": 3,
      "attributed_to_ai_code": 1,
      "attributed_to_human_code": 2
    },
    
    "linting_issues": {
      "total": 234,
      "critical": 2,
      "high": 15,
      "medium": 67,
      "low": 150
    }
  }
}
```

**VD Performance Metrics:**
```json
{
  "vd_performance": {
    "validation_accuracy": {
      "true_positives": 234,  // Correctly flagged issues
      "false_positives": 12,  // Incorrectly flagged valid code
      "true_negatives": 890,  // Correctly approved good code
      "false_negatives": 5,   // Missed issues that caused bugs
      "precision": 0.95,
      "recall": 0.98,
      "f1_score": 0.96
    },
    
    "escalation_metrics": {
      "total_escalations": 45,
      "level_1": 25,
      "level_2": 15,
      "level_3": 3,
      "level_4_human": 2,
      "escalation_rate": 0.24,  // % of tasks escalated
      "avg_cost_per_escalation": 0.47
    },
    
    "routing_efficiency": {
      "vd_only_tasks": 145,
      "rai_tasks": 187,
      "hybrid_tasks": 45,
      "misrouted_tasks": 8,  // Should have gone to different path
      "routing_accuracy": 0.96
    }
  }
}
```

---

**Category 4: Design Quality Metrics (P1)**

**Task Clarity Assessment:**
```json
{
  "design_quality": {
    "task_clarity_score": 78,  // VD scores each task's clarity
    "tasks_requiring_clarification": 12,
    "avg_clarification_rounds": 1.2,
    
    "task_decomposition": {
      "avg_subtasks_per_task": 3.4,
      "tasks_decomposed_well": 87,  // VD subjective assessment
      "tasks_poorly_decomposed": 13,
      "common_issues": [
        "Task too broad, required 5+ subtasks",
        "Missing acceptance criteria",
        "Unclear dependencies"
      ]
    },
    
    "chunking_optimization": {
      "avg_tokens_per_rai_call": 4500,
      "optimal_range": [2000, 8000],
      "tasks_within_optimal": 0.89,
      "tasks_too_small": 0.05,  // Inefficient, multiple calls needed
      "tasks_too_large": 0.06   // Context overflow risk
    },
    
    "rework_rate": {
      "tasks_requiring_rework": 18,
      "rework_percentage": 9.6,
      "common_rework_reasons": [
        "Requirements changed",
        "Missed edge case in design",
        "Integration issues"
      ]
    }
  }
}
```

---

#### Automated Reporting (P1):

**Daily Digest (Email/Slack):**
```
Obra Daily Report - 2025-11-01

✅ 47 tasks completed (avg 12 min each)
💰 $23.45 spent (47% of daily budget)
🎯 96% test pass rate
⚠️ 3 escalations (all resolved)

Top Accomplishments:
- User authentication feature (45 min, $1.47)
- Refactored payment service (32 min, $0.89)
- Generated API documentation (8 min, $0.12)

Attention Needed:
- TypeScript validation scores down 8%
  → Recommendation: Update linting rules

Cost Savings Today: $67.80 vs baseline
Time Saved: 2.3 developer hours
```

**Weekly Summary (Dashboard/PDF):**
```markdown
# Obra Weekly Report
**Week of Oct 28 - Nov 1, 2025**

## Executive Summary
- **Productivity:** 187 tasks completed, 44% faster than baseline
- **Cost:** $234.56 spent, 69% savings vs all-rAI
- **Quality:** 96.5% test pass rate, 1.2 bugs/kloc

## Key Metrics
| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Tasks Completed | 187 | 156 | +20% |
| Avg Task Time | 12.5 min | 15.2 min | -18% |
| API Costs | $234.56 | $289.45 | -19% |
| Test Pass Rate | 96.5% | 94.8% | +1.7% |

## Cost Analysis
- Total spend: $234.56
- Savings vs baseline: $522.24 (69%)
- ROI: Obra subscription paid back in 0.5 months

## Top Features Delivered
1. User authentication system (4.2 hours, $23.45)
2. Payment processing refactor (3.1 hours, $18.67)
3. Admin dashboard v2 (5.5 hours, $34.23)

## Areas for Improvement
- Escalation rate increased to 24% (target: <15%)
  → Root cause: Complex TypeScript types
  → Action: Enhance VD type validation module
```

**Milestone Reports (Generated on demand):**
```markdown
# Feature Delivery Retrospective
**Feature:** User Authentication System  
**Completion Date:** 2025-11-01  
**Duration:** 4.2 hours  
**Cost:** $23.45  

## Breakdown
- Planning & Design: 0.5 hours, $2.34
- Code Generation: 2.1 hours, $12.45
- Testing: 1.0 hours, $5.67
- Debugging: 0.4 hours, $1.89
- Documentation: 0.2 hours, $1.10

## Quality Metrics
- Test coverage: 92%
- Bug rate: 0.8/kloc
- Code review: Approved with 2 minor comments

## Lessons Learned
- OAuth library integration required 2 escalations
- VD validation caught 5 bugs before testing
- Parallel test execution saved 30 minutes

## Recommendations
- Add OAuth patterns to VD knowledge base
- Update prompt templates for auth tasks
```

---

### 4.3 Real-Time Dashboard **[P2]**
**Description:** Visual interface for project monitoring (Future)

#### Dashboard Components:

**1. Project Health Overview:**
- Status indicators: On track / At risk / Blocked
- Progress bar: % complete by LOC or tasks
- ETA to next milestone
- Current sprint/week velocity

**2. Hierarchical Task View:**
```
📁 Project: E-commerce Platform
  ├── 🎯 Epic: User Authentication [80% complete]
  │   ├── ✅ Task: OAuth integration [Complete]
  │   ├── 🔄 Task: Session management [In Progress]
  │   │   ├── ✅ Design [Complete]
  │   │   ├── ✅ Implementation [Complete]
  │   │   ├── ✅ Unit tests [Complete]
  │   │   ├── 🔄 Integration tests [Running]
  │   │   └── ⏳ Deployment [Pending]
  │   └── ⏳ Task: Password reset flow [Pending]
  ├── 🎯 Epic: Payment Processing [40% complete]
  │   └── ...
```

**3. Agent Activity Monitor:**
```
🤖 Active Agents (5/10 slots used):

Coding Agent #1 [GPU: 78%]
  └─ Implementing payment service refactor (12 min elapsed)

Testing Agent #2 [CPU: 45%]
  └─ Running integration tests (234/500 tests complete)

Testing Agent #3 [CPU: 52%]
  └─ Running unit tests (890/1200 tests complete)

Documentation Agent [CPU: 12%]
  └─ Generating API docs for auth module (3 min elapsed)

VD Coordinator [CPU: 34%, GPU: 65%]
  └─ Validating payment service code (score: 82/100)
```

**4. Cost & Budget Tracker:**
```
Daily Budget: $50.00
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫ $23.45 / $50.00
47% used, $26.55 remaining

Monthly Budget: $1,000.00
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫ $456.78 / $1,000.00
46% used, 16 days remaining, projected: $878.45

Savings vs Baseline: $522.24 (69%)
```

**5. Quality Metrics Card:**
```
📊 Quality Metrics

Test Pass Rate: 96.5% ▲ +1.7%
Code Coverage: 87% ▬ 0%
Bug Rate: 1.2/kloc ▼ -0.3
VD Validation Accuracy: 95% ▲ +2%
```

**6. System Resources:**
```
💻 Hardware Utilization

CPU: [████████░░] 78% (24 cores)
GPU: [██████████] 92% (RTX 4090)
VRAM: [████████░░] 78% (19GB / 24GB)
RAM: [█████░░░░░] 52% (32GB / 64GB)
Disk I/O: [███░░░░░░░] 34% (450 MB/s)
```

**7. Recent Activity Log:**
```
🕐 Recent Events

14:32:45 ✅ Validation passed: auth/middleware.ts (score: 87)
14:31:23 🔄 Started: Integration tests for auth module
14:29:18 ⚠️ Escalation (L1): Type error in payment/service.ts
14:27:05 💰 Cost alert: 50% of daily budget used
14:25:42 ✅ Completed: User login endpoint (12 min, $0.89)
14:23:10 🔄 Started: Password reset flow
```

**8. Alerts & Notifications:**
```
⚠️ Active Alerts (2)

🔴 MEDIUM: TypeScript validation scores declined 8%
   → Recommendation: Update linting rules

🟡 LOW: Approaching 50% of daily budget ($25/$50)
   → Current pace: $34.20 by end of day
```

---

### 4.4 Notifications & Alerting **[P0 → P1]**
**Description:** Multi-channel notification system for task updates and critical events

#### Notification Channels **[P1]**

**Supported Integrations:**

**1. Slack Integration:**
```python
class SlackNotifier:
    """Send notifications to Slack channels"""

    def __init__(self, webhook_url: str, default_channel: str):
        self.webhook = webhook_url
        self.channel = default_channel

    def notify_task_complete(self, task: Task):
        """Notify when task completes successfully"""
        message = {
            "channel": task.slack_channel or self.channel,
            "username": "Obra",
            "icon_emoji": ":robot_face:",
            "attachments": [{
                "color": "good",  # Green
                "title": f"✅ Task Complete: {task.intent}",
                "fields": [
                    {"title": "Validation Score", "value": f"{task.validation_score}/100", "short": True},
                    {"title": "Cost", "value": f"${task.cost:.2f}", "short": True},
                    {"title": "Time", "value": f"{task.duration:.1f} minutes", "short": True},
                    {"title": "Files Changed", "value": str(len(task.files_modified)), "short": True}
                ],
                "actions": [
                    {"type": "button", "text": "View Diff", "url": task.diff_url},
                    {"type": "button", "text": "Approve", "url": task.approval_url, "style": "primary"},
                    {"type": "button", "text": "Request Changes", "url": task.reject_url}
                ],
                "footer": f"Task ID: {task.id}",
                "ts": int(task.completed_at.timestamp())
            }]
        }
        self._send(message)

    def notify_task_failed(self, task: Task, error: str):
        """Notify when task fails or escalates"""
        message = {
            "channel": task.slack_channel or self.channel,
            "username": "Obra",
            "icon_emoji": ":warning:",
            "attachments": [{
                "color": "danger",  # Red
                "title": f"❌ Task Failed: {task.intent}",
                "text": f"Error: {error}",
                "fields": [
                    {"title": "Attempts", "value": str(task.attempt_count), "short": True},
                    {"title": "Last Score", "value": f"{task.last_validation_score}/100", "short": True},
                    {"title": "Cost So Far", "value": f"${task.cumulative_cost:.2f}", "short": True}
                ],
                "actions": [
                    {"type": "button", "text": "View Logs", "url": task.logs_url},
                    {"type": "button", "text": "Retry Manually", "url": task.retry_url}
                ],
                "footer": f"Task ID: {task.id} | Escalated to: {task.assigned_developer}",
                "ts": int(task.failed_at.timestamp())
            }]
        }
        self._send(message)

    def notify_budget_alert(self, budget_info: BudgetInfo):
        """Alert when budget threshold reached"""
        percent_used = (budget_info.spent / budget_info.limit) * 100
        color = "danger" if percent_used >= 90 else "warning"

        message = {
            "channel": budget_info.alert_channel or self.channel,
            "username": "Obra",
            "icon_emoji": ":money_with_wings:",
            "attachments": [{
                "color": color,
                "title": f"⚠️ Budget Alert: {percent_used:.0f}% Used",
                "text": f"${budget_info.spent:.2f} of ${budget_info.limit:.2f} daily budget consumed",
                "fields": [
                    {"title": "Remaining", "value": f"${budget_info.remaining:.2f}", "short": True},
                    {"title": "Projected End-of-Day", "value": f"${budget_info.projected_total:.2f}", "short": True}
                ],
                "footer": "Obra will auto-pause when limit reached"
            }]
        }
        self._send(message)

    def _send(self, message: dict):
        """Send message via webhook"""
        try:
            response = requests.post(
                self.webhook,
                json=message,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack notification: {e}")
```

**2. Email Notifications:**
```python
class EmailNotifier:
    """Send email notifications for critical events"""

    def __init__(self, smtp_config: SMTPConfig):
        self.smtp = smtp_config

    def send_weekly_summary(self, user_email: str, summary: WeeklySummary):
        """Send weekly summary report"""
        html_content = f"""
        <html>
        <head><style>
            body {{ font-family: Arial, sans-serif; }}
            .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f5f5f5; border-radius: 5px; }}
            .metric-value {{ font-size: 32px; font-weight: bold; color: #333; }}
            .metric-label {{ font-size: 14px; color: #666; }}
            .success {{ color: #28a745; }}
            .warning {{ color: #ffc107; }}
            .danger {{ color: #dc3545; }}
        </style></head>
        <body>
            <h2>Obra Weekly Summary</h2>
            <p>Week of {summary.week_start.strftime('%B %d, %Y')}</p>

            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{summary.tasks_completed}</div>
                    <div class="metric-label">Tasks Completed</div>
                </div>
                <div class="metric">
                    <div class="metric-value success">${summary.cost_savings:.0f}</div>
                    <div class="metric-label">Cost Savings vs Manual</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary.avg_validation_score:.0f}/100</div>
                    <div class="metric-label">Avg Validation Score</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary.time_saved:.0f} hrs</div>
                    <div class="metric-label">Developer Time Saved</div>
                </div>
            </div>

            <h3>Top Features Delivered</h3>
            <ul>
                {"".join(f"<li>{feature}</li>" for feature in summary.top_features[:5])}
            </ul>

            <h3>Cost Breakdown</h3>
            <ul>
                <li>rAI API Costs: ${summary.rai_costs:.2f}</li>
                <li>VD Compute: ${summary.vd_costs:.2f}</li>
                <li>Total: ${summary.total_costs:.2f}</li>
                <li>Avg Cost per Task: ${summary.avg_cost_per_task:.2f}</li>
            </ul>

            <p><a href="{summary.full_report_url}">View Full Report →</a></p>
        </body>
        </html>
        """

        self._send_email(
            to=user_email,
            subject=f"Obra Weekly Summary - {summary.tasks_completed} tasks completed",
            html_content=html_content
        )
```

**3. Microsoft Teams Integration (P2):**
- Webhook-based notifications similar to Slack
- Adaptive Cards for rich formatting
- Action buttons for task approval

**4. Discord Integration (P2):**
- For developer community / open-source projects
- Webhook notifications to Discord channels

**5. PagerDuty / Opsgenie Integration (P2):**
- Critical alerts for production issues
- Escalation for VD failures
- Incident tracking

---

#### Alert Rules & Triggers **[P0]**

**Alert Severity Levels:**

```python
class AlertSeverity(Enum):
    INFO = "info"          # Informational, no action required
    LOW = "low"            # Minor issue, review when convenient
    MEDIUM = "medium"      # Potential issue, investigate soon
    HIGH = "high"          # Significant issue, investigate now
    CRITICAL = "critical"  # Severe issue, immediate action required

class AlertRule:
    """Define when and how to alert"""

    def __init__(self, name: str, condition: Callable, severity: AlertSeverity):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.cooldown_seconds = 300  # Prevent alert spam
        self.last_triggered = None

    def should_trigger(self, context: dict) -> bool:
        """Check if alert should fire"""
        # Check cooldown
        if self.last_triggered:
            if time.time() - self.last_triggered < self.cooldown_seconds:
                return False

        # Evaluate condition
        if self.condition(context):
            self.last_triggered = time.time()
            return True

        return False

# Pre-defined alert rules
ALERT_RULES = [
    AlertRule(
        name="budget_threshold_80",
        condition=lambda ctx: (ctx['budget_spent'] / ctx['budget_limit']) >= 0.80,
        severity=AlertSeverity.MEDIUM
    ),
    AlertRule(
        name="budget_threshold_95",
        condition=lambda ctx: (ctx['budget_spent'] / ctx['budget_limit']) >= 0.95,
        severity=AlertSeverity.HIGH
    ),
    AlertRule(
        name="validation_score_declining",
        condition=lambda ctx: ctx['avg_validation_score_7d'] < ctx['avg_validation_score_30d'] - 10,
        severity=AlertSeverity.MEDIUM
    ),
    AlertRule(
        name="task_failure_rate_high",
        condition=lambda ctx: (ctx['failed_tasks_1h'] / max(ctx['total_tasks_1h'], 1)) > 0.3,
        severity=AlertSeverity.HIGH
    ),
    AlertRule(
        name="rai_provider_down",
        condition=lambda ctx: ctx['rai_consecutive_failures'] >= 5,
        severity=AlertSeverity.CRITICAL
    ),
    AlertRule(
        name="vd_response_slow",
        condition=lambda ctx: ctx['vd_p95_latency_5m'] > 30.0,  # 30 seconds
        severity=AlertSeverity.MEDIUM
    ),
    AlertRule(
        name="disk_space_low",
        condition=lambda ctx: ctx['disk_free_gb'] < 5.0,
        severity=AlertSeverity.HIGH
    ),
    AlertRule(
        name="gpu_temperature_high",
        condition=lambda ctx: ctx.get('gpu_temp_c', 0) > 85,
        severity=AlertSeverity.MEDIUM
    )
]
```

**Alert Routing:**
```yaml
# .obra/alerts.yaml
routing:
  # Route by severity
  critical:
    channels: [slack, email, pagerduty]
    mentions: ["@channel"]  # Mention everyone

  high:
    channels: [slack, email]
    mentions: ["@eng-leads"]

  medium:
    channels: [slack]
    mentions: []

  low:
    channels: [slack]
    mentions: []

  info:
    channels: []  # Don't send, just log

# Route by event type
events:
  task_complete:
    severity: info
    channels: [slack]
    conditions:
      - validation_score < 75  # Only notify if score is low

  task_failed:
    severity: high
    channels: [slack, email]

  budget_alert:
    severity: medium
    channels: [slack]

  security_vulnerability:
    severity: critical
    channels: [slack, email, pagerduty]

# Quiet hours (P2)
quiet_hours:
  enabled: true
  timezone: "America/Los_Angeles"
  start: "22:00"  # 10 PM
  end: "08:00"    # 8 AM
  suppress_severities: [info, low]  # Still alert for medium+
  weekends: true  # Suppress on weekends too
```

**Alert Aggregation:**
```python
class AlertAggregator:
    """Prevent alert spam by aggregating similar alerts"""

    def __init__(self, window_seconds=300):
        self.window = window_seconds
        self.pending_alerts = []

    def add_alert(self, alert: Alert):
        """Add alert to aggregation buffer"""
        self.pending_alerts.append(alert)

        # Flush if window expired or too many alerts
        if self._should_flush():
            self.flush()

    def _should_flush(self) -> bool:
        if not self.pending_alerts:
            return False

        oldest = self.pending_alerts[0].timestamp
        if time.time() - oldest > self.window:
            return True

        if len(self.pending_alerts) >= 10:
            return True

        return False

    def flush(self):
        """Send aggregated alert"""
        if not self.pending_alerts:
            return

        # Group by type
        grouped = {}
        for alert in self.pending_alerts:
            key = alert.rule_name
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(alert)

        # Send one notification per group
        for rule_name, alerts in grouped.items():
            if len(alerts) == 1:
                # Send individual alert
                send_notification(alerts[0])
            else:
                # Send aggregated alert
                send_notification(self._create_aggregate(rule_name, alerts))

        self.pending_alerts = []

    def _create_aggregate(self, rule_name: str, alerts: list) -> Alert:
        """Create single alert summarizing multiple occurrences"""
        return Alert(
            rule_name=rule_name,
            severity=max(a.severity for a in alerts),
            message=f"{rule_name} triggered {len(alerts)} times in last {self.window}s",
            details={"occurrences": len(alerts), "first": alerts[0].timestamp, "last": alerts[-1].timestamp}
        )
```

---

#### User Preferences **[P1]**

**Per-User Notification Settings:**
```yaml
# User: alice@acme.com
notification_preferences:
  # Channel preferences
  channels:
    slack: true
    email: true
    sms: false

  # Frequency
  real_time_notifications:
    task_complete: false  # Too noisy
    task_failed: true
    budget_alert: true

  daily_summary:
    enabled: true
    time: "09:00"
    timezone: "America/New_York"

  weekly_summary:
    enabled: true
    day: "monday"
    time: "09:00"

  # Filter by project
  projects:
    - name: "main-app"
      notify_all: true
    - name: "experimental-features"
      notify_all: false
      notify_on_failure_only: true

  # Minimum severity to notify
  min_severity: "medium"

  # Quiet hours
  do_not_disturb:
    enabled: true
    start: "20:00"
    end: "08:00"
    emergency_override: true  # Still notify for CRITICAL
```

---

### 4.5 Cost Prediction & Budgeting **[P0 → P1]**
**Description:** Proactive cost estimation and budget management

#### Pre-Task Cost Estimation **[P0]**

```python
class CostPredictor:
    """Predict task cost before execution"""

    def __init__(self, historical_data: pd.DataFrame):
        self.model = self._train_model(historical_data)

    def predict_cost(self, task: Task, project_context: dict) -> CostEstimate:
        """
        Predict cost with confidence interval.

        Returns: (estimated_cost, lower_bound, upper_bound, confidence)
        """
        # Extract features
        features = self._extract_features(task, project_context)

        # Predict using trained model
        predicted_tokens_rai = self.model.predict_rai_tokens(features)
        predicted_tokens_vd = self.model.predict_vd_tokens(features)

        # Calculate cost
        rai_cost = predicted_tokens_rai * get_token_cost(task.rai_provider)
        vd_cost = predicted_tokens_vd * get_token_cost("vd_local")  # Usually near zero
        total_cost = rai_cost + vd_cost

        # Confidence interval (based on historical variance)
        std_dev = self.model.get_prediction_std(features)
        lower = total_cost - (1.96 * std_dev)  # 95% CI
        upper = total_cost + (1.96 * std_dev)

        return CostEstimate(
            estimated_cost=total_cost,
            lower_bound=max(0, lower),
            upper_bound=upper,
            confidence=self.model.get_confidence(features),
            breakdown={
                "rai_tokens": predicted_tokens_rai,
                "rai_cost": rai_cost,
                "vd_tokens": predicted_tokens_vd,
                "vd_cost": vd_cost
            }
        )

    def _extract_features(self, task: Task, project_context: dict) -> np.array:
        """Extract features for ML model"""
        return [
            len(task.intent.split()),  # Intent length
            task.complexity_score,
            len(project_context['relevant_files']),
            sum(len(f) for f in project_context['relevant_files']),  # Total context size
            project_context['language_encoding'],  # Python=0, JS=1, etc.
            task.type_encoding,  # feature=0, bug=1, refactor=2, etc.
            project_context['avg_file_size'],
            project_context['dependency_count'],
            task.has_tests_required,
            task.estimated_output_lines
        ]

    def _train_model(self, historical_data: pd.DataFrame):
        """Train ML model on historical task data"""
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import train_test_split

        X = historical_data[self.feature_columns]
        y_rai = historical_data['actual_rai_tokens']
        y_vd = historical_data['actual_vd_tokens']

        X_train, X_test, y_train, y_test = train_test_split(X, y_rai, test_size=0.2)

        model_rai = GradientBoostingRegressor(n_estimators=100, max_depth=5)
        model_rai.fit(X_train, y_train)

        model_vd = GradientBoostingRegressor(n_estimators=100, max_depth=5)
        model_vd.fit(X_train, y_vd)

        return {"rai": model_rai, "vd": model_vd}
```

**Cost Approval Workflow:**
```python
def submit_task_with_cost_approval(task: Task, user: User) -> TaskSubmission:
    """Require approval for expensive tasks"""

    # Predict cost
    cost_estimate = cost_predictor.predict_cost(task, project_context)

    # Check if approval required
    if cost_estimate.estimated_cost > user.auto_approve_threshold:
        # Show cost estimate to user, require explicit approval
        approval = request_user_approval(
            task=task,
            cost_estimate=cost_estimate,
            message=f"Estimated cost: ${cost_estimate.estimated_cost:.2f} "
                    f"(range: ${cost_estimate.lower_bound:.2f} - ${cost_estimate.upper_bound:.2f})"
        )

        if not approval.approved:
            return TaskSubmission(status="cancelled", reason="User declined due to cost")

    # Check budget availability
    if not budget_manager.has_available_budget(cost_estimate.upper_bound):
        return TaskSubmission(
            status="blocked",
            reason=f"Insufficient budget. Need ${cost_estimate.upper_bound:.2f}, "
                   f"have ${budget_manager.available:.2f}"
        )

    # Proceed with task
    return submit_task(task)
```

---

## 5. TESTING & QUALITY ASSURANCE

### 5.1 Automated Testing Framework **[P0]**
**Description:** Comprehensive testing orchestration with intelligent result interpretation

#### Test Types & Implementation:

**Unit Testing (P0):**

**Test Generation Strategy:**
```python
def generate_unit_tests(function_code, project_context):
    """VD orchestrates unit test generation"""
    
    # Step 1: Analyze function
    function_analysis = vd_analyze_function(function_code)
    # Returns: parameters, return type, dependencies, edge cases
    
    # Step 2: Determine test cases
    test_cases = identify_test_cases(function_analysis)
    # Returns: happy path, error cases, edge cases, boundary values
    
    # Step 3: Generate tests (rAI)
    rai_prompt = f"""
    Generate unit tests for this function:
    
    {function_code}
    
    Test framework: {project_context.test_framework}
    Required test cases: {json.dumps(test_cases)}
    Style guide: {project_context.test_style_guide}
    
    Requirements:
    - Test all identified edge cases
    - Use meaningful test names
    - Include assertions for expected behavior
    - Mock external dependencies
    - Ensure test isolation
    
    Output format: JSON with test code and descriptions
    """
    
    test_code = rai_generate(rai_prompt)
    
    # Step 4: VD validates tests
    validation = vd_validate_tests(test_code, function_code)
    if validation.score < 80:
        # Refine and regenerate
        test_code = refine_tests(test_code, validation.feedback)
    
    return test_code
```

**Test Case Categories:**
```
For function: calculate_discount(price, user_tier, promo_code)

Happy Path:
- Regular user, no promo: 0% discount
- Premium user, no promo: 10% discount  
- Regular user, valid promo: 15% discount
- Premium user, valid promo: 25% discount

Error Cases:
- Negative price → Raise ValueError
- Invalid user_tier → Raise ValueError
- Expired promo code → Return 0% discount
- None/null parameters → Raise TypeError

Edge Cases:
- Price = 0 → Return 0 discount
- Price = MAX_FLOAT → Handle overflow
- Promo code uppercase/lowercase → Case-insensitive
- User tier not in known list → Default to regular

Boundary Values:
- Price = 0.01 (minimum positive)
- Discount = 99.99% (maximum)
- Promo code length = 1 character
- Promo code length = 50 characters
```

**Test Execution:**
- Run tests in isolated environment (Docker container or virtualenv)
- Parallel execution per test file (not per test to avoid conflicts)
- Capture stdout, stderr, exit codes
- Generate coverage reports (line, branch, function coverage)
- Timeout per test file: 60 seconds (configurable)

---

**Integration Testing (P0):**

**Test Strategy:**
```python
def generate_integration_tests(module_interfaces, project_context):
    """Test interactions between modules"""
    
    # Step 1: Identify module dependencies
    dependency_graph = build_dependency_graph(module_interfaces)
    
    # Step 2: Generate interaction test cases
    test_scenarios = []
    for module_a, module_b in dependency_graph.edges():
        # Test data flow from A to B
        scenario = {
            "setup": f"Initialize {module_a} and {module_b}",
            "action": f"Call {module_a}.method() which invokes {module_b}",
            "assertions": [
                f"{module_b} receives correct data",
                f"{module_a} handles {module_b} response correctly",
                f"Error handling works when {module_b} fails"
            ]
        }
        test_scenarios.append(scenario)
    
    # Step 3: Generate test code (rAI)
    integration_tests = rai_generate_integration_tests(test_scenarios)
    
    return integration_tests
```

**Isolation Strategy:**
- Spin up test database (PostgreSQL, MySQL) per test run
- Use test fixtures for consistent state
- Clean up after tests (drop tables, clear caches)
- Mock external APIs (use recorded responses or stubs)

---

**System Testing (P1):**

**End-to-End Test Scenarios:**
```
Scenario: User Registration and Login
1. Navigate to signup page
2. Fill registration form with valid data
3. Submit form
4. Assert: Confirmation email sent
5. Click confirmation link
6. Assert: User account activated
7. Navigate to login page
8. Enter credentials
9. Assert: Dashboard displayed, user session created
```

**Test Execution:**
- Use Selenium/Playwright for UI automation
- Run in headless browser for CI/CD
- Capture screenshots on failures
- Record video of test execution
- Check API responses, database state, UI state

---

**Regression Testing (P0):**

**Strategy:**
- Maintain golden dataset of test cases
- Run full suite after every significant change
- Detect new failures (regressions)
- Compare current results vs baseline
- Auto-bisect to find commit that introduced regression

**Smart Regression Selection (P1):**
```python
def select_regression_tests(changed_files):
    """Run only tests affected by code changes"""
    
    # Step 1: Analyze file changes
    affected_functions = analyze_changes(changed_files)
    
    # Step 2: Map to tests
    test_coverage_map = load_test_coverage_map()
    relevant_tests = []
    for func in affected_functions:
        relevant_tests.extend(test_coverage_map.get_tests_for_function(func))
    
    # Step 3: Add critical path tests (always run)
    relevant_tests.extend(critical_tests)
    
    # Step 4: Prioritize by past failure rate
    relevant_tests.sort(key=lambda t: t.failure_rate, reverse=True)
    
    return relevant_tests
```

---

**Code Coverage Analysis (P1):**

**Coverage Tracking:**
- Instrument code during test runs (using coverage.py, istanbul.js)
- Track line coverage, branch coverage, function coverage
- Generate HTML reports with uncovered lines highlighted
- Set coverage thresholds (e.g., 80% for new code)
- Block PRs if coverage drops below threshold

**Coverage-Driven Test Generation:**
```python
def improve_coverage(project):
    """Generate tests for uncovered code"""
    
    # Step 1: Identify uncovered code
    coverage_report = run_coverage_analysis(project)
    uncovered_functions = coverage_report.get_uncovered_functions()
    
    # Step 2: Generate tests for uncovered code
    new_tests = []
    for func in uncovered_functions:
        tests = generate_unit_tests(func.code, project)
        new_tests.extend(tests)
    
    # Step 3: Validate new tests
    run_tests(new_tests)
    new_coverage = run_coverage_analysis(project)
    
    improvement = new_coverage.percentage - coverage_report.percentage
    print(f"Coverage improved by {improvement}%")
    
    return new_tests
```

---

**Performance Testing (P1):**

**Load Testing:**
```python
def generate_load_tests(api_endpoints, project_context):
    """Generate load tests for APIs"""
    
    load_scenarios = []
    for endpoint in api_endpoints:
        scenario = {
            "endpoint": endpoint.url,
            "method": endpoint.http_method,
            "concurrent_users": [10, 50, 100, 500],
            "duration_seconds": 60,
            "assertions": {
                "avg_response_time_ms": 200,
                "p95_response_time_ms": 500,
                "p99_response_time_ms": 1000,
                "error_rate": 0.01,  # <1%
                "throughput_rps": 100
            }
        }
        load_scenarios.append(scenario)
    
    # Generate Locust / JMeter / k6 test scripts
    load_tests = rai_generate_load_tests(load_scenarios)
    
    return load_tests
```

**Benchmark Tracking:**
- Run performance tests regularly (nightly builds)
- Track metrics over time (response times, throughput, resource usage)
- Alert on performance degradation (>10% regression)
- Store benchmark results in database
- Visualize trends in dashboard

---

**Security Testing (P2):**

**Static Application Security Testing (SAST):**
- Integrate with Snyk, Semgrep, Bandit, etc.
- Scan for known vulnerability patterns
- Check for OWASP Top 10 issues
- Flag insecure dependencies
- Generate security reports

**Dynamic Testing:**
- OWASP ZAP integration for API security scanning
- Fuzz testing for input validation
- Penetration testing (manual or automated with Metasploit)

---

#### VD Test Result Interpretation (P0):

**Key Responsibility:** VD must understand why tests fail and guide debugging

**Failure Analysis Workflow:**
```python
def interpret_test_failure(test_result):
    """VD analyzes test failure and determines next action"""
    
    # Step 1: Parse test output
    failure_info = parse_test_output(test_result.stdout, test_result.stderr)
    # Returns: test name, error message, stack trace, file/line
    
    # Step 2: Categorize failure type
    failure_category = categorize_failure(failure_info)
    # Returns: assertion_error, exception, timeout, syntax_error, etc.
    
    # Step 3: Identify root cause
    root_cause_analysis = vd_diagnose_failure(
        failure_info=failure_info,
        test_code=test_result.test_code,
        implementation_code=test_result.implementation_code,
        recent_changes=test_result.git_diff
    )
    
    # Step 4: Generate fix strategy
    fix_strategy = determine_fix_strategy(root_cause_analysis)
    
    # Step 5: Execute fix
    if fix_strategy.type == "simple":
        # VD can fix directly (e.g., missing import, typo)
        fixed_code = vd_apply_fix(failure_info, fix_strategy)
        return {"action": "retry", "fixed_code": fixed_code}
    
    elif fix_strategy.type == "medium":
        # Need rAI to regenerate section
        prompt = generate_debug_prompt(failure_info, fix_strategy)
        fixed_code = rai_generate(prompt)
        return {"action": "retry", "fixed_code": fixed_code}
    
    elif fix_strategy.type == "complex":
        # Escalate to human
        report = generate_debug_report(failure_info, root_cause_analysis)
        return {"action": "escalate", "report": report}
```

**Failure Categories:**

```
ASSERTION_ERROR:
  - Expected value != actual value
  - Example: assert user.name == "Alice", got "Bob"
  - Root causes: Logic error, incorrect test data, race condition
  - Fix: Correct logic or test assertion

EXCEPTION:
  - Uncaught exception during execution
  - Example: KeyError, AttributeError, NullPointerException
  - Root causes: Missing null checks, incorrect assumptions, invalid input
  - Fix: Add error handling, validate inputs

TIMEOUT:
  - Test exceeded time limit
  - Example: Test ran >60 seconds
  - Root causes: Infinite loop, slow query, deadlock
  - Fix: Optimize algorithm, fix loop condition, add timeout handling

SYNTAX_ERROR:
  - Code doesn't parse
  - Example: SyntaxError: invalid syntax at line 42
  - Root causes: Typo, incomplete refactoring, wrong language version
  - Fix: Correct syntax

IMPORT_ERROR:
  - Missing dependency or wrong import path
  - Example: ModuleNotFoundError: No module named 'requests'
  - Root causes: Missing installation, wrong package name
  - Fix: Add dependency, correct import statement

TYPE_ERROR:
  - Type mismatch
  - Example: Expected int, got str
  - Root causes: Wrong type passed, missing type conversion
  - Fix: Convert types, update type annotations

INTEGRATION_FAILURE:
  - Module interaction failed
  - Example: API returned 500 error
  - Root causes: Missing setup, incorrect API contract, timing issue
  - Fix: Verify module interfaces, add retries, fix setup
```

**Debug Prompt Generation:**
```python
def generate_debug_prompt(failure_info, fix_strategy):
    """Create targeted prompt for rAI to fix issue"""
    
    prompt = f"""
    A test failed with the following error:
    
    Test Name: {failure_info.test_name}
    Error Type: {failure_info.error_type}
    Error Message: {failure_info.error_message}
    Stack Trace:
    {failure_info.stack_trace}
    
    Implementation Code:
    {failure_info.implementation_code}
    
    Test Code:
    {failure_info.test_code}
    
    Root Cause Analysis:
    {fix_strategy.diagnosis}
    
    Your task: Fix the implementation to pass this test.
    
    Requirements:
    - Only modify the implementation, not the test
    - Maintain existing functionality (don't break other tests)
    - Add comments explaining the fix
    - Consider edge cases to prevent similar failures
    
    Output format: JSON with fixed code and explanation
    """
    
    return prompt
```

**Retry Logic:**
- After fix, rerun failed test
- If still fails, escalate (don't loop forever)
- Maximum 3 retry attempts per test failure
- Track retry history for analysis

---

**LLM-Optimized Test Output (P1):**

**Structured Test Results:**
```json
{
  "test_run": {
    "id": "run_abc123",
    "timestamp": "2025-11-01T14:32:45Z",
    "total_tests": 1234,
    "passed": 1189,
    "failed": 45,
    "skipped": 0,
    "duration_seconds": 123.45,
    "coverage_percentage": 87.3
  },
  "failures": [
    {
      "test_name": "test_user_login_with_invalid_credentials",
      "test_file": "tests/auth/test_login.py",
      "line_number": 42,
      "error_type": "AssertionError",
      "error_message": "Expected status code 401, got 500",
      "stack_trace": "...",
      "relevant_code": {
        "implementation_file": "src/auth/login.py",
        "implementation_lines": [45, 46, 47, 48, 49],
        "implementation_code": "def login(username, password):\n    user = User.query.filter_by(username=username).first()\n    if not user:\n        raise Exception('User not found')\n    ..."
      },
      "suggested_causes": [
        "Unhandled exception (Exception instead of custom error)",
        "Missing HTTP error code mapping"
      ],
      "similar_past_failures": [
        {
          "test_name": "test_user_registration_with_duplicate_email",
          "resolution": "Added proper exception handling and HTTP status codes"
        }
      ]
    }
  ],
  "summary": {
    "pass_rate": 96.4,
    "compared_to_last_run": -0.8,
    "critical_failures": 3,
    "flaky_tests_detected": 2,
    "recommendations": [
      "Fix exception handling in login.py line 47",
      "Add integration test for error scenarios",
      "Review HTTP status code mappings across auth module"
    ]
  }
}
```

**Benefits:**
- VD can parse JSON efficiently
- Includes context for debugging
- Suggests probable causes
- Links to similar past issues
- Human-readable summary also included

---

## 6. ENTERPRISE FEATURES

### 6.1 Multi-Tenancy & Isolation **[P1]**
**Description:** Support multiple teams/projects with strict isolation

#### Tenant Architecture:

**Tenant Model:**
```python
class Tenant:
    id: str  # tenant_abc123
    name: str  # "Acme Corp - Engineering"
    plan: str  # "enterprise", "professional", "starter"
    max_seats: int
    active_seats: int
    
    projects: List[Project]
    users: List[User]
    
    billing: BillingInfo
    settings: TenantSettings
    quotas: TenantQuotas
```

**Isolation Guarantees:**

**Data Isolation:**
- Separate database schemas per tenant (PostgreSQL schemas)
- Separate file storage paths (/data/tenant_{id}/)
- Separate VD model instances (no shared state)
- Separate log files and metrics

**Resource Isolation:**
- CPU/GPU quotas per tenant (cgroups, Kubernetes resource limits)
- Memory limits per tenant
- API rate limits per tenant
- Storage quotas

**Network Isolation:**
- Separate VPC/subnets for enterprise tenants (P2)
- Firewall rules per tenant
- Private API endpoints for enterprise

**Security Isolation:**
- Tenant-specific encryption keys
- Separate API tokens/credentials
- Audit logs per tenant (immutable, separate storage)

---

### 6.2 Role-Based Access Control (RBAC) **[P1]**
**Description:** Fine-grained permissions and access controls

#### Role Hierarchy:

**Built-in Roles:**

```
ADMIN:
  - Full access to tenant settings
  - Manage users and roles
  - Configure billing
  - Access all projects
  - View all audit logs
  
PROJECT_OWNER:
  - Create/delete projects
  - Manage project members
  - Configure project settings (VD model, budget)
  - Access project audit logs
  
DEVELOPER:
  - Submit tasks to Obra
  - Review and approve VD outputs
  - Access project code and logs
  - Cannot change project settings
  
VIEWER:
  - Read-only access to projects
  - View metrics and reports
  - Cannot submit tasks or modify code
  
AUDITOR:
  - Read-only access to all projects
  - Access all audit logs
  - Generate compliance reports
  - Cannot modify any data
```

**Custom Roles (P2):**
- Define custom roles with specific permissions
- Example: "Test Engineer" role with test execution but no code modification
- Permission granularity:
  - Project-level: Can access specific projects only
  - Feature-level: Can use specific Obra features
  - Resource-level: Can access specific resources (budgets, models)

**Permission Enforcement:**
```python
@require_permission("project.write")
def submit_task(user, project, task):
    if not user.has_permission("project.write", project):
        raise PermissionError("User lacks write permission")
    
    # Proceed with task submission
    ...

@require_permission("audit.read")
def view_audit_logs(user, tenant):
    if not user.has_permission("audit.read", tenant):
        raise PermissionError("User lacks audit read permission")
    
    # Return audit logs
    ...
```

---

### 6.3 Single Sign-On (SSO) & Identity **[P1]**
**Description:** Enterprise authentication integration

**Supported Protocols:**
- **SAML 2.0:** Integrate with Okta, OneLogin, Azure AD
- **OAuth 2.0 / OpenID Connect:** Google Workspace, Microsoft 365
- **LDAP/Active Directory:** On-prem enterprise directories

**SSO Configuration:**
```yaml
sso:
  enabled: true
  provider: "okta"
  saml_endpoint: "https://acme.okta.com/app/obra/sso/saml"
  entity_id: "https://obra.ai/saml/tenant_abc123"
  certificate: "-----BEGIN CERTIFICATE-----\n..."
  
  # Attribute mapping
  attributes:
    user_id: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"
    email: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
    first_name: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
    last_name: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
    role: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/role"
  
  # Just-in-time (JIT) provisioning
  jit_provisioning: true
  default_role: "developer"
```

**Multi-Factor Authentication (MFA):**
- Support for TOTP (Google Authenticator, Authy)
- SMS-based MFA (via Twilio)
- Hardware tokens (YubiKey, U2F)
- Enforce MFA for admin roles
- Configurable MFA policies per tenant

---

### 6.4 Audit Logging & Compliance **[P1]**
**Description:** Comprehensive audit trails for compliance and security

#### Audit Log Events:

**Authentication Events:**
```json
{
  "event_type": "user.login",
  "timestamp": "2025-11-01T14:32:45.123Z",
  "user_id": "user_123",
  "user_email": "alice@acme.com",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0...",
  "mfa_used": true,
  "success": true
}
```

**Data Access Events:**
```json
{
  "event_type": "data.access",
  "timestamp": "2025-11-01T14:35:12.456Z",
  "user_id": "user_123",
  "resource_type": "project",
  "resource_id": "proj_abc123",
  "action": "read",
  "data_classification": "confidential",
  "success": true
}
```

**Configuration Changes:**
```json
{
  "event_type": "config.change",
  "timestamp": "2025-11-01T14:40:33.789Z",
  "user_id": "user_123",
  "resource_type": "project_settings",
  "resource_id": "proj_abc123",
  "action": "update",
  "changes": {
    "vd_model": {"old": "llama-3.1-8b", "new": "llama-3.1-70b"},
    "daily_budget": {"old": 50.0, "new": 100.0}
  },
  "success": true
}
```

**AI Interactions:**
```json
{
  "event_type": "ai.generation",
  "timestamp": "2025-11-01T14:45:22.111Z",
  "user_id": "user_123",
  "project_id": "proj_abc123",
  "task_id": "task_xyz789",
  "rai_provider": "anthropic",
  "rai_model": "claude-sonnet-4",
  "tokens_used": 5347,
  "cost_usd": 0.107,
  "prompt_hash": "sha256:abc...",
  "response_hash": "sha256:def...",
  "validation_score": 87,
  "approved_by_user": true
}
```

**Data Export/Deletion (GDPR):**
```json
{
  "event_type": "data.export",
  "timestamp": "2025-11-01T15:00:00.000Z",
  "user_id": "user_123",
  "requested_by": "user_123",
  "export_type": "full",  // "full" or "partial"
  "data_types": ["projects", "audit_logs", "user_profile"],
  "export_format": "json",
  "export_location": "s3://exports/user_123_20251101.tar.gz"
}
```

#### Audit Log Management:

**Storage:**
- Write-once, read-many storage (immutable logs)
- Encrypted at rest (AES-256)
- Separate storage from application data (prevent tampering)
- Long-term retention (7 years for SOC 2)

**Access Control:**
- Only AUDITOR role can read audit logs
- System administrators cannot modify logs
- Cryptographic verification of log integrity (digital signatures)

**Search & Reporting:**
- Full-text search across all audit events
- Filter by user, resource, action, date range
- Generate compliance reports (SOC 2, HIPAA, GDPR)
- Export logs in standard formats (JSON, CSV, SIEM)

**Alerting:**
- Real-time alerts for suspicious events:
  - Failed login attempts (5+ in 5 minutes)
  - Privilege escalation attempts
  - Mass data access
  - Configuration changes by unauthorized users
- Integration with SIEM systems (Splunk, DataDog, Elastic Security)

---

### 6.5 Data Residency & Sovereignty **[P1]**
**Description:** Control where data is stored and processed

**Deployment Options:**

**1. Cloud Regions (SaaS):**
```yaml
# Customer selects data region during signup
data_residency:
  region: "eu-west-1"  # EU (Frankfurt)
  
# All data stored and processed in this region:
- Database: eu-west-1
- Object storage: eu-west-1
- VD compute: eu-west-1
- Backups: eu-west-1 (with replication to eu-west-2)

# rAI calls routed to regional endpoints:
- Anthropic EU: https://api.anthropic.com/eu
- OpenAI EU: https://eu.api.openai.com
```

**Supported Regions:**
- **US:** us-east-1 (Virginia), us-west-2 (Oregon)
- **EU:** eu-west-1 (Ireland), eu-central-1 (Frankfurt)
- **UK:** uk-south-1 (London)
- **APAC:** ap-southeast-1 (Singapore), ap-northeast-1 (Tokyo)
- **Canada:** ca-central-1 (Montreal)
- **Australia:** ap-southeast-2 (Sydney)

**2. On-Premises Deployment (Appliance):**
```
Hardware appliance shipped to customer site:
- All data stays within customer network
- No data leaves premises
- Air-gapped mode: VD only, no rAI calls
- Hybrid mode: VD local, rAI via approved proxies
```

**3. Virtual Private Cloud (VPC):**
```
Dedicated VPC within customer's cloud account:
- Customer owns infrastructure
- Obra deployed as managed service
- Data sovereignty guaranteed
- Customer controls network access
```

**Cross-Border Data Transfer:**
- **Disabled by default** for EU/UK customers
- Require explicit consent for data transfer outside region
- Log all cross-border transfers
- Comply with GDPR, CCPA, other regulations

---

### 6.6 Disaster Recovery & Business Continuity **[P1]**
**Description:** Ensure Obra availability and data safety

#### Backup Strategy:

**Automated Backups:**
- **Full backup:** Daily at 2 AM UTC
- **Incremental backup:** Every 6 hours
- **Retention:** 30 daily backups, 12 monthly backups, 7 yearly backups
- **Backup storage:** Separate region from primary (geo-redundant)
- **Encryption:** All backups encrypted (AES-256)

**Backup Verification:**
- Weekly restore tests (automated)
- Monthly disaster recovery drills (manual)
- Verify data integrity (checksums)
- Test recovery time objective (RTO) and recovery point objective (RPO)

**Backup Contents:**
- Database snapshots (PostgreSQL, MySQL)
- File storage (project files, logs)
- VD model weights and configurations
- Application settings and secrets (encrypted)
- Audit logs

**Recovery Procedures:**

**Scenario 1: Single Server Failure**
- **RTO:** 5 minutes
- **RPO:** 0 (no data loss, using replication)
- **Action:** Auto-failover to standby server

**Scenario 2: Data Center Outage**
- **RTO:** 1 hour
- **RPO:** 6 hours (last incremental backup)
- **Action:** Failover to secondary region, restore from backup

**Scenario 3: Data Corruption**
- **RTO:** 2 hours
- **RPO:** 24 hours (last full backup)
- **Action:** Identify corruption point, restore from backup, replay transaction logs

**Scenario 4: Complete Data Loss (Catastrophic)**
- **RTO:** 24 hours
- **RPO:** 24 hours
- **Action:** Rebuild from geo-redundant backups, restore all services

#### High Availability Architecture:

**Database:**
- Primary-replica replication (PostgreSQL streaming replication)
- Automatic failover (Patroni, pg_auto_failover)
- Read replicas for load distribution
- Connection pooling (PgBouncer)

**Application Servers:**
- Load balancer (NGINX, AWS ALB)
- Multiple application instances (Kubernetes, ECS)
- Auto-scaling based on load
- Health checks and automatic restart

**VD Compute:**
- Multi-instance deployment (multiple VD processes)
- Task queue for load distribution (Redis, RabbitMQ)
- Graceful degradation if VD overloaded (queue tasks)

**Storage:**
- Redundant storage (RAID, S3 with versioning)
- Snapshot-based backups
- Cross-region replication

**Network:**
- Redundant network paths
- DDoS protection (Cloudflare, AWS Shield)
- CDN for static assets (Cloudflare, CloudFront)

**Monitoring & Alerting:**
- 24/7 monitoring (Datadog, Prometheus + Grafana)
- Automatic alerts for failures
- On-call rotation for critical issues
- Status page for customers (status.obra.ai)

---

### 6.7 API & Extensibility **[P2]**
**Description:** Allow customers to integrate Obra into custom workflows

#### REST API:

**Authentication:**
```bash
# API key-based authentication
curl -H "Authorization: Bearer obra_sk_abc123..." \
     https://api.obra.ai/v1/projects
```

**Core Endpoints:**

```
POST /v1/projects
  - Create a new project
  - Request: { "name": "My Project", "language": "python", ... }
  - Response: { "project_id": "proj_abc123", ... }

GET /v1/projects/{project_id}
  - Get project details
  - Response: { "id": "proj_abc123", "name": "My Project", "status": "active", ... }

POST /v1/tasks
  - Submit a task to Obra
  - Request: { "project_id": "proj_abc123", "intent": "Add user login", ... }
  - Response: { "task_id": "task_xyz789", "status": "queued", ... }

GET /v1/tasks/{task_id}
  - Get task status
  - Response: { "id": "task_xyz789", "status": "completed", "result": { ... } }

GET /v1/metrics/{project_id}
  - Get project metrics
  - Response: { "cost_usd": 234.56, "tasks_completed": 187, ... }
```

**Webhooks:**
```yaml
webhooks:
  - event: "task.completed"
    url: "https://customer.com/webhook/obra"
    payload:
      {
        "event": "task.completed",
        "task_id": "task_xyz789",
        "project_id": "proj_abc123",
        "result": { ... },
        "timestamp": "2025-11-01T14:32:45Z"
      }
  
  - event: "task.failed"
    url: "https://customer.com/webhook/obra"
  
  - event: "budget.threshold"
    url: "https://customer.com/webhook/obra"
```

**SDK Libraries:**
- **Python:** `pip install obra-sdk`
- **JavaScript/TypeScript:** `npm install @obra/sdk`
- **Go:** `go get github.com/obra-ai/obra-go`

```python
# Python SDK example
from obra import ObraClient

client = ObraClient(api_key="obra_sk_abc123...")

# Create project
project = client.projects.create(name="My Project", language="python")

# Submit task
task = client.tasks.create(
    project_id=project.id,
    intent="Add user authentication with OAuth"
)

# Wait for completion
task.wait_until_complete()

# Get result
print(task.result)
```

#### Plugin System (P3):

**Custom Validation Rules:**
```python
# Customer-defined validation plugin
class CustomSecurityValidator(ObraPlugin):
    def validate(self, code):
        """Run custom security checks"""
        issues = []
        
        # Example: Enforce custom crypto library
        if "from cryptography import" in code:
            issues.append({
                "severity": "high",
                "message": "Must use company-approved crypto library",
                "line": code.index("from cryptography")
            })
        
        return issues

# Register plugin
obra.plugins.register(CustomSecurityValidator())
```

**Custom Test Frameworks:**
```python
# Support for proprietary test frameworks
class CustomTestRunner(ObraPlugin):
    def run_tests(self, test_files):
        """Run tests using custom framework"""
        # Execute tests
        results = custom_framework.run(test_files)
        
        # Convert to Obra format
        return self.convert_results(results)
```

---

### 6.8 Cost Management & Chargebacks **[P1]**
**Description:** Track and allocate costs across teams

#### Cost Allocation:

**Cost Centers:**
```yaml
cost_centers:
  - id: "cc_frontend"
    name: "Frontend Team"
    projects: ["proj_webapp", "proj_mobile"]
    monthly_budget: 500.00
  
  - id: "cc_backend"
    name: "Backend Team"
    projects: ["proj_api", "proj_services"]
    monthly_budget: 1000.00
  
  - id: "cc_ml"
    name: "ML Team"
    projects: ["proj_recommendations", "proj_search"]
    monthly_budget: 2000.00
```

**Chargeback Reports:**
```json
{
  "billing_period": "2025-11",
  "cost_centers": [
    {
      "id": "cc_frontend",
      "name": "Frontend Team",
      "total_cost": 456.78,
      "budget": 500.00,
      "utilization": 0.914,
      "breakdown": {
        "rai_api_costs": 345.67,
        "vd_compute_costs": 89.12,
        "storage_costs": 21.99
      },
      "projects": [
        {
          "id": "proj_webapp",
          "name": "Web App",
          "cost": 289.45
        },
        {
          "id": "proj_mobile",
          "name": "Mobile App",
          "cost": 167.33
        }
      ]
    }
  ]
}
```

**Budget Enforcement:**
- Set hard limits per cost center
- Alert when approaching limit (80%, 90%, 95%)
- Option to pause tasks when budget exceeded
- Automatic budget reset per billing period

**Cost Showback (View-Only):**
- Display costs without enforcement
- Useful for internal transparency
- Generate monthly reports for finance team

---

### 6.9 Service Level Agreements (SLAs) **[P1]**
**Description:** Guaranteed uptime and performance commitments

**Enterprise SLA Tiers:**

**Standard SLA (Included):**
- **Uptime:** 99.5% (43.8 hours downtime/year)
- **Support:** Email support, 24-hour response time
- **RTO:** 4 hours
- **RPO:** 24 hours

**Premium SLA (+$200/month):**
- **Uptime:** 99.9% (8.76 hours downtime/year)
- **Support:** Priority email + chat, 4-hour response time
- **RTO:** 1 hour
- **RPO:** 6 hours
- **Dedicated customer success manager**

**Enterprise SLA (+$500/month):**
- **Uptime:** 99.95% (4.38 hours downtime/year)
- **Support:** 24/7 phone + email + chat, 1-hour response time for critical issues
- **RTO:** 30 minutes
- **RPO:** 1 hour
- **Dedicated technical account manager**
- **Quarterly business reviews**
- **Custom integrations assistance**

**SLA Credits:**
```
Uptime < 99.95% → 10% credit
Uptime < 99.9%  → 25% credit
Uptime < 99.5%  → 50% credit
Uptime < 99.0%  → 100% credit (full refund for month)
```

**Monitoring & Transparency:**
- Public status page: https://status.obra.ai
- Real-time uptime metrics
- Incident post-mortems published
- SLA compliance reports

---

### 6.10 Professional Services **[P2]**
**Description:** Hands-on support for enterprise customers

**Service Offerings:**

**1. Implementation & Onboarding:**
- Dedicated implementation engineer (40 hours)
- Project setup and configuration
- Custom prompt templates for customer codebase
- Integration with customer CI/CD
- Team training (4-hour workshop)
- **Cost:** $15,000

**2. Custom Integration:**
- Connect Obra to proprietary systems
- Custom API development
- Data pipeline setup
- Webhook configuration
- **Cost:** $200/hour (minimum 20 hours)

**3. Workflow Optimization:**
- Analyze customer usage patterns
- Recommend configuration changes
- Optimize prompt templates
- Improve validation accuracy
- **Cost:** $10,000 (one-time)

**4. Dedicated Support:**
- Technical account manager (TAM)
- Weekly check-ins
- Proactive monitoring and recommendations
- Priority bug fixes
- **Cost:** $5,000/month

---

## 7. DEPLOYMENT & OPERATIONS

### 7.1 Deployment Architectures **[P1]**

**Option 1: SaaS (Multi-Tenant)**
```
Architecture:
- Shared infrastructure (Kubernetes cluster)
- Tenant isolation via namespaces
- Shared VD model instances (resource pooling)
- Shared database (separate schemas per tenant)

Pros:
- Lowest cost for customers
- Managed by Obra team
- Automatic updates

Cons:
- Data on Obra infrastructure
- Shared resources (potential noisy neighbor)
```

**Option 2: Single-Tenant Cloud**
```
Architecture:
- Dedicated Kubernetes cluster per customer
- Separate VPC, database, VD instances
- Deployed in customer's cloud account (AWS, GCP, Azure)

Pros:
- Data isolation
- Dedicated resources
- Customer controls infrastructure

Cons:
- Higher cost
- Customer manages infrastructure (or pays for managed service)
```

**Option 3: On-Premises Appliance**
```
Architecture:
- Pre-configured hardware appliance
- Shipped to customer data center
- Self-contained (VD, database, storage)
- Optional: VPN tunnel for remote support

Pros:
- Complete data sovereignty
- Air-gapped operation possible
- Meets strictest compliance requirements

Cons:
- Highest upfront cost
- Customer manages hardware
- Manual updates (or remote managed updates)
```

---

### 7.2 Infrastructure Requirements **[P1]**

**Minimum Requirements (Development):**
- **CPU:** 8 cores (Intel i7 or equivalent)
- **RAM:** 32 GB
- **GPU:** NVIDIA RTX 3060 (12 GB VRAM) or better
- **Storage:** 500 GB SSD
- **Network:** 100 Mbps

**Recommended (Production - 20 users):**
- **CPU:** 24 cores (Intel Xeon or AMD EPYC)
- **RAM:** 128 GB
- **GPU:** NVIDIA RTX 4090 (24 GB VRAM) or A5000
- **Storage:** 2 TB NVMe SSD
- **Network:** 1 Gbps

**Enterprise (Production - 100+ users):**
- **CPU:** 64+ cores (Multi-socket Xeon or EPYC)
- **RAM:** 512 GB+
- **GPU:** 4x NVIDIA A100 (80 GB VRAM each) or 8x RTX 4090
- **Storage:** 10 TB NVMe SSD (RAID 10)
- **Network:** 10 Gbps

**Cloud Equivalents:**
- **AWS:** g5.12xlarge (4x A10G GPUs), p4d.24xlarge (8x A100 GPUs)
- **GCP:** a2-highgpu-4g (4x A100 GPUs)
- **Azure:** NC40ads_A100_v4 (4x A100 GPUs)

---

### 7.3 Monitoring & Alerting **[P1]**

**Metrics Collection:**
- **Prometheus:** Scrape metrics from Obra services
- **Grafana:** Visualize metrics in dashboards
- **Loki:** Centralized log aggregation
- **Jaeger:** Distributed tracing (for debugging performance)

**Key Metrics to Monitor:**
```
System Health:
- CPU, RAM, GPU usage
- Disk I/O, network bandwidth
- VD model inference latency
- rAI API latency and error rates

Application Health:
- Task queue length (backlog)
- Task completion rate (throughput)
- Validation accuracy
- Escalation rate

Business Metrics:
- API costs (total, per tenant, per project)
- Task completion time
- User satisfaction (NPS)
- SLA compliance (uptime)
```

**Alerting Rules:**
```yaml
alerts:
  - name: HighCPUUsage
    condition: cpu_usage > 90% for 5 minutes
    severity: warning
    action: send_slack_notification
  
  - name: VDModelDown
    condition: vd_model_health_check == 0 for 1 minute
    severity: critical
    action: page_oncall_engineer
  
  - name: BudgetThresholdExceeded
    condition: daily_cost > daily_budget * 1.1
    severity: warning
    action: notify_customer
  
  - name: HighEscalationRate
    condition: escalation_rate > 0.30 for 1 hour
    severity: warning
    action: send_slack_notification
```

---

### 7.4 Updates & Maintenance **[P1]**

**Update Strategy:**

**SaaS Customers:**
- Automatic updates (weekly releases)
- Zero-downtime deployments (blue-green, rolling updates)
- Rollback capability if issues detected
- Notify customers of upcoming changes

**On-Premises Customers:**
- Manual updates (or opt-in automatic updates)
- Update packages delivered via secure download
- Update notes with breaking changes
- Support for N-1 version (previous version supported for 6 months)

**Maintenance Windows:**
- Scheduled maintenance: Monthly, announced 1 week in advance
- Emergency maintenance: As needed, announced ASAP
- Duration: Target <30 minutes, maximum 2 hours

**Update Contents:**
- VD model updates (improved validation, new features)
- Prompt template improvements
- Bug fixes and performance optimizations
- Security patches (applied immediately)
- New integrations and features

---

## 8. SECURITY & COMPLIANCE

### 8.1 Security Architecture **[P1]**

**Defense in Depth:**

**Layer 1: Network Security**
- Firewall rules (allow only necessary ports)
- DDoS protection (Cloudflare, AWS Shield)
- VPN for remote access
- Private subnets for backend services

**Layer 2: Application Security**
- Input validation (prevent injection attacks)
- Output encoding (prevent XSS)
- CSRF protection
- Rate limiting (prevent abuse)
- API key rotation

**Layer 3: Data Security**
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Database encryption (PostgreSQL pgcrypto)
- Secrets management (HashiCorp Vault, AWS Secrets Manager)

**Layer 4: Access Control**
- RBAC (Role-Based Access Control)
- SSO integration
- MFA enforcement
- Principle of least privilege
- Regular access reviews

**Layer 5: Monitoring & Detection**
- Intrusion detection (fail2ban, AWS GuardDuty)
- Anomaly detection (unusual access patterns)
- SIEM integration (Splunk, Elastic Security)
- Incident response playbooks

---

### 8.2 Compliance Certifications **[P1 → P2]**

**SOC 2 Type II (P1):**
- Annual audit by third-party firm
- Controls for security, availability, confidentiality
- Demonstrates operational excellence
- Required for most enterprise customers

**ISO 27001 (P2):**
- Information Security Management System (ISMS)
- Broader than SOC 2, covers entire organization
- Internationally recognized standard

**HIPAA (P2):**
- For healthcare customers
- Protects patient health information (PHI)
- Business Associate Agreement (BAA) required
- Specific controls for ePHI

**GDPR (P1):**
- EU data protection regulation
- Data residency in EU region
- Right to access, delete, export data
- Data Processing Agreement (DPA) with customers
- Privacy by design principles

**FedRAMP (P3):**
- For US government customers
- Rigorous security assessment
- Moderate or High impact level
- Continuous monitoring

---

### 8.3 Penetration Testing **[P1]**

**Annual Penetration Tests:**
- Hire external security firm (e.g., Bishop Fox, NCC Group)
- Test all attack surfaces:
  - Web application (Obra dashboard, API)
  - Network infrastructure
  - VD/rAI integration points
  - Customer data storage
- Remediate findings within 30 days
- Re-test critical vulnerabilities
- Publish summary report (with sensitive details redacted)

**Continuous Security Scanning:**
- Automated vulnerability scanning (Qualys, Tenable)
- Dependency scanning (Snyk, Dependabot)
- Container image scanning (Trivy, Clair)
- Infrastructure as Code scanning (Checkov, Terrascan)

---

### 8.4 Incident Response & Runbooks **[P1]**
**Description:** Structured procedures for handling security incidents and operational issues

#### Incident Response Plan (IRP)

**Incident Severity Levels:**

```python
class IncidentSeverity(Enum):
    SEV1_CRITICAL = "sev1"    # Complete service outage, data breach, security compromise
    SEV2_HIGH = "sev2"         # Significant degradation, limited data exposure
    SEV3_MEDIUM = "sev3"       # Partial degradation, minor security issue
    SEV4_LOW = "sev4"          # Minor issue, no customer impact
```

**SEV1 Response (Critical):**
- **Detection:** Automated alerting + on-call paged immediately
- **Response Time:** 15 minutes
- **Communication:** Customer status page updated within 30 minutes
- **Escalation:** VP Engineering notified within 1 hour
- **Post-Mortem:** Required within 72 hours

**SEV2 Response (High):**
- **Detection:** Automated alerting + on-call notified
- **Response Time:** 1 hour
- **Communication:** Status page updated within 2 hours
- **Escalation:** VP Engineering notified if not resolved in 4 hours
- **Post-Mortem:** Recommended

**Incident Response Workflow:**

```
Detection → Assessment → Containment → Eradication → Recovery → Post-Mortem
```

**1. Detection & Assessment (0-15 min):**
```yaml
- Alert fires (Prometheus, PagerDuty, security tool)
- On-call engineer acknowledged
- Initial assessment:
  - What service is affected?
  - How many customers impacted?
  - Is this a security incident?
  - What is the severity?
- Declare incident and create Slack #incident-YYYY-MM-DD channel
- Assign incident commander (IC)
```

**2. Containment (15-60 min):**
```yaml
For Service Outages:
  - Identify root cause (check logs, metrics, traces)
  - Implement temporary fix (rollback, disable feature, scale up)
  - Verify containment (monitoring shows recovery)

For Security Incidents:
  - Isolate affected systems (network segmentation, firewall rules)
  - Preserve evidence (snapshots, logs, memory dumps)
  - Disable compromised credentials
  - Block malicious IPs
```

**3. Eradication (1-4 hours):**
```yaml
For Service Outages:
  - Deploy permanent fix
  - Run full test suite
  - Gradual rollout (canary → 10% → 50% → 100%)

For Security Incidents:
  - Remove malware/backdoors
  - Patch vulnerabilities
  - Reset all credentials
  - Review and close attack vectors
```

**4. Recovery (4-24 hours):**
```yaml
- Restore normal operations
- Validate all services healthy
- Monitor for recurrence
- Update status page: "Incident resolved"
- Thank customers for patience
```

**5. Post-Mortem (72 hours after resolution):**
```markdown
## Incident Post-Mortem Template

**Incident ID:** INC-2025-11-01-001
**Severity:** SEV1
**Duration:** 2 hours 37 minutes
**Impact:** 100% of customers unable to submit tasks

### Timeline
- **14:00 UTC:** Alert fired - rAI provider API returning 503
- **14:15 UTC:** IC declared SEV1, assembled response team
- **14:30 UTC:** Root cause identified - rate limit exceeded
- **14:45 UTC:** Temporary fix deployed - switched to backup provider
- **15:00 UTC:** Service restored, monitoring for stability
- **16:37 UTC:** Permanent fix deployed - improved rate limiting logic

### Root Cause
Obra's rAI request batching logic failed to account for burst traffic patterns,
causing rate limit exhaustion during peak hours.

### Impact
- 100% of customers affected
- 2,347 tasks queued
- Estimated revenue impact: $0 (SLA credits issued)
- Customer trust impact: Medium

### What Went Well
- Fast detection (<5 min from first failure)
- Clear escalation and communication
- Backup provider failover worked as designed

### What Went Wrong
- Rate limiting logic insufficiently tested
- No pre-emptive alerting before hitting limit
- Status page update delayed (45 min)

### Action Items
- [ ] Implement predictive rate limit monitoring (@eng-lead, 2025-11-05)
- [ ] Add integration tests for burst traffic (@qa-lead, 2025-11-08)
- [ ] Automate status page updates (@devops, 2025-11-03)
- [ ] Review all rAI providers' rate limits (@arch-lead, 2025-11-10)
- [ ] Improve runbook for rAI provider failures (@sre, 2025-11-05)

### Lessons Learned
- Defensive coding: Always assume external APIs can fail
- Testing: Simulate failure scenarios regularly (chaos engineering)
- Communication: Automate status updates to reduce manual toil
```

---

#### Operational Runbooks **[P1]**

**Runbook Structure:**

Each runbook follows this template:
```markdown
# Runbook: [Title]

**When to use:** [Triggering condition]
**Severity:** [SEV1/SEV2/SEV3/SEV4]
**Estimated time to resolve:** [X minutes/hours]

## Symptoms
- [Observable behavior indicating this issue]

## Initial Assessment
1. Check [monitoring dashboard/logs]
2. Verify [key metric/health check]
3. Confirm [scope of impact]

## Resolution Steps
### Step 1: [Action]
```bash
# Commands to run
```
**Expected outcome:** [What should happen]
**If step fails:** [What to do next]

### Step 2: [Action]
...

## Verification
- [ ] [Health check passes]
- [ ] [Metrics return to normal]
- [ ] [Customer can successfully X]

## Rollback Procedure
[How to undo changes if resolution fails]

## Post-Resolution
- Update incident ticket
- Notify stakeholders
- Schedule post-mortem if SEV1/SEV2
```

**Example Runbook: VD Model Out of Memory**

```markdown
# Runbook: VD Model Out of Memory

**When to use:** Alert "VD GPU Memory >90%" or VD process crashes with OOM error
**Severity:** SEV2 (degrades service, but rAI fallback available)
**Estimated time to resolve:** 15-30 minutes

## Symptoms
- Alert: "VD GPU memory usage >90%"
- VD inference latency increases (>10s per request)
- VD process crashes with "CUDA out of memory" error
- Tasks automatically routed to rAI-only mode (cost increase)

## Initial Assessment
1. Check GPU memory usage:
   ```bash
   nvidia-smi
   # Look for VRAM usage near 100%
   ```

2. Check active VD inference requests:
   ```bash
   curl http://localhost:8080/vd/stats | jq '.active_requests'
   # Expected: <5, if >10 then request backlog
   ```

3. Verify VD model loaded correctly:
   ```bash
   tail -n 100 /var/log/obra/vd.log | grep "model_loaded"
   # Should see "model_loaded: true"
   ```

## Resolution Steps

### Step 1: Clear GPU Memory Cache
```bash
# Restart VD service (gracefully)
systemctl restart obra-vd

# Or via Obra CLI
obra vd restart --graceful

# Wait for model to reload (30-60 seconds)
sleep 60

# Verify memory usage normalized
nvidia-smi | grep "MiB /"
```
**Expected outcome:** VRAM usage <70%
**If step fails:** Proceed to Step 2

### Step 2: Reduce Batch Size
```bash
# Edit VD configuration
vim /etc/obra/vd.yaml

# Change:
# batch_size: 8
# To:
# batch_size: 4

# Restart VD
systemctl restart obra-vd
```
**Expected outcome:** VRAM usage <80%, latency <5s
**If step fails:** Proceed to Step 3

### Step 3: Switch to Smaller Model (Temporary)
```bash
# Edit configuration
vim /etc/obra/vd.yaml

# Change:
# model: llama-3.1-70b
# To:
# model: llama-3.1-8b  # Much smaller VRAM footprint

# Restart VD
systemctl restart obra-vd
```
**Expected outcome:** Service degraded but functional
**Note:** Schedule GPU upgrade or optimize workload

### Step 4: Investigate Memory Leak (If recurrent)
```bash
# Enable memory profiling
export CUDA_LAUNCH_BLOCKING=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Restart with profiling
systemctl restart obra-vd

# Monitor for gradual memory growth over 1 hour
watch -n 60 nvidia-smi

# If memory grows continuously, file bug with logs:
tar -czf vd-memleak-$(date +%Y%m%d).tar.gz /var/log/obra/vd.log
```

## Verification
- [ ] VD responding to health checks: `curl http://localhost:8080/vd/health`
- [ ] GPU memory <80%: `nvidia-smi`
- [ ] Validation latency <5s: Check Grafana dashboard
- [ ] Tasks successfully completing with VD validation (not rAI-only)

## Rollback Procedure
If resolution steps break VD entirely:
```bash
# Restore previous configuration
cp /etc/obra/vd.yaml.backup /etc/obra/vd.yaml

# Restart
systemctl restart obra-vd

# Force rAI-only mode while debugging
obra config set vd.enabled=false
```

## Post-Resolution
1. Update incident ticket with resolution details
2. If recurring issue (3+ times in 30 days):
   - File engineering ticket for permanent fix
   - Consider hardware upgrade
   - Review VD model selection
3. Update runbook if new information discovered
```

**Other Critical Runbooks:**

1. **rAI Provider Outage**
   - Symptoms, failover to backup provider, cost monitoring

2. **Database Connection Pool Exhausted**
   - Symptoms, connection analysis, pool size tuning

3. **Disk Space Full**
   - Symptoms, log rotation, data cleanup, storage expansion

4. **SSL Certificate Expiration**
   - Symptoms, cert renewal (Let's Encrypt), verification

5. **Git Integration Broken**
   - Symptoms, credential refresh, API token rotation

6. **Test Suite Failures Blocking Deployments**
   - Symptoms, flaky test identification, test environment debugging

7. **Cost Budget Exceeded**
   - Symptoms, spike analysis, automatic pause, budget increase

---

#### Chaos Engineering **[P2]**
**Description:** Proactively test system resilience

**Chaos Experiments:**

```python
# Example: Randomly kill rAI provider connections
class ChaosExperiment:
    def __init__(self, name: str, blast_radius: str):
        self.name = name
        self.blast_radius = blast_radius  # "test", "staging", "prod-1%", etc.

    def run(self):
        """Execute chaos experiment"""
        pass

class SimulateRAIProviderOutage(ChaosExperiment):
    """Kill connections to rAI provider to test failover"""

    def run(self):
        logger.info(f"[CHAOS] Starting {self.name}")

        # Block outbound connections to rAI provider
        if self.blast_radius == "staging":
            block_outbound("api.anthropic.com", duration=300)  # 5 min

            # Verify failover to backup provider
            assert circuit_breaker.is_open("claude-sonnet"), "Circuit breaker should open"
            assert fallback_provider_used(), "Should failover to GPT-4"

            logger.info("[CHAOS] Failover successful")

        # Restore connections
        unblock_outbound("api.anthropic.com")
        logger.info(f"[CHAOS] Completed {self.name}")

# Run monthly chaos experiments
experiments = [
    SimulateRAIProviderOutage("rai_outage", "staging"),
    SimulateVDCrash("vd_crash", "staging"),
    SimulateDiskFull("disk_full", "test"),
    SimulateNetworkLatency("network_slow", "staging")
]
```

**Chaos Schedule (P2):**
- **Monthly:** Run all experiments in staging
- **Quarterly:** Run low-risk experiments in prod (1% of traffic)
- **Post-experiment:** Update runbooks with learnings

---

## 9. CUSTOMER SUCCESS & SUPPORT

### 9.1 Support Tiers **[P1]**

**Standard Support (Included):**
- Email support: support@obra.ai
- Response time: 24 hours for normal issues, 4 hours for critical
- Available: 8 AM - 6 PM PT, Monday - Friday
- Knowledge base access
- Community forums

**Premium Support (+$200/month per tenant):**
- Email + chat support
- Response time: 4 hours for normal, 1 hour for critical
- Available: 24/7
- Dedicated Slack channel
- Priority bug fixes

**Enterprise Support (Custom pricing):**
- Email + chat + phone support
- Response time: 1 hour for normal, 15 minutes for critical
- Available: 24/7
- Dedicated technical account manager (TAM)
- Quarterly business reviews (QBRs)
- Proactive monitoring and recommendations
- Custom SLA

---

### 9.2 Training & Onboarding **[P1]**

**Self-Service Resources:**
- Comprehensive documentation (docs.obra.ai)
- Video tutorials (YouTube channel)
- Interactive demos
- Sample projects and templates
- API reference (Swagger/OpenAPI)

**Guided Onboarding (For paying customers):**
- 1-hour kickoff call
- Project setup assistance
- Configuration best practices
- Integration guidance
- Q&A session

**Team Training (Enterprise):**
- 4-hour workshop (up to 20 attendees)
- Topics:
  - Obra fundamentals
  - Writing effective intent statements
  - Reviewing and approving VD outputs
  - Interpreting metrics and reports
  - Troubleshooting common issues
- Hands-on exercises
- Delivered on-site or remotely

---

### 9.3 Success Metrics & QBRs **[Enterprise]**

**Quarterly Business Reviews:**
- 1-hour video call with customer stakeholders
- Review metrics:
  - Cost savings vs baseline
  - Productivity gains (cycle time reduction)
  - Quality metrics (test pass rate, bug rate)
  - User satisfaction (NPS, survey results)
- Discuss challenges and opportunities
- Roadmap preview (upcoming features)
- Gather feedback for product improvements

**Success Criteria (Defined upfront with customer):**
- Cost reduction: 60-75%
- Cycle time improvement: 40-60%
- User satisfaction: NPS >50
- Adoption: 80%+ of developers using Obra regularly

---

## 10. FUTURE INNOVATIONS (P3)

### 10.1 AI Model Fine-Tuning **[P3]**
- Fine-tune VD model on customer codebase
- Improve validation accuracy for customer-specific patterns
- Personalized prompt templates
- Requires significant compute and data

### 10.2 Autonomous Debugging **[P3]**
- VD autonomously debugs production issues
- Analyzes logs, traces, metrics
- Generates fixes and creates PRs
- Requires high confidence in VD quality

### 10.3 Predictive Maintenance **[P3]**
- Predict when code is likely to have issues
- Suggest refactorings before problems arise
- Identify technical debt hotspots
- Machine learning on historical data

### 10.4 Natural Language Interfaces **[P3]**
- Voice interface for hands-free coding
- Conversational UX ("Obra, add user auth")
- Integration with Alexa, Google Assistant
- Requires advanced NLP and context management

### 10.5 Collaborative AI **[P3]**
- Multiple developers + VD working together in real-time
- Google Docs-like collaboration on AI-generated code
- Conflict resolution and merging
- Real-time suggestions and corrections

---

## 11. OPEN QUESTIONS & DECISIONS

### 11.1 Technical Decisions

**Q1: VD Model Selection**
- **Decision needed:** Llama 3.1 70B vs Qwen 2.5 72B vs Mixtral 8x22B?
- **Criteria:** Validation accuracy, inference speed, memory usage
- **Timeline:** Before alpha program starts
- **Owner:** Lead engineer

**Q2: rAI Provider Priority**
- **Decision needed:** Default to Claude or GPT-4?
- **Criteria:** Quality, cost, availability, customer preference
- **Timeline:** Before alpha program starts
- **Owner:** Product manager + lead engineer

**Q3: Context Window Strategy**
- **Decision needed:** Hierarchical planning vs RAG?
- **Criteria:** Complexity, effectiveness, customer codebase size
- **Timeline:** After alpha program (based on learnings)
- **Owner:** Lead engineer

**Q4: Multi-Agent Timing**
- **Decision needed:** When to implement full multi-agent?
- **Criteria:** Alpha feedback, resource availability, customer demand
- **Timeline:** Decide at Beta milestone
- **Owner:** Product manager

---

### 11.2 Business Decisions

**Q5: Pricing Tiers**
- **Decision needed:** $250, $300, or $400 for standard tier?
- **Criteria:** Competitive positioning, customer willingness to pay, margins
- **Timeline:** Before beta launch
- **Owner:** CEO + sales lead

**Q6: Appliance Hardware**
- **Decision needed:** Which GPU for appliance tier?
- **Criteria:** Performance, cost, availability
- **Timeline:** Before Year 2 (appliance launch)
- **Owner:** Hardware engineer + product manager

**Q7: Compliance Priority**
- **Decision needed:** SOC 2 first or GDPR first?
- **Criteria:** Customer requirements, sales pipeline
- **Timeline:** Immediately (affects roadmap)
- **Owner:** CEO + security lead

---

## 12. SUCCESS METRICS & KPIs

**Alpha Program Success Criteria:**
- [ ] 5 customers deployed
- [ ] 60-75% API cost reduction achieved
- [ ] <2.5 average prompt iterations per feature
- [ ] VD validation catches 80%+ of bugs
- [ ] 4 of 5 customers willing to pay full price
- [ ] NPS >40

**Beta Launch Success Criteria:**
- [ ] 20 paying customers
- [ ] $450k ARR
- [ ] 90% customer retention
- [ ] NPS >50
- [ ] SOC 2 Type I certification obtained

**Year 1 Success Criteria:**
- [ ] 50 paying customers
- [ ] $3.2M ARR
- [ ] 95% uptime
- [ ] <5% monthly churn
- [ ] NPS >60

---

## APPENDIX

### A. Glossary of Terms

**VD (Virtual Developer):** Local LLM orchestration layer (Obra product)  
**rAI (Remote AI):** External LLM APIs (Claude, GPT-4, Gemini)  
**Agent:** Specialized VD instance or context for specific tasks  
**Orchestration Loop:** Complete cycle from intent → generation → validation → testing → integration  
**Escalation:** Progressive use of more capable models when initial attempts fail  
**Checkpoint:** Saved state snapshot enabling rollback and recovery  
**Token:** Unit of text processed by LLM (roughly 4 characters)  
**Context Window:** Maximum token capacity for VD or rAI model  
**Prompt Template:** Pre-structured prompt format for common tasks  
**Validation Score:** 0-100 metric indicating code quality from VD analysis  
**Tenant:** Isolated customer environment with separate data and resources  
**RTO (Recovery Time Objective):** Target time to restore service after failure  
**RPO (Recovery Point Objective):** Maximum acceptable data loss duration  

---

### B. Technology Stack

**Core Infrastructure:**
- **Container Orchestration:** Kubernetes (EKS, GKE, AKS)
- **Service Mesh:** Istio or Linkerd
- **Load Balancer:** NGINX or Envoy
- **Database:** PostgreSQL 15+ (primary), Redis (cache/queues)
- **Object Storage:** S3, GCS, or Azure Blob
- **Message Queue:** RabbitMQ or Apache Kafka

**VD Runtime:**
- **Inference Engine:** vLLM, TensorRT-LLM, or llama.cpp
- **Model Format:** GGUF or SafeTensors
- **GPU Acceleration:** CUDA 12+, cuDNN 8+

**Application Stack:**
- **Backend:** Python 3.11+ (FastAPI, Celery)
- **Frontend:** React 18+ with TypeScript
- **API:** REST (OpenAPI 3.0) + GraphQL (optional)
- **CLI:** Python Click or Go Cobra

**Monitoring & Observability:**
- **Metrics:** Prometheus + Grafana
- **Logs:** Loki or ELK Stack
- **Tracing:** Jaeger or Tempo
- **APM:** Datadog or New Relic

**Security:**
- **Secrets Management:** HashiCorp Vault or AWS Secrets Manager
- **Certificate Management:** Let's Encrypt + cert-manager
- **WAF:** Cloudflare or AWS WAF
- **SIEM:** Splunk or Elastic Security

---

### C. Resource Estimation Calculator

**Estimate resources needed for your deployment:**

```
Team Size: _____ developers
Projects: _____ concurrent projects
Tasks per day: _____ tasks

Recommended Configuration:
- CPU cores: team_size * 2
- RAM: team_size * 4 GB + 32 GB base
- GPU VRAM: max(24 GB, team_size * 2 GB)
- Storage: projects * 10 GB + 500 GB base
- Network: 100 Mbps * (1 + team_size / 20)

Estimated Costs:
- Obra Subscription: team_size * $300/month
- Infrastructure (cloud): $_____ /month
- rAI API Costs: tasks_per_day * 30 * $0.50 (before Obra)
- rAI API Costs: tasks_per_day * 30 * $0.15 (with Obra)
- Total Monthly: $_____
- Savings: $_____
```

---

**Document Version:** 3.0 - Production-Ready Enhanced
**Last Updated:** November 2025
**Status:** Ready for Engineering Review and Implementation
**Next Review:** Before Alpha Program Launch

---

## Document Changelog

### Version 3.0 (November 2025) - Production-Ready Enhancements

**Major Additions:**

1. **Developer Workflows & Integrations (Section 1.4)**
   - IDE integration for VS Code, JetBrains, Vim, Emacs
   - Git integration with automated branch/PR workflows
   - CI/CD integration (GitHub Actions, GitLab CI)
   - Project onboarding and codebase analysis
   - Migration tools from Copilot, Cursor, Aider

2. **Notifications & Alerting (Section 4.4)**
   - Multi-channel notifications (Slack, Email, Teams, Discord)
   - Alert rules and severity levels
   - Alert routing and aggregation
   - User-specific notification preferences
   - Quiet hours and do-not-disturb settings

3. **Cost Prediction & Budgeting (Section 4.5)**
   - ML-based pre-task cost estimation
   - Cost approval workflows
   - Budget tracking and alerting
   - Confidence intervals for cost predictions

4. **OpenTelemetry Integration**
   - Distributed tracing for task execution
   - Vendor-neutral observability
   - Correlation with logs
   - Smart sampling strategies

5. **Incident Response & Runbooks (Section 8.4)**
   - Structured incident response plan
   - SEV1-SEV4 severity levels
   - Detailed operational runbooks
   - Post-mortem templates
   - Chaos engineering framework

**Industry Best Practices Added:**

- Circuit breaker pattern for rAI providers with automatic failover
- Production-ready error handling with proper logging
- OpenTelemetry for distributed tracing and observability
- Comprehensive alert management with severity levels
- Structured incident response procedures
- Operational runbooks for common scenarios
- Chaos engineering for resilience testing

**Technical Accuracy Improvements:**

- Added proper exception handling to code examples
- Included retry logic and fallback mechanisms
- Enhanced security considerations
- Added realistic performance targets
- Improved resource estimation formulas
- Fixed type hints and imports in Python examples

**Clarity Enhancements:**

- More concrete examples throughout
- Step-by-step implementation guidance
- Clear dependencies between features
- Specific success criteria
- Detailed configuration examples
- Visual workflow representations

**Missing Features Now Included:**

- IDE plugins and editor integration
- Version control automation
- Continuous integration hooks
- Developer notification system
- Cost prediction before execution
- Project onboarding workflow
- Tool migration utilities
- Distributed tracing infrastructure
- Incident management procedures
- Operational runbooks

### Version 2.0 (November 2025) - Enterprise Enhanced
- Initial comprehensive technical design
- Core orchestration layer
- Reliability and recovery systems
- Performance and resource management
- Monitoring and observability
- Testing and quality assurance
- Enterprise features (multi-tenancy, RBAC, SSO)
- Security and compliance frameworks
- Deployment architectures

---

**Production Readiness Assessment:**

This document now provides:
- ✅ Complete feature specifications with priorities
- ✅ Industry-standard best practices
- ✅ Production-ready code examples with error handling
- ✅ Comprehensive operational procedures
- ✅ Security and incident response frameworks
- ✅ Observability and monitoring strategies
- ✅ Clear implementation guidance
- ✅ Realistic resource requirements
- ✅ Migration and onboarding workflows

**Recommended Next Steps:**

1. Review enhancements with engineering team
2. Validate OpenTelemetry integration approach
3. Prioritize P0 features for MVP
4. Create detailed task breakdown from this spec
5. Set up incident response procedures
6. Implement circuit breakers and failover logic
7. Build runbooks for operational scenarios

---

**End of Document**
