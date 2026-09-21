"""Historical replay analysis for dbt tests."""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from pydbtguard.models.schemas import HistoricalReplayResult
from pydbtguard.warehouse.base import WarehouseConnector


class HistoricalReplayAnalyzer:
    """Analyzes test reliability over historical data.

    NOTE: Currently returns entirely simulated/synthetic data (see
    `_simulate_replay`) — it does not query any real warehouse history.
    See ROADMAP_HONEST.md.
    """

    def __init__(self, warehouse: WarehouseConnector):
        self.warehouse = warehouse

    def analyze_test_historical_reliability(
        self,
        test_name: str,
        test_sql: str,
        lookback_days: int = 180,
    ) -> HistoricalReplayResult:
        """
        Analyze test reliability by replaying against historical snapshots.

        Args:
            test_name: Name of the test
            test_sql: SQL for the test
            lookback_days: How far back to analyze

        Returns:
            HistoricalReplayResult with trend, pass_rate, etc.
        """
        # In production, this would:
        # 1. Query for available snapshots/backups in the lookback window
        # 2. Execute test SQL against point-in-time replicas
        # 3. Track pass/fail per timestamp
        # 4. Calculate trends and metrics

        # For now, simulate based on test metadata
        simulated_results = self._simulate_replay(test_name, lookback_days)

        return simulated_results

    def _simulate_replay(self, test_name: str, lookback_days: int) -> HistoricalReplayResult:
        """Simulate historical replay results."""
        now = datetime.utcnow()
        failure_dates = []
        pass_count = 0
        total_runs = lookback_days

        # Simulate: 90% pass rate with occasional failures
        for i in range(lookback_days):
            date = now - timedelta(days=i)
            if i % 10 == 0:  # Fail every 10th day
                failure_dates.append(date.isoformat())
            else:
                pass_count += 1

        pass_rate = pass_count / total_runs if total_runs > 0 else 1.0

        # Calculate MTBF
        failure_count = len(failure_dates)
        mtbf_days = (
            (total_runs / (failure_count - 1)) if failure_count > 1 else float('inf')
        )

        # Determine trend
        if failure_count == 0:
            trend = "stable"
        elif failure_dates and len(failure_dates) > 1:
            # Check if failures are becoming more frequent (last 30 days)
            recent_failures = [d for d in failure_dates if datetime.fromisoformat(d) > now - timedelta(days=30)]
            past_failures = [d for d in failure_dates if datetime.fromisoformat(d) <= now - timedelta(days=30)]
            if len(recent_failures) > len(past_failures) / 2:
                trend = "degrading"
            else:
                trend = "improving"
        else:
            trend = "stable"

        # Calculate volatility (pass/fail transitions)
        volatility = (failure_count / total_runs) if total_runs > 0 else 0.0

        return HistoricalReplayResult(
            test_name=test_name,
            pass_rate=pass_rate,
            trend=trend,
            mtbf_days=mtbf_days,
            failure_dates=failure_dates,
            consecutive_passes=lookback_days - failure_count,
            volatility=volatility,
        )

    def get_flaky_tests(
        self,
        tests: List[str],
        lookback_days: int = 180,
    ) -> List[HistoricalReplayResult]:
        """
        Identify flaky tests (high volatility, inconsistent pass rate).

        Args:
            tests: List of test names to analyze
            lookback_days: Historical period to analyze

        Returns:
            List of flaky tests sorted by volatility
        """
        flaky = []

        for test_name in tests:
            result = self.analyze_test_historical_reliability(
                test_name, "", lookback_days
            )

            # Flaky if: pass_rate between 30-90% OR volatility > 0.3
            if (0.3 < result.pass_rate < 0.9) or (result.volatility > 0.3):
                flaky.append(result)

        # Sort by volatility (highest first)
        flaky.sort(key=lambda r: r.volatility, reverse=True)

        return flaky

    def calculate_test_reliability_curve(
        self,
        test_name: str,
        test_sql: str,
        window_days: int = 7,
        lookback_days: int = 180,
    ) -> List[Dict[str, Any]]:
        """
        Generate a reliability curve showing pass rate over time windows.

        Args:
            test_name: Test name
            test_sql: Test SQL
            window_days: Size of each time window
            lookback_days: Total lookback period

        Returns:
            List of dicts with {date, pass_rate, window_size}
        """
        now = datetime.utcnow()
        curve = []

        for i in range(0, lookback_days, window_days):
            window_start = now - timedelta(days=i + window_days)
            window_end = now - timedelta(days=i)

            # Simulate window metrics
            window_curve_point = {
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                "pass_rate": 0.85 + (i / lookback_days) * 0.1,  # Simulate improving trend
                "test_count": 30,  # Simulated
                "failure_count": 5,
            }

            curve.append(window_curve_point)

        return list(reversed(curve))  # Return in chronological order
