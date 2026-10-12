"""Tests for artifact discovery and the run-history store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pydbtguard import artifacts
from pydbtguard.artifacts import ArtifactError, RunHistoryStore


def test_manifest_missing_raises_with_actionable_hint(tmp_path: Path) -> None:
    with pytest.raises(ArtifactError, match="dbt parse"):
        artifacts.manifest_text(tmp_path)


def test_catalog_is_optional(project: Path) -> None:
    # present in the fixture project
    assert artifacts.catalog_text(project).strip()
    # absent when the project has no target/catalog.json
    empty = project.parent / "no-target"
    empty.mkdir()
    assert artifacts.catalog_text(empty) == ""


def test_sources_text_reads_explicit_path(project: Path, fixtures_dir: Path) -> None:
    text = artifacts.sources_text(project, fixtures_dir / "sources.json")
    assert "raw_orders" in text


def test_history_store_records_real_outcomes(project: Path) -> None:
    store = RunHistoryStore(project)
    run_results = artifacts.run_results_text(project)

    recorded = store.record_from_run_results(run_results)
    assert recorded == 11  # 11 test nodes; the single model result is ignored
    assert store.recorded_run_count() == 1

    # Re-recording the identical run (same invocation_id) must not duplicate.
    assert store.record_from_run_results(run_results) == 0
    assert store.recorded_run_count() == 1


def test_history_store_ignores_non_test_and_skipped(tmp_path: Path) -> None:
    store = RunHistoryStore(tmp_path)
    payload = {
        "metadata": {"invocation_id": "x1"},
        "results": [
            {"unique_id": "model.pkg.orders", "status": "success"},
            {"unique_id": "test.pkg.a", "status": "pass"},
            {"unique_id": "test.pkg.b", "status": "skipped"},
            {"unique_id": "test.pkg.c", "status": "fail"},
        ],
    }
    recorded = store.record_from_run_results(payload_to_text(payload))
    # 'skipped' is retained as a raw status but only real tests are recorded;
    # the model node is dropped. pass + fail + skipped = 3 rows recorded.
    assert recorded == 3
    snapshot = store._snapshots()[0]
    assert snapshot["results"] == {
        "test.pkg.a": "pass",
        "test.pkg.b": "skipped",
        "test.pkg.c": "fail",
    }


def payload_to_text(payload: dict) -> str:
    return json.dumps(payload)
