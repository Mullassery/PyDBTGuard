from typing import Optional, Dict, Any
from .base import WarehouseConnector
from .snowflake import SnowflakeConnector
from .bigquery import BigQueryConnector


def warehouse_factory(
    warehouse_type: str, config: Dict[str, Any]
) -> WarehouseConnector:
    """Factory function to create warehouse connector"""
    if warehouse_type.lower() == "snowflake":
        return SnowflakeConnector(**config)
    elif warehouse_type.lower() == "bigquery":
        return BigQueryConnector(**config)
    else:
        raise ValueError(f"Unsupported warehouse type: {warehouse_type}")
