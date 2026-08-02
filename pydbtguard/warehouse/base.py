from abc import ABC, abstractmethod
from typing import Dict, Any, List


class WarehouseConnector(ABC):
    """Base class for warehouse connectors"""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to warehouse"""
        pass

    @abstractmethod
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query"""
        pass

    @abstractmethod
    def get_table_stats(self, schema: str, table: str) -> Dict[str, Any]:
        """Get statistics for a table (row count, bytes, etc.)"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection"""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
