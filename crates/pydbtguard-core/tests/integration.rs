//! End-to-end tests over realistic hand-authored dbt artifacts.
//!
//! The JSON fixtures under `tests/fixtures/` mirror the exact files dbt writes
//! (`manifest.json`, `catalog.json`, `run_results.json`, `sources.json`) for a
//! small jaffle_shop-style project, plus the tool's own accumulated
//! `run_history.jsonl`. These tests drive the public `api` boundary exactly as
//! the Python CLI does.

use pydbtguard_core::api;
use serde_json::Value;

const MANIFEST: &str = include_str!("../../../tests/fixtures/manifest.json");
const CATALOG: &str = include_str!("../../../tests/fixtures/catalog.json");
const CATALOG_V2: &str = include_str!("../../../tests/fixtures/catalog_v2.json");
const RUN_RESULTS: &str = include_str!("../../../tests/fixtures/run_results.json");
const SOURCES: &str = include_str!("../../../tests/fixtures/sources.json");
const HISTORY: &str = include_str!("../../../tests/fixtures/run_history.jsonl");

fn parse(out: String) -> Value {
    serde_json::from_str(&out).expect("api must return valid JSON")
}

#[test]
fn analyze_scores_real_history_and_marks_flaky_dangerous() {
    let v = parse(api::analyze(MANIFEST, HISTORY).unwrap());
    assert_eq!(v["kind"], "analyze");
    assert_eq!(v["project_name"], "jaffle_shop");
    assert_eq!(v["adapter_type"], "bigquery");
    assert_eq!(v["total_tests"], 11);
    assert_eq!(v["summary"]["stable"], 10);
    assert_eq!(v["summary"]["dangerous"], 1);
    assert_eq!(v["summary"]["at_risk"], 0);
    assert_eq!(v["summary"]["unknown"], 0);

    let flaky = v["tests"]
        .as_array()
        .unwrap()
        .iter()
        .find(|t| t["name"] == "assert_positive_amount")
        .unwrap();
    assert_eq!(flaky["test_type"], "singular");
    assert_eq!(flaky["risk_level"], "DANGEROUS");
    assert!(flaky["flaky"].as_bool().unwrap());
    assert!((flaky["failure_probability"].as_f64().unwrap() - 2.0 / 3.0).abs() < 1e-9);
    assert_eq!(flaky["attached_node"], "model.jaffle_shop.stg_payments");
}

#[test]
fn coverage_reports_real_gaps_from_the_manifest_graph() {
    let v = parse(api::coverage_report(MANIFEST, CATALOG).unwrap());
    assert_eq!(v["total_models"], 5);
    assert_eq!(v["models_with_gaps"], 5);

    let gaps = v["gaps"].as_array().unwrap();
    let missing = |model: &str| -> Vec<String> {
        gaps.iter()
            .find(|g| g["model_id"] == format!("model.jaffle_shop.{model}"))
            .map(|g| {
                g["missing_test_types"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|m| m.as_str().unwrap().to_string())
                    .collect()
            })
            .unwrap_or_default()
    };

    // orders has a relationships test but neither unique nor not_null.
    let orders = missing("orders");
    assert!(orders.contains(&"unique".to_string()));
    assert!(orders.contains(&"not_null".to_string()));
    assert!(!orders.contains(&"relationships".to_string()));

    // stg_payments has only not_null(payment_id); it needs unique + relationships.
    let payments = missing("stg_payments");
    assert!(payments.contains(&"unique".to_string()));
    assert!(payments.contains(&"relationships".to_string()));
}

#[test]
fn blast_radius_uses_real_child_map_distances() {
    let v = parse(api::blast_radius_report(MANIFEST, "model.jaffle_shop.stg_orders").unwrap());
    assert_eq!(v["downstream_models"], 2);
    assert_eq!(v["downstream_tests"], 7);
    assert_eq!(v["affected_exposures"].as_array().unwrap().len(), 1);
    assert_eq!(v["affected_exposures"][0]["distance"], 2);
    assert_eq!(v["impact_score"], 75.0);
    assert_eq!(v["upstream_count"], 0);
}

#[test]
fn cost_uses_real_catalog_bytes_and_bigquery_price() {
    let v = parse(api::cost_report(MANIFEST, CATALOG, None).unwrap());
    assert_eq!(v["adapter_type"], "bigquery");
    assert_eq!(v["price_per_tb_usd"], 6.25);
    assert_eq!(v["priced_tests"], 11);
    // (2048000*2 + 18000000*3 + 3400000000*2 + 120000000*2 + 2500000000*2) bytes / 1e12 * 6.25
    let expected = 12098096000f64 / 1e12 * 6.25;
    assert!((v["total_estimated_cost_usd_per_scan"].as_f64().unwrap() - expected).abs() < 1e-6);
    assert_eq!(v["optimizations"].as_array().unwrap().len(), 4);
}

#[test]
fn cost_reports_null_for_unpriced_adapters() {
    let locally = MANIFEST.replace("\"bigquery\"", "\"duckdb\"");
    let v = parse(api::cost_report(&locally, CATALOG, None).unwrap());
    assert_eq!(v["price_per_tb_usd"], 0.0);
    assert_eq!(v["total_estimated_cost_usd_per_scan"], 0.0);

    let unknown = api::cost_report(MANIFEST, CATALOG, Some("mystery-db")).unwrap();
    let v = parse(unknown);
    assert!(v["price_per_tb_usd"].is_null());
    assert_eq!(v["priced_tests"], 0);
}

#[test]
fn history_parses_real_accumulated_runs_and_detects_flake() {
    let v = parse(api::history_report(HISTORY).unwrap());
    assert_eq!(v["total_runs"], 3);
    assert_eq!(v["total_tests"], 11);
    assert_eq!(v["flaky_count"], 1);
}

#[test]
fn run_results_are_truly_reproducible_from_run_history() {
    // The history store appends exactly the test outcomes in run_results.json;
    // the API must therefore see a 4th run when we append a real run snapshot.
    let extra = format!("{HISTORY}\n{}", snapshot_from_run_results());
    let v = parse(api::history_report(&extra).unwrap());
    assert_eq!(v["total_runs"], 4);
}

fn snapshot_from_run_results() -> String {
    let results: Value = serde_json::from_str(RUN_RESULTS).unwrap();
    let meta = &results["metadata"];
    let mut map = serde_json::Map::new();
    for node in results["results"].as_array().unwrap() {
        let id = node["unique_id"].as_str().unwrap();
        if id.starts_with("test.") {
            map.insert(id.to_string(), node["status"].clone());
        }
    }
    serde_json::json!({
        "invocation_id": meta["invocation_id"],
        "generated_at": meta["generated_at"],
        "results": map,
    })
    .to_string()
}

#[test]
fn freshness_reshapes_dbt_verdicts_without_recomputing_them() {
    let v = parse(api::freshness_report(SOURCES, MANIFEST).unwrap());
    assert_eq!(v["total_sources"], 3);
    assert_eq!(v["warn_count"], 1);
    assert_eq!(v["pass_count"], 1);
    assert_eq!(v["error_count"], 1);
    let warned = v["sources"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s["status"] == "warn")
        .unwrap();
    assert_eq!(warned["source_name"], "raw_orders");
    assert_eq!(warned["warn_after"], "12 hour");
}

#[test]
fn drift_detects_schema_and_volume_changes_between_catalogs() {
    let v = parse(api::drift_report(CATALOG, CATALOG_V2).unwrap());
    assert_eq!(v["nodes_compared"], 5);
    assert_eq!(v["nodes_with_drift"], 2);

    let orders = v["drift"]
        .as_array()
        .unwrap()
        .iter()
        .find(|n| n["unique_id"] == "model.jaffle_shop.orders")
        .unwrap();
    assert_eq!(orders["row_delta"], 300000);
    assert!(orders["added_columns"]
        .as_array()
        .unwrap()
        .iter()
        .any(|c| c == "lifetime_value"));
    assert!(orders["removed_columns"]
        .as_array()
        .unwrap()
        .iter()
        .any(|c| c == "amount"));
    assert_eq!(orders["type_changes"][0]["column"], "status");
}

#[test]
fn every_report_carries_the_engine_version() {
    let v = parse(api::analyze(MANIFEST, "").unwrap());
    assert_eq!(v["version"], pydbtguard_core::VERSION);
}
