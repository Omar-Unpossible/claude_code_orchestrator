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
        entity_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format execution result as human-friendly response.

        Args:
            execution_result: Result from CommandExecutor
            intent: Intent type (COMMAND, QUESTION, CLARIFICATION_NEEDED)
            entity_details: Optional additional entity details

        Returns:
            Formatted response string with color codes

        Example:
            >>> formatter = ResponseFormatter()
            >>> result = ExecutionResult(success=True, created_ids=[5])
            >>> response = formatter.format(result, 'COMMAND')
        """
        if execution_result.confirmation_required:
            return self._format_confirmation(execution_result)

        if not execution_result.success:
            return self._format_error(execution_result)

        # Success case
        return self._format_success(execution_result, entity_details)

    def _format_success(
        self,
        result: ExecutionResult,
        entity_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format success response.

        Args:
            result: Successful execution result
            entity_details: Optional entity details

        Returns:
            Green-colored success message with next actions
        """
        entity_type = result.results.get('entity_type', 'item')
        created_count = len(result.created_ids)

        # Build main success message
        if created_count == 1:
            entity_id = result.created_ids[0]
            title = self._get_entity_title(result.results, entity_details)
            title_part = f": {title}" if title else ""

            message = (
                f"{Fore.GREEN}✓ Created {entity_type.title()} "
                f"#{entity_id}{title_part}{Style.RESET_ALL}"
            )
        else:
            message = (
                f"{Fore.GREEN}✓ Created {created_count} {entity_type}s: "
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
        action = result.results.get('action', 'operation')

        message = (
            f"{Fore.YELLOW}⚠ This will {action} {entity_type}. "
            f"Confirm? (y/n){Style.RESET_ALL}"
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

        # Epic not found
        if 'epic' in error_lower and 'not found' in error_lower:
            return "List epics with 'show epics' or create one first"

        # Story not found
        if 'story' in error_lower and 'not found' in error_lower:
            return "List stories with 'show stories' or create one first"

        # Missing required field
        if 'requires' in error_lower or 'required' in error_lower:
            return "Check required fields and try again"

        # Circular dependency
        if 'circular' in error_lower:
            return "Review task dependencies to remove cycles"

        # Database error
        if 'database' in error_lower or 'db' in error_lower:
            return "Check database connection and try again"

        # Generic recovery
        return "Review your command and try again"

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
