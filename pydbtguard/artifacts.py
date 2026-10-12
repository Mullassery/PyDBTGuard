"""Locate and read the real dbt artifacts PyDBTGuard analyses.

Every input is a file dbt itself writes into ``target/``:

* ``manifest.json``    -- ``dbt parse`` / ``dbt build`` / ``dbt compile``
* ``catalog.json``     -- ``dbt docs generate``
* ``run_results.json`` -- ``dbt test`` / ``dbt build``
* ``sources.json``     -- ``dbt source freshness``

There is no warehouse connection here. The only persistent state PyDBTGuard
creates is the append-only run-history file under ``.pydbtguard/``, which
accumulates the real per-test outcomes from ``run_results.json`` across runs.
"""

from __future__ import annotations

import json
from pathlib import Path

HISTORY_DIR = ".pydbtguard"
HISTORY_FILE = "run_history.jsonl"

_PASS_FAIL = ("pass", "fail", "error", "skipped")


class ArtifactError(Exception):
    """Raised when a required dbt artifact is missing or unreadable."""


def target_dir(project_path: Path | str) -> Path:
    return Path(project_path) / "target"


def _read_required(path: Path, name: str, hint: str) -> str:
    if not path.exists():
        raise ArtifactError(f"{name} not found at {path}. {hint}")
    return path.read_text(encoding="utf-8")


def manifest_text(project_path: Path | str) -> str:
    return _read_required(
        target_dir(project_path) / "manifest.json",
        "manifest.json",
        "Run 'dbt parse' (or 'dbt build') first.",
    )


def run_results_text(project_path: Path | str) -> str:
    return _read_required(
        target_dir(project_path) / "run_results.json",
        "run_results.json",
        "Run 'dbt test' or 'dbt build' first.",
    )


def catalog_text(
    project_path: Path | str, catalog_path: Path | str | None = None
) -> str:
    """Catalog JSON text, or ``""`` when no catalog exists (it is optional)."""
    path = (
        Path(catalog_path)
        if catalog_path
        else target_dir(project_path) / "catalog.json"
    )
    return path.read_text(encoding="utf-8") if path.exists() else ""


def sources_text(
    project_path: Path | str, sources_path: Path | str | None = None
) -> str:
    """Source-freshness JSON text, or ``""`` when it does not exist."""
    path = (
        Path(sources_path)
        if sources_path
        else target_dir(project_path) / "sources.json"
    )
    return path.read_text(encoding="utf-8") if path.exists() else ""


class RunHistoryStore:
    """Append-only, de-duplicated record of real dbt test outcomes.

    Snapshot de-duplication uses the ``invocation_id`` dbt writes into every
    ``run_results.json``, so re-running ``pydbtguard analyze`` without a new
    ``dbt test`` does not double-count the same run.
    """

    def __init__(self, project_path: Path | str):
        self.project_path = Path(project_path)
        self.path = self.project_path / HISTORY_DIR / HISTORY_FILE

    def _snapshots(self) -> list[dict]:
        if not self.path.exists():
            return []
        snapshots = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                snapshots.append(json.loads(line))
        return snapshots

    def record_from_run_results(self, run_results_text: str) -> int:
        """Record a snapshot; return the number of test outcomes added.

        Only real test nodes are recorded, and only their real
        pass/fail/error/skipped status. Returns ``0`` when there is nothing new.
        """
        data = json.loads(run_results_text)
        meta = data.get("metadata", {}) or {}
        results: dict[str, str] = {}
        for node in data.get("results", []):
            unique_id = node.get("unique_id", "")
            status = node.get("status", "")
            if unique_id.startswith("test.") and status in _PASS_FAIL:
                results[unique_id] = status

        if not results:
            return 0

        snapshot = {
            "invocation_id": meta.get("invocation_id"),
            "generated_at": meta.get("generated_at"),
            "results": results,
        }

        existing = self._snapshots()
        if existing and self._is_duplicate(existing[-1], snapshot):
            return 0

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot, sort_keys=True) + "\n")
        return len(results)

    @staticmethod
    def _is_duplicate(previous: dict, current: dict) -> bool:
        prev_invocation = previous.get("invocation_id")
        curr_invocation = current.get("invocation_id")
        if prev_invocation and curr_invocation:
            return prev_invocation == curr_invocation
        return previous.get("results") == current.get("results")

    def history_text(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.exists() else ""

    def recorded_run_count(self) -> int:
        return len(self._snapshots())
