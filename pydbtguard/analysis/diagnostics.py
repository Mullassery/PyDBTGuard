"""Diagnostic and root cause analysis for test failures."""

from typing import List, Dict, Any, Tuple
from dataclasses import asdict
from collections import defaultdict

from pydbtguard.models.schemas import DiagnosticPlan


class DiagnosticsAnalyzer:
    """Performs diagnostic analysis on test failures."""

    def __init__(self, manifest: Dict[str, Any]):
        """
        Initialize diagnostics analyzer.

        Args:
            manifest: dbt manifest
        """
        self.manifest = manifest
        self.nodes = manifest.get("nodes", {})

    def diagnose_failure(
        self,
        failing_test_name: str,
        historical_failures: List[Dict[str, Any]],
    ) -> DiagnosticPlan:
        """
        Generate diagnostic plan for a failing test.

        Args:
            failing_test_name: Name of the failing test
            historical_failures: Historical failure data

        Returns:
            DiagnosticPlan with likely causes, diagnostic tests, etc.
        """
        # Find likely causes
        likely_causes = self._identify_likely_causes(failing_test_name, historical_failures)

        # Find correlated tests
        correlation_scores = self._find_correlated_tests(failing_test_name, historical_failures)

        # Find pattern matches
        pattern_matches = self._find_pattern_matches(failing_test_name, historical_failures)

        # Suggest diagnostic tests
        diagnostic_tests = self._suggest_diagnostic_tests(failing_test_name, likely_causes)

        return DiagnosticPlan(
            test_name=failing_test_name,
            likely_causes=likely_causes,
            diagnostic_tests=diagnostic_tests,
            correlation_scores=correlation_scores,
            pattern_matches=pattern_matches,
        )

    def _identify_likely_causes(
        self,
        test_name: str,
        historical_failures: List[Dict[str, Any]],
    ) -> List[str]:
        """Identify likely causes of failures."""
        causes = []

        # Analyze failure frequency patterns
        if historical_failures:
            recent_failures = [f for f in historical_failures if f.get("recent", False)]
            if len(recent_failures) > 0:
                causes.append("Recent data quality issue")

        # Check for common patterns
        if "unique_id" in self._get_test_config(test_name):
            causes.append("Duplicate row detection failure")

        if "freshness" in self._get_test_config(test_name):
            causes.append("Data freshness SLA breach")

        if "relationships" in test_name.lower():
            causes.append("Foreign key constraint violation")

        if "not_null" in test_name.lower():
            causes.append("Unexpected NULL values introduced")

        return causes or ["Unknown data quality issue"]

    def _get_test_config(self, test_name: str) -> Dict[str, Any]:
        """Get test configuration from manifest."""
        for node_id, node in self.nodes.items():
            if node.get("name") == test_name:
                return node.get("config", {})
        return {}

    def _find_correlated_tests(
        self,
        test_name: str,
        historical_failures: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Find tests that fail together (correlation)."""
        correlations = {}

        # Simplified: tests on same model have high correlation
        test_model = self._get_attached_node(test_name)

        for node_id, node in self.nodes.items():
            if node.get("resource_type") == "test":
                other_model = node.get("attached_node")
                if other_model == test_model and node.get("name") != test_name:
                    # Estimate correlation (simplified)
                    correlation = 0.7 if other_model else 0.3
                    correlations[node.get("name", node_id)] = correlation

        return correlations

    def _get_attached_node(self, test_name: str) -> str:
        """Get the model/column this test is attached to."""
        for node in self.nodes.values():
            if node.get("name") == test_name:
                return node.get("attached_node", "")
        return ""

    def _find_pattern_matches(
        self,
        test_name: str,
        historical_failures: List[Dict[str, Any]],
    ) -> List[str]:
        """Find historical failure patterns that match."""
        patterns = []

        if not historical_failures:
            return patterns

        # Check for recurring patterns
        failure_dates = [f.get("timestamp", "") for f in historical_failures]

        # Check if failures are on specific days (e.g., month-end)
        month_end_failures = sum(
            1 for date in failure_dates if date.endswith("-28") or date.endswith("-29") or date.endswith("-30")
        )
        if month_end_failures > len(failure_dates) / 2:
            patterns.append("Month-end volume surge pattern")

        # Check for cycle patterns
        if len(failure_dates) > 2:
            patterns.append("Periodic failure pattern detected")

        return patterns

    def _suggest_diagnostic_tests(
        self,
        test_name: str,
        likely_causes: List[str],
    ) -> List[str]:
        """Suggest specific diagnostic tests to run."""
        diagnostics = []

        # Always suggest checking row count
        diagnostics.append("SELECT COUNT(*) FROM <table>")

        # Based on likely causes
        for cause in likely_causes:
            if "duplicate" in cause.lower():
                diagnostics.append("SELECT COUNT(*), COUNT(DISTINCT <key>) FROM <table>")
                diagnostics.append("SELECT <key>, COUNT(*) FROM <table> GROUP BY <key> HAVING COUNT(*) > 1")

            if "freshness" in cause.lower():
                diagnostics.append("SELECT MAX(updated_at) FROM <table>")
                diagnostics.append("SELECT COUNT(*) FROM <table> WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL 1 HOUR")

            if "null" in cause.lower():
                diagnostics.append("SELECT COUNT(*), COUNT(<column>), COUNT(CASE WHEN <column> IS NULL THEN 1 END) FROM <table>")

            if "foreign key" in cause.lower():
                diagnostics.append("SELECT * FROM <table> WHERE <fk> NOT IN (SELECT pk FROM <ref_table>)")

        return diagnostics
