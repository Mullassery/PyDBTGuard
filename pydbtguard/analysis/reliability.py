from typing import Dict, Any, List, Optional
from pydbtguard.dbt.manifest import ManifestLoader
from pydbtguard.models.schemas import (
    ReliabilityScore,
    TestAnalysis,
    AnalysisReport,
)


class ReliabilityAnalyzer:
    """Analyze test reliability and stability"""

    def analyze(
        self,
        manifest: Dict[str, Any],
        warehouse_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze dbt tests for reliability"""
        loader = ManifestLoader(".")

        tests = loader.get_tests(manifest)
        models = loader.get_models(manifest)

        test_analyses = []
        for test in tests:
            analysis = self._analyze_single_test(test, models)
            test_analyses.append(analysis)

        return {
            "version": "0.1.0",
            "total_tests": len(tests),
            "tests": test_analyses,
            "summary": {
                "stable": sum(1 for t in test_analyses if t.get("risk_level") == "STABLE"),
                "at_risk": sum(1 for t in test_analyses if t.get("risk_level") == "AT_RISK"),
                "dangerous": sum(
                    1 for t in test_analyses if t.get("risk_level") == "DANGEROUS"
                ),
            },
        }

    def _analyze_single_test(self, test: Dict[str, Any], models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a single test"""
        score = self._compute_reliability_score(test)

        return {
            "name": test.get("name"),
            "unique_id": test.get("unique_id"),
            "type": test.get("test_type"),
            "attached_node": test.get("attached_node"),
            "reliability_score": score,
            "risk_level": self._risk_level(score),
            "recommendations": self._get_recommendations(test, score),
        }

    # dbt's built-in schema ("generic") test types, as returned by
    # ManifestLoader._infer_test_type on a real manifest -- that function
    # never returns the literal string "generic", so checking against it
    # directly (as this scoring used to) meant the +10 bonus below could
    # never fire for any test, on any real project: max reachable score was
    # 75, one point under the STABLE threshold, so nothing could ever be
    # classified STABLE regardless of real data.
    GENERIC_TEST_TYPES = {"unique", "not_null", "accepted_values", "relationships"}

    @staticmethod
    def _compute_reliability_score(test: Dict[str, Any]) -> int:
        """Compute reliability score (0-100)"""
        score = 75

        if test.get("test_type") in ReliabilityAnalyzer.GENERIC_TEST_TYPES:
            score += 10

        if "unique" in test.get("name", "").lower():
            score -= 5

        if "relationship" in test.get("name", "").lower():
            score -= 3

        return min(100, max(0, score))

    @staticmethod
    def _risk_level(score: int) -> str:
        """Determine risk level from score"""
        if score >= 80:
            return "STABLE"
        elif score >= 50:
            return "AT_RISK"
        else:
            return "DANGEROUS"

    @staticmethod
    def _get_recommendations(test: Dict[str, Any], score: int) -> List[str]:
        """Generate recommendations"""
        recommendations = []

        if score < 80:
            recommendations.append("Monitor test failure patterns")

        if "unique" in test.get("name", "").lower():
            recommendations.append("Consider adding partition filters for large tables")

        return recommendations
