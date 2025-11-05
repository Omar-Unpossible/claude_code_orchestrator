# ADR-010: Git Auto-Integration with LLM-Generated Commit Messages

**Status**: Accepted
**Date**: 2025-11-04
**Deciders**: Obra Development Team
**Context**: M9 Core Enhancements (v1.2)

## Context and Problem Statement

Obra orchestrates code changes via Claude Code CLI, which modifies files in a git-tracked workspace. Currently:

- **No automatic commits**: Code changes are not committed until manual intervention
- **No audit trail**: Hard to track which changes belong to which task
- **No rollback mechanism**: Can't easily revert task-specific changes
- **Manual commit messages**: User must craft messages after each task
- **No PR workflow**: Pull request creation is entirely manual

This creates several problems:

1. **Lost context**: By the time user commits, they may have forgotten what changed
2. **Poor commit messages**: Rushed messages lack detail
3. **No granular rollback**: Can't revert individual task changes
4. **No git-based task tracking**: Can't correlate commits to tasks
5. **Manual PR creation**: Tedious for multi-task workflows

**Requirements**:
1. Automatically commit successful task changes
2. Generate semantic, context-aware commit messages
3. Link commits to tasks for traceability
4. Support branch-per-task workflow
5. Optionally create pull requests
6. Provide git-based rollback mechanism
7. Maintain conventional commit standards

## Decision Drivers

- **Traceability**: Every task change should be tracked in git
- **Quality**: Commit messages should be semantic and informative
- **Autonomy**: Reduce manual git operations
- **Safety**: Provide rollback capability via git
- **Integration**: Work with GitHub/GitLab workflows
- **Flexibility**: Support different commit strategies

## Considered Options

### Option 1: No Git Integration (Status Quo)

User manually commits changes.

**Pros**:
- Complete user control
- No complexity added
- User can craft perfect messages

**Cons**:
- Manual work required
- Context loss over time
- No automatic audit trail
- Poor message quality when rushed
- No task-commit linkage

### Option 2: Simple Auto-Commit with Template Messages

Auto-commit with basic template: "Task {id}: {title}".

**Pros**:
- Simple implementation
- Fast execution
- Predictable messages

**Cons**:
- Low-quality commit messages
- Doesn't explain what changed
- Doesn't follow conventional commit format
- No semantic value
- Doesn't scale to complex changes

### Option 3: LLM-Generated Semantic Commit Messages (Selected)

Use local LLM (Qwen) to analyze changes and generate semantic commit messages.

**Workflow**:
```python
1. Task completes successfully
2. GitManager.auto_commit(task, changes):
    a. Get list of changed files
    b. Get git diff for changes
    c. Send to LLM with prompt:
       "Analyze these changes and generate a conventional commit message"
    d. LLM returns: "feat(api): Add user authentication endpoints"
    e. GitManager stages and commits with generated message
    f. Commit hash saved to task metadata
3. (Optional) Create branch and PR
```

**Pros**:
- High-quality, semantic messages
- Context-aware (understands code changes)
- Follows conventional commit format
- Leverages existing LLM infrastructure
- Messages explain "why" not just "what"
- Industry best practice

**Cons**:
- Adds latency (LLM inference time)
- LLM messages may need validation
- More complex implementation
- Requires fallback for LLM failures

### Option 4: Hybrid (Template + Optional LLM)

Use template by default, LLM on-demand.

**Pros**:
- Fast default path (template)
- Quality option available (LLM)
- User choice

**Cons**:
- Two code paths to maintain
- Inconsistent message quality
- User must remember to enable LLM
- Doesn't maximize automation value

## Decision Outcome

**Chosen option**: **Option 3 - LLM-Generated Semantic Commit Messages**

### Rationale

1. **Quality > Speed**: Better commit messages justify small latency cost
2. **Leverage Existing Infrastructure**: Obra already runs Qwen for validation
3. **Best Practice**: Semantic commit messages are industry standard
4. **Autonomy**: Fully automated, no user decisions needed
5. **Traceability**: High-quality messages improve audit trail
6. **Scalability**: LLM can handle simple and complex changes equally well

Fallback to template messages if LLM fails ensures robustness.

## Design Details

### GitManager Class

```python
class GitManager:
    """Manages git operations with LLM-generated commit messages."""

    def __init__(
        self,
        working_dir: str,
        config: dict,
        llm_interface: LLMInterface
    ):
        self.repo = git.Repo(working_dir)
        self.config = config
        self.llm = llm_interface
        self.logger = logging.getLogger(__name__)

    def auto_commit(
        self,
        task: Task,
        message_override: Optional[str] = None
    ) -> str:
        """
        Auto-commit task changes with LLM-generated message.

        Returns:
            Commit hash (SHA)
        """

    def generate_commit_message(
        self,
        task: Task,
        changed_files: List[str],
        diff: str
    ) -> str:
        """
        Generate semantic commit message using LLM.

        Returns:
            Conventional commit message
        """

    def create_task_branch(self, task: Task) -> str:
        """
        Create branch: obra/task-{id}-{slug}

        Returns:
            Branch name
        """

    def create_pull_request(
        self,
        task: Task,
        branch: str,
        base_branch: str = 'main'
    ) -> str:
        """
        Create PR via gh CLI (GitHub) or glab CLI (GitLab).

        Returns:
            PR URL
        """

    def rollback_to_commit(self, commit_hash: str) -> None:
        """Rollback workspace to specific commit."""

    def rollback_task(self, task_id: int) -> None:
        """Rollback all commits for specific task."""

    def get_task_commits(self, task_id: int) -> List[str]:
        """Get all commit hashes for task (from metadata)."""

    def validate_working_tree(self) -> bool:
        """Check if working tree is clean (no uncommitted changes)."""
```

### LLM Commit Message Generation

**Prompt Template**:
```python
COMMIT_MESSAGE_PROMPT = """
You are a senior software engineer writing a git commit message.

Task Information:
- ID: {task_id}
- Title: {task_title}
- Description: {task_description}

Changed Files:
{changed_files}

Git Diff (summary):
{diff_summary}

Generate a semantic commit message following the Conventional Commits specification:
- Format: type(scope): short description
- Types: feat, fix, refactor, docs, test, chore, style, perf
- Keep short description under 72 characters
- Include detailed body explaining what and why (not how)
- Add footer with "Task-ID: {task_id}"

Example:
feat(auth): Add JWT-based user authentication

Implemented JWT token generation and validation for API endpoints.
Added middleware for protected routes and token refresh mechanism.

Task-ID: 123
Generated-By: Obra v1.2

Your commit message:
"""
```

**LLM Response Parsing**:
```python
def parse_commit_message(llm_response: str) -> dict:
    """
    Parse LLM response into structured commit message.

    Returns:
        {
            'type': 'feat',
            'scope': 'auth',
            'subject': 'Add JWT-based user authentication',
            'body': '...',
            'footer': '...'
        }
    """
```

**Validation**:
```python
def validate_commit_message(message: dict) -> bool:
    """
    Validate commit message format.

    Rules:
    - Type must be valid (feat, fix, etc.)
    - Subject under 72 chars
    - Scope is optional
    - Body and footer are optional
    """
```

**Fallback**:
```python
def generate_fallback_message(task: Task, changed_files: List[str]) -> str:
    """
    Generate simple template message if LLM fails.

    Format:
    chore(task): {task_title}

    Task ID: {task_id}
    Changed files: {file_list}

    Generated-By: Obra v1.2 (fallback)
    """
```

### Conventional Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(api): Add user registration endpoint` |
| `fix` | Bug fix | `fix(auth): Resolve token expiration issue` |
| `refactor` | Code refactoring | `refactor(db): Simplify query logic` |
| `docs` | Documentation | `docs(readme): Update installation instructions` |
| `test` | Add/update tests | `test(api): Add integration tests for auth` |
| `chore` | Maintenance | `chore(deps): Update dependencies` |
| `style` | Code style | `style(api): Fix linting errors` |
| `perf` | Performance | `perf(db): Optimize query with index` |

### Commit Strategies

**1. Per-Task Commit** (Default)
```yaml
git:
  commit_strategy: per_task
  # One commit per completed task
```

**Behavior**:
- Auto-commit when task status → `completed`
- Single commit per task (all changes together)
- Commit message links to task ID

**Use case**: Standard development workflow

**2. Per-Milestone Commit**
```yaml
git:
  commit_strategy: per_milestone
  # One commit per milestone completion
```

**Behavior**:
- No commits during individual tasks
- Single commit when milestone completes
- Commit message lists all task IDs

**Use case**: Feature branches with squashed commits

**3. Manual Commit**
```yaml
git:
  commit_strategy: manual
  # No auto-commits, user controls git
```

**Behavior**:
- No automatic commits
- User manually commits when desired
- Obra tracks task completion without git

**Use case**: User prefers full git control

### Branch-Per-Task Workflow

**Configuration**:
```yaml
git:
  branch_per_task: true
  branch_prefix: "obra/task-"
  base_branch: "main"
```

**Workflow**:
```python
1. Task starts:
   - Create branch: obra/task-123-add-user-auth
   - Switch to branch
   - Task metadata: branch_name = "obra/task-123-add-user-auth"

2. Task completes:
   - Auto-commit changes to task branch
   - (Optional) Create PR: obra/task-123-add-user-auth → main

3. PR merged:
   - Update task metadata: merged = True, pr_url = "..."
   - (Optional) Delete task branch
```

**Branch Naming**:
```python
def generate_branch_name(task: Task) -> str:
    """
    Generate branch name: {prefix}{id}-{slug}

    Example:
    - Task ID: 123
    - Task Title: "Add user authentication"
    - Branch: obra/task-123-add-user-auth
    """
    slug = task.title.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')[:50]  # Max 50 chars
    return f"{config.branch_prefix}{task.id}-{slug}"
```

### Pull Request Creation

**Configuration**:
```yaml
git:
  create_pr: true
  pr_template: ".github/PULL_REQUEST_TEMPLATE.md"
  pr_auto_merge: false
  pr_reviewers: []
  pr_labels:
    - "obra-generated"
    - "automated"
```

**Implementation**:
```python
def create_pull_request(
    self,
    task: Task,
    branch: str,
    base_branch: str = 'main'
) -> str:
    """
    Create PR via gh CLI (GitHub) or glab CLI (GitLab).

    Steps:
    1. Push branch to remote
    2. Generate PR title and body (via LLM or template)
    3. Run gh pr create or glab mr create
    4. Return PR URL
    """
    # Push branch
    self.repo.git.push('origin', branch)

    # Generate PR content
    pr_title = f"[Task {task.id}] {task.title}"
    pr_body = self.generate_pr_body(task)

    # Create PR via gh CLI
    result = subprocess.run(
        [
            'gh', 'pr', 'create',
            '--title', pr_title,
            '--body', pr_body,
            '--base', base_branch,
            '--head', branch,
            '--label', 'obra-generated',
        ],
        capture_output=True,
        text=True
    )

    pr_url = result.stdout.strip()
    return pr_url
```

**PR Body Template**:
```markdown
## Task Information
- **Task ID**: {task_id}
- **Status**: {task_status}
- **Created**: {task_created_at}
- **Completed**: {task_completed_at}

## Description
{task_description}

## Changes
{commit_message_body}

## Files Changed
{changed_files_list}

## Testing
{test_summary}

---
Generated by [Obra](https://github.com/Omar-Unpossible/claude_code_orchestrator) v{version}
```

### Rollback Mechanism

**Rollback to Commit**:
```python
def rollback_to_commit(self, commit_hash: str) -> None:
    """
    Rollback workspace to specific commit.

    Uses git reset --hard (destructive).
    """
    self.logger.warning(f"Rolling back to commit {commit_hash}")
    self.repo.git.reset('--hard', commit_hash)
```

**Rollback Task**:
```python
def rollback_task(self, task_id: int) -> None:
    """
    Rollback all changes for specific task.

    Process:
    1. Get task from StateManager
    2. Get commit hash from task metadata
    3. Find parent commit (before task commit)
    4. Reset to parent commit
    """
    task = self.state.get_task(task_id)
    if not task.metadata.get('commit_hash'):
        raise GitError("No commit found for task")

    commit_hash = task.metadata['commit_hash']
    parent_commit = self.repo.commit(commit_hash).parents[0].hexsha

    self.rollback_to_commit(parent_commit)
    self.logger.info(f"Rolled back task {task_id}")
```

### Configuration

```yaml
git:
  enabled: true                         # Enable git integration
  auto_commit: true                     # Auto-commit task changes
  commit_strategy: per_task             # per_task, per_milestone, manual
  branch_per_task: false                # Create branch per task
  branch_prefix: "obra/task-"           # Branch name prefix
  base_branch: "main"                   # Base branch for PRs
  create_pr: false                      # Auto-create PRs
  pr_template: ".github/PULL_REQUEST_TEMPLATE.md"
  pr_auto_merge: false                  # Auto-merge PRs (dangerous!)
  pr_reviewers: []                      # Reviewers to assign
  pr_labels:                            # Labels to add
    - "obra-generated"
    - "automated"
  commit_message:
    use_llm: true                       # Use LLM for messages
    fallback_template: "chore(task): {task_title}"
    max_subject_length: 72              # Conventional commit limit
    include_diff_summary: true          # Include diff in prompt
  validation:
    check_working_tree: true            # Ensure clean tree before commit
    prevent_empty_commits: true         # Skip commits with no changes
  rollback:
    enabled: true                       # Enable rollback capability
    create_backup_branch: true          # Create backup before rollback
```

## Integration with Orchestrator

```python
class Orchestrator:
    def __init__(self, ...):
        # ... existing initialization ...
        if self.config.get('git.enabled'):
            self.git_manager = GitManager(
                working_dir=self.config.get('project.working_directory'),
                config=self.config.get('git'),
                llm_interface=self.llm
            )

    def execute_task(self, task_id: int):
        """Execute task with git integration."""
        task = self.state.get_task(task_id)

        # Create branch if branch-per-task enabled
        if self.config.get('git.branch_per_task'):
            branch = self.git_manager.create_task_branch(task)
            task.metadata['branch_name'] = branch

        # Execute task
        result = self._execute_task_internal(task)

        # Auto-commit if enabled and task successful
        if (result.status == 'completed' and
            self.config.get('git.auto_commit') and
            self.config.get('git.commit_strategy') == 'per_task'):

            try:
                commit_hash = self.git_manager.auto_commit(task)
                task.metadata['commit_hash'] = commit_hash
                self.logger.info(f"Auto-committed: {commit_hash[:7]}")

                # Create PR if enabled
                if self.config.get('git.create_pr'):
                    pr_url = self.git_manager.create_pull_request(
                        task=task,
                        branch=task.metadata['branch_name']
                    )
                    task.metadata['pr_url'] = pr_url
                    self.logger.info(f"Created PR: {pr_url}")

            except GitError as e:
                self.logger.error(f"Git operation failed: {e}")
                # Don't fail task due to git issues

        self.state.update_task(task)
```

## Consequences

### Positive

- **Audit Trail**: Every task change is tracked in git
- **High-Quality Messages**: LLM-generated semantic messages
- **Traceability**: Commits linked to tasks via metadata
- **Rollback Capability**: Git-based rollback complements checkpoints
- **PR Automation**: Automatic pull request creation
- **Conventional Commits**: Industry-standard message format
- **Flexibility**: Multiple commit strategies for different workflows

### Negative

- **Latency**: LLM inference adds ~2-5 seconds per commit
- **Complexity**: Additional component (GitManager) and dependency (GitPython)
- **Git Dependency**: Requires git installed and configured
- **LLM Quality Risk**: Generated messages may occasionally need manual fixes
- **Storage Overhead**: More commits = larger git history

### Neutral

- **Testing Overhead**: Requires git repository setup in tests
- **Configuration Complexity**: Many git-related options
- **Documentation**: Need comprehensive user guide

## Implementation Notes

### Phase 1: GitManager Core (~200 lines)
- Implement GitManager class
- Implement auto_commit()
- Implement generate_commit_message()
- Add LLM prompt for commit messages
- Add fallback template messages
- Add commit message validation

### Phase 2: Branch and PR Support (~100 lines)
- Implement create_task_branch()
- Implement branch naming logic
- Implement create_pull_request()
- Add PR template generation
- Integrate gh/glab CLI

### Phase 3: Rollback Support (~50 lines)
- Implement rollback_to_commit()
- Implement rollback_task()
- Add backup branch creation
- Add safety checks

### Phase 4: Orchestrator Integration (~100 lines)
- Integrate GitManager into Orchestrator
- Add git operations to task lifecycle
- Add error handling for git failures
- Update task metadata with git info

### Phase 5: Configuration (~50 lines)
- Add git config to default_config.yaml
- Add git config to all profiles
- Add configuration validation

### Phase 6: Testing (~100 tests)
- Unit tests: commit message generation, branch naming, rollback
- Integration tests: full workflow with real git repo
- Edge cases: empty commits, merge conflicts, LLM failures
- Performance tests: commit latency measurement

## Edge Cases and Handling

### No Changes to Commit
```python
# Task completes but no files changed
if not self.repo.is_dirty():
    if config.get('git.prevent_empty_commits'):
        logger.info("No changes to commit, skipping")
        return None
```

### LLM Failure
```python
# LLM fails to generate message
try:
    message = generate_commit_message(task, diff)
except LLMError:
    message = generate_fallback_message(task)
    logger.warning("LLM failed, using fallback message")
```

### Merge Conflicts
```python
# Branch has conflicts with base
if self.repo.is_dirty() or self.repo.untracked_files:
    raise GitError("Working tree not clean, cannot commit")
```

### gh CLI Not Installed
```python
# gh command not found
if not shutil.which('gh'):
    raise GitError("gh CLI not installed, cannot create PR")
```

### Permission Denied
```python
# No git push permission
try:
    self.repo.git.push('origin', branch)
except git.exc.GitCommandError as e:
    raise GitError(f"Failed to push: {e}")
```

## Alternatives Considered But Rejected

### Commitizen Library
Use existing Commitizen library for commit message generation.

**Rejected because**:
- Template-based, not LLM-based
- Can't analyze code changes semantically
- Less context-aware than Qwen
- Adds unnecessary dependency
- Obra's LLM is already available

### Pre-Commit Hooks
Use git pre-commit hooks for message generation.

**Rejected because**:
- Runs on every commit (not just Obra commits)
- Can't access task context easily
- Less control over workflow
- Harder to debug
- Obra needs programmatic git control

### Manual Git Operations
Keep git operations manual, just add task metadata to workspace.

**Rejected because**:
- Doesn't solve the problem
- Manual work still required
- No automatic audit trail
- Missing opportunity for automation

## Related Decisions

- **ADR-001**: State Management - Git metadata stored in StateManager
- **ADR-004**: Local Agent Architecture - Git operations in same environment as agent
- **ADR-008**: Retry Logic (M9) - Retry applies to git operations
- **ADR-009**: Task Dependencies (M9) - Dependencies don't affect commit strategy

## References

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [GitPython Documentation](https://gitpython.readthedocs.io/)
- [GitHub CLI (gh)](https://cli.github.com/)
- [GitLab CLI (glab)](https://gitlab.com/gitlab-org/cli)
- [Semantic Versioning](https://semver.org/)
- [Commitizen Tools](https://commitizen-tools.github.io/commitizen/)

## Acceptance Criteria

- ✅ GitManager class implemented
- ✅ LLM-generated commit messages with fallback
- ✅ Conventional commit format validation
- ✅ Auto-commit after task completion
- ✅ Branch-per-task workflow
- ✅ Pull request creation via gh/glab CLI
- ✅ Rollback to commit and rollback task
- ✅ Integration with Orchestrator
- ✅ Configuration in default_config.yaml and profiles
- ✅ Comprehensive logging (GIT_COMMIT, GIT_PR, GIT_ROLLBACK)
- ✅ ≥90% test coverage
- ✅ User guide for git integration
- ✅ Git metadata tracked in task state

---

**Last Updated**: 2025-11-04
**Status**: Accepted (Implementation Pending)
**Related Issues**: M9 Phase 4 - Git Integration
