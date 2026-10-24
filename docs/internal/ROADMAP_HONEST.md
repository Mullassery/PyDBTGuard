# Roadmap (Honest)

## Current state (v2.3.0)
- Artifact-only analysis: analyze/coverage/blast-radius/cost/history/freshness/drift
- Opt-in read-only local SQLite connector (`pydbtguard query`) via a plugin
  interface; live warehouses remain unwired
- Real behavior (no stubs, no fabricated scores when unknown)
- Hybrid Rust core + thin Python CLI + PyO3
- Fixtures + full test coverage passing

## Known technical debt
- pyo3 0.23 ABI3; extension-module requires maturin (not plain cargo build at workspace root)
- macOS lacks timeout utility (use Python subprocess timeout in tests if needed)
- No real dbt projects shipped with repo – fixtures are hand-authored

## Planned (near term)
- Publish wheels to PyPI (v2.0.0)
- Expand fixtures for more edge cases (singular tests, seeds/snapshots)
- Optional JSON schema validation for artifacts

## Non-goals
- Live warehouse queries
- ML training (keep simple, explainable statistics)
