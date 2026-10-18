"""Tests for dbt manifest comparison."""

import json

import pytest

from pydbtguard.manifest_diff import diff_manifests, render_text


def _manifest(mode: str, checksum: str = "a", columns=None):
    node = {
        "resource_type": "model",
        "name": "orders",
        "checksum": {"checksum": checksum},
        "columns": columns or {"id": {"name": "id"}},
    }
    test = {
        "resource_type": "test",
        "name": "unique_orders_id",
        "attached_node": "model.proj.orders",
        "depends_on": {"nodes": ["model.proj.orders"]},
    }
    nodes = {"model.proj.orders": node, "test.proj.unique_orders_id": test}
    if mode == "added":
        nodes["model.proj.new"] = {
            "resource_type": "model",
            "name": "new",
            "checksum": {"checksum": "n"},
        }
    return {"nodes": nodes}


def test_detects_added_modified_and_affected_tests():
    base = _manifest("base", checksum="a")
    current = _manifest("added", checksum="b", columns={"id": {"name": "id"}, "x": {"name": "x"}})
    diff = diff_manifests(base, current)

    assert diff.added_models == ["model.proj.new"]
    assert diff.modified_models == ["model.proj.orders"]
    assert diff.affected_tests == ["test.proj.unique_orders_id"]
    assert diff.has_changes


def test_identical_manifests_have_no_changes():
    manifest = _manifest("base")
    diff = diff_manifests(manifest, manifest)
    assert not diff.has_changes
    assert render_text(diff) == "No manifest changes."


def test_missing_nodes_is_rejected():
    with pytest.raises(ValueError, match="nodes"):
        diff_manifests({}, _manifest("base"))


def test_markdown_rendering_contains_sections():
    from pydbtguard.manifest_diff import render_markdown

    base = _manifest("base")
    current = _manifest("added", checksum="b")
    text = render_markdown(diff_manifests(base, current))
    assert "## PyDBTGuard manifest diff" in text
    assert "### Added models (1)" in text
    assert "`model.proj.new`" in text
