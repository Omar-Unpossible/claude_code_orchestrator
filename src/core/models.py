"""SQLAlchemy ORM models for the orchestrator database.

This module defines all database models with:
- Relationships between entities
- Validation constraints
- Indexes for performance
- Soft delete support
- Audit timestamps
- Serialization methods
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, Enum, CheckConstraint, Index, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# Enums

class TaskStatus(str, enum.Enum):
    """Task status values."""
    PENDING = 'pending'
    READY = 'ready'
    RUNNING = 'running'
    BLOCKED = 'blocked'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    RETRYING = 'retrying'


class TaskAssignee(str, enum.Enum):
    """Task assignee types."""
    HUMAN = 'human'
    LOCAL_LLM = 'local_llm'
    CLAUDE_CODE = 'claude_code'
    SYSTEM = 'system'


class InteractionSource(str, enum.Enum):
    """Source of interaction."""
    LOCAL_LLM = 'local_llm'
    CLAUDE_CODE = 'claude_code'


class BreakpointSeverity(str, enum.Enum):
    """Breakpoint severity levels."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class ProjectStatus(str, enum.Enum):
    """Project status values."""
    ACTIVE = 'active'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'


# Models

class ProjectState(Base):
    """Project state model.

    Represents a project being orchestrated.
    """
    __tablename__ = 'project_state'

    id = Column(Integer, primary_key=True)
    project_name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    working_directory = Column(String(512), nullable=False)
    status = Column(
        Enum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.ACTIVE,
        index=True
    )

    # Configuration stored as JSON
    configuration = Column(JSON, nullable=False, default=dict)

    # Metadata
    project_metadata = Column(JSON, default=dict)

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tasks = relationship('Task', back_populates='project', cascade='all, delete-orphan')
    interactions = relationship('Interaction', back_populates='project', cascade='all, delete-orphan')
    checkpoints = relationship('Checkpoint', back_populates='project', cascade='all, delete-orphan')
    breakpoint_events = relationship('BreakpointEvent', back_populates='project', cascade='all, delete-orphan')
    usage_tracking = relationship('UsageTracking', back_populates='project', cascade='all, delete-orphan')
    file_states = relationship('FileState', back_populates='project', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ProjectState(id={self.id}, name='{self.project_name}', status='{self.status.value}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'project_name': self.project_name,
            'description': self.description,
            'working_directory': self.working_directory,
            'status': self.status.value,
            'configuration': self.configuration,
            'project_metadata': self.project_metadata,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Task(Base):
    """Task model.

    Represents a task to be completed by an agent.
    """
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)

    # Task hierarchy (self-referential)
    parent_task_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)

    # Task details
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True
    )
    assigned_to = Column(
        Enum(TaskAssignee),
        nullable=False,
        default=TaskAssignee.CLAUDE_CODE
    )
    priority = Column(
        Integer,
        nullable=False,
        default=5,
        index=True
    )

    # Task dependencies (stored as JSON list of task IDs)
    dependencies = Column(JSON, default=list)

    # Task context and results
    context = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    task_metadata = Column(JSON, default=dict)  # Additional task metadata (retry_at, reason, etc.)

    # Retry tracking
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint('priority >= 1 AND priority <= 10', name='check_priority_range'),
        Index('idx_task_project_status', 'project_id', 'status'),
    )

    # Relationships
    project = relationship('ProjectState', back_populates='tasks')
    parent_task = relationship('Task', remote_side=[id], backref='subtasks')
    interactions = relationship('Interaction', back_populates='task', cascade='all, delete-orphan')
    breakpoint_events = relationship('BreakpointEvent', back_populates='task', cascade='all, delete-orphan')
    file_states = relationship('FileState', back_populates='task')

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title[:30]}...', status='{self.status.value}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'parent_task_id': self.parent_task_id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'assigned_to': self.assigned_to.value,
            'priority': self.priority,
            'dependencies': self.dependencies,
            'context': self.context,
            'result': self.result,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_deleted': self.is_deleted
        }

    # M9: Dependency management methods

    def add_dependency(self, task_id: int) -> None:
        """Add a task dependency (M9).

        Args:
            task_id: ID of task this task depends on

        Example:
            >>> task.add_dependency(5)  # Task depends on task #5
        """
        if self.dependencies is None:
            self.dependencies = []
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)

    def remove_dependency(self, task_id: int) -> None:
        """Remove a task dependency (M9).

        Args:
            task_id: ID of task to remove from dependencies

        Example:
            >>> task.remove_dependency(5)
        """
        if self.dependencies and task_id in self.dependencies:
            self.dependencies.remove(task_id)

    def get_dependencies(self) -> List[int]:
        """Get list of task IDs this task depends on (M9).

        Returns:
            List of task IDs

        Example:
            >>> deps = task.get_dependencies()
            >>> print(f"Depends on tasks: {deps}")
        """
        return self.dependencies if self.dependencies else []

    def has_dependencies(self) -> bool:
        """Check if task has any dependencies (M9).

        Returns:
            True if task has dependencies

        Example:
            >>> if task.has_dependencies():
            ...     print("Task is waiting on dependencies")
        """
        return bool(self.dependencies)


class Interaction(Base):
    """Interaction model.

    Represents a prompt/response interaction with an agent or LLM.
    """
    __tablename__ = 'interaction'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)

    # Interaction details
    source = Column(
        Enum(InteractionSource),
        nullable=False,
        index=True
    )
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)

    # Metadata
    confidence_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    validation_passed = Column(Boolean, nullable=True)

    # Timing
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    duration_seconds = Column(Float, nullable=True)

    # Context
    context = Column(JSON, default=dict)

    # ============================================================================
    # Claude Code JSON Metadata (from --output-format json)
    # Added: 2025-11-03 (Phase 1, Task 1.2 - Headless Mode Enhancements)
    # ============================================================================

    # Token usage (per-request breakdown)
    input_tokens = Column(Integer, nullable=True, default=0)
    cache_creation_input_tokens = Column(Integer, nullable=True, default=0)
    cache_read_input_tokens = Column(Integer, nullable=True, default=0)
    output_tokens = Column(Integer, nullable=True, default=0)
    total_tokens = Column(Integer, nullable=True, default=0)  # Sum of all token types

    # Performance metrics
    duration_ms = Column(Integer, nullable=True, default=0)  # Total duration (client-side)
    duration_api_ms = Column(Integer, nullable=True, default=0)  # API time only
    num_turns = Column(Integer, nullable=True, default=0)  # Number of turns used

    # Session tracking
    agent_session_id = Column(String(64), nullable=True, index=True)  # Claude Code session UUID

    # Error handling
    error_subtype = Column(String(50), nullable=True, index=True)  # error_max_turns, etc.

    # Cost tracking (optional - Claude Pro subscription)
    cost_usd = Column(Float, nullable=True, default=0.0)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)',
            name='check_confidence_range'
        ),
        CheckConstraint(
            'quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 100.0)',
            name='check_quality_range'
        ),
        Index('idx_interaction_project_task_time', 'project_id', 'task_id', 'timestamp'),
    )

    # Relationships
    project = relationship('ProjectState', back_populates='interactions')
    task = relationship('Task', back_populates='interactions')

    def __repr__(self):
        return f"<Interaction(id={self.id}, source='{self.source.value}', timestamp={self.timestamp})>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'source': self.source.value,
            'prompt': self.prompt,
            'response': self.response,
            'confidence_score': self.confidence_score,
            'quality_score': self.quality_score,
            'validation_passed': self.validation_passed,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'duration_seconds': self.duration_seconds,
            'context': self.context,
            # Claude Code JSON metadata
            'input_tokens': self.input_tokens,
            'cache_creation_input_tokens': self.cache_creation_input_tokens,
            'cache_read_input_tokens': self.cache_read_input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'duration_ms': self.duration_ms,
            'duration_api_ms': self.duration_api_ms,
            'num_turns': self.num_turns,
            'agent_session_id': self.agent_session_id,
            'error_subtype': self.error_subtype,
            'cost_usd': self.cost_usd
        }


class Checkpoint(Base):
    """Checkpoint model.

    Represents a state snapshot for rollback capability.
    """
    __tablename__ = 'checkpoint'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)

    # Checkpoint details
    checkpoint_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # State snapshot (JSON serialization of full state)
    state_snapshot = Column(JSON, nullable=False)

    # Metadata
    created_by = Column(String(100), nullable=True)
    checkpoint_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Relationships
    project = relationship('ProjectState', back_populates='checkpoints')

    def __repr__(self):
        return f"<Checkpoint(id={self.id}, type='{self.checkpoint_type}', created={self.created_at})>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'checkpoint_type': self.checkpoint_type,
            'description': self.description,
            'state_snapshot': self.state_snapshot,
            'created_by': self.created_by,
            'checkpoint_metadata': self.checkpoint_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BreakpointEvent(Base):
    """Breakpoint event model.

    Represents a breakpoint trigger requiring human intervention.
    """
    __tablename__ = 'breakpoint_event'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)

    # Breakpoint details
    breakpoint_type = Column(String(100), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    severity = Column(
        Enum(BreakpointSeverity),
        nullable=False,
        default=BreakpointSeverity.MEDIUM
    )

    # Context
    context = Column(JSON, default=dict)

    # Resolution
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolution = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    triggered_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    project = relationship('ProjectState', back_populates='breakpoint_events')
    task = relationship('Task', back_populates='breakpoint_events')

    def __repr__(self):
        return f"<BreakpointEvent(id={self.id}, type='{self.breakpoint_type}', resolved={self.resolved})>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'breakpoint_type': self.breakpoint_type,
            'reason': self.reason,
            'severity': self.severity.value,
            'context': self.context,
            'resolved': self.resolved,
            'resolution': self.resolution,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None
        }


class UsageTracking(Base):
    """Usage tracking model.

    Tracks usage statistics for analytics.
    """
    __tablename__ = 'usage_tracking'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)

    # Date tracking
    date = Column(DateTime, nullable=False, index=True)

    # Usage metrics
    interactions_count = Column(Integer, default=0, nullable=False)
    tasks_completed = Column(Integer, default=0, nullable=False)
    tasks_failed = Column(Integer, default=0, nullable=False)
    breakpoints_triggered = Column(Integer, default=0, nullable=False)

    # Performance metrics
    avg_confidence_score = Column(Float, nullable=True)
    avg_quality_score = Column(Float, nullable=True)
    total_duration_seconds = Column(Float, default=0.0, nullable=False)

    # Additional metrics
    metrics = Column(JSON, default=dict)

    # Relationships
    project = relationship('ProjectState', back_populates='usage_tracking')

    __table_args__ = (
        Index('idx_usage_project_date', 'project_id', 'date'),
    )

    def __repr__(self):
        return f"<UsageTracking(id={self.id}, date={self.date}, tasks_completed={self.tasks_completed})>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'date': self.date.isoformat() if self.date else None,
            'interactions_count': self.interactions_count,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'breakpoints_triggered': self.breakpoints_triggered,
            'avg_confidence_score': self.avg_confidence_score,
            'avg_quality_score': self.avg_quality_score,
            'total_duration_seconds': self.total_duration_seconds,
            'metrics': self.metrics
        }


class PatternLearning(Base):
    """Pattern learning model.

    Stores learned patterns for future optimization (v2.0 feature).
    """
    __tablename__ = 'pattern_learning'

    id = Column(Integer, primary_key=True)

    # Pattern identification
    pattern_type = Column(String(100), nullable=False, index=True)
    pattern_key = Column(String(255), nullable=False, index=True)

    # Pattern data
    pattern_data = Column(JSON, nullable=False)

    # Usage tracking
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_pattern_type_key', 'pattern_type', 'pattern_key'),
    )

    def __repr__(self):
        return f"<PatternLearning(id={self.id}, type='{self.pattern_type}', key='{self.pattern_key}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'pattern_type': self.pattern_type,
            'pattern_key': self.pattern_key,
            'pattern_data': self.pattern_data,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ParameterEffectiveness(Base):
    """Track which parameters help LLM make accurate decisions.

    Records which parameters were included in prompts and whether
    the resulting LLM decision was accurate (as determined by
    later human review or test outcomes).

    This enables data-driven optimization of prompt parameters.

    Attributes:
        id: Primary key
        template_name: Which template was used (e.g., 'validation', 'task_execution')
        parameter_name: Which parameter (e.g., 'file_changes', 'retry_context')
        was_included: Whether parameter fit in token budget and was included
        validation_accurate: Whether LLM validation matched reality (nullable until known)
        task_id: Associated task
        prompt_token_count: Total tokens in prompt
        parameter_token_count: Tokens used by this parameter
        timestamp: When this was recorded
    """
    __tablename__ = 'parameter_effectiveness'

    id = Column(Integer, primary_key=True)
    template_name = Column(String(100), nullable=False, index=True)
    parameter_name = Column(String(100), nullable=False, index=True)
    was_included = Column(Boolean, nullable=False, index=True)
    validation_accurate = Column(Boolean, nullable=True, index=True)

    # Context
    task_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)
    prompt_token_count = Column(Integer, nullable=True)
    parameter_token_count = Column(Integer, nullable=True)

    # Metadata
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Relationships
    task = relationship('Task', backref='parameter_usage')

    __table_args__ = (
        Index('idx_param_eff_template_param', 'template_name', 'parameter_name'),
        Index('idx_param_eff_task_template', 'task_id', 'template_name'),
    )

    def __repr__(self):
        return (
            f"<ParameterEffectiveness("
            f"template={self.template_name}, "
            f"param={self.parameter_name}, "
            f"included={self.was_included}, "
            f"accurate={self.validation_accurate})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'template_name': self.template_name,
            'parameter_name': self.parameter_name,
            'was_included': self.was_included,
            'validation_accurate': self.validation_accurate,
            'task_id': self.task_id,
            'prompt_token_count': self.prompt_token_count,
            'parameter_token_count': self.parameter_token_count,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class FileState(Base):
    """File state model.

    Tracks file changes in the workspace.
    """
    __tablename__ = 'file_state'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)

    # File details
    file_path = Column(String(1024), nullable=False, index=True)
    file_hash = Column(String(64), nullable=False)  # SHA-256 hash
    file_size = Column(Integer, nullable=False)

    # Change tracking
    change_type = Column(String(20), nullable=False)  # created, modified, deleted

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Relationships
    project = relationship('ProjectState', back_populates='file_states')
    task = relationship('Task', back_populates='file_states')

    __table_args__ = (
        Index('idx_file_project_path', 'project_id', 'file_path'),
    )

    def __repr__(self):
        return f"<FileState(id={self.id}, path='{self.file_path}', change='{self.change_type}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'file_path': self.file_path,
            'file_hash': self.file_hash,
            'file_size': self.file_size,
            'change_type': self.change_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PromptRuleViolation(Base):
    """Prompt rule violation model.

    Tracks violations of prompt engineering rules for pattern learning.
    Enables the system to learn from mistakes and improve prompt quality.
    """
    __tablename__ = 'prompt_rule_violation'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=False, index=True)

    # Rule details
    rule_id = Column(String(50), nullable=False, index=True)  # e.g., "CODE_001"
    rule_name = Column(String(255), nullable=False)
    rule_domain = Column(String(50), nullable=False, index=True)  # e.g., "code_generation"

    # Violation details
    violation_details = Column(JSON, nullable=False)  # Context, location, specifics
    severity = Column(String(20), nullable=False, index=True)  # critical, high, medium, low

    # Resolution tracking
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    task = relationship('Task', backref='rule_violations')

    __table_args__ = (
        Index('idx_violation_task_rule', 'task_id', 'rule_id'),
        Index('idx_violation_severity_resolved', 'severity', 'resolved'),
    )

    def __repr__(self):
        return f"<PromptRuleViolation(id={self.id}, rule='{self.rule_id}', severity='{self.severity}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'rule_domain': self.rule_domain,
            'violation_details': self.violation_details,
            'severity': self.severity,
            'resolved': self.resolved,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class ComplexityEstimate(Base):
    """Task complexity estimate model.

    Stores complexity estimates for tasks to enable automatic decomposition
    and resource planning. Tracks both heuristic and actual complexity.
    """
    __tablename__ = 'complexity_estimate'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=False, unique=True, index=True)

    # Estimated complexity metrics
    estimated_tokens = Column(Integer, nullable=False)
    estimated_loc = Column(Integer, nullable=False)  # Lines of code
    estimated_files = Column(Integer, nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=False)

    # Complexity scores (0-100 scale)
    overall_complexity_score = Column(Integer, nullable=False)
    heuristic_score = Column(Integer, nullable=False)
    llm_adjusted_score = Column(Integer, nullable=True)

    # Decomposition decision
    should_decompose = Column(Boolean, nullable=False, index=True)
    decomposition_reason = Column(Text, nullable=True)

    # Actual metrics (filled after task completion)
    actual_tokens = Column(Integer, nullable=True)
    actual_loc = Column(Integer, nullable=True)
    actual_files = Column(Integer, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)

    # Accuracy tracking
    estimation_accuracy = Column(Float, nullable=True)  # 0.0-1.0

    # Metadata
    estimation_factors = Column(JSON, default=dict)  # Factors that influenced estimate
    confidence = Column(Float, nullable=False, default=0.5)  # 0.0-1.0

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    task = relationship('Task', backref='complexity_estimate')

    __table_args__ = (
        CheckConstraint('overall_complexity_score >= 0 AND overall_complexity_score <= 100', name='check_complexity_range'),
        CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='check_confidence_range'),
        Index('idx_complexity_should_decompose', 'should_decompose', 'overall_complexity_score'),
    )

    def __repr__(self):
        return f"<ComplexityEstimate(task_id={self.task_id}, score={self.overall_complexity_score}, decompose={self.should_decompose})>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'estimated_tokens': self.estimated_tokens,
            'estimated_loc': self.estimated_loc,
            'estimated_files': self.estimated_files,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'overall_complexity_score': self.overall_complexity_score,
            'heuristic_score': self.heuristic_score,
            'llm_adjusted_score': self.llm_adjusted_score,
            'should_decompose': self.should_decompose,
            'decomposition_reason': self.decomposition_reason,
            'actual_tokens': self.actual_tokens,
            'actual_loc': self.actual_loc,
            'actual_files': self.actual_files,
            'actual_duration_minutes': self.actual_duration_minutes,
            'estimation_accuracy': self.estimation_accuracy,
            'estimation_factors': self.estimation_factors,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SessionRecord(Base):
    """Session tracking model for milestone and standalone task execution.

    Tracks session lifecycle and usage metrics for both milestone-based work
    and standalone task execution. Sessions maintain context across multiple
    tasks within a milestone, or track usage for individual tasks.

    Important: session_id is a SHARED UUID between Obra and Claude Code.
    Obra generates this UUID, stores it in the database, and passes it to
    Claude Code for coordinated session tracking. Claude returns this same
    UUID in response metadata, enabling Obra to update the correct session record.

    Attributes:
        id: Primary key
        session_id: Shared session UUID (generated by Obra, used by both Obra and Claude Code)
        project_id: Associated project
        milestone_id: Milestone being executed (null for standalone tasks)
        started_at: Session start timestamp
        ended_at: Session end timestamp (null if active)
        summary: Generated summary of session work (for transitions)
        status: Session status (active, completed, refreshed, abandoned)
        total_tokens: Cumulative tokens used in session
        total_turns: Cumulative turns used in session
        total_cost_usd: Cumulative cost in USD
    """
    __tablename__ = 'session_record'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project_state.id'), nullable=False, index=True)
    milestone_id = Column(Integer, nullable=True, index=True)  # Optional milestone association
    task_id = Column(Integer, ForeignKey('task.id'), nullable=True, index=True)  # Task for per-iteration sessions

    # Lifecycle timestamps
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True)

    # Session summary (generated by Qwen for milestone transitions)
    summary = Column(Text, nullable=True)

    # Session status
    status = Column(String(20), nullable=False, default='active', index=True)
    # active: Currently in use
    # completed: Successfully finished
    # refreshed: Context window refresh triggered new session
    # abandoned: Session ended due to error

    # Cumulative usage tracking (for context window management)
    total_tokens = Column(Integer, default=0, nullable=False)
    total_turns = Column(Integer, default=0, nullable=False)
    total_cost_usd = Column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship('ProjectState', backref='sessions')

    __table_args__ = (
        Index('idx_session_project_status', 'project_id', 'status'),
        Index('idx_session_milestone', 'milestone_id'),
    )

    def __repr__(self):
        return f"<SessionRecord(session_id='{self.session_id[:8]}...', status='{self.status}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'project_id': self.project_id,
            'milestone_id': self.milestone_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'summary': self.summary,
            'status': self.status,
            'total_tokens': self.total_tokens,
            'total_turns': self.total_turns,
            'total_cost_usd': self.total_cost_usd,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ContextWindowUsage(Base):
    """Context window token usage tracking model.

    Tracks cumulative token usage per session for context window management.
    Used for Path B (manual tracking) since Claude Code doesn't provide context %.

    Attributes:
        id: Primary key
        session_id: Associated session UUID
        task_id: Task that generated these tokens (optional)
        cumulative_tokens: Running total of tokens in session
        input_tokens: Input tokens for this interaction
        cache_creation_tokens: Tokens cached in this interaction
        cache_read_tokens: Tokens read from cache in this interaction
        output_tokens: Output tokens for this interaction
        timestamp: When this usage was recorded
    """
    __tablename__ = 'context_window_usage'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=True)

    # Cumulative token count (running total for session)
    cumulative_tokens = Column(Integer, nullable=False, index=True)

    # Per-interaction token breakdown
    input_tokens = Column(Integer, nullable=False, default=0)
    cache_creation_tokens = Column(Integer, nullable=False, default=0)
    cache_read_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)

    # Timestamp for ordering
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Composite index for efficient session queries
    __table_args__ = (
        Index('idx_context_window_session_time', 'session_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<ContextWindowUsage(session_id='{self.session_id[:8]}...', cumulative={self.cumulative_tokens:,})>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'task_id': self.task_id,
            'cumulative_tokens': self.cumulative_tokens,
            'input_tokens': self.input_tokens,
            'cache_creation_tokens': self.cache_creation_tokens,
            'cache_read_tokens': self.cache_read_tokens,
            'output_tokens': self.output_tokens,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class ParallelAgentAttempt(Base):
    """Parallel agent execution attempt model.

    Tracks attempts to execute tasks using multiple parallel agents.
    Records success/failure, agent coordination, and performance metrics.
    """
    __tablename__ = 'parallel_agent_attempt'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=False, index=True)

    # Parallel execution details
    num_agents = Column(Integer, nullable=False)
    agent_ids = Column(JSON, nullable=False)  # List of agent identifiers
    subtask_ids = Column(JSON, nullable=False)  # List of subtask IDs assigned to agents

    # Execution results
    success = Column(Boolean, nullable=False, index=True)
    failure_reason = Column(Text, nullable=True)
    conflict_detected = Column(Boolean, default=False, nullable=False)
    conflict_details = Column(JSON, nullable=True)

    # Performance metrics
    total_duration_seconds = Column(Float, nullable=False)
    sequential_estimate_seconds = Column(Float, nullable=True)
    speedup_factor = Column(Float, nullable=True)  # Actual time / Sequential estimate

    # Resource usage
    max_concurrent_agents = Column(Integer, nullable=False)
    total_token_usage = Column(Integer, nullable=True)
    failed_agent_count = Column(Integer, default=0, nullable=False)

    # Strategy used
    parallelization_strategy = Column(String(100), nullable=False)  # e.g., "file_based", "feature_based"
    fallback_to_sequential = Column(Boolean, default=False, nullable=False)

    # Metadata
    execution_metadata = Column(JSON, default=dict)  # Additional context

    # Timestamps
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    task = relationship('Task', backref='parallel_attempts')

    __table_args__ = (
        CheckConstraint('num_agents >= 2', name='check_min_agents'),
        CheckConstraint('speedup_factor > 0', name='check_positive_speedup'),
        Index('idx_parallel_success_strategy', 'success', 'parallelization_strategy'),
    )

    def __repr__(self):
        return f"<ParallelAgentAttempt(id={self.id}, task_id={self.task_id}, agents={self.num_agents}, success={self.success})>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'num_agents': self.num_agents,
            'agent_ids': self.agent_ids,
            'subtask_ids': self.subtask_ids,
            'success': self.success,
            'failure_reason': self.failure_reason,
            'conflict_detected': self.conflict_detected,
            'conflict_details': self.conflict_details,
            'total_duration_seconds': self.total_duration_seconds,
            'sequential_estimate_seconds': self.sequential_estimate_seconds,
            'speedup_factor': self.speedup_factor,
            'max_concurrent_agents': self.max_concurrent_agents,
            'total_token_usage': self.total_token_usage,
            'failed_agent_count': self.failed_agent_count,
            'parallelization_strategy': self.parallelization_strategy,
            'fallback_to_sequential': self.fallback_to_sequential,
            'execution_metadata': self.execution_metadata,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Helper function to create all tables
def create_tables(engine):
    """Create all database tables.

    Args:
        engine: SQLAlchemy engine

    Example:
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine('sqlite:///test.db')
        >>> create_tables(engine)
    """
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """Drop all database tables.

    Args:
        engine: SQLAlchemy engine

    Example:
        >>> drop_tables(engine)  # For testing
    """
    Base.metadata.drop_all(engine)
