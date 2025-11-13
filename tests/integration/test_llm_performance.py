"""LLM performance baseline tests.

Run on: Nightly, before release
Speed: 10-15 minutes
Purpose: Establish performance baselines and detect regressions
"""

import pytest
import time
import statistics
from typing import List
from src.nl.intent_classifier import IntentClassifier
from src.nl.entity_extractor import EntityExtractor


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_ollama
class TestLLMPerformance:
    """Establish performance baselines for LLM operations."""

    @pytest.fixture(scope='class')
    def real_intent_classifier(self):
        """Real intent classifier with Ollama."""
        from src.llm.local_interface import LocalLLMInterface

        llm = LocalLLMInterface()
        llm.initialize({
            'model': 'qwen2.5-coder:32b',
            'endpoint': 'http://10.0.75.1:11434',
            'timeout': 30.0,
            'temperature': 0.1
        })

        classifier = IntentClassifier(
            llm_plugin=llm,
            confidence_threshold=0.7
        )
        return classifier

    @pytest.fixture(scope='class')
    def real_entity_extractor(self):
        """Real entity extractor with Ollama."""
        from src.llm.local_interface import LocalLLMInterface

        llm = LocalLLMInterface()
        llm.initialize({
            'model': 'qwen2.5-coder:32b',
            'endpoint': 'http://10.0.75.1:11434',
            'timeout': 30.0,
            'temperature': 0.1
        })

        extractor = EntityExtractor(llm_plugin=llm)
        return extractor

    def test_intent_classification_latency_ollama(self, real_intent_classifier):
        """Baseline: Intent classification latency with Ollama."""
        test_prompts = [
            "create epic for user authentication",
            "show all projects",
            "update task 5 status to completed",
            "delete project 3",
            "list tasks",
            "what is the status of epic 2",
            "create story in epic 5",
            "show milestone progress",
            "create task with high priority",
            "mark story 3 as blocked"
        ]

        latencies = []
        for prompt in test_prompts:
            start = time.time()
            result = real_intent_classifier.classify(prompt)
            duration = (time.time() - start) * 1000  # ms
            latencies.append(duration)

            assert result.confidence >= 0.7

        # Calculate percentiles
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]
        p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else latencies[0]

        print(f"\nIntent Classification Latency (Ollama):")
        print(f"  p50: {p50:.0f}ms")
        print(f"  p95: {p95:.0f}ms")
        print(f"  p99: {p99:.0f}ms")

        # Baseline assertions (adjust based on hardware and network conditions)
        # Allow for some variance - most important is detecting dramatic regressions
        assert p95 < 20000, f"p95 latency too high: {p95}ms (dramatic regression detected)"
        assert p99 < 30000, f"p99 latency too high: {p99}ms (dramatic regression detected)"

    def test_entity_extraction_accuracy_ollama(self, real_entity_extractor):
        """Baseline: Entity extraction accuracy with Ollama."""
        test_cases = [
            ("create epic for user authentication", "epic"),
            ("create story in epic 5", "story"),
            ("create task with high priority", "task"),
            ("create project for mobile app", "project"),
            ("create milestone for MVP release", "milestone"),
        ]

        correct = 0
        for prompt, expected_entity in test_cases:
            result = real_entity_extractor.extract(prompt, intent="COMMAND")
            if result.entity_type == expected_entity:
                correct += 1

        accuracy = correct / len(test_cases)
        print(f"\nEntity Extraction Accuracy (Ollama): {accuracy*100:.1f}%")

        # Should achieve at least 80% accuracy
        assert accuracy >= 0.8, f"Accuracy too low: {accuracy*100:.1f}%"

    def test_full_pipeline_latency_ollama(self, real_intent_classifier, real_entity_extractor):
        """Baseline: Full NL pipeline latency with Ollama."""
        test_prompts = [
            "create epic for user authentication",
            "create story in epic 5",
            "create task with high priority",
            "list all tasks",
            "show project status"
        ]

        latencies = []
        for prompt in test_prompts:
            start = time.time()

            # Step 1: Intent classification
            intent_result = real_intent_classifier.classify(prompt)

            # Step 2: Entity extraction (if COMMAND)
            if intent_result.intent == "COMMAND":
                entity_result = real_entity_extractor.extract(prompt, intent="COMMAND")

            duration = (time.time() - start) * 1000  # ms
            latencies.append(duration)

        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]
        print(f"\nFull Pipeline Latency p95 (Ollama): {p95:.0f}ms")

        # Should complete reasonably fast (allow variance for network/hardware)
        assert p95 < 30000, f"Pipeline too slow: {p95}ms (dramatic regression detected)"
