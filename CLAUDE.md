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
├── crates/pydbtguard-core/                 # Core library
│   └── src/
│       ├── stats/                          # Statistical analysis
│       │   ├── fingerprint.rs              # Column fingerprinting (nulls, cardinality, distribution)
│       │   └── predictor.rs                # ML failure prediction model
│       ├── lineage/                        # Impact analysis
│       │   └── graph.rs                    # DAG for blast radius
│       └── manifest/                       # dbt manifest parsing
│           └── parser.rs
├── bindings/python/                        # PyO3 bindings
│   └── src/lib.rs                         # Python-exported types
├── pydbtguard/                            # Python package
│   ├── cli.py                             # Click CLI commands
│   ├── dbt/                               # dbt integration
│   │   └── manifest.py                    # Manifest loader
│   ├── warehouse/                         # Warehouse connectors
│   │   ├── base.py                        # Base connector interface
│   │   ├── snowflake.py
│   │   ├── bigquery.py
│   │   └── factory.py
│   ├── analysis/                          # Analysis engines
│   │   └── reliability.py                 # Reliability scoring
│   ├── models/                            # Data models
│   │   └── schemas.py
│   └── __init__.py
├── tests/                                 # Test suite
├── docs/                                  # Documentation
└── examples/                              # Sample projects
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

### Manifest
- Loaded from `target/manifest.json` (via `dbt parse`)
- Nodes: models, tests, sources, snapshots, exposures
- Tests: unique_id, fqn, attached_node, raw_sql, config

### Warehouse Connectors
- Abstract interface: `connect()` → `execute_query()` → results
- Context manager support: `with WarehouseConnector(...) as conn:`
- Per-warehouse: authentication, query syntax, metadata schema

### Reliability Analysis
- Input: test definition + warehouse metadata
- Output: 0-100 score + risk level (STABLE / AT_RISK / DANGEROUS)
- Factors: test type, failure history, cost, blast radius

## CLI Commands (v0.1)

```bash
pydbtguard analyze .              # Main command: reliability scoring
pydbtguard replay --lookback 180d # Historical replay (v0.2)
pydbtguard simulate               # Failure simulation (v0.3)
pydbtguard pr-check               # GitHub PR integration (v0.4)
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

## Next Phases

- **v0.2**: Historical replay + blast radius mapping
- **v0.3**: Failure simulation + diagnostic plans
- **v0.4**: Dashboard + PR integration
- **v1.0**: Enterprise features, multi-warehouse lineage

## Contact

Questions? File an issue or PR at https://github.com/Mullassery/PyDBTGuard
