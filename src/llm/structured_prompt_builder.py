"""StructuredPromptBuilder - Builds structured prompts with JSON metadata and natural language.

This module provides the StructuredPromptBuilder class for creating hybrid prompts that combine:
- JSON metadata section with task context, rules, and expectations
- Natural language instruction section for clear task description

Part of the LLM-first prompt engineering framework (PHASE_3).

Key Features:
- Hybrid prompt format (JSON metadata + natural language)
- Integration with PromptRuleEngine for rule injection
- Multiple prompt types: task_execution, validation, error_analysis, decision, planning
- Template-based instruction generation
- Type-safe design with comprehensive docstrings
"""

import json
import logging
from threading import RLock
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from src.llm.prompt_rule import PromptRule
from src.llm.prompt_rule_engine import PromptRuleEngine

if TYPE_CHECKING:
    from src.orchestration.complexity_estimate import ComplexityEstimate

logger = logging.getLogger(__name__)


class StructuredPromptBuilderException(Exception):
    """Base exception for StructuredPromptBuilder errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            context: Optional context dict
        """
        super().__init__(message)
        self.context = context or {}


class StructuredPromptBuilder:
    """Builds structured prompts combining JSON metadata with natural language instructions.

    The StructuredPromptBuilder creates hybrid prompts with two sections:
    1. METADATA section - JSON with task context, rules, expectations
    2. INSTRUCTION section - Natural language task description

    Integrates with PromptRuleEngine to inject applicable rules based on
    prompt type and domains.

    Supports optional complexity analysis for parallelization suggestions.

    Thread-safe with internal locking for concurrent access.

    Example:
        >>> rule_engine = PromptRuleEngine('config/prompt_rules.yaml')
        >>> rule_engine.load_rules_from_yaml()
        >>>
        >>> builder = StructuredPromptBuilder(rule_engine=rule_engine)
        >>>
        >>> prompt = builder.build_task_execution_prompt(
        ...     task_data={
        ...         'task_id': 123,
        ...         'title': 'Implement authentication',
        ...         'description': 'Add user authentication with JWT tokens'
        ...     },
        ...     context={
        ...         'project_id': 1,
        ...         'files': ['auth.py', 'models.py'],
        ...         'dependencies': ['PyJWT']
        ...     }
        ... )
        >>> print(prompt)
        <METADATA>
        {
          "prompt_type": "task_execution",
          "task_id": 123,
          "context": {...},
          "rules": [...],
          "expectations": {...}
        }
        </METADATA>

        <INSTRUCTION>
        Implement the following task: Implement authentication

        Description:
        Add user authentication with JWT tokens

        Requirements:
        - Follow all specified rules
        - Implement complete, working code (no stubs)
        - Include proper error handling
        - Add comprehensive tests
        </INSTRUCTION>
    """

    # Prompt type constants
    PROMPT_TYPE_TASK_EXECUTION = 'task_execution'
    PROMPT_TYPE_VALIDATION = 'validation'
    PROMPT_TYPE_ERROR_ANALYSIS = 'error_analysis'
    PROMPT_TYPE_DECISION = 'decision'
    PROMPT_TYPE_PLANNING = 'planning'

    # Valid prompt types
    VALID_PROMPT_TYPES = {
        PROMPT_TYPE_TASK_EXECUTION,
        PROMPT_TYPE_VALIDATION,
        PROMPT_TYPE_ERROR_ANALYSIS,
        PROMPT_TYPE_DECISION,
        PROMPT_TYPE_PLANNING
    }

    def __init__(self, rule_engine: Optional[PromptRuleEngine] = None):
        """Initialize StructuredPromptBuilder.

        Args:
            rule_engine: Optional PromptRuleEngine for rule injection.
                        If None, prompts will not include rules.

        Example:
            >>> # With rule engine
            >>> engine = PromptRuleEngine('config/prompt_rules.yaml')
            >>> engine.load_rules_from_yaml()
            >>> builder = StructuredPromptBuilder(rule_engine=engine)
            >>>
            >>> # Without rule engine
            >>> builder = StructuredPromptBuilder()
        """
        self.rule_engine = rule_engine
        self._lock = RLock()

        # Statistics
        self.stats = {
            'prompts_built': 0,
            'task_execution_count': 0,
            'validation_count': 0,
            'error_analysis_count': 0,
            'decision_count': 0,
            'planning_count': 0,
            'rules_injected_total': 0
        }

        logger.info(
            f"StructuredPromptBuilder initialized "
            f"(rule_engine={'enabled' if rule_engine else 'disabled'})"
        )

    def build_task_execution_prompt(
        self,
        task_data: Dict[str, Any],
        context: Dict[str, Any],
        complexity_estimate: Optional['ComplexityEstimate'] = None
    ) -> str:
        """Build task execution prompt with metadata and instructions.

        Creates a structured prompt for executing a development task.
        Injects rules from domains: code_generation, testing, documentation, security.
        Optionally includes complexity analysis for parallelization suggestions.

        Args:
            task_data: Task information with keys:
                - task_id: int - Unique task identifier
                - title: str - Task title
                - description: str - Detailed task description
                - constraints: Optional[List[str]] - Task constraints
                - acceptance_criteria: Optional[List[str]] - Success criteria
            context: Execution context with keys:
                - project_id: Optional[int] - Project identifier
                - files: Optional[List[str]] - Relevant file paths
                - dependencies: Optional[List[str]] - Required dependencies
                - working_directory: Optional[str] - Workspace path
            complexity_estimate: Optional complexity analysis with Obra's parallelization suggestions

        Returns:
            Structured prompt string with metadata and instruction sections

        Raises:
            StructuredPromptBuilderException: If required task_data fields missing

        Example:
            >>> prompt = builder.build_task_execution_prompt(
            ...     task_data={
            ...         'task_id': 1,
            ...         'title': 'Add logging',
            ...         'description': 'Implement structured logging with rotating files',
            ...         'constraints': ['Use stdlib logging', 'Max file size 10MB'],
            ...         'acceptance_criteria': ['Logs rotate correctly', 'Tests pass']
            ...     },
            ...     context={
            ...         'project_id': 1,
            ...         'files': ['logger.py'],
            ...         'dependencies': []
            ...     }
            ... )
        """
        with self._lock:
            # Validate required fields
            required_fields = ['task_id', 'title', 'description']
            missing = [f for f in required_fields if f not in task_data]
            if missing:
                raise StructuredPromptBuilderException(
                    f"Missing required task_data fields: {', '.join(missing)}",
                    context={'task_data': task_data}
                )

            # Build metadata
            metadata = {
                'prompt_type': self.PROMPT_TYPE_TASK_EXECUTION,
                'task_id': task_data['task_id'],
                'task_title': task_data['title'],
                'context': context,
                'expectations': {
                    'complete_implementation': True,
                    'no_stubs': True,
                    'include_tests': True,
                    'error_handling': True,
                    'documentation': True
                }
            }

            # Add optional fields
            if 'constraints' in task_data:
                metadata['constraints'] = task_data['constraints']
            if 'acceptance_criteria' in task_data:
                metadata['acceptance_criteria'] = task_data['acceptance_criteria']

            # Add complexity analysis if provided
            if complexity_estimate:
                metadata['complexity_analysis'] = complexity_estimate.to_suggestion_dict()

            # Inject rules for task execution domains
            domains = ['code_generation', 'testing', 'documentation', 'security']
            metadata = self._inject_rules(
                metadata,
                self.PROMPT_TYPE_TASK_EXECUTION,
                domains
            )

            # Build instruction
            instruction = f"""Implement the following task: {task_data['title']}

Description:
{task_data['description']}

Requirements:
- Follow all specified rules
- Implement complete, working code (no stubs or placeholders)
- Include proper error handling
- Add comprehensive tests
- Document all public APIs"""

            # Add constraints if present
            if 'constraints' in task_data and task_data['constraints']:
                instruction += "\n\nConstraints:\n"
                for constraint in task_data['constraints']:
                    instruction += f"- {constraint}\n"

            # Add acceptance criteria if present
            if 'acceptance_criteria' in task_data and task_data['acceptance_criteria']:
                instruction += "\n\nAcceptance Criteria:\n"
                for criterion in task_data['acceptance_criteria']:
                    instruction += f"- {criterion}\n"

            # Add parallelization query if complexity suggests decomposition
            if complexity_estimate and complexity_estimate.obra_suggests_decomposition:
                instruction += self._build_parallelization_query(complexity_estimate)

            # Format hybrid prompt
            prompt = self._format_hybrid_prompt(metadata, instruction)

            # Update statistics
            self.stats['prompts_built'] += 1
            self.stats['task_execution_count'] += 1

            logger.debug(
                f"Built task_execution prompt for task {task_data['task_id']} "
                f"({len(metadata.get('rules', []))} rules injected)"
            )

            return prompt

    def build_validation_prompt(
        self,
        code: str,
        rules: List[PromptRule]
    ) -> str:
        """Build validation prompt for code review against rules.

        Creates a structured prompt for validating code against specific rules.

        Args:
            code: Source code to validate
            rules: List of PromptRule objects to check against

        Returns:
            Structured prompt string for code validation

        Example:
            >>> rules = rule_engine.get_rules_for_domain('code_generation')
            >>> prompt = builder.build_validation_prompt(
            ...     code='def func():\\n    pass',
            ...     rules=rules
            ... )
        """
        with self._lock:
            # Build metadata
            metadata = {
                'prompt_type': self.PROMPT_TYPE_VALIDATION,
                'code_length': len(code),
                'rules': [
                    {
                        'id': rule.id,
                        'name': rule.name,
                        'description': rule.description,
                        'severity': rule.severity,
                        'validation_type': rule.validation_type
                    }
                    for rule in rules
                ],
                'expectations': {
                    'detailed_violations': True,
                    'location_info': True,
                    'suggestions': True
                }
            }

            # Build instruction
            instruction = f"""Validate the following code against the specified rules:

```
{code}
```

For each rule violation found:
1. Identify the rule ID and name
2. Specify the exact location (file, line, column if applicable)
3. Explain why it violates the rule
4. Provide a specific suggestion for fixing the violation

If no violations are found, explicitly state that the code passes validation."""

            # Format hybrid prompt
            prompt = self._format_hybrid_prompt(metadata, instruction)

            # Update statistics
            self.stats['prompts_built'] += 1
            self.stats['validation_count'] += 1

            logger.debug(
                f"Built validation prompt for {len(code)} chars code "
                f"with {len(rules)} rules"
            )

            return prompt

    def build_error_analysis_prompt(
        self,
        error_data: Dict[str, Any]
    ) -> str:
        """Build error analysis prompt for diagnosing and fixing errors.

        Creates a structured prompt for analyzing errors and generating fixes.
        Injects rules from domains: error_handling, performance.

        Args:
            error_data: Error information with keys:
                - error_type: str - Type of error (e.g., 'RuntimeError')
                - error_message: str - Error message
                - traceback: str - Full traceback
                - context: Optional[Dict] - Additional context (file, line, code)
                - previous_attempts: Optional[List[str]] - Previous fix attempts

        Returns:
            Structured prompt string for error analysis

        Raises:
            StructuredPromptBuilderException: If required error_data fields missing

        Example:
            >>> prompt = builder.build_error_analysis_prompt(
            ...     error_data={
            ...         'error_type': 'AttributeError',
            ...         'error_message': "'NoneType' object has no attribute 'value'",
            ...         'traceback': 'Traceback (most recent call last)...',
            ...         'context': {
            ...             'file': 'app.py',
            ...             'line': 42,
            ...             'code': 'result = obj.value'
            ...         }
            ...     }
            ... )
        """
        with self._lock:
            # Validate required fields
            required_fields = ['error_type', 'error_message', 'traceback']
            missing = [f for f in required_fields if f not in error_data]
            if missing:
                raise StructuredPromptBuilderException(
                    f"Missing required error_data fields: {', '.join(missing)}",
                    context={'error_data': error_data}
                )

            # Build metadata
            metadata = {
                'prompt_type': self.PROMPT_TYPE_ERROR_ANALYSIS,
                'error_type': error_data['error_type'],
                'error_message': error_data['error_message'],
                'expectations': {
                    'root_cause_analysis': True,
                    'fix_suggestions': True,
                    'prevention_strategies': True
                }
            }

            # Add optional context
            if 'context' in error_data:
                metadata['context'] = error_data['context']
            if 'previous_attempts' in error_data:
                metadata['previous_attempts'] = error_data['previous_attempts']

            # Inject rules for error analysis domains
            domains = ['error_handling', 'performance']
            metadata = self._inject_rules(
                metadata,
                self.PROMPT_TYPE_ERROR_ANALYSIS,
                domains
            )

            # Build instruction
            instruction = f"""Analyze the following error and provide a fix:

Error Type: {error_data['error_type']}
Error Message: {error_data['error_message']}

Traceback:
```
{error_data['traceback']}
```"""

            # Add context if present
            if 'context' in error_data and error_data['context']:
                ctx = error_data['context']
                instruction += f"\n\nContext:\n"
                if 'file' in ctx:
                    instruction += f"- File: {ctx['file']}\n"
                if 'line' in ctx:
                    instruction += f"- Line: {ctx['line']}\n"
                if 'code' in ctx:
                    instruction += f"- Code:\n```\n{ctx['code']}\n```\n"

            # Add previous attempts if present
            if 'previous_attempts' in error_data and error_data['previous_attempts']:
                instruction += "\n\nPrevious Fix Attempts (unsuccessful):\n"
                for i, attempt in enumerate(error_data['previous_attempts'], 1):
                    instruction += f"{i}. {attempt}\n"

            instruction += """
Please provide:
1. Root cause analysis - What caused this error?
2. Recommended fix - Specific code changes to resolve the error
3. Prevention strategies - How to avoid this error in the future"""

            # Format hybrid prompt
            prompt = self._format_hybrid_prompt(metadata, instruction)

            # Update statistics
            self.stats['prompts_built'] += 1
            self.stats['error_analysis_count'] += 1

            logger.debug(
                f"Built error_analysis prompt for {error_data['error_type']} "
                f"({len(metadata.get('rules', []))} rules injected)"
            )

            return prompt

    def build_decision_prompt(
        self,
        decision_context: Dict[str, Any]
    ) -> str:
        """Build decision prompt for orchestration decisions.

        Creates a structured prompt for making orchestration decisions
        (proceed, retry, clarify, escalate).

        Args:
            decision_context: Decision context with keys:
                - task_id: int - Task identifier
                - current_state: str - Current task state
                - validation_result: Dict - Validation outcome
                - quality_score: Optional[float] - Quality score (0.0-1.0)
                - confidence_score: Optional[float] - Confidence score (0.0-1.0)
                - retry_count: Optional[int] - Number of retries so far
                - options: Optional[List[str]] - Available decision options

        Returns:
            Structured prompt string for decision making

        Raises:
            StructuredPromptBuilderException: If required fields missing

        Example:
            >>> prompt = builder.build_decision_prompt(
            ...     decision_context={
            ...         'task_id': 1,
            ...         'current_state': 'validation_complete',
            ...         'validation_result': {'is_valid': True},
            ...         'quality_score': 0.85,
            ...         'confidence_score': 0.92,
            ...         'retry_count': 0
            ...     }
            ... )
        """
        with self._lock:
            # Validate required fields
            required_fields = ['task_id', 'current_state', 'validation_result']
            missing = [f for f in required_fields if f not in decision_context]
            if missing:
                raise StructuredPromptBuilderException(
                    f"Missing required decision_context fields: {', '.join(missing)}",
                    context={'decision_context': decision_context}
                )

            # Build metadata
            metadata = {
                'prompt_type': self.PROMPT_TYPE_DECISION,
                'task_id': decision_context['task_id'],
                'current_state': decision_context['current_state'],
                'validation_result': decision_context['validation_result'],
                'expectations': {
                    'decision': True,
                    'reasoning': True,
                    'confidence': True
                }
            }

            # Add optional fields
            if 'quality_score' in decision_context:
                metadata['quality_score'] = decision_context['quality_score']
            if 'confidence_score' in decision_context:
                metadata['confidence_score'] = decision_context['confidence_score']
            if 'retry_count' in decision_context:
                metadata['retry_count'] = decision_context['retry_count']
            if 'options' in decision_context:
                metadata['options'] = decision_context['options']

            # No rule injection for decision prompts (domain-agnostic)

            # Build instruction
            instruction = f"""Make an orchestration decision for the current task state.

Task ID: {decision_context['task_id']}
Current State: {decision_context['current_state']}

Validation Result:
{json.dumps(decision_context['validation_result'], indent=2)}
"""

            # Add quality/confidence scores if present
            if 'quality_score' in decision_context:
                instruction += f"\nQuality Score: {decision_context['quality_score']:.2f}"
            if 'confidence_score' in decision_context:
                instruction += f"\nConfidence Score: {decision_context['confidence_score']:.2f}"
            if 'retry_count' in decision_context:
                instruction += f"\nRetry Count: {decision_context['retry_count']}"

            instruction += """

Available Decisions:
- PROCEED: Continue to next step (task is complete and valid)
- RETRY: Retry the current step (minor issues, likely to succeed)
- CLARIFY: Request human clarification (ambiguous requirements)
- ESCALATE: Escalate to human (critical issues, low confidence)

Provide:
1. Decision - Which action to take
2. Reasoning - Why this decision is appropriate
3. Confidence - How confident you are in this decision (0.0-1.0)"""

            # Format hybrid prompt
            prompt = self._format_hybrid_prompt(metadata, instruction)

            # Update statistics
            self.stats['prompts_built'] += 1
            self.stats['decision_count'] += 1

            logger.debug(
                f"Built decision prompt for task {decision_context['task_id']}"
            )

            return prompt

    def build_planning_prompt(
        self,
        planning_data: Dict[str, Any]
    ) -> str:
        """Build planning prompt for task decomposition and planning.

        Creates a structured prompt for breaking down complex tasks into
        subtasks and planning execution strategy.
        Injects rules from domains: code_generation, parallel_agents.

        Args:
            planning_data: Planning information with keys:
                - task_id: int - Main task identifier
                - task_description: str - High-level task description
                - project_context: Dict - Project information
                - constraints: Optional[List[str]] - Planning constraints
                - available_resources: Optional[Dict] - Available resources

        Returns:
            Structured prompt string for planning

        Raises:
            StructuredPromptBuilderException: If required fields missing

        Example:
            >>> prompt = builder.build_planning_prompt(
            ...     planning_data={
            ...         'task_id': 1,
            ...         'task_description': 'Build REST API for user management',
            ...         'project_context': {
            ...             'language': 'Python',
            ...             'framework': 'Flask'
            ...         },
            ...         'constraints': ['Must use JWT auth', 'PostgreSQL only']
            ...     }
            ... )
        """
        with self._lock:
            # Validate required fields
            required_fields = ['task_id', 'task_description', 'project_context']
            missing = [f for f in required_fields if f not in planning_data]
            if missing:
                raise StructuredPromptBuilderException(
                    f"Missing required planning_data fields: {', '.join(missing)}",
                    context={'planning_data': planning_data}
                )

            # Build metadata
            metadata = {
                'prompt_type': self.PROMPT_TYPE_PLANNING,
                'task_id': planning_data['task_id'],
                'project_context': planning_data['project_context'],
                'expectations': {
                    'subtask_breakdown': True,
                    'execution_order': True,
                    'dependencies': True,
                    'resource_allocation': True
                }
            }

            # Add optional fields
            if 'constraints' in planning_data:
                metadata['constraints'] = planning_data['constraints']
            if 'available_resources' in planning_data:
                metadata['available_resources'] = planning_data['available_resources']

            # Inject rules for planning domains
            domains = ['code_generation', 'parallel_agents']
            metadata = self._inject_rules(
                metadata,
                self.PROMPT_TYPE_PLANNING,
                domains
            )

            # Build instruction
            instruction = f"""Create an execution plan for the following task:

Task Description:
{planning_data['task_description']}

Project Context:
{json.dumps(planning_data['project_context'], indent=2)}
"""

            # Add constraints if present
            if 'constraints' in planning_data and planning_data['constraints']:
                instruction += "\n\nConstraints:\n"
                for constraint in planning_data['constraints']:
                    instruction += f"- {constraint}\n"

            instruction += """
Please provide:
1. Subtask Breakdown - Break the task into smaller, manageable subtasks
2. Execution Order - Specify the order and dependencies between subtasks
3. Resource Allocation - Identify required resources for each subtask
4. Risk Assessment - Identify potential risks and mitigation strategies"""

            # Format hybrid prompt
            prompt = self._format_hybrid_prompt(metadata, instruction)

            # Update statistics
            self.stats['prompts_built'] += 1
            self.stats['planning_count'] += 1

            logger.debug(
                f"Built planning prompt for task {planning_data['task_id']} "
                f"({len(metadata.get('rules', []))} rules injected)"
            )

            return prompt

    def _build_parallelization_query(
        self,
        complexity_estimate: 'ComplexityEstimate'
    ) -> str:
        """
        Build parallelization query section for Claude.

        This section asks Claude to consider parallel execution using Task tool.

        Args:
            complexity_estimate: Complexity estimate with Obra's suggestions

        Returns:
            Formatted parallelization query string
        """
        query = {
            "parallelization_consideration": {
                "obra_analysis": complexity_estimate.to_suggestion_dict(),
                "your_task": [
                    "Review Obra's complexity analysis and suggestions above",
                    "Decide if this task would benefit from decomposition",
                    "If yes, identify independent components that could be developed in parallel",
                    "If appropriate, use the Task tool to deploy multiple agents in parallel",
                    "If no, execute the task sequentially and explain your reasoning"
                ],
                "safety_rules": [
                    "NEVER run tests in parallel with code development (tests must run alone)",
                    "Ensure parallel tasks don't modify the same files (check for conflicts)",
                    "Consider dependencies before parallelizing (data flow, imports, etc.)",
                    "If uncertain, default to sequential execution (safer)"
                ],
                "response_requirements": {
                    "include_in_response": {
                        "parallel_execution_used": "boolean",
                        "parallel_decision_rationale": "string explaining why you did/didn't parallelize",
                        "tasks_parallelized": "array of task descriptions if you used parallel execution"
                    }
                }
            }
        }

        return f"\n\n## Parallelization Consideration\n{json.dumps(query, indent=2)}"

    def _format_hybrid_prompt(
        self,
        metadata: Dict[str, Any],
        instruction: str
    ) -> str:
        """Format hybrid prompt with metadata and instruction sections.

        Creates the standard hybrid prompt format:
        <METADATA>
        {...JSON...}
        </METADATA>

        <INSTRUCTION>
        ...text...
        </INSTRUCTION>

        Args:
            metadata: Metadata dictionary (will be JSON-serialized)
            instruction: Natural language instruction text

        Returns:
            Formatted hybrid prompt string

        Example:
            >>> metadata = {'prompt_type': 'task_execution', 'task_id': 1}
            >>> instruction = 'Implement feature X'
            >>> prompt = builder._format_hybrid_prompt(metadata, instruction)
        """
        # Serialize metadata to pretty JSON
        metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)

        # Build hybrid prompt
        prompt = f"""<METADATA>
{metadata_json}
</METADATA>

<INSTRUCTION>
{instruction.strip()}
</INSTRUCTION>"""

        return prompt

    def _inject_rules(
        self,
        metadata: Dict[str, Any],
        prompt_type: str,
        domains: List[str]
    ) -> Dict[str, Any]:
        """Inject rules from rule engine into metadata.

        Queries the rule engine for applicable rules based on prompt type
        and domains, then adds them to the metadata.

        Args:
            metadata: Metadata dictionary to inject rules into
            prompt_type: Type of prompt (for logging)
            domains: List of domain names to get rules from

        Returns:
            Updated metadata with 'rules' field added (or unchanged if no engine)

        Example:
            >>> metadata = {'prompt_type': 'task_execution'}
            >>> metadata = builder._inject_rules(
            ...     metadata,
            ...     'task_execution',
            ...     ['code_generation', 'testing']
            ... )
            >>> 'rules' in metadata
            True
        """
        if not self.rule_engine:
            # No rule engine, skip injection
            metadata['rules'] = []
            return metadata

        # Collect rules from all specified domains
        all_rules = []
        for domain in domains:
            domain_rules = self.rule_engine.get_rules_for_domain(domain)
            all_rules.extend(domain_rules)

        # Convert rules to serializable format
        metadata['rules'] = [
            {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'severity': rule.severity,
                'validation_type': rule.validation_type,
                'domain': rule.domain
            }
            for rule in all_rules
        ]

        # Update statistics
        self.stats['rules_injected_total'] += len(all_rules)

        logger.debug(
            f"Injected {len(all_rules)} rules from domains {domains} "
            f"for {prompt_type} prompt"
        )

        return metadata

    def get_stats(self) -> Dict[str, Any]:
        """Get builder statistics.

        Returns:
            Dictionary with statistics:
                - prompts_built: Total prompts built
                - task_execution_count: Task execution prompts
                - validation_count: Validation prompts
                - error_analysis_count: Error analysis prompts
                - decision_count: Decision prompts
                - planning_count: Planning prompts
                - rules_injected_total: Total rules injected across all prompts

        Example:
            >>> stats = builder.get_stats()
            >>> print(f"Prompts built: {stats['prompts_built']}")
            >>> print(f"Rules injected: {stats['rules_injected_total']}")
        """
        with self._lock:
            return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset all statistics to zero.

        Example:
            >>> builder.reset_stats()
            >>> stats = builder.get_stats()
            >>> assert stats['prompts_built'] == 0
        """
        with self._lock:
            for key in self.stats:
                self.stats[key] = 0
            logger.info("Statistics reset")

    def __repr__(self) -> str:
        """String representation of builder state.

        Returns:
            String showing builder configuration and stats

        Example:
            >>> repr(builder)
            '<StructuredPromptBuilder(rule_engine=enabled, prompts_built=42)>'
        """
        return (
            f"<StructuredPromptBuilder("
            f"rule_engine={'enabled' if self.rule_engine else 'disabled'}, "
            f"prompts_built={self.stats['prompts_built']})>"
        )
