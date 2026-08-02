pub mod stats;
pub mod lineage;
pub mod manifest;

pub use stats::{fingerprint, predictor};

#[derive(Debug, Clone)]
pub struct AnalysisResult {
    pub test_name: String,
    pub reliability_score: f64,
    pub failure_probability: f64,
    pub stability_history: Vec<bool>,
}
