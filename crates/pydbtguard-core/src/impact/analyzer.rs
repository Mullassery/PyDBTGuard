use super::{AffectedModel, BlastRadiusResult, ImpactAnalysisOptions, ImpactLevel};
use crate::lineage::graph::{LineageGraph, NodeType};
use std::collections::{HashMap, HashSet};

pub struct BlastRadiusAnalyzer {
    options: ImpactAnalysisOptions,
}

impl BlastRadiusAnalyzer {
    pub fn new(options: ImpactAnalysisOptions) -> Self {
        Self { options }
    }

    pub fn analyze(
        &self,
        graph: &LineageGraph,
        source_model_id: &str,
        model_metadata: &HashMap<String, HashMap<String, String>>,
    ) -> BlastRadiusResult {
        let mut result = BlastRadiusResult::new(source_model_id.to_string());

        // Get downstream nodes
        let downstream = if self.options.include_indirect_impacts {
            graph.downstream_nodes(source_model_id)
        } else {
            self.get_direct_downstream(graph, source_model_id)
        };

        result.total_affected_models = downstream
            .iter()
            .filter(|id| {
                graph
                    .nodes
                    .get(*id)
                    .map(|n| n.node_type == NodeType::Model)
                    .unwrap_or(false)
            })
            .count();

        // Calculate impact for each affected model
        for node_id in &downstream {
            if let Some(node) = graph.nodes.get(node_id) {
                if node.node_type == NodeType::Model {
                    let distance = self.calculate_distance(graph, source_model_id, node_id);
                    let impact_level =
                        self.determine_impact_level(distance, model_metadata, node_id);
                    let criticality = self.calculate_criticality_score(model_metadata, node_id);

                    let affected_model = AffectedModel {
                        model_id: node_id.clone(),
                        model_name: node.name.clone(),
                        impact_level: impact_level.clone(),
                        criticality_score: criticality,
                        affected_users: self.estimate_user_impact(model_metadata, node_id),
                        sla_freshness_hours: self.get_freshness_sla(model_metadata, node_id),
                        bi_dependencies: self.count_bi_dependencies(graph, node_id),
                        distance_from_source: distance,
                    };

                    result.add_affected_model(affected_model);
                }
            }
        }

        // Identify exposures at risk
        for node_id in &downstream {
            if let Some(node) = graph.nodes.get(node_id) {
                if node.node_type == NodeType::Exposure {
                    result.add_exposure_at_risk(node_id.clone());
                }
            }
        }

        // Calculate total estimated users
        result.estimated_users_affected = result
            .affected_models
            .iter()
            .map(|m| m.affected_users)
            .sum();

        // Generate recommendations
        self.generate_recommendations(&mut result);

        // Recalculate final score
        result.recalculate_score();

        result
    }

    fn get_direct_downstream(&self, graph: &LineageGraph, node_id: &str) -> HashSet<String> {
        let mut downstream = HashSet::new();
        for edge in &graph.edges {
            if edge.from == node_id {
                downstream.insert(edge.to.clone());
            }
        }
        downstream
    }

    fn calculate_distance(&self, graph: &LineageGraph, source: &str, target: &str) -> usize {
        // BFS to find shortest path
        let mut visited = HashSet::new();
        let mut queue = vec![(source.to_string(), 0)];
        visited.insert(source.to_string());

        while let Some((current, dist)) = queue.pop() {
            if current == target {
                return dist;
            }

            for edge in &graph.edges {
                if edge.from == current && !visited.contains(&edge.to) {
                    visited.insert(edge.to.clone());
                    queue.push((edge.to.clone(), dist + 1));
                }
            }
        }

        usize::MAX
    }

    fn determine_impact_level(
        &self,
        distance: usize,
        _metadata: &HashMap<String, HashMap<String, String>>,
        _model_id: &str,
    ) -> ImpactLevel {
        // Closer = more critical impact
        match distance {
            0..=1 => ImpactLevel::Critical,
            2 => ImpactLevel::High,
            3 => ImpactLevel::Medium,
            _ => ImpactLevel::Low,
        }
    }

    fn calculate_criticality_score(
        &self,
        metadata: &HashMap<String, HashMap<String, String>>,
        model_id: &str,
    ) -> f64 {
        let mut score = 50.0; // Base score

        if let Some(meta) = metadata.get(model_id) {
            // Check for freshness SLA
            if let Some(sla) = meta.get("freshness_sla_hours") {
                if let Ok(hours) = sla.parse::<u32>() {
                    // Tighter SLA = more critical
                    score += (24.0 - (hours as f64)) / 24.0 * 25.0;
                }
            }

            // Check for BI dependencies
            if let Some(deps) = meta.get("bi_dependencies") {
                if let Ok(dep_count) = deps.parse::<usize>() {
                    score += (dep_count as f64 / 10.0) * 25.0;
                }
            }
        }

        score.min(100.0)
    }

    fn estimate_user_impact(
        &self,
        metadata: &HashMap<String, HashMap<String, String>>,
        model_id: &str,
    ) -> usize {
        if let Some(meta) = metadata.get(model_id) {
            if let Some(users) = meta.get("estimated_users") {
                return users.parse().unwrap_or(0);
            }
        }
        0
    }

    fn get_freshness_sla(
        &self,
        metadata: &HashMap<String, HashMap<String, String>>,
        model_id: &str,
    ) -> Option<u32> {
        metadata
            .get(model_id)
            .and_then(|meta| meta.get("freshness_sla_hours").and_then(|s| s.parse().ok()))
    }

    fn count_bi_dependencies(&self, graph: &LineageGraph, model_id: &str) -> usize {
        graph
            .downstream_nodes(model_id)
            .iter()
            .filter(|id| {
                graph
                    .nodes
                    .get(*id)
                    .map(|n| n.node_type == NodeType::Exposure)
                    .unwrap_or(false)
            })
            .count()
    }

    fn generate_recommendations(&self, result: &mut BlastRadiusResult) {
        if result.critical_impact_count > 0 {
            result.add_recommendation(
                "Critical impact detected. Consider staging deployment with limited rollout."
                    .to_string(),
            );
        }

        if !result.exposures_at_risk.is_empty() {
            result.add_recommendation(format!(
                "Notify {} downstream stakeholders before deployment.",
                result.exposures_at_risk.len()
            ));
        }

        if result.estimated_recovery_time_hours > 4.0 {
            result.add_recommendation(
                "Estimated recovery time > 4 hours. Ensure rollback plan is ready.".to_string(),
            );
        }
    }
}

impl Default for BlastRadiusAnalyzer {
    fn default() -> Self {
        Self::new(Default::default())
    }
}
