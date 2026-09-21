import re
from typing import Dict, Any, List, Optional
import snowflake.connector

from .base import WarehouseConnector

_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def _validate_identifier(value: str) -> str:
    """Defense-in-depth check before interpolating an identifier into SQL.

    `schema`/`table` are expected to come from the dbt manifest, not
    end-user input, but this still guards against unexpected manifest
    content (e.g. a name containing a quote) reaching a raw SQL string.
    Not a substitute for real parameterization, which most SQL drivers
    don't support for identifiers (only for values) anyway.
    """
    if not _SAFE_IDENTIFIER_RE.match(value):
        raise ValueError(f"Unsafe warehouse identifier: {value!r}")
    return value


class SnowflakeConnector(WarehouseConnector):
    """Snowflake warehouse connector"""

    def __init__(
        self,
        account: str,
        user: str,
        password: str,
        database: str,
        schema: str,
        warehouse: str,
        **kwargs
    ):
        self.account = account
        self.user = user
        self.password = password
        self.database = database
        self.schema = schema
        self.warehouse = warehouse
        self.connection = None

    def connect(self) -> None:
        """Establish Snowflake connection"""
        self.connection = snowflake.connector.connect(
            account=self.account,
            user=self.user,
            password=self.password,
            database=self.database,
            schema=self.schema,
            warehouse=self.warehouse,
        )

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        if not self.connection:
            raise RuntimeError("Not connected to Snowflake")

        cursor = self.connection.cursor()
        cursor.execute(query)
        return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

    def get_table_stats(self, schema: str, table: str) -> Dict[str, Any]:
        """Get table statistics"""
        schema = _validate_identifier(schema)
        table = _validate_identifier(table)
        query = f"""
        SELECT
            row_count,
            bytes as size_bytes
        FROM {schema}.information_schema.tables
        WHERE table_schema = '{schema.upper()}' AND table_name = '{table.upper()}'
        """
        results = self.execute_query(query)
        return results[0] if results else {"row_count": 0, "size_bytes": 0}

    def disconnect(self) -> None:
        """Close connection"""
        if self.connection:
            self.connection.close()
