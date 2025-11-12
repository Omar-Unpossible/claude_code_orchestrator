#!/usr/bin/env python3
"""
Manual Testing Issue Log Analyzer

This script analyzes the MANUAL_TESTING_LOG.yaml file and generates statistics,
pattern detection, and insights for quality improvement.

Usage:
    python analyze_issues.py                    # Basic analysis
    python analyze_issues.py --export csv       # Export to CSV
    python analyze_issues.py --export json      # Export to JSON
    python analyze_issues.py --chart            # Generate trend charts (requires matplotlib)
    python analyze_issues.py --patterns         # Deep pattern analysis
"""

import yaml
import argparse
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Any
import json


class IssueLogAnalyzer:
    """Analyzes the manual testing issue log for patterns and insights."""

    def __init__(self, log_path: str):
        """Initialize the analyzer with the log file path.

        Args:
            log_path: Path to MANUAL_TESTING_LOG.yaml
        """
        self.log_path = Path(log_path)
        self.data = self._load_log()
        self.issues = self.data.get('issues', [])

    def _load_log(self) -> Dict[str, Any]:
        """Load and parse the YAML log file.

        Returns:
            Parsed log data as dictionary

        Raises:
            FileNotFoundError: If log file doesn't exist
            yaml.YAMLError: If log file is invalid YAML
        """
        if not self.log_path.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_path}")

        with open(self.log_path, 'r') as f:
            return yaml.safe_load(f)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics for the log.

        Returns:
            Dictionary with total, open, closed, and by-status counts
        """
        total = len(self.issues)
        open_issues = sum(1 for i in self.issues if i['status'] in ['OPEN', 'IN_PROGRESS'])
        closed_issues = sum(1 for i in self.issues if i['status'] in ['RESOLVED', 'CLOSED'])

        status_counts = Counter(i['status'] for i in self.issues)

        return {
            'total': total,
            'open': open_issues,
            'closed': closed_issues,
            'by_status': dict(status_counts)
        }

    def get_category_breakdown(self) -> Dict[str, int]:
        """Get count of issues by category.

        Returns:
            Dictionary mapping category to count, sorted by count descending
        """
        categories = Counter(i['category'] for i in self.issues)
        return dict(sorted(categories.items(), key=lambda x: -x[1]))

    def get_severity_breakdown(self) -> Dict[str, int]:
        """Get count of issues by severity.

        Returns:
            Dictionary mapping severity to count, ordered by severity
        """
        severities = Counter(i['severity'] for i in self.issues)
        # Order by severity (CRITICAL > HIGH > MEDIUM > LOW)
        severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        return {sev: severities.get(sev, 0) for sev in severity_order}

    def get_type_breakdown(self) -> Dict[str, int]:
        """Get count of issues by type.

        Returns:
            Dictionary mapping type to count, sorted by count descending
        """
        types = Counter(i['type'] for i in self.issues)
        return dict(sorted(types.items(), key=lambda x: -x[1]))

    def get_resolution_time_stats(self) -> Dict[str, Any]:
        """Calculate resolution time statistics for closed issues.

        Returns:
            Dictionary with average, min, max resolution times in days
        """
        resolution_times = []

        for issue in self.issues:
            if issue['status'] not in ['RESOLVED', 'CLOSED']:
                continue

            try:
                # Parse timestamp (may have timezone info)
                timestamp_str = issue['timestamp'].replace('Z', '+00:00')
                timestamp = datetime.fromisoformat(timestamp_str)

                resolution = issue.get('resolution', {})
                verified_date_str = resolution.get('verified_date')

                if verified_date_str:
                    # Make verified_date timezone-aware to match timestamp
                    verified_date = datetime.fromisoformat(verified_date_str + 'T00:00:00+00:00')
                    delta = (verified_date - timestamp).days
                    resolution_times.append(delta)
            except (ValueError, KeyError, TypeError):
                continue

        if not resolution_times:
            return {'average': None, 'min': None, 'max': None, 'count': 0}

        return {
            'average': sum(resolution_times) / len(resolution_times),
            'min': min(resolution_times),
            'max': max(resolution_times),
            'count': len(resolution_times)
        }

    def detect_patterns(self) -> Dict[str, Any]:
        """Detect recurring patterns in the issues.

        Returns:
            Dictionary with detected patterns, recurring themes, hot components
        """
        # Analyze tags for recurring themes
        tag_counter = Counter()
        for issue in self.issues:
            tags = issue.get('tags', [])
            tag_counter.update(tags)

        # Find most common tags (potential themes)
        recurring_tags = tag_counter.most_common(10)

        # Analyze affected components
        component_counter = Counter()
        for issue in self.issues:
            components = issue.get('affected_components', [])
            component_counter.update(components)

        hot_components = component_counter.most_common(10)

        # Find issues that reference other issues (potential clusters)
        issue_clusters = defaultdict(list)
        for issue in self.issues:
            related = issue.get('related_links', {}).get('issues', [])
            if related:
                issue_id = issue['id']
                for related_id in related:
                    issue_clusters[related_id].append(issue_id)

        return {
            'recurring_tags': [{'tag': tag, 'count': count} for tag, count in recurring_tags],
            'hot_components': [{'component': comp, 'count': count} for comp, count in hot_components],
            'issue_clusters': dict(issue_clusters)
        }

    def get_open_critical_issues(self) -> List[Dict[str, Any]]:
        """Get list of open critical/high severity issues.

        Returns:
            List of issue dictionaries with id, title, severity, category
        """
        critical_issues = [
            {
                'id': i['id'],
                'title': i['title'],
                'severity': i['severity'],
                'category': i['category'],
                'status': i['status']
            }
            for i in self.issues
            if i['severity'] in ['CRITICAL', 'HIGH'] and i['status'] in ['OPEN', 'IN_PROGRESS']
        ]
        return critical_issues

    def print_analysis(self) -> None:
        """Print comprehensive analysis to stdout."""
        print("=" * 80)
        print("MANUAL TESTING ISSUE LOG ANALYSIS")
        print("=" * 80)
        print()

        # Summary statistics
        summary = self.get_summary_stats()
        print("SUMMARY STATISTICS")
        print("-" * 80)
        print(f"Total Issues:        {summary['total']}")
        print(f"Open Issues:         {summary['open']}")
        print(f"Closed Issues:       {summary['closed']}")
        print()
        print("By Status:")
        for status, count in summary['by_status'].items():
            print(f"  {status:15s}: {count:3d}")
        print()

        # Category breakdown
        categories = self.get_category_breakdown()
        print("ISSUES BY CATEGORY")
        print("-" * 80)
        for category, count in categories.items():
            bar = "█" * (count * 2)
            print(f"{category:30s}: {count:3d} {bar}")
        print()

        # Severity breakdown
        severities = self.get_severity_breakdown()
        print("ISSUES BY SEVERITY")
        print("-" * 80)
        for severity, count in severities.items():
            bar = "█" * (count * 3)
            print(f"{severity:15s}: {count:3d} {bar}")
        print()

        # Type breakdown
        types = self.get_type_breakdown()
        print("ISSUES BY TYPE")
        print("-" * 80)
        for issue_type, count in types.items():
            bar = "█" * (count * 2)
            print(f"{issue_type:20s}: {count:3d} {bar}")
        print()

        # Resolution time
        resolution_stats = self.get_resolution_time_stats()
        print("RESOLUTION TIME STATISTICS")
        print("-" * 80)
        if resolution_stats['count'] > 0:
            print(f"Average Resolution Time: {resolution_stats['average']:.1f} days")
            print(f"Fastest Resolution:      {resolution_stats['min']} days")
            print(f"Slowest Resolution:      {resolution_stats['max']} days")
            print(f"Resolved Issues:         {resolution_stats['count']}")
        else:
            print("No resolved issues with verification dates yet.")
        print()

        # Critical/high issues
        critical = self.get_open_critical_issues()
        if critical:
            print("OPEN CRITICAL/HIGH SEVERITY ISSUES")
            print("-" * 80)
            for issue in critical:
                print(f"⚠️  [{issue['severity']}] {issue['id']}: {issue['title']}")
                print(f"    Category: {issue['category']}, Status: {issue['status']}")
            print()
        else:
            print("✅ No open critical or high severity issues!")
            print()

        # Pattern detection
        patterns = self.detect_patterns()
        if patterns['recurring_tags']:
            print("RECURRING THEMES (Top Tags)")
            print("-" * 80)
            for tag_info in patterns['recurring_tags'][:5]:
                print(f"  {tag_info['tag']:30s}: {tag_info['count']:3d} occurrences")
            print()

        if patterns['hot_components']:
            print("HOT COMPONENTS (Most Issues)")
            print("-" * 80)
            for comp_info in patterns['hot_components'][:5]:
                print(f"  {comp_info['component']:50s}: {comp_info['count']:3d} issues")
            print()

        print("=" * 80)

    def export_csv(self, output_path: str) -> None:
        """Export issues to CSV format.

        Args:
            output_path: Path to output CSV file
        """
        import csv

        with open(output_path, 'w', newline='') as f:
            if not self.issues:
                return

            # Define fields to export
            fields = ['id', 'title', 'category', 'severity', 'type', 'status',
                     'timestamp', 'version', 'reporter']

            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            for issue in self.issues:
                row = {field: issue.get(field, '') for field in fields}
                writer.writerow(row)

        print(f"Exported {len(self.issues)} issues to {output_path}")

    def export_json(self, output_path: str) -> None:
        """Export analysis to JSON format.

        Args:
            output_path: Path to output JSON file
        """
        analysis = {
            'generated_at': datetime.now().isoformat(),
            'summary': self.get_summary_stats(),
            'category_breakdown': self.get_category_breakdown(),
            'severity_breakdown': self.get_severity_breakdown(),
            'type_breakdown': self.get_type_breakdown(),
            'resolution_stats': self.get_resolution_time_stats(),
            'patterns': self.detect_patterns(),
            'open_critical': self.get_open_critical_issues()
        }

        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)

        print(f"Exported analysis to {output_path}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Analyze Manual Testing Issue Log',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--log',
        default='docs/quality/MANUAL_TESTING_LOG.yaml',
        help='Path to log file (default: docs/quality/MANUAL_TESTING_LOG.yaml)'
    )

    parser.add_argument(
        '--export',
        choices=['csv', 'json'],
        help='Export format (csv or json)'
    )

    parser.add_argument(
        '--output',
        help='Output file path for export (default: auto-generated)'
    )

    parser.add_argument(
        '--patterns',
        action='store_true',
        help='Run deep pattern analysis'
    )

    parser.add_argument(
        '--chart',
        action='store_true',
        help='Generate trend charts (requires matplotlib)'
    )

    args = parser.parse_args()

    try:
        analyzer = IssueLogAnalyzer(args.log)

        # Always print basic analysis
        analyzer.print_analysis()

        # Pattern analysis
        if args.patterns:
            print("\n" + "=" * 80)
            print("DEEP PATTERN ANALYSIS")
            print("=" * 80)
            patterns = analyzer.detect_patterns()
            print(json.dumps(patterns, indent=2))

        # Export
        if args.export:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if not args.output:
                args.output = f"issue_analysis_{timestamp}.{args.export}"

            if args.export == 'csv':
                analyzer.export_csv(args.output)
            elif args.export == 'json':
                analyzer.export_json(args.output)

        # Chart generation
        if args.chart:
            try:
                import matplotlib.pyplot as plt
                print("\n📊 Chart generation not yet implemented. Coming soon!")
            except ImportError:
                print("\n⚠️  Chart generation requires matplotlib: pip install matplotlib")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in log file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
