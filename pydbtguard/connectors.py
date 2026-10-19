"""Warehouse connector plugins for PyDBTGuard.

The analysis engine itself remains artifact-only. This module adds an explicit,
opt-in way to run a small read-only query against a *local* database through a
plugin, used by the ``pydbtguard query`` CLI command.

Built-in connector: ``sqlite`` (stdlib ``sqlite3``, opened read-only). External
connectors declare themselves with::

    [project.entry-points."pydbtguard.warehouse_connectors"]
    my_connector = "my_package.connectors:MyConnector"

The entry point may be a ``WarehouseConnector`` subclass, an instance, or a
zero-argument factory returning one. Snowflake, BigQuery, Redshift, Postgres,
MySQL, and DuckDB are explicitly *not wired*: selecting one produces a clear
error instead of a fake connection or a stubbed success.
"""

from __future__ import annotations

import re
import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

ENTRY_POINT_GROUP = "pydbtguard.warehouse_connectors"

_SELECT_OR_WITH = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)

NOT_WIRED: dict[str, str] = {
    "snowflake": "no Snowflake driver or credentials are configured",
    "bigquery": "no BigQuery client or credentials are configured",
    "redshift": "no Redshift driver or credentials are configured",
    "postgres": "no Postgres driver or credentials are configured",
    "mysql": "no MySQL driver or credentials are configured",
    "duckdb": "the optional DuckDB driver is not bundled",
}


class ConnectorError(RuntimeError):
    """A connector could not be resolved, configured, validated, or queried."""


@dataclass(frozen=True)
class QueryValidation:
    """Result of validating a query without returning rows."""

    connector: str
    valid: bool
    message: str


class WarehouseConnector(ABC):
    """Read-only warehouse connector interface."""

    name: str = ""

    @abstractmethod
    def validate_query(
        self, config: Mapping[str, Any], sql: str
    ) -> QueryValidation:
        """Validate ``sql`` without returning rows."""

    @abstractmethod
    def fetch(
        self, config: Mapping[str, Any], sql: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return at most ``limit`` rows for a read-only query."""


def _read_only_sql(sql: str) -> str:
    statement = sql.strip()
    if statement.endswith(";"):
        statement = statement[:-1].rstrip()
    if not statement:
        raise ConnectorError("query is empty")
    if ";" in statement:
        raise ConnectorError("only one statement is allowed")
    if not _SELECT_OR_WITH.match(statement):
        raise ConnectorError("only read-only SELECT/WITH queries are allowed")
    return statement


def _database_path(config: Mapping[str, Any]) -> Path:
    raw = config.get("path", config.get("database"))
    if not isinstance(raw, str) or not raw:
        raise ConnectorError("sqlite connector requires a 'path' (or 'database')")
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise ConnectorError(f"sqlite database not found: {path}")
    return path


def _read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)


def _json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    return value


class SQLiteConnector(WarehouseConnector):
    """Read-only queries against a real local SQLite file.

    The database is opened with SQLite's ``mode=ro`` URI, and queries are
    restricted to a single ``SELECT``/``WITH`` statement before execution.
    """

    name = "sqlite"

    def validate_query(
        self, config: Mapping[str, Any], sql: str
    ) -> QueryValidation:
        statement = _read_only_sql(sql)
        path = _database_path(config)
        try:
            with _read_only_connection(path) as connection:
                connection.execute(f"EXPLAIN QUERY PLAN {statement}").fetchall()
        except sqlite3.Error as exc:
            return QueryValidation(self.name, False, str(exc))
        return QueryValidation(self.name, True, "query is valid and read-only")

    def fetch(
        self, config: Mapping[str, Any], sql: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ConnectorError("limit must be >= 1")
        validation = self.validate_query(config, sql)
        if not validation.valid:
            raise ConnectorError(f"query validation failed: {validation.message}")
        statement = _read_only_sql(sql)
        path = _database_path(config)
        try:
            with _read_only_connection(path) as connection:
                connection.row_factory = sqlite3.Row
                cursor = connection.execute(statement)
                return [
                    {key: _json_value(value) for key, value in dict(row).items()}
                    for row in cursor.fetchmany(limit)
                ]
        except sqlite3.Error as exc:
            raise ConnectorError(f"sqlite query failed: {exc}") from exc


_REGISTRY: dict[str, Any] = {"sqlite": SQLiteConnector}


def register_connector(name: str, factory: Any) -> None:
    """Register a connector class or zero-argument factory under ``name``."""
    if not isinstance(name, str) or not name:
        raise ConnectorError("connector name must be a non-empty string")
    if not (isinstance(factory, WarehouseConnector) or callable(factory)):
        raise ConnectorError(
            "connector factory must be a WarehouseConnector or callable"
        )
    _REGISTRY[name] = factory


def _entry_points() -> list[Any]:
    discovered = metadata.entry_points()
    if hasattr(discovered, "select"):
        return list(discovered.select(group=ENTRY_POINT_GROUP))
    return list(discovered.get(ENTRY_POINT_GROUP, []))


def _instantiate(obj: Any) -> WarehouseConnector:
    if isinstance(obj, WarehouseConnector):
        return obj
    if isinstance(obj, type) and issubclass(obj, WarehouseConnector):
        return obj()
    if callable(obj):
        candidate = obj()
        if isinstance(candidate, WarehouseConnector):
            return candidate
    raise ConnectorError(
        "connector entry point must be a WarehouseConnector subclass, an "
        "instance, or a zero-argument factory returning one"
    )


def get_connector(name: str) -> WarehouseConnector:
    """Resolve a local connector by name, or fail explicitly if not wired."""
    if name in _REGISTRY:
        return _instantiate(_REGISTRY[name])
    for entry_point in _entry_points():
        if entry_point.name == name:
            try:
                return _instantiate(entry_point.load())
            except Exception as exc:
                raise ConnectorError(
                    f"failed to load connector plugin {name!r}: {exc}"
                ) from exc
    if name in NOT_WIRED:
        raise ConnectorError(
            f"warehouse connector {name!r} is not wired ({NOT_WIRED[name]}). "
            "Only the local 'sqlite' connector is available; analysis remains "
            "artifact-only."
        )
    available = ", ".join(sorted(available_connectors())) or "(none)"
    raise ConnectorError(f"unknown connector {name!r}; available: {available}")


def available_connectors() -> dict[str, str]:
    """Return ``{name: origin}`` for built-in and discoverable local plugins."""
    available = {
        name: getattr(factory, "__module__", type(factory).__name__)
        for name, factory in _REGISTRY.items()
    }
    for entry_point in _entry_points():
        available.setdefault(entry_point.name, entry_point.value)
    return available


__all__ = [
    "ENTRY_POINT_GROUP",
    "NOT_WIRED",
    "ConnectorError",
    "QueryValidation",
    "SQLiteConnector",
    "WarehouseConnector",
    "available_connectors",
    "get_connector",
    "register_connector",
]
