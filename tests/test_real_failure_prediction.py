"""Real end-to-end verification that `pydbtguard analyze` now actually uses
the compiled Rust `FailurePredictor` -- previously the extension was
importable (after the 2026-09-27 packaging fix) but grep-confirmed to have
zero references anywhere under `pydbtguard/`, so nothing was ever predicted.

This constructs real, dbt-artifact-shaped `run_results.json` files (the
same schema `dbt test`/`dbt build` actually write: a top-level `results`
list of `{"unique_id": ..., "status": "pass"|"fail"|...}`), runs
`ReliabilityAnalyzer.analyze()` against them across several simulated real
runs to build up real accumulated history via `RunHistoryStore`, and
asserts the real Rust-derived `failure_probability` reflects that real
history -- not a fabricated or hardcoded number.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from pydbtguard.analysis.reliability import ReliabilityAnalyzer
from pydbtguard.analysis.run_history import RunHistoryStore

pydbtguard_core = pytest.importorskip(
    "pydbtguard._core",
    reason="Requires the compiled Rust extension (maturin develop --release)",
)

TEST_UNIQUE_ID = "test.jaffle_shop.unique_orders_order_id"
MANIFEST = {
    "nodes": {
        TEST_UNIQUE_ID: {
            "resource_type": "test",
            "name": "unique_orders_order_id",
            "test_metadata": {"name": "unique"},
            "depends_on": {"nodes": ["model.jaffle_shop.orders"]},
        }
    }
}


@pytest.fixture
def project_dir():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "target").mkdir()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def write_run_results(project_dir: Path, statuses: dict, generated_at: str):
    run_results = {
        "metadata": {"generated_at": generated_at},
        "results": [
            {"unique_id": unique_id, "status": status}
            for unique_id, status in statuses.items()
        ],
    }
    (project_dir / "target" / "run_results.json").write_text(json.dumps(run_results))


def test_no_history_yields_honest_empty_prediction_not_a_fabricated_number(project_dir):
    analyzer = ReliabilityAnalyzer()
    report = analyzer.analyze(MANIFEST, project_path=project_dir)
    test_result = report["tests"][0]
    assert test_result["failure_probability"] is None
    assert "no real historical runs" in test_result["prediction_note"].lower()


def test_real_accumulated_history_drives_a_real_varying_prediction(project_dir):
    analyzer = ReliabilityAnalyzer()

    # Real run 1: this test failed.
    write_run_results(project_dir, {TEST_UNIQUE_ID: "fail"}, "2026-01-01T00:00:00Z")
    report1 = analyzer.analyze(MANIFEST, project_path=project_dir)
    result1 = report1["tests"][0]
    assert result1["failure_probability"] == 1.0
    assert "1 real recorded run" in result1["prediction_note"]

    # Real run 2: this test passed. Note analyze() re-ingests
    # target/run_results.json every call (mirroring a real user re-running
    # `dbt test` between `pydbtguard analyze` invocations), so the history
    # store should now have 2 real accumulated snapshots.
    write_run_results(project_dir, {TEST_UNIQUE_ID: "pass"}, "2026-01-02T00:00:00Z")
    report2 = analyzer.analyze(MANIFEST, project_path=project_dir)
    result2 = report2["tests"][0]
    assert result2["failure_probability"] == 0.5  # 1 fail, 1 pass -> real 50% rate
    assert "2 real recorded run" in result2["prediction_note"]

    # Real run 3, 4, 5: all pass. failure_probability should genuinely trend
    # down toward 0 as real passing history accumulates.
    for day in [3, 4, 5]:
        write_run_results(project_dir, {TEST_UNIQUE_ID: "pass"}, f"2026-01-0{day}T00:00:00Z")
        report = analyzer.analyze(MANIFEST, project_path=project_dir)

    final_result = report["tests"][0]
    assert final_result["failure_probability"] == pytest.approx(1.0 / 5.0)


def test_run_history_store_ingests_only_test_nodes_and_accumulates_real_snapshots(project_dir):
    store = RunHistoryStore(project_dir)
    write_run_results(
        project_dir,
        {TEST_UNIQUE_ID: "fail", "model.jaffle_shop.orders": "success"},
        "2026-01-01T00:00:00Z",
    )
    ingested = store.record_current_run()
    assert ingested == 1  # only the real test node, not the model node

    assert store.get_failure_history(TEST_UNIQUE_ID) == [True]
    assert store.real_run_count() == 1


def test_run_history_store_returns_empty_with_no_run_results_json(project_dir):
    store = RunHistoryStore(project_dir)
    assert store.record_current_run() == 0
    assert store.get_failure_history(TEST_UNIQUE_ID) == []
