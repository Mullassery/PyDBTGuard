# PyDBTGuard

**Pre-deployment validation & reliability testing for dbt**

PyDBTGuard prevents fragile, expensive, and operationally dangerous dbt tests from reaching production. It shifts validation left by evaluating the reliability, stability, cost, and operational impact of dbt tests *before* they are merged or deployed.

## Problem Statement

Organizations deploy thousands of dbt tests that:
- **Fail unpredictably** → halt analytics pipelines, break ML models, crash dashboards
- **Are inefficient** → scan petabytes to check 100 rows
- **Are overfit** → too strict for real business data variation
- **Lack visibility** → no one knows which downstream systems break if a test fails
- **Are expensive** → unoptimized queries, redundant checks
- **Are unvalidated** → deployed without historical validation or production simulation

## Core Philosophy

**Traditional dbt**: Did the test pass?  
**PyDBTGuard**: Should this test exist? Is it safe? Will it break production? How much damage can it cause?

## Features (v0.1)

### Predictive Failure Scoring
Forecast which tests will fail before execution using historical patterns + ML:
```bash
pydbtguard analyze .
```

### Silent Failure Detection
Identify behavioral anomalies (data passes tests but is semantically wrong).

### Test Reliability Scoring
Generate 0-100 reliability scores with risk levels (STABLE / AT_RISK / DANGEROUS).

## Installation

```bash
pip install pydbtguard
```

## Quick Start

```bash
# 1. Analyze your dbt project
pydbtguard analyze .

# 2. View the report
pydbtguard analyze . --output report.json
```

## Warehouse Support

- ✅ Snowflake
- ✅ BigQuery
- 🚧 Redshift (v0.2)
- 🚧 Databricks (v0.2)

## Roadmap

| Version | Focus | Timeline |
|---------|-------|----------|
| **v0.1** | Predictive Failure Scoring + Silent Failures | Now |
| **v0.2** | Blast Radius Mapping + Test Cost ROI | 3-4 weeks |
| **v0.3** | Diagnostic Plans + Test Optimization | 4-5 weeks |
| **v0.4** | Dashboard + PR Integration | 3-4 weeks |
| **v1.0** | Enterprise features + Multi-warehouse lineage | TBD |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation Guide](docs/INSTALLATION.md)
- [Getting Started](docs/GETTING_STARTED.md)
- [API Reference](docs/API.md)
- [Roadmap](docs/ROADMAP.md)

## License

Proprietary — Free to use

## Authors

Georgi Mammen Mullassery
