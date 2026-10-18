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
`--fail-on-change` gates CI. Tests: 3 passed. Version `2.1.0`.

Still open: publishing to PyPI, wiring the diff into a PR-comment action, and
replacing the remaining stubbed commands.
