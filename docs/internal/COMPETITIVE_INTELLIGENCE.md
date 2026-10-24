# Competitive intelligence in roadmap and upgrade work

**Policy date:** 2026-10-19

Competitive findings are an input to product decisions, not a one-off report.
Every pending roadmap item, new feature, and routine dependency upgrade should
check the repository's [`AUDIT_FINDINGS.md`](AUDIT_FINDINGS.md) before work
starts, and record the decision in the PR or changelog.

## Required check before building

1. **Read `AUDIT_FINDINGS.md`.** Find the relevant competitor row and the
   ranked next actions. If the finding is stale, update it with a dated source.
2. **Name the competitor and the user problem.** A feature is not justified by
   "competitor has it". State the workflow it unlocks, who needs it, and how
   often. Mark unverified demand as a hypothesis.
3. **Prefer reuse over new code.** Check whether an existing Mullassery repo
   already provides the capability (see `BUNDLES.md` in the profile repo and
   the bundle role file in this repo, when present). Typical reuse:
   - crawling/fetching/robots/SSRF → **MudFish**
   - architecture maps / PR diffs → **CodeAtlas**
   - data-quality contracts / validation → **StatGuardian**
   - token counting / cost tables → **PyTokenCalc**
   - dependency graph / advisories / SBOM → **PyDeepMesh**
   - segmentation / CLV / churn → **ClusterAudienceKit**
   - activation / lineage / PII → **PyReverseETL**
   - fleet state sync → **SyncFleet** (only after conflict resolution)
4. **Choose one disposition:** build, integrate, defer, or reject. Write it
   down. A rejection with a reason is a successful outcome.
5. **For routine upgrades**, check whether the upgrade closes a known
   competitor gap or breaks a differentiated capability. Run the tests that
   cover the affected path; do not merge a green build that silently changes a
   user-visible contract.

## PR / changelog checklist

- [ ] Competitor and source URL/date recorded (or "no direct competitor").
- [ ] User impact and frequency stated; unverified demand labelled.
- [ ] Reuse check done against sibling repos/bundles.
- [ ] Failure mode and rollback considered (especially auth, PII, cost).
- [ ] Docs/roadmap status updated honestly.
- [ ] Tests or a manual verification command included.

## Review cadence

- Refresh the competitor row when a release changes the capability.
- Re-check the full `AUDIT_FINDINGS.md` at least quarterly and before a major
  release.
- If a finding is wrong or stale, correct it in the same PR that relies on it.

## Non-goals

- Copying features for parity.
- Adding a dependency just because a competitor uses it.
- Treating star counts or download counts as proof of user need.

## OSS gap analysis — 2026-10-24

**What matters most here:** stay static, but close the loop. It cannot execute SQL/tests by design; the gaps to close are PR review comments and risk scoring validated against real dbt projects, not a warehouse connection.

Scope: open-source dbt validation, observability, and review tools. The
artifact-only constraint is a product boundary, not a defect. Dates and licenses
were checked against primary repositories on 2026-10-24.

### Comparable OSS projects

- **dbt-checkpoint** — `https://github.com/dbt-checkpoint/dbt-checkpoint`;
  MIT; v2.0.10 (2026-06-18). Pre-commit hooks validating dbt files and manifest
  metadata; no SQL execution.
- **Elementary** — `https://github.com/elementary-data/elementary`;
  Apache-2.0; v0.26.1 (2026-10-11). dbt-native test results, run history,
  alerts, lineage, and a report UI. Tests execute through dbt.
- **dbt-expectations** — `https://github.com/metaplane/dbt-expectations`;
  Apache-2.0; v0.10.10 (2025-12-02). A dbt test package that executes
  warehouse-side assertions; the original `calogica` repo is less active.
- **Recce** — `https://github.com/DataRecce/recce`; Apache-2.0; v1.69.1
  (2026-10-22). Local dbt PR review with lineage, impact assessment, and data
  diffs against two environments.

### Capability comparison

| Capability | PyDBTGuard | dbt-checkpoint | Elementary | dbt-expectations | Recce |
| --- | --- | --- | --- | --- | --- |
| Artifact-only, no warehouse access | Yes | Yes | No | No | No |
| Static manifest/run_results analysis | Yes | Partial | Partial | No | Yes |
| Test coverage audit | Partial | Yes | Partial | Partial | No |
| Failure or flaky-test risk scoring | Yes | No | No | No | No |
| Blast radius / lineage impact | Yes | Partial | Partial | No | Yes |
| Cost estimation | Yes | No | No | No | No |
| Executes SQL or dbt tests | No | No | Yes | Yes | Yes |
| Historical run trends | Partial | No | Yes | No | Partial |
| PR review surface | No | Partial | Partial | No | Yes |
| Web UI or dashboard | No | No | Yes | No | Yes |
| CI/pre-commit gate | Partial | Yes | Partial | No | Partial |

### Gaps that matter (ranked)

1. **No SQL or test execution.** PyDBTGuard cannot confirm that a model's SQL
   returns correct data; Elementary, dbt-expectations, and Recce can. Effort:
   L. **Reject** changing the artifact-only core; document an optional
   integration path instead.
2. **No automated PR review surface.** dbt-checkpoint owns pre-commit and Recce
   owns interactive PR impact review. A GitHub Action that runs `diff` and
   posts a markdown report is still missing. Effort: M. Build the Action and
   comment output, not a full GitHub App.
3. **Risk model is unvalidated.** Failure probability is an observed failure
   rate plus fixed confidence steps, and flaky detection is heuristic. There is
   no backtest against real dbt projects or calibration data. Effort: M. Build
   an evaluation harness before presenting scores as predictive.
4. **Coverage is model-level and shallow.** `coverage.rs` requires
   `unique`/`not_null` for all models and adds `relationships` for id-like
   columns; it does not reason about custom tests, `accepted_values`, exposures,
   or source freshness. Effort: M. Build deeper per-column coverage.
5. **dbt version and Fusion compatibility are unverified.** The model layer is
   tolerant of manifest differences, but CI does not exercise current dbt or
   dbt Fusion artifacts. Effort: M. Build a manifest-fixture matrix.
6. **No UI or visualization.** Recce and Elementary provide lineage and result
   views. Effort: L. Defer; the CLI/JSON contract is the current product.
7. **Docs and CLI drift.** README advertises `diagnose` and `coverage-audit`,
   while the implemented command is `coverage`; the audit also mentions
   `optimize`/`pr-check`/`replay` stubs absent from the current CLI. Effort: S.

### Where we are differentiated

- One artifact-only pass produces risk, flaky-test history, blast radius, and cost without warehouse credentials.
- A Rust core keeps analysis fast and the JSON boundary stable.
- It complements, rather than duplicates, pre-commit checks, observability, and interactive PR review.
- Apache-2.0 licensing and a local-first workflow suit regulated or offline environments.

### Disposition

**Build.** Prioritize the GitHub Action/PR report, risk calibration on real
projects, deeper coverage, and a dbt-version fixture matrix. Keep the
artifact-only boundary and reject warehouse execution as a core feature; defer
the UI until the CLI has validated demand.

### Sources

- https://github.com/dbt-checkpoint/dbt-checkpoint/releases/tag/v2.0.10
- https://raw.githubusercontent.com/dbt-checkpoint/dbt-checkpoint/main/LICENSE
- https://github.com/elementary-data/elementary/releases/tag/v0.26.1
- https://raw.githubusercontent.com/elementary-data/elementary/master/LICENSE
- https://github.com/metaplane/dbt-expectations/releases/tag/0.10.10
- https://github.com/DataRecce/recce/releases/tag/v1.69.1
- https://raw.githubusercontent.com/DataRecce/recce/main/LICENSE
- https://pypi.org/project/pydbtguard/2.4.2/
- Repository evidence: `README.md`, `AUDIT_FINDINGS.md`, `docs/ARCHITECTURE.md`, `ROADMAP_HONEST.md`, `coverage.rs`, `stats.rs`.
