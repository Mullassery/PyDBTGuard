# PyDBTGuard

**Stop fragile dbt tests from breaking production. Validate before you deploy.**

Predict which tests will fail. Measure blast radius. Optimize expensive queries. PyDBTGuard catches broken tests *before* they halt pipelines, crash dashboards, or break ML models.

[![PyPI](https://img.shields.io/pypi/v/pydbtguard)](https://pypi.org/project/pydbtguard)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-blue.svg)](./LICENSE)

---

## 30-Second Start

```bash
# Analyze your dbt project
pydbtguard analyze .

# View reliability scores
pydbtguard analyze . --output report.json
```

**Output:** Reliability scores (0-100), failure predictions, blast radius analysis.

---

## Why PyDBTGuard?

**The Problem:**
- dbt tests fail unpredictably and break production
- No way to know which downstream systems will crash
- Tests are expensive (scan petabytes to validate 100 rows)
- Tests pass but data is wrong (silent failures)
- No validation before deployment

**The Solution:**
- Predict failures before they happen (ML-based scoring)
- Map blast radius (which systems are affected)
- Optimize expensive tests (cut costs 30-70%)
- Detect silent failures (data anomalies tests miss)
- Validate in pre-deployment checks

---

## Key Features

- **Predictive Failure Scoring:** Machine learning model predicts test failures (0-100 score)
- **Historical Analysis:** 180-day reliability curves show true test stability
- **Blast Radius Mapping:** Understand which models/dashboards break if test fails
- **Cost Analysis:** Identify most expensive tests and optimization opportunities
- **Failure Pattern Detection:** Detect flaky tests, seasonal anomalies, data issues
- **Test Optimization:** Recommendations to improve reliability and reduce cost
- **Coverage Audit:** Identify gaps in what you're testing

---

## Real-World Use Cases

**Stop Pipeline Failures:**
```bash
# Find unreliable tests that will break production
pydbtguard analyze . --find-risky
# Result: "test_users_unique_id has 23% failure rate, affects 5 dashboards"
```

**Reduce Test Costs:**
```bash
# Find expensive tests burning query budget
pydbtguard cost-analysis
# Result: "test_orders_complete scans 10M rows unnecessarily, optimize: add WHERE clause"
```

**Deploy with Confidence:**
```bash
# Validate all tests before merge
pydbtguard pre-check --fail-on-risky
# Result: Blocks merge if high-risk tests detected
```

---

## Warehouse Support

| Warehouse | Status | Notes |
|-----------|--------|-------|
| Snowflake | ✅ | Full support |
| BigQuery | ✅ | Full support |
| Redshift | 🚧 | v0.2 |
| Databricks | 🚧 | v0.2 |

---

## Installation

```bash
pip install pydbtguard
# or with uv
uv pip install pydbtguard
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
