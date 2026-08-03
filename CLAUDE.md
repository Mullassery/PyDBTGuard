# PyDBTGuard Codebase Guide

## Project Overview

**PyDBTGuard** is a Rust + Python platform for pre-deployment validation of dbt tests.

**Architecture**: Hybrid Rust/Python monorepo
- **Rust core** (`crates/pydbtguard-core`): Statistical analysis, failure prediction, lineage graphs
- **Python bindings** (`bindings/python`): PyO3 FFI layer
- **Python CLI** (`pydbtguard/`): dbt integration, warehouse connectors, CLI orchestration

## Directory Structure

```
PyDBTGuard/
├── Cargo.toml                              # Rust workspace root
├── crates/pydbtguard-core/                 # Core library (Rust)
│   └── src/
│       ├── stats/                          # Statistical analysis (v0.1)
│       │   ├── fingerprint.rs              # Column fingerprinting
│       │   └── predictor.rs                # ML failure prediction
│       ├── lineage/                        # Impact analysis (v0.1)
│       │   └── graph.rs                    # DAG for blast radius
│       ├── manifest/                       # dbt manifest parsing (v0.1)
│       │   └── parser.rs
│       ├── replay/                         # Historical replay engine (v0.2)
│       │   ├── mod.rs                      # HistoricalReliabilityCurve, ReplayResult
│       │   └── engine.rs                   # HistoricalReplayEngine
│       ├── patterns/                       # Failure pattern detection (v0.2)
│       │   ├── mod.rs                      # PatternType, FailurePattern
│       │   └── detector.rs                 # FailurePatternDetector
│       ├── impact/                         # Blast radius analysis (v0.2)
│       │   ├── mod.rs                      # BlastRadiusResult, ImpactLevel
│       │   └── analyzer.rs                 # BlastRadiusAnalyzer
│       └── cost/                           # Cost analysis (v0.2)
│           ├── mod.rs                      # QueryCost, TestCost
│           └── calculator.rs               # CostCalculator
├── pydbtguard/                             # Python package
│   ├── cli.py                              # Click CLI commands
│   ├── dbt/                                # dbt integration
│   │   └── manifest.py                     # Manifest loader
│   ├── warehouse/                          # Warehouse connectors
│   │   ├── base.py
│   │   ├── snowflake.py
│   │   ├── bigquery.py
│   │   └── factory.py
│   ├── analysis/                           # Analysis engines
│   │   ├── reliability.py                  # Reliability scoring (v0.1)
│   │   ├── replay.py                       # Historical replay (v0.2)
│   │   ├── blast_radius.py                 # Blast radius mapping (v0.2)
│   │   ├── cost.py                         # Cost analysis (v0.2)
│   │   ├── diagnostics.py                  # Diagnostic plans (v0.3)
│   │   ├── optimization.py                 # Test optimization (v0.3)
│   │   ├── coverage.py                     # Coverage audit (v0.3)
│   │   └── __init__.py
│   ├── models/                             # Data models
│   │   ├── schemas.py                      # Dataclasses for all output types
│   │   └── __init__.py
│   └── __init__.py
├── tests/                                  # Test suite
│   ├── test_phase2_analysis.py             # v0.2 tests (replay, blast radius, cost)
│   ├── test_phase3_analysis.py             # v0.3 tests (diagnostics, optimize, coverage)
│   └── __init__.py
├── docs/                                   # Documentation
│   ├── PHASE2_v0.2.md                      # v0.2 feature guide
│   ├── PHASE3_v0.3.md                      # v0.3 feature guide
│   ├── GETTING_STARTED.md
│   ├── API.md
│   └── ROADMAP.md
└── examples/                               # Sample projects
```

## Development Workflow

### Setup

```bash
# Clone and enter repo
git clone https://github.com/Mullassery/PyDBTGuard
cd PyDBTGuard

# Install Python dependencies + build Rust bindings
pip install -e ".[dev]"

# Build Rust core
cargo build --release

# Run tests
pytest tests/
cargo test
```

### Adding a New Warehouse Connector

1. Create `pydbtguard/warehouse/newdb.py`
2. Inherit from `WarehouseConnector` base class
3. Implement: `connect()`, `execute_query()`, `get_table_stats()`, `disconnect()`
4. Update `warehouse/factory.py` to register the connector
5. Add integration tests

### Adding a New Analysis Engine

1. Create `pydbtguard/analysis/newfeature.py`
2. Implement analysis logic (use Rust core where computationally heavy)
3. Export from `pydbtguard/analysis/__init__.py`
4. Integrate into CLI via `pydbtguard/cli.py`
5. Add tests and documentation

### Rust Core Development

- Statistical analysis: `crates/pydbtguard-core/src/stats/`
- Lineage/impact: `crates/pydbtguard-core/src/lineage/`
- Python exports: `bindings/python/src/lib.rs`

Use `cargo build --release` for optimized binaries, `cargo test` for testing.

## Key Types & Concepts

### v0.1: Foundation

#### Manifest
- Loaded from `target/manifest.json` (via `dbt parse`)
- Nodes: models, tests, sources, snapshots, exposures
- Tests: unique_id, fqn, attached_node, raw_sql, config

#### Warehouse Connectors
- Abstract interface: `connect()` → `execute_query()` → results
- Context manager support: `with WarehouseConnector(...) as conn:`
- Per-warehouse: authentication, query syntax, metadata schema

#### Reliability Analysis
- Input: test definition + warehouse metadata
- Output: 0-100 score + risk level (STABLE / AT_RISK / DANGEROUS)
- Factors: test type, failure history, cost, blast radius

### v0.2: Historical & Impact Analysis

#### HistoricalReliabilityCurve
- Test execution history over time
- Metrics: pass_rate, trend, mtbf_days, consecutive_passes, volatility
- Used for: identifying flaky tests, reliability trends

#### FailurePattern
- Detected patterns: DuplicateSpike, SeasonalAnomaly, BackfillSensitivity, etc.
- Attributes: confidence (0-1), severity (CRITICAL/HIGH/MEDIUM/LOW), evidence
- Output: recommended fixes for each pattern

#### BlastRadiusResult
- Impact analysis of a model failure
- Metrics: total_affected_models, critical_impact_count, overall_score (0-100)
- Output: affected models, exposures at risk, recovery time, recommendations

#### CostAnalysisResult
- Test execution costs and optimizations
- Metrics: monthly_cost_usd, annual_cost_usd, estimated_savings_usd
- Output: most expensive tests, optimization opportunities, ROI

### v0.3: Diagnostics & Optimization

#### DiagnosticPlan
- Root cause analysis for failing tests
- Attributes: likely_causes, diagnostic_tests (SQL queries), correlation_scores
- Output: actionable debugging steps

#### OptimizationSuggestion
- Test rewrite suggestions
- Types: partition filtering, incremental validation, caching, sampling
- Metrics: estimated_latency_reduction_percent, estimated_cost_reduction_percent

#### CoverageGap
- Missing test types per model
- Attributes: risk_score, missing_test_types, recommended_tests, priority
- Output: risk-prioritized list of coverage gaps

## CLI Commands

### v0.1 Commands
```bash
pydbtguard analyze .              # Main command: reliability scoring + risk levels
```

### v0.2 Commands (Phase 2 - Historical Analysis)
```bash
pydbtguard replay --lookback 180d              # Historical reliability analysis
pydbtguard blast-radius --model model.x.users  # Impact mapping for failures
pydbtguard cost                                 # Test execution cost analysis
```

### v0.3 Commands (Phase 3 - Operational Intelligence)
```bash
pydbtguard diagnose --test test_unique_id     # Root cause analysis & diagnostics
pydbtguard optimize                            # Test optimization suggestions
pydbtguard coverage-audit                      # Coverage gap detection + prioritization
```

### v0.4+ (Planned)
```bash
pydbtguard pr-check                           # GitHub PR integration
pydbtguard simulate                           # Failure scenario simulation
```

## Testing

- **Unit tests**: `tests/unit/`
- **Integration tests**: `tests/integration/` (require warehouse access)
- **Fixtures**: `tests/fixtures/` (sample manifests, data)

Run tests:
```bash
pytest tests/unit/        # Fast, no warehouse required
pytest tests/integration/ # Requires Snowflake/BigQuery credentials
pytest                    # All tests
```

## Dependencies

**Python**:
- `click` — CLI framework
- `pydantic` — Data validation
- `sqlglot` — SQL parsing
- `networkx` — Lineage graphs
- `snowflake-connector-python`, `google-cloud-bigquery` — Warehouse clients

**Rust**:
- `polars` — DataFrame/statistical analysis
- `statrs` — Statistical functions
- `pyo3` — Python bindings

## Coding Standards

- **Python**: Follow PEP 8, use type hints, add docstrings
- **Rust**: Follow rustfmt, add unit tests, document public APIs
- **Tests**: Aim for >80% coverage, test error paths
- **No comments**: Use clear naming; add comments only for non-obvious logic

## Versioning

- Current: `0.1.0`
- Bumped via: `Cargo.toml` (Rust) + `pyproject.toml` (Python)
- Release: tag `v0.1.0`, publish to PyPI via GitHub Actions

## CI/CD

- GitHub Actions: `tests/`, `lint`, `build`
- Pre-commit: Run tests before commit (if configured)
- Release: Tag → build → PyPI

## Version Roadmap

### v0.1.0 (Complete)
- Dbt manifest parsing
- Reliability scoring with statistical analysis
- Failure prediction models
- Lineage graph construction

### v0.2.0 (Complete)
- Historical replay engine (180-day reliability curves)
- Failure pattern detection (6+ patterns)
- Blast radius analysis with impact scoring
- Test cost analysis with optimization ROI
- 4 new Rust modules (~1K LOC)

### v0.3.0 (Complete)
- Predictive diagnostic plans
- Test optimization suggestions (partition, incremental, caching)
- Coverage audit with risk-based prioritization
- 3 new Python modules (~1.5K LOC)

### v0.4.0 (Planned - Q3 2024)
- Real warehouse snapshot integration
- GitHub PR analysis and gating
- Slack/Teams integration
- Dashboard UI (Streamlit)
- Multi-warehouse cost comparison

### v1.0.0 (Planned - Q4 2024)
- Enterprise RBAC and audit logging
- Scheduled batch analysis jobs
- ML-based failure prediction
- Advanced visualizations
- REST API for external integrations
- Performance optimizations (1000s of tests)

## Contact

Questions? File an issue or PR at https://github.com/Mullassery/PyDBTGuard
