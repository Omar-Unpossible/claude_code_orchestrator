"""Question Handling for Natural Language Interface (ADR-016).

This module provides question handling for informational questions that don't
execute commands. This is the QUESTION path of the NL command pipeline.

Classes:
    QuestionHandler: Handles informational questions with StateManager integration

Example:
    >>> from plugins.ollama import OllamaLLMPlugin
    >>> from state.state_manager import StateManager
    >>> llm = OllamaLLMPlugin()
    >>> llm.initialize({'model': 'qwen2.5-coder:32b'})
    >>> state = StateManager(...)
    >>> handler = QuestionHandler(state, llm)
    >>> result = handler.handle("What's next for the tetris game?")
    >>> print(result.answer)
    "Next steps for Tetris Game: 1. Implement scoring (PENDING), 2. Add sound effects (PENDING)"
"""

import json
import logging
import re
from typing import Dict, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from plugins.base import LLMPlugin
from core.exceptions import OrchestratorException
from src.nl.base import QuestionHandlerInterface
from src.nl.types import QuestionType, QuestionResponse

logger = logging.getLogger(__name__)


class QuestionHandlingException(OrchestratorException):
    """Exception raised when question handling fails."""
    pass


class QuestionHandler(QuestionHandlerInterface):
    """Handles informational questions with StateManager integration.

    Processes questions through a 4-step pipeline:
        1. Classify question type (NEXT_STEPS/STATUS/BLOCKERS/PROGRESS/GENERAL)
        2. Extract entities from question (project name, epic ID, etc.)
        3. Query StateManager for relevant data
        4. Format helpful response

    Question Types:
        - NEXT_STEPS: "What's next?", "Next tasks for project X?"
        - STATUS: "What's the status?", "How's progress?", "Is it done?"
        - BLOCKERS: "What's blocking?", "Any issues?", "What's stuck?"
        - PROGRESS: "Show progress", "How far along?", "Completion %?"
        - GENERAL: Catch-all for other questions

    Args:
        state_manager: StateManager instance for querying data
        llm_plugin: LLM provider for question classification
        template_path: Path to Jinja2 template directory (default: prompts/)

    Example:
        >>> handler = QuestionHandler(state_manager, llm_plugin)
        >>> result = handler.handle("How's project 1 going?")
        >>> print(result.answer)  # "Project #1 'Tetris Game' is ACTIVE. 3/5 tasks completed (60%)"
        >>> print(result.question_type)  # QuestionType.STATUS
    """

    def __init__(
        self,
        state_manager,
        llm_plugin: LLMPlugin,
        template_path: Path = None
    ):
        """Initialize question handler with StateManager and LLM.

        Args:
            state_manager: StateManager instance for querying data
            llm_plugin: LLM provider for question classification
            template_path: Path to prompt templates (default: prompts/)

        Raises:
            QuestionHandlingException: If template not found
        """
        super().__init__(state_manager, llm_plugin)

        # Set up Jinja2 template environment
        if template_path is None:
            # Default to prompts/ directory relative to project root
            template_path = Path(__file__).parent.parent.parent / 'prompts'

        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(template_path)),
                trim_blocks=True,
                lstrip_blocks=True
            )
            # Verify template exists
            self.template = self.jinja_env.get_template('question_classification.j2')
        except TemplateNotFound as e:
            raise QuestionHandlingException(
                f"Question classification template not found: {e}",
                context={'template_path': str(template_path)},
                recovery="Ensure prompts/question_classification.j2 exists"
            )

        logger.info(f"QuestionHandler initialized with template_path={template_path}")

    def handle(self, user_input: str) -> QuestionResponse:
        """Handle a user question and return informational response.

        Args:
            user_input: User's question string

        Returns:
            QuestionResponse with formatted answer

        Raises:
            ValueError: If user_input is empty
            QuestionHandlingException: If question handling fails
        """
        if not user_input or not user_input.strip():
            raise ValueError("user_input cannot be empty")

        try:
            # Step 1: Classify question type
            question_type = self._classify_question_type(user_input)
            logger.info(f"Classified question as: {question_type.value}")

            # Step 2: Extract entities from question
            entities = self._extract_question_entities(user_input)
            logger.info(f"Extracted entities: {entities}")

            # Step 3: Query relevant data from StateManager
            data = self._query_relevant_data(question_type, entities)
            logger.info(f"Queried data: {len(data)} items")

            # Step 4: Format response
            answer = self._format_response(question_type, data)

            return QuestionResponse(
                answer=answer,
                question_type=question_type,
                entities=entities,
                data=data,
                confidence=0.9  # High confidence since we have data
            )

        except Exception as e:
            raise QuestionHandlingException(
                f"Failed to handle question: {e}",
                context={'user_input': user_input},
                recovery="Check LLM availability and StateManager connectivity"
            ) from e

    def _classify_question_type(self, question: str) -> QuestionType:
        """Classify question into NEXT_STEPS/STATUS/BLOCKERS/PROGRESS/GENERAL.

        Args:
            question: User's question string

        Returns:
            QuestionType enum value
        """
        # Build prompt
        prompt = self.template.render(user_question=question)

        try:
            # Call LLM
            response = self.llm.generate(prompt, max_tokens=150, temperature=0.1)

            # Parse response
            try:
                response_json = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group(0))
                else:
                    # Fallback: Look for question type keywords in text
                    response_upper = response.upper()
                    if 'NEXT_STEPS' in response_upper or 'NEXT STEPS' in response_upper:
                        return QuestionType.NEXT_STEPS
                    elif 'STATUS' in response_upper:
                        return QuestionType.STATUS
                    elif 'BLOCKER' in response_upper:
                        return QuestionType.BLOCKERS
                    elif 'PROGRESS' in response_upper:
                        return QuestionType.PROGRESS
                    else:
                        return QuestionType.GENERAL

            question_type_str = response_json.get('question_type', 'GENERAL').upper()

            # Map to QuestionType enum
            type_mapping = {
                'NEXT_STEPS': QuestionType.NEXT_STEPS,
                'NEXT STEPS': QuestionType.NEXT_STEPS,
                'STATUS': QuestionType.STATUS,
                'BLOCKERS': QuestionType.BLOCKERS,
                'BLOCKER': QuestionType.BLOCKERS,
                'PROGRESS': QuestionType.PROGRESS,
                'GENERAL': QuestionType.GENERAL
            }

            return type_mapping.get(question_type_str, QuestionType.GENERAL)

        except Exception as e:
            logger.warning(f"Failed to classify question type: {e}, defaulting to GENERAL")
            return QuestionType.GENERAL

    def _extract_question_entities(self, question: str) -> Dict[str, Any]:
        """Extract entities from question (project name, task ID, etc.).

        Uses pattern matching to extract common entity references.

        Args:
            question: User's question string

        Returns:
            Dictionary of extracted entities (e.g., {"project_name": "tetris game", "project_id": 1})
        """
        entities = {}

        # Pattern: project ID (project 1, project #3)
        project_id_match = re.search(r'project\s+#?(\d+)', question, re.IGNORECASE)
        if project_id_match:
            entities['project_id'] = int(project_id_match.group(1))

        # Pattern: epic ID (epic 2, epic #5)
        epic_id_match = re.search(r'epic\s+#?(\d+)', question, re.IGNORECASE)
        if epic_id_match:
            entities['epic_id'] = int(epic_id_match.group(1))

        # Pattern: task ID (task 3, task #7)
        task_id_match = re.search(r'task\s+#?(\d+)', question, re.IGNORECASE)
        if task_id_match:
            entities['task_id'] = int(task_id_match.group(1))

        # Pattern: project name (for X, for the X, X development, X project)
        # Common patterns: "for the tetris game", "tetris game development", "project tetris"
        name_patterns = [
            r'for\s+the\s+([\w\s]+?)(?:\s+development|\s+project|$|\?)',
            r'for\s+([\w\s]+?)(?:\s+development|\s+project|$|\?)',
            r'([\w\s]+?)\s+development',
            r'project\s+([\w\s]+?)(?:$|\?)',
        ]

        for pattern in name_patterns:
            name_match = re.search(pattern, question, re.IGNORECASE)
            if name_match:
                project_name = name_match.group(1).strip()
                # Filter out common question words
                if project_name.lower() not in ['what', 'how', 'when', 'where', 'why', 'is', 'the']:
                    entities['project_name'] = project_name
                    break

        return entities

    def _query_relevant_data(
        self,
        question_type: QuestionType,
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query StateManager for data relevant to question type.

        Args:
            question_type: Type of question being asked
            entities: Entities extracted from question

        Returns:
            Dictionary of relevant data (e.g., {"tasks": [...], "project": {...}})
        """
        data = {}

        try:
            # Get project if specified
            if 'project_id' in entities:
                project = self.state.get_project(entities['project_id'])
                if project:
                    data['project'] = {
                        'id': project.id,
                        'name': project.project_name,
                        'status': project.status,
                        'working_directory': project.working_directory
                    }
            elif 'project_name' in entities:
                # Try to find project by name
                projects = self.state.list_projects()
                for proj in projects:
                    if entities['project_name'].lower() in proj.project_name.lower():
                        data['project'] = {
                            'id': proj.id,
                            'name': proj.project_name,
                            'status': proj.status,
                            'working_directory': proj.working_directory
                        }
                        entities['project_id'] = proj.id  # Update for subsequent queries
                        break

            # Query based on question type
            if question_type == QuestionType.NEXT_STEPS:
                # Get pending tasks
                if 'project_id' in entities:
                    tasks = self.state.list_tasks(project_id=entities['project_id'], status='PENDING')
                    data['tasks'] = [self._task_to_dict(t) for t in tasks[:5]]  # Limit to 5
                else:
                    # Get next tasks across all projects
                    tasks = self.state.list_tasks(status='PENDING')
                    data['tasks'] = [self._task_to_dict(t) for t in tasks[:5]]

            elif question_type == QuestionType.STATUS:
                # Get project/task status info
                if 'project_id' in entities:
                    project_id = entities['project_id']
                    all_tasks = self.state.list_tasks(project_id=project_id)
                    completed = len([t for t in all_tasks if t.status == 'COMPLETED'])
                    data['total_tasks'] = len(all_tasks)
                    data['completed_tasks'] = completed
                    data['completion_percentage'] = int((completed / len(all_tasks) * 100)) if all_tasks else 0

            elif question_type == QuestionType.BLOCKERS:
                # Get blocked tasks
                if 'project_id' in entities:
                    blocked_tasks = self.state.list_tasks(project_id=entities['project_id'], status='BLOCKED')
                    data['blocked_tasks'] = [self._task_to_dict(t) for t in blocked_tasks]
                else:
                    blocked_tasks = self.state.list_tasks(status='BLOCKED')
                    data['blocked_tasks'] = [self._task_to_dict(t) for t in blocked_tasks[:5]]

            elif question_type == QuestionType.PROGRESS:
                # Get progress metrics
                if 'project_id' in entities:
                    project_id = entities['project_id']
                    all_tasks = self.state.list_tasks(project_id=project_id)
                    completed = len([t for t in all_tasks if t.status == 'COMPLETED'])
                    in_progress = len([t for t in all_tasks if t.status == 'IN_PROGRESS'])
                    pending = len([t for t in all_tasks if t.status == 'PENDING'])
                    data['total_tasks'] = len(all_tasks)
                    data['completed_tasks'] = completed
                    data['in_progress_tasks'] = in_progress
                    data['pending_tasks'] = pending
                    data['completion_percentage'] = int((completed / len(all_tasks) * 100)) if all_tasks else 0

        except Exception as e:
            logger.warning(f"Failed to query data: {e}")
            # Return empty data rather than failing

        return data

    def _format_response(
        self,
        question_type: QuestionType,
        data: Dict[str, Any]
    ) -> str:
        """Format informational response based on question type and data.

        Args:
            question_type: Type of question being asked
            data: Data from StateManager

        Returns:
            Formatted response string
        """
        if question_type == QuestionType.NEXT_STEPS:
            if 'tasks' in data and data['tasks']:
                project_info = ""
                if 'project' in data:
                    project_info = f" for {data['project']['name']}"

                tasks_str = "\n".join([
                    f"  {i+1}. {task['title']} (ID: {task['id']}, Priority: {task.get('priority', 'MEDIUM')})"
                    for i, task in enumerate(data['tasks'])
                ])
                return f"Next steps{project_info}:\n{tasks_str}"
            else:
                return "No pending tasks found."

        elif question_type == QuestionType.STATUS:
            if 'project' in data:
                proj = data['project']
                completion = data.get('completion_percentage', 0)
                completed = data.get('completed_tasks', 0)
                total = data.get('total_tasks', 0)
                return (
                    f"Project #{proj['id']} '{proj['name']}' is {proj['status']}. "
                    f"{completed}/{total} tasks completed ({completion}%)"
                )
            else:
                return "No project information available."

        elif question_type == QuestionType.BLOCKERS:
            if 'blocked_tasks' in data and data['blocked_tasks']:
                project_info = ""
                if 'project' in data:
                    project_info = f" in {data['project']['name']}"

                tasks_str = "\n".join([
                    f"  - Task #{task['id']}: {task['title']} (Reason: {task.get('blocked_reason', 'Not specified')})"
                    for task in data['blocked_tasks']
                ])
                return f"Blocked tasks{project_info}:\n{tasks_str}"
            else:
                return "No blocked tasks found."

        elif question_type == QuestionType.PROGRESS:
            if 'total_tasks' in data:
                project_info = ""
                if 'project' in data:
                    project_info = f" for {data['project']['name']}"

                return (
                    f"Progress{project_info}:\n"
                    f"  Total tasks: {data['total_tasks']}\n"
                    f"  Completed: {data.get('completed_tasks', 0)}\n"
                    f"  In Progress: {data.get('in_progress_tasks', 0)}\n"
                    f"  Pending: {data.get('pending_tasks', 0)}\n"
                    f"  Completion: {data.get('completion_percentage', 0)}%"
                )
            else:
                return "No progress information available."

        else:  # GENERAL
            return "I can help you with questions about tasks, projects, progress, and blockers. Try asking 'What's next?' or 'How's project 1 going?'"

    def _task_to_dict(self, task) -> Dict[str, Any]:
        """Convert task model to dictionary.

        Args:
            task: Task model instance

        Returns:
            Dictionary with task information
        """
        return {
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'priority': task.priority if hasattr(task, 'priority') else 'MEDIUM',
            'description': task.description if hasattr(task, 'description') else '',
            'blocked_reason': task.blocked_reason if hasattr(task, 'blocked_reason') else None
        }


__all__ = [
    "QuestionHandler",
    "QuestionHandlingException",
]
