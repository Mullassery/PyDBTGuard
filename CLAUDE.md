# CLAUDE.md

## Commands
- Build extension: `maturin develop --offline`
- Rust tests: `cargo test -p pydbtguard-core`
- Python tests: `pytest`
- Lint: `ruff check pydbtguard tests`
- Format Rust: `cargo fmt --all`
- Clippy: `cargo clippy -p pydbtguard-core --lib --tests -- -D warnings`

## Architecture
- Rust core (`crates/pydbtguard-core`): models + analysis + api (JSON in/out)
- PyO3 bindings (`bindings/python`): `_core` module
- Python (`pydbtguard/`): `artifacts.py`, `cli.py`, `__init__.py`

## Principles
- Artifact-only; no warehouse connection
- Honest when unknown (no fake values)
- Real data from fixtures/tests; avoid stubs
- Thin boundary (JSON strings) for stability
