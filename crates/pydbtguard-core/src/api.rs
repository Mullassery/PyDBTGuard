//! The stable boundary between the Rust engine and any host language.
//!
//! Every function here takes raw artifact text (exactly what you read from
//! `target/*.json` / the accumulated history file) and returns a pretty JSON
//! report string. The Python bindings are a thin wrapper over these, so the
//! same well-tested code path drives both the CLI and the Rust tests.

use crate::cost as cost_engine;
use crate::coverage;
use crate::drift as drift_engine;
use crate::error::{Error, Result};
use crate::freshness as freshness_engine;
use crate::history as history_engine;
use crate::lineage;
use crate::model::{Catalog, Manifest, SourcesArtifact};
use crate::stats;
use serde::de::DeserializeOwned;
use serde::Serialize;
use std::collections::HashMap;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Serialize)]
struct Envelope<T> {
    version: &'static str,
    kind: &'static str,
    #[serde(flatten)]
    report: T,
}

fn emit<T: Serialize>(kind: &'static str, report: T) -> Result<String> {
    serde_json::to_string_pretty(&Envelope {
        version: VERSION,
        kind,
        report,
    })
    .map_err(|source| Error::Serialize { source })
}

fn parse<T: DeserializeOwned>(artifact: &'static str, json: &str) -> Result<T> {
    serde_json::from_str(json).map_err(|source| Error::parse(artifact, source))
}

fn parse_manifest(json: &str) -> Result<Manifest> {
    let mut manifest: Manifest = parse("manifest.json", json)?;
    manifest.normalize();
    Ok(manifest)
}

fn optional_catalog(json: &str) -> Result<Option<Catalog>> {
    if json.trim().is_empty() {
        Ok(None)
    } else {
        Ok(Some(parse("catalog.json", json)?))
    }
}

// ---------------------------------------------------------------------------
// analyze
// ---------------------------------------------------------------------------

#[derive(Serialize, Default)]
struct AnalyzeSummary {
    stable: usize,
    at_risk: usize,
    dangerous: usize,
    unknown: usize,
}

#[derive(Serialize)]
struct TestAnalysis {
    test_id: String,
    name: String,
    test_type: String,
    attached_node: Option<String>,
    severity: String,
    tags: Vec<String>,
    #[serde(flatten)]
    prediction: stats::Prediction,
}

#[derive(Serialize)]
struct AnalyzeReport {
    project_name: Option<String>,
    adapter_type: Option<String>,
    total_tests: usize,
    summary: AnalyzeSummary,
    tests: Vec<TestAnalysis>,
}

fn risk_rank(level: stats::RiskLevel) -> u8 {
    match level {
        stats::RiskLevel::Dangerous => 0,
        stats::RiskLevel::AtRisk => 1,
        stats::RiskLevel::Stable => 2,
        stats::RiskLevel::Unknown => 3,
    }
}

/// Reliability scoring + failure prediction for every test in the manifest,
/// using the accumulated real run history.
pub fn analyze(manifest_json: &str, history_jsonl: &str) -> Result<String> {
    let manifest = parse_manifest(manifest_json)?;
    let parsed = history_engine::parse(history_jsonl)?;
    let by_id: HashMap<&str, &Vec<bool>> = parsed.iter().map(|(id, h)| (id.as_str(), h)).collect();

    let mut summary = AnalyzeSummary::default();
    let mut tests = Vec::new();

    for (id, test) in manifest.tests() {
        let empty = Vec::new();
        let outcomes = by_id.get(id.as_str()).copied().unwrap_or(&empty);
        let prediction = stats::predict(outcomes);

        match prediction.risk_level {
            stats::RiskLevel::Stable => summary.stable += 1,
            stats::RiskLevel::AtRisk => summary.at_risk += 1,
            stats::RiskLevel::Dangerous => summary.dangerous += 1,
            stats::RiskLevel::Unknown => summary.unknown += 1,
        }

        tests.push(TestAnalysis {
            test_id: id.clone(),
            name: test.name.clone(),
            test_type: test.test_type(),
            attached_node: test.attached_node().map(str::to_string),
            severity: test.severity(),
            tags: test.tags.clone(),
            prediction,
        });
    }

    tests.sort_by(|a, b| {
        risk_rank(a.prediction.risk_level)
            .cmp(&risk_rank(b.prediction.risk_level))
            .then_with(|| a.name.cmp(&b.name))
    });

    emit(
        "analyze",
        AnalyzeReport {
            project_name: manifest.metadata.project_name.clone(),
            adapter_type: manifest.metadata.adapter_type.clone(),
            total_tests: tests.len(),
            summary,
            tests,
        },
    )
}

// ---------------------------------------------------------------------------
// coverage
// ---------------------------------------------------------------------------

pub fn coverage_report(manifest_json: &str, catalog_json: &str) -> Result<String> {
    let manifest = parse_manifest(manifest_json)?;
    let catalog = optional_catalog(catalog_json)?;
    emit("coverage", coverage::analyze(&manifest, catalog.as_ref()))
}

// ---------------------------------------------------------------------------
// blast radius
// ---------------------------------------------------------------------------

pub fn blast_radius_report(manifest_json: &str, model_id: &str) -> Result<String> {
    if model_id.trim().is_empty() {
        return Err(Error::Invalid("model_id must not be empty".to_string()));
    }
    let manifest = parse_manifest(manifest_json)?;
    emit("blast-radius", lineage::analyze(&manifest, model_id)?)
}

// ---------------------------------------------------------------------------
// cost
// ---------------------------------------------------------------------------

pub fn cost_report(
    manifest_json: &str,
    catalog_json: &str,
    adapter_override: Option<&str>,
) -> Result<String> {
    let manifest = parse_manifest(manifest_json)?;
    let catalog = parse::<Catalog>("catalog.json", catalog_json)?;
    let report = cost_engine::analyze(&manifest, &catalog, adapter_override);
    emit("cost", report)
}

// ---------------------------------------------------------------------------
// history
// ---------------------------------------------------------------------------

pub fn history_report(history_jsonl: &str) -> Result<String> {
    emit("history", history_engine::analyze(history_jsonl)?)
}

// ---------------------------------------------------------------------------
// freshness
// ---------------------------------------------------------------------------

pub fn freshness_report(sources_json: &str, manifest_json: &str) -> Result<String> {
    let sources: SourcesArtifact = parse("sources.json", sources_json)?;
    let manifest = if manifest_json.trim().is_empty() {
        None
    } else {
        Some(parse_manifest(manifest_json)?)
    };
    emit(
        "freshness",
        freshness_engine::analyze(&sources, manifest.as_ref()),
    )
}

// ---------------------------------------------------------------------------
// drift
// ---------------------------------------------------------------------------

pub fn drift_report(old_catalog_json: &str, new_catalog_json: &str) -> Result<String> {
    let old: Catalog = parse("catalog.json (old)", old_catalog_json)?;
    let new: Catalog = parse("catalog.json (new)", new_catalog_json)?;
    emit("drift", drift_engine::analyze(&old, &new))
}

#[cfg(test)]
mod tests {
    use super::*;

    const MANIFEST: &str = r#"{
        "metadata": {"project_name": "jaffle_shop", "adapter_type": "bigquery"},
        "nodes": {
            "model.pkg.orders": {"unique_id": "model.pkg.orders", "name": "orders", "resource_type": "model"},
            "test.pkg.unique_orders_id": {
                "unique_id": "test.pkg.unique_orders_id", "name": "unique_orders_id",
                "resource_type": "test", "test_metadata": {"name": "unique"},
                "depends_on": {"nodes": ["model.pkg.orders"]}
            }
        },
        "child_map": {"model.pkg.orders": ["test.pkg.unique_orders_id"]}
    }"#;

    const HISTORY: &str = r#"{"results": {"test.pkg.unique_orders_id": "fail"}}
{"results": {"test.pkg.unique_orders_id": "pass"}}"#;

    #[test]
    fn analyze_reports_typed_prediction_from_real_history() {
        let out = analyze(MANIFEST, HISTORY).unwrap();
        let v: serde_json::Value = serde_json::from_str(&out).unwrap();
        assert_eq!(v["kind"], "analyze");
        assert_eq!(v["total_tests"], 1);
        assert_eq!(v["summary"]["unknown"], 0);
        assert_eq!(v["tests"][0]["test_type"], "unique");
        assert_eq!(v["tests"][0]["failure_probability"], 0.5);
    }

    #[test]
    fn analyze_without_history_is_honestly_unknown() {
        let out = analyze(MANIFEST, "").unwrap();
        let v: serde_json::Value = serde_json::from_str(&out).unwrap();
        assert_eq!(v["summary"]["unknown"], 1);
        assert!(v["tests"][0]["failure_probability"].is_null());
    }

    #[test]
    fn blast_radius_errors_on_unknown_model() {
        assert!(blast_radius_report(MANIFEST, "model.pkg.nope").is_err());
        assert!(blast_radius_report(MANIFEST, "").is_err());
    }

    #[test]
    fn coverage_works_without_catalog() {
        let out = coverage_report(MANIFEST, "").unwrap();
        let v: serde_json::Value = serde_json::from_str(&out).unwrap();
        // orders has unique covered, not_null missing.
        assert_eq!(v["models_with_gaps"], 1);
        assert_eq!(v["gaps"][0]["model_id"], "model.pkg.orders");
    }

    #[test]
    fn every_report_carries_the_version() {
        let v: serde_json::Value = serde_json::from_str(&history_report("").unwrap()).unwrap();
        assert_eq!(v["version"], VERSION);
    }
}
