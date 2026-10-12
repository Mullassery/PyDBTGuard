//! Schema and volume drift between two real `catalog.json` snapshots.
//!
//! Capturing `target/catalog.json` after successive `dbt docs generate`
//! runs gives real, warehouse-sourced table statistics over time. Comparing
//! two of those snapshots yields genuine row-count/byte growth and real
//! column additions, removals, and type changes — no warehouse connection
//! required at analysis time.

use crate::model::Catalog;
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct ColumnTypeChange {
    pub column: String,
    pub old_type: Option<String>,
    pub new_type: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct NodeDrift {
    pub unique_id: String,
    pub row_count_old: Option<u64>,
    pub row_count_new: Option<u64>,
    pub row_delta: Option<i64>,
    pub row_delta_percent: Option<f64>,
    pub bytes_old: Option<u64>,
    pub bytes_new: Option<u64>,
    pub bytes_delta: Option<i64>,
    pub added_columns: Vec<String>,
    pub removed_columns: Vec<String>,
    pub type_changes: Vec<ColumnTypeChange>,
}

#[derive(Debug, Clone, Serialize)]
pub struct DriftReport {
    pub nodes_compared: usize,
    pub nodes_with_drift: usize,
    pub drift: Vec<NodeDrift>,
}

fn signed_delta(old: Option<u64>, new: Option<u64>) -> Option<i64> {
    match (old, new) {
        (Some(o), Some(n)) => Some(n as i64 - o as i64),
        _ => None,
    }
}

fn percent_delta(old: Option<u64>, new: Option<u64>) -> Option<f64> {
    match (old, new) {
        (Some(o), Some(n)) if o > 0 => Some((n as f64 - o as f64) / o as f64 * 100.0),
        _ => None,
    }
}

/// Compare two catalog snapshots and report every node whose row count,
/// bytes, or columns changed.
pub fn analyze(old: &Catalog, new: &Catalog) -> DriftReport {
    let mut drift = Vec::new();
    let mut compared = 0usize;

    for (id, old_node) in &old.nodes {
        let Some(new_node) = new.nodes.get(id) else {
            continue;
        };
        compared += 1;

        let old_cols: std::collections::BTreeSet<&String> = old_node.columns.keys().collect();
        let new_cols: std::collections::BTreeSet<&String> = new_node.columns.keys().collect();

        let added_columns: Vec<String> = new_cols
            .difference(&old_cols)
            .map(|s| (*s).clone())
            .collect();
        let removed_columns: Vec<String> = old_cols
            .difference(&new_cols)
            .map(|s| (*s).clone())
            .collect();

        let mut type_changes = Vec::new();
        for col in old_cols.intersection(&new_cols) {
            let old_type = old_node.columns.get(*col).and_then(|c| c.data_type.clone());
            let new_type = new_node.columns.get(*col).and_then(|c| c.data_type.clone());
            if old_type != new_type {
                type_changes.push(ColumnTypeChange {
                    column: (*col).clone(),
                    old_type,
                    new_type,
                });
            }
        }

        let row_delta = signed_delta(old_node.row_count(), new_node.row_count());

        let changed = row_delta.is_some_and(|d| d != 0)
            || signed_delta(old_node.bytes(), new_node.bytes()).is_some_and(|d| d != 0)
            || !added_columns.is_empty()
            || !removed_columns.is_empty()
            || !type_changes.is_empty();

        if !changed {
            continue;
        }

        drift.push(NodeDrift {
            unique_id: id.clone(),
            row_count_old: old_node.row_count(),
            row_count_new: new_node.row_count(),
            row_delta: signed_delta(old_node.row_count(), new_node.row_count()),
            row_delta_percent: percent_delta(old_node.row_count(), new_node.row_count()),
            bytes_old: old_node.bytes(),
            bytes_new: new_node.bytes(),
            bytes_delta: signed_delta(old_node.bytes(), new_node.bytes()),
            added_columns,
            removed_columns,
            type_changes,
        });
    }

    drift.sort_by(|a, b| a.unique_id.cmp(&b.unique_id));

    DriftReport {
        nodes_compared: compared,
        nodes_with_drift: drift.len(),
        drift,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn catalog(json: serde_json::Value) -> Catalog {
        serde_json::from_value(json).unwrap()
    }

    #[test]
    fn detects_row_growth_and_column_changes() {
        let old = catalog(serde_json::json!({
            "nodes": {
                "model.pkg.orders": {
                    "unique_id": "model.pkg.orders",
                    "stats": {"row_count": {"value": 100}, "bytes": {"value": 1000}},
                    "columns": {
                        "id": {"name": "id", "type": "INTEGER"},
                        "amount": {"name": "amount", "type": "INTEGER"}
                    }
                },
                "model.pkg.stable": {
                    "unique_id": "model.pkg.stable",
                    "stats": {"row_count": {"value": 5}, "bytes": {"value": 50}},
                    "columns": {"id": {"name": "id", "type": "INTEGER"}}
                }
            }
        }));
        let new = catalog(serde_json::json!({
            "nodes": {
                "model.pkg.orders": {
                    "unique_id": "model.pkg.orders",
                    "stats": {"row_count": {"value": 150}, "bytes": {"value": 1500}},
                    "columns": {
                        "id": {"name": "id", "type": "INTEGER"},
                        "amount": {"name": "amount", "type": "NUMERIC"},
                        "created_at": {"name": "created_at", "type": "TIMESTAMP"}
                    }
                },
                "model.pkg.stable": {
                    "unique_id": "model.pkg.stable",
                    "stats": {"row_count": {"value": 5}, "bytes": {"value": 50}},
                    "columns": {"id": {"name": "id", "type": "INTEGER"}}
                }
            }
        }));

        let report = analyze(&old, &new);
        assert_eq!(report.nodes_compared, 2);
        assert_eq!(report.nodes_with_drift, 1);
        let d = &report.drift[0];
        assert_eq!(d.unique_id, "model.pkg.orders");
        assert_eq!(d.row_delta, Some(50));
        assert!((d.row_delta_percent.unwrap() - 50.0).abs() < 1e-9);
        assert_eq!(d.added_columns, vec!["created_at".to_string()]);
        assert_eq!(d.type_changes.len(), 1);
        assert_eq!(d.type_changes[0].column, "amount");
    }

    #[test]
    fn identical_catalogs_report_no_drift() {
        let c = catalog(serde_json::json!({
            "nodes": {
                "model.pkg.orders": {
                    "unique_id": "model.pkg.orders",
                    "stats": {"row_count": {"value": 100}},
                    "columns": {"id": {"name": "id", "type": "INTEGER"}}
                }
            }
        }));
        let report = analyze(&c, &c);
        assert_eq!(report.nodes_with_drift, 0);
        assert_eq!(report.nodes_compared, 1);
    }
}
