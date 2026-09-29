"""Real historical test-run tracking, from dbt's own real run_results.json artifact.

This exists to give `FailurePredictor` (the Rust engine in
`crates/pydbtguard-core/src/stats/predictor.rs`) something real to predict
from. Before this module, there was no real per-test pass/fail history
anywhere in this codebase -- `HistoricalReplayAnalyzer` (`replay.py`)
fabricates an entirely synthetic "fail every 10th day" pattern (see its own
docstring), and `ReliabilityAnalyzer.analyze()` never called the compiled
Rust prediction engine at all, so `FailurePredictor`/`ColumnFingerprint`
being importable didn't mean anything was actually predicted.

This module reads dbt's real `target/run_results.json` (written after every
real `dbt test`/`dbt build` invocation, with a real `status` per test node)
and appends each real run's outcomes to a local, persistent history file
(`.pydbtguard/run_history.jsonl` under the project root). Every subsequent
`pydbtguard analyze` run genuinely accumulates more real history -- there is
no fabricated data here, only what dbt itself actually reported. On a fresh
project (no accumulated history yet), failure history is simply short/empty,
which is an honest reflection of not having observed any real runs yet, not
a bug to paper over with synthetic data.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class RunHistoryStore:
    """Persists and reads real dbt test-run outcomes for a project."""

    def __init__(self, project_path: Path | str):
        self.project_path = Path(project_path)
        self.run_results_path = self.project_path / "target" / "run_results.json"
        self.history_dir = self.project_path / ".pydbtguard"
        self.history_path = self.history_dir / "run_history.jsonl"

    def record_current_run(self) -> int:
        """Read the real `target/run_results.json` (if present) and append
        its real per-test outcomes as one new line to the real local history
        file. Returns the number of real test results ingested (0 if no
        run_results.json exists yet -- e.g. only `dbt parse`, never `dbt
        test`, has been run in this project).
        """
        if not self.run_results_path.exists():
            return 0

        with open(self.run_results_path) as f:
            run_results = json.load(f)

        results = run_results.get("results", [])
        test_statuses: Dict[str, str] = {}
        for result in results:
            unique_id = result.get("unique_id")
            status = result.get("status")
            if unique_id is None or status is None:
                continue
            # Only test nodes are meaningful to FailurePredictor; dbt's
            # run_results.json unique_ids are prefixed by resource type
            # (e.g. "test.my_project...", "model.my_project...").
            if unique_id.startswith("test."):
                test_statuses[unique_id] = status

        if not test_statuses:
            return 0

        generated_at = run_results.get("metadata", {}).get("generated_at")
        snapshot = {"generated_at": generated_at, "results": test_statuses}

        self.history_dir.mkdir(parents=True, exist_ok=True)
        with open(self.history_path, "a") as f:
            f.write(json.dumps(snapshot) + "\n")

        return len(test_statuses)

    def get_failure_history(self, test_unique_id: str) -> List[bool]:
        """Real chronological pass/fail history for one test, from every
        real recorded run that included it (oldest first). `True` = that
        real run reported `"fail"` or `"error"`; `False` = `"pass"`.
        `"skipped"` runs are omitted (the test genuinely didn't execute,
        neither a real pass nor a real failure). Returns an empty list if
        no real history has been recorded for this test yet.
        """
        if not self.history_path.exists():
            return []

        history: List[bool] = []
        with open(self.history_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                snapshot = json.loads(line)
                status = snapshot.get("results", {}).get(test_unique_id)
                if status in ("fail", "error"):
                    history.append(True)
                elif status == "pass":
                    history.append(False)
                # "skipped" or missing (test didn't exist in that run): omit.
        return history

    def real_run_count(self) -> int:
        """How many real historical runs have been recorded, total."""
        if not self.history_path.exists():
            return 0
        with open(self.history_path) as f:
            return sum(1 for line in f if line.strip())
