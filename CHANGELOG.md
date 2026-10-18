# Changelog

## [2.2.0] - 2026-10-19
### Added
- `pydbtguard diff --format markdown` for PR comments/job summaries. The
  composite CI action now uses Markdown. Tests cover the renderer.

## [2.1.0] - 2026-10-19
### Added
- `pydbtguard diff BASE_MANIFEST CURRENT_MANIFEST`: manifest-only
  `state:modified` view. Reports added/removed/modified models and
  added/removed tests, plus tests attached to or depending on changed models.
  `--fail-on-change` exits 1 for CI. No warehouse connection.
- Tests in `tests/test_manifest_diff.py`.

## [2.0.0] - 2026-10-12
### Added
- Full rewrite from scratch: hybrid Rust + Python (artifact-only)
- Core analysis: analyze, coverage, blast-radius, cost, history, freshness, drift
- Thin PyO3 bindings with JSON boundary
- Python CLI + artifact discovery + append-only history store
- Realistic dbt fixtures + Rust integration + Python e2e tests

### Changed
- Honest scoring: unknown → no fabricated probability/score
- Cost: only price adapters that bill per byte; null for unknown
- Lineage uses dbt child_map; coverage uses depends_on
- Version bumped to 2.0.0 everywhere

### Removed
- Dead/unused legacy modules, warehouse runtime queries from analysis path (left as non-goal)
