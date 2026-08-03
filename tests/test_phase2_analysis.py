"""Tests for Phase 2 (v0.2) analysis modules."""

import pytest
from datetime import datetime

from pydbtguard.analysis.replay import HistoricalReplayAnalyzer
from pydbtguard.analysis.blast_radius import BlastRadiusAnalyzer
from pydbtguard.analysis.cost import CostAnalyzer
from pydbtguard.models.schemas import HistoricalReplayResult, BlastRadiusAnalysis, CostAnalysisReport


@pytest.fixture
def sample_manifest():
    """Provide a sample dbt manifest for testing."""
    return {
        "nodes": {
            "model.test.users": {
                "unique_id": "model.test.users",
                "name": "users",
                "resource_type": "model",
                "config": {"materialized": "table", "freshness": {"warn_after": {"count": 24}}},
                "depends_on": {"nodes": ["source.test.raw_users"]},
            },
            "model.test.orders": {
                "unique_id": "model.test.orders",
                "name": "orders",
                "resource_type": "model",
                "config": {"materialized": "incremental"},
                "depends_on": {"nodes": ["model.test.users"]},
            },
            "test.test.unique_users_id": {
                "unique_id": "test.test.unique_users_id",
                "name": "unique_users_id",
                "resource_type": "test",
                "attached_node": "model.test.users",
                "raw_sql": "SELECT id, COUNT(*) FROM users GROUP BY id HAVING COUNT(*) > 1",
            },
        },
        "exposures": {
            "dashboard.main_dashboard": {
                "unique_id": "dashboard.main_dashboard",
                "depends_on": {"nodes": ["model.test.orders"]},
            }
        },
    }


class TestHistoricalReplayAnalyzer:
    """Test suite for HistoricalReplayAnalyzer."""

    def test_analyze_test_historical_reliability(self):
        """Test analyzing test reliability over time."""
        analyzer = HistoricalReplayAnalyzer(None)

        result = analyzer.analyze_test_historical_reliability(
            test_name="test_unique_id",
            test_sql="SELECT * FROM table WHERE id IS NOT NULL",
            lookback_days=180,
        )

        assert isinstance(result, HistoricalReplayResult)
        assert result.test_name == "test_unique_id"
        assert 0 <= result.pass_rate <= 1.0
        assert result.trend in ["improving", "degrading", "stable"]
        assert result.mtbf_days >= 0

    def test_get_flaky_tests(self):
        """Test identifying flaky tests."""
        analyzer = HistoricalReplayAnalyzer(None)

        tests = ["test_1", "test_2", "test_3"]
        flaky = analyzer.get_flaky_tests(tests, lookback_days=30)

        assert isinstance(flaky, list)
        assert all(isinstance(r, HistoricalReplayResult) for r in flaky)

    def test_calculate_reliability_curve(self):
        """Test generating reliability curve."""
        analyzer = HistoricalReplayAnalyzer(None)

        curve = analyzer.calculate_test_reliability_curve(
            test_name="test_unique_id",
            test_sql="SELECT COUNT(*) FROM table",
            window_days=7,
            lookback_days=30,
        )

        assert isinstance(curve, list)
        assert len(curve) > 0
        assert all("window_start" in point and "pass_rate" in point for point in curve)


class TestBlastRadiusAnalyzer:
    """Test suite for BlastRadiusAnalyzer."""

    def test_analyze_failure_impact(self, sample_manifest):
        """Test analyzing blast radius of a model failure."""
        analyzer = BlastRadiusAnalyzer(sample_manifest)

        result = analyzer.analyze_failure_impact("model.test.users")

        assert isinstance(result, BlastRadiusAnalysis)
        assert result.source_model == "model.test.users"
        assert result.total_affected_models >= 0
        assert 0 <= result.overall_score <= 100
        assert result.estimated_recovery_hours >= 0
        assert len(result.recommendations) > 0

    def test_exposure_detection(self, sample_manifest):
        """Test detection of exposures at risk."""
        analyzer = BlastRadiusAnalyzer(sample_manifest)

        result = analyzer.analyze_failure_impact("model.test.orders")

        assert len(result.exposures_at_risk) > 0

    def test_impact_level_calculation(self, sample_manifest):
        """Test impact level calculation."""
        analyzer = BlastRadiusAnalyzer(sample_manifest)

        result = analyzer.analyze_failure_impact("model.test.users")

        assert any(m["impact_level"] in ["critical", "high", "medium", "low"]
                   for m in result.affected_models)


class TestCostAnalyzer:
    """Test suite for CostAnalyzer."""

    def test_analyze_test_costs(self):
        """Test analyzing costs for multiple tests."""
        analyzer = CostAnalyzer(warehouse_type="snowflake")

        tests = [
            {
                "name": "test_1",
                "test_type": "unique",
                "run_frequency": "daily",
                "estimated_bytes_scanned": 1_000_000_000,  # 1GB
            },
            {
                "name": "test_2",
                "test_type": "not_null",
                "run_frequency": "nightly",
                "estimated_bytes_scanned": 500_000_000,  # 500MB
            },
        ]

        report = analyzer.analyze_test_costs(tests)

        assert isinstance(report, CostAnalysisReport)
        assert report.total_tests == 2
        assert report.total_monthly_cost_usd > 0
        assert report.total_annual_cost_usd > report.total_monthly_cost_usd * 10
        assert len(report.most_expensive_tests) > 0
        assert len(report.optimization_opportunities) > 0

    def test_estimate_runs_per_month(self):
        """Test run frequency estimation."""
        analyzer = CostAnalyzer()

        assert analyzer._estimate_runs_per_month("on-every-commit") == 250
        assert analyzer._estimate_runs_per_month("daily") == 30
        assert analyzer._estimate_runs_per_month("nightly") == 30
        assert analyzer._estimate_runs_per_month("weekly") == 4
        assert analyzer._estimate_runs_per_month("monthly") == 1

    def test_cost_optimization_roi(self):
        """Test ROI calculation for optimizations."""
        from pydbtguard.models.schemas import CostOptimizationOpportunity

        analyzer = CostAnalyzer()

        opp = CostOptimizationOpportunity(
            test_name="test_1",
            optimization_type="partition",
            estimated_cost_reduction_percent=60.0,
            estimated_savings_usd_annual=500.0,
            implementation_effort="low",
            recommendation="Add partition filter",
        )

        roi = analyzer.estimate_optimization_roi(opp, implementation_cost_hours=4, hourly_rate=100)

        assert roi["annual_savings"] == 500.0
        assert roi["implementation_cost"] == 400.0
        assert roi["payback_months"] < 12
        assert roi["break_even"]
