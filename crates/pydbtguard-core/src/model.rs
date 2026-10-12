//! Typed, tolerant views over the real dbt artifacts this tool consumes.
//!
//! Everything here mirrors the actual on-disk schema written by `dbt parse`,
//! `dbt build`, `dbt docs generate`, and `dbt source freshness`:
//!
//! * `target/manifest.json`   -> [`Manifest`]
//! * `target/catalog.json`    -> [`Catalog`]
//! * `target/run_results.json`-> [`RunResults`]
//! * `target/sources.json`    -> [`SourcesArtifact`]
//!
//! All collections default to empty and all optional fields are `Option`, so a
//! manifest produced by any recent dbt version deserialises without error even
//! when a given key is absent.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Shared `metadata` block present in every dbt artifact.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct Metadata {
    #[serde(default)]
    pub dbt_schema_version: Option<String>,
    #[serde(default)]
    pub dbt_version: Option<String>,
    #[serde(default)]
    pub generated_at: Option<String>,
    #[serde(default)]
    pub project_name: Option<String>,
    #[serde(default)]
    pub adapter_type: Option<String>,
}

// ---------------------------------------------------------------------------
// manifest.json
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Manifest {
    #[serde(default)]
    pub metadata: Metadata,
    #[serde(default)]
    pub nodes: HashMap<String, Node>,
    #[serde(default)]
    pub sources: HashMap<String, Node>,
    #[serde(default)]
    pub exposures: HashMap<String, Node>,
    /// Real dependency map dbt itself writes: node id -> direct parents.
    #[serde(default)]
    pub parent_map: HashMap<String, Vec<String>>,
    /// Real dependency map dbt itself writes: node id -> direct children.
    #[serde(default)]
    pub child_map: HashMap<String, Vec<String>>,
}

impl Manifest {
    /// Fill in `unique_id` from the map key where dbt omitted it (older
    /// versions did not always repeat the id inside the node body).
    pub(crate) fn normalize(&mut self) {
        for (id, node) in self.nodes.iter_mut() {
            if node.unique_id.is_empty() {
                node.unique_id = id.clone();
            }
        }
        for (id, node) in self.sources.iter_mut() {
            if node.unique_id.is_empty() {
                node.unique_id = id.clone();
            }
        }
        for (id, node) in self.exposures.iter_mut() {
            if node.unique_id.is_empty() {
                node.unique_id = id.clone();
            }
        }
    }
    /// Every test node keyed by unique id.
    pub fn tests(&self) -> impl Iterator<Item = (&String, &Node)> {
        self.nodes.iter().filter(|(_, n)| n.resource_type == "test")
    }

    /// Every model node keyed by unique id.
    pub fn models(&self) -> impl Iterator<Item = (&String, &Node)> {
        self.nodes
            .iter()
            .filter(|(_, n)| n.resource_type == "model")
    }

    /// Direct children of a node from dbt's real `child_map`.
    pub fn children(&self, id: &str) -> &[String] {
        self.child_map.get(id).map(Vec::as_slice).unwrap_or(&[])
    }
}

/// A manifest node: model, test, snapshot, seed, exposure, source, ...
#[derive(Debug, Clone, Default, Deserialize)]
pub struct Node {
    #[serde(default)]
    pub unique_id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub resource_type: String,
    #[serde(default)]
    pub package_name: String,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub config: NodeConfig,
    #[serde(default)]
    pub depends_on: DependsOn,
    #[serde(default)]
    pub columns: HashMap<String, Column>,
    /// Present on every generic (schema) test; absent on singular tests.
    #[serde(default)]
    pub test_metadata: Option<TestMetadata>,
    /// Set on generic tests to the column under test.
    #[serde(default)]
    pub column_name: Option<String>,
    #[serde(default)]
    pub raw_code: Option<String>,
    #[serde(default)]
    pub compiled_code: Option<String>,
    /// Present on source nodes.
    #[serde(default)]
    pub source_name: Option<String>,
}

impl Node {
    pub fn is_test(&self) -> bool {
        self.resource_type == "test"
    }

    pub fn is_model(&self) -> bool {
        self.resource_type == "model"
    }

    pub fn is_exposure(&self) -> bool {
        self.resource_type == "exposure"
    }

    /// The real dbt test type. Generic tests carry `test_metadata.name`
    /// (`unique`, `not_null`, `accepted_values`, `relationships`, ...); a
    /// singular test has `test_metadata == null` but real code, so it is
    /// reported as `singular`. Anything else is `unknown`.
    pub fn test_type(&self) -> String {
        if let Some(meta) = &self.test_metadata {
            if !meta.name.is_empty() {
                return meta.name.clone();
            }
        }
        if self.raw_code.is_some() || self.compiled_code.is_some() {
            return "singular".to_string();
        }
        "unknown".to_string()
    }

    /// The model/source/seed a test is attached to: the first dependency that
    /// is not itself a test.
    pub fn attached_node(&self) -> Option<&str> {
        self.depends_on
            .nodes
            .iter()
            .find(|dep| !dep.starts_with("test."))
            .map(String::as_str)
    }

    /// Test severity from `config.severity` (defaults to `error` in dbt).
    pub fn severity(&self) -> String {
        self.config
            .severity
            .clone()
            .unwrap_or_else(|| "error".to_string())
            .to_lowercase()
    }

    /// The column under test, for generic tests. Prefers the explicit
    /// `column_name`, then `test_metadata.kwargs.column_name`.
    pub fn tested_column(&self) -> Option<String> {
        if let Some(col) = &self.column_name {
            if !col.is_empty() {
                return Some(col.clone());
            }
        }
        self.test_metadata
            .as_ref()
            .and_then(|m| m.kwargs.get("column_name"))
            .and_then(|v| v.as_str())
            .map(str::to_string)
    }
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct NodeConfig {
    #[serde(default)]
    pub materialized: Option<String>,
    #[serde(default)]
    pub severity: Option<String>,
    #[serde(default)]
    pub enabled: Option<bool>,
    #[serde(default)]
    pub tags: Option<serde_json::Value>,
    #[serde(default)]
    pub meta: serde_json::Value,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct DependsOn {
    #[serde(default)]
    pub nodes: Vec<String>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct TestMetadata {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub kwargs: serde_json::Value,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Column {
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub data_type: Option<String>,
}

// ---------------------------------------------------------------------------
// catalog.json
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Catalog {
    #[serde(default)]
    pub metadata: Metadata,
    #[serde(default)]
    pub nodes: HashMap<String, CatalogNode>,
    #[serde(default)]
    pub sources: HashMap<String, CatalogNode>,
}

impl Catalog {
    /// Look up a node by unique id in `nodes` then `sources`.
    pub fn get(&self, id: &str) -> Option<&CatalogNode> {
        self.nodes.get(id).or_else(|| self.sources.get(id))
    }
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct CatalogNode {
    #[serde(default)]
    pub unique_id: String,
    #[serde(default)]
    pub metadata: CatalogNodeMetadata,
    #[serde(default)]
    pub columns: HashMap<String, CatalogColumn>,
    #[serde(default)]
    pub stats: HashMap<String, CatalogStat>,
}

impl CatalogNode {
    /// Real row count from `stats.row_count`, if the warehouse populated it.
    pub fn row_count(&self) -> Option<u64> {
        self.stat_u64("row_count")
    }

    /// Real approximate table size in bytes from `stats.bytes`.
    pub fn bytes(&self) -> Option<u64> {
        self.stat_u64("bytes")
    }

    fn stat_u64(&self, key: &str) -> Option<u64> {
        self.stats.get(key).and_then(|s| stat_u64(&s.value))
    }
}

/// Catalog node `metadata` (table type, schema, database, ...).
#[derive(Debug, Clone, Default, Deserialize)]
pub struct CatalogNodeMetadata {
    #[serde(rename = "type", default)]
    pub kind: Option<String>,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct CatalogColumn {
    #[serde(default)]
    pub name: Option<String>,
    #[serde(rename = "type", default)]
    pub data_type: Option<String>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct CatalogStat {
    #[serde(default)]
    pub value: serde_json::Value,
}

/// Extract an unsigned integer from a catalog stat value, which dbt writes as
/// a JSON number, a numeric string, or occasionally `null`.
pub fn stat_u64(value: &serde_json::Value) -> Option<u64> {
    match value {
        serde_json::Value::Number(n) => n.as_u64().or_else(|| n.as_f64().map(|f| f as u64)),
        serde_json::Value::String(s) => s
            .parse::<u64>()
            .ok()
            .or_else(|| s.parse::<f64>().ok().map(|f| f as u64)),
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// run_results.json
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default, Deserialize)]
pub struct RunResults {
    #[serde(default)]
    pub metadata: Metadata,
    #[serde(default)]
    pub results: Vec<RunResult>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct RunResult {
    #[serde(default)]
    pub unique_id: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub execution_time: Option<f64>,
    #[serde(default)]
    pub failures: Option<u64>,
    #[serde(default)]
    pub message: Option<String>,
}

// ---------------------------------------------------------------------------
// sources.json
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default, Deserialize)]
pub struct SourcesArtifact {
    #[serde(default)]
    pub metadata: Metadata,
    #[serde(default)]
    pub results: Vec<SourceResult>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct SourceResult {
    #[serde(default)]
    pub unique_id: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub max_loaded_at: Option<String>,
    #[serde(default)]
    pub snapshotted_at: Option<String>,
    #[serde(default)]
    pub max_loaded_at_time_ago_in_s: Option<f64>,
    #[serde(default)]
    pub criteria: SourceCriteria,
}

/// `criteria` block within a source-freshness result.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct SourceCriteria {
    #[serde(default)]
    pub warn_after: Option<FreshnessThreshold>,
    #[serde(default)]
    pub error_after: Option<FreshnessThreshold>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct FreshnessThreshold {
    #[serde(default)]
    pub count: Option<f64>,
    #[serde(default)]
    pub period: Option<String>,
}

// ---------------------------------------------------------------------------
// run history (our own accumulated file, one JSON snapshot per line)
// ---------------------------------------------------------------------------

/// One real historical run, as persisted by the CLI's history store: a JSON
/// line like `{"generated_at": "...", "results": {"<test id>": "pass"}}`. The
/// `results` map is test unique id -> raw dbt status (`pass`, `fail`,
/// `error`, `skipped`, ...).
#[derive(Debug, Clone, Default, Deserialize)]
pub struct RunHistorySnapshot {
    #[serde(default)]
    pub generated_at: Option<String>,
    #[serde(default)]
    pub results: HashMap<String, String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_type_prefers_metadata_name() {
        let node = Node {
            test_metadata: Some(TestMetadata {
                name: "unique".into(),
                kwargs: serde_json::json!({"column_name": "id"}),
            }),
            ..Default::default()
        };
        assert_eq!(node.test_type(), "unique");
        assert_eq!(node.tested_column().as_deref(), Some("id"));
    }

    #[test]
    fn singular_test_detected_from_code() {
        let node = Node {
            raw_code: Some("select 1".into()),
            ..Default::default()
        };
        assert_eq!(node.test_type(), "singular");
    }

    #[test]
    fn attached_node_skips_test_dependencies() {
        let node = Node {
            depends_on: DependsOn {
                nodes: vec!["test.pkg.other".into(), "model.pkg.orders".into()],
            },
            ..Default::default()
        };
        assert_eq!(node.attached_node(), Some("model.pkg.orders"));
    }

    #[test]
    fn catalog_stats_parse_numbers_and_strings() {
        let node: CatalogNode = serde_json::from_value(serde_json::json!({
            "stats": {
                "row_count": {"value": 42},
                "bytes": {"value": "1024"}
            }
        }))
        .unwrap();
        assert_eq!(node.row_count(), Some(42));
        assert_eq!(node.bytes(), Some(1024));
    }
}
