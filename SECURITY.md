# Security Policy

## Reporting a vulnerability

Please report security issues privately by emailing
**mullassery@gmail.com** rather than opening a public GitHub issue. Include
enough detail to reproduce the issue. This is a solo-maintained project —
expect a best-effort response, not a formal SLA.

## Current known security-relevant issues (disclosed, not hidden)

These are tracked in detail in [ROADMAP_HONEST.md](ROADMAP_HONEST.md):

- `pydbtguard/warehouse/snowflake.py` (`SnowflakeConnector.get_table_stats`)
  builds a SQL query via unparameterized f-string interpolation of
  `schema`/`table` values. In the current codebase these values originate
  from the dbt manifest rather than direct end-user input, so practical risk
  is low today, but the query is not defended against a manifest containing
  unexpected content, and this pattern should not be copied elsewhere.
- No dependency lockfile exists for the Python side (`pyproject.toml` uses
  `>=` version constraints throughout), so installed dependency versions are
  not reproducible or pinned. `Cargo.lock` is committed for the Rust side.
- Warehouse credentials, if you configure them (Snowflake password, BigQuery
  service account key path), are passed through in memory to the respective
  official client library and are not logged by PyDBTGuard code as far as
  this repository's code was reviewed — but this has not been verified with
  a dedicated audit, and neither connector has been exercised against a real
  warehouse as part of any review to date.

## Scope

PyDBTGuard, in its current state, does not connect to any warehouse at
runtime from any CLI command (see README and ROADMAP_HONEST.md) — it only
parses a local `target/manifest.json` file. The warehouse connector code
exists but is not wired into any analysis path yet, so most warehouse
credential handling described above is currently inert/untested code, not
a live attack surface.

## Supported versions

There are no tagged releases yet; only `main` is supported.
