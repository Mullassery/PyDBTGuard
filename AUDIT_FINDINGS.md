# Audit findings — 2026-10-19

This file records the repository-specific findings from the portfolio audit
conducted on 2026-10-19. It is documentation only; no code or release artifacts
were changed in this pass unless explicitly noted under "Implementation status".

Sources: the repository's own README/source/workflows, GitHub metadata and
Actions runs, PyPI metadata, and official competitor documentation. Claims are
marked as verified, inferred, or open questions. "Absent" means not found in the
inspected repository/docs, not proof that it cannot exist.

## What it is

Pre-deployment dbt test risk/impact/cost analysis from local `manifest.json` and `run_results.json`.

## Verified strengths

- Manifest/run_results parsing; risk scoring; historical failure probability; blast radius; coverage audit; cost; diagnostics; Rust failure predictor; 30 tests.
- Manifest-only analysis avoids warehouse credentials.

## Verified gaps and user-facing risks

- `pip install pydbtguard` returns 404 — the documented install path does not work.
- `optimize`, `pr-check`, `replay` are stubs/simulated; no warehouse connection; heuristics not ML; alpha.
- No GitHub release.

## Direct competitors

- dbt `state:modified`, Elementary, dbt-checkpoint, Recce/Datafold, Monte Carlo.

## Ranked next actions

- P1: publish PyPI + tag/release (S).
- P1: implement real `state:modified` diff + PR comment (M).
- P2: remove or clearly label stubbed commands (S).

## Do not build

- Warehouse connectors now; static artifacts are the point.

## Evidence gaps / validation needed

- No benchmark on real dbt projects; risk scores not validated against failures.

## Recommended disposition

Fix distribution and stubs first; otherwise freeze.

## Implementation status

Added `pydbtguard diff BASE CURRENT` (manifest-only `state:modified`) with
added/removed/modified models, added/removed tests, and affected-test mapping.
`--fail-on-change` gates CI and `--format markdown` feeds PR summaries. Tests:
4 passed. Version `2.2.0`. A composite GitHub Action + example is in
`.github/actions/dbt-diff` / `docs/CI.md`.

Added a release workflow (Linux/macOS/Windows/sdist + PyPI Trusted Publishing)
and `docs/RELEASE.md`. Still open: the actual PyPI Trusted Publisher setup,
verifying the PR action on a real dbt project, and replacing the remaining
stubbed commands.

Added a warehouse-connector plugin interface and a real local SQLite
connector in version `2.3.0`:

- Plugin interface: `pydbtguard.connectors.WarehouseConnector`, programmatic
  registration, and the `pydbtguard.warehouse_connectors` entry-point group.
- `pydbtguard query` validates or fetches a small read-only result from a local
  SQLite database; `pydbtguard connectors` lists plugins.
- Snowflake, BigQuery, Redshift, Postgres, MySQL, and DuckDB are explicitly not
  wired; the artifact-only analysis path is unchanged.
- Tests use temporary SQLite databases. No live-warehouse support is claimed.
