"""Column-level dbt model lineage with SQLGlot.

PyDBTGuard's manifest diff works at model level. This module adds a
column-level view of each model's compiled SQL so reviewers can see which
source columns feed an output column before changing a model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class LineageUnavailable(RuntimeError):
    """Raised when sqlglot is not installed."""


@dataclass
class ModelColumnLineage:
    model: str
    outputs: dict[str, list[str]] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "outputs": self.outputs,
            "sources": self.sources,
            "warnings": self.warnings,
        }


def _require_sqlglot():
    try:
        import sqlglot
        from sqlglot import exp
    except ImportError as exc:
        raise LineageUnavailable(
            "sqlglot is required for column lineage. Install with "
            '`pip install "pydbtguard[lineage]"`.'
        ) from exc
    return sqlglot, exp


def _cte_maps(statement, exp) -> dict[str, dict[str, list[str]]]:
    maps: dict[str, dict[str, list[str]]] = {}
    for cte in statement.find_all(exp.CTE):
        select = cte.this.find(exp.Select) if cte.this is not None else None
        if select is None:
            continue
        tables = [t.sql() for t in select.find_all(exp.Table)]
        base = tables[0] if tables else ""
        mapping: dict[str, list[str]] = {}
        for projection in select.expressions:
            output = projection.alias_or_name
            if output:
                columns = []
                for column in projection.find_all(exp.Column):
                    columns.append(
                        f"{base}.{column.name}"
                        if base and not column.table
                        else column.sql()
                    )
                mapping[output] = columns
        maps[cte.alias_or_name] = mapping
    return maps


def analyze_model_sql(
    model_name: str, sql: str, *, dialect: str | None = None
) -> ModelColumnLineage:
    sqlglot, exp = _require_sqlglot()
    parsed = sqlglot.parse(sql, read=dialect)
    result = ModelColumnLineage(model=model_name)
    for statement in parsed:
        if statement is None:
            continue
        select = statement.find(exp.Select)
        if select is None:
            result.warnings.append("statement is not a SELECT; skipped")
            continue
        cte_maps = _cte_maps(statement, exp)
        alias_to_cte = {
            table.alias_or_name: table.name
            for table in select.find_all(exp.Table)
            if table.name in cte_maps
        }
        for table in select.find_all(exp.Table):
            result.sources.append(table.alias or table.name)
        for projection in select.expressions:
            output = projection.alias_or_name
            if not output:
                result.warnings.append("projection without output name; skipped")
                continue
            resolved = []
            for column in projection.find_all(exp.Column):
                table = alias_to_cte.get(column.table, column.table)
                if table in cte_maps and column.name in cte_maps[table]:
                    resolved.extend(cte_maps[table][column.name])
                else:
                    resolved.append(column.sql(dialect=dialect))
            result.outputs[output] = sorted(set(resolved))
            if not resolved and projection.find(exp.Star):
                result.warnings.append(
                    f"{output}: wildcard projection has unknown columns"
                )
    result.sources = sorted(set(result.sources))
    return result


def analyze_manifest_column_lineage(
    manifest_path: str | Path,
    *,
    dialect: str | None = None,
    model_filter: str | None = None,
) -> list[ModelColumnLineage]:
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    nodes = data.get("nodes") or {}
    if not isinstance(nodes, dict):
        raise TypeError("manifest is missing a nodes object")
    results: list[ModelColumnLineage] = []
    for unique_id, node in sorted(nodes.items()):
        if not isinstance(node, dict) or node.get("resource_type") != "model":
            continue
        if model_filter and model_filter not in unique_id:
            continue
        sql = node.get("compiled_code") or node.get("raw_code") or node.get("raw_sql")
        if not sql:
            continue
        results.append(analyze_model_sql(unique_id, str(sql), dialect=dialect))
    return results


__all__ = [
    "LineageUnavailable",
    "ModelColumnLineage",
    "analyze_manifest_column_lineage",
    "analyze_model_sql",
]
