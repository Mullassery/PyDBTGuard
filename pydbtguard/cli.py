"""PyDBTGuard command-line interface.

Every command reads real dbt artifacts from a project's ``target/`` directory
and prints a real report. Errors are surfaced as ``click.ClickException`` (a
clean exit code 1 with a message), never swallowed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import click

from . import __version__, _core, artifacts
from .artifacts import ArtifactError, RunHistoryStore

PROJECT = click.argument(
    "project_path",
    type=click.Path(exists=True, file_okay=False),
    default=".",
)


def _call(func: Callable[..., str], *args: str) -> dict:
    try:
        return json.loads(func(*args))
    except ValueError as exc:  # raised by the Rust engine via ValueError
        raise click.ClickException(str(exc)) from exc


def _dump(payload: dict) -> None:
    click.echo(json.dumps(payload, indent=2))


def _project(project_path: str) -> Path:
    return Path(project_path)


class _GuardGroup(click.Group):
    """Turn artifact-location failures into clean, actionable CLI errors."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except ArtifactError as exc:
            raise click.ClickException(str(exc)) from exc


@click.group(cls=_GuardGroup, context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "--version", prog_name="pydbtguard")
@click.option("--json", "as_json", is_flag=True, help="Print the raw JSON report.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """PyDBTGuard: validate dbt tests from local dbt artifacts (no warehouse)."""
    ctx.ensure_object(dict)
    ctx.obj["as_json"] = as_json


@cli.command()
@PROJECT
@click.pass_context
def analyze(ctx: click.Context, project_path: str) -> None:
    """Score test reliability and predict failures from recorded run history."""
    project = _project(project_path)
    manifest = artifacts.manifest_text(project)

    store = RunHistoryStore(project)
    recorded = 0
    try:
        run_results_text = artifacts.run_results_text(project)
    except ArtifactError:
        pass  # no run_results.json yet; history may still exist
    else:
        # A malformed run_results.json raises ArtifactError here, which the
        # group turns into a clean ClickException rather than being swallowed.
        recorded = store.record_from_run_results(run_results_text)

    payload = _call(_core.analyze, manifest, store.history_text())

    if ctx.obj["as_json"]:
        _dump(payload)
        return

    summary = payload["summary"]
    click.echo(
        f"PyDBTGuard {payload['version']} - {payload.get('project_name') or 'project'} "
        f"({payload.get('adapter_type') or 'unknown adapter'})"
    )
    if recorded:
        click.echo(f"Recorded {recorded} new test outcome(s) from run_results.json.")
    click.echo(
        f"Tests: {payload['total_tests']}  "
        f"stable={summary['stable']} at_risk={summary['at_risk']} "
        f"dangerous={summary['dangerous']} unknown={summary['unknown']}"
    )
    for test in payload["tests"]:
        prob = test["failure_probability"]
        prob_text = "n/a" if prob is None else f"{prob:.0%}"
        click.echo(
            f"  [{test['risk_level']:<9}] {test['name']} "
            f"({test['test_type']}, failure={prob_text})"
        )


@cli.command()
@PROJECT
@click.option("--catalog", type=click.Path(exists=True, dir_okay=False), default=None)
@click.pass_context
def coverage(ctx: click.Context, project_path: str, catalog: str | None) -> None:
    """Audit test coverage and list prioritized gaps."""
    project = _project(project_path)
    manifest = artifacts.manifest_text(project)
    catalog_text = artifacts.catalog_text(project, catalog)
    payload = _call(_core.coverage, manifest, catalog_text)

    if ctx.obj["as_json"]:
        _dump(payload)
        return

    click.echo(
        f"Coverage: {payload['total_models']} models, "
        f"{payload['models_with_gaps']} with gaps "
        f"({payload['critical_count']} CRITICAL, {payload['high_count']} HIGH)"
    )
    for gap in payload["gaps"]:
        missing = ", ".join(gap["missing_test_types"])
        click.echo(
            f"  [{gap['priority']:<8}] {gap['model_name']} "
            f"(risk={gap['risk_score']}) missing: {missing}"
        )


@cli.command(name="blast-radius")
@PROJECT
@click.option("--model", required=True, help="Model unique id, e.g. model.pkg.orders")
@click.pass_context
def blast_radius(ctx: click.Context, project_path: str, model: str) -> None:
    """Show downstream impact of a failure in one model."""
    manifest = artifacts.manifest_text(_project(project_path))
    payload = _call(_core.blast_radius, manifest, model)

    if ctx.obj["as_json"]:
        _dump(payload)
        return

    click.echo(
        f"Blast radius of {payload['source_model_name']} "
        f"({payload['source_model_id']}): impact {payload['impact_score']:.0f}/100"
    )
    click.echo(
        f"  downstream models={payload['downstream_models']} "
        f"tests={payload['downstream_tests']} "
        f"exposures={len(payload['affected_exposures'])}"
    )
    for impact in payload["affected_models"]:
        click.echo(
            f"  [{impact['impact_level']:<8}] {impact['model_name']} "
            f"(distance {impact['distance']})"
        )
    for exposure in payload["affected_exposures"]:
        click.echo(f"  [exposure] {exposure['exposure_name']}")
    for rec in payload["recommendations"]:
        click.echo(f"  -> {rec}")


@cli.command()
@PROJECT
@click.option("--catalog", type=click.Path(exists=True, dir_okay=False), default=None)
@click.option("--adapter", default=None, help="Override the adapter used for pricing.")
@click.pass_context
def cost(
    ctx: click.Context,
    project_path: str,
    catalog: str | None,
    adapter: str | None,
) -> None:
    """Estimate per-scan cost from real catalog table sizes."""
    project = _project(project_path)
    manifest = artifacts.manifest_text(project)
    catalog_text = artifacts.catalog_text(project, catalog)
    if not catalog_text:
        raise click.ClickException(
            "catalog.json not found; run 'dbt docs generate' first (it records "
            "real table sizes)."
        )
    payload = _call(lambda m, c: _core.cost(m, c, adapter), manifest, catalog_text)

    if ctx.obj["as_json"]:
        _dump(payload)
        return

    price = payload["price_per_tb_usd"]
    click.echo(
        f"Cost estimate (adapter={payload['adapter_type'] or 'unknown'}, "
        f"price/TB={price if price is not None else 'n/a'})"
    )
    click.echo(f"  {payload['note']}")
    click.echo(
        f"  tests priced: {payload['priced_tests']}/{payload['total_tests']}, "
        f"total per scan: ${payload['total_estimated_cost_usd_per_scan']:.4f}"
    )
    for test in payload["most_expensive_tests"][:5]:
        cost_value = test["estimated_cost_usd_per_scan"]
        shown = "n/a" if cost_value is None else f"${cost_value:.4f}"
        bytes_value = test["scanned_bytes"]
        gb = "n/a" if bytes_value is None else f"{bytes_value / 1e9:.2f} GB"
        click.echo(f"  {test['test_name']}: {gb} -> {shown}/scan")
    for opt in payload["optimizations"][:5]:
        click.echo(f"  -> {opt['recommendation']}")


@cli.command()
@PROJECT
@click.pass_context
def history(ctx: click.Context, project_path: str) -> None:
    """Show reliability trends from the accumulated real run history."""
    store = RunHistoryStore(_project(project_path))
    history_text = store.history_text()
    if not history_text.strip():
        raise click.ClickException(
            "no run history recorded yet; run 'dbt test' (or 'dbt build') then "
            "'pydbtguard analyze' to start recording real outcomes."
        )
    payload = _call(_core.history, history_text)

    if ctx.obj["as_json"]:
        _dump(payload)
        return

    click.echo(
        f"History: {payload['total_runs']} recorded runs, "
        f"{payload['total_tests']} tests, {payload['flaky_count']} flaky"
    )
    for test in payload["tests"]:
        click.echo(
            f"  {test['test_id']}: pass_rate={test['pass_rate']:.0%} "
            f"transitions={test['transitions']} streak={test['current_pass_streak']} "
            f"trend={test['trend']}{' FLAKY' if test['flaky'] else ''}"
        )


@cli.command()
@PROJECT
@click.option("--sources", type=click.Path(exists=True, dir_okay=False), default=None)
@click.pass_context
def freshness(ctx: click.Context, project_path: str, sources: str | None) -> None:
    """Show source freshness from dbt's real sources.json."""
    project = _project(project_path)
    sources_json = artifacts.sources_text(project, sources)
    if not sources_json.strip():
        raise click.ClickException(
            "sources.json not found; run 'dbt source freshness' first."
        )
    manifest_text = artifacts.manifest_text(project)
    payload = _call(_core.freshness, sources_json, manifest_text)

    if ctx.obj["as_json"]:
        _dump(payload)
        return

    click.echo(
        f"Freshness: {payload['total_sources']} sources "
        f"(pass={payload['pass_count']} warn={payload['warn_count']} "
        f"error={payload['error_count']})"
    )
    for source in payload["sources"]:
        age_seconds = source["age_seconds"]
        age = "n/a" if age_seconds is None else f"{age_seconds / 3600:.1f}h"
        click.echo(f"  [{source['status']:<5}] {source['source_name']} age={age}")


@cli.command()
@click.option(
    "--old", "old_path", required=True, type=click.Path(exists=True, dir_okay=False)
)
@click.option(
    "--new", "new_path", required=True, type=click.Path(exists=True, dir_okay=False)
)
@click.pass_context
def drift(ctx: click.Context, old_path: str, new_path: str) -> None:
    """Compare two catalog.json snapshots for schema and volume drift."""
    old_text = Path(old_path).read_text(encoding="utf-8")
    new_text = Path(new_path).read_text(encoding="utf-8")
    payload = _call(_core.drift, old_text, new_text)

    if ctx.obj["as_json"]:
        _dump(payload)
        return

    click.echo(
        f"Drift: {payload['nodes_with_drift']} of {payload['nodes_compared']} "
        f"compared nodes changed"
    )
    for node in payload["drift"]:
        parts = []
        if node["row_delta"] is not None:
            parts.append(f"rows {node['row_delta']:+d}")
        if node["added_columns"]:
            parts.append(f"+cols {', '.join(node['added_columns'])}")
        if node["removed_columns"]:
            parts.append(f"-cols {', '.join(node['removed_columns'])}")
        for change in node["type_changes"]:
            parts.append(
                f"{change['column']}: {change['old_type']}->{change['new_type']}"
            )
        click.echo(f"  {node['unique_id']}: {'; '.join(parts)}")


@cli.command("select")
@click.argument("base_manifest", type=click.Path(exists=True, dir_okay=False))
@click.argument("current_manifest", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text"
)
@click.option(
    "--downstream/--no-downstream",
    default=True,
    help="Include downstream dependents (default) or only changed models.",
)
@click.option("--fail-on-empty", is_flag=True, help="Exit 1 when nothing is selected.")
@click.pass_context
def select(
    ctx: click.Context,
    base_manifest: str,
    current_manifest: str,
    output_format: str,
    downstream: bool,
    fail_on_empty: bool,
) -> None:
    """Select models/tests to run for changed dbt models (state:modified+)."""
    from .manifest_diff import load_manifest, select_tests

    try:
        selection = select_tests(
            load_manifest(base_manifest),
            load_manifest(current_manifest),
            include_downstream=downstream,
        )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    empty = not selection.selected_models and not selection.selected_tests
    if ctx.obj["as_json"] or output_format == "json":
        _dump(selection.to_dict())
    else:
        if empty:
            click.echo("No models or tests selected.")
        else:
            click.echo("--select " + " ".join(selection.dbt_select_args()))
            click.echo("")
            click.echo(f"Models ({len(selection.selected_models)}):")
            for value in selection.selected_models:
                click.echo(f"  {value}")
            click.echo(f"Tests ({len(selection.selected_tests)}):")
            for value in selection.selected_tests:
                click.echo(f"  {value}")
    if fail_on_empty and empty:
        raise click.exceptions.Exit(1)


@cli.command()
@click.argument("base_manifest", type=click.Path(exists=True, dir_okay=False))
@click.argument("current_manifest", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "markdown", "json"]),
    default="text",
    show_default=True,
)
@click.option(
    "--fail-on-change",
    is_flag=True,
    help="Exit 1 when any model or test was added/removed/modified (for CI).",
)
@click.pass_context
def diff(
    ctx: click.Context,
    base_manifest: str,
    current_manifest: str,
    output_format: str,
    fail_on_change: bool,
) -> None:
    """Compare two dbt manifest.json files (state:modified without a warehouse)."""
    from .manifest_diff import (
        diff_manifests,
        load_manifest,
        render_markdown,
        render_text,
    )

    try:
        result = diff_manifests(
            load_manifest(base_manifest), load_manifest(current_manifest)
        )
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    if ctx.obj["as_json"] or output_format == "json":
        _dump(result.to_dict())
    elif output_format == "markdown":
        click.echo(render_markdown(result))
    else:
        click.echo(render_text(result))

    if fail_on_change and result.has_changes:
        raise click.exceptions.Exit(1)


@cli.command("columns")
@click.argument("manifest", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--model", "model_filter", default=None, help="Filter by model unique_id substring"
)
@click.option("--dialect", default=None, help="SQLGlot dialect")
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text"
)
@click.pass_context
def columns(ctx, manifest, model_filter, dialect, output_format):
    """Show column-level lineage for dbt models in a manifest."""
    from .column_lineage import LineageUnavailable, analyze_manifest_column_lineage

    try:
        results = analyze_manifest_column_lineage(
            manifest, dialect=dialect, model_filter=model_filter
        )
    except LineageUnavailable as exc:
        raise click.ClickException(str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    if ctx.obj["as_json"] or output_format == "json":
        _dump([r.to_dict() for r in results])
        return
    for result in results:
        click.echo(result.model)
        for output, sources in result.outputs.items():
            click.echo(f"  {output} <- {', '.join(sources) or '(unknown)'}")
        for warning in result.warnings:
            click.echo(f"  warning: {warning}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
