"""Response Formatting for Natural Language Commands.

This module formats execution results into human-friendly responses with:
- Color coding (green=success, red=error, yellow=warning)
- Created IDs and entity details
- Recovery suggestions for errors
- Next action suggestions for success
- Clear confirmation/clarification prompts

Classes:
    ResponseFormatter: Formats execution results for user display

Example:
    >>> formatter = ResponseFormatter()
    >>> result = ExecutionResult(success=True, created_ids=[5])
    >>> response = formatter.format(result, intent='COMMAND')
    >>> print(response)  # ✓ Created Epic #5...
"""

import logging
from typing import Dict, Any, List, Optional
from colorama import Fore, Style, init as colorama_init
from nl.command_executor import ExecutionResult

logger = logging.getLogger(__name__)

# Initialize colorama for cross-platform colored output
colorama_init(autoreset=True)


class ResponseFormatter:
    """Formats execution results into human-friendly responses.

    Generates clear, actionable responses with color coding and helpful
    suggestions for next actions or error recovery.

    Example:
        >>> formatter = ResponseFormatter()
        >>> result = ExecutionResult(
        ...     success=True,
        ...     created_ids=[5],
        ...     results={'entity_type': 'epic', 'epic_title': 'User Auth'}
        ... )
        >>> response = formatter.format(result, intent='COMMAND')
        >>> print(response)
        ✓ Created Epic #5: User Auth
          Next: Add stories with 'add story to epic 5'
    """

    def __init__(self):
        """Initialize response formatter."""
        logger.info("ResponseFormatter initialized")

    def format(
        self,
        execution_result: ExecutionResult,
        intent: str,
        entity_details: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None
    ) -> str:
        """Format execution result as human-friendly response.

        Args:
            execution_result: Result from CommandExecutor
            intent: Intent type (COMMAND, QUESTION, CLARIFICATION_NEEDED)
            entity_details: Optional additional entity details
            operation: Optional operation type (create, update, delete, query)

        Returns:
            Formatted response string with color codes

        Example:
            >>> formatter = ResponseFormatter()
            >>> result = ExecutionResult(success=True, created_ids=[5])
            >>> response = formatter.format(result, 'COMMAND', operation='create')
        """
        if execution_result.confirmation_required:
            return self._format_confirmation(execution_result)

        if not execution_result.success:
            return self._format_error(execution_result)

        # Success case
        return self._format_success(execution_result, entity_details, operation)

    def _format_success(
        self,
        result: ExecutionResult,
        entity_details: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None
    ) -> str:
        """Format success response.

        Args:
            result: Successful execution result
            entity_details: Optional entity details
            operation: Optional operation type (create, update, delete, query)

        Returns:
            Green-colored success message with next actions
        """
        entity_type = result.results.get('entity_type', 'item')

        # Check if this is a QUERY operation
        if operation == 'query' or result.results.get('operation') == 'query' or result.results.get('query_type'):
            # Format as a list response
            entities = result.results.get('entities', [])
            count = result.results.get('count', len(entities))

            if count == 0:
                return f"{Fore.YELLOW}No {entity_type}s found{Style.RESET_ALL}"

            # Format the list
            return self.format_list_response(entities, entity_type)

        # CREATE/UPDATE/DELETE operations
        created_count = len(result.created_ids)

        # Build main success message
        if created_count == 1:
            entity_id = result.created_ids[0]
            title = self._get_entity_title(result.results, entity_details)
            title_part = f": {title}" if title else ""

            action = "Created" if operation == 'create' else "Updated" if operation == 'update' else "Deleted" if operation == 'delete' else "Created"

            message = (
                f"{Fore.GREEN}✓ {action} {entity_type.title()} "
                f"#{entity_id}{title_part}{Style.RESET_ALL}"
            )
        else:
            action = "Created" if operation == 'create' else "Updated" if operation == 'update' else "Deleted" if operation == 'delete' else "Created"
            message = (
                f"{Fore.GREEN}✓ {action} {created_count} {entity_type}s: "
                f"{', '.join(f'#{id}' for id in result.created_ids)}"
                f"{Style.RESET_ALL}"
            )

        # Add next action suggestion
        next_action = self._suggest_next_action(entity_type, result.created_ids)
        if next_action:
            message += f"\n  {Fore.CYAN}Next: {next_action}{Style.RESET_ALL}"

        return message

    def _format_error(self, result: ExecutionResult) -> str:
        """Format error response.

        Args:
            result: Failed execution result

        Returns:
            Red-colored error message with recovery suggestions
        """
        if not result.errors:
            return f"{Fore.RED}✗ Error: Unknown error occurred{Style.RESET_ALL}"

        # Main error message
        error_msg = result.errors[0]
        message = f"{Fore.RED}✗ Error: {error_msg}{Style.RESET_ALL}"

        # Add recovery suggestion
        recovery = self._suggest_recovery(error_msg, result.results)
        if recovery:
            message += f"\n  {Fore.YELLOW}Try: {recovery}{Style.RESET_ALL}"

        # Add additional errors if any
        if len(result.errors) > 1:
            message += f"\n  {Fore.YELLOW}({len(result.errors)-1} more errors)"
            message += f"{Style.RESET_ALL}"

        return message

    def _format_confirmation(self, result: ExecutionResult) -> str:
        """Format confirmation prompt.

        Args:
            result: Execution result requiring confirmation

        Returns:
            Yellow-colored confirmation prompt
        """
        entity_type = result.results.get('entity_type', 'item')
        operation = result.results.get('operation', 'modify')
        identifier = result.results.get('identifier')

        # Build identifier part
        identifier_part = ""
        if identifier is not None:
            if isinstance(identifier, int):
                identifier_part = f" #{identifier}"
            else:
                identifier_part = f" '{identifier}'"

        message = (
            f"{Fore.YELLOW}⚠ Confirmation required:{Style.RESET_ALL}\n"
            f"  This will {operation} {entity_type}{identifier_part}.\n"
            f"\n"
            f"  Type 'yes' to confirm, 'no' to cancel"
        )
        return message

    def format_clarification_request(
        self,
        message: str,
        suggestions: Optional[List[str]] = None
    ) -> str:
        """Format clarification request.

        Args:
            message: Clarification message
            suggestions: Optional list of suggested interpretations

        Returns:
            Yellow-colored clarification prompt with suggestions

        Example:
            >>> formatter = ResponseFormatter()
            >>> response = formatter.format_clarification_request(
            ...     "Did you mean:",
            ...     ["Create epic 'User Dashboard'", "List existing epics"]
            ... )
        """
        response = f"{Fore.YELLOW}? {message}{Style.RESET_ALL}"

        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                response += f"\n  {i}. {suggestion}"
            response += "\n  0. Something else (please clarify)"

        return response

    def format_info_response(self, content: str) -> str:
        """Format informational response (for QUESTION intent).

        Args:
            content: Information content

        Returns:
            Plain text information (no special formatting)

        Example:
            >>> formatter = ResponseFormatter()
            >>> response = formatter.format_info_response(
            ...     "You have 3 epics: ..."
            ... )
        """
        return content

    def _get_entity_title(
        self,
        results: Dict[str, Any],
        entity_details: Optional[Dict[str, Any]]
    ) -> str:
        """Extract entity title from results or details.

        Args:
            results: Execution results
            entity_details: Optional entity details

        Returns:
            Entity title or empty string
        """
        # Try common title fields
        for key in ['title', 'name', 'epic_title', 'story_title', 'task_title']:
            if key in results:
                return results[key]
            if entity_details and key in entity_details:
                return entity_details[key]

        return ""

    def _suggest_next_action(
        self,
        entity_type: str,
        created_ids: List[int]
    ) -> str:
        """Suggest next action after successful creation.

        Args:
            entity_type: Type of entity created
            created_ids: List of created IDs

        Returns:
            Suggested next action string
        """
        if entity_type == 'epic':
            epic_id = created_ids[0]
            return f"Add stories with 'create story in epic {epic_id}'"
        elif entity_type == 'story':
            story_id = created_ids[0]
            return f"Add tasks with 'create task in story {story_id}'"
        elif entity_type == 'task':
            return "Execute task or add subtasks"
        elif entity_type == 'milestone':
            return "Check milestone completion status"
        else:
            return ""

    def _suggest_recovery(
        self,
        error_msg: str,
        results: Dict[str, Any]
    ) -> str:
        """Suggest recovery action for error.

        Args:
            error_msg: Error message
            results: Execution results

        Returns:
            Recovery suggestion string
        """
        error_lower = error_msg.lower()

        # Entity not found - provide list command
        if 'not found' in error_lower:
            entity_type = results.get('entity_type', 'item')
            if entity_type in ['epic', 'story', 'task', 'project', 'milestone']:
                return f"List {entity_type}s with 'list {entity_type}s' to see available options"
            return "List available items to see what exists"

        # Missing required field - be specific
        if 'requires' in error_lower or 'required' in error_lower:
            if 'epic_id' in error_lower or 'epic' in error_lower:
                return "Specify epic with 'in epic <id>' or 'for epic <name>'"
            elif 'story_id' in error_lower or 'story' in error_lower:
                return "Specify story with 'in story <id>' or 'for story <name>'"
            elif 'parent_task_id' in error_lower or 'parent' in error_lower:
                return "Specify parent task with 'under task <id>'"
            elif 'title' in error_lower or 'name' in error_lower:
                return "Add a title/name: 'create epic \"My Epic Name\"'"
            return "Check required fields and try again"

        # Circular dependency
        if 'circular' in error_lower or 'cycle' in error_lower:
            return "Remove the circular dependency: task A depends on B, B depends on A"

        # Confirmation required (should not normally happen)
        if 'confirmation' in error_lower:
            return "Confirmation prompt should appear - this may be a bug"

        # Database/connection errors
        if 'database' in error_lower or 'connection' in error_lower:
            return "Database connection issue. Check logs and try again"

        # Permission/access errors
        if 'permission' in error_lower or 'access' in error_lower:
            return "Check file permissions and working directory access"

        # Invalid parameter values
        if 'invalid' in error_lower:
            if 'priority' in error_lower:
                return "Priority must be 1-10 or HIGH/MEDIUM/LOW"
            if 'status' in error_lower:
                return "Status must be PENDING/RUNNING/COMPLETED/BLOCKED/READY"
            return "Check parameter values and try again"

        # Transaction/lock errors
        if 'transaction' in error_lower or 'lock' in error_lower:
            return "Database lock detected. Wait a moment and try again"

        # Generic recovery with help hint
        return "Try rephrasing your command or type 'help' for examples"

    def format_error_with_examples(
        self,
        result: ExecutionResult,
        operation: Optional[str] = None
    ) -> str:
        """Format error with command examples.

        Args:
            result: Execution result with error
            operation: Optional operation type (create, update, delete, query)

        Returns:
            Formatted error message with examples

        Example:
            >>> formatter = ResponseFormatter()
            >>> result = ExecutionResult(success=False, errors=['Project not found'])
            >>> response = formatter.format_error_with_examples(result, 'create')
        """
        # Get base error message
        base_error = self._format_error(result)

        # Add examples if we have operation and entity type
        entity_type = result.results.get('entity_type')
        if operation and entity_type:
            examples = self._get_examples(entity_type, operation)
            if examples:
                base_error += f"\n\n{Fore.CYAN}Examples:{Style.RESET_ALL}"
                for example in examples:
                    base_error += f"\n  • {example}"

        return base_error

    def _get_examples(self, entity_type: str, operation: str) -> List[str]:
        """Get example commands for entity type and operation.

        Args:
            entity_type: Entity type (project, epic, story, task, milestone)
            operation: Operation type (create, update, delete, query)

        Returns:
            List of example command strings
        """
        examples_map = {
            ('project', 'create'): [
                "create project 'My New Project'",
                "create project for mobile app",
            ],
            ('project', 'update'): [
                "update project 5 status to completed",
                "mark project 'Mobile App' as inactive",
            ],
            ('project', 'query'): [
                "list projects",
                "show all projects",
                "show project status",
            ],
            ('epic', 'create'): [
                "create epic for user authentication",
                "add epic 'Payment System' to project 1",
            ],
            ('epic', 'update'): [
                "update epic 3 status to blocked",
                "mark epic 'Auth System' as completed",
            ],
            ('epic', 'query'): [
                "list epics",
                "show all epics",
                "list epics for project 1",
            ],
            ('story', 'create'): [
                "create story in epic 5",
                "add story 'User Login' for epic 3",
            ],
            ('story', 'update'): [
                "update story 7 priority to high",
                "mark story 2 as completed",
            ],
            ('story', 'query'): [
                "list stories",
                "show stories for epic 5",
            ],
            ('task', 'create'): [
                "create task with priority HIGH",
                "add task 'Write tests' in story 3",
            ],
            ('task', 'update'): [
                "update task 10 status to running",
                "change task 5 priority to LOW",
            ],
            ('task', 'query'): [
                "list tasks",
                "show tasks for story 5",
                "show my tasks",
            ],
            ('milestone', 'create'): [
                "create milestone 'MVP Release'",
                "add milestone for epic completion",
            ],
            ('milestone', 'query'): [
                "list milestones",
                "show milestone status",
            ],
        }

        return examples_map.get((entity_type, operation), [])

    def format_list_response(
        self,
        items: List[Dict[str, Any]],
        entity_type: str
    ) -> str:
        """Format list of items for display.

        Args:
            items: List of items to display
            entity_type: Type of entities

        Returns:
            Formatted list

        Example:
            >>> formatter = ResponseFormatter()
            >>> items = [
            ...     {'id': 1, 'title': 'Epic 1'},
            ...     {'id': 2, 'title': 'Epic 2'}
            ... ]
            >>> response = formatter.format_list_response(items, 'epic')
        """
        if not items:
            return f"{Fore.YELLOW}No {entity_type}s found{Style.RESET_ALL}"

        header = f"{Fore.CYAN}{len(items)} {entity_type}(s):{Style.RESET_ALL}"
        lines = [header]

        for item in items:
            item_id = item.get('id', '?')
            title = item.get('title') or item.get('name', 'Untitled')
            status = item.get('status', '')

            status_part = f" ({status})" if status else ""
            lines.append(f"  #{item_id}: {title}{status_part}")

        return "\n".join(lines)
