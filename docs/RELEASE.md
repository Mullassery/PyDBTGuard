# Releasing PyDBTGuard

The `Release` workflow builds wheels for Linux (x86_64/aarch64), macOS
(x86_64/arm64), Windows, and an sdist on a `v*` tag. The `publish` job uses
PyPI Trusted Publishing (OIDC), so it requires a one-time PyPI configuration:

1. Create the `pydbtguard` project on PyPI (or reserve the name).
2. Add a Trusted Publisher: owner `Mullassery`, repository `PyDBTGuard`,
   workflow `release.yml`, environment `pypi`.
3. Push a tag (`git tag v2.2.0 && git push origin v2.2.0`).

Until that setup exists, the build jobs still produce downloadable wheel
artifacts from a manual `workflow_dispatch` run; upload them with `twine`.
