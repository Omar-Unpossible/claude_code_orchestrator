"""DocumentationManager - Automatic project infrastructure maintenance.

This module provides DocumentationManager which automatically maintains project
documentation (CHANGELOG, architecture docs, ADRs, guides) by creating maintenance
tasks at key project events (epic completion, milestone achievement, periodic checks).

Part of v1.4.0: Project Infrastructure Maintenance System (ADR-015)
"""

import os
import logging
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, NamedTuple
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass

from src.core.state import StateManager
from src.core.config import Config
from src.core.models import Task, TaskType, TaskStatus, TaskAssignee

logger = logging.getLogger(__name__)


@dataclass
class DocumentStatus:
    """Status of a documentation file."""
    path: str
    last_modified: datetime
    age_days: int
    category: str  # 'critical', 'important', 'normal'
    is_stale: bool
    threshold_days: int


class DocumentationManager:
    """Manages project documentation maintenance.

    Responsibilities:
    - Track documentation freshness (last modified vs last code change)
    - Detect stale documentation (threshold-based)
    - Generate maintenance tasks with context
    - Archive completed implementation plans
    - Update CHANGELOG, architecture docs, ADRs, guides

    Usage:
        >>> state_manager = StateManager.get_instance()
        >>> config = Config.load()
        >>> doc_mgr = DocumentationManager(state_manager, config)
        >>> stale_docs = doc_mgr.check_documentation_freshness()
        >>> task_id = doc_mgr.create_maintenance_task(
        ...     trigger='epic_complete',
        ...     scope='comprehensive',
        ...     context={'epic_id': 5}
        ... )
    """

    def __init__(self, state_manager: StateManager, config: Config):
        """Initialize DocumentationManager.

        Args:
            state_manager: StateManager instance for task creation
            config: Config instance for settings
        """
        self.state_manager = state_manager
        self.config = config
        self.enabled = config.get('documentation.enabled', False)

        # Load configuration
        self.maintenance_targets = config.get(
            'documentation.maintenance_targets',
            [
                'CHANGELOG.md',
                'docs/architecture/ARCHITECTURE.md',
                'docs/README.md',
                'docs/decisions/',
                'docs/guides/'
            ]
        )

        self.freshness_thresholds = config.get(
            'documentation.freshness_thresholds',
            {'critical': 30, 'important': 60, 'normal': 90}
        )

        self.archive_config = config.get(
            'documentation.archive',
            {
                'enabled': True,
                'source_dir': 'docs/development',
                'archive_dir': 'docs/archive/development',
                'patterns': [
                    '*_IMPLEMENTATION_PLAN.md',
                    '*_COMPLETION_PLAN.md',
                    '*_GUIDE.md'
                ]
            }
        )

        # Periodic check configuration (Story 2.1)
        self.periodic_config = config.get(
            'documentation.triggers.periodic',
            {
                'enabled': False,
                'interval_days': 7,
                'scope': 'lightweight',
                'auto_create_task': True
            }
        )

        # Threading for periodic checks
        self._periodic_timer: Optional[threading.Timer] = None
        self._timer_lock = threading.Lock()

        logger.debug(
            f"DocumentationManager initialized (enabled={self.enabled}, "
            f"targets={len(self.maintenance_targets)}, "
            f"periodic={'enabled' if self.periodic_config.get('enabled') else 'disabled'})"
        )

    def check_documentation_freshness(self) -> Dict[str, DocumentStatus]:
        """Check which documentation files are stale.

        Compares file modification times against thresholds to determine
        if documentation needs updating.

        Returns:
            Dict mapping document path to DocumentStatus

        Example:
            >>> stale_docs = doc_mgr.check_documentation_freshness()
            >>> for path, status in stale_docs.items():
            ...     if status.is_stale:
            ...         print(f"{path} is {status.age_days} days old")
        """
        if not self.enabled:
            logger.debug("Documentation maintenance disabled, skipping freshness check")
            return {}

        stale_docs = {}
        now = datetime.now(UTC)

        for target in self.maintenance_targets:
            # Determine if target is file or directory
            target_path = Path(target)

            if not target_path.exists():
                logger.warning(f"Documentation target does not exist: {target}")
                continue

            # Handle directory targets (recursively check files)
            if target_path.is_dir():
                for doc_file in target_path.rglob('*.md'):
                    status = self._check_file_freshness(doc_file, now)
                    if status and status.is_stale:
                        stale_docs[str(doc_file)] = status
            else:
                # Handle file targets
                status = self._check_file_freshness(target_path, now)
                if status and status.is_stale:
                    stale_docs[str(target_path)] = status

        logger.info(f"Freshness check complete: {len(stale_docs)} stale documents found")
        return stale_docs

    def _check_file_freshness(
        self,
        file_path: Path,
        now: datetime
    ) -> Optional[DocumentStatus]:
        """Check freshness of a single file.

        Args:
            file_path: Path to file
            now: Current datetime (UTC)

        Returns:
            DocumentStatus if file exists, None otherwise
        """
        if not file_path.exists():
            return None

        # Get file modification time
        mtime_timestamp = os.path.getmtime(file_path)
        last_modified = datetime.fromtimestamp(mtime_timestamp, tz=UTC)

        # Calculate age in days
        age_days = (now - last_modified).days

        # Determine category based on file path
        file_str = str(file_path)
        if 'CHANGELOG' in file_str or 'README' in file_str:
            category = 'critical'
        elif 'architecture' in file_str or 'decisions' in file_str:
            category = 'important'
        else:
            category = 'normal'

        # Get threshold for this category
        threshold_days = self.freshness_thresholds.get(category, 90)

        # Determine if stale
        is_stale = age_days > threshold_days

        return DocumentStatus(
            path=file_str,
            last_modified=last_modified,
            age_days=age_days,
            category=category,
            is_stale=is_stale,
            threshold_days=threshold_days
        )

    def create_maintenance_task(
        self,
        trigger: str,
        scope: str,
        context: Dict[str, Any]
    ) -> int:
        """Create documentation maintenance task.

        Args:
            trigger: Trigger type - 'epic_complete' | 'milestone_achieved' |
                    'version_bump' | 'periodic'
            scope: Maintenance scope - 'lightweight' | 'comprehensive' | 'full_review'
            context: Context dict with:
                - epic_id (for epic_complete)
                - milestone_id (for milestone_achieved)
                - milestone_name (for milestone_achieved)
                - version (for milestone_achieved)
                - stale_docs (for periodic)
                - changes (description of what changed)

        Returns:
            Task ID of created maintenance task

        Raises:
            Exception: If task creation fails

        Example:
            >>> task_id = doc_mgr.create_maintenance_task(
            ...     trigger='epic_complete',
            ...     scope='comprehensive',
            ...     context={
            ...         'epic_id': 5,
            ...         'epic_title': 'User Auth System',
            ...         'changes': 'Added OAuth, MFA, session mgmt'
            ...     }
            ... )
        """
        if not self.enabled:
            logger.debug("Documentation maintenance disabled, skipping task creation")
            return -1

        # Check if auto_maintain is enabled
        auto_maintain = self.config.get('documentation.auto_maintain', True)
        if not auto_maintain:
            logger.warning(
                f"Documentation auto_maintain disabled. "
                f"Maintenance recommended for trigger={trigger}, scope={scope}"
            )
            return -1

        # Check trigger-specific config
        trigger_enabled = self.config.get(
            f'documentation.triggers.{trigger}.enabled',
            True
        )
        if not trigger_enabled:
            logger.debug(f"Trigger '{trigger}' disabled, skipping maintenance task")
            return -1

        # Check auto_create_task setting
        auto_create_task = self.config.get(
            f'documentation.triggers.{trigger}.auto_create_task',
            True
        )
        if not auto_create_task:
            logger.info(
                f"Maintenance recommended (trigger={trigger}, scope={scope}) "
                f"but auto_create_task=false"
            )
            return -1

        # Detect stale documentation
        stale_docs = context.get('stale_docs')
        if not stale_docs and trigger == 'periodic':
            stale_docs = self.check_documentation_freshness()
            context['stale_docs'] = stale_docs

        # Add trigger and scope to context for prompt generation
        context['trigger'] = trigger
        context['scope'] = scope

        # Generate maintenance prompt
        prompt = self.generate_maintenance_prompt(
            stale_docs=list(stale_docs.keys()) if stale_docs else [],
            context=context
        )

        # Get task configuration
        task_config = self.config.get('documentation.task_config', {})
        priority = task_config.get('priority', 3)
        assigned_agent = task_config.get('assigned_agent', None)

        # Build task title
        if trigger == 'epic_complete':
            title = f"Documentation: Update docs for Epic #{context.get('epic_id')}"
        elif trigger == 'milestone_achieved':
            milestone_name = context.get('milestone_name', 'Unknown')
            title = f"Documentation: {milestone_name} milestone achieved"
        elif trigger == 'version_bump':
            version = context.get('version', 'Unknown')
            title = f"Documentation: Full review for {version}"
        else:  # periodic
            title = f"Documentation: Periodic freshness check ({scope})"

        # Create task data
        task_data = {
            'title': title,
            'description': prompt,
            'priority': priority,
            'assigned_to': TaskAssignee[assigned_agent] if assigned_agent else TaskAssignee.CLAUDE_CODE,
            'task_type': TaskType.TASK,
            'context': {
                'trigger': trigger,
                'scope': scope,
                'maintenance_context': context,
                'stale_docs': list(stale_docs.keys()) if stale_docs else []
            }
        }

        # Get project ID (assume project ID 1 for now - could be passed in context)
        project_id = context.get('project_id', 1)

        # Create task
        try:
            task = self.state_manager.create_task(project_id, task_data)
            logger.info(
                f"Created documentation maintenance task #{task.id} "
                f"(trigger={trigger}, scope={scope})"
            )
            return task.id
        except Exception as e:
            logger.error(f"Failed to create maintenance task: {e}")
            raise

    def generate_maintenance_prompt(
        self,
        stale_docs: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate detailed prompt for documentation maintenance.

        Args:
            stale_docs: List of stale document paths
            context: Context dict with epic/milestone details

        Returns:
            Formatted prompt string for the maintenance task

        Example:
            >>> prompt = doc_mgr.generate_maintenance_prompt(
            ...     stale_docs=['CHANGELOG.md', 'docs/architecture/ARCHITECTURE.md'],
            ...     context={'epic_id': 5, 'changes': 'Added OAuth'}
            ... )
        """
        trigger = context.get('trigger', 'unknown')
        scope = context.get('scope', 'comprehensive')

        # Build prompt header
        prompt_parts = [
            "# Documentation Maintenance Task",
            "",
            f"**Trigger**: {trigger}",
            f"**Scope**: {scope}",
            ""
        ]

        # Add epic/milestone context
        if trigger == 'epic_complete':
            epic_id = context.get('epic_id')
            epic_title = context.get('epic_title', 'Unknown Epic')
            changes = context.get('changes', 'No changes summary provided')

            prompt_parts.extend([
                f"## Epic Completion: #{epic_id} - {epic_title}",
                "",
                "**Changes Summary**:",
                changes,
                ""
            ])

        elif trigger == 'milestone_achieved':
            milestone_id = context.get('milestone_id')
            milestone_name = context.get('milestone_name', 'Unknown Milestone')
            version = context.get('version', 'Unknown')
            epics = context.get('epics', [])

            prompt_parts.extend([
                f"## Milestone Achievement: {milestone_name} ({version})",
                "",
                f"**Milestone ID**: {milestone_id}",
                f"**Completed Epics**: {len(epics)}",
                ""
            ])

        # Add stale documentation section
        if stale_docs:
            prompt_parts.extend([
                "## Stale Documentation Detected",
                "",
                "The following documents need updating:",
                ""
            ])
            for doc_path in stale_docs:
                prompt_parts.append(f"- `{doc_path}`")
            prompt_parts.append("")

        # Add maintenance instructions
        prompt_parts.extend([
            "## Maintenance Instructions",
            "",
            "Please update the following project documentation:",
            "",
            "1. **CHANGELOG.md**: Add entry for completed work",
            "2. **Architecture docs**: Update if architectural changes made",
            "3. **ADRs**: Create new ADR if significant decision made",
            "4. **Guides**: Update user/developer guides if needed",
            "5. **README**: Update if project structure or setup changed",
            "",
            "### Archive Completed Plans",
            "",
            "If this maintenance is for completed work, archive implementation plans:",
            f"- Source: `{self.archive_config.get('source_dir', 'docs/development')}`",
            f"- Archive: `{self.archive_config.get('archive_dir', 'docs/archive/development')}`",
            "",
            "### Documentation Patterns",
            "",
            "Follow these patterns when updating documentation:",
            "- **CHANGELOG**: Use semantic versioning and Keep a Changelog format",
            "- **ADRs**: Follow ADR template in docs/decisions/",
            "- **Architecture**: Update component diagrams if structure changed",
            "- **Guides**: Include examples and troubleshooting sections",
            "",
            "### References",
            "",
            "- Epic/Story details available in task context",
            "- Recent changes tracked in StateManager",
            "- Configuration in config/default_config.yaml",
            ""
        ])

        return "\n".join(prompt_parts)

    def archive_completed_plans(self, epic_id: int) -> List[str]:
        """Archive implementation plans for completed epic.

        Moves completed implementation plans from docs/development/ to
        docs/archive/development/ to keep active directory clean.

        Args:
            epic_id: Epic ID to archive plans for

        Returns:
            List of archived file paths

        Example:
            >>> archived = doc_mgr.archive_completed_plans(epic_id=5)
            >>> print(f"Archived {len(archived)} files")
        """
        if not self.archive_config.get('enabled', True):
            logger.debug("Archive disabled, skipping")
            return []

        source_dir = Path(self.archive_config.get('source_dir', 'docs/development'))
        archive_dir = Path(self.archive_config.get('archive_dir', 'docs/archive/development'))
        patterns = self.archive_config.get('patterns', [])

        if not source_dir.exists():
            logger.warning(f"Source directory does not exist: {source_dir}")
            return []

        # Create archive directory if it doesn't exist
        archive_dir.mkdir(parents=True, exist_ok=True)

        archived_files = []

        # Search for files matching patterns
        for pattern in patterns:
            for file_path in source_dir.glob(pattern):
                if not file_path.is_file():
                    continue

                # Build archive destination
                dest_path = archive_dir / file_path.name

                # Handle duplicate filenames
                if dest_path.exists():
                    timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
                    dest_path = archive_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"

                try:
                    # Move file to archive
                    shutil.move(str(file_path), str(dest_path))
                    archived_files.append(str(dest_path))
                    logger.info(f"Archived: {file_path.name} -> {dest_path}")
                except Exception as e:
                    logger.error(f"Failed to archive {file_path}: {e}")

        logger.info(f"Archived {len(archived_files)} files for epic #{epic_id}")
        return archived_files

    def update_changelog(self, epic: Task) -> None:
        """Update CHANGELOG.md with epic completion.

        Args:
            epic: Completed Epic task

        Example:
            >>> epic = state_manager.get_task(5)
            >>> doc_mgr.update_changelog(epic)
        """
        changelog_path = Path('CHANGELOG.md')

        if not changelog_path.exists():
            logger.warning("CHANGELOG.md not found, skipping update")
            return

        try:
            # Read current changelog
            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Build changelog entry
            entry_date = datetime.now(UTC).strftime('%Y-%m-%d')
            entry = f"- {epic.title} (Epic #{epic.id}) - {entry_date}\n"

            # Find [Unreleased] section and add entry
            if '[Unreleased]' in content:
                # Add after [Unreleased] header
                unreleased_pos = content.find('[Unreleased]')
                insert_pos = content.find('\n', unreleased_pos) + 1

                # Check if there's an "Added" subsection
                if '### Added' in content[insert_pos:insert_pos+500]:
                    added_pos = content.find('### Added', insert_pos)
                    insert_pos = content.find('\n', added_pos) + 1
                else:
                    # Add "Added" subsection
                    insert_pos = content.find('\n', unreleased_pos) + 1
                    entry = f"\n### Added\n{entry}"

                # Insert entry
                updated_content = content[:insert_pos] + entry + content[insert_pos:]

                # Write updated changelog
                with open(changelog_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)

                logger.info(f"Updated CHANGELOG.md with epic #{epic.id}")
            else:
                logger.warning("CHANGELOG.md does not have [Unreleased] section")

        except Exception as e:
            logger.error(f"Failed to update CHANGELOG.md: {e}")

    def suggest_adr_creation(self, epic: Task) -> bool:
        """Check if epic requires ADR creation.

        Args:
            epic: Epic task to check

        Returns:
            True if ADR creation suggested, False otherwise

        Example:
            >>> if doc_mgr.suggest_adr_creation(epic):
            ...     print("Consider creating an ADR for this epic")
        """
        # Check if epic has requires_adr flag (will be added in Story 1.2)
        # For now, use heuristics based on epic title/description

        requires_adr = False

        # Check epic metadata/context for requires_adr flag
        if hasattr(epic, 'requires_adr') and epic.requires_adr:
            requires_adr = True
        elif hasattr(epic, 'has_architectural_changes') and epic.has_architectural_changes:
            requires_adr = True
        else:
            # Heuristic: Check for keywords in title/description
            adr_keywords = [
                'architecture', 'design decision', 'pattern', 'framework',
                'migration', 'refactor', 'integration', 'ADR'
            ]
            text = f"{epic.title} {epic.description}".lower()
            for keyword in adr_keywords:
                if keyword.lower() in text:
                    requires_adr = True
                    break

        if requires_adr:
            logger.info(
                f"ADR creation suggested for epic #{epic.id} ({epic.title})"
            )

        return requires_adr

    # ============================================================================
    # Periodic Freshness Checks (Story 2.1)
    # ============================================================================

    def start_periodic_checks(self, project_id: int = 1) -> bool:
        """Start periodic documentation freshness checks.

        Schedules a recurring timer that checks documentation freshness
        at the configured interval. Creates maintenance tasks if stale
        docs are detected (based on auto_create_task config).

        Args:
            project_id: Project ID for maintenance task creation

        Returns:
            True if periodic checks started, False if disabled or already running

        Example:
            >>> doc_mgr.start_periodic_checks(project_id=1)
            True
        """
        if not self.enabled:
            logger.debug("Documentation maintenance disabled, skipping periodic checks")
            return False

        if not self.periodic_config.get('enabled', False):
            logger.debug("Periodic checks disabled in configuration")
            return False

        with self._timer_lock:
            if self._periodic_timer and self._periodic_timer.is_alive():
                logger.warning("Periodic checks already running")
                return False

            # Calculate interval in seconds
            interval_days = self.periodic_config.get('interval_days', 7)
            interval_seconds = interval_days * 24 * 60 * 60

            # Schedule first check
            self._periodic_timer = threading.Timer(
                interval_seconds,
                self._run_periodic_check,
                args=(project_id,)
            )
            self._periodic_timer.daemon = True
            self._periodic_timer.start()

            logger.info(
                f"Started periodic documentation checks "
                f"(interval={interval_days} days, project={project_id})"
            )
            return True

    def stop_periodic_checks(self) -> None:
        """Stop periodic documentation freshness checks.

        Cancels any running timers to ensure graceful shutdown.
        This method is idempotent (safe to call multiple times).

        Example:
            >>> doc_mgr.stop_periodic_checks()
        """
        with self._timer_lock:
            if self._periodic_timer:
                if self._periodic_timer.is_alive():
                    self._periodic_timer.cancel()
                    logger.info("Cancelled periodic documentation checks")
                self._periodic_timer = None

    def _run_periodic_check(self, project_id: int) -> None:
        """Run periodic documentation freshness check (internal).

        This method is called by the timer thread. It:
        1. Checks documentation freshness
        2. Creates maintenance task if stale docs found (or logs notification)
        3. Reschedules next check

        Args:
            project_id: Project ID for maintenance task creation
        """
        try:
            logger.info("Running periodic documentation freshness check")

            # Check documentation freshness
            stale_docs = self.check_documentation_freshness()

            if stale_docs:
                logger.info(
                    f"Periodic check found {len(stale_docs)} stale documents"
                )

                # Prepare context for maintenance task
                scope = self.periodic_config.get('scope', 'lightweight')
                auto_create_task = self.periodic_config.get('auto_create_task', True)

                context = {
                    'project_id': project_id,
                    'stale_docs': stale_docs,
                    'check_time': datetime.now(UTC).isoformat()
                }

                if auto_create_task:
                    # Create maintenance task
                    try:
                        task_id = self.create_maintenance_task(
                            trigger='periodic',
                            scope=scope,
                            context=context
                        )
                        if task_id > 0:
                            logger.info(
                                f"Created periodic maintenance task #{task_id} "
                                f"({len(stale_docs)} stale docs)"
                            )
                    except Exception as e:
                        logger.error(f"Failed to create periodic maintenance task: {e}")
                else:
                    # Just log notification
                    logger.warning(
                        f"Periodic check: {len(stale_docs)} stale documents detected. "
                        f"auto_create_task=false, no task created. "
                        f"Stale docs: {list(stale_docs.keys())}"
                    )
            else:
                logger.debug("Periodic check: All documentation is fresh")

        except Exception as e:
            logger.error(f"Error in periodic documentation check: {e}", exc_info=True)

        finally:
            # Reschedule next check
            with self._timer_lock:
                if self.periodic_config.get('enabled', False):
                    interval_days = self.periodic_config.get('interval_days', 7)
                    interval_seconds = interval_days * 24 * 60 * 60

                    self._periodic_timer = threading.Timer(
                        interval_seconds,
                        self._run_periodic_check,
                        args=(project_id,)
                    )
                    self._periodic_timer.daemon = True
                    self._periodic_timer.start()
                    logger.debug(f"Rescheduled next periodic check in {interval_days} days")
                else:
                    logger.info("Periodic checks disabled, not rescheduling")
                    self._periodic_timer = None
