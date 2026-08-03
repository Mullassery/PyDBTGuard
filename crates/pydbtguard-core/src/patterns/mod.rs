use serde::{Deserialize, Serialize};

pub mod detector;

pub use detector::FailurePatternDetector;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum PatternType {
    DuplicateSpike,
    SeasonalAnomaly,
    BackfillSensitivity,
    CDCReplayEvent,
    LateArrivingData,
    VolumeSurge,
    SchemaChange,
    TimeZoneShift,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FailurePattern {
    pub pattern_type: PatternType,
    pub test_name: String,
    pub confidence: f64,      // 0.0-1.0
    pub severity: String,      // CRITICAL, HIGH, MEDIUM, LOW
    pub description: String,
    pub evidence: Vec<String>,
    pub detected_at: String,
    pub suggested_fix: String,
}

impl FailurePattern {
    pub fn new(pattern_type: PatternType, test_name: String) -> Self {
        Self {
            pattern_type,
            test_name,
            confidence: 0.0,
            severity: "LOW".to_string(),
            description: String::new(),
            evidence: Vec::new(),
            detected_at: chrono::Utc::now().to_rfc3339(),
            suggested_fix: String::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnMetrics {
    pub column_name: String,
    pub null_count: u64,
    pub unique_count: u64,
    pub max_value: Option<String>,
    pub min_value: Option<String>,
    pub distinct_ratio: f64,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableSnapshot {
    pub table_name: String,
    pub row_count: u64,
    pub schema_hash: String,
    pub columns: Vec<ColumnMetrics>,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyScore {
    pub metric_name: String,
    pub current_value: f64,
    pub historical_mean: f64,
    pub historical_stddev: f64,
    pub z_score: f64,
    pub is_anomaly: bool, // z_score > 2 or < -2
}

#[derive(Debug, Clone)]
pub struct PatternDetectionResult {
    pub patterns: Vec<FailurePattern>,
    pub anomalies: Vec<AnomalyScore>,
    pub high_severity_count: usize,
    pub recommended_actions: Vec<String>,
}

impl PatternDetectionResult {
    pub fn new() -> Self {
        Self {
            patterns: Vec::new(),
            anomalies: Vec::new(),
            high_severity_count: 0,
            recommended_actions: Vec::new(),
        }
    }

    pub fn add_pattern(&mut self, pattern: FailurePattern) {
        if pattern.severity == "CRITICAL" || pattern.severity == "HIGH" {
            self.high_severity_count += 1;
        }
        self.patterns.push(pattern);
    }

    pub fn add_anomaly(&mut self, anomaly: AnomalyScore) {
        self.anomalies.push(anomaly);
    }

    pub fn add_recommendation(&mut self, action: String) {
        self.recommended_actions.push(action);
    }
}

impl Default for PatternDetectionResult {
    fn default() -> Self {
        Self::new()
    }
}
