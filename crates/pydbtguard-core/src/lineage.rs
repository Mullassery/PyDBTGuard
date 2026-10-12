//! Blast-radius analysis over dbt's real `child_map` from `manifest.json`.
//!
//! Given a model id, this does a breadth-first walk of dbt's own dependency
//! graph to find every downstream model, test, and exposure, with the true
//! shortest-path distance. No heuristics about "distance 1 vs 2" — the graph
//! dbt ships is authoritative.

use crate::error::{Error, Result};
use crate::model::Manifest;
use serde::Serialize;
use std::collections::{HashSet, VecDeque};

#[derive(Debug, Clone, Serialize)]
pub struct ModelImpact {
    pub model_id: String,
    pub model_name: String,
    pub distance: usize,
    pub impact_level: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ExposureImpact {
    pub exposure_id: String,
    pub exposure_name: String,
    pub distance: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct BlastRadius {
    pub source_model_id: String,
    pub source_model_name: String,
    pub upstream_count: usize,
    pub downstream_models: usize,
    pub downstream_tests: usize,
    pub affected_exposures: Vec<ExposureImpact>,
    pub affected_models: Vec<ModelImpact>,
    /// 0-100, a documented weighted sum of critical/high/medium/low impacts
    /// plus exposures at risk.
    pub impact_score: f64,
    pub recommendations: Vec<String>,
}

fn resource_type(manifest: &Manifest, id: &str) -> Option<&'static str> {
    if let Some(n) = manifest.nodes.get(id) {
        return Some(match n.resource_type.as_str() {
            "model" => "model",
            "test" => "test",
            "snapshot" => "snapshot",
            "seed" => "seed",
            _ => "other",
        });
    }
    if manifest.exposures.contains_key(id) {
        return Some("exposure");
    }
    if manifest.sources.contains_key(id) {
        return Some("source");
    }
    None
}

fn name_of(manifest: &Manifest, id: &str) -> String {
    if let Some(n) = manifest.nodes.get(id) {
        return n.name.clone();
    }
    if let Some(e) = manifest.exposures.get(id) {
        return e.name.clone();
    }
    if let Some(s) = manifest.sources.get(id) {
        return s.name.clone();
    }
    id.to_string()
}

fn impact_level(distance: usize) -> &'static str {
    match distance {
        1 => "critical",
        2 => "high",
        3 => "medium",
        _ => "low",
    }
}

/// Analyze the blast radius of a failure originating at `model_id`.
pub fn analyze(manifest: &Manifest, model_id: &str) -> Result<BlastRadius> {
    let source_node = manifest
        .nodes
        .get(model_id)
        .ok_or_else(|| Error::ModelNotFound(model_id.to_string()))?;

    if !source_node.is_model() {
        return Err(Error::Invalid(format!(
            "{model_id} is a '{}' node, not a model",
            source_node.resource_type
        )));
    }

    let upstream_count = manifest
        .parent_map
        .get(model_id)
        .map(|p| p.iter().filter(|id| id.starts_with("model.")).count())
        .unwrap_or(0);

    let mut visited: HashSet<String> = HashSet::new();
    visited.insert(model_id.to_string());

    let mut queue: VecDeque<(String, usize)> = VecDeque::new();
    queue.push_back((model_id.to_string(), 0));

    let mut affected_models = Vec::new();
    let mut affected_exposures = Vec::new();
    let mut downstream_tests = 0usize;

    while let Some((id, distance)) = queue.pop_front() {
        for child in manifest.children(&id) {
            if !visited.insert(child.clone()) {
                continue;
            }
            let next = distance + 1;
            match resource_type(manifest, child) {
                Some("model") => {
                    affected_models.push(ModelImpact {
                        model_id: child.clone(),
                        model_name: name_of(manifest, child),
                        distance: next,
                        impact_level: impact_level(next).to_string(),
                    });
                    queue.push_back((child.clone(), next));
                }
                Some("exposure") => {
                    affected_exposures.push(ExposureImpact {
                        exposure_id: child.clone(),
                        exposure_name: name_of(manifest, child),
                        distance: next,
                    });
                    queue.push_back((child.clone(), next));
                }
                Some("test") => downstream_tests += 1,
                _ => {}
            }
        }
    }

    let critical = affected_models
        .iter()
        .filter(|m| m.impact_level == "critical")
        .count();
    let high = affected_models
        .iter()
        .filter(|m| m.impact_level == "high")
        .count();
    let medium = affected_models
        .iter()
        .filter(|m| m.impact_level == "medium")
        .count();
    let low = affected_models.len() - critical - high - medium;

    let impact_score =
        ((critical * 30 + high * 20 + medium * 10 + low * 5 + affected_exposures.len() * 15)
            as f64)
            .min(100.0);

    let mut recommendations = Vec::new();
    if critical > 0 {
        recommendations.push(
            "Critical downstream models affected: stage the change with a limited rollout.".into(),
        );
    }
    if !affected_exposures.is_empty() {
        recommendations.push(format!(
            "Notify stakeholders: {} exposure(s) depend on this model.",
            affected_exposures.len()
        ));
    }
    if (critical + high) > 3 {
        recommendations.push(format!(
            "Large blast radius ({} models within 2 hops): prepare a rollback plan.",
            critical + high
        ));
    }
    if affected_models.is_empty() && affected_exposures.is_empty() {
        recommendations.push(
            "No downstream models or exposures depend on this model; a failure stays contained."
                .into(),
        );
    }

    affected_models.sort_by(|a, b| {
        a.distance
            .cmp(&b.distance)
            .then_with(|| a.model_name.cmp(&b.model_name))
    });

    Ok(BlastRadius {
        source_model_id: model_id.to_string(),
        source_model_name: source_node.name.clone(),
        upstream_count,
        downstream_models: affected_models.len(),
        downstream_tests,
        affected_exposures,
        affected_models,
        impact_score,
        recommendations,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn manifest() -> Manifest {
        let json = serde_json::json!({
            "nodes": {
                "model.pkg.orders": {
                    "unique_id": "model.pkg.orders", "name": "orders", "resource_type": "model"
                },
                "model.pkg.customers": {
                    "unique_id": "model.pkg.customers", "name": "customers",
                    "resource_type": "model"
                },
                "test.pkg.unique_orders_id": {
                    "unique_id": "test.pkg.unique_orders_id", "name": "unique_orders_id",
                    "resource_type": "test", "test_metadata": {"name": "unique"},
                    "depends_on": {"nodes": ["model.pkg.orders"]}
                }
            },
            "exposures": {
                "exposure.pkg.dash": {
                    "unique_id": "exposure.pkg.dash", "name": "dash", "resource_type": "exposure"
                }
            },
            "parent_map": {
                "model.pkg.orders": ["source.pkg.raw_orders"],
                "model.pkg.customers": ["model.pkg.orders"],
                "test.pkg.unique_orders_id": ["model.pkg.orders"]
            },
            "child_map": {
                "model.pkg.orders": [
                    "model.pkg.customers",
                    "test.pkg.unique_orders_id",
                    "exposure.pkg.dash"
                ],
                "model.pkg.customers": []
            }
        });
        let mut m: Manifest = serde_json::from_value(json).unwrap();
        m.normalize();
        m
    }

    #[test]
    fn walks_child_map_to_real_distance() {
        let m = manifest();
        let result = analyze(&m, "model.pkg.orders").unwrap();
        assert_eq!(result.downstream_models, 1); // customers, 1 hop
        assert_eq!(result.affected_models[0].distance, 1);
        assert_eq!(result.affected_models[0].impact_level, "critical");
        assert_eq!(result.downstream_tests, 1);
        assert_eq!(result.affected_exposures.len(), 1);
        assert_eq!(result.affected_exposures[0].distance, 1);
        assert_eq!(result.upstream_count, 0); // parent is a source, not a model
                                              // 1 critical model (30) + 1 exposure (15) = 45.
        assert!((result.impact_score - 45.0).abs() < 1e-9);
    }

    #[test]
    fn leaf_model_has_zero_impact() {
        let m = manifest();
        let result = analyze(&m, "model.pkg.customers").unwrap();
        assert_eq!(result.downstream_models, 0);
        assert_eq!(result.impact_score, 0.0);
        assert!(result
            .recommendations
            .iter()
            .any(|r| r.contains("stays contained")));
    }

    #[test]
    fn missing_model_is_an_error() {
        let m = manifest();
        assert!(matches!(
            analyze(&m, "model.pkg.nope"),
            Err(Error::ModelNotFound(_))
        ));
    }
}
