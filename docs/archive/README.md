# Archived docs

Historical phase-implementation write-ups, kept for reference rather than
deleted. They describe the design intent for v0.2/v0.3 work at the time they
were written.

**Read [../../ROADMAP_HONEST.md](../../ROADMAP_HONEST.md) instead for
current, verified status.** Specific known inaccuracies in these archived
docs:

- **PHASE2_v0.2.md** describes the historical replay engine
  (`pydbtguard.analysis.replay`) as if it performs real historical analysis
  against warehouse snapshots. As of the 2026-09-19 audit, it generates
  100% synthetic/hardcoded data and never queries a warehouse — see
  ROADMAP_HONEST.md, Bucket 4. The blast-radius section describes impact
  mapping that, per the same audit, appears to walk the dependency graph in
  the wrong direction.
- **PHASE3_v0.3.md** describes diagnostics, optimization, and coverage-audit
  features that are largely real (backed by working code and passing
  tests), with one exception: the diagnostic "likely causes" heuristic has
  a real bug for the uniqueness-test case (checks the wrong condition) —
  see ROADMAP_HONEST.md, Bucket 3.
- Both docs describe these as versions "v0.2"/"v0.3" — `pyproject.toml` and
  `Cargo.toml` have remained at `0.1.0` throughout, so treat any version
  number in these documents as aspirational, not a real release marker.

| File | Topic |
|---|---|
| [PHASE2_v0.2.md](PHASE2_v0.2.md) | Historical replay, failure patterns, blast radius, cost analysis |
| [PHASE3_v0.3.md](PHASE3_v0.3.md) | Diagnostics, test optimization, coverage audit |
