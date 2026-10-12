"""End-to-end CLI tests against an isolated fixture project."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pydbtguard import __version__
from pydbtguard.cli import cli


def run(*args: str):
    return CliRunner().invoke(cli, [str(a) for a in args])


def test_version_reports_engine_version() -> None:
    result = run("--version")
    assert result.exit_code == 0
    assert __version__ in result.output


def test_analyze_json_is_typed_and_real(project: Path) -> None:
    result = run("--json", "analyze", project)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["kind"] == "analyze"
    assert payload["version"] == __version__
    assert payload["total_tests"] == 11
    assert payload["summary"]["dangerous"] == 1


def test_analyze_records_history_then_reports_it(project: Path) -> None:
    # First run ingests run_results.json into .pydbtguard/
    first = run("analyze", project)
    assert first.exit_code == 0, first.output
    assert "Recorded 11 new test outcome(s)" in first.output
    assert (project / ".pydbtguard" / "run_history.jsonl").exists()


def test_analyze_missing_manifest_exits_cleanly(tmp_path: Path) -> None:
    result = run("analyze", tmp_path)
    assert result.exit_code == 1
    assert "manifest.json not found" in result.output
    assert "dbt parse" in result.output


def test_coverage_lists_prioritized_gaps(project: Path) -> None:
    result = run("coverage", project)
    assert result.exit_code == 0, result.output
    assert "Coverage: 5 models" in result.output
    assert "5 with gaps" in result.output


def test_blast_radius_reports_real_impact(project: Path) -> None:
    result = run("blast-radius", "--model", "model.jaffle_shop.stg_orders", project)
    assert result.exit_code == 0, result.output
    assert "impact 75/100" in result.output
    assert "orders_dashboard" in result.output


def test_blast_radius_unknown_model_is_an_error(project: Path) -> None:
    result = run("blast-radius", "--model", "model.jaffle_shop.nope", project)
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_cost_requires_and_uses_catalog(project: Path) -> None:
    result = run("cost", project)
    assert result.exit_code == 0, result.output
    assert "adapter=bigquery" in result.output
    assert "price/TB=6.25" in result.output


def test_cost_without_catalog_is_a_clear_error(tmp_path: Path) -> None:
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text("{}")
    result = run("cost", tmp_path)
    assert result.exit_code == 1
    assert "dbt docs generate" in result.output


def test_history_without_recordings_is_a_clear_error(project: Path) -> None:
    result = run("history", project)
    assert result.exit_code == 1
    assert "no run history recorded yet" in result.output


def test_history_uses_recorded_outcomes(project: Path) -> None:
    # Seed the store by ingesting the fixture run (which has one failure).
    run("analyze", project)
    result = run("history", project)
    assert result.exit_code == 0, result.output
    assert "1 recorded runs" in result.output
    assert "assert_positive_amount" in result.output


def test_freshness_reshapes_sources_json(project: Path) -> None:
    result = run("freshness", project)
    assert result.exit_code == 0, result.output
    assert "pass=1" in result.output
    assert "warn=1" in result.output
    assert "error=1" in result.output


def test_drift_compares_two_catalogs(fixtures_dir: Path) -> None:
    result = run(
        "drift",
        "--old",
        fixtures_dir / "catalog.json",
        "--new",
        fixtures_dir / "catalog_v2.json",
    )
    assert result.exit_code == 0, result.output
    assert "2 of 5 compared nodes changed" in result.output
    assert "lifetime_value" in result.output
