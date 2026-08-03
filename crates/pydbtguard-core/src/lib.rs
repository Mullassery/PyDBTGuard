pub mod stats;
pub mod lineage;
pub mod manifest;
pub mod replay;
pub mod patterns;
pub mod impact;
pub mod cost;

pub use stats::{fingerprint, predictor};
pub use replay::HistoricalReplayEngine;
pub use patterns::FailurePatternDetector;
pub use impact::BlastRadiusAnalyzer;
pub use cost::CostCalculator;

#[derive(Debug, Clone)]
pub struct AnalysisResult {
    pub test_name: String,
    pub reliability_score: f64,
    pub failure_probability: f64,
    pub stability_history: Vec<bool>,
}
