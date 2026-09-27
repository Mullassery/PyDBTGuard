"""Regression test found via real-world benchmarking against a real dbt
project (dbt-labs/jaffle-shop-classic, built with dbt-duckdb): every one of
20 real tests came back with type "unknown" from `pydbtguard analyze`.
Root cause: ManifestLoader._infer_test_type checked for an `attached_to`
key (never present on any real dbt manifest test node) and a `raw_sql` key
(renamed to `raw_code`/`compiled_code` in dbt core years ago) - both checks
were always false, so every real test fell through to "unknown" regardless
of its actual type.
"""
from pydbtguard.dbt.manifest import ManifestLoader


def test_infer_test_type_reads_real_generic_test_metadata():
    node = {
        "test_metadata": {
            "name": "unique",
            "kwargs": {"column_name": "customer_id"},
        },
    }
    assert ManifestLoader._infer_test_type(node) == "unique"


def test_infer_test_type_reads_real_singular_test():
    node = {"compiled_code": "select * from {{ ref('orders') }} where amount < 0"}
    assert ManifestLoader._infer_test_type(node) == "singular"


def test_infer_test_type_falls_back_to_unknown_for_real_edge_case():
    assert ManifestLoader._infer_test_type({}) == "unknown"
