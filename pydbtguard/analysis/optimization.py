"""Test optimization analysis and suggestions."""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict

from pydbtguard.models.schemas import OptimizationSuggestion


class TestOptimizer:
    """Analyzes tests and suggests optimizations."""

    def __init__(self, manifest: Dict[str, Any]):
        """
        Initialize test optimizer.

        Args:
            manifest: dbt manifest
        """
        self.manifest = manifest
        self.nodes = manifest.get("nodes", {})

    def suggest_optimizations(
        self,
        test_name: str,
        test_sql: str,
        avg_execution_time_ms: int = 0,
    ) -> List[OptimizationSuggestion]:
        """
        Suggest optimizations for a test.

        Args:
            test_name: Name of test
            test_sql: SQL for the test
            avg_execution_time_ms: Current average execution time

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Parse test SQL (simplified)
        parsed = self._parse_test_sql(test_sql)

        # Suggest partition filters
        if parsed.get("scans_full_table"):
            partition_opt = self._suggest_partition_filter(test_name, test_sql)
            if partition_opt:
                suggestions.append(partition_opt)

        # Suggest incremental validation
        if avg_execution_time_ms > 1000:  # > 1 second
            incr_opt = self._suggest_incremental_validation(test_name, test_sql)
            if incr_opt:
                suggestions.append(incr_opt)

        # Suggest reference table caching
        cache_opt = self._suggest_caching(test_name, test_sql)
        if cache_opt:
            suggestions.append(cache_opt)

        return suggestions

    def _parse_test_sql(self, sql: str) -> Dict[str, Any]:
        """Parse SQL to extract optimization hints."""
        parsed = {
            "scans_full_table": True,
            "has_where_clause": "WHERE" in sql.upper(),
            "has_window_function": "OVER" in sql.upper(),
            "has_join": "JOIN" in sql.upper(),
        }
        return parsed

    def _suggest_partition_filter(
        self,
        test_name: str,
        test_sql: str,
    ) -> Optional[OptimizationSuggestion]:
        """Suggest adding partition filters."""
        # Find the table being scanned
        tables = self._extract_tables_from_sql(test_sql)
        if not tables:
            return None

        table = tables[0]
        suggested_sql = f"""
        SELECT *
        FROM {table}
        WHERE created_date >= CURRENT_DATE - 1
        """

        return OptimizationSuggestion(
            test_name=test_name,
            test_sql=test_sql,
            optimization_type="partition",
            suggested_sql=suggested_sql,
            estimated_latency_reduction_percent=50.0,
            estimated_cost_reduction_percent=60.0,
            effort_level="low",
            risk_level="low",
        )

    def _suggest_incremental_validation(
        self,
        test_name: str,
        test_sql: str,
    ) -> Optional[OptimizationSuggestion]:
        """Suggest incremental validation (last 24h only)."""
        suggested_sql = f"""
        -- Incremental validation: last 24 hours only
        {test_sql}
        AND updated_at >= CURRENT_TIMESTAMP - INTERVAL 1 DAY
        """

        return OptimizationSuggestion(
            test_name=test_name,
            test_sql=test_sql,
            optimization_type="incremental",
            suggested_sql=suggested_sql,
            estimated_latency_reduction_percent=45.0,
            estimated_cost_reduction_percent=50.0,
            effort_level="low",
            risk_level="medium",
        )

    def _suggest_caching(
        self,
        test_name: str,
        test_sql: str,
    ) -> Optional[OptimizationSuggestion]:
        """Suggest caching for reference tables."""
        # Detect if test uses large reference tables
        tables = self._extract_tables_from_sql(test_sql)
        if len(tables) < 2:
            return None

        # Assume second table is a reference
        ref_table = tables[1]
        suggested_sql = f"""
        -- Cache reference table for better performance
        WITH {ref_table}_cache AS (
            SELECT * FROM {ref_table}
        )
        {test_sql.replace(ref_table, f'{ref_table}_cache')}
        """

        return OptimizationSuggestion(
            test_name=test_name,
            test_sql=test_sql,
            optimization_type="caching",
            suggested_sql=suggested_sql,
            estimated_latency_reduction_percent=30.0,
            estimated_cost_reduction_percent=35.0,
            effort_level="medium",
            risk_level="low",
        )

    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL (simplified)."""
        # This is a simplified parser; in production use sqlparse or sqlglot
        tables = []

        # Find FROM clauses
        import re
        from_pattern = r"FROM\s+(\w+)"
        matches = re.findall(from_pattern, sql, re.IGNORECASE)
        tables.extend(matches)

        # Find JOIN clauses
        join_pattern = r"JOIN\s+(\w+)"
        matches = re.findall(join_pattern, sql, re.IGNORECASE)
        tables.extend(matches)

        return list(set(tables))  # Remove duplicates

    def estimate_optimization_impact(
        self,
        optimization: OptimizationSuggestion,
    ) -> Dict[str, Any]:
        """Estimate impact of an optimization."""
        return {
            "optimization_type": optimization.optimization_type,
            "estimated_latency_reduction_percent": optimization.estimated_latency_reduction_percent,
            "estimated_cost_reduction_percent": optimization.estimated_cost_reduction_percent,
            "effort_level": optimization.effort_level,
            "risk_level": optimization.risk_level,
            "recommended": optimization.estimated_cost_reduction_percent > 30.0,
        }
