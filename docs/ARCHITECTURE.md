# Architecture

## Overview
PyDBTGuard is a hybrid Rust + Python tool that validates dbt tests entirely from local dbt artifacts (manifest, catalog, run_results, sources) with no warehouse connection at analysis time.

- **Rust core (`crates/pydbtguard-core`)**: parsing, analysis, statistics, lineage, cost, drift. Pure logic, deterministic, no network.
- **Python bindings (`bindings/python`)**: thin PyO3 shim. Each function takes JSON strings and returns a JSON report string.
- **Python package (`pydbtguard/`)**: artifact I/O, history store, Click CLI.

## Flow
1. CLI reads `target/*.json` and `.pydbtguard/run_history.jsonl` via `pydbtguard.artifacts`.
2. Passes raw JSON to `_core` (PyO3). Core deserializes with tolerant models (`model.rs`).
3. Analysis produces typed reports; API wraps in `Envelope{version,kind,...}` and returns pretty JSON.
4. CLI renders human-readable output or passes `--json`.

## Core modules
- `model.rs` – typed views over real dbt schemas (manifest/catalog/run_results/sources/history)
- `stats.rs` – prediction from real pass/fail history (failure rate + confidence + risk)
- `history.rs` – accumulate/aggregate run history
- `coverage.rs` – test coverage gaps from manifest graph
- `lineage.rs` – blast radius via child_map
- `cost.rs` – per-scan cost from catalog bytes (adapter-aware, honest nulls)
- `freshness.rs` – reshape sources.json
- `drift.rs` – compare two catalogs
- `api.rs` – stable boundary

## Data shapes
Artifacts follow real dbt schemas. Tests attach via `depends_on.nodes` (attached model is first non-test). Coverage uses manifest edges; lineage uses `child_map`. Catalog stats parse number/string `value` for `row_count`/`bytes`.

## Testing
- Rust: 28 unit + 10 integration (over fixture artifacts) – all green
- Python: 18 CLI/artifacts tests – all green
