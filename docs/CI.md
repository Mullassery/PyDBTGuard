# dbt manifest diff in CI

`pydbtguard diff` compares two `target/manifest.json` files and reports
added/removed/modified models plus tests attached to changed models. The
composite action in `.github/actions/dbt-diff` wires it into a PR check.

```yaml
name: dbt-manifest-diff
on: pull_request
jobs:
  diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          path: head
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.base_ref }}
          path: base
      # Build both dbt projects (or copy cached target/ artifacts) first.
      - uses: ./.github/actions/dbt-diff
        with:
          base-manifest: base/target/manifest.json
          current-manifest: head/target/manifest.json
          fail-on-change: "true"
```

Notes:

- The action builds PyDBTGuard from source (`maturin` + Rust) because the
  package is not yet on PyPI. Pin the action to a commit/tag once releases exist.
- `fail-on-change` is intentionally strict: any added/removed/modified model or
  test fails the job.
- You must produce `manifest.json` for both checkouts before this runs
  (`dbt parse`/`dbt build` in each project).
