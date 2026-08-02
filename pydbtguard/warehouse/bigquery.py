from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from google.oauth2 import service_account

from .base import WarehouseConnector


class BigQueryConnector(WarehouseConnector):
    """BigQuery warehouse connector"""

    def __init__(
        self,
        project_id: str,
        credentials_path: Optional[str] = None,
        dataset_id: Optional[str] = None,
        **kwargs
    ):
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.dataset_id = dataset_id
        self.client = None

    def connect(self) -> None:
        """Establish BigQuery connection"""
        if self.credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path
            )
            self.client = bigquery.Client(project=self.project_id, credentials=credentials)
        else:
            self.client = bigquery.Client(project=self.project_id)

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        if not self.client:
            raise RuntimeError("Not connected to BigQuery")

        query_job = self.client.query(query)
        results = query_job.result()
        return [dict(row) for row in results]

    def get_table_stats(self, dataset: str, table: str) -> Dict[str, Any]:
        """Get table statistics"""
        if not self.client:
            raise RuntimeError("Not connected to BigQuery")

        table_ref = self.client.get_table(f"{self.project_id}.{dataset}.{table}")
        return {
            "row_count": table_ref.num_rows,
            "size_bytes": table_ref.num_bytes or 0,
            "created": table_ref.created.isoformat() if table_ref.created else None,
            "modified": table_ref.modified.isoformat() if table_ref.modified else None,
        }

    def disconnect(self) -> None:
        """Close connection"""
        if self.client:
            self.client.close()
            self.client = None
