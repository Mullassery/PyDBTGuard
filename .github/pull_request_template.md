## What does this change?

<!-- Describe the change. Link any related issue. -->

## Why?

<!-- The problem this solves. -->

## Testing

- [ ] `PYTHONPATH=. pytest tests/` passes (or: explain which tests still fail and why, referencing ROADMAP_HONEST.md if it's a pre-existing failure)
- [ ] `cargo test -p pydbtguard-core` passes (if you touched Rust code)
- [ ] `cargo fmt --check` / `cargo clippy` clean (if you touched Rust code)

## Honesty checklist

- [ ] If this fixes something listed in `ROADMAP_HONEST.md`, I updated that file and `CHANGELOG.md`.
- [ ] If this adds a new feature, I did not describe it with unverified claims ("production-ready", "ML-based", etc.) — I stated what was actually tested and how.
- [ ] No fabricated/simulated data is returned silently where real data was expected (see `pydbtguard/analysis/replay.py` for the anti-pattern to avoid).
