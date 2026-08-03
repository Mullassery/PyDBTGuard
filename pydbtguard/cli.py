import click
import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from pydbtguard.dbt.manifest import ManifestLoader
from pydbtguard.analysis.reliability import ReliabilityAnalyzer
from pydbtguard.warehouse.factory import warehouse_factory


@click.group()
@click.version_option("0.1.0")
def cli():
    """PyDBTGuard: Pre-deployment validation for dbt tests"""
    pass


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option(
    "--warehouse",
    type=click.Choice(["snowflake", "bigquery"]),
    help="Warehouse type (auto-detect from profiles.yml if not specified)",
)
@click.option("--output", type=click.Path(), default=None, help="Output JSON file")
@click.option("--verbose", is_flag=True, help="Verbose output")
def analyze(project_path: str, warehouse: Optional[str], output: Optional[str], verbose: bool):
    """Analyze dbt tests for reliability and safety"""
    try:
        project_path = Path(project_path)

        if verbose:
            click.echo(f"📊 Analyzing dbt project at {project_path}")

        manifest_loader = ManifestLoader(project_path)
        manifest = manifest_loader.load()

        if verbose:
            click.echo(f"✓ Loaded manifest with {len(manifest.get('nodes', {}))} nodes")

        analyzer = ReliabilityAnalyzer()
        report = analyzer.analyze(manifest, warehouse_type=warehouse)

        if verbose:
            click.echo(f"✓ Analysis complete: {len(report['tests'])} tests analyzed")

        output_text = json.dumps(report, indent=2)

        if output:
            Path(output).write_text(output_text)
            click.echo(f"\n✓ Report saved to {output}")
        else:
            click.echo("\n" + output_text)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.Exit(1)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--lookback", default="180d", help="Lookback period (e.g., 180d, 6m)")
@click.option("--warehouse", type=click.Choice(["snowflake", "bigquery"]))
@click.option("--output", type=click.Path(), default=None, help="Output JSON file")
def replay(project_path: str, lookback: str, warehouse: Optional[str], output: Optional[str]):
    """Replay tests against historical warehouse states (Phase 2)"""
    try:
        from pydbtguard.analysis.replay import HistoricalReplayAnalyzer
        from pydbtguard.warehouse.factory import warehouse_factory

        project_path = Path(project_path)

        click.echo("⏮️  Historical replay engine (v0.2)")
        click.echo(f"Lookback period: {lookback}")

        # Parse lookback period
        lookback_days = 180
        if lookback.endswith("d"):
            lookback_days = int(lookback[:-1])
        elif lookback.endswith("m"):
            lookback_days = int(lookback[:-1]) * 30

        # TODO: Connect to warehouse and perform replay
        click.echo(f"✓ Analysis ready (lookback: {lookback_days} days)")
        click.echo("  Results would show: pass_rate, trend, flaky tests, reliability curves")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.Exit(1)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--model", default=None, help="Model ID to analyze")
@click.option("--output", type=click.Path(), default=None, help="Output JSON file")
def blast_radius(project_path: str, model: Optional[str], output: Optional[str]):
    """Analyze blast radius of test failures (Phase 2)"""
    try:
        from pydbtguard.dbt.manifest import ManifestLoader
        from pydbtguard.analysis.blast_radius import BlastRadiusAnalyzer

        project_path = Path(project_path)

        click.echo("💥 Blast radius analysis (v0.2)")

        manifest_loader = ManifestLoader(project_path)
        manifest = manifest_loader.load()

        analyzer = BlastRadiusAnalyzer(manifest)

        if model:
            # Analyze specific model
            result = analyzer.analyze_failure_impact(model)
            click.echo(f"✓ Model: {result.source_model}")
            click.echo(f"  Affected models: {result.total_affected_models}")
            click.echo(f"  Critical impact: {result.critical_impact_count}")
            click.echo(f"  Blast radius score: {result.overall_score:.1f}/100")
            click.echo(f"  Recovery time: {result.estimated_recovery_hours:.1f} hours")

            if output:
                import json
                Path(output).write_text(json.dumps(result.__dict__, indent=2))
                click.echo(f"\n✓ Report saved to {output}")
        else:
            click.echo("❌ Please specify --model <model_id>")
            raise click.Exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.Exit(1)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--output", type=click.Path(), default=None, help="Output JSON file")
def cost(project_path: str, output: Optional[str]):
    """Analyze test execution costs and optimization opportunities (Phase 2)"""
    try:
        from pydbtguard.dbt.manifest import ManifestLoader
        from pydbtguard.analysis.cost import CostAnalyzer

        project_path = Path(project_path)

        click.echo("💰 Cost analysis (v0.2)")

        manifest_loader = ManifestLoader(project_path)
        manifest = manifest_loader.load()

        # Extract test definitions
        tests = []
        for node_id, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "test":
                tests.append({
                    "name": node.get("name"),
                    "test_type": "custom",
                    "run_frequency": "daily",
                    "estimated_bytes_scanned": 1_000_000_000,
                })

        analyzer = CostAnalyzer()
        report = analyzer.analyze_test_costs(tests)

        click.echo(f"✓ {report.total_tests} tests analyzed")
        click.echo(f"  Monthly cost: ${report.total_monthly_cost_usd:.2f}")
        click.echo(f"  Annual cost: ${report.total_annual_cost_usd:.2f}")
        click.echo(f"  Potential savings: ${report.estimated_savings_usd:.2f}/year")
        click.echo(f"  Optimization opportunities: {len(report.optimization_opportunities)}")

        if output:
            import json
            Path(output).write_text(json.dumps(report.__dict__, indent=2, default=str))
            click.echo(f"\n✓ Report saved to {output}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.Exit(1)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--test", default=None, help="Test name to diagnose")
@click.option("--output", type=click.Path(), default=None, help="Output JSON file")
def diagnose(project_path: str, test: Optional[str], output: Optional[str]):
    """Generate diagnostic plan for test failure (Phase 3)"""
    try:
        from pydbtguard.dbt.manifest import ManifestLoader
        from pydbtguard.analysis.diagnostics import DiagnosticsAnalyzer

        project_path = Path(project_path)

        click.echo("🔍 Diagnostic analysis (v0.3)")

        manifest_loader = ManifestLoader(project_path)
        manifest = manifest_loader.load()

        analyzer = DiagnosticsAnalyzer(manifest)

        if test:
            plan = analyzer.diagnose_failure(test, [])
            click.echo(f"✓ Test: {plan.test_name}")
            click.echo(f"  Likely causes: {', '.join(plan.likely_causes)}")
            click.echo(f"  Diagnostic tests: {len(plan.diagnostic_tests)}")

            if output:
                import json
                Path(output).write_text(json.dumps(plan.__dict__, indent=2))
                click.echo(f"\n✓ Plan saved to {output}")
        else:
            click.echo("❌ Please specify --test <test_name>")
            raise click.Exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.Exit(1)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--output", type=click.Path(), default=None, help="Output JSON file")
def coverage_audit(project_path: str, output: Optional[str]):
    """Audit test coverage and identify gaps (Phase 3)"""
    try:
        from pydbtguard.dbt.manifest import ManifestLoader
        from pydbtguard.analysis.coverage import CoverageAuditor

        project_path = Path(project_path)

        click.echo("📊 Coverage audit (v0.3)")

        manifest_loader = ManifestLoader(project_path)
        manifest = manifest_loader.load()

        auditor = CoverageAuditor(manifest)
        gaps = auditor.audit_coverage()

        click.echo(f"✓ Coverage audit complete")
        click.echo(f"  Models with gaps: {len(gaps)}")

        critical = [g for g in gaps if g.priority == "CRITICAL"]
        high = [g for g in gaps if g.priority == "HIGH"]
        click.echo(f"  Critical gaps: {len(critical)}")
        click.echo(f"  High priority gaps: {len(high)}")

        if output:
            import json
            Path(output).write_text(json.dumps([asdict(g) for g in gaps], indent=2))
            click.echo(f"\n✓ Report saved to {output}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.Exit(1)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
def optimize(project_path: str):
    """Suggest test optimizations (Phase 3)"""
    click.echo("⚡ Test optimization engine (v0.3)")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
def pr_check(project_path: str):
    """Analyze tests in a GitHub PR"""
    click.echo("🔍 PR check integration (v0.4)")


def main():
    cli()


if __name__ == "__main__":
    main()
