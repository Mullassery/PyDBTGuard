# Contributing to PyDBTGuard

This is a small, early-stage, mostly-solo-maintained project. Contributions
are welcome, but please read [ROADMAP_HONEST.md](ROADMAP_HONEST.md) first —
it lists the real, current bugs and gaps so you don't duplicate work or build
on top of something (like the historical-replay engine) that is known to be
fake/broken.

## Before you start

- **Packaging is currently broken** (`pip install -e .` fails — see
  ROADMAP_HONEST.md). Use the `PYTHONPATH=.` workflow described in the
  README's Installation section to run the CLI locally.
- Check open issues and `ROADMAP_HONEST.md`'s "warrants a dedicated
  follow-up session" list before picking something to work on — some known
  bugs are flagged as needing careful, focused fixes rather than quick
  patches.

## Development setup

```bash
git clone https://github.com/Mullassery/PyDBTGuard
cd PyDBTGuard
python3.10 -m venv .venv && source .venv/bin/activate
pip install click pydantic pyyaml sqlglot networkx pandas pyarrow tqdm tomli \
            snowflake-connector-python google-cloud-bigquery \
            pytest pytest-cov pytest-xdist black isort mypy
```

## Running tests

```bash
# Python
PYTHONPATH=. pytest tests/ -v

# Rust core (do NOT run plain `cargo test` at the workspace root — the
# bindings/python crate is a PyO3 extension-module cdylib and cannot be
# linked by cargo directly; it must go through maturin, which is currently
# broken — see ROADMAP_HONEST.md)
cargo test -p pydbtguard-core
```

As of this writing, 19/21 Python tests pass and 4/4 Rust core tests pass.
If your change causes previously-passing tests to fail, fix it before
opening a PR. If you fix one of the two currently-failing tests
(`test_impact_level_calculation`, `test_identify_likely_causes` — see
ROADMAP_HONEST.md for root cause analysis of both), say so explicitly in
your PR description.

## Code style

- Python: type hints, docstrings on public functions/classes, PEP 8.
- Rust: `cargo fmt` and `cargo clippy` clean.
- No fabricated test data or fake stub implementations that look real. If
  something is a placeholder, mark it clearly (e.g. `NotImplementedError`,
  or an explicit `# SIMULATED — see issue #N` comment), don't return
  plausible-looking fake numbers silently the way
  `pydbtguard/analysis/replay.py` currently does.

## Pull requests

- Keep PRs focused on one thing.
- Update `ROADMAP_HONEST.md` and `CHANGELOG.md` if your change fixes or adds
  something described there.
- Don't add marketing language ("production-ready", "enterprise-grade",
  "blazing fast") to the README or docs — describe what the code actually
  does and what's verified.

## Reporting bugs / requesting features

Use the GitHub issue templates
(`.github/ISSUE_TEMPLATE/bug_report.yml` and
`.github/ISSUE_TEMPLATE/feature_request.yml`).
