"""PromptGenerator - Jinja2-based prompt generation with context management.

This module provides the PromptGenerator class for creating optimized prompts
from templates with intelligent context injection, token budget management,
and caching.

Key Features:
- Jinja2 template rendering with custom filters
- Context prioritization and injection
- Token budget awareness with automatic truncation
- Prompt optimization to reduce token count
- Few-shot example injection from pattern learning
- Template validation and caching
- Preview functionality for debugging
"""

import hashlib
import logging
import re
import yaml
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING

import jinja2
import jinja2.meta
from jinja2 import Environment, FileSystemLoader, Template, TemplateError
from jinja2.exceptions import TemplateNotFound, UndefinedError

from src.core.exceptions import StateManagerException
# Note: StructuredPromptBuilder is being created in parallel (TASK_3.2)
from src.llm.structured_prompt_builder import StructuredPromptBuilder

if TYPE_CHECKING:
    from src.orchestration.complexity_estimate import ComplexityEstimate

logger = logging.getLogger(__name__)


class PromptGeneratorException(Exception):
    """Base exception for PromptGenerator errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            context: Optional context dict
        """
        super().__init__(message)
        self.context = context or {}


class TemplateValidationError(PromptGeneratorException):
    """Exception raised when template validation fails."""
    pass


class PromptGenerator:
    """Jinja2-based prompt generator with context management and optimization.

    This class manages prompt generation from templates with:
    - Template loading and validation
    - Context injection with prioritization
    - Token budget management
    - Prompt optimization
    - Few-shot example injection
    - Caching for performance
    - **Structured mode support** (opt-in) for rule-based prompt generation
    - **Optional complexity estimates** (PHASE_5B) for parallelization suggestions

    The generator supports two modes:

    1. **Unstructured Mode** (default): Uses Jinja2 templates from YAML files
       - Natural language prompts with variable substitution
       - Full template customization via config/prompt_templates.yaml
       - Backward compatible with existing code

    2. **Structured Mode** (opt-in): Uses StructuredPromptBuilder for rule-based prompts
       - Declarative prompt rules with conditional logic
       - More maintainable and testable
       - Consistent structure across different prompt types
       - Enable via `structured_mode=True` in constructor
       - Optional complexity analysis for task parallelization suggestions

    Example (Unstructured Mode):
        >>> from src.llm.local_interface import LocalLLMInterface
        >>> from src.core.state import StateManager
        >>>
        >>> llm = LocalLLMInterface()
        >>> llm.initialize({'endpoint': 'http://localhost:11434'})
        >>> state_manager = StateManager.get_instance('sqlite:///test.db')
        >>>
        >>> generator = PromptGenerator(
        ...     template_dir='config',
        ...     llm_interface=llm,
        ...     state_manager=state_manager
        ... )
        >>>
        >>> prompt = generator.generate_prompt(
        ...     'task_execution',
        ...     {
        ...         'project_name': 'my-project',
        ...         'task_id': 1,
        ...         'task_title': 'Implement feature',
        ...         'task_description': 'Add new functionality',
        ...         'working_directory': '/tmp/project'
        ...     }
        ... )

    Example (Structured Mode):
        >>> from src.llm.structured_prompt_builder import StructuredPromptBuilder
        >>>
        >>> builder = StructuredPromptBuilder(rule_validator=rule_validator)
        >>> generator = PromptGenerator(
        ...     template_dir='config',
        ...     llm_interface=llm,
        ...     state_manager=state_manager,
        ...     structured_mode=True,
        ...     structured_builder=builder
        ... )
        >>>
        >>> # Same API, but uses structured rules internally
        >>> prompt = generator.generate_task_prompt(task, context)

    Example (Structured Mode with Complexity Analysis):
        >>> from src.orchestration.complexity_estimate import ComplexityEstimate
        >>>
        >>> # Generate complexity estimate
        >>> estimate = ComplexityEstimate(
        ...     task_id=1,
        ...     estimated_tokens=5000,
        ...     estimated_loc=250,
        ...     estimated_files=3,
        ...     complexity_score=65.0,
        ...     obra_suggests_decomposition=True,
        ...     obra_suggestion_confidence=0.8
        ... )
        >>>
        >>> # Pass to prompt generator
        >>> prompt = generator.generate_task_prompt(
        ...     task,
        ...     context,
        ...     complexity_estimate=estimate
        ... )

    Thread-safety:
        This class is thread-safe. The Jinja2 environment and LRU caches
        are safe for concurrent use.
    """

    # Default configuration
    DEFAULT_CONFIG = {
        'max_context_tokens': 100000,
        'summarization_threshold': 50000,
        'cache_size': 100,
        'optimization_target': 0.20,  # 20% reduction target
        'context_priority_order': [
            'current_task_description',
            'recent_errors',
            'active_code_files',
            'task_dependencies',
            'project_goals',
            'conversation_history'
        ]
    }

    def __init__(
        self,
        template_dir: str,
        llm_interface: Any,  # LocalLLMInterface, avoiding circular import
        state_manager: Optional[Any] = None,  # StateManager
        config: Optional[Dict[str, Any]] = None,
        structured_mode: bool = False,
        structured_builder: Optional[StructuredPromptBuilder] = None
    ):
        """Initialize PromptGenerator.

        Args:
            template_dir: Directory containing prompt_templates.yaml
            llm_interface: LocalLLMInterface instance for token counting and summarization
            state_manager: Optional StateManager instance for pattern learning
            config: Optional configuration overrides
            structured_mode: Enable structured prompt mode (default: False for backward compatibility)
            structured_builder: Optional StructuredPromptBuilder instance for structured mode.
                              If structured_mode=True and this is None, a default builder will be created.
        """
        self.template_dir = Path(template_dir)
        self.llm_interface = llm_interface
        self.state_manager = state_manager
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # Structured mode configuration
        self._structured_mode = structured_mode
        self._structured_builder = structured_builder

        # Load templates from YAML
        self.templates_yaml_path = self.template_dir / 'prompt_templates.yaml'
        self.templates: Dict[str, str] = {}
        self._load_templates_from_yaml()

        # Load hybrid prompt templates configuration (PHASE_6 TASK_6.1)
        self.hybrid_templates_yaml_path = self.template_dir / 'hybrid_prompt_templates.yaml'
        self.hybrid_config: Dict[str, Any] = {}
        self.template_modes: Dict[str, str] = {}
        self._load_hybrid_templates_config()

        # Create Jinja2 environment with custom filters
        self.env = Environment(
            loader=jinja2.DictLoader(self.templates),
            autoescape=False,  # Don't escape for text prompts
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Register custom filters
        self._register_custom_filters()

        # Cache for rendered prompts
        self._prompt_cache: Dict[str, str] = {}

        # Statistics
        self.stats = {
            'prompts_generated': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'optimizations_applied': 0,
            'total_tokens_saved': 0
        }

        mode_str = "structured" if self._structured_mode else "unstructured"
        logger.info(
            f"PromptGenerator initialized in {mode_str} mode with {len(self.templates)} templates "
            f"from {self.templates_yaml_path}"
        )

    def _load_templates_from_yaml(self) -> None:
        """Load templates from YAML file.

        Raises:
            PromptGeneratorException: If template file not found or invalid
        """
        if not self.templates_yaml_path.exists():
            raise PromptGeneratorException(
                f"Template file not found: {self.templates_yaml_path}",
                context={'path': str(self.templates_yaml_path)}
            )

        try:
            with open(self.templates_yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise PromptGeneratorException(
                    "Template file must contain a YAML dictionary",
                    context={'path': str(self.templates_yaml_path)}
                )

            self.templates = data
            logger.info(f"Loaded {len(self.templates)} templates from YAML")

        except yaml.YAMLError as e:
            raise PromptGeneratorException(
                f"Failed to parse template YAML: {e}",
                context={'path': str(self.templates_yaml_path)}
            ) from e
        except Exception as e:
            raise PromptGeneratorException(
                f"Failed to load templates: {e}",
                context={'path': str(self.templates_yaml_path)}
            ) from e

    def _load_hybrid_templates_config(self) -> None:
        """Load hybrid prompt templates configuration (PHASE_6 TASK_6.1).

        Loads configuration from hybrid_prompt_templates.yaml to determine
        which templates should use structured mode on a per-template basis.

        If file doesn't exist, uses default (all unstructured).
        """
        if not self.hybrid_templates_yaml_path.exists():
            logger.info(
                f"Hybrid templates config not found: {self.hybrid_templates_yaml_path}. "
                "Using default (unstructured) mode for all templates."
            )
            return

        try:
            with open(self.hybrid_templates_yaml_path, 'r', encoding='utf-8') as f:
                self.hybrid_config = yaml.safe_load(f)

            if not isinstance(self.hybrid_config, dict):
                logger.warning("Hybrid templates config is not a dictionary. Using defaults.")
                return

            # Extract template_modes from global.template_modes
            global_config = self.hybrid_config.get('global', {})
            self.template_modes = global_config.get('template_modes', {})

            logger.info(
                f"Loaded hybrid templates config with {len(self.template_modes)} template modes"
            )

            # Log which templates use structured mode
            structured_templates = [
                name for name, mode in self.template_modes.items()
                if mode == 'structured'
            ]
            if structured_templates:
                logger.info(
                    f"Templates using structured mode: {', '.join(structured_templates)}"
                )

        except yaml.YAMLError as e:
            logger.warning(
                f"Failed to parse hybrid templates YAML: {e}. Using defaults."
            )
        except Exception as e:
            logger.warning(
                f"Failed to load hybrid templates config: {e}. Using defaults."
            )

    def _register_custom_filters(self) -> None:
        """Register custom Jinja2 filters."""
        self.env.filters['truncate'] = self._filter_truncate
        self.env.filters['summarize'] = self._filter_summarize
        self.env.filters['format_code'] = self._filter_format_code

    def _is_structured_mode(self, template_name: Optional[str] = None) -> bool:
        """Check if structured mode is enabled for a given template.

        PHASE_6 TASK_6.1: Now supports per-template mode configuration from
        hybrid_prompt_templates.yaml.

        Args:
            template_name: Optional template name to check specific mode.
                          If provided, checks template_modes config.
                          If None, uses global structured_mode setting.

        Returns:
            True if structured mode is enabled for this template, False otherwise

        Example:
            >>> # Check global mode
            >>> generator._is_structured_mode()  # False (default)
            >>>
            >>> # Check specific template (PHASE_6)
            >>> generator._is_structured_mode('validation')  # True (migrated)
            >>> generator._is_structured_mode('task_execution')  # False (pending)
        """
        # If template name provided, check per-template configuration
        if template_name and self.template_modes:
            template_mode = self.template_modes.get(template_name, 'unstructured')
            return template_mode == 'structured'

        # Otherwise use global setting
        return self._structured_mode

    def _ensure_structured_builder(self) -> None:
        """Ensure StructuredPromptBuilder is available.

        Raises:
            PromptGeneratorException: If structured mode is enabled but builder is not available
        """
        if self._structured_mode and self._structured_builder is None:
            raise PromptGeneratorException(
                "Structured mode is enabled but no StructuredPromptBuilder was provided",
                context={'structured_mode': self._structured_mode}
            )

    def set_structured_mode(
        self,
        enabled: bool,
        builder: Optional[StructuredPromptBuilder] = None
    ) -> None:
        """Toggle structured mode at runtime.

        Args:
            enabled: Enable or disable structured mode
            builder: Optional StructuredPromptBuilder instance. If not provided and enabling,
                    the existing builder will be used (must have been set in constructor).

        Raises:
            PromptGeneratorException: If enabling structured mode without a builder

        Example:
            >>> generator.set_structured_mode(True, my_builder)
            >>> # Now uses structured mode
            >>> generator.set_structured_mode(False)
            >>> # Back to unstructured mode
        """
        self._structured_mode = enabled

        if builder is not None:
            self._structured_builder = builder

        if enabled:
            self._ensure_structured_builder()

        mode_str = "structured" if enabled else "unstructured"
        logger.info(f"PromptGenerator mode changed to {mode_str}")

    def _filter_truncate(self, text: str, max_tokens: int = 1000) -> str:
        """Truncate text to maximum token count.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens to keep

        Returns:
            Truncated text with ellipsis if needed
        """
        if not text:
            return ''

        current_tokens = self.llm_interface.estimate_tokens(text)

        if current_tokens <= max_tokens:
            return text

        # Binary search for the right length
        ratio = max_tokens / current_tokens
        estimated_chars = int(len(text) * ratio * 0.9)  # Conservative estimate

        truncated = text[:estimated_chars]
        while self.llm_interface.estimate_tokens(truncated) > max_tokens - 3:
            truncated = truncated[:int(len(truncated) * 0.9)]

        return truncated + '...'

    def _filter_summarize(self, text: str, max_tokens: int = 500) -> str:
        """Summarize text using local LLM.

        Args:
            text: Text to summarize
            max_tokens: Target token count for summary

        Returns:
            Summarized text
        """
        if not text:
            return ''

        current_tokens = self.llm_interface.estimate_tokens(text)

        # If already small enough, return as-is
        if current_tokens <= max_tokens:
            return text

        # Use LLM to generate summary
        try:
            summary_prompt = (
                f"Summarize the following text in {max_tokens} tokens or less, "
                f"preserving key information:\n\n{text}"
            )
            summary = self.llm_interface.generate(
                summary_prompt,
                max_tokens=max_tokens,
                temperature=0.3
            )
            return summary.strip()
        except Exception as e:
            logger.warning(f"Summarization failed, falling back to truncation: {e}")
            return self._filter_truncate(text, max_tokens)

    def _filter_format_code(self, code: str) -> str:
        """Format code for display.

        Args:
            code: Code to format

        Returns:
            Formatted code
        """
        if not code:
            return ''

        # Remove excessive blank lines
        code = re.sub(r'\n{3,}', '\n\n', code)

        # Ensure consistent indentation (convert tabs to spaces)
        code = code.replace('\t', '    ')

        return code.strip()

    def load_template(self, template_name: str) -> Template:
        """Load a template by name.

        Args:
            template_name: Name of the template

        Returns:
            Jinja2 Template object

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        try:
            return self.env.get_template(template_name)
        except TemplateNotFound as e:
            raise TemplateNotFound(
                f"Template '{template_name}' not found. "
                f"Available templates: {', '.join(self.templates.keys())}"
            ) from e

    def validate_template(self, template_name: str) -> bool:
        """Validate template syntax and structure.

        Args:
            template_name: Name of the template to validate

        Returns:
            True if template is valid

        Raises:
            TemplateValidationError: If validation fails
        """
        try:
            # Load template (will raise TemplateNotFound if missing)
            template = self.load_template(template_name)

            # Try to render with empty variables to check syntax
            # Use undefined=jinja2.StrictUndefined to catch missing variables
            strict_env = Environment(
                loader=jinja2.DictLoader(self.templates),
                undefined=jinja2.StrictUndefined
            )
            strict_template = strict_env.get_template(template_name)

            # Get all undefined variables
            ast = self.env.parse(self.templates[template_name])
            undefined_vars = jinja2.meta.find_undeclared_variables(ast)

            logger.debug(
                f"Template '{template_name}' validated successfully. "
                f"Required variables: {', '.join(sorted(undefined_vars))}"
            )

            return True

        except TemplateError as e:
            raise TemplateValidationError(
                f"Template '{template_name}' validation failed: {e}",
                context={'template': template_name, 'error': str(e)}
            ) from e

    def generate_prompt(
        self,
        template_name: str,
        variables: Dict[str, Any],
        max_tokens: Optional[int] = None,
        enable_optimization: bool = True,
        enable_caching: bool = True,
        **kwargs
    ) -> str:
        """Generate a prompt from template with variables.

        Args:
            template_name: Name of template to use
            variables: Variables to substitute in template
            max_tokens: Optional maximum token budget
            enable_optimization: Whether to optimize for token count
            enable_caching: Whether to use cached result if available
            **kwargs: Additional options (passed to template rendering)

        Returns:
            Generated prompt string

        Raises:
            TemplateNotFound: If template doesn't exist
            PromptGeneratorException: If rendering fails

        Example:
            >>> prompt = generator.generate_prompt(
            ...     'task_execution',
            ...     {'task_title': 'Fix bug', 'task_description': 'Fix issue #123'}
            ... )
        """
        self.stats['prompts_generated'] += 1

        # Create cache key
        cache_key = self._make_cache_key(template_name, variables, kwargs)

        # Check cache
        if enable_caching and cache_key in self._prompt_cache:
            self.stats['cache_hits'] += 1
            logger.debug(f"Cache hit for template '{template_name}'")
            return self._prompt_cache[cache_key]

        self.stats['cache_misses'] += 1

        try:
            # Load template
            template = self.load_template(template_name)

            # Merge variables with kwargs
            all_vars = {**variables, **kwargs}

            # Render template
            prompt = template.render(**all_vars)

            # Apply optimization if requested
            if enable_optimization and max_tokens:
                prompt = self.optimize_for_tokens(prompt, max_tokens)

            # Cache result
            if enable_caching:
                self._prompt_cache[cache_key] = prompt

            logger.debug(
                f"Generated prompt from template '{template_name}' "
                f"({self.llm_interface.estimate_tokens(prompt)} tokens)"
            )

            return prompt

        except UndefinedError as e:
            raise PromptGeneratorException(
                f"Missing required variable in template '{template_name}': {e}",
                context={'template': template_name, 'variables': list(variables.keys())}
            ) from e
        except TemplateError as e:
            raise PromptGeneratorException(
                f"Template rendering failed for '{template_name}': {e}",
                context={'template': template_name}
            ) from e

    def _make_cache_key(
        self,
        template_name: str,
        variables: Dict[str, Any],
        kwargs: Dict[str, Any]
    ) -> str:
        """Create cache key from template and variables.

        Args:
            template_name: Template name
            variables: Variables dict
            kwargs: Additional kwargs

        Returns:
            Hash string for caching
        """
        # Create deterministic string from inputs
        key_data = {
            'template': template_name,
            'variables': variables,
            'kwargs': kwargs
        }

        # Convert to JSON-like string and hash
        key_str = str(sorted(key_data.items()))
        return hashlib.sha256(key_str.encode()).hexdigest()

    def optimize_for_tokens(self, prompt: str, max_tokens: int) -> str:
        """Optimize prompt to fit within token budget.

        Applies various optimization strategies:
        - Remove redundant whitespace
        - Truncate verbose sections
        - Use concise language

        Args:
            prompt: Prompt to optimize
            max_tokens: Maximum token budget

        Returns:
            Optimized prompt (may still exceed if impossible to reduce further)
        """
        current_tokens = self.llm_interface.estimate_tokens(prompt)

        if current_tokens <= max_tokens:
            return prompt

        logger.info(
            f"Optimizing prompt from {current_tokens} to {max_tokens} tokens "
            f"({current_tokens - max_tokens} to remove)"
        )

        original_tokens = current_tokens
        optimized = prompt

        # Strategy 1: Remove redundant whitespace
        optimized = re.sub(r' +', ' ', optimized)  # Multiple spaces to single
        optimized = re.sub(r'\n{3,}', '\n\n', optimized)  # Multiple newlines to double
        optimized = optimized.strip()

        current_tokens = self.llm_interface.estimate_tokens(optimized)

        # Strategy 2: Remove example sections if still too long
        if current_tokens > max_tokens:
            # Look for ## Example or ### Example sections and remove them
            optimized = re.sub(
                r'## Example.*?(?=\n## |\n#|\Z)',
                '',
                optimized,
                flags=re.DOTALL
            )
            current_tokens = self.llm_interface.estimate_tokens(optimized)

        # Strategy 3: Truncate to fit
        if current_tokens > max_tokens:
            # Use the truncate filter
            optimized = self._filter_truncate(optimized, max_tokens)
            current_tokens = self.llm_interface.estimate_tokens(optimized)

        tokens_saved = original_tokens - current_tokens
        self.stats['optimizations_applied'] += 1
        self.stats['total_tokens_saved'] += tokens_saved

        logger.debug(
            f"Optimization saved {tokens_saved} tokens "
            f"({tokens_saved / original_tokens * 100:.1f}% reduction)"
        )

        return optimized

    def inject_context(
        self,
        prompt: str,
        context_data: Dict[str, Any],
        max_tokens: int
    ) -> str:
        """Inject context into prompt with prioritization.

        Adds context items in priority order until token budget is reached.

        Args:
            prompt: Base prompt
            context_data: Dictionary of context items to inject
            max_tokens: Maximum total tokens (prompt + context)

        Returns:
            Prompt with context injected

        Example:
            >>> context = {
            ...     'recent_errors': ['Error 1', 'Error 2'],
            ...     'active_code_files': [{'path': 'foo.py', 'size': 100}],
            ...     'conversation_history': 'Previous discussion...'
            ... }
            >>> prompt_with_context = generator.inject_context(
            ...     base_prompt,
            ...     context,
            ...     max_tokens=5000
            ... )
        """
        # Start with base prompt tokens
        current_tokens = self.llm_interface.estimate_tokens(prompt)
        available_tokens = max_tokens - current_tokens

        if available_tokens <= 0:
            logger.warning(
                f"No tokens available for context injection "
                f"(base prompt: {current_tokens}, max: {max_tokens})"
            )
            return prompt

        # Get priority order from config
        priority_order = self.config['context_priority_order']

        # Build context sections in priority order
        context_sections = []

        for context_key in priority_order:
            if context_key not in context_data:
                continue

            context_value = context_data[context_key]

            # Format context section
            section = self._format_context_section(context_key, context_value)
            section_tokens = self.llm_interface.estimate_tokens(section)

            # Check if we have room
            if current_tokens + section_tokens <= max_tokens:
                context_sections.append(section)
                current_tokens += section_tokens
            else:
                # Try to fit a truncated version
                remaining_tokens = max_tokens - current_tokens - 50  # Leave buffer
                if remaining_tokens > 100:  # Only if meaningful space left
                    truncated_section = self._filter_truncate(section, remaining_tokens)
                    context_sections.append(truncated_section)
                    current_tokens += self.llm_interface.estimate_tokens(truncated_section)

                # No more room for context
                break

        # Combine prompt with context
        if context_sections:
            full_prompt = prompt + '\n\n' + '\n\n'.join(context_sections)
        else:
            full_prompt = prompt

        logger.debug(
            f"Injected {len(context_sections)} context sections "
            f"({current_tokens} total tokens)"
        )

        return full_prompt

    def _format_context_section(self, key: str, value: Any) -> str:
        """Format a context item as a section.

        Args:
            key: Context key
            value: Context value

        Returns:
            Formatted section string
        """
        # Convert key to readable title
        title = key.replace('_', ' ').title()

        if isinstance(value, list):
            if not value:
                return ''

            # Format as bullet list
            items = '\n'.join(f"- {item}" for item in value)
            return f"## {title}\n{items}"

        elif isinstance(value, dict):
            if not value:
                return ''

            # Format as key-value pairs
            items = '\n'.join(f"- {k}: {v}" for k, v in value.items())
            return f"## {title}\n{items}"

        else:
            # Format as simple section
            return f"## {title}\n{value}"

    def add_examples(
        self,
        prompt: str,
        pattern_type: str,
        count: int = 3
    ) -> str:
        """Add few-shot examples from pattern learning.

        Queries StateManager for successful patterns and injects them as examples.

        Args:
            prompt: Base prompt
            pattern_type: Type of pattern to look up (e.g., 'bug_fix', 'feature_implementation')
            count: Number of examples to add

        Returns:
            Prompt with examples appended

        Example:
            >>> prompt_with_examples = generator.add_examples(
            ...     base_prompt,
            ...     pattern_type='error_handling',
            ...     count=3
            ... )
        """
        if not self.state_manager:
            logger.debug("No StateManager available for pattern learning")
            return prompt

        try:
            # Query pattern learning table
            from src.core.models import PatternLearning
            from sqlalchemy import desc

            session = self.state_manager._get_session()

            # Get top patterns by success rate
            patterns = session.query(PatternLearning).filter(
                PatternLearning.pattern_type == pattern_type,
                PatternLearning.success_count > 0
            ).order_by(
                desc(PatternLearning.success_count)
            ).limit(count).all()

            if not patterns:
                logger.debug(f"No patterns found for type '{pattern_type}'")
                return prompt

            # Format examples
            examples_section = "\n\n## Example Solutions\n"
            examples_section += "Based on successful previous solutions:\n\n"

            for i, pattern in enumerate(patterns, 1):
                pattern_data = pattern.pattern_data
                examples_section += f"### Example {i}\n"

                if 'description' in pattern_data:
                    examples_section += f"{pattern_data['description']}\n"

                if 'solution' in pattern_data:
                    examples_section += f"```\n{pattern_data['solution']}\n```\n"

                examples_section += f"(Success rate: {pattern.success_count} / {pattern.success_count + pattern.failure_count})\n\n"

            logger.debug(f"Added {len(patterns)} examples for pattern type '{pattern_type}'")

            return prompt + examples_section

        except Exception as e:
            logger.warning(f"Failed to add examples from pattern learning: {e}")
            return prompt

    def get_prompt_stats(self, prompt: str) -> Dict[str, Any]:
        """Get statistics about a prompt.

        Args:
            prompt: Prompt to analyze

        Returns:
            Dictionary with statistics:
                - token_count: Estimated token count
                - character_count: Character count
                - line_count: Number of lines
                - word_count: Number of words
                - sections: List of section headers found
        """
        stats = {
            'token_count': self.llm_interface.estimate_tokens(prompt),
            'character_count': len(prompt),
            'line_count': len(prompt.split('\n')),
            'word_count': len(prompt.split()),
            'sections': []
        }

        # Extract section headers (lines starting with ##)
        for line in prompt.split('\n'):
            if line.strip().startswith('##'):
                stats['sections'].append(line.strip())

        return stats

    def preview_prompt(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> str:
        """Preview prompt without caching or optimization.

        Useful for debugging templates.

        Args:
            template_name: Name of template
            variables: Variables to substitute

        Returns:
            Rendered prompt
        """
        return self.generate_prompt(
            template_name,
            variables,
            enable_optimization=False,
            enable_caching=False
        )

    def clear_cache(self) -> None:
        """Clear the prompt cache.

        Example:
            >>> generator.clear_cache()
        """
        self._prompt_cache.clear()
        logger.info("Prompt cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics.

        Returns:
            Dictionary with statistics:
                - prompts_generated: Total prompts generated
                - cache_hits: Number of cache hits
                - cache_misses: Number of cache misses
                - cache_hit_rate: Cache hit rate (0.0-1.0)
                - optimizations_applied: Number of optimizations
                - total_tokens_saved: Total tokens saved by optimization
                - avg_tokens_saved: Average tokens saved per optimization
        """
        stats = self.stats.copy()

        # Calculate derived metrics
        total_requests = stats['cache_hits'] + stats['cache_misses']
        if total_requests > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / total_requests
        else:
            stats['cache_hit_rate'] = 0.0

        if stats['optimizations_applied'] > 0:
            stats['avg_tokens_saved'] = (
                stats['total_tokens_saved'] / stats['optimizations_applied']
            )
        else:
            stats['avg_tokens_saved'] = 0.0

        return stats

    def generate_task_prompt(
        self,
        task: Any,  # Task model, avoiding circular import
        context: Dict[str, Any],
        complexity_estimate: Optional['ComplexityEstimate'] = None
    ) -> str:
        """Generate task execution prompt.

        Supports both structured and unstructured modes based on configuration.
        PHASE_6 TASK_6.4: Automatically uses structured mode if configured in
        hybrid_prompt_templates.yaml.

        Optionally accepts complexity analysis from Obra for parallelization suggestions.

        Args:
            task: Task model instance with task details
            context: Additional context for prompt generation
            complexity_estimate: Optional complexity analysis from Obra (PHASE_5B)

        Returns:
            Generated prompt string

        Example (Unstructured):
            >>> prompt = generator.generate_task_prompt(
            ...     task,
            ...     {'working_directory': '/tmp/project'}
            ... )

        Example (Structured - PHASE_6):
            >>> # Automatically uses structured mode if task_execution: structured in config
            >>> prompt = generator.generate_task_prompt(task, context)

        Example (Structured with Complexity):
            >>> from src.orchestration.complexity_estimate import ComplexityEstimate
            >>> estimate = ComplexityEstimate(...)
            >>> prompt = generator.generate_task_prompt(
            ...     task,
            ...     context,
            ...     complexity_estimate=estimate
            ... )
        """
        if self._is_structured_mode(template_name='task_execution'):
            # Use StructuredPromptBuilder (PHASE_6 migration)
            self._ensure_structured_builder()
            return self._structured_builder.build_task_execution_prompt(
                task_data=self._task_to_dict(task),
                context=context,
                complexity_estimate=complexity_estimate
            )
        else:
            # Use existing unstructured generation logic
            variables = {
                'project_name': getattr(task, 'project_name', 'Unknown'),
                'task_id': getattr(task, 'id', 0),
                'task_title': getattr(task, 'title', ''),
                'task_description': getattr(task, 'description', ''),
                'task_priority': getattr(task, 'priority', 5),
                'working_directory': context.get('working_directory', '.'),
                **context
            }
            return self.generate_prompt('task_execution', variables)

    def generate_validation_prompt(
        self,
        task: Any,  # Task model
        work_output: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate validation prompt.

        Supports both structured and unstructured modes based on configuration.
        PHASE_6 TASK_6.1: Automatically uses structured mode for validation if
        configured in hybrid_prompt_templates.yaml.

        Args:
            task: Task model instance
            work_output: The work output to validate
            context: Additional context including validation criteria

        Returns:
            Generated validation prompt string

        Example (Unstructured):
            >>> prompt = generator.generate_validation_prompt(
            ...     task,
            ...     "Implementation complete",
            ...     {'validation_criteria': ['Correctness', 'Completeness']}
            ... )

        Example (Structured - PHASE_6):
            >>> # Automatically uses structured mode if validation: structured in config
            >>> prompt = generator.generate_validation_prompt(task, output, context)
        """
        if self._is_structured_mode(template_name='validation'):
            # Use StructuredPromptBuilder (PHASE_6 migration)
            self._ensure_structured_builder()
            # Extract code from work_output
            code = work_output if isinstance(work_output, str) else work_output.get('code', str(work_output))
            # Get rules from context or use empty list
            rules = context.get('rules', [])
            return self._structured_builder.build_validation_prompt(
                code=code,
                rules=rules
            )
        else:
            # Use existing unstructured generation logic
            variables = {
                'task_title': getattr(task, 'title', ''),
                'task_description': getattr(task, 'description', ''),
                'expected_outcome': context.get('expected_outcome', 'Task completion'),
                'work_output': work_output,
                'validation_criteria': context.get('validation_criteria', [
                    'Correctness',
                    'Completeness',
                    'Code quality'
                ]),
                **context
            }
            return self.generate_prompt('validation', variables)

    def generate_error_analysis_prompt(
        self,
        task: Any,  # Task model
        error_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate error analysis prompt.

        Supports both structured and unstructured modes based on configuration.

        Args:
            task: Task model instance
            error_data: Error details (type, message, stacktrace, etc.)
            context: Additional context

        Returns:
            Generated error analysis prompt string

        Example (Unstructured):
            >>> prompt = generator.generate_error_analysis_prompt(
            ...     task,
            ...     {
            ...         'error_type': 'ValueError',
            ...         'error_message': 'Invalid input',
            ...         'error_stacktrace': '...'
            ...     },
            ...     {'agent_output': 'Previous output...'}
            ... )

        Example (Structured):
            >>> generator.set_structured_mode(True, builder)
            >>> prompt = generator.generate_error_analysis_prompt(task, error_data, context)
        """
        if self._is_structured_mode():
            # Use StructuredPromptBuilder
            self._ensure_structured_builder()
            return self._structured_builder.build_error_analysis_prompt(
                error_data=error_data
            )
        else:
            # Use existing unstructured generation logic
            variables = {
                'task_title': getattr(task, 'title', ''),
                'task_description': getattr(task, 'description', ''),
                'error_type': error_data.get('error_type', 'Unknown'),
                'error_message': error_data.get('error_message', ''),
                'error_stacktrace': error_data.get('error_stacktrace', ''),
                'agent_output': context.get('agent_output', ''),
                **context
            }
            return self.generate_prompt('error_analysis', variables)

    def generate_decision_prompt(
        self,
        task: Any,  # Task model
        agent_response: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate decision prompt.

        Supports both structured and unstructured modes based on configuration.

        Args:
            task: Task model instance
            agent_response: The latest agent response
            context: Additional context including validation results

        Returns:
            Generated decision prompt string

        Example (Unstructured):
            >>> prompt = generator.generate_decision_prompt(
            ...     task,
            ...     "Task completed",
            ...     {
            ...         'validation_result': {'is_valid': True, 'quality_score': 0.9},
            ...         'attempt_count': 1
            ...     }
            ... )

        Example (Structured):
            >>> generator.set_structured_mode(True, builder)
            >>> prompt = generator.generate_decision_prompt(task, response, context)
        """
        if self._is_structured_mode():
            # Use StructuredPromptBuilder
            self._ensure_structured_builder()
            # Merge task data, agent response, and context into decision_context
            decision_context = {
                **self._task_to_dict(task),
                'agent_response': agent_response,
                **context
            }
            return self._structured_builder.build_decision_prompt(
                decision_context=decision_context
            )
        else:
            # Use existing unstructured generation logic
            variables = {
                'task_id': getattr(task, 'id', 0),
                'task_title': getattr(task, 'title', ''),
                'task_status': getattr(task, 'status', 'unknown'),
                'agent_name': context.get('agent_name', 'Claude Code'),
                'agent_response': agent_response,
                'attempt_count': context.get('attempt_count', 1),
                'max_attempts': context.get('max_attempts', 3),
                'active_task_count': context.get('active_task_count', 0),
                'pending_task_count': context.get('pending_task_count', 0),
                'recent_breakpoint_count': context.get('recent_breakpoint_count', 0),
                **context
            }
            return self.generate_prompt('decision', variables)

    def _task_to_dict(self, task: Any) -> Dict[str, Any]:
        """Convert task model to dictionary for structured builder.

        Args:
            task: Task model instance

        Returns:
            Dictionary representation of task
        """
        # Basic task attributes
        task_dict = {
            'task_id': getattr(task, 'id', 0),  # StructuredPromptBuilder expects 'task_id'
            'title': getattr(task, 'title', ''),
            'description': getattr(task, 'description', ''),
            'status': getattr(task, 'status', 'unknown'),
            'priority': getattr(task, 'priority', 5),
        }

        # Optional attributes
        for attr in ['project_name', 'dependencies', 'expected_outcome',
                     'working_directory', 'created_at', 'updated_at']:
            if hasattr(task, attr):
                task_dict[attr] = getattr(task, attr)

        return task_dict

    def list_templates(self) -> List[str]:
        """List available template names.

        Returns:
            List of template names
        """
        return list(self.templates.keys())
