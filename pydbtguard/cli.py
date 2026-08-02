import click
import json
from pathlib import Path
from typing import Optional

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
def replay(project_path: str, lookback: str, warehouse: Optional[str]):
    """Replay tests against historical warehouse states"""
    click.echo("⏮️  Historical replay engine (v0.2)")
    click.echo(f"Lookback: {lookback}")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
def simulate(project_path: str):
    """Simulate failure scenarios before deployment"""
    click.echo("🔄 Failure simulation engine (v0.3)")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
def pr_check(project_path: str):
    """Analyze tests in a GitHub PR"""
    click.echo("🔍 PR check integration (v0.4)")


def main():
    cli()


if __name__ == "__main__":
    main()
