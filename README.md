# PyDBTGuard

Analyzes a dbt project's `manifest.json` to flag which tests look risky, map
which downstream models a failing test would affect, and estimate test
execution cost — all from static dbt metadata.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)

**Status: early / experimental.** Packaging is currently broken (see below),
one of the headline features (historical replay) returns fabricated data,
and the blast-radius direction is inverted. Do not use this for anything
that matters yet. Read "What's built but not verified / not working" before
you install it.

---

## Problem

dbt tests fail unpredictably, and dbt itself gives you no signal on:
- which tests are likely to break before you run them,
- what breaks downstream (dashboards, other models) if a given model's test fails,
- which tests are expensive to run relative to the value they provide.

## Solution

PyDBTGuard reads a dbt project's compiled `target/manifest.json` (the file
`dbt parse` / `dbt compile` produces) and applies rule-based heuristics over
that static metadata — model/test names, `depends_on` graph edges, configured
freshness SLAs — to produce a reliability score, a dependency-graph impact
estimate, and a cost estimate per test.

**Important — this is metadata-only today, not a live-warehouse tool.**
PyDBTGuard does not currently query Snowflake, BigQuery, or any warehouse at
runtime. Real `SnowflakeConnector` / `BigQueryConnector` classes exist
(`pydbtguard/warehouse/snowflake.py`, `pydbtguard/warehouse/bigquery.py`) using
the real `snowflake-connector-python` / `google-cloud-bigquery` client
libraries, but no analysis command actually instantiates or calls them yet —
`--warehouse` is accepted as a CLI flag and then ignored. Everything you get
today comes from parsing the manifest JSON, not from live table stats, query
history, or execution logs.

**No machine learning.** Despite "predictive"/"ML-based" language in earlier
drafts of this README, the scoring is fixed-weight arithmetic (a base score
plus/minus fixed penalties keyed on substrings like `"unique"` in a test
name) — see `pydbtguard/analysis/reliability.py`. There is no trained model,
no historical training data, and no statistical inference.

## Use Cases (once the packaging bug below is fixed)

```bash
# Score every test in a dbt project from its manifest
pydbtguard analyze .

# Save the JSON report
pydbtguard analyze . --output report.json
```

Output is a reliability score (0-100) and risk level (`STABLE` / `AT_RISK` /
`DANGEROUS`) per test, derived purely from test name/type/config in the
manifest — not from any observed pass/fail history.

## Installation

**Currently broken.** `pip install -e ".[dev]"` fails immediately with:

```
💥 maturin failed
Caused by: Failed to parse Cargo.toml at .../Cargo.toml
Caused by: TOML parse error at line 1, column 1
missing field `package`
```

Root cause: `pyproject.toml` uses the `maturin` build backend with no
`manifest-path` set, so maturin looks for `Cargo.toml` next to
`pyproject.toml` — but that file is a Cargo **workspace** manifest (no
`[package]` section); the actual Python-extension crate is at
`bindings/python/Cargo.toml`. This has not been verified to work via `pip
install pydbtguard` or `pip install -e .` in this pass — see
[ROADMAP_HONEST.md](ROADMAP_HONEST.md) for the full breakdown and what a fix
needs to also address (module-name mismatch, unused Rust core).

To run the Python CLI logic without building the Rust extension (nothing in
the `pydbtguard` package currently imports the compiled extension, so this
works):

```bash
git clone https://github.com/Mullassery/PyDBTGuard
cd PyDBTGuard
python3.10 -m venv .venv && source .venv/bin/activate
pip install click pydantic pyyaml sqlglot networkx pandas pyarrow tqdm tomli \
            snowflake-connector-python google-cloud-bigquery
PYTHONPATH=. python -m pydbtguard.cli analyze /path/to/dbt/project
```

This is how the CLI was actually exercised for this audit — it was not
installed as a package.

## What's working now (verified by me, this pass)

- **`pydbtguard analyze .`** — loads `target/manifest.json`, extracts
  tests/models, computes a heuristic 0-100 score per test. Verified by
  running it directly against a sample manifest via `PYTHONPATH=.`
  (see Installation above); not tested against a real dbt project's manifest.
- **`pydbtguard coverage-audit`** — real logic in
  `pydbtguard/analysis/coverage.py`, walks manifest nodes and flags missing
  test types per model, prioritized. 10/10 of its unit tests pass.
- **`pydbtguard diagnose --test <name>`** — real logic in
  `pydbtguard/analysis/diagnostics.py`; produces plausible-looking diagnostic
  SQL templates from name/config pattern matching. 2/3 of its unit tests
  pass — one is currently failing (see below).
- **`pydbtguard cost`** — real arithmetic in `pydbtguard/analysis/cost.py`
  over test metadata; all its unit tests pass. Note the CLI feeds it a
  hard-coded `estimated_bytes_scanned: 1_000_000_000` for every single test
  (`pydbtguard/cli.py`, `cost` command) rather than any real scanned-bytes
  figure, so the dollar amounts are not meaningful yet.
- **Rust core unit tests**: `cargo test -p pydbtguard-core` — 4/4 pass
  (fixed one broken test as part of this pass, see CHANGELOG).
- **Python test suite**: `PYTHONPATH=. pytest tests/` — 19/21 pass, 2 fail
  (see "Not working" below). Run against Python 3.11 (the repo declares
  `requires-python = ">=3.10"`; the machine's default `python3` was 3.9).

## What's built but not verified / not working

- **Historical replay (`pydbtguard replay`, `pydbtguard.analysis.replay`) is
  fabricated data, not analysis.** `HistoricalReplayAnalyzer._simulate_replay`
  (`pydbtguard/analysis/replay.py:46-94`) hardcodes "fail every 10th day" and
  `calculate_test_reliability_curve` (line 157) returns
  `0.85 + (i / lookback_days) * 0.1` regardless of the test or warehouse
  passed in. It never queries a warehouse — the method's own comment says
  "In production, this would... For now, simulate." The CLI's `replay`
  command (`pydbtguard/cli.py`, `replay`) doesn't even call this class; it
  just does date-string math and prints "Results would show: ...". This
  feature does not work.
- **Blast radius direction looks inverted.** `_get_downstream_models`
  (`pydbtguard/analysis/blast_radius.py:67-110`) walks
  `node["depends_on"]["nodes"]` — a dbt node's *upstream* dependencies — and
  labels the result "affected"/downstream models. In dbt, `depends_on.nodes`
  points at ancestors, not descendants, so this appears to walk the wrong
  direction. This is consistent with a real, currently-failing test:
  `tests/test_phase2_analysis.py::TestBlastRadiusAnalyzer::test_impact_level_calculation`.
  Not fixed in this pass — needs a dedicated look at graph direction and the
  fixture semantics.
- **`pydbtguard optimize` and `pydbtguard pr-check` (top-level CLI
  commands) are stubs** — each is a single `click.echo(...)` line
  (`pydbtguard/cli.py`) and does nothing. Confusingly, a real, more complete
  `TestOptimizer` class exists at `pydbtguard/analysis/optimization.py` but
  is never wired into the `optimize` CLI command.
- **Warehouse connectors untested.** `SnowflakeConnector` and
  `BigQueryConnector` (`pydbtguard/warehouse/`) are written against the real
  client libraries but have no unit tests and were not exercised against a
  real warehouse in this pass (no credentials available). Also not
  parameterized: `SnowflakeConnector.get_table_stats`
  (`pydbtguard/warehouse/snowflake.py`) builds SQL via an f-string
  interpolating `schema`/`table` directly.
- **The Rust core is architecturally disconnected from the Python CLI.**
  `bindings/python/src/lib.rs` exposes `ColumnFingerprint` and
  `FailurePredictor` via PyO3, but nothing under `pydbtguard/` imports the
  compiled extension (`pydbtguard._core`) — confirmed by grep, zero
  references. All current analysis is pure Python. The "hybrid Rust+Python"
  architecture described in `docs/ARCHITECTURE.md` is not wired up yet.
- **Package has never actually been built/published successfully as far as
  this pass could verify** — see Installation above. The `pyproject.toml`
  and `Cargo.toml` both report version `0.1.0` even though
  `docs/archive/PHASE2_v0.2.md` / `PHASE3_v0.3.md` describe v0.2/v0.3
  features as "Complete" — the version number was never bumped for that
  work.

Full bug list, technical debt, and what's simply not built at all:
[ROADMAP_HONEST.md](ROADMAP_HONEST.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap / honest status](ROADMAP_HONEST.md)
- [Archived phase docs](docs/archive/README.md) (v0.2/v0.3 feature write-ups, kept for reference — contain claims this audit found to be inaccurate; read the disclaimer at the top of each)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Author

Georgi Mammen Mullassery
