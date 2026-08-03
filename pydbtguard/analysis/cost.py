"""Cost analysis for dbt tests."""

from typing import List, Dict, Any, Tuple
from dataclasses import asdict

from pydbtguard.models.schemas import (
    TestCostAnalysis,
    CostAnalysisReport,
    CostOptimizationOpportunity,
)


class CostAnalyzer:
    """Analyzes test execution costs and optimization opportunities."""

    def __init__(self, warehouse_type: str = "snowflake", cost_per_credit_usd: float = 4.0):
        """
        Initialize cost analyzer.

        Args:
            warehouse_type: "snowflake", "bigquery", etc.
            cost_per_credit_usd: Cost per credit/unit for the warehouse
        """
        self.warehouse_type = warehouse_type
        self.cost_per_credit_usd = cost_per_credit_usd

    def analyze_test_costs(
        self,
        tests: List[Dict[str, Any]],
    ) -> CostAnalysisReport:
        """
        Analyze costs for a list of tests.

        Args:
            tests: List of test definitions with metadata

        Returns:
            CostAnalysisReport with breakdown and optimizations
        """
        test_costs = []
        cost_by_type = {}
        total_monthly = 0.0
        total_annual = 0.0

        for test in tests:
            cost = self._estimate_test_cost(test)
            test_costs.append(cost)

            # Aggregate by type
            test_type = test.get("test_type", "other")
            if test_type not in cost_by_type:
                cost_by_type[test_type] = 0.0
            cost_by_type[test_type] += cost.annual_cost_usd

            total_monthly += cost.monthly_cost_usd
            total_annual += cost.annual_cost_usd

        # Sort by cost (most expensive first)
        test_costs.sort(key=lambda t: t.annual_cost_usd, reverse=True)

        # Identify optimizations
        optimizations = self._identify_optimizations(test_costs)

        estimated_savings = sum(o.estimated_savings_usd_annual for o in optimizations)

        report = CostAnalysisReport(
            total_tests=len(tests),
            total_monthly_cost_usd=total_monthly,
            total_annual_cost_usd=total_annual,
            cost_by_test_type=cost_by_type,
            most_expensive_tests=test_costs[:10],
            optimization_opportunities=optimizations,
            estimated_savings_usd=estimated_savings,
        )

        return report

    def _estimate_test_cost(self, test: Dict[str, Any]) -> TestCostAnalysis:
        """Estimate cost for a single test."""
        test_name = test.get("name", "unknown")
        test_type = test.get("test_type", "other")
        frequency = test.get("run_frequency", "nightly")

        # Estimate bytes scanned (simplified)
        estimated_bytes = test.get("estimated_bytes_scanned", 1_000_000_000)  # 1GB default

        # Calculate cost per run
        cost_per_run = self._calculate_cost_per_run(estimated_bytes)

        # Estimate runs per month based on frequency
        runs_per_month = self._estimate_runs_per_month(frequency)

        return TestCostAnalysis(
            test_name=test_name,
            test_type=test_type,
            average_cost_usd=cost_per_run,
            average_execution_time_ms=int(estimated_bytes / 1024 / 1024 + 50),
            run_frequency=frequency,
            monthly_cost_usd=cost_per_run * runs_per_month,
            annual_cost_usd=cost_per_run * runs_per_month * 12,
        )

    def _calculate_cost_per_run(self, bytes_scanned: int) -> float:
        """Calculate cost for a single test run."""
        # Snowflake: 1 credit per 1GB scanned, approximately
        gb_scanned = bytes_scanned / (1024 ** 3)
        credits = max(1.0, gb_scanned)  # Minimum 1 credit
        return credits * self.cost_per_credit_usd

    def _estimate_runs_per_month(self, frequency: str) -> int:
        """Estimate number of test runs per month."""
        mapping = {
            "on-every-commit": 250,  # 8-10 commits/day, 25 days/month
            "daily": 30,
            "nightly": 30,
            "weekly": 4,
            "monthly": 1,
        }
        return mapping.get(frequency, 30)

    def _identify_optimizations(
        self,
        test_costs: List[TestCostAnalysis],
    ) -> List[CostOptimizationOpportunity]:
        """Identify optimization opportunities for expensive tests."""
        optimizations = []

        # Focus on top 5 most expensive tests
        for cost in test_costs[:5]:
            if cost.annual_cost_usd > 100.0:
                # Partition optimization
                partition_opt = CostOptimizationOpportunity(
                    test_name=cost.test_name,
                    optimization_type="partition",
                    estimated_cost_reduction_percent=60.0,
                    estimated_savings_usd_annual=cost.annual_cost_usd * 0.6,
                    implementation_effort="medium",
                    recommendation=(
                        f"Add partition filtering to {cost.test_name}. "
                        f"Expected to reduce scan volume by ~60%, saving ${cost.annual_cost_usd * 0.6:.2f}/year."
                    ),
                )
                optimizations.append(partition_opt)

                # Incremental validation
                if cost.run_frequency == "daily":
                    incr_opt = CostOptimizationOpportunity(
                        test_name=cost.test_name,
                        optimization_type="incremental",
                        estimated_cost_reduction_percent=45.0,
                        estimated_savings_usd_annual=cost.annual_cost_usd * 0.45,
                        implementation_effort="medium",
                        recommendation=(
                            f"Convert {cost.test_name} to incremental validation (validate last 24h only). "
                            f"Expected savings: ${cost.annual_cost_usd * 0.45:.2f}/year."
                        ),
                    )
                    optimizations.append(incr_opt)

        return optimizations

    def estimate_optimization_roi(
        self,
        optimization: CostOptimizationOpportunity,
        implementation_cost_hours: float = 8,
        hourly_rate: float = 100.0,
    ) -> Dict[str, float]:
        """
        Estimate ROI for an optimization.

        Args:
            optimization: The optimization opportunity
            implementation_cost_hours: Estimated dev time
            hourly_rate: Hourly rate for calculation

        Returns:
            Dict with roi_percent, payback_months, etc.
        """
        annual_savings = optimization.estimated_savings_usd_annual
        implementation_cost = implementation_cost_hours * hourly_rate

        payback_months = 12 * implementation_cost / annual_savings if annual_savings > 0 else float('inf')
        roi_percent = (annual_savings - implementation_cost) / implementation_cost * 100 if implementation_cost > 0 else 0

        return {
            "annual_savings": annual_savings,
            "implementation_cost": implementation_cost,
            "payback_months": payback_months,
            "roi_percent": roi_percent,
            "break_even": payback_months <= 12,
        }
