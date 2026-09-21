# ROADMAP_HONEST

Honest status of PyDBTGuard as of 2026-09-19. No hedge words. If something is
broken or fake, it's stated as broken or fake, not "planned" or "in progress."

This repo is a hybrid Rust + Python monorepo (`crates/pydbtguard-core` +
`bindings/python` + `pydbtguard/`). It reads a dbt project's static
`target/manifest.json` and scores tests with fixed-weight heuristics. It does
**not** connect to a live warehouse anywhere in the current code path, and it
is **not** ML-based anywhere in the current code path.

---

## Bucket 1: Built and tested by me, this pass

- `pydbtguard/analysis/coverage.py` (`CoverageAuditor`) — 10/10 unit tests
  pass (`tests/test_phase3_analysis.py::TestCoverageAuditor`).
- `pydbtguard/analysis/cost.py` (`CostAnalyzer`) — 3/3 unit tests pass
  (`tests/test_phase2_analysis.py::TestCostAnalyzer`). Arithmetic is real;
  inputs fed to it by the CLI are not (see Bucket 4).
- `pydbtguard/analysis/optimization.py` (`TestOptimizer`) — 3/3 unit tests
  pass (`tests/test_phase3_analysis.py::TestTestOptimizer`). Not reachable
  from any CLI command (see Bucket 3, `optimize`).
- `pydbtguard/dbt/manifest.py` (`ManifestLoader`) — exercised indirectly by
  every passing test above; loads and parses `target/manifest.json`
  correctly for the sample fixtures used.
- Rust core unit tests: `cargo test -p pydbtguard-core` → 4/4 pass
  (`stats::predictor`, `manifest::parser`, `lineage::graph`). Fixed one of
  these as part of this pass (see CHANGELOG) — it did not compile before.
- `pydbtguard analyze .` — ran directly via `PYTHONPATH=. python -m
  pydbtguard.cli analyze` against a hand-built manifest; produced scores
  without crashing. Not run against a real dbt project's manifest.

## Bucket 2: Built, not tested (by me or anyone, as far as this pass found)

- `pydbtguard/warehouse/snowflake.py` (`SnowflakeConnector`) — real code
  against the real `snowflake-connector-python` API. Zero unit tests. Never
  exercised against a real Snowflake account (no credentials available in
  this environment). SQL in `get_table_stats` is built via unparameterized
  f-string interpolation of `schema`/`table` (line ~48) — low practical risk
  since those values come from the dbt manifest rather than end-user input,
  but it is not defended against a manifest containing unexpected content.
- `pydbtguard/warehouse/bigquery.py` (`BigQueryConnector`) — same: real
  client library usage, zero unit tests, never exercised against a real
  BigQuery project.
- `pydbtguard/warehouse/factory.py` — trivial, untested, but low-risk
  (`if/elif/else` dispatch).
- `pydbtguard/analysis/diagnostics.py::DiagnosticsAnalyzer.diagnose_failure`
  (the public entry point, as opposed to its sub-methods) — only exercised
  through `test_diagnose_failure`, which passes; the sub-method
  `_identify_likely_causes` is separately broken (Bucket 3).
- Rust modules `impact/`, `cost/`, `patterns/`, `replay/` in
  `crates/pydbtguard-core/src/` (~700 LOC combined) — **zero unit tests**.
  Only `stats/predictor.rs`, `manifest/parser.rs`, and `lineage/graph.rs`
  have any tests at all.
- `bindings/python/src/lib.rs` (PyO3 `ColumnFingerprint`, `FailurePredictor`
  classes) — cannot currently be built as an installable extension (see
  Bucket 3), so it has never been tested from Python at all, not even
  manually.

## Bucket 3: CI errors / broken

- **Packaging is broken.** `pip install -e ".[dev]"` fails immediately:
  ```
  💥 maturin failed
  Caused by: Failed to parse Cargo.toml at /.../Cargo.toml
  Caused by: TOML parse error at line 1, column 1
  missing field `package`
  ```
  `pyproject.toml`'s `[tool.maturin]` has no `manifest-path`, so maturin
  looks for `Cargo.toml` beside `pyproject.toml` — the workspace root
  manifest, which has no `[package]` table. The actual buildable crate is
  `bindings/python/Cargo.toml`. **This needs a dedicated session** — beyond
  adding `manifest-path = "bindings/python/Cargo.toml"`, two more things
  need resolving together or the build will still be broken/misleading:
  1. `pyproject.toml` sets `module-name = "pydbtguard._core"`, but
     `bindings/python/src/lib.rs:64` declares `#[pymodule] fn pydbtguard(...)`
     — the Rust module function is named `pydbtguard`, not `_core`. These
     need to agree, and `pydbtguard` (the extension name) would then
     collide with the top-level pure-Python package of the same name unless
     deliberately renamed/namespaced.
  2. Nothing under `pydbtguard/` imports the compiled extension once it
     does build (grepped, zero references), so fixing the build alone
     doesn't make the "hybrid Rust+Python" architecture real — the Python
     analysis code would need to actually call into it.
- **`cargo build` / `cargo test` at the workspace root fail** with a linker
  error (`ld: symbol(s) not found for architecture arm64`, missing
  `_PyObject_GetItem` etc.) because `bindings/python` is a PyO3
  `extension-module` cdylib, which cargo cannot link directly on macOS —
  it must be built through `maturin`. This is expected PyO3 behavior, not a
  new bug, but it means `cargo test` (no `-p` flag) cannot be used as a
  smoke test for this repo; use `cargo test -p pydbtguard-core` instead. Not
  documented anywhere in the repo before this pass.
- **`crates/pydbtguard-core/src/manifest/parser.rs` and `mod.rs` were
  untracked in git** until this pass, due to a `.gitignore` bug: a bare
  `MANIFEST` pattern (line 30, meant to ignore Python's sdist `MANIFEST`
  file) also matched the directory `src/manifest/` because git's
  `core.ignorecase` defaults to true on macOS. **Fixed in this pass** —
  narrowed the pattern to `/MANIFEST` and `/MANIFEST.in`, and committed the
  two previously-invisible source files. Before this fix, a fresh clone
  from GitHub would have been missing two Rust source files that `lib.rs`
  declares as `pub mod manifest;` — the crate would not have compiled at
  all from a clean clone.
- **`Cargo.lock` was gitignored** — fixed in this pass (removed from
  `.gitignore`, committed the lockfile). A workspace producing a
  distributable extension module should commit its lockfile for
  reproducible builds; this is a recurring pattern flagged across this
  author's other Rust repos.
- **No CI existed at all before this pass**, despite `CLAUDE.md` claiming
  "GitHub Actions: `tests/`, `lint`, `build`" under its CI/CD section — that
  claim was false. Added `.github/workflows/ci.yml` in this pass (Python
  tests on 3.10/3.11/3.12, Rust `cargo test -p pydbtguard-core`, cargo
  fmt/clippy checks) and `.github/dependabot.yml` (pip, cargo,
  github-actions ecosystems). **Neither has run on GitHub yet** — these
  commits have not been pushed. No README badge has been added for CI,
  because there is no live workflow run to point it at yet; add one only
  after the workflow has actually run green on GitHub.
- **FIXED (quick-fix pass, 2026-09-21): 2 of 21 Python tests were failing,
  now 21/21 pass.**
  - `tests/test_phase2_analysis.py::TestBlastRadiusAnalyzer::test_impact_level_calculation`
    — was failing because blast-radius traversal walked the wrong graph
    direction. Fixed in `pydbtguard/analysis/blast_radius.py::_get_downstream_models`
    (now scans for nodes whose `depends_on.nodes` lists the source model,
    instead of following the source model's own upstream deps) and
    `_calculate_distance` (same inverted check). Also fixed a latent
    `None < 4` crash in `_generate_recommendations` that this change
    surfaced (see CHANGELOG).
  - `tests/test_phase3_analysis.py::TestDiagnosticsAnalyzer::test_identify_likely_causes`
    — `_identify_likely_causes` (`pydbtguard/analysis/diagnostics.py:73`)
    checked `"unique_id" in self._get_test_config(test_name)`, i.e. whether
    the literal string `"unique_id"` is a **key** in the test's config
    dict — it almost never will be. Fixed to check
    `"unique" in test_name.lower()`, matching the pattern used two lines
    later for `relationships`/`not_null`. The sibling `freshness` branch
    had the same class of bug and was fixed the same way.
- **pytest collection warning**: `pydbtguard/analysis/optimization.py:9`
  defines `class TestOptimizer`, which pytest tries to collect as a test
  class (name starts with `Test`) and warns because it has an `__init__`.
  Harmless today, but confusing and worth a rename in a future pass
  (touches `pydbtguard/analysis/__init__.py`, `tests/test_phase3_analysis.py`,
  and the class definition itself — three files, so deferred rather than
  done as a "small fix" here).

## Bucket 4: Features that don't work / aren't functional despite existing as code

- **`pydbtguard replay`** — does not perform historical analysis. The CLI
  command (`pydbtguard/cli.py`, `replay`) never calls
  `HistoricalReplayAnalyzer` at all; it parses the `--lookback` string and
  prints a placeholder message. The underlying class
  (`pydbtguard/analysis/replay.py`) that the CLI *should* be calling
  generates 100% synthetic data regardless of input — see README for the
  specific hardcoded values. There is no code path today that reads actual
  historical test-run data from anywhere.
- **`pydbtguard optimize`** (top-level CLI command) — `click.echo` only,
  does nothing (`pydbtguard/cli.py`).
- **`pydbtguard pr-check`** — `click.echo` only, does nothing
  (`pydbtguard/cli.py`). No GitHub API integration exists anywhere in the
  repo despite being referenced in `docs/ARCHITECTURE.md` and `README.md`'s
  original use-case example (`pydbtguard pre-check --fail-on-risky` — that
  exact flag/command combination does not exist in `cli.py` at all; the
  closest real command is the no-op `pr-check`).
- **`pydbtguard cost`** feeds every test a hard-coded
  `estimated_bytes_scanned: 1_000_000_000` (`pydbtguard/cli.py`, `cost`
  command) instead of any real scanned-bytes figure — the dollar figures
  it prints are not meaningful for a real project, only internally
  consistent with each other.
- **Blast radius mapping** — FIXED (2026-09-21), see Bucket 3. Traversal
  direction corrected; no longer returns empty/inverted results.
- **Warehouse-aware anything** — no CLI command actually opens a warehouse
  connection. `--warehouse snowflake|bigquery` is accepted by `analyze` and
  silently unused inside `ReliabilityAnalyzer.analyze()`
  (`pydbtguard/analysis/reliability.py` — `warehouse_type` parameter is
  never referenced in the method body).
- **"ML-based failure prediction"** (as described in the pre-audit README
  and `docs/ARCHITECTURE.md`) — does not exist. Both the Python
  (`reliability.py`) and Rust (`stats/predictor.rs`) implementations are
  fixed arithmetic over static inputs; `FailurePredictor::predict` in Rust
  literally returns the input failure rate as-is
  (`crates/pydbtguard-core/src/stats/predictor.rs:53`,
  `let failure_probability = pattern.failure_rate;`) with a confidence
  score based only on sample-count thresholds. No training, no model
  weights, no statistics beyond a ratio.
- **`docs/GETTING_STARTED.md`, `docs/API.md`, `docs/ROADMAP.md`,
  `docs/INSTALLATION.md`** — referenced by the pre-audit README's
  Documentation section. None of these files exist. Removed the dead links
  in this pass; not backfilled with real content (would need to describe a
  tool that mostly doesn't work yet as documented above).

---

## Technical debt (concrete, file:line)

**Warrants a dedicated follow-up session:**
- Packaging/build chain (`pyproject.toml` maturin config + module name
  mismatch + disconnected Rust core) — three interacting issues, see Bucket
  3. Fixing one without the others produces a build that "works" but is
  still not doing anything real.
- Blast-radius graph direction bug,
  `pydbtguard/analysis/blast_radius.py:67-121` (`_get_downstream_models`) —
  FIXED 2026-09-21, see Bucket 3 / CHANGELOG. Still worth a follow-up: add a
  regression test that asserts the *specific* right models are returned
  (not just that the field is populated), and consider whether
  `_calculate_distance` should compute real shortest-path distance instead
  of a 1-vs-2 approximation.
- `pydbtguard/analysis/diagnostics.py:73` heuristic bug — FIXED 2026-09-21
  (`unique`/`freshness` branches both now check `test_name.lower()`, see
  CHANGELOG). `relationships`/`not_null` branches already checked
  `test_name.lower()` correctly and needed no change.
- Rust modules with zero test coverage: `crates/pydbtguard-core/src/impact/`
  (218+128 LOC), `cost/` (111+108 LOC), `patterns/` (265+114 LOC),
  `replay/` (166+118 LOC) — roughly 700 LOC of untested Rust, none of it
  reachable from Python today anyway.
- `pydbtguard replay` CLI wiring — decide whether to (a) delete the
  simulated `HistoricalReplayAnalyzer` and the `replay` command until real
  warehouse-history querying exists, or (b) clearly gate it behind a
  `--simulate` flag if kept for demo purposes. Shipping it silently as-is
  (a command that looks like it analyzes real history but always returns
  the same synthetic curve) is the kind of thing that should not exist
  un-flagged in a tool people run against production systems.

**Minor / can be fixed opportunistically, not urgent:**
- `pydbtguard/analysis/optimization.py:9` — rename `TestOptimizer` to avoid
  the pytest collection name collision (see Bucket 3).
- `pydbtguard/cli.py` — every command wraps its whole body in
  `except Exception as e: click.echo(...); raise click.Exit(1)`, which
  swallows the original traceback; fine for a CLI but means bug reports
  from users will have very little to go on. Consider re-raising with
  `--verbose`.
- `crates/pydbtguard-core/src/stats/predictor.rs:44` — `lookback_days`
  field on `FailurePredictor` is never read (dead-code warning at build
  time).
- `crates/pydbtguard-core/src/replay/engine.rs:5` — `options` field on
  `HistoricalReplayEngine` is never read (dead-code warning at build time).
- `pydbtguard/warehouse/snowflake.py` `get_table_stats` — still builds SQL
  via f-string interpolation of `schema`/`table`. Added
  `_validate_identifier()` as defense-in-depth (2026-09-21): rejects any
  value that isn't a simple identifier before interpolation, even though
  current inputs are manifest-derived rather than user-supplied. Real
  parameterization of identifiers (as opposed to values) isn't supported by
  most driver bind-parameter APIs, so restructuring further than this was
  judged out of scope for a quick fix.
- Version drift: `pyproject.toml` / `Cargo.toml` both say `0.1.0` while
  `docs/archive/PHASE2_v0.2.md` and `PHASE3_v0.3.md` (moved to archive in
  this pass) describe v0.2.0/v0.3.0 as "Complete" in `CLAUDE.md`. Either the
  version was never bumped, or the "Complete" claims predate actual
  completion. Pick one number and make it true.
- `CLAUDE.md` "Coding Standards" section says "No comments: Use clear
  naming; add comments only for non-obvious logic" while the codebase
  itself has module/function docstrings throughout — the stated standard
  and the actual code disagree; not a bug, just an internal-doc
  inconsistency worth fixing next time `CLAUDE.md` is touched.

---

## Not built at all (no code exists)

- GitHub PR integration / gating (`pr-check` is a no-op stub, no GitHub API
  client anywhere in the repo).
- Slack/Teams integration.
- Dashboard UI.
- Redshift and Databricks connectors (README previously showed these as
  "🚧 v0.2" — no code for either exists anywhere in the repo).
- RBAC, audit logging, REST API, scheduled batch jobs (all listed under
  "v1.0" in `CLAUDE.md`) — none exist.
- Real historical-replay data ingestion (reading actual past test-run
  results from a warehouse, dbt Cloud, or anywhere else) — see Bucket 4.

---

## Dependency/security posture

- No secrets, credentials, or connection strings found committed in this
  repo (checked `pydbtguard/warehouse/`, root, and did a repo-wide search
  for `.env`/credential-shaped filenames — none found).
- Dependencies were not pinned to exact versions anywhere (`pyproject.toml`
  uses `>=` everywhere); no lockfile exists for the Python side (`Cargo.lock`
  now committed for the Rust side as of this pass, but there is no
  `requirements-lock` / `uv.lock` / `poetry.lock` equivalent for Python).
  `cargo audit` and a Python dependency audit were not run to completion as
  part of a CI job before this pass — a `security-audit` job was added to
  `.github/workflows/ci.yml` in this pass (see CHANGELOG) but, per the CI
  note above, has not yet run on GitHub.
