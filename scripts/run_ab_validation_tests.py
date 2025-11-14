#!/usr/bin/env python3
"""Run A/B validation tests comparing structured vs unstructured prompts.

This script executes TASK_6.3 from PHASE_6 of the LLM-First Implementation Plan.
It runs 20-30 validation tasks with both prompt formats and generates a comprehensive
comparison report.

Usage:
    python scripts/run_ab_validation_tests.py [--test-cases N] [--output PATH]

Example:
    python scripts/run_ab_validation_tests.py --test-cases 25 --output evaluation_results/validation_ab.json
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.core.state import StateManager
from src.core.config import Config
from src.core.models import Task, Project
from src.llm.local_interface import LocalLLMInterface
from src.llm.prompt_generator import PromptGenerator
from src.llm.structured_prompt_builder import StructuredPromptBuilder
from src.llm.prompt_rule_engine import PromptRuleEngine
from src.evaluation.ab_testing import ABTestingFramework

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_cases(state_manager: StateManager, count: int) -> list:
    """Create validation test cases.

    Args:
        state_manager: StateManager instance
        count: Number of test cases to create

    Returns:
        List of test case dictionaries
    """
    logger.info(f"Creating {count} test cases for validation")

    # Sample code snippets with varying complexity and rule violations
    code_samples = [
        # Sample 1: Stub function (violates NO_STUBS)
        '''def login_user(email, password):
    # TODO: implement login logic
    pass''',

        # Sample 2: Missing docstrings (violates COMPREHENSIVE_DOCSTRINGS)
        '''def calculate_total(items):
    return sum(item.price for item in items)''',

        # Sample 3: Hardcoded values (violates NO_HARDCODED_VALUES)
        '''def validate_token(token):
    secret_key = "my_secret_key_123"
    return jwt.decode(token, secret_key, algorithms=["HS256"])''',

        # Sample 4: Good code (should pass all rules)
        '''def process_payment(amount: float, currency: str) -> dict:
    """Process a payment transaction.

    Args:
        amount: Payment amount
        currency: Currency code (e.g., 'USD')

    Returns:
        Transaction result dict with keys: success, transaction_id, timestamp

    Raises:
        ValueError: If amount is negative or currency is invalid
    """
    if amount < 0:
        raise ValueError("Amount must be non-negative")

    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency}")

    transaction_id = generate_transaction_id()
    timestamp = datetime.now(UTC)

    result = payment_gateway.charge(
        amount=amount,
        currency=currency,
        transaction_id=transaction_id
    )

    return {
        'success': result.success,
        'transaction_id': transaction_id,
        'timestamp': timestamp.isoformat()
    }''',

        # Sample 5: No error handling (violates ERROR_HANDLING)
        '''def read_config(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)''',
    ]

    # Create tasks
    test_cases = []
    for i in range(count):
        # Create a dummy project if needed
        projects = state_manager.list_projects()
        if not projects:
            project = state_manager.create_project(
                name="AB Test Project",
                working_directory="/tmp/ab_test"
            )
        else:
            project = projects[0]

        # Create task
        task = state_manager.create_task(
            project_id=project.id,
            title=f"Validation Test Case {i+1}",
            description=f"Validate code sample {(i % len(code_samples)) + 1}"
        )

        # Select code sample (cycle through samples)
        code = code_samples[i % len(code_samples)]

        test_cases.append({
            'task': task,
            'work_output': code,
            'context': {
                'validation_criteria': [
                    'Code completeness',
                    'Rule compliance',
                    'Documentation quality',
                    'Error handling'
                ],
                'rules': []  # Will be populated by PromptRuleEngine
            }
        })

    logger.info(f"Created {len(test_cases)} test cases")
    return test_cases


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Run A/B validation tests (PHASE_6 TASK_6.3)'
    )
    parser.add_argument(
        '--test-cases',
        type=int,
        default=25,
        help='Number of test cases to run (default: 25)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='evaluation_results/ab_test_validation_prompts.json',
        help='Output JSON file path'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Configuration file path'
    )

    args = parser.parse_args()

    logger.info("=== PHASE_6 TASK_6.3: A/B Validation Tests ===")
    logger.info(f"Test cases: {args.test_cases}")
    logger.info(f"Output: {args.output}")

    # Load configuration
    try:
        config = Config.load(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        logger.info("Using default configuration")
        config = Config()

    # Initialize components
    logger.info("Initializing components...")

    # State manager
    state_manager = StateManager.get_instance(
        config.get('database.url', 'sqlite:///data/obra.db')
    )

    # LLM interface
    llm = LocalLLMInterface()
    llm.initialize({
        'endpoint': config.get('llm.endpoint', 'http://172.29.144.1:11434'),
        'model': config.get('llm.model', 'qwen2.5-coder:32b-instruct-q4_K_M'),
        'timeout': config.get('llm.timeout', 120)
    })

    # Prompt rule engine
    rule_engine = PromptRuleEngine(config_path='config/prompt_rules.yaml')
    try:
        rule_engine.load_rules_from_yaml()
        logger.info(f"Loaded {len(rule_engine._rules)} rules")
    except Exception as e:
        logger.warning(f"Failed to load rules: {e}")

    # Structured prompt builder
    structured_builder = StructuredPromptBuilder(rule_engine=rule_engine)

    # Prompt generator
    prompt_generator = PromptGenerator(
        template_dir='config',
        llm_interface=llm,
        state_manager=state_manager,
        structured_mode=False,  # Will toggle via framework
        structured_builder=structured_builder
    )

    # A/B testing framework
    ab_framework = ABTestingFramework(
        prompt_generator=prompt_generator,
        llm_interface=llm,
        state_manager=state_manager
    )

    logger.info("Components initialized successfully")

    # Create test cases
    test_cases = create_test_cases(state_manager, args.test_cases)

    # Run A/B test
    logger.info("Running A/B test...")
    try:
        result = ab_framework.run_ab_test(
            test_name='validation_prompts_ab_test',
            prompt_type='validation',
            test_cases=test_cases,
            alpha=0.05  # 95% confidence level
        )

        # Export results
        ab_framework.export_results(result, args.output)

        # Print summary
        print("\n" + "="*80)
        print(result.get_summary())
        print("="*80)
        print(f"\nResults exported to: {args.output}")

        logger.info("A/B test completed successfully")

    except Exception as e:
        logger.error(f"A/B test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
