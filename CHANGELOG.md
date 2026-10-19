# Changelog

## [Unreleased]
### Added
- Optional local DuckDB connector (`duckdb` extra) with real read-only
  validation and fetches against temporary DuckDB databases.
- Optional Postgres connector skeleton (`postgres` extra, `psycopg`) for a
  local server. Tests require `PYDBTGUARD_TEST_POSTGRES_DSN` and skip with an
  explicit reason when no server or driver is available.
- `pydbtguard query --warehouse duckdb|postgres` plus `--dsn`/`DATABASE_URL`
  for Postgres. The existing `--connector`/`--database` SQLite path remains.
- Tests cover real DuckDB reads and query validation; Postgres tests never fake
  success and skip cleanly.

### Changed
- `pydbtguard connectors` now lists DuckDB and Postgres as available optional
  plugins; Snowflake, BigQuery, Redshift, and MySQL remain explicitly unwired.

## [2.3.0] - 2026-10-20
### Added
- Warehouse-connector plugin interface (`pydbtguard.connectors.WarehouseConnector`)
  with programmatic registration and the `pydbtguard.warehouse_connectors`
  entry-point group.
- Real local SQLite connector (stdlib `sqlite3`, opened read-only) used by the
  new `pydbtguard query` command to validate a query or fetch a small table.
- `pydbtguard connectors` lists available local plugins and explicitly unwired
  warehouses (Snowflake, BigQuery, Redshift, Postgres, MySQL, DuckDB).
- Tests use temporary SQLite databases; live warehouses remain unwired.

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
