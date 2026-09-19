use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestTest {
    pub unique_id: String,
    pub name: String,
    pub test_type: String,
    pub attached_node: String,
    pub fqn: Vec<String>,
    pub tags: Vec<String>,
    pub config: HashMap<String, serde_json::Value>,
    pub raw_sql: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestModel {
    pub unique_id: String,
    pub name: String,
    pub resource_type: String,
    pub fqn: Vec<String>,
    pub depends_on: Vec<String>,
    pub tags: Vec<String>,
    pub meta: HashMap<String, serde_json::Value>,
}

#[derive(Debug)]
pub struct ManifestParser;

impl ManifestParser {
    pub fn parse_manifest(manifest_content: &str) -> Result<ManifestData, serde_json::Error> {
        serde_json::from_str(manifest_content)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestData {
    pub metadata: ManifestMetadata,
    pub nodes: HashMap<String, serde_json::Value>,
    pub exposures: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestMetadata {
    pub dbt_schema_version: String,
    pub dbt_version: String,
    pub generated_at: String,
    pub invocation_id: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parser_initialization() {
        let parser = ManifestParser;
        assert!(format!("{:?}", parser).contains("ManifestParser"));
    }
}
