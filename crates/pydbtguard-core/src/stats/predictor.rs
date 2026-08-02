use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestFailurePattern {
    pub test_name: String,
    pub failure_history: Vec<bool>,
    pub historical_stability: f64,
    pub failure_rate: f64,
    pub common_causes: Vec<String>,
}

impl TestFailurePattern {
    pub fn new(test_name: String, failure_history: Vec<bool>) -> Self {
        let failure_count = failure_history.iter().filter(|&&f| f).count();
        let total = failure_history.len();
        let failure_rate = if total == 0 {
            0.0
        } else {
            failure_count as f64 / total as f64
        };

        let historical_stability = 1.0 - failure_rate;

        Self {
            test_name,
            failure_history,
            historical_stability,
            failure_rate,
            common_causes: vec![],
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FailurePrediction {
    pub test_name: String,
    pub failure_probability: f64,
    pub confidence_score: f64,
    pub likely_causes: Vec<String>,
    pub recommended_action: String,
}

pub struct FailurePredictor {
    lookback_days: u32,
}

impl FailurePredictor {
    pub fn new(lookback_days: u32) -> Self {
        Self { lookback_days }
    }

    pub fn predict(&self, pattern: &TestFailurePattern) -> FailurePrediction {
        let failure_probability = pattern.failure_rate;

        let confidence_score = if pattern.failure_history.len() >= 30 {
            0.95
        } else if pattern.failure_history.len() >= 14 {
            0.75
        } else {
            0.50
        };

        let mut likely_causes = pattern.common_causes.clone();
        if likely_causes.is_empty() {
            likely_causes = vec!["Unknown pattern".to_string()];
        }

        let recommended_action = if failure_probability > 0.3 {
            "Consider converting to warning or investigating root cause".to_string()
        } else if failure_probability > 0.1 {
            "Monitor closely for patterns".to_string()
        } else {
            "Test appears stable".to_string()
        };

        FailurePrediction {
            test_name: pattern.test_name.clone(),
            failure_probability,
            confidence_score,
            likely_causes,
            recommended_action,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_failure_pattern_creation() {
        let history = vec![true, true, false, false, false];
        let pattern = TestFailurePattern::new("test_unique".to_string(), history);
        assert_eq!(pattern.failure_rate, 0.4);
        assert_eq!(pattern.historical_stability, 0.6);
    }

    #[test]
    fn test_failure_prediction() {
        let history = vec![true, false, false, false, false];
        let pattern = TestFailurePattern::new("test_unique".to_string(), history);
        let predictor = FailurePredictor::new(180);
        let prediction = predictor.predict(&pattern);
        assert_eq!(prediction.failure_probability, 0.2);
    }
}
