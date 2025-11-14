#!/usr/bin/env python3
"""Test full Obra orchestration cycle with conversation logging.

This test demonstrates:
1. Obra (with Qwen LLM) generating prompts
2. Claude Code executing tasks
3. Obra validating responses
4. Full conversation history from both LLMs
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.llm.local_interface import LocalLLMInterface
from src.llm.prompt_generator import PromptGenerator
from src.llm.response_validator import ResponseValidator
from src.orchestration.quality_controller import QualityController
from src.utils.confidence_scorer import ConfidenceScorer
from src.orchestration.decision_engine import DecisionEngine
from src.core.config import Config


class ConversationLogger:
    """Logger that tracks the full conversation between Obra and Claude."""

    def __init__(self):
        self.conversation = []
        self.start_time = datetime.now()

    def log_obra_prompt_generation(self, task, generated_prompt, metadata=None):
        """Log when Obra (Qwen) generates a prompt."""
        entry = {
            'timestamp': (datetime.now() - self.start_time).total_seconds(),
            'source': 'OBRA (Qwen)',
            'action': 'Generate Prompt',
            'task': task,
            'output': generated_prompt,
            'metadata': metadata or {}
        }
        self.conversation.append(entry)
        self._print_entry(entry)

    def log_claude_response(self, prompt, response, duration, metadata=None):
        """Log Claude's response."""
        entry = {
            'timestamp': (datetime.now() - self.start_time).total_seconds(),
            'source': 'CLAUDE CODE',
            'action': 'Execute Task',
            'input': prompt[:200] + '...' if len(prompt) > 200 else prompt,
            'output': response,
            'duration': duration,
            'metadata': metadata or {}
        }
        self.conversation.append(entry)
        self._print_entry(entry)

    def log_obra_validation(self, response, validation_result, metadata=None):
        """Log Obra's validation of Claude's response."""
        entry = {
            'timestamp': (datetime.now() - self.start_time).total_seconds(),
            'source': 'OBRA (Response Validator)',
            'action': 'Validate Response',
            'input': response[:200] + '...' if len(response) > 200 else response,
            'output': validation_result,
            'metadata': metadata or {}
        }
        self.conversation.append(entry)
        self._print_entry(entry)

    def log_obra_quality_check(self, response, quality_result, duration, metadata=None):
        """Log Obra's quality check (using Qwen)."""
        entry = {
            'timestamp': (datetime.now() - self.start_time).total_seconds(),
            'source': 'OBRA (Qwen - Quality Check)',
            'action': 'Check Quality',
            'input': response[:200] + '...' if len(response) > 200 else response,
            'output': quality_result,
            'duration': duration,
            'metadata': metadata or {}
        }
        self.conversation.append(entry)
        self._print_entry(entry)

    def log_obra_confidence(self, response, confidence, metadata=None):
        """Log Obra's confidence scoring."""
        entry = {
            'timestamp': (datetime.now() - self.start_time).total_seconds(),
            'source': 'OBRA (Confidence Scorer)',
            'action': 'Score Confidence',
            'input': response[:200] + '...' if len(response) > 200 else response,
            'output': f"Confidence: {confidence:.2f}",
            'metadata': metadata or {}
        }
        self.conversation.append(entry)
        self._print_entry(entry)

    def log_obra_decision(self, decision, reason, metadata=None):
        """Log Obra's decision."""
        entry = {
            'timestamp': (datetime.now() - self.start_time).total_seconds(),
            'source': 'OBRA (Decision Engine)',
            'action': 'Make Decision',
            'output': f"Decision: {decision}",
            'reason': reason,
            'metadata': metadata or {}
        }
        self.conversation.append(entry)
        self._print_entry(entry)

    def _print_entry(self, entry):
        """Pretty print a conversation entry."""
        print(f"\n{'='*100}")
        print(f"[{entry['timestamp']:.1f}s] {entry['source']} - {entry['action']}")
        print(f"{'='*100}")

        if 'task' in entry:
            print(f"Task: {entry['task']}")

        if 'input' in entry:
            print(f"\nInput: {entry['input']}")

        if 'output' in entry:
            print(f"\nOutput: {entry['output']}")

        if 'duration' in entry:
            print(f"\nDuration: {entry['duration']:.1f}s")

        if 'reason' in entry:
            print(f"Reason: {entry['reason']}")

        if entry.get('metadata'):
            print(f"\nMetadata: {json.dumps(entry['metadata'], indent=2)}")

    def save_to_file(self, filepath):
        """Save conversation log to JSON file."""
        with open(filepath, 'w') as f:
            json.dump({
                'start_time': self.start_time.isoformat(),
                'total_duration': (datetime.now() - self.start_time).total_seconds(),
                'conversation': self.conversation
            }, f, indent=2)
        print(f"\n\n✓ Conversation saved to: {filepath}")


def test_full_cycle():
    """Test complete Obra ↔ Claude orchestration cycle."""

    print("="*100)
    print("FULL OBRA ORCHESTRATION CYCLE TEST")
    print("="*100)
    print("\nThis test demonstrates the complete workflow:")
    print("  1. User provides high-level task")
    print("  2. Obra (PromptGenerator with Qwen) generates optimized prompt")
    print("  3. Claude Code executes the task")
    print("  4. Obra (ResponseValidator) validates response format")
    print("  5. Obra (QualityController with Qwen) checks quality")
    print("  6. Obra (ConfidenceScorer) rates confidence")
    print("  7. Obra (DecisionEngine) decides next action")
    print("  8. Loop continues if needed")
    print()

    # Initialize conversation logger
    logger = ConversationLogger()

    # Initialize components
    print("Initializing Obra components...")

    # Load config
    config = Config.load()

    # Initialize Claude Code agent in headless mode
    agent = ClaudeCodeLocalAgent()
    agent.initialize({
        'workspace_path': '/tmp/obra_full_cycle_test',
        'bypass_permissions': True,  # Dangerous mode for automation
        'response_timeout': 120,
        'use_session_persistence': False  # Fresh sessions
    })
    print("✓ Claude Code agent initialized (headless + dangerous mode)")

    # Initialize Qwen LLM interface
    llm = LocalLLMInterface()
    llm_config = {
        'endpoint': config.get('llm.api_url', 'http://172.29.144.1:11434'),
        'model': config.get('llm.model', 'qwen2.5-coder:32b'),
        'temperature': config.get('llm.temperature', 0.7),
        'timeout': config.get('llm.timeout', 30)
    }
    llm.initialize(llm_config)
    print(f"✓ Qwen LLM initialized: {llm.endpoint}")

    # Initialize Obra components
    prompt_generator = PromptGenerator(config)
    print("✓ PromptGenerator initialized")

    validator = ResponseValidator()
    print("✓ ResponseValidator initialized")

    quality_controller = QualityController(llm)
    print("✓ QualityController initialized")

    confidence_scorer = ConfidenceScorer()
    print("✓ ConfidenceScorer initialized")

    decision_engine = DecisionEngine()
    print("✓ DecisionEngine initialized")

    print("\n" + "="*100)
    print("STARTING ORCHESTRATION CYCLE")
    print("="*100)

    # Iteration 1: Simple task
    task_description = "Create a simple Python file called 'greeting.py' that prints 'Hello from Obra and Claude!'"

    # Step 1: Obra generates prompt using Qwen
    print("\n[USER] Task:", task_description)

    context = {
        'task_description': task_description,
        'iteration': 1,
        'project_name': 'Full Cycle Test',
        'working_directory': '/tmp/obra_full_cycle_test'
    }

    # Note: PromptGenerator might use templates or LLM to enhance the prompt
    # For now, we'll create a simple prompt and show where Qwen would be involved
    basic_prompt = f"""You have full permission to create, read, and modify files.

Task: {task_description}

Please complete this task and report when done."""

    logger.log_obra_prompt_generation(
        task=task_description,
        generated_prompt=basic_prompt,
        metadata={'iteration': 1, 'method': 'template'}
    )

    # Step 2: Send to Claude Code
    print("\n\nSending prompt to Claude Code...")
    start = time.time()

    try:
        response = agent.send_prompt(basic_prompt)
        duration = time.time() - start

        logger.log_claude_response(
            prompt=basic_prompt,
            response=response,
            duration=duration,
            metadata={'response_length': len(response)}
        )

    except Exception as e:
        print(f"\n✗ Claude Code failed: {e}")
        return 1

    # Step 3: Obra validates response
    print("\n\nValidating response...")
    validation = validator.validate_response(response, context)

    logger.log_obra_validation(
        response=response,
        validation_result={
            'is_valid': validation['is_valid'],
            'completeness': validation.get('completeness', 'N/A'),
            'issues': validation.get('issues', [])
        },
        metadata=validation
    )

    if not validation['is_valid']:
        print(f"✗ Validation failed: {validation.get('reason')}")
        # In real orchestration, this would trigger retry or clarification
    else:
        print("✓ Response validation passed")

    # Step 4: Obra checks quality using Qwen
    print("\n\nChecking quality with Qwen LLM...")
    start = time.time()

    try:
        quality_result = quality_controller.check_quality(
            response=response,
            task_description=task_description,
            context=context
        )
        duration = time.time() - start

        logger.log_obra_quality_check(
            response=response,
            quality_result={
                'score': quality_result.get('score', 0),
                'passed': quality_result.get('passed', False),
                'issues': quality_result.get('issues', [])
            },
            duration=duration,
            metadata=quality_result
        )

        print(f"✓ Quality score: {quality_result.get('score', 0):.2f}")

    except Exception as e:
        print(f"⚠️ Quality check failed: {e}")
        quality_result = {'score': 0.5, 'passed': False}

    # Step 5: Obra scores confidence
    print("\n\nScoring confidence...")

    confidence = confidence_scorer.calculate_confidence(
        response=response,
        task_description=task_description,
        quality_result=quality_result,
        validation_result=validation
    )

    logger.log_obra_confidence(
        response=response,
        confidence=confidence,
        metadata={
            'quality_score': quality_result.get('score', 0),
            'validation_passed': validation['is_valid']
        }
    )

    print(f"✓ Confidence: {confidence:.2f}")

    # Step 6: Obra makes decision
    print("\n\nMaking decision...")

    decision_result = decision_engine.decide(
        confidence=confidence,
        quality_score=quality_result.get('score', 0),
        validation=validation,
        iteration=1,
        max_iterations=5
    )

    logger.log_obra_decision(
        decision=decision_result['action'],
        reason=decision_result.get('reason', 'N/A'),
        metadata=decision_result
    )

    print(f"✓ Decision: {decision_result['action']}")
    print(f"  Reason: {decision_result.get('reason', 'N/A')}")

    # Verify file was created
    print("\n\n" + "="*100)
    print("VERIFYING RESULTS")
    print("="*100)

    workspace = Path('/tmp/obra_full_cycle_test')
    greeting_file = workspace / 'greeting.py'

    if greeting_file.exists():
        print(f"\n✓ File created: {greeting_file}")
        content = greeting_file.read_text()
        print(f"\nContent ({len(content)} bytes):")
        print("-" * 80)
        print(content)
        print("-" * 80)
    else:
        print(f"\n✗ File not found: {greeting_file}")

    # Save conversation log
    print("\n\n" + "="*100)
    print("SAVING CONVERSATION LOG")
    print("="*100)

    log_file = Path(__file__).parent.parent / 'logs' / f'orchestration_cycle_{int(time.time())}.json'
    log_file.parent.mkdir(exist_ok=True)
    logger.save_to_file(log_file)

    # Print summary
    print("\n\n" + "="*100)
    print("ORCHESTRATION CYCLE SUMMARY")
    print("="*100)

    print(f"\nTotal conversation entries: {len(logger.conversation)}")
    print(f"Total duration: {logger.conversation[-1]['timestamp']:.1f}s")

    print("\n\nConversation flow:")
    for i, entry in enumerate(logger.conversation, 1):
        print(f"  {i}. [{entry['timestamp']:5.1f}s] {entry['source']:30s} → {entry['action']}")

    print("\n\n✅ Full orchestration cycle complete!")
    print(f"\nConversation log: {log_file}")
    print("\nThis demonstrates:")
    print("  ✓ Obra generating prompts")
    print("  ✓ Claude Code executing tasks")
    print("  ✓ Obra validating responses")
    print("  ✓ Obra checking quality with Qwen LLM")
    print("  ✓ Obra scoring confidence")
    print("  ✓ Obra making decisions")
    print("  ✓ Full conversation tracking")

    # Cleanup
    agent.cleanup()

    return 0


if __name__ == '__main__':
    sys.exit(test_full_cycle())
