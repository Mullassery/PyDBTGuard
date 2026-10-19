# Queue status — 2026-10-19

This file records what was shipped, what is blocked/failed, and what is rejected for this repository. It complements `AUDIT_FINDINGS.md`.

## Shipped
- Manifest diff, Markdown PR output, release workflow (2.2.0).
- Published `pydbtguard 2.2.0` to PyPI.

## Blocked / failed
- Verify the PR action on a real dbt project.

## Rejected / deferred
- Warehouse connectors now; static artifacts are the point.

## Policy

Any future feature or upgrade must check `AUDIT_FINDINGS.md` and this file before implementation. A blocked item is retried only when its external dependency is available; a rejected item needs new user evidence or a design change to reopen.
