# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). No entries
are backfilled for history that predates this file — only changes made from
this point forward are recorded.

## [Unreleased]

### Fixed
- `crates/pydbtguard-core/src/manifest/parser.rs`: added missing
  `#[derive(Debug)]` on `ManifestParser` — `cargo test -p pydbtguard-core`
  previously failed to compile because of this.
- `.gitignore`: narrowed a bare `MANIFEST` pattern (intended for the Python
  sdist `MANIFEST` file) to `/MANIFEST` and `/MANIFEST.in`. On macOS
  (`core.ignorecase=true`), the old pattern also matched the directory
  `crates/pydbtguard-core/src/manifest/`, so `parser.rs` and `mod.rs` in
  that directory were never tracked in git — a fresh clone would not have
  compiled.
- `.gitignore`: stopped ignoring `Cargo.lock` and committed it, for
  reproducible builds.
- `pyproject.toml`: added `include = ["LICENSE"]` under `[tool.maturin]` so
  the sdist includes the license file.
- `cargo fmt -p pydbtguard-core` — applied (previously had unformatted code
  in `cost/mod.rs` and `impact/analyzer.rs`); `-- --check` now passes.
- `cargo clippy -p pydbtguard-core --all-targets -- -D warnings -A dead-code`
  — fixed 5 real lints so this now passes clean: two `or_insert_with(Vec::new)`
  → `or_default()` (`replay/engine.rs`, `patterns/detector.rs`), two
  unnecessary `as u64` casts on already-`u64` values (`replay/engine.rs`,
  `cost/calculator.rs`), and one `.len() > 0` → `!.is_empty()`
  (`impact/analyzer.rs`). `dead_code` is allowed deliberately for two
  fields that are genuinely unused today — tracked as disclosed tech debt
  in `ROADMAP_HONEST.md`, not suppressed.

### Changed
- License switched from a custom "Proprietary — free to use with
  attribution" license to Apache-2.0, matching current org-wide policy for
  github.com/Mullassery repositories. Updated `LICENSE`, `pyproject.toml`
  (`license`), and `Cargo.toml` (`license`).
- README rewritten for accuracy: removed "ML-based"/"predictive" marketing
  language that doesn't match the actual (fixed-weight heuristic)
  implementation, documented that no analysis command connects to a live
  warehouse, and added explicit "what's built but not verified / not
  working" sections. Removed links to `docs/GETTING_STARTED.md`,
  `docs/API.md`, `docs/ROADMAP.md`, `docs/INSTALLATION.md` — none of these
  files exist.
- Moved `docs/PHASE2_v0.2.md` and `docs/PHASE3_v0.3.md` to `docs/archive/`
  with an index and accuracy disclaimer (see `docs/archive/README.md`).

### Added
- `ROADMAP_HONEST.md` — full built/not-built/broken status.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`.
- `.github/ISSUE_TEMPLATE/bug_report.yml`,
  `.github/ISSUE_TEMPLATE/feature_request.yml`,
  `.github/pull_request_template.md`.
- `.github/workflows/ci.yml` — Python tests (3.10/3.11/3.12) run against the
  pure-Python package via `PYTHONPATH` (the maturin build is currently
  broken, see `ROADMAP_HONEST.md`, so the extension is not built in CI),
  `cargo test -p pydbtguard-core`, `cargo fmt -p pydbtguard-core -- --check`,
  `cargo clippy -p pydbtguard-core --all-targets -- -D warnings -A dead-code`,
  and a `security-audit` job (`pip-audit` + `cargo audit`, both
  `continue-on-error: true` for now — informational, not yet gating).
  Every command the workflow runs was verified locally in this pass (Python
  3.11.16, Rust 1.97.1) and passes except the two known Python test
  failures below, which the workflow will surface as a real (expected) CI
  failure until they're fixed. **The workflow itself has not yet run on
  GitHub** — these commits have not been pushed as of this entry, so no
  status badge was added to the README.
- `.github/dependabot.yml` — weekly updates for `pip`, `cargo`, and
  `github-actions` ecosystems.

### Known issues (see `ROADMAP_HONEST.md` for full detail)
- Package cannot currently be installed via `pip install -e .` /
  `pip install pydbtguard` — maturin build fails.
- `tests/test_phase2_analysis.py::TestBlastRadiusAnalyzer::test_impact_level_calculation`
  and
  `tests/test_phase3_analysis.py::TestDiagnosticsAnalyzer::test_identify_likely_causes`
  currently fail. Not fixed in this pass — root causes documented in
  `ROADMAP_HONEST.md`.
- `pydbtguard replay` returns fabricated data, not real historical analysis.
