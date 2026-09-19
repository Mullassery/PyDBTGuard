pub mod cost;
pub mod impact;
pub mod lineage;
pub mod manifest;
pub mod patterns;
pub mod replay;
pub mod stats;

pub use cost::CostCalculator;
pub use impact::BlastRadiusAnalyzer;
pub use patterns::FailurePatternDetector;
pub use replay::HistoricalReplayEngine;
pub use stats::{fingerprint, predictor};

#[derive(Debug, Clone)]
pub struct AnalysisResult {
    pub test_name: String,
    pub reliability_score: f64,
    pub failure_probability: f64,
    pub stability_history: Vec<bool>,
}
