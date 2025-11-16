"""NL Variation Generator for stress testing NL command parsing.

Generates semantic variations of natural language commands to validate
robustness of intent classification, entity extraction, and parsing.

Uses real LLM (OpenAI Codex or configured provider) to generate variations
with different phrasings, synonyms, case variations, and subtle typos.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VariationCategory:
    """Category of variation with generation strategy."""
    name: str
    description: str
    count: int  # Number of variations to generate in this category


class NLVariationGenerator:
    """Generate NL command variations for stress testing.

    Uses LLM to generate semantically equivalent variations of commands
    with different phrasings, synonyms, case, typos, and verbosity.

    Example:
        >>> generator = NLVariationGenerator(llm_plugin)
        >>> variations = generator.generate_variations(
        ...     "create epic for user authentication",
        ...     count=100
        ... )
        >>> print(len(variations))  # 100
    """

    # Variation categories with distribution
    CATEGORIES = [
        VariationCategory(
            name="synonyms",
            description="Replace action verbs with synonyms (create→add, make, build)",
            count=20
        ),
        VariationCategory(
            name="phrasings",
            description="Rephrase command structure (create X → I need X, add X, make X)",
            count=25
        ),
        VariationCategory(
            name="case",
            description="Vary capitalization (lowercase, UPPERCASE, Title Case)",
            count=15
        ),
        VariationCategory(
            name="typos",
            description="Inject subtle misspellings (create→crete, epic→epik)",
            count=15
        ),
        VariationCategory(
            name="verbose",
            description="Add politeness and filler words (please, can you, I would like)",
            count=25
        )
    ]

    def __init__(self, llm_plugin):
        """Initialize variation generator with LLM plugin.

        Args:
            llm_plugin: LLM plugin instance (OpenAI Codex or any LLMPlugin)
        """
        self.llm = llm_plugin

    def generate_variations(
        self,
        base_command: str,
        count: int = 100,
        categories: Optional[List[str]] = None
    ) -> List[str]:
        """Generate variations of a base command.

        Args:
            base_command: Base NL command to vary
            count: Total number of variations to generate
            categories: Optional list of category names to use (default: all)

        Returns:
            List of variation strings (semantically equivalent to base)

        Example:
            >>> variations = generator.generate_variations(
            ...     "create epic for user authentication",
            ...     count=100
            ... )
        """
        logger.info(f"Generating {count} variations for: '{base_command}'")

        # Filter categories if specified
        active_categories = self.CATEGORIES
        if categories:
            active_categories = [c for c in self.CATEGORIES if c.name in categories]

        # Calculate distribution across categories
        total_category_count = sum(c.count for c in active_categories)
        variations = []

        for category in active_categories:
            # Scale category count proportionally
            category_count = int((category.count / total_category_count) * count)

            logger.debug(f"Generating {category_count} variations for category: {category.name}")

            # Generate variations for this category
            category_variations = self._generate_category_variations(
                base_command,
                category,
                category_count
            )

            variations.extend(category_variations)

        # Ensure we have exactly 'count' variations
        # (may be slightly off due to rounding)
        if len(variations) < count:
            # Generate a few more random variations
            extra_count = count - len(variations)
            extra = self._generate_mixed_variations(base_command, extra_count)
            variations.extend(extra)
        elif len(variations) > count:
            # Trim to exact count
            variations = variations[:count]

        logger.info(f"Generated {len(variations)} variations successfully")
        return variations

    def _generate_category_variations(
        self,
        base_command: str,
        category: VariationCategory,
        count: int
    ) -> List[str]:
        """Generate variations for a specific category.

        Args:
            base_command: Base command
            category: VariationCategory instance
            count: Number to generate

        Returns:
            List of variations for this category
        """
        # Build LLM prompt for category-specific generation
        prompt = f"""Generate {count} variations of this command: "{base_command}"

Variation strategy: {category.description}

Requirements:
1. Each variation must be semantically equivalent to the original
2. Each variation should be a COMPLETE natural language command
3. Variations should feel natural (how a human would phrase it)
4. Return ONLY the variations, one per line
5. Do not number them or add any other text

Examples for strategy "{category.name}":
"""

        # Add category-specific examples
        if category.name == "synonyms":
            prompt += """- "add epic for user authentication"
- "make epic for user authentication"
- "build epic for user authentication"
"""
        elif category.name == "phrasings":
            prompt += """- "I need an epic for user authentication"
- "I want to create an epic for user authentication"
- "add an epic called user authentication"
"""
        elif category.name == "case":
            prompt += """- "CREATE EPIC FOR USER AUTHENTICATION"
- "Create Epic For User Authentication"
- "create epic for user authentication"
"""
        elif category.name == "typos":
            prompt += """- "crete epic for user authentication"
- "create epik for user authentication"
- "create epic for user autentication"
"""
        elif category.name == "verbose":
            prompt += """- "please create epic for user authentication"
- "can you create epic for user authentication"
- "I would like to create epic for user authentication"
"""

        prompt += f"\nNow generate {count} variations:\n"

        # Call LLM
        try:
            response = self.llm.generate(prompt, max_tokens=2000)

            # Parse response (one variation per line)
            variations = [
                line.strip()
                for line in response.strip().split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]

            # Filter out any numbered lines (1., 2., etc.)
            variations = [
                v.split('.', 1)[-1].strip() if v[0].isdigit() else v
                for v in variations
            ]

            # Ensure we have at least some variations
            if not variations:
                logger.warning(f"No variations generated for category {category.name}, using fallback")
                variations = [base_command]  # Fallback to base command

            logger.debug(f"Generated {len(variations)} variations for {category.name}")
            return variations[:count]  # Trim to requested count

        except Exception as e:
            logger.error(f"Failed to generate variations for {category.name}: {e}")
            # Fallback: return base command repeated
            return [base_command] * count

    def _generate_mixed_variations(self, base_command: str, count: int) -> List[str]:
        """Generate mixed variations (random categories).

        Args:
            base_command: Base command
            count: Number to generate

        Returns:
            List of mixed variations
        """
        prompt = f"""Generate {count} different variations of this command: "{base_command}"

Mix different strategies:
- Synonyms (create→add, make, build)
- Different phrasings (create X → I need X)
- Case variations (lowercase, UPPERCASE, Title Case)
- Politeness (please, can you, I would like)

Requirements:
1. Each variation must be semantically equivalent
2. Use different strategies for variety
3. Return ONLY the variations, one per line

Generate {count} variations:
"""

        try:
            response = self.llm.generate(prompt, max_tokens=1500)
            variations = [
                line.strip()
                for line in response.strip().split('\n')
                if line.strip()
            ]
            return variations[:count]
        except Exception as e:
            logger.error(f"Failed to generate mixed variations: {e}")
            return [base_command] * count

    def validate_variation(self, base_command: str, variation: str) -> Dict[str, Any]:
        """Validate that a variation is semantically equivalent to base.

        Uses LLM to check if variation has same intent as base command.

        Args:
            base_command: Original command
            variation: Variation to validate

        Returns:
            Dictionary with validation results:
                - is_valid: bool
                - confidence: float (0-1)
                - reasoning: str

        Example:
            >>> result = generator.validate_variation(
            ...     "create epic for user auth",
            ...     "add an epic for authentication"
            ... )
            >>> print(result['is_valid'])  # True
        """
        prompt = f"""Are these two commands semantically equivalent?

Command 1: "{base_command}"
Command 2: "{variation}"

Answer in JSON format:
{{
    "is_equivalent": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

JSON response:
"""

        try:
            response = self.llm.generate(prompt, max_tokens=200)

            # Try to parse JSON from response
            # Handle cases where LLM wraps in markdown code blocks
            response = response.strip()
            if response.startswith('```json'):
                response = response.split('```json')[1]
            if response.startswith('```'):
                response = response.split('```')[1]
            if response.endswith('```'):
                response = response.rsplit('```', 1)[0]

            result = json.loads(response.strip())

            return {
                'is_valid': result.get('is_equivalent', False),
                'confidence': result.get('confidence', 0.0),
                'reasoning': result.get('reasoning', '')
            }

        except Exception as e:
            logger.error(f"Failed to validate variation: {e}")
            return {
                'is_valid': False,
                'confidence': 0.0,
                'reasoning': f'Validation error: {e}'
            }

    def generate_and_validate(
        self,
        base_command: str,
        count: int = 100,
        min_confidence: float = 0.7
    ) -> Dict[str, Any]:
        """Generate variations and validate semantic equivalence.

        Args:
            base_command: Base command
            count: Number of variations to generate
            min_confidence: Minimum confidence for validation

        Returns:
            Dictionary with:
                - variations: List of valid variations
                - rejected: List of rejected variations with reasons
                - stats: Statistics about generation
        """
        # Generate variations
        variations = self.generate_variations(base_command, count)

        # Validate each variation (sample only, full validation is expensive)
        sample_size = min(10, len(variations))
        valid_variations = []
        rejected = []

        logger.info(f"Validating {sample_size} sample variations...")

        for i, variation in enumerate(variations[:sample_size]):
            validation = self.validate_variation(base_command, variation)

            if validation['is_valid'] and validation['confidence'] >= min_confidence:
                valid_variations.append(variation)
            else:
                rejected.append({
                    'variation': variation,
                    'reason': validation['reasoning'],
                    'confidence': validation['confidence']
                })

        # If sample validation passes, assume rest are valid
        if len(valid_variations) >= sample_size * 0.8:  # 80% pass rate
            logger.info(f"Sample validation passed ({len(valid_variations)}/{sample_size}), assuming rest valid")
            final_variations = variations
        else:
            logger.warning(f"Sample validation failed ({len(valid_variations)}/{sample_size}), returning only validated")
            final_variations = valid_variations

        return {
            'variations': final_variations,
            'rejected': rejected,
            'stats': {
                'total_generated': len(variations),
                'sample_validated': sample_size,
                'sample_valid': len(valid_variations),
                'sample_rejected': len(rejected),
                'final_count': len(final_variations)
            }
        }
