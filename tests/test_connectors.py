"""Tests for the warehouse-connector plugin interface and local SQLite connector.

Every test uses a real temporary SQLite database; no warehouse or network
connection is made.
"""

from __future__ import annotations

import json
import sqlite3

import pytest
from click.testing import CliRunner

from pydbtguard.cli import cli
from pydbtguard.connectors import (
    ENTRY_POINT_GROUP,
    NOT_WIRED,
    ConnectorError,
    SQLiteConnector,
    WarehouseConnector,
    available_connectors,
    get_connector,
    register_connector,
)


def run(*args: str):
    return CliRunner().invoke(cli, [str(arg) for arg in args])


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "warehouse.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
        )
        connection.executemany(
            "INSERT INTO customers (id, name, email) VALUES (?, ?, ?)",
            [
                (1, "Alice", "alice@example.com"),
                (2, "Bob", "bob@example.com"),
                (3, "Cara", "cara@example.com"),
            ],
        )
    return path


def test_sqlite_is_a_builtin_connector():
    assert "sqlite" in available_connectors()
    assert isinstance(get_connector("sqlite"), SQLiteConnector)
    assert ENTRY_POINT_GROUP == "pydbtguard.warehouse_connectors"


def test_sqlite_validates_a_read_only_query(database):
    connector = SQLiteConnector()
    validation = connector.validate_query(
        {"path": str(database)}, "SELECT id, name FROM customers"
    )

    assert validation.valid is True
    assert validation.connector == "sqlite"


def test_sqlite_reports_invalid_sql(database):
    validation = SQLiteConnector().validate_query(
        {"path": str(database)}, "SELECT * FROM missing_table"
    )

    assert validation.valid is False
    assert "no such table" in validation.message


def test_sqlite_fetches_real_rows_with_limit(database):
    rows = SQLiteConnector().fetch(
        {"path": str(database)},
        "SELECT id, name FROM customers ORDER BY id",
        limit=2,
    )

    assert rows == [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]


def test_sqlite_rejects_writes_and_multiple_statements(database):
    connector = SQLiteConnector()

    with pytest.raises(ConnectorError, match="read-only"):
        connector.validate_query({"path": str(database)}, "DELETE FROM customers")
    with pytest.raises(ConnectorError, match="one statement"):
        connector.validate_query(
            {"path": str(database)}, "SELECT 1; DELETE FROM customers"
        )


def test_missing_database_is_a_clear_error(tmp_path):
    with pytest.raises(ConnectorError, match="database not found"):
        SQLiteConnector().validate_query(
            {"path": str(tmp_path / "missing.db")}, "SELECT 1"
        )


def test_warehouses_are_explicitly_not_wired():
    assert "snowflake" in NOT_WIRED
    assert "bigquery" in NOT_WIRED
    with pytest.raises(ConnectorError, match="not wired"):
        get_connector("snowflake")


def test_query_cli_validates_only(database):
    result = run(
        "--json",
        "query",
        "--database",
        database,
        "--sql",
        "SELECT * FROM customers",
        "--validate-only",
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["connector"] == "sqlite"
    assert payload["validated"] is True
    assert "rows" not in payload


def test_query_cli_fetches_small_table(database):
    result = run(
        "--json",
        "query",
        "--database",
        database,
        "--sql",
        "SELECT id, name FROM customers ORDER BY id",
        "--limit",
        "2",
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["row_count"] == 2
    assert payload["rows"][1] == {"id": 2, "name": "Bob"}


def test_query_cli_rejects_a_write(database):
    result = run(
        "--json",
        "query",
        "--database",
        database,
        "--sql",
        "DELETE FROM customers",
    )

    assert result.exit_code == 1
    assert "read-only" in result.output


def test_connectors_cli_lists_available_and_not_wired():
    result = run("--json", "connectors")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    names = [connector["name"] for connector in payload["available"]]
    assert "sqlite" in names
    not_wired = {connector["name"] for connector in payload["not_wired"]}
    assert {"snowflake", "bigquery"} <= not_wired


class _StubConnector(WarehouseConnector):
    name = "stub"

    def validate_query(self, config, sql):
        from pydbtguard.connectors import QueryValidation

        return QueryValidation(self.name, True, "stub ok")

    def fetch(self, config, sql, limit=100):
        return [{"ok": True}]


def test_custom_connector_can_be_registered():
    register_connector("stub", _StubConnector)
    connector = get_connector("stub")

    assert isinstance(connector, _StubConnector)
    assert connector.fetch({}, "SELECT 1") == [{"ok": True}]


def test_entry_point_plugins_are_discovered(monkeypatch):
    class EntryPointConnector(_StubConnector):
        name = "from_entry_point"

    class FakeEntryPoint:
        name = "from_entry_point"
        value = "fake:EntryPointConnector"

        def load(self):
            return EntryPointConnector

    monkeypatch.setattr(
        "pydbtguard.connectors._entry_points", lambda: [FakeEntryPoint()]
    )

    connector = get_connector("from_entry_point")
    assert isinstance(connector, EntryPointConnector)
    assert available_connectors()["from_entry_point"] == "fake:EntryPointConnector"
