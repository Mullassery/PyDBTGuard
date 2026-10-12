//! Source-freshness reporting from real `target/sources.json`.
//!
//! `sources.json` is written by `dbt source freshness`; it already contains
//! dbt's own `pass`/`warn`/`error` verdict per source, the max loaded
//! timestamp, and the configured warn/error thresholds. This module only
//! reshapes that real artifact into a report; it makes no freshness judgement
//! of its own.

use crate::model::{Manifest, SourcesArtifact};
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct SourceFreshness {
    pub source_id: String,
    pub source_name: String,
    pub status: String,
    pub max_loaded_at: Option<String>,
    pub snapshotted_at: Option<String>,
    pub age_seconds: Option<f64>,
    pub warn_after: Option<String>,
    pub error_after: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct FreshnessReport {
    pub total_sources: usize,
    pub pass_count: usize,
    pub warn_count: usize,
    pub error_count: usize,
    pub sources: Vec<SourceFreshness>,
}

fn criteria_string(threshold: &Option<crate::model::FreshnessThreshold>) -> Option<String> {
    threshold
        .as_ref()
        .and_then(|t| match (&t.count, &t.period) {
            (Some(c), Some(p)) => Some(format!("{} {}", c, p)),
            (Some(c), None) => Some(format!("{c}")),
            _ => None,
        })
}

/// Summarize real source-freshness results.
pub fn analyze(sources: &SourcesArtifact, manifest: Option<&Manifest>) -> FreshnessReport {
    let mut entries = Vec::new();

    for result in &sources.results {
        let name = manifest
            .and_then(|m| m.sources.get(&result.unique_id))
            .map(|n| n.name.clone())
            .unwrap_or_else(|| result.unique_id.clone());

        entries.push(SourceFreshness {
            source_id: result.unique_id.clone(),
            source_name: name,
            status: result.status.to_lowercase(),
            max_loaded_at: result.max_loaded_at.clone(),
            snapshotted_at: result.snapshotted_at.clone(),
            age_seconds: result.max_loaded_at_time_ago_in_s,
            warn_after: criteria_string(&result.criteria.warn_after),
            error_after: criteria_string(&result.criteria.error_after),
        });
    }

    let count = |s: &str| entries.iter().filter(|e| e.status == s).count();

    FreshnessReport {
        total_sources: entries.len(),
        pass_count: count("pass"),
        warn_count: count("warn"),
        error_count: count("error"),
        sources: entries,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_real_source_freshness_results() {
        let json = serde_json::json!({
            "results": [
                {
                    "unique_id": "source.pkg.raw_orders",
                    "status": "warn",
                    "max_loaded_at": "2026-01-01T00:00:00Z",
                    "snapshotted_at": "2026-01-01T13:00:00Z",
                    "max_loaded_at_time_ago_in_s": 46800.0,
                    "criteria": {
                        "warn_after": {"count": 12, "period": "hour"},
                        "error_after": {"count": 24, "period": "hour"}
                    }
                },
                {
                    "unique_id": "source.pkg.raw_customers",
                    "status": "pass",
                    "max_loaded_at_time_ago_in_s": 100.0
                }
            ]
        });
        let sources: SourcesArtifact = serde_json::from_value(json).unwrap();
        let report = analyze(&sources, None);
        assert_eq!(report.total_sources, 2);
        assert_eq!(report.warn_count, 1);
        assert_eq!(report.pass_count, 1);
        let warned = &report.sources[0];
        assert_eq!(warned.warn_after.as_deref(), Some("12 hour"));
        assert_eq!(warned.error_after.as_deref(), Some("24 hour"));
        assert_eq!(warned.age_seconds, Some(46800.0));
    }
}
