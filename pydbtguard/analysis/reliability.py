from pathlib import Path
from typing import Dict, Any, List, Optional
from pydbtguard.dbt.manifest import ManifestLoader
from pydbtguard.analysis.run_history import RunHistoryStore

try:
    import pydbtguard._core as _core

    _RUST_CORE_AVAILABLE = True
except ImportError:
    _RUST_CORE_AVAILABLE = False


class ReliabilityAnalyzer:
    """Analyze test reliability and stability"""

    def analyze(
        self,
        manifest: Dict[str, Any],
        project_path: Path | str = ".",
        warehouse_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze dbt tests for reliability"""
        loader = ManifestLoader(".")

        tests = loader.get_tests(manifest)
        models = loader.get_models(manifest)

        # Real historical failure tracking: ingest the current real
        # `target/run_results.json` (if `dbt test`/`dbt build` has been run)
        # into a real, locally-accumulated history, then use that real
        # per-test history to drive the real Rust FailurePredictor. See
        # run_history.py's module docstring for why this exists -- there
        # was previously no real historical data anywhere in this codebase
        # to predict from.
        history_store = RunHistoryStore(project_path)
        history_store.record_current_run()

        test_analyses = []
        for test in tests:
            analysis = self._analyze_single_test(test, models, history_store)
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

    def _analyze_single_test(
        self,
        test: Dict[str, Any],
        models: List[Dict[str, Any]],
        history_store: RunHistoryStore,
    ) -> Dict[str, Any]:
        """Analyze a single test"""
        score = self._compute_reliability_score(test)
        prediction = self._predict_failure(test, history_store)

        result = {
            "name": test.get("name"),
            "unique_id": test.get("unique_id"),
            "type": test.get("test_type"),
            "attached_node": test.get("attached_node"),
            "reliability_score": score,
            "risk_level": self._risk_level(score),
            "recommendations": self._get_recommendations(test, score),
        }
        result.update(prediction)
        return result

    @staticmethod
    def _predict_failure(
        test: Dict[str, Any], history_store: RunHistoryStore
    ) -> Dict[str, Any]:
        """Real failure-probability prediction from real accumulated run
        history, via the compiled Rust `FailurePredictor`. Returns an
        honest, explicitly-flagged empty result (not a fabricated number)
        when either the Rust extension isn't built or no real historical
        runs have been recorded for this test yet -- `pydbtguard analyze`
        must actually be run after real `dbt test` invocations to build
        this up; it's real accumulated data, not a one-shot guess.
        """
        unique_id = test.get("unique_id")
        failure_history = history_store.get_failure_history(unique_id) if unique_id else []

        if not _RUST_CORE_AVAILABLE:
            return {
                "failure_probability": None,
                "prediction_confidence": None,
                "likely_causes": [],
                "prediction_note": "Rust prediction engine not available (pydbtguard._core failed to import).",
            }

        if not failure_history:
            return {
                "failure_probability": None,
                "prediction_confidence": None,
                "likely_causes": [],
                "prediction_note": (
                    "No real historical runs recorded for this test yet -- run "
                    "'dbt test' followed by 'pydbtguard analyze' again to start "
                    "building real failure history."
                ),
            }

        predictor = _core.FailurePredictor(180)
        failure_probability, confidence, likely_causes = predictor.predict_py(failure_history)

        return {
            "failure_probability": failure_probability,
            "prediction_confidence": confidence,
            "likely_causes": likely_causes,
            "prediction_note": f"Based on {len(failure_history)} real recorded run(s).",
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
