"""Test coverage audit and gap analysis."""

from typing import List, Dict, Any, Set
from dataclasses import asdict

from pydbtguard.models.schemas import CoverageGap


class CoverageAuditor:
    """Audits dbt test coverage and identifies gaps."""

    def __init__(self, manifest: Dict[str, Any]):
        """
        Initialize coverage auditor.

        Args:
            manifest: dbt manifest
        """
        self.manifest = manifest
        self.nodes = manifest.get("nodes", {})
        self.tests = manifest.get("nodes", {})

    def audit_coverage(self) -> List[CoverageGap]:
        """
        Audit test coverage across all models.

        Returns:
            List of coverage gaps, sorted by priority
        """
        gaps = []

        for node_id, node in self.nodes.items():
            if node.get("resource_type") == "model":
                gap = self._analyze_model_coverage(node_id, node)
                if gap and gap.missing_test_types:
                    gaps.append(gap)

        # Sort by priority
        gaps.sort(key=lambda g: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(g.priority, 4))

        return gaps

    def _analyze_model_coverage(self, model_id: str, model_node: Dict[str, Any]) -> CoverageGap:
        """Analyze test coverage for a single model."""
        model_name = model_node.get("name", model_id)

        # Find tests attached to this model
        attached_tests = self._find_attached_tests(model_id)
        test_types = {test.get("attached_node_test_type", "other") for test in attached_tests}

        # Determine missing test types
        all_test_types = {"unique", "not_null", "relationships", "freshness"}
        missing_types = list(all_test_types - test_types)

        # Calculate risk score
        risk_score = self._calculate_model_risk_score(model_node)

        # Get model metadata
        config = model_node.get("config", {})
        freshness_sla = config.get("freshness", {}).get("warn_after", {}).get("count")
        bi_dependencies = self._count_downstream_exposures(model_id)

        # Recommend test types
        recommended_tests = self._recommend_tests(model_node, missing_types)

        # Determine priority
        priority = self._determine_priority(risk_score, missing_types, bi_dependencies)

        return CoverageGap(
            model_name=model_name,
            model_id=model_id,
            risk_score=risk_score,
            freshness_sla_hours=freshness_sla,
            bi_dependencies=bi_dependencies,
            row_count=0,  # Would come from warehouse metadata
            missing_test_types=missing_types,
            recommended_tests=recommended_tests,
            priority=priority,
        )

    def _find_attached_tests(self, model_id: str) -> List[Dict[str, Any]]:
        """Find all tests attached to a model."""
        tests = []

        for node_id, node in self.nodes.items():
            if node.get("resource_type") == "test":
                if node.get("attached_node") == model_id:
                    test_type = self._infer_test_type(node)
                    test_copy = node.copy()
                    test_copy["attached_node_test_type"] = test_type
                    tests.append(test_copy)

        return tests

    def _infer_test_type(self, test_node: Dict[str, Any]) -> str:
        """Infer test type from test definition."""
        test_name = test_node.get("name", "").lower()
        sql = test_node.get("raw_sql", "").lower()

        if "unique" in test_name or "unique" in sql:
            return "unique"
        elif "not_null" in test_name or "not null" in sql or "is not null" in sql:
            return "not_null"
        elif "relationships" in test_name or "foreign key" in sql:
            return "relationships"
        elif "freshness" in test_name or "max(" in sql:
            return "freshness"
        else:
            return "custom"

    def _calculate_model_risk_score(self, model_node: Dict[str, Any]) -> float:
        """Calculate risk score for a model (0-100)."""
        score = 50.0  # Base score

        # Increase risk for models with:
        # - Tighter freshness SLA
        freshness = model_node.get("config", {}).get("freshness", {}).get("warn_after", {})
        if freshness:
            hours = freshness.get("count", 24)
            score += (24 - hours) / 24 * 25

        # - Complex transformations
        materialization = model_node.get("config", {}).get("materialized", "table")
        if materialization == "incremental":
            score += 10

        # - High column count (more surface area for quality issues)
        columns = model_node.get("columns", {})
        if len(columns) > 50:
            score += 10

        return min(score, 100.0)

    def _count_downstream_exposures(self, model_id: str) -> int:
        """Count how many BI exposures depend on this model."""
        exposures = self.manifest.get("exposures", {})
        count = 0

        for exposure in exposures.values():
            deps = exposure.get("depends_on", {}).get("nodes", [])
            if model_id in deps or self._is_transitive_dependency(model_id, deps):
                count += 1

        return count

    def _is_transitive_dependency(self, source: str, targets: List[str]) -> bool:
        """Check if source is a transitive dependency."""
        visited = set()

        def check(node_id: str) -> bool:
            if node_id in visited:
                return False
            visited.add(node_id)

            if node_id == source:
                return True

            if node_id in self.nodes:
                deps = self.nodes[node_id].get("depends_on", {}).get("nodes", [])
                for dep in deps:
                    if check(dep):
                        return True

            return False

        for target in targets:
            if check(target):
                return True

        return False

    def _recommend_tests(
        self,
        model_node: Dict[str, Any],
        missing_types: List[str],
    ) -> List[str]:
        """Recommend specific tests to add."""
        recommendations = []

        if "unique" in missing_types:
            recommendations.append("Add unique test on primary key column")

        if "not_null" in missing_types:
            recommendations.append("Add not_null tests on required columns")

        if "relationships" in missing_types and model_node.get("config", {}).get("materialized") != "source":
            recommendations.append("Add relationship tests for foreign keys")

        if "freshness" in missing_types:
            recommendations.append("Add freshness test on updated_at column")

        return recommendations

    def _determine_priority(
        self,
        risk_score: float,
        missing_types: List[str],
        bi_dependencies: int,
    ) -> str:
        """Determine priority for covering gaps."""
        if risk_score > 75 or (bi_dependencies > 2 and len(missing_types) > 1):
            return "CRITICAL"
        elif risk_score > 60 or (bi_dependencies > 0 and len(missing_types) > 0):
            return "HIGH"
        elif risk_score > 40 or len(missing_types) > 1:
            return "MEDIUM"
        else:
            return "LOW"
