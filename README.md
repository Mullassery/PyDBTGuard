# PyDBTGuard

[![PyPI](https://img.shields.io/pypi/v/pydbtguard.svg)](https://pypi.org/project/pydbtguard/)

Pre-deployment validation for dbt tests: analyze risk, impact, and cost from local dbt artifacts (`manifest.json`, `run_results.json`) without connecting to a warehouse.

> **Not to be confused with [PyAirflowTester](https://github.com/Mullassery/PyAirflowTester) or [PyBlastRadius](https://github.com/Mullassery/PyBlastRadius):** PyDBTGuard statically analyzes a dbt `manifest.json`; PyAirflowTester validates Airflow DAGs and dbt runs; PyBlastRadius simulates cascading-failure impact across whole systems.

## Which project do I need?

Part of the Mullassery open-source family. These tools have similar names — here is the short version of who does what:

| If you need to… | Use |
| --- | --- |
| Build a repository's dependency graph and match it against vulnerability advisories (Python, Rust, Node, containers) | [PyDeepMesh](https://github.com/Mullassery/PyDeepMesh) |
| Understand *why* a Python dependency exists, who added it, and whether it is actually used | [PyDependencyCheck](https://github.com/Mullassery/PyDependencyCheck) |
| Statically analyze a **dbt** project (risky tests, test blast radius, cost) | [PyDBTGuard](https://github.com/Mullassery/PyDBTGuard) |
| Statically analyze **Apache Beam / Dataflow** pipelines (cost, hot keys, reliability) | [PyBeamGuard](https://github.com/Mullassery/PyBeamGuard) |
| Validate **Airflow** DAGs and dbt runs | [PyAirflowTester](https://github.com/Mullassery/PyAirflowTester) |
| Simulate cascading-failure **blast radius** across infrastructure, data pipelines, and AI systems | [PyBlastRadius](https://github.com/Mullassery/PyBlastRadius) |
| Check the **quality of the data itself** at runtime (schema, drift, anomalies) | [StatGuardian](https://github.com/Mullassery/StatGuardian) |
| Discover **devices, services, and vulnerabilities on a network** | [PyNetworkIntel](https://github.com/Mullassery/PyNetworkIntel) |
| Discover and score **API security** risk (real traffic, agent/MCP, Cedar policy) | [PyAPICheck](https://github.com/Mullassery/PyAPICheck) |
| Trace and root-cause **AI agent** failures | [PyAgentHound](https://github.com/Mullassery/PyAgentHound) |
| Diagnose **RAG retrieval** failures | [PyVectorHound](https://github.com/Mullassery/PyVectorHound) |
| Orchestrate **local, dependency-aware tasks** (DAG scheduler + content-addressed cache) | [PyTaskWireCheck](https://github.com/Mullassery/PyTaskWireCheck) |

[Browse all projects →](https://github.com/Mullassery?tab=repositories)

## What it is

PyDBTGuard reads compiled dbt metadata to help you understand which tests are risky, which downstream models they protect, and how to prioritize testing. It works entirely from local artifacts—no live warehouse queries. A Rust core supports failure prediction based on historical run results.

## Features / Highlights

- **Risk scoring**: Heuristic reliability scoring for each test based on test type and metadata from `manifest.json`.
- **Failure prediction**: Computes historical failure probability from accumulated `run_results.json` files (wired to Rust `FailurePredictor`).
- **Impact analysis**: Maps tests to affected downstream models using the dbt lineage graph (blast radius).
- **Coverage audit**: Identifies missing test coverage by model and prioritizes gaps.
- **Cost estimation**: Estimates relative test cost from manifest metadata.
- **Diagnostics**: Generates diagnostic hints for tests based on patterns in names/config.
- **CLI-first**: Simple commands to analyze, diagnose, audit coverage, and estimate cost.
- **Opt-in local query connectors**: `pydbtguard query` can validate a
  read-only SQL statement or fetch a few rows from a local SQLite or DuckDB
  database, or from a Postgres server you configure, through a plugin. This is
  separate from the artifact-only analysis path.

## Who it's for / Use cases

- **Pre-PR checks**: Quickly assess which tests are high-risk before running the full suite.
- **CI optimization**: Prioritize tests that protect critical downstream models.
- **dbt maintenance**: Audit coverage gaps and understand test impact across lineage.
- **Historical insights**: Leverage past `run_results.json` to gauge test stability.

## What it is not

- **Not a full dbt observability platform**: Focused on pre-deployment risk/impact analysis from artifacts; no alerting, dashboards, or SLA tracking.
- **Not live-warehouse-connected**: Analysis uses only local dbt artifacts. The
  optional `query` command talks to a local SQLite/DuckDB file or a Postgres
  server you configure through an explicit plugin interface; Snowflake,
  BigQuery, Redshift, and MySQL are explicitly not wired and produce a clear
  error.
- **Not ML-powered**: Reliability scoring uses fixed heuristics; failure probability is a historical failure rate computed from run history, not a trained model.
- **Experimental in places**: Some commands (`optimize`, `pr-check`, `replay`) are stubs or simulated. See roadmap for details.

## Project status

Version 2.4.2. Core analysis features (analyze, coverage-audit, diagnose, cost, blast radius) are implemented and tested. Historical failure prediction is wired to the Rust core. The opt-in SQLite, DuckDB, and Postgres connectors are real local read-only connectors (Postgres tests skip unless a local DSN is configured). Snowflake, BigQuery, Redshift, and MySQL are not wired. Some features remain stubbed/simulated; see [docs/internal/ROADMAP_HONEST.md](docs/internal/ROADMAP_HONEST.md) for honest limitations.

## Installation

```bash
pip install pydbtguard
```

From source:

```bash
git clone https://github.com/Mullassery/PyDBTGuard
cd PyDBTGuard
pip install maturin
maturin develop
```

Requires Python 3.9+.

## Quick start

```bash
# Analyze tests in a dbt project (from manifest.json in target/)
pydbtguard analyze /path/to/dbt/project

# Save report as JSON
pydbtguard analyze /path/to/dbt/project --output report.json

# Diagnose a specific test
pydbtguard diagnose --test my_model_unique_key

# Audit test coverage
pydbtguard coverage-audit /path/to/dbt/project

# Estimate test cost
pydbtguard cost /path/to/dbt/project
```

The CLI expects compiled dbt artifacts (`target/manifest.json`). For historical failure probability, include `target/run_results.json` (or multiple runs accumulated by your process).

## Manifest diff (state:modified without a warehouse)

```bash
pydbtguard diff base/target/manifest.json current/target/manifest.json --format markdown --fail-on-change
```

Reports added/removed/modified models, added/removed tests, and tests attached
to or depending on changed models. Reads artifacts only.

## CI

A composite GitHub Action and PR example live in
[`docs/CI.md`](docs/CI.md). It runs the manifest diff and writes the report to
the job summary.

## Releasing

See [`docs/RELEASE.md`](docs/RELEASE.md) for the Trusted Publishing setup and
the wheel matrix.

## Known issues and deferred work

**Blocked / failed:**
- Verify the PR action on a real dbt project.

**Rejected / deferred:**
- Live warehouse connectors; static artifacts remain the primary path. Shipped
  connectors are opt-in and read-only: local SQLite and DuckDB, plus an
  optional Postgres skeleton for a local server.

Full shipped/blocked/rejected detail: [`docs/internal/QUEUE_STATUS.md`](docs/internal/QUEUE_STATUS.md).

## Documentation

- [Roadmap & honest limitations](docs/internal/ROADMAP_HONEST.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of conduct](CODE_OF_CONDUCT.md)

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

### Select only affected tests (`state:modified+`)

The diff engine now expands changed models to downstream dependents and selects
the tests attached to any selected model, not only the directly changed one:

```bash
pydbtguard select target/base_manifest.json target/manifest.json
pydbtguard select base.json current.json --no-downstream --format json
```

Output is ready for dbt:

```
--select model.proj.raw model.proj.mid model.proj.final test.proj.raw_unique ...
```

This complements `pydbtguard diff`, which reports the raw added/removed/modified
sets. No warehouse or dbt run is required.

### Column-level lineage

`pydbtguard columns` parses compiled model SQL with SQLGlot and reports which
source columns feed each output column, including CTE resolution:

```bash
pip install "pydbtguard[lineage]"
pydbtguard columns target/manifest.json --model orders --format json
```

It reads only manifest SQL; SQLGlot is an optional dependency and the command
exits with an install hint when it is absent.

### Local warehouse connectors (opt-in)

The plugin interface lives in `pydbtguard.connectors`. A connector subclasses
`WarehouseConnector` and implements `validate_query` and `fetch`:

```python
from pydbtguard.connectors import (
    QueryValidation, WarehouseConnector, get_connector, register_connector,
)

class MyConnector(WarehouseConnector):
    name = "my_connector"

    def validate_query(self, config, sql):
        return QueryValidation(self.name, True, "validated")

    def fetch(self, config, sql, limit=100):
        return []  # real read-only I/O here

register_connector("my_connector", MyConnector)
```

External packages can declare the `pydbtguard.warehouse_connectors`
entry-point group instead of calling `register_connector`:

```toml
[project.entry-points."pydbtguard.warehouse_connectors"]
my_connector = "my_package.connectors:MyConnector"
```

The bundled `sqlite` connector opens the database with SQLite's `mode=ro` URI
and accepts only one `SELECT`/`WITH` statement. The optional `duckdb` and
`postgres` connectors follow the same read-only rule:

```bash
pip install "pydbtguard[duckdb]"     # DuckDB driver
pip install "pydbtguard[postgres]"   # psycopg driver for a local server

pydbtguard connectors
pydbtguard query --database ./warehouse.db --sql "SELECT * FROM customers" --limit 5
pydbtguard query --database ./warehouse.db --sql "SELECT * FROM customers" --validate-only
pydbtguard --json query --database ./warehouse.db --sql "SELECT * FROM customers"

pydbtguard query --warehouse duckdb --database ./warehouse.duckdb \
  --sql "SELECT * FROM customers" --limit 5

pydbtguard query --warehouse postgres --dsn "$DATABASE_URL" \
  --sql "SELECT * FROM customers" --limit 5
```

The DuckDB database is opened with `read_only=True`. The Postgres connector is
a skeleton: it uses `psycopg`, requires a server you configure (`--dsn` or
`DATABASE_URL`), and is tested only when a local Postgres server is available
(those tests skip with an explicit reason otherwise). Snowflake, BigQuery,
Redshift, and MySQL remain listed by `pydbtguard connectors` as not wired. No
live-warehouse support is claimed.

