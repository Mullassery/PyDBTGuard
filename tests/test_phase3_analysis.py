"""Tests for Phase 3 (v0.3) analysis modules."""

import pytest

from pydbtguard.analysis.diagnostics import DiagnosticsAnalyzer
from pydbtguard.analysis.optimization import TestOptimizer
from pydbtguard.analysis.coverage import CoverageAuditor
from pydbtguard.models.schemas import DiagnosticPlan, OptimizationSuggestion, CoverageGap


@pytest.fixture
def sample_manifest():
    """Provide a sample dbt manifest for testing."""
    return {
        "nodes": {
            "model.test.users": {
                "unique_id": "model.test.users",
                "name": "users",
                "resource_type": "model",
                "config": {
                    "materialized": "table",
                    "freshness": {"warn_after": {"count": 6}},
                },
                "depends_on": {"nodes": ["source.test.raw_users"]},
                "columns": {id: {}, email: {}, created_at: {}},
            },
            "model.test.orders": {
                "unique_id": "model.test.orders",
                "name": "orders",
                "resource_type": "model",
                "config": {"materialized": "incremental"},
                "depends_on": {"nodes": ["model.test.users"]},
                "columns": {},
            },
            "test.test.unique_users_id": {
                "unique_id": "test.test.unique_users_id",
                "name": "unique_users_id",
                "resource_type": "test",
                "attached_node": "model.test.users",
                "raw_sql": "SELECT id, COUNT(*) FROM users GROUP BY id HAVING COUNT(*) > 1",
            },
            "test.test.not_null_users_email": {
                "unique_id": "test.test.not_null_users_email",
                "name": "not_null_users_email",
                "resource_type": "test",
                "attached_node": "model.test.users",
                "raw_sql": "SELECT * FROM users WHERE email IS NULL",
            },
        },
        "exposures": {
            "dashboard.main": {
                "unique_id": "dashboard.main",
                "depends_on": {"nodes": ["model.test.orders"]},
            }
        },
    }


class TestDiagnosticsAnalyzer:
    """Test suite for DiagnosticsAnalyzer."""

    def test_diagnose_failure(self, sample_manifest):
        """Test generating diagnostic plan for a failing test."""
        analyzer = DiagnosticsAnalyzer(sample_manifest)

        plan = analyzer.diagnose_failure(
            failing_test_name="unique_users_id",
            historical_failures=[{"timestamp": "2024-01-01", "recent": True}],
        )

        assert isinstance(plan, DiagnosticPlan)
        assert plan.test_name == "unique_users_id"
        assert len(plan.likely_causes) > 0
        assert len(plan.diagnostic_tests) > 0
        assert isinstance(plan.correlation_scores, dict)

    def test_identify_likely_causes(self, sample_manifest):
        """Test identifying likely causes of failures."""
        analyzer = DiagnosticsAnalyzer(sample_manifest)

        causes = analyzer._identify_likely_causes("unique_users_id", [])

        assert isinstance(causes, list)
        assert len(causes) > 0
        assert any("duplicate" in cause.lower() for cause in causes)

    def test_suggest_diagnostic_tests(self, sample_manifest):
        """Test suggesting diagnostic test queries."""
        analyzer = DiagnosticsAnalyzer(sample_manifest)

        diagnostics = analyzer._suggest_diagnostic_tests(
            "unique_users_id",
            ["Duplicate row detection failure"],
        )

        assert isinstance(diagnostics, list)
        assert len(diagnostics) > 0
        assert any("COUNT" in d for d in diagnostics)


class TestTestOptimizer:
    """Test suite for TestOptimizer."""

    def test_suggest_optimizations(self, sample_manifest):
        """Test suggesting test optimizations."""
        optimizer = TestOptimizer(sample_manifest)

        suggestions = optimizer.suggest_optimizations(
            test_name="test_unique_id",
            test_sql="SELECT * FROM users WHERE id IS NOT NULL",
            avg_execution_time_ms=2000,
        )

        assert isinstance(suggestions, list)

    def test_suggest_partition_filter(self, sample_manifest):
        """Test partition filter suggestion."""
        optimizer = TestOptimizer(sample_manifest)

        opt = optimizer._suggest_partition_filter("test_1", "SELECT * FROM users")

        if opt:
            assert isinstance(opt, OptimizationSuggestion)
            assert opt.optimization_type == "partition"
            assert opt.estimated_cost_reduction_percent > 0

    def test_extract_tables_from_sql(self, sample_manifest):
        """Test SQL table extraction."""
        optimizer = TestOptimizer(sample_manifest)

        sql = "SELECT u.* FROM users u JOIN orders o ON u.id = o.user_id"
        tables = optimizer._extract_tables_from_sql(sql)

        assert "users" in tables or "u" in [t.lower() for t in tables]


class TestCoverageAuditor:
    """Test suite for CoverageAuditor."""

    def test_audit_coverage(self, sample_manifest):
        """Test auditing test coverage across models."""
        auditor = CoverageAuditor(sample_manifest)

        gaps = auditor.audit_coverage()

        assert isinstance(gaps, list)
        assert all(isinstance(g, CoverageGap) for g in gaps)

    def test_find_attached_tests(self, sample_manifest):
        """Test finding tests attached to a model."""
        auditor = CoverageAuditor(sample_manifest)

        tests = auditor._find_attached_tests("model.test.users")

        assert isinstance(tests, list)
        assert len(tests) >= 2  # Should have at least unique and not_null tests

    def test_infer_test_type(self, sample_manifest):
        """Test inferring test type from definition."""
        auditor = CoverageAuditor(sample_manifest)

        test_node = sample_manifest["nodes"]["test.test.unique_users_id"]
        test_type = auditor._infer_test_type(test_node)

        assert test_type == "unique"

    def test_coverage_gap_priority(self, sample_manifest):
        """Test coverage gap priority determination."""
        auditor = CoverageAuditor(sample_manifest)

        gap = auditor._analyze_model_coverage("model.test.orders", sample_manifest["nodes"]["model.test.orders"])

        if gap:
            assert gap.priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    def test_calculate_model_risk_score(self, sample_manifest):
        """Test model risk score calculation."""
        auditor = CoverageAuditor(sample_manifest)

        model_node = sample_manifest["nodes"]["model.test.users"]
        risk_score = auditor._calculate_model_risk_score(model_node)

        assert 0 <= risk_score <= 100

    def test_recommend_tests(self, sample_manifest):
        """Test recommending test types."""
        auditor = CoverageAuditor(sample_manifest)

        model_node = sample_manifest["nodes"]["model.test.orders"]
        missing_types = ["unique", "relationships"]
        recommendations = auditor._recommend_tests(model_node, missing_types)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
