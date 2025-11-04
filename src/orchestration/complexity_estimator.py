"""Task complexity estimation using heuristics and optional LLM analysis.

This module provides the TaskComplexityEstimator class that analyzes task
descriptions to estimate complexity metrics including:
- Lines of code (LOC) to write
- Number of files to modify/create
- Token count for prompts/responses
- Overall complexity score (0-100)
- Decomposition suggestions with subtask recommendations

PHASE_5B UPDATE: Estimates are SUGGESTIONS for Claude Code to consider,
not authoritative commands. Claude makes final decisions on decomposition
and parallelization based on its understanding of the codebase.

The estimator combines multiple analysis methods:
1. Heuristic analysis using keyword patterns and verb counting
2. Optional LLM-based analysis for detailed assessment
3. Historical data from previous tasks (if available)

Example Usage:
    >>> from src.orchestration.complexity_estimator import TaskComplexityEstimator
    >>> from src.core.state import StateManager
    >>> from src.llm.local_interface import LocalLLMInterface
    >>>
    >>> # Initialize with LLM and state manager
    >>> llm = LocalLLMInterface()
    >>> state_manager = StateManager.get_instance()
    >>> estimator = TaskComplexityEstimator(
    ...     llm_interface=llm,
    ...     state_manager=state_manager
    ... )
    >>>
    >>> # Estimate task complexity
    >>> task = state_manager.get_task(123)
    >>> estimate = estimator.estimate_complexity(task, context={'files': [...]})
    >>>
    >>> # Check results
    >>> if estimate.obra_suggests_decomposition:
    ...     print(f"Obra suggests decomposing into {len(estimate.suggested_subtasks)} subtasks")
    ...     print(f"Confidence: {estimate.obra_suggestion_confidence:.2f}")
    ...     print(f"Rationale: {estimate.suggestion_rationale}")
    ...     for suggestion in estimate.suggested_subtasks:
    ...         print(f"  - {suggestion}")
    >>>
    >>> # Access metrics
    >>> print(f"Complexity: {estimate.complexity_score}/100")
    >>> print(f"Category: {estimate.get_complexity_category()}")
    >>> print(f"Estimated LOC: {estimate.estimated_loc}")
"""

import json
import logging
import re
import threading
import yaml
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.orchestration.complexity_estimate import ComplexityEstimate
from src.orchestration.subtask import SubTask
from src.core.exceptions import ConfigValidationException

logger = logging.getLogger(__name__)


class TaskComplexityEstimator:
    """Estimates task complexity using heuristics and optional LLM analysis.

    This class analyzes task descriptions to estimate complexity metrics,
    determine if decomposition is needed, and suggest subtasks if appropriate.
    Combines heuristic keyword analysis with optional LLM-based assessment
    for comprehensive complexity evaluation.

    Thread-safety:
        This class is thread-safe. The RLock protects internal state access.

    Attributes:
        llm_interface: Optional LLM interface for detailed analysis
        state_manager: Optional StateManager for logging and historical data
        config_path: Path to complexity thresholds YAML configuration
        thresholds: Loaded configuration thresholds and heuristics
    """

    def __init__(
        self,
        llm_interface: Optional[Any] = None,
        state_manager: Optional[Any] = None,
        config_path: str = 'config/complexity_thresholds.yaml'
    ):
        """Initialize the TaskComplexityEstimator.

        Args:
            llm_interface: Optional LLM interface for detailed analysis.
                          Should implement generate(prompt) -> str method.
            state_manager: Optional StateManager for logging estimates.
                          Should implement log_complexity_estimate(data) method.
            config_path: Path to YAML configuration file with thresholds.

        Raises:
            ConfigValidationException: If config file is invalid or missing required fields.
        """
        self.llm_interface = llm_interface
        self.state_manager = state_manager
        self.config_path = config_path
        self.thresholds: Dict[str, Any] = {}
        self._lock = threading.RLock()

        # Load configuration
        self._load_thresholds()

        logger.info(
            "TaskComplexityEstimator initialized (LLM: %s, StateManager: %s)",
            "enabled" if llm_interface else "disabled",
            "enabled" if state_manager else "disabled"
        )

    def _load_thresholds(self) -> None:
        """Load complexity thresholds from YAML configuration file.

        Expected YAML structure:
            complexity_heuristics:
              loc_estimation:
                simple_function: 20
                medium_function: 35
                ...
              file_count_weights:
                1_file: 1.0
                ...
              conceptual_complexity:
                algorithm_implementation: 1.8
                ...
            decomposition_thresholds:
              max_tokens: 8000
              max_files: 5
              ...
            task_type_multipliers:
              feature_implementation: 1.5
              ...

        Raises:
            ConfigValidationException: If file not found or invalid format.
        """
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.warning(
                    "Configuration file not found: %s, using default thresholds",
                    self.config_path
                )
                self.thresholds = self._get_default_thresholds()
                return

            with open(config_file, 'r', encoding='utf-8') as f:
                self.thresholds = yaml.safe_load(f)

            # Validate required sections
            required_sections = [
                'complexity_heuristics',
                'decomposition_thresholds',
                'task_type_multipliers'
            ]
            for section in required_sections:
                if section not in self.thresholds:
                    raise ConfigValidationException(
                        f"Missing required section '{section}' in {self.config_path}",
                        context={'file': self.config_path, 'section': section}
                    )

            logger.info("Loaded complexity thresholds from %s", self.config_path)

        except yaml.YAMLError as e:
            raise ConfigValidationException(
                f"Invalid YAML format in {self.config_path}",
                context={'file': self.config_path, 'error': str(e)}
            ) from e
        except Exception as e:
            logger.error("Failed to load thresholds: %s", e)
            raise ConfigValidationException(
                f"Error loading configuration from {self.config_path}",
                context={'file': self.config_path, 'error': str(e)}
            ) from e

    def _get_default_thresholds(self) -> Dict[str, Any]:
        """Get default thresholds when configuration file is unavailable.

        Returns:
            Dictionary with sensible default thresholds and heuristics.
        """
        return {
            'complexity_heuristics': {
                'loc_estimation': {
                    'simple_function': 20,
                    'medium_function': 35,
                    'complex_function': 50,
                    'simple_class': 80,
                    'medium_class': 150,
                    'complex_class': 250,
                    'small_module': 200,
                    'medium_module': 400,
                    'large_module': 600,
                    'api_endpoint': 100,
                },
                'file_count_weights': {
                    '1_file': 1.0,
                    '2_3_files': 1.3,
                    '4_6_files': 1.6,
                    '7_10_files': 2.0,
                    '11_plus_files': 2.5,
                },
                'conceptual_complexity': {
                    'algorithm_implementation': 1.8,
                    'concurrency_handling': 2.0,
                    'security_critical': 1.7,
                    'performance_optimization': 1.6,
                    'external_api_integration': 1.3,
                }
            },
            'decomposition_thresholds': {
                'max_tokens': 8000,
                'max_files': 5,
                'max_dependencies': 3,
                'max_duration_hours': 4,
                'max_loc_estimate': 400,
                'max_complexity_score': 100,
                'suggestion_threshold': 60,  # PHASE_5B: Obra suggests decomposition
                'decompose_threshold': 70,   # Deprecated, fallback
                'high_complexity_threshold': 60,
                'medium_complexity_threshold': 30,
            },
            'task_type_multipliers': {
                'feature_implementation': 1.5,
                'bug_fix': 0.8,
                'refactoring': 1.2,
                'testing': 0.6,
                'documentation': 0.4,
                'performance_optimization': 1.7,
                'security_enhancement': 1.8,
            }
        }

    def estimate_complexity(
        self,
        task: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> ComplexityEstimate:
        """Estimate task complexity using multi-method analysis.

        Combines heuristic analysis with optional LLM analysis to produce
        a comprehensive complexity estimate. If state_manager is available,
        may also incorporate historical data from similar tasks.

        Args:
            task: Task model from src.core.models (must have id, description attributes)
            context: Optional context with additional information:
                    - files: List of file paths to modify
                    - dependencies: List of dependency task IDs
                    - task_type: Type of task (feature, bug_fix, etc.)

        Returns:
            ComplexityEstimate with all fields populated including:
            - estimated_tokens, estimated_loc, estimated_files
            - complexity_score (0-100)
            - obra_suggests_decomposition flag (suggestion, not command)
            - suggested_subtasks if applicable
            - obra_suggestion_confidence score
            - suggestion_rationale explaining Obra's recommendation

        Raises:
            ValueError: If task is invalid or missing required attributes

        Example:
            >>> task = state_manager.get_task(123)
            >>> estimate = estimator.estimate_complexity(
            ...     task,
            ...     context={'files': ['src/foo.py', 'src/bar.py']}
            ... )
            >>> print(f"Complexity: {estimate.complexity_score}")
        """
        if not hasattr(task, 'id') or not hasattr(task, 'description'):
            raise ValueError("Task must have 'id' and 'description' attributes")

        with self._lock:
            context = context or {}
            description = task.description

            logger.info("Estimating complexity for task %s", task.id)

            # Step 1: Heuristic analysis (always performed)
            heuristic_result = self._heuristic_analysis(description, context)
            logger.debug("Heuristic analysis result: %s", heuristic_result)

            # Step 2: Optional LLM analysis
            llm_result = None
            if self.llm_interface:
                try:
                    llm_result = self._llm_analysis(description, context)
                    logger.debug("LLM analysis result: %s", llm_result)
                except Exception as e:
                    logger.warning("LLM analysis failed: %s, using heuristics only", e)

            # Step 3: Combine estimates
            estimate = self._combine_estimates(heuristic_result, llm_result)

            # Step 4: Generate decomposition suggestions if needed
            if estimate.obra_suggests_decomposition:
                suggestions = self._suggest_decomposition(task, estimate, context)

                # Step 4a: Create SubTask instances from suggestions
                subtasks = self._create_subtasks_from_suggestions(
                    task_id=task.id,
                    suggestions=suggestions,
                    estimate=estimate
                )

                # Step 4b: Analyze parallelization opportunities
                parallel_opportunities = []
                if subtasks:
                    try:
                        parallel_opportunities = self.analyze_parallelization_opportunities(
                            subtasks=subtasks,
                            context=context
                        )
                        logger.info(
                            "Identified %d parallel groups for task %s",
                            len(parallel_opportunities), task.id
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to analyze parallelization for task %s: %s",
                            task.id, e
                        )

                # Create updated estimate with suggestions and parallelization
                estimate = ComplexityEstimate(
                    task_id=estimate.task_id,
                    estimated_tokens=estimate.estimated_tokens,
                    estimated_loc=estimate.estimated_loc,
                    estimated_files=estimate.estimated_files,
                    complexity_score=estimate.complexity_score,
                    obra_suggests_decomposition=estimate.obra_suggests_decomposition,
                    obra_suggestion_confidence=estimate.obra_suggestion_confidence,
                    suggested_subtasks=suggestions,
                    suggested_parallel_groups=parallel_opportunities,
                    estimated_duration_minutes=estimate.estimated_duration_minutes,
                    suggestion_rationale=estimate.suggestion_rationale,
                    timestamp=estimate.timestamp
                )

            # Step 5: Log estimate if state_manager available
            if self.state_manager:
                try:
                    self._log_estimate(estimate)
                except Exception as e:
                    logger.warning("Failed to log estimate: %s", e)

            logger.info(
                "Complexity estimate complete for task %s: score=%.1f, suggests_decompose=%s (confidence=%.2f)",
                task.id, estimate.complexity_score, estimate.obra_suggests_decomposition,
                estimate.obra_suggestion_confidence
            )

            return estimate

    def _heuristic_analysis(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze task description using keyword patterns and heuristics.

        Uses pattern matching to estimate complexity based on:
        - Keywords indicating scope (implement, create, fix, update)
        - File mentions and counts
        - Action verb counting
        - Dependency indicators
        - List/enumeration detection
        - Task type classification

        Args:
            description: Task description text
            context: Optional context with files, dependencies, task_type

        Returns:
            Dictionary with:
            - estimated_tokens: int
            - estimated_loc: int
            - estimated_files: int
            - complexity_score: float (0-100)
            - indicators: List[str] (what drove the score)
            - confidence: float (0-1)
        """
        context = context or {}
        indicators = []
        base_loc = 50  # Base estimate
        base_tokens = 1000
        complexity_score = 20.0  # Base complexity

        # Convert to lowercase for pattern matching
        desc_lower = description.lower()

        # Keyword patterns for LOC estimation
        high_loc_keywords = ['implement', 'create', 'build', 'develop', 'design']
        medium_loc_keywords = ['fix', 'update', 'refactor', 'modify', 'enhance']
        low_loc_keywords = ['test', 'document', 'comment', 'format']

        # Count keyword matches
        high_count = sum(1 for kw in high_loc_keywords if kw in desc_lower)
        medium_count = sum(1 for kw in medium_loc_keywords if kw in desc_lower)
        low_count = sum(1 for kw in low_loc_keywords if kw in desc_lower)

        # Adjust LOC based on keywords
        if high_count > 0:
            base_loc += high_count * 100
            complexity_score += high_count * 15
            indicators.append(f"High-complexity keywords: {high_count}")

        if medium_count > 0:
            base_loc += medium_count * 50
            complexity_score += medium_count * 8
            indicators.append(f"Medium-complexity keywords: {medium_count}")

        if low_count > 0:
            base_loc += low_count * 20
            complexity_score += low_count * 3
            indicators.append(f"Low-complexity keywords: {low_count}")

        # File count analysis
        files = context.get('files', [])
        file_count = len(files)

        if file_count > 0:
            # Use file count weights from config
            weights = self.thresholds['complexity_heuristics']['file_count_weights']
            if file_count == 1:
                multiplier = weights.get('1_file', 1.0)
            elif 2 <= file_count <= 3:
                multiplier = weights.get('2_3_files', 1.3)
            elif 4 <= file_count <= 6:
                multiplier = weights.get('4_6_files', 1.6)
            elif 7 <= file_count <= 10:
                multiplier = weights.get('7_10_files', 2.0)
            else:
                multiplier = weights.get('11_plus_files', 2.5)

            base_loc = int(base_loc * multiplier)
            complexity_score *= multiplier
            indicators.append(f"File count: {file_count} (multiplier: {multiplier})")
        else:
            # Estimate file count from description
            file_mentions = len(re.findall(r'\b\w+\.(py|js|java|go|rs|cpp|c|h)\b', desc_lower))
            file_count = max(1, file_mentions)

        # Detect complexity indicators in description
        complexity_patterns = {
            'algorithm': ('algorithm', 'sort', 'search', 'optimize', 'graph'),
            'concurrency': ('thread', 'async', 'parallel', 'concurrent', 'lock'),
            'security': ('auth', 'security', 'encrypt', 'validate', 'sanitize'),
            'integration': ('integrate', 'api', 'external', 'third-party'),
            'database': ('database', 'schema', 'migration', 'query', 'sql'),
        }

        for pattern_name, keywords in complexity_patterns.items():
            if any(kw in desc_lower for kw in keywords):
                multipliers = self.thresholds['complexity_heuristics']['conceptual_complexity']
                multiplier_key = f"{pattern_name}_implementation"
                if multiplier_key in multipliers:
                    multiplier = multipliers[multiplier_key]
                    complexity_score *= multiplier
                    indicators.append(f"{pattern_name.capitalize()} complexity detected")

        # Verb counting (more verbs = more actions = higher complexity)
        action_verbs = [
            'add', 'remove', 'modify', 'update', 'create', 'delete',
            'implement', 'refactor', 'optimize', 'validate', 'test',
            'document', 'fix', 'enhance', 'integrate', 'configure'
        ]
        verb_count = sum(1 for verb in action_verbs if verb in desc_lower)
        if verb_count > 3:
            complexity_score += (verb_count - 3) * 5
            indicators.append(f"High verb count: {verb_count}")

        # List/enumeration detection
        list_patterns = [
            r'\d+\.',  # Numbered lists (1. 2. 3.)
            r'-\s+\w',  # Bullet points (- item)
            r'\*\s+\w',  # Asterisk bullets (* item)
        ]
        list_items = sum(len(re.findall(pattern, description)) for pattern in list_patterns)
        if list_items > 2:
            base_loc += list_items * 30
            complexity_score += list_items * 5
            indicators.append(f"Multiple sub-items: {list_items}")

        # Dependency analysis
        dependencies = context.get('dependencies', [])
        dep_count = len(dependencies)
        if dep_count > 0:
            depth_scoring = self.thresholds['complexity_heuristics']['dependency_depth_scoring']
            if dep_count <= 1:
                dep_score = depth_scoring.get('depth_1', 5)
            elif dep_count == 2:
                dep_score = depth_scoring.get('depth_2', 12)
            elif dep_count == 3:
                dep_score = depth_scoring.get('depth_3', 20)
            else:
                dep_score = depth_scoring.get('depth_5_plus', 40)

            complexity_score += dep_score
            indicators.append(f"Dependencies: {dep_count}")

        # Task type multiplier
        task_type = context.get('task_type', 'feature_implementation')
        type_multipliers = self.thresholds['task_type_multipliers']
        if task_type in type_multipliers:
            type_mult = type_multipliers[task_type]
            complexity_score *= type_mult
            indicators.append(f"Task type: {task_type} (x{type_mult})")

        # Cap complexity score at 100
        complexity_score = min(100.0, complexity_score)

        # Estimate tokens (prompt + expected response)
        # Rough estimate: 1 token ≈ 4 characters
        desc_tokens = len(description) // 4
        estimated_tokens = desc_tokens + (base_loc * 2)  # 2 tokens per LOC on average

        # Estimate duration based on LOC (rough: 5 LOC per minute)
        estimated_duration_minutes = max(15, base_loc // 5)

        # Confidence based on available information
        confidence = 0.6  # Base confidence for heuristics
        if files:
            confidence += 0.1  # More confident with explicit file list
        if task_type != 'feature_implementation':
            confidence += 0.1  # More confident with explicit task type

        return {
            'estimated_tokens': estimated_tokens,
            'estimated_loc': base_loc,
            'estimated_files': file_count,
            'complexity_score': complexity_score,
            'indicators': indicators,
            'confidence': min(1.0, confidence),
            'estimated_duration_minutes': estimated_duration_minutes,
        }

    def _llm_analysis(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Use LLM for detailed complexity analysis.

        Sends a structured prompt to the LLM requesting detailed complexity
        assessment including LOC estimate, file count, token estimate, and
        decomposition recommendations.

        Args:
            description: Task description text
            context: Optional context dictionary

        Returns:
            Dictionary with same structure as _heuristic_analysis, but with
            LLM-generated estimates

        Raises:
            Exception: If LLM call fails or response is invalid
        """
        context = context or {}

        # Build prompt for LLM
        prompt = self._build_llm_analysis_prompt(description, context)

        # Call LLM
        logger.debug("Sending complexity analysis prompt to LLM")
        response = self.llm_interface.generate(prompt)

        # Parse LLM response (expecting JSON)
        try:
            result = self._parse_llm_response(response)
            logger.debug("LLM analysis parsed successfully")
            return result
        except Exception as e:
            logger.error("Failed to parse LLM response: %s", e)
            raise

    def _build_llm_analysis_prompt(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> str:
        """Build structured prompt for LLM complexity analysis.

        Args:
            description: Task description
            context: Context dictionary

        Returns:
            Formatted prompt string
        """
        context_str = ""
        if context.get('files'):
            context_str += f"\nFiles to modify: {', '.join(context['files'])}"
        if context.get('dependencies'):
            context_str += f"\nDependent tasks: {len(context['dependencies'])}"
        if context.get('task_type'):
            context_str += f"\nTask type: {context['task_type']}"

        prompt = f"""Analyze this software development task and estimate its complexity.

Task Description:
{description}
{context_str}

Provide estimates for:
1. Lines of code (LOC) to write or modify
2. Number of files to modify or create
3. Estimated tokens for prompt + response (conservative estimate)
4. Overall complexity score (0-100 scale, where 0=trivial, 100=extremely complex)
5. Do you suggest this task be decomposed into subtasks? (yes/no)
6. If yes, suggest 3-7 subtasks with clear boundaries

NOTE: This is a SUGGESTION for Claude Code to consider, not a command.
Claude makes final decisions based on codebase understanding.

Consider these factors:
- Scope and breadth of changes required
- Technical complexity (algorithms, concurrency, security, etc.)
- Integration points and dependencies
- Testing and validation requirements
- Documentation needs

Respond in JSON format:
{{
  "estimated_loc": <number>,
  "estimated_files": <number>,
  "estimated_tokens": <number>,
  "complexity_score": <number 0-100>,
  "suggest_decompose": <true|false>,
  "decomposition_reason": "<brief explanation if true>",
  "subtask_suggestions": [
    "<subtask 1 description>",
    "<subtask 2 description>",
    ...
  ],
  "suggestion_confidence": <number 0-1>
}}

Provide only the JSON response, no additional text."""

        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response.

        Args:
            response: LLM response text

        Returns:
            Parsed dictionary with complexity estimates

        Raises:
            ValueError: If response is not valid JSON or missing required fields
        """
        # Try to extract JSON from response (may have markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in LLM response")

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}") from e

        # Validate required fields (support both old and new field names)
        required_fields = [
            'estimated_loc', 'estimated_files', 'estimated_tokens',
            'complexity_score'
        ]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in LLM response")

        # Check for suggest_decompose (new) or should_decompose (old)
        if 'suggest_decompose' not in data and 'should_decompose' not in data:
            raise ValueError("Missing required field 'suggest_decompose' in LLM response")

        # Calculate duration from LOC
        estimated_loc = data['estimated_loc']
        estimated_duration_minutes = max(15, estimated_loc // 5)

        # Support both old and new field names
        suggest_decompose = data.get('suggest_decompose', data.get('should_decompose', False))
        suggestion_confidence = data.get('suggestion_confidence', data.get('confidence', 0.7))

        return {
            'estimated_tokens': int(data['estimated_tokens']),
            'estimated_loc': int(data['estimated_loc']),
            'estimated_files': int(data['estimated_files']),
            'complexity_score': float(data['complexity_score']),
            'suggest_decompose': bool(suggest_decompose),
            'decomposition_reason': data.get('decomposition_reason', ''),
            'subtask_suggestions': data.get('subtask_suggestions', []),
            'suggestion_confidence': float(suggestion_confidence),
            'indicators': ['LLM analysis'],
            'estimated_duration_minutes': estimated_duration_minutes,
        }

    def _combine_estimates(
        self,
        heuristic_result: Dict[str, Any],
        llm_result: Optional[Dict[str, Any]] = None
    ) -> ComplexityEstimate:
        """Merge heuristic and LLM estimates using weighted average.

        If both estimates available: 40% heuristic + 60% LLM
        If only heuristic: 100% heuristic

        The weights favor LLM analysis as it tends to be more accurate,
        but heuristics provide a safety net when LLM is unavailable.

        Args:
            heuristic_result: Result from _heuristic_analysis
            llm_result: Optional result from _llm_analysis

        Returns:
            ComplexityEstimate instance with combined estimates
        """
        if llm_result:
            # Weighted combination: 40% heuristic, 60% LLM
            estimated_tokens = int(
                0.4 * heuristic_result['estimated_tokens'] +
                0.6 * llm_result['estimated_tokens']
            )
            estimated_loc = int(
                0.4 * heuristic_result['estimated_loc'] +
                0.6 * llm_result['estimated_loc']
            )
            estimated_files = int(
                0.4 * heuristic_result['estimated_files'] +
                0.6 * llm_result['estimated_files']
            )
            complexity_score = (
                0.4 * heuristic_result['complexity_score'] +
                0.6 * llm_result['complexity_score']
            )
            confidence = (
                0.4 * heuristic_result['confidence'] +
                0.6 * llm_result['confidence']
            )
            estimated_duration = int(
                0.4 * heuristic_result['estimated_duration_minutes'] +
                0.6 * llm_result['estimated_duration_minutes']
            )

            # Use LLM's decomposition suggestion if confidence is high
            if llm_result['suggestion_confidence'] >= 0.7:
                suggests_decomposition = llm_result['suggest_decompose']
                suggestion_confidence = llm_result['suggestion_confidence']
            else:
                # Fall back to threshold-based decision
                threshold = self.thresholds['decomposition_thresholds']
                # Use suggestion_threshold (PHASE_5B) or fallback to decompose_threshold
                score_threshold = threshold.get('suggestion_threshold', threshold.get('decompose_threshold', 60))
                suggests_decomposition = (
                    complexity_score >= score_threshold or
                    estimated_loc >= threshold.get('max_loc_estimate', 400) or
                    estimated_files >= threshold.get('max_files', 5) or
                    estimated_tokens >= threshold.get('max_tokens', 8000)
                )
                # Lower confidence when falling back to heuristics
                suggestion_confidence = 0.6
        else:
            # Use heuristic only
            estimated_tokens = heuristic_result['estimated_tokens']
            estimated_loc = heuristic_result['estimated_loc']
            estimated_files = heuristic_result['estimated_files']
            complexity_score = heuristic_result['complexity_score']
            estimated_duration = heuristic_result['estimated_duration_minutes']

            # Threshold-based decomposition decision
            threshold = self.thresholds['decomposition_thresholds']
            # Use suggestion_threshold (PHASE_5B) or fallback to decompose_threshold
            score_threshold = threshold.get('suggestion_threshold', threshold.get('decompose_threshold', 60))
            suggests_decomposition = (
                complexity_score >= score_threshold or
                estimated_loc >= threshold.get('max_loc_estimate', 400) or
                estimated_files >= threshold.get('max_files', 5) or
                estimated_tokens >= threshold.get('max_tokens', 8000)
            )

            # Calculate suggestion confidence from heuristics
            suggestion_confidence = self._calculate_suggestion_confidence(
                heuristic_result=heuristic_result,
                llm_result=None
            )

        # Generate rationale for the suggestion
        suggestion_rationale = self._generate_suggestion_rationale(
            combined={
                'complexity_score': complexity_score,
                'estimated_tokens': estimated_tokens,
                'estimated_loc': estimated_loc,
                'estimated_files': estimated_files
            },
            suggests_decomposition=suggests_decomposition
        )

        # Create ComplexityEstimate (without task_id for now, will be set by caller)
        return ComplexityEstimate(
            task_id=0,  # Placeholder, will be replaced
            estimated_tokens=estimated_tokens,
            estimated_loc=estimated_loc,
            estimated_files=estimated_files,
            complexity_score=min(100.0, complexity_score),
            obra_suggests_decomposition=suggests_decomposition,
            obra_suggestion_confidence=min(1.0, suggestion_confidence),
            suggested_subtasks=[],  # Will be populated if needed
            suggested_parallel_groups=[],  # Will be populated if needed
            estimated_duration_minutes=estimated_duration,
            suggestion_rationale=suggestion_rationale,
            timestamp=datetime.now()
        )

    def _calculate_suggestion_confidence(
        self,
        heuristic_result: Dict,
        llm_result: Optional[Dict]
    ) -> float:
        """Calculate confidence in Obra's suggestion (0-1).

        Confidence is higher when:
        - LLM analysis is available (0.8 base)
        - Complexity score is far from threshold (not near boundary)
        - Multiple indicators agree

        Args:
            heuristic_result: Result from _heuristic_analysis
            llm_result: Optional result from _llm_analysis

        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = 0.6  # Heuristics alone

        if llm_result:
            # LLM analysis increases confidence
            base_confidence = 0.8

        # Reduce confidence if near threshold (ambiguous zone)
        thresholds = self.thresholds['decomposition_thresholds']
        # Use suggestion_threshold (PHASE_5B) or fallback to decompose_threshold
        score_threshold = thresholds.get('suggestion_threshold', thresholds.get('decompose_threshold', 60))
        complexity_score = heuristic_result.get('complexity_score', 50)

        # Within 10 points of threshold = less confident
        if abs(complexity_score - score_threshold) < 10:
            base_confidence *= 0.8  # 20% reduction

        return min(1.0, base_confidence)

    def _generate_suggestion_rationale(
        self,
        combined: Dict,
        suggests_decomposition: bool
    ) -> str:
        """Generate rationale for Obra's suggestion.

        Creates human-readable explanation for why Obra suggests
        decomposition or keeping the task as-is.

        Args:
            combined: Combined metrics (score, tokens, loc, files)
            suggests_decomposition: Whether decomposition is suggested

        Returns:
            Rationale string explaining the suggestion
        """
        score = combined.get('complexity_score', 0)
        tokens = combined.get('estimated_tokens', 0)
        files = combined.get('estimated_files', 0)
        loc = combined.get('estimated_loc', 0)

        if suggests_decomposition:
            reasons = []
            if score >= 70:
                reasons.append(f"high complexity score ({score:.0f}/100)")
            if tokens >= 8000:
                reasons.append(f"large token estimate ({tokens})")
            if files >= 5:
                reasons.append(f"multiple files affected ({files})")
            if loc >= 400:
                reasons.append(f"substantial LOC estimate ({loc})")

            reason_str = ", ".join(reasons) if reasons else f"complexity score {score:.0f}/100"
            return (
                f"Based on {reason_str}, this task may benefit from decomposition "
                f"for better manageability. Claude should review and decide based on codebase context."
            )
        else:
            return (
                f"Complexity score {score:.0f}/100 with {tokens} estimated tokens across {files} files "
                f"suggests this task is manageable as a single unit. Claude may still choose to decompose "
                f"based on architectural considerations."
            )

    def _suggest_decomposition(
        self,
        task: Any,
        complexity_estimate: ComplexityEstimate,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate subtask suggestions if obra_suggests_decomposition=True.

        Uses pattern-based decomposition strategies based on task description
        and type. Common patterns:
        - Feature: Design → Implement → Test → Document
        - Bug fix: Reproduce → Fix → Test → Verify
        - Refactor: Analyze → Plan → Execute → Validate

        Args:
            task: Task model with description
            complexity_estimate: ComplexityEstimate indicating decomposition needed
            context: Optional context dictionary

        Returns:
            List of subtask description strings
        """
        context = context or {}
        description = task.description.lower()
        suggestions = []

        # If LLM provided suggestions, use those
        # (This requires passing LLM result through, which we'll do via context)
        if 'llm_subtask_suggestions' in context and context['llm_subtask_suggestions']:
            return context['llm_subtask_suggestions']

        # Pattern-based decomposition
        task_type = context.get('task_type', '')

        # Feature implementation pattern
        if any(kw in description for kw in ['implement', 'create', 'build', 'add feature']):
            suggestions = [
                "Design data models and API interfaces",
                "Implement core functionality",
                "Add comprehensive test coverage",
                "Write user documentation and examples"
            ]

        # Bug fix pattern
        elif any(kw in description for kw in ['fix', 'bug', 'issue', 'error']):
            suggestions = [
                "Reproduce the bug with minimal test case",
                "Identify root cause and implement fix",
                "Add regression tests to prevent recurrence",
                "Verify fix in production-like environment"
            ]

        # Refactoring pattern
        elif 'refactor' in description:
            suggestions = [
                "Analyze current code structure and identify issues",
                "Plan refactoring approach and migration strategy",
                "Execute refactoring with test coverage maintained",
                "Validate functionality and performance"
            ]

        # Integration pattern
        elif any(kw in description for kw in ['integrate', 'connect', 'api']):
            suggestions = [
                "Design integration interfaces and contracts",
                "Implement integration layer with error handling",
                "Add integration tests and mocking",
                "Document integration setup and usage"
            ]

        # Database/schema pattern
        elif any(kw in description for kw in ['database', 'schema', 'migration']):
            suggestions = [
                "Design schema changes and migration strategy",
                "Implement migration scripts with rollback",
                "Update ORM models and queries",
                "Test migration on staging environment"
            ]

        # Default decomposition by scope
        else:
            # Generic decomposition based on estimated files
            if complexity_estimate.estimated_files > 5:
                suggestions = [
                    "Implement core components and data structures",
                    "Add supporting utilities and helpers",
                    "Implement integration and coordination logic",
                    "Add comprehensive tests and documentation"
                ]
            elif complexity_estimate.estimated_loc > 300:
                suggestions = [
                    "Implement main functionality",
                    "Add error handling and validation",
                    "Add tests and documentation"
                ]
            else:
                # Shouldn't decompose, but provide generic suggestions anyway
                suggestions = [
                    "Implement core changes",
                    "Add tests",
                    "Update documentation"
                ]

        # Ensure we have 3-7 suggestions
        if len(suggestions) < 3:
            suggestions.append("Validate changes and handle edge cases")
        if len(suggestions) > 7:
            suggestions = suggestions[:7]

        logger.info(
            "Generated %d decomposition suggestions for task %s",
            len(suggestions), task.id
        )

        return suggestions

    def analyze_parallelization_opportunities(
        self,
        subtasks: List[SubTask],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Analyze subtasks for parallelization opportunities.

        This method identifies which subtasks can be executed in parallel by
        building a dependency graph and finding independent groups of work.
        Uses topological sorting to organize subtasks into "levels" where all
        tasks in a level can run concurrently.

        Args:
            subtasks: List of SubTask instances from decomposition
            context: Optional context (file dependencies, resource constraints)

        Returns:
            List of parallelization opportunity dicts, each containing:
            - group_id: int (sequential group number)
            - subtask_ids: List[int] (tasks that can run in parallel)
            - estimated_duration_minutes: int (max duration in group)
            - can_parallelize: bool (True if group has 2+ tasks)
            - speedup_estimate: Dict with sequential/parallel/time_saved
            - resource_requirements: Dict (estimated resources)

        Example:
            >>> subtasks = [
            ...     SubTask(1, 100, "Design", "...", 30, 45, []),
            ...     SubTask(2, 100, "Implement", "...", 50, 90, [1]),
            ...     SubTask(3, 100, "Test", "...", 40, 60, [2])
            ... ]
            >>> opportunities = estimator.analyze_parallelization_opportunities(subtasks)
            >>> # Returns groups with parallel execution plan

        Thread-safety:
            This method is thread-safe via self._lock.
        """
        if not subtasks:
            logger.warning("No subtasks provided for parallelization analysis")
            return []

        with self._lock:
            logger.info(
                "Analyzing parallelization opportunities for %d subtasks",
                len(subtasks)
            )

            # Step 1: Build dependency graph
            dependency_graph = self._build_dependency_graph(subtasks)
            logger.debug("Dependency graph: %s", dependency_graph)

            # Step 2: Identify parallelizable groups using topological sorting
            parallel_levels = self._identify_parallelizable_subtasks(
                dependency_graph,
                subtasks
            )
            logger.debug("Parallel levels: %s", parallel_levels)

            # Step 3: Create parallel group specifications
            parallel_groups = self._create_parallel_groups(parallel_levels, subtasks)
            logger.debug("Created %d parallel groups", len(parallel_groups))

            # Step 4: Add speedup estimates to each group
            speedup_info = self._estimate_parallel_speedup(parallel_groups, subtasks)
            logger.info(
                "Parallelization analysis complete: %.1fx speedup potential",
                speedup_info.get('speedup_factor', 1.0)
            )

            # Add speedup estimate to each group
            for group in parallel_groups:
                # Calculate group-specific speedup
                group_subtasks = [
                    st for st in subtasks if st.subtask_id in group['subtask_ids']
                ]
                sequential_time = sum(st.estimated_duration_minutes for st in group_subtasks)
                parallel_time = max(
                    (st.estimated_duration_minutes for st in group_subtasks),
                    default=0
                )

                group['speedup_estimate'] = {
                    'sequential': sequential_time,
                    'parallel': parallel_time,
                    'time_saved': sequential_time - parallel_time
                }

            return parallel_groups

    def _build_dependency_graph(
        self,
        subtasks: List[SubTask]
    ) -> Dict[int, Set[int]]:
        """Build dependency graph from subtasks.

        Creates a graph where each node (subtask) maps to a set of nodes
        (subtasks) it depends on. Dependencies are extracted from the
        SubTask.dependencies field.

        Args:
            subtasks: List of SubTask instances

        Returns:
            Dict mapping subtask_id -> set of subtask_ids it depends on

        Example:
            >>> subtasks = [
            ...     SubTask(1, 100, "Design", "...", 30, 45, []),
            ...     SubTask(2, 100, "Implement", "...", 50, 90, [1]),
            ...     SubTask(3, 100, "Test", "...", 40, 60, [1]),
            ...     SubTask(4, 100, "Deploy", "...", 30, 30, [2, 3])
            ... ]
            >>> graph = estimator._build_dependency_graph(subtasks)
            >>> graph
            {1: set(), 2: {1}, 3: {1}, 4: {2, 3}}

        Thread-safety:
            Called within _lock context from public methods.
        """
        graph: Dict[int, Set[int]] = {}

        # Initialize all nodes
        for subtask in subtasks:
            graph[subtask.subtask_id] = set(subtask.dependencies)

        # Validate dependencies exist
        valid_ids = {st.subtask_id for st in subtasks}
        for subtask_id, deps in graph.items():
            invalid_deps = deps - valid_ids
            if invalid_deps:
                logger.warning(
                    "Subtask %d has invalid dependencies: %s",
                    subtask_id,
                    invalid_deps
                )
                # Remove invalid dependencies
                graph[subtask_id] = deps & valid_ids

        return graph

    def _identify_parallelizable_subtasks(
        self,
        dependency_graph: Dict[int, Set[int]],
        subtasks: List[SubTask]
    ) -> List[List[int]]:
        """Identify groups of subtasks that can run in parallel.

        Uses topological sorting (Kahn's algorithm) to organize subtasks into
        "levels" where all tasks in a level have no dependencies on each other
        and can therefore run in parallel. Each level must complete before the
        next level can begin.

        Args:
            dependency_graph: Graph from _build_dependency_graph()
            subtasks: List of SubTask instances

        Returns:
            List of parallel groups, where each group is a list of subtask_ids
            that can run simultaneously. Groups are ordered by execution level.

        Example:
            >>> graph = {1: set(), 2: {1}, 3: {1}, 4: {2, 3}}
            >>> levels = estimator._identify_parallelizable_subtasks(graph, subtasks)
            >>> levels
            [[1], [2, 3], [4]]
            # Level 0: task 1 runs alone (no dependencies)
            # Level 1: tasks 2 and 3 run in parallel (both depend only on 1)
            # Level 2: task 4 runs alone (depends on 2 and 3)

        Thread-safety:
            Called within _lock context from public methods.

        Note:
            Detects circular dependencies and logs warnings. Circular
            dependencies will result in incomplete parallelization.
        """
        # Create a copy of the graph to avoid modifying the original
        graph = {k: v.copy() for k, v in dependency_graph.items()}

        # Calculate in-degree for each node (number of dependencies)
        in_degree: Dict[int, int] = {subtask_id: len(deps) for subtask_id, deps in graph.items()}

        # Initialize queue with nodes that have no dependencies
        queue: deque = deque([
            subtask_id for subtask_id, degree in in_degree.items() if degree == 0
        ])

        levels: List[List[int]] = []
        processed_count = 0

        while queue:
            # All nodes in queue can run in parallel (same level)
            current_level = list(queue)
            levels.append(current_level)
            queue.clear()

            # Process this level's nodes
            for subtask_id in current_level:
                processed_count += 1

                # Find all nodes that depend on this one
                for other_id, deps in graph.items():
                    if subtask_id in deps:
                        # Remove this dependency
                        deps.remove(subtask_id)
                        in_degree[other_id] -= 1

                        # If all dependencies are satisfied, add to queue
                        if in_degree[other_id] == 0:
                            queue.append(other_id)

        # Check for circular dependencies
        if processed_count < len(graph):
            unprocessed = [
                subtask_id for subtask_id in graph.keys()
                if subtask_id not in [id for level in levels for id in level]
            ]
            logger.warning(
                "Circular dependency detected: %d subtasks could not be processed: %s",
                len(unprocessed),
                unprocessed
            )

        logger.debug("Identified %d parallel levels", len(levels))
        return levels

    def _create_parallel_groups(
        self,
        parallel_levels: List[List[int]],
        subtasks: List[SubTask]
    ) -> List[Dict[str, Any]]:
        """Create parallel group specifications for orchestration.

        Converts the parallel levels into structured group dictionaries that
        can be used by the orchestration engine to schedule parallel execution.

        Args:
            parallel_levels: Output from _identify_parallelizable_subtasks()
            subtasks: List of SubTask instances

        Returns:
            List of dicts with parallel group specifications:
            - group_id: int (sequential group number, 0-indexed)
            - subtask_ids: List[int] (tasks in this group)
            - estimated_duration_minutes: int (max duration in group)
            - can_parallelize: bool (True if 2+ tasks in group)
            - resource_requirements: Dict (estimated resources)

        Example:
            >>> levels = [[1], [2, 3], [4]]
            >>> groups = estimator._create_parallel_groups(levels, subtasks)
            >>> groups[1]
            {
                'group_id': 1,
                'subtask_ids': [2, 3],
                'estimated_duration_minutes': 90,  # max(90, 60)
                'can_parallelize': True,
                'resource_requirements': {'max_agents': 2}
            }

        Thread-safety:
            Called within _lock context from public methods.
        """
        # Create subtask lookup for quick access
        subtask_map = {st.subtask_id: st for st in subtasks}

        parallel_groups = []

        for group_id, level in enumerate(parallel_levels):
            # Get subtasks in this level
            level_subtasks = [
                subtask_map[subtask_id]
                for subtask_id in level
                if subtask_id in subtask_map
            ]

            if not level_subtasks:
                continue

            # Calculate max duration (bottleneck task)
            max_duration = max(
                st.estimated_duration_minutes for st in level_subtasks
            )

            # Determine if parallelization is beneficial
            can_parallelize = len(level_subtasks) > 1

            # Estimate resource requirements
            resource_requirements = {
                'max_agents': len(level_subtasks),
                'max_complexity': max(st.estimated_complexity for st in level_subtasks),
                'total_complexity': sum(st.estimated_complexity for st in level_subtasks)
            }

            parallel_groups.append({
                'group_id': group_id,
                'subtask_ids': level,
                'estimated_duration_minutes': max_duration,
                'can_parallelize': can_parallelize,
                'resource_requirements': resource_requirements
            })

        return parallel_groups

    def _estimate_parallel_speedup(
        self,
        parallel_groups: List[Dict[str, Any]],
        subtasks: List[SubTask]
    ) -> Dict[str, Any]:
        """Calculate estimated time savings from parallelization.

        Compares sequential execution time (all tasks run one after another)
        with parallel execution time (tasks in same group run simultaneously)
        to estimate speedup and efficiency.

        Args:
            parallel_groups: Output from _create_parallel_groups()
            subtasks: List of SubTask instances

        Returns:
            Dict with speedup metrics:
            - sequential_duration_minutes: int (total if all tasks sequential)
            - parallel_duration_minutes: int (total with parallelization)
            - time_saved_minutes: int (difference)
            - speedup_factor: float (sequential / parallel)
            - efficiency: float (speedup / num_groups)

        Example:
            >>> groups = [
            ...     {'group_id': 0, 'subtask_ids': [1], 'estimated_duration_minutes': 45},
            ...     {'group_id': 1, 'subtask_ids': [2, 3], 'estimated_duration_minutes': 90},
            ...     {'group_id': 2, 'subtask_ids': [4], 'estimated_duration_minutes': 30}
            ... ]
            >>> speedup = estimator._estimate_parallel_speedup(groups, subtasks)
            >>> speedup
            {
                'sequential_duration_minutes': 225,  # 45 + 90 + 60 + 30
                'parallel_duration_minutes': 165,    # 45 + 90 + 30
                'time_saved_minutes': 60,
                'speedup_factor': 1.36,              # 225 / 165
                'efficiency': 0.45                   # 1.36 / 3 groups
            }

        Thread-safety:
            Called within _lock context from public methods.
        """
        # Calculate sequential duration (sum all tasks)
        sequential_duration = sum(st.estimated_duration_minutes for st in subtasks)

        # Calculate parallel duration (sum of group max durations)
        parallel_duration = sum(
            group['estimated_duration_minutes'] for group in parallel_groups
        )

        # Time saved
        time_saved = max(0, sequential_duration - parallel_duration)

        # Speedup factor
        if parallel_duration > 0:
            speedup_factor = sequential_duration / parallel_duration
        else:
            speedup_factor = 1.0

        # Efficiency (how well we use parallelization)
        num_groups = len(parallel_groups)
        if num_groups > 0:
            efficiency = speedup_factor / num_groups
        else:
            efficiency = 0.0

        return {
            'sequential_duration_minutes': sequential_duration,
            'parallel_duration_minutes': parallel_duration,
            'time_saved_minutes': time_saved,
            'speedup_factor': speedup_factor,
            'efficiency': efficiency
        }

    def _create_subtasks_from_suggestions(
        self,
        task_id: int,
        suggestions: List[str],
        estimate: ComplexityEstimate
    ) -> List[SubTask]:
        """Create SubTask instances from decomposition suggestions.

        Converts string suggestions into structured SubTask objects with
        estimated complexity, duration, and auto-detected dependencies based
        on common patterns in the suggestion text.

        Args:
            task_id: Parent task ID
            suggestions: List of subtask description strings
            estimate: ComplexityEstimate with overall complexity info

        Returns:
            List of SubTask instances with:
            - Estimated complexity (distributed from parent)
            - Estimated duration (distributed from parent)
            - Auto-detected dependencies based on patterns
            - Parallelization flags set appropriately

        Example:
            >>> suggestions = [
            ...     "Design data models",
            ...     "Implement core functionality",
            ...     "Add tests",
            ...     "Document API"
            ... ]
            >>> subtasks = estimator._create_subtasks_from_suggestions(
            ...     task_id=100,
            ...     suggestions=suggestions,
            ...     estimate=estimate
            ... )
            >>> subtasks[0].dependencies
            []  # Design has no dependencies
            >>> subtasks[1].dependencies
            [1]  # Implement depends on Design

        Thread-safety:
            Called within _lock context from public methods.

        Note:
            Dependencies are detected heuristically using keyword patterns:
            - "Design/Plan/Architecture" tasks have no dependencies
            - "Implement/Build/Create" tasks depend on design tasks
            - "Test/Verify" tasks depend on implementation tasks
            - "Document" tasks can run in parallel with tests
            - "Deploy/Release" tasks depend on all other tasks
        """
        if not suggestions:
            return []

        # Distribute complexity and duration across subtasks
        num_subtasks = len(suggestions)
        avg_complexity = estimate.complexity_score / num_subtasks
        avg_duration = estimate.estimated_duration_minutes / num_subtasks

        subtasks: List[SubTask] = []

        # Track subtask categories for dependency detection
        design_tasks: List[int] = []
        implement_tasks: List[int] = []
        test_tasks: List[int] = []

        for idx, suggestion in enumerate(suggestions):
            subtask_id = idx + 1  # 1-indexed
            suggestion_lower = suggestion.lower()

            # Detect task category and set dependencies
            dependencies: List[int] = []

            if any(kw in suggestion_lower for kw in ['design', 'plan', 'architecture', 'model']):
                # Design tasks: no dependencies, runs first
                design_tasks.append(subtask_id)
                complexity_mult = 0.8  # Usually less complex

            elif any(kw in suggestion_lower for kw in ['implement', 'build', 'create', 'develop', 'add']):
                # Implementation tasks: depend on design
                dependencies = design_tasks.copy()
                implement_tasks.append(subtask_id)
                complexity_mult = 1.2  # Usually more complex

            elif any(kw in suggestion_lower for kw in ['test', 'verify', 'validate']):
                # Test tasks: depend on implementation
                dependencies = implement_tasks.copy()
                test_tasks.append(subtask_id)
                complexity_mult = 0.7  # Usually less complex

            elif any(kw in suggestion_lower for kw in ['document', 'write docs', 'readme']):
                # Documentation: can run in parallel with tests
                # Only depends on implementation
                dependencies = implement_tasks.copy()
                complexity_mult = 0.5  # Usually least complex

            elif any(kw in suggestion_lower for kw in ['integrate', 'connect', 'hook up']):
                # Integration: depends on implementation
                dependencies = implement_tasks.copy()
                complexity_mult = 1.0

            elif any(kw in suggestion_lower for kw in ['deploy', 'release', 'ship']):
                # Deployment: depends on everything
                dependencies = list(range(1, subtask_id))  # All previous tasks
                complexity_mult = 0.9

            else:
                # Unknown category: sequential dependency on previous task
                if idx > 0:
                    dependencies = [idx]  # Depend on previous task
                complexity_mult = 1.0

            # Create SubTask
            subtask = SubTask(
                subtask_id=subtask_id,
                parent_task_id=task_id,
                title=suggestion[:80],  # Truncate long titles
                description=suggestion,
                estimated_complexity=min(100.0, avg_complexity * complexity_mult),
                estimated_duration_minutes=max(15, int(avg_duration * complexity_mult)),
                dependencies=dependencies,
                parallelizable=(len(dependencies) == 0 or idx == 0),  # Can parallelize if no deps
                parallel_group=None,  # Will be set by parallelization analysis
                status="pending",
                assigned_agent_id=None,
                created_at=datetime.now()
            )

            subtasks.append(subtask)

        logger.info(
            "Created %d subtasks from suggestions for task %d",
            len(subtasks), task_id
        )

        return subtasks

    def _log_estimate(self, estimate: ComplexityEstimate) -> None:
        """Log complexity estimate to database via StateManager.

        Converts estimate to dictionary and calls state_manager to persist.
        Errors are logged but not raised to avoid breaking the estimation flow.

        Args:
            estimate: ComplexityEstimate to log

        Note:
            Only logs if state_manager was provided during initialization.
        """
        if not self.state_manager:
            return

        try:
            # Convert to dictionary for logging
            estimate_data = estimate.to_dict()

            # Log to state manager (assuming it has this method)
            # Note: Actual StateManager API may differ, adjust as needed
            if hasattr(self.state_manager, 'log_complexity_estimate'):
                self.state_manager.log_complexity_estimate(estimate_data)
                logger.debug("Logged complexity estimate for task %s", estimate.task_id)
            else:
                logger.warning(
                    "StateManager does not have log_complexity_estimate method"
                )

        except Exception as e:
            logger.error("Failed to log complexity estimate: %s", e, exc_info=True)
