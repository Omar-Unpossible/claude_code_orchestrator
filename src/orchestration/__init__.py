"""Orchestration engine for task scheduling, decision making, and quality control.

This package provides the core orchestration logic:
- TaskScheduler: Task queue management with dependency resolution
- DecisionEngine: Intelligent decision making and action routing
- BreakpointManager: Breakpoint triggering and resolution tracking
- QualityController: Multi-stage quality validation

Architecture:
    The orchestration engine coordinates between agents, LLMs, and file monitoring
    to autonomously execute tasks while maintaining quality and triggering human
    intervention when needed.

Example:
    >>> from src.orchestration import TaskScheduler, DecisionEngine
    >>> scheduler = TaskScheduler(state_manager)
    >>> engine = DecisionEngine(state_manager, config)
    >>>
    >>> # Schedule tasks
    >>> scheduler.schedule_task(task1)
    >>> scheduler.schedule_task(task2)
    >>>
    >>> # Execute tasks
    >>> task = scheduler.get_next_task(project_id)
    >>> action = engine.decide_next_action(context)
"""

from src.orchestration.task_scheduler import TaskScheduler
from src.orchestration.breakpoint_manager import BreakpointManager, BreakpointEvent
from src.orchestration.decision_engine import DecisionEngine, Action
from src.orchestration.quality_controller import QualityController, QualityResult

__all__ = [
    'TaskScheduler',
    'BreakpointManager',
    'BreakpointEvent',
    'DecisionEngine',
    'Action',
    'QualityController',
    'QualityResult'
]
