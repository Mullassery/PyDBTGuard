import json
from pathlib import Path
from typing import Dict, Any, Optional


class ManifestLoader:
    """Load and parse dbt manifest.json"""

    def __init__(self, project_path: Path | str):
        self.project_path = Path(project_path)
        self.manifest_path = self.project_path / "target" / "manifest.json"

    def load(self) -> Dict[str, Any]:
        """Load manifest.json from dbt target directory"""
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"manifest.json not found at {self.manifest_path}. "
                "Run 'dbt parse' first."
            )

        with open(self.manifest_path) as f:
            return json.load(f)

    def get_tests(self, manifest: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Extract all tests from manifest"""
        tests = []
        for node_id, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "test":
                tests.append(
                    {
                        "unique_id": node_id,
                        "name": node.get("name"),
                        "test_type": self._infer_test_type(node),
                        "attached_node": self._get_attached_node(node),
                        "fqn": node.get("fqn", []),
                        "tags": node.get("tags", []),
                        "config": node.get("config", {}),
                        "raw_sql": node.get("raw_sql"),
                    }
                )
        return tests

    def get_models(self, manifest: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Extract all models from manifest"""
        models = []
        for node_id, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") in ("model", "source"):
                models.append(
                    {
                        "unique_id": node_id,
                        "name": node.get("name"),
                        "resource_type": node.get("resource_type"),
                        "fqn": node.get("fqn", []),
                        "depends_on": node.get("depends_on", {}).get("nodes", []),
                        "tags": node.get("tags", []),
                        "meta": node.get("meta", {}),
                    }
                )
        return models

    @staticmethod
    def _infer_test_type(node: Dict[str, Any]) -> str:
        """Infer test type from node metadata"""
        attached_to = node.get("attached_to")
        if attached_to:
            return "generic"

        raw_sql = node.get("raw_sql", "")
        if raw_sql:
            return "singular"

        return "unknown"

    @staticmethod
    def _get_attached_node(node: Dict[str, Any]) -> Optional[str]:
        """Get the model this test is attached to"""
        depends_on = node.get("depends_on", {})
        nodes = depends_on.get("nodes", [])
        for dep in nodes:
            if not dep.startswith("test."):
                return dep
        return None
