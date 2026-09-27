"""Regression test found via real-world benchmarking against a real dbt
project (dbt-labs/jaffle-shop-classic): all 20 real, currently-passing
tests were classified AT_RISK, 0 STABLE. Root cause:
_compute_reliability_score checked `test.get("test_type") == "generic"`,
but ManifestLoader._infer_test_type (see test_manifest_test_type.py) never
returns the literal string "generic" - it returns the specific dbt test
name ("unique", "not_null", "accepted_values", "relationships") or
"singular"/"unknown". That +10 bonus could therefore never fire, capping
every test's score at 75 - one point under the STABLE threshold of 80 - so
nothing could ever be classified STABLE, on any project, regardless of
real data.
"""
from pydbtguard.analysis.reliability import ReliabilityAnalyzer


def test_generic_dbt_test_types_can_reach_stable():
    analyzer = ReliabilityAnalyzer()
    for test_type in ["not_null", "accepted_values"]:
        score = analyzer._compute_reliability_score({"test_type": test_type, "name": test_type})
        assert score >= 80, f"{test_type} scored {score}, expected >=80 (STABLE)"
        assert analyzer._risk_level(score) == "STABLE"


def test_singular_test_cannot_reach_stable_without_the_generic_bonus():
    analyzer = ReliabilityAnalyzer()
    score = analyzer._compute_reliability_score({"test_type": "singular", "name": "my_check"})
    assert score == 75
    assert analyzer._risk_level(score) == "AT_RISK"
