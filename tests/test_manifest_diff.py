"""Tests for dbt manifest comparison."""

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
    current = _manifest(
        "added", checksum="b", columns={"id": {"name": "id"}, "x": {"name": "x"}}
    )
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


def _lineage_manifest():
    nodes = {
        "model.proj.raw": {
            "resource_type": "model",
            "name": "raw",
            "checksum": {"checksum": "a"},
            "depends_on": {"nodes": []},
        },
        "model.proj.mid": {
            "resource_type": "model",
            "name": "mid",
            "checksum": {"checksum": "m"},
            "depends_on": {"nodes": ["model.proj.raw"]},
        },
        "model.proj.final": {
            "resource_type": "model",
            "name": "final",
            "checksum": {"checksum": "f"},
            "depends_on": {"nodes": ["model.proj.mid"]},
        },
        "test.proj.final_not_null": {
            "resource_type": "test",
            "name": "final_not_null",
            "attached_node": "model.proj.final",
            "depends_on": {"nodes": ["model.proj.final"]},
        },
        "test.proj.raw_unique": {
            "resource_type": "test",
            "name": "raw_unique",
            "attached_node": "model.proj.raw",
            "depends_on": {"nodes": ["model.proj.raw"]},
        },
    }
    return {"nodes": nodes}


def test_select_includes_downstream_models_and_tests():
    from pydbtguard.manifest_diff import select_tests

    base = _lineage_manifest()
    current = _lineage_manifest()
    current["nodes"]["model.proj.raw"]["checksum"]["checksum"] = "changed"

    selection = select_tests(base, current)
    assert "model.proj.raw" in selection.selected_models
    assert "model.proj.mid" in selection.selected_models
    assert "model.proj.final" in selection.selected_models
    assert "test.proj.raw_unique" in selection.selected_tests
    assert "test.proj.final_not_null" in selection.selected_tests


def test_select_can_exclude_downstream():
    from pydbtguard.manifest_diff import select_tests

    base = _lineage_manifest()
    current = _lineage_manifest()
    current["nodes"]["model.proj.raw"]["checksum"]["checksum"] = "changed"

    selection = select_tests(base, current, include_downstream=False)
    assert selection.selected_models == ["model.proj.raw"]
    assert "model.proj.mid" not in selection.selected_models
