"""Compare two dbt manifests without a warehouse.

This is the pre-deploy ``state:modified`` view PyDBTGuard needs: which models
were added/removed/changed, and which tests are attached to or depend on the
changed models. It reads artifacts only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set


def _load(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def _nodes(manifest: Dict[str, Any]) -> Dict[str, Any]:
    nodes = manifest.get("nodes")
    if not isinstance(nodes, dict):
        raise ValueError("manifest is missing a nodes object")
    return {key: value for key, value in nodes.items() if isinstance(value, dict)}


def _model_checksum(node: Dict[str, Any]) -> str:
    checksum = node.get("checksum")
    if isinstance(checksum, dict):
        return str(checksum.get("checksum") or "")
    return str(checksum or "")


def _columns(node: Dict[str, Any]) -> Dict[str, Any]:
    columns = node.get("columns")
    return columns if isinstance(columns, dict) else {}


@dataclass
class ManifestDiff:
    added_models: List[str] = field(default_factory=list)
    removed_models: List[str] = field(default_factory=list)
    modified_models: List[str] = field(default_factory=list)
    added_tests: List[str] = field(default_factory=list)
    removed_tests: List[str] = field(default_factory=list)
    affected_tests: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added_models
            or self.removed_models
            or self.modified_models
            or self.added_tests
            or self.removed_tests
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_changes": self.has_changes,
            "added_models": self.added_models,
            "removed_models": self.removed_models,
            "modified_models": self.modified_models,
            "added_tests": self.added_tests,
            "removed_tests": self.removed_tests,
            "affected_tests": self.affected_tests,
        }


def _is_model(node: Dict[str, Any]) -> bool:
    return node.get("resource_type") == "model"


def _is_test(node: Dict[str, Any]) -> bool:
    return node.get("resource_type") == "test"


def diff_manifests(base: Dict[str, Any], current: Dict[str, Any]) -> ManifestDiff:
    base_nodes = _nodes(base)
    current_nodes = _nodes(current)
    result = ManifestDiff()

    base_models = {k: v for k, v in base_nodes.items() if _is_model(v)}
    current_models = {k: v for k, v in current_nodes.items() if _is_model(v)}
    base_tests = {k: v for k, v in base_nodes.items() if _is_test(v)}
    current_tests = {k: v for k, v in current_nodes.items() if _is_test(v)}

    result.added_models = sorted(set(current_models) - set(base_models))
    result.removed_models = sorted(set(base_models) - set(current_models))
    result.added_tests = sorted(set(current_tests) - set(base_tests))
    result.removed_tests = sorted(set(base_tests) - set(current_tests))

    for unique_id in sorted(set(base_models) & set(current_models)):
        before = base_models[unique_id]
        after = current_models[unique_id]
        if _model_checksum(before) != _model_checksum(after):
            result.modified_models.append(unique_id)
        elif _columns(before) != _columns(after):
            result.modified_models.append(unique_id)

    changed: Set[str] = set(result.modified_models) | set(result.added_models)
    for test_id, test in sorted(current_tests.items()):
        attached = test.get("attached_node")
        depends = (test.get("depends_on") or {}).get("nodes") or []
        if attached in changed or any(dep in changed for dep in depends):
            result.affected_tests.append(test_id)

    return result


def render_text(diff: ManifestDiff) -> str:
    if not diff.has_changes:
        return "No manifest changes."
    lines = ["PyDBTGuard manifest diff", "=" * 27, ""]

    def section(title: str, values: List[str]) -> None:
        if not values:
            return
        lines.append(f"{title} ({len(values)}):")
        lines.extend(f"  - {value}" for value in values)
        lines.append("")

    section("Added models", diff.added_models)
    section("Removed models", diff.removed_models)
    section("Modified models", diff.modified_models)
    section("Added tests", diff.added_tests)
    section("Removed tests", diff.removed_tests)
    if diff.affected_tests:
        lines.append(f"Tests attached to changed models ({len(diff.affected_tests)}):")
        lines.extend(f"  ! {value}" for value in diff.affected_tests)
    return "\n".join(lines).rstrip()


def load_manifest(path: str) -> Dict[str, Any]:
    return _load(path)


def render_markdown(diff: ManifestDiff) -> str:
    if not diff.has_changes:
        return "No manifest changes."
    lines = ["## PyDBTGuard manifest diff", ""]

    def section(title: str, values: list[str], code: bool = False) -> None:
        if not values:
            return
        lines.append(f"### {title} ({len(values)})")
        for value in values:
            lines.append(f"- `{value}`" if code else f"- {value}")
        lines.append("")

    section("Added models", diff.added_models, code=True)
    section("Removed models", diff.removed_models, code=True)
    section("Modified models", diff.modified_models, code=True)
    section("Added tests", diff.added_tests, code=True)
    section("Removed tests", diff.removed_tests, code=True)
    section("Tests attached to changed models", diff.affected_tests, code=True)
    return "\n".join(lines).rstrip()
