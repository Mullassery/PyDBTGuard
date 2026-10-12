"""Shared fixtures for the PyDBTGuard Python test-suite.

Each test gets an isolated temporary dbt project whose ``target/`` directory
contains copies of the real artifact fixtures, so nothing is written back into
the repository.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

_ARTIFACTS = (
    "manifest.json",
    "catalog.json",
    "run_results.json",
    "sources.json",
)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A temp project with a populated ``target/`` directory."""
    target = tmp_path / "target"
    target.mkdir()
    for name in _ARTIFACTS:
        shutil.copy(FIXTURES / name, target / name)
    return tmp_path


@pytest.fixture
def project_with_history(project: Path) -> Path:
    """A temp project that also has an accumulated run history."""
    history_dir = project / ".pydbtguard"
    history_dir.mkdir()
    shutil.copy(FIXTURES / "run_history.jsonl", history_dir / "run_history.jsonl")
    return project
