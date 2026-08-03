use serde::{Deserialize, Serialize};

pub mod engine;

pub use engine::HistoricalReplayEngine;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ReplaySnapshot {
    pub timestamp: String,
    pub table_name: String,
    pub row_count: u64,
    pub bytes_used: u64,
    pub schema_hash: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReplayResult {
    pub test_name: String,
    pub test_sql: String,
    pub passed: bool,
    pub timestamp: String,
    pub rows_affected: u64,
    pub execution_time_ms: u64,
    pub error_message: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalReliabilityCurve {
    pub test_name: String,
    pub results: Vec<ReplayResult>,
    pub pass_rate: f64,
    pub trend: String, // "improving", "degrading", "stable"
    pub failure_dates: Vec<String>,
    pub first_failure: Option<String>,
    pub last_failure: Option<String>,
    pub consecutive_passes: u32,
    pub mtbf_days: f64, // Mean Time Between Failures
}

impl HistoricalReliabilityCurve {
    pub fn new(test_name: String) -> Self {
        Self {
            test_name,
            results: Vec::new(),
            pass_rate: 1.0,
            trend: "stable".to_string(),
            failure_dates: Vec::new(),
            first_failure: None,
            last_failure: None,
            consecutive_passes: 0,
            mtbf_days: 0.0,
        }
    }

    pub fn add_result(&mut self, result: ReplayResult) {
        if !result.passed {
            self.failure_dates.push(result.timestamp.clone());
            if self.first_failure.is_none() {
                self.first_failure = Some(result.timestamp.clone());
            }
            self.last_failure = Some(result.timestamp.clone());
            self.consecutive_passes = 0;
        } else {
            self.consecutive_passes += 1;
        }

        self.results.push(result);
        self.recalculate_metrics();
    }

    fn recalculate_metrics(&mut self) {
        if self.results.is_empty() {
            return;
        }

        let pass_count = self.results.iter().filter(|r| r.passed).count();
        self.pass_rate = (pass_count as f64) / (self.results.len() as f64);

        // Calculate trend
        if self.results.len() >= 10 {
            let recent = &self.results[self.results.len() - 10..];
            let recent_passes = recent.iter().filter(|r| r.passed).count();
            let recent_rate = (recent_passes as f64) / 10.0;

            if recent_rate > self.pass_rate + 0.1 {
                self.trend = "improving".to_string();
            } else if recent_rate < self.pass_rate - 0.1 {
                self.trend = "degrading".to_string();
            } else {
                self.trend = "stable".to_string();
            }
        }

        // Calculate MTBF
        if self.failure_dates.len() > 1 {
            self.mtbf_days = (self.results.len() as f64) / ((self.failure_dates.len() - 1) as f64);
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReplayOptions {
    pub lookback_days: u32,
    pub sample_rate: f64, // 0.0-1.0, for cost reduction
    pub include_error_messages: bool,
    pub parallel_tests: bool,
}

impl Default for ReplayOptions {
    fn default() -> Self {
        Self {
            lookback_days: 180,
            sample_rate: 1.0,
            include_error_messages: true,
            parallel_tests: true,
        }
    }
}
