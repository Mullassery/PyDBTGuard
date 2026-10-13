# PyDBTGuard

Pre-deployment validation for dbt tests: analyze risk, impact, and cost from local dbt artifacts (`manifest.json`, `run_results.json`) without connecting to a warehouse.

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

## Who it's for / Use cases

- **Pre-PR checks**: Quickly assess which tests are high-risk before running the full suite.
- **CI optimization**: Prioritize tests that protect critical downstream models.
- **dbt maintenance**: Audit coverage gaps and understand test impact across lineage.
- **Historical insights**: Leverage past `run_results.json` to gauge test stability.

## What it is not

- **Not a full dbt observability platform**: Focused on pre-deployment risk/impact analysis from artifacts; no alerting, dashboards, or SLA tracking.
- **Not warehouse-connected**: Does not query Snowflake, BigQuery, or other warehouses. Warehouse connector classes exist in the codebase but are not wired to CLI commands.
- **Not ML-powered**: Reliability scoring uses fixed heuristics; failure probability is a historical failure rate computed from run history, not a trained model.
- **Experimental in places**: Some commands (`optimize`, `pr-check`, `replay`) are stubs or simulated. See roadmap for details.

## Project status

Version 2.0.0. Core analysis features (analyze, coverage-audit, diagnose, cost, blast radius) are implemented and tested (30/30 Python tests pass). Historical failure prediction is wired to the Rust core. Some features remain stubbed/simulated; see [ROADMAP_HONEST.md](ROADMAP_HONEST.md) for honest limitations.

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

## Documentation

- [Roadmap & honest limitations](ROADMAP_HONEST.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of conduct](CODE_OF_CONDUCT.md)

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
