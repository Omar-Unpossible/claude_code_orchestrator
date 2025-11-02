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
            'context': self.context
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
