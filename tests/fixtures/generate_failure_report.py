"""Failure analysis and report generation for NL variation tests.

Analyzes test results from variation stress tests and generates
comprehensive reports with categorized failures and actionable recommendations.

Usage:
    python tests/fixtures/generate_failure_report.py --test-log tests/test_run.log
"""

import argparse
import json
import re
import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class FailureAnalyzer:
    """Analyze test failures and categorize by root cause."""

    # Failure patterns and categories
    FAILURE_PATTERNS = {
        'low_confidence': {
            'pattern': r'Low confidence: (\d+\.\d+)',
            'category': 'Low Confidence',
            'recommendation': 'Improve confidence scoring or lower threshold'
        },
        'wrong_operation': {
            'pattern': r'Wrong operation: (\w+)',
            'category': 'Wrong Operation Type',
            'recommendation': 'Add patterns for operation classification'
        },
        'missing_entity': {
            'pattern': r'Missing (\w+) entity type',
            'category': 'Missing Entity Type',
            'recommendation': 'Improve entity type extraction'
        },
        'wrong_identifier': {
            'pattern': r'Wrong identifier: (\w+)',
            'category': 'Identifier Extraction Failure',
            'recommendation': 'Improve identifier parsing'
        },
        'typo_failure': {
            'pattern': r'typo',
            'category': 'Typo Tolerance',
            'recommendation': 'Add fuzzy matching or spelling correction'
        }
    }

    def __init__(self):
        """Initialize failure analyzer."""
        self.failures = []
        self.categories = defaultdict(list)

    def add_failure(self, test_name: str, variation: str, error: str):
        """Add a failure to the analysis.

        Args:
            test_name: Name of the test that failed
            variation: The variation that caused the failure
            error: Error message
        """
        self.failures.append({
            'test_name': test_name,
            'variation': variation,
            'error': error
        })

        # Categorize failure
        category = self._categorize_failure(error)
        self.categories[category].append({
            'test_name': test_name,
            'variation': variation,
            'error': error
        })

    def _categorize_failure(self, error: str) -> str:
        """Categorize failure based on error message.

        Args:
            error: Error message

        Returns:
            Category name
        """
        for pattern_name, pattern_info in self.FAILURE_PATTERNS.items():
            if re.search(pattern_info['pattern'], error, re.IGNORECASE):
                return pattern_info['category']

        # Unknown category
        return 'Unknown'

    def generate_report(self) -> str:
        """Generate comprehensive failure report.

        Returns:
            Markdown formatted report
        """
        total_failures = len(self.failures)

        if total_failures == 0:
            return "# NL Variation Failure Report\n\n✅ **All tests passed!** No failures to report.\n"

        report = []
        report.append("# NL Variation Failure Report\n")
        report.append(f"**Generated**: {self._get_timestamp()}\n")
        report.append("## Summary\n")
        report.append(f"- **Total failures**: {total_failures}")
        report.append(f"- **Unique categories**: {len(self.categories)}\n")

        # Category breakdown
        report.append("## Failure Categories\n")
        sorted_categories = sorted(
            self.categories.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        for category, failures in sorted_categories:
            percentage = (len(failures) / total_failures) * 100
            report.append(f"### {category} ({len(failures)} failures, {percentage:.1f}%)\n")

            # Get recommendation
            recommendation = self._get_recommendation(category)
            if recommendation:
                report.append(f"**Recommendation**: {recommendation}\n")

            # Show first 5 examples
            report.append("**Examples**:\n")
            for i, failure in enumerate(failures[:5], 1):
                report.append(f"{i}. Test: `{failure['test_name']}`")
                report.append(f"   - Variation: \"{failure['variation']}\"")
                report.append(f"   - Error: {failure['error']}\n")

            if len(failures) > 5:
                report.append(f"   _(... and {len(failures) - 5} more)_\n")

        # Recommendations section
        report.append("## Prioritized Recommendations\n")
        sorted_categories = sorted(
            self.categories.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        for i, (category, failures) in enumerate(sorted_categories[:5], 1):
            recommendation = self._get_recommendation(category)
            impact = len(failures)
            report.append(f"{i}. **{category}** ({impact} failures)")
            report.append(f"   - {recommendation}\n")

        return "\n".join(report)

    def _get_recommendation(self, category: str) -> str:
        """Get recommendation for a failure category.

        Args:
            category: Failure category name

        Returns:
            Recommendation string
        """
        for pattern_info in self.FAILURE_PATTERNS.values():
            if pattern_info['category'] == category:
                return pattern_info['recommendation']

        return 'Investigate error patterns and update parser logic'

    def _get_timestamp(self) -> str:
        """Get current timestamp for report.

        Returns:
            ISO formatted timestamp
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about failures.

        Returns:
            Dictionary with statistics
        """
        return {
            'total_failures': len(self.failures),
            'categories': {
                category: len(failures)
                for category, failures in self.categories.items()
            },
            'most_common_category': max(
                self.categories.items(),
                key=lambda x: len(x[1])
            )[0] if self.categories else None
        }


def parse_test_log(log_file: Path) -> FailureAnalyzer:
    """Parse pytest test log and extract failures.

    Args:
        log_file: Path to test log file

    Returns:
        FailureAnalyzer with parsed failures
    """
    analyzer = FailureAnalyzer()

    if not log_file.exists():
        logger.error(f"Log file not found: {log_file}")
        return analyzer

    logger.info(f"Parsing test log: {log_file}")

    current_test = None
    current_variation = None

    with open(log_file, 'r') as f:
        for line in f:
            # Match test name
            test_match = re.search(r'test_(\w+)_variations', line)
            if test_match:
                current_test = test_match.group(0)

            # Match variation failure
            variation_match = re.search(r'Variation \d+ failed: (.+?) - (.+)', line)
            if variation_match and current_test:
                variation = variation_match.group(1)
                error = variation_match.group(2)
                analyzer.add_failure(current_test, variation, error)

    logger.info(f"Parsed {len(analyzer.failures)} failures")
    return analyzer


def main():
    """Main entry point for report generation."""
    parser = argparse.ArgumentParser(
        description='Generate failure analysis report for NL variation tests'
    )
    parser.add_argument(
        '--test-log',
        type=Path,
        default=Path('tests/test_run.log'),
        help='Path to pytest test log file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('tests/reports/nl_variation_failures.md'),
        help='Output path for failure report'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Also output JSON format'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    # Parse test log
    analyzer = parse_test_log(args.test_log)

    # Generate report
    report = analyzer.generate_report()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Write report
    with open(args.output, 'w') as f:
        f.write(report)

    logger.info(f"Report written to: {args.output}")

    # Optionally write JSON
    if args.json:
        json_output = args.output.with_suffix('.json')
        stats = analyzer.get_stats()
        with open(json_output, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"JSON stats written to: {json_output}")

    # Print summary
    stats = analyzer.get_stats()
    print(f"\nSummary:")
    print(f"  Total failures: {stats['total_failures']}")
    print(f"  Categories: {len(stats['categories'])}")
    if stats['most_common_category']:
        print(f"  Most common: {stats['most_common_category']}")


if __name__ == '__main__':
    main()
