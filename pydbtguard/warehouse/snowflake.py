from typing import Dict, Any, List, Optional
import snowflake.connector

from .base import WarehouseConnector


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
