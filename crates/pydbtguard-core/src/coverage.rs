//! Test-coverage gap analysis from the real `manifest.json` dependency graph
//! (and `catalog.json`, when present, for real row counts).
//!
//! Coverage is decided from dbt's own `depends_on.nodes`: a test covers a
//! model when the model id appears in the test's dependencies, and the test's
//! type comes from `test_metadata.name`. Nothing here relies on keys that do
//! not exist in a real manifest (the old code read a fabricated
//! `attached_node` field from raw manifest nodes, which silently produced
//! "every model is uncovered").

use crate::model::{Catalog, Manifest};
use serde::Serialize;
use std::collections::{BTreeSet, HashMap};

/// Test types this tool treats as required for every model. `relationships`
/// becomes required for models that expose an id-like column.
const ALWAYS_REQUIRED: [&str; 2] = ["unique", "not_null"];

#[derive(Debug, Clone, Serialize)]
pub struct CoverageGap {
    pub model_id: String,
    pub model_name: String,
    pub materialized: Option<String>,
    pub covered_test_types: Vec<String>,
    pub missing_test_types: Vec<String>,
    pub attached_tests: Vec<String>,
    pub bi_dependencies: usize,
    pub downstream_models: usize,
    pub row_count: Option<u64>,
    pub risk_score: u8,
    pub priority: String,
    pub recommended_tests: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct CoverageReport {
    pub total_models: usize,
    pub models_with_gaps: usize,
    pub critical_count: usize,
    pub high_count: usize,
    pub gaps: Vec<CoverageGap>,
}

/// Analyze coverage across all models in the manifest.
pub fn analyze(manifest: &Manifest, catalog: Option<&Catalog>) -> CoverageReport {
    // model_id -> list of (test name, test type)
    let mut attached: HashMap<String, Vec<(String, String)>> = HashMap::new();
    for (_, test) in manifest.tests() {
        if let Some(model_id) = test.attached_node() {
            attached
                .entry(model_id.to_string())
                .or_default()
                .push((test.name.clone(), test.test_type()));
        }
    }

    let mut gaps = Vec::new();
    let mut total_models = 0usize;

    for (model_id, model) in manifest.models() {
        total_models += 1;

        let tests = attached.get(model_id).cloned().unwrap_or_default();
        let covered: BTreeSet<String> = tests.iter().map(|(_, t)| t.clone()).collect();

        let mut required: Vec<String> = ALWAYS_REQUIRED.iter().map(|s| s.to_string()).collect();
        if model.columns.keys().any(|c| is_id_like(c)) {
            required.push("relationships".to_string());
        }

        let missing: Vec<String> = required
            .into_iter()
            .filter(|t| !covered.contains(t))
            .collect();

        if missing.is_empty() {
            continue;
        }

        let downstream_models = manifest
            .children(model_id)
            .iter()
            .filter(|id| id.starts_with("model."))
            .count();

        let bi_dependencies = manifest
            .exposures
            .values()
            .filter(|e| e.depends_on.nodes.iter().any(|d| d == model_id))
            .count();

        let row_count = catalog
            .and_then(|c| c.get(model_id))
            .and_then(|n| n.row_count());

        let mut risk: i32 = 40;
        risk += (downstream_models.min(5) * 4) as i32;
        risk += (bi_dependencies.min(3) * 6) as i32;
        risk += match row_count {
            Some(rc) if rc >= 1_000_000 => 15,
            Some(rc) if rc >= 10_000 => 8,
            Some(_) => 3,
            None => 0,
        };
        risk += (missing.len() as i32) * 5;

        gaps.push(CoverageGap {
            model_id: model_id.clone(),
            model_name: model.name.clone(),
            materialized: model.config.materialized.clone(),
            covered_test_types: covered.into_iter().collect(),
            priority: priority_for(risk, bi_dependencies, &missing),
            recommended_tests: missing
                .iter()
                .map(|m| recommended_tests_for(m).to_string())
                .collect(),
            missing_test_types: missing,
            attached_tests: tests.into_iter().map(|(n, _)| n).collect(),
            bi_dependencies,
            downstream_models,
            row_count,
            risk_score: risk.clamp(0, 100) as u8,
        });
    }

    gaps.sort_by(|a, b| {
        priority_rank(&a.priority)
            .cmp(&priority_rank(&b.priority))
            .then_with(|| b.risk_score.cmp(&a.risk_score))
            .then_with(|| a.model_name.cmp(&b.model_name))
    });

    CoverageReport {
        total_models,
        models_with_gaps: gaps.len(),
        critical_count: gaps.iter().filter(|g| g.priority == "CRITICAL").count(),
        high_count: gaps.iter().filter(|g| g.priority == "HIGH").count(),
        gaps,
    }
}

fn is_id_like(column: &str) -> bool {
    column == "id" || column.ends_with("_id")
}

fn priority_rank(priority: &str) -> u8 {
    match priority {
        "CRITICAL" => 0,
        "HIGH" => 1,
        "MEDIUM" => 2,
        _ => 3,
    }
}

fn priority_for(risk: i32, bi_dependencies: usize, missing: &[String]) -> String {
    if risk >= 75 || (bi_dependencies >= 2 && missing.len() >= 2) {
        "CRITICAL".to_string()
    } else if risk >= 60 || (bi_dependencies >= 1 && !missing.is_empty()) {
        "HIGH".to_string()
    } else if risk >= 40 {
        "MEDIUM".to_string()
    } else {
        "LOW".to_string()
    }
}

fn recommended_tests_for(missing: &str) -> &'static str {
    match missing {
        "unique" => "Add a unique test on the model's primary key",
        "not_null" => "Add not_null tests on required columns",
        "relationships" => "Add relationship tests for foreign-key columns",
        _ => "Add this test type",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn manifest() -> Manifest {
        let json = serde_json::json!({
            "nodes": {
                "model.pkg.orders": {
                    "unique_id": "model.pkg.orders", "name": "orders", "resource_type": "model",
                    "columns": {"order_id": {}, "customer_id": {}},
                    "config": {"materialized": "table"}
                },
                "model.pkg.customers": {
                    "unique_id": "model.pkg.customers", "name": "customers", "resource_type": "model",
                    "columns": {"customer_id": {}}
                },
                "test.pkg.unique_orders_order_id": {
                    "unique_id": "test.pkg.unique_orders_order_id", "name": "unique_orders_order_id",
                    "resource_type": "test", "test_metadata": {"name": "unique"},
                    "depends_on": {"nodes": ["model.pkg.orders"]}
                },
                "test.pkg.not_null_orders_order_id": {
                    "unique_id": "test.pkg.not_null_orders_order_id", "name": "not_null_orders_order_id",
                    "resource_type": "test", "test_metadata": {"name": "not_null"},
                    "depends_on": {"nodes": ["model.pkg.orders"]}
                }
            },
            "exposures": {
                "exposure.pkg.dash": {
                    "unique_id": "exposure.pkg.dash", "name": "dash", "resource_type": "exposure",
                    "depends_on": {"nodes": ["model.pkg.customers"]}
                }
            },
            "child_map": {
                "model.pkg.orders": ["model.pkg.customers", "test.pkg.unique_orders_order_id"],
                "model.pkg.customers": ["exposure.pkg.dash"]
            },
            "parent_map": {}
        });
        let mut m: Manifest = serde_json::from_value(json).unwrap();
        m.normalize();
        m
    }

    #[test]
    fn covered_model_is_only_missing_relationships() {
        let report = analyze(&manifest(), None);
        let orders = report
            .gaps
            .iter()
            .find(|g| g.model_id == "model.pkg.orders")
            .unwrap();
        assert!(!orders.missing_test_types.contains(&"unique".to_string()));
        assert!(!orders.missing_test_types.contains(&"not_null".to_string()));
        assert!(orders
            .missing_test_types
            .contains(&"relationships".to_string()));
        assert!(orders.covered_test_types.contains(&"unique".to_string()));
    }

    #[test]
    fn uncovered_model_reports_core_types() {
        let report = analyze(&manifest(), None);
        let customers = report
            .gaps
            .iter()
            .find(|g| g.model_id == "model.pkg.customers")
            .unwrap();
        assert!(customers.missing_test_types.contains(&"unique".to_string()));
        assert!(customers
            .missing_test_types
            .contains(&"not_null".to_string()));
        assert_eq!(customers.bi_dependencies, 1);
        assert!(!customers.recommended_tests.is_empty());
    }
}
