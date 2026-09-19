use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub mod analyzer;

pub use analyzer::BlastRadiusAnalyzer;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum ImpactLevel {
    Critical,
    High,
    Medium,
    Low,
}

impl ImpactLevel {
    pub fn score(&self) -> f64 {
        match self {
            ImpactLevel::Critical => 100.0,
            ImpactLevel::High => 75.0,
            ImpactLevel::Medium => 50.0,
            ImpactLevel::Low => 25.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AffectedModel {
    pub model_id: String,
    pub model_name: String,
    pub impact_level: ImpactLevel,
    pub criticality_score: f64,
    pub affected_users: usize,
    pub sla_freshness_hours: Option<u32>,
    pub bi_dependencies: usize,
    pub distance_from_source: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlastRadiusResult {
    pub source_model: String,
    pub total_affected_models: usize,
    pub critical_impact_count: usize,
    pub high_impact_count: usize,
    pub estimated_users_affected: usize,
    pub affected_models: Vec<AffectedModel>,
    pub exposures_at_risk: Vec<String>,
    pub overall_blast_radius_score: f64, // 0-100
    pub estimated_recovery_time_hours: f64,
    pub recommendations: Vec<String>,
}

impl BlastRadiusResult {
    pub fn new(source_model: String) -> Self {
        Self {
            source_model,
            total_affected_models: 0,
            critical_impact_count: 0,
            high_impact_count: 0,
            estimated_users_affected: 0,
            affected_models: Vec::new(),
            exposures_at_risk: Vec::new(),
            overall_blast_radius_score: 0.0,
            estimated_recovery_time_hours: 0.0,
            recommendations: Vec::new(),
        }
    }

    pub fn add_affected_model(&mut self, model: AffectedModel) {
        match model.impact_level {
            ImpactLevel::Critical => self.critical_impact_count += 1,
            ImpactLevel::High => self.high_impact_count += 1,
            _ => {}
        }
        self.affected_models.push(model);
    }

    pub fn add_exposure_at_risk(&mut self, exposure_id: String) {
        self.exposures_at_risk.push(exposure_id);
    }

    pub fn add_recommendation(&mut self, recommendation: String) {
        self.recommendations.push(recommendation);
    }

    pub fn recalculate_score(&mut self) {
        if self.affected_models.is_empty() {
            self.overall_blast_radius_score = 0.0;
            return;
        }

        let total_score: f64 = self
            .affected_models
            .iter()
            .map(|m| m.impact_level.score() * (m.criticality_score / 100.0))
            .sum();

        self.overall_blast_radius_score =
            (total_score / (self.affected_models.len() as f64)).min(100.0);

        // Estimate recovery time: ~1 hour per 10 affected models, plus exposure risk
        self.estimated_recovery_time_hours = (self.affected_models.len() as f64 / 10.0)
            + (self.exposures_at_risk.len() as f64 * 2.0);
    }
}

#[derive(Debug, Clone)]
pub struct ImpactAnalysisOptions {
    pub include_indirect_impacts: bool,
    pub max_depth: usize,
    pub include_user_counts: bool,
    pub criticality_weights: HashMap<String, f64>,
}

impl Default for ImpactAnalysisOptions {
    fn default() -> Self {
        let mut weights = HashMap::new();
        weights.insert("freshness_sla".to_string(), 0.4);
        weights.insert("bi_dependencies".to_string(), 0.3);
        weights.insert("user_exposure".to_string(), 0.3);

        Self {
            include_indirect_impacts: true,
            max_depth: 10,
            include_user_counts: true,
            criticality_weights: weights,
        }
    }
}
