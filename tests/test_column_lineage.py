"""Column lineage tests for dbt models."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("sqlglot")

from pydbtguard.column_lineage import analyze_manifest_column_lineage, analyze_model_sql


def test_model_columns_and_sources():
    lineage = analyze_model_sql(
        "model.proj.orders",
        "SELECT o.id AS order_id, o.total * 1.2 AS gross FROM raw.orders o",
    )
    assert lineage.outputs["order_id"] == ["o.id"]
    assert lineage.outputs["gross"] == ["o.total"]
    assert lineage.sources == ["o"]


def test_manifest_filtering(tmp_path):
    manifest = {
        "nodes": {
            "model.proj.a": {
                "resource_type": "model",
                "compiled_code": "SELECT id AS a_id FROM raw.a",
            },
            "model.proj.b": {
                "resource_type": "model",
                "compiled_code": "SELECT id AS b_id FROM raw.b",
            },
        }
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    results = analyze_manifest_column_lineage(path, model_filter="model.proj.a")
    assert len(results) == 1
    assert results[0].outputs == {"a_id": ["id"]}


def test_cte_columns_resolve_to_source_tables():
    lineage = analyze_model_sql(
        "model.proj.orders",
        "WITH base AS (SELECT id, total FROM raw.orders) "
        "SELECT b.id AS order_id FROM base b",
    )
    assert lineage.outputs["order_id"] == ["raw.orders.id"]
