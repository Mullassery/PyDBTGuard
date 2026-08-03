use super::{AnomalyScore, FailurePattern, PatternDetectionResult, PatternType, TableSnapshot};
use std::collections::HashMap;

pub struct FailurePatternDetector;

impl FailurePatternDetector {
    pub fn new() -> Self {
        Self
    }

    pub fn detect_patterns(
        &self,
        test_name: &str,
        snapshots: &[TableSnapshot],
    ) -> PatternDetectionResult {
        let mut result = PatternDetectionResult::new();

        if snapshots.len() < 2 {
            return result;
        }

        // Detect duplicate spike
        if let Some(pattern) = self.detect_duplicate_spike(test_name, snapshots) {
            result.add_pattern(pattern);
        }

        // Detect seasonal anomalies
        if let Some(patterns) = self.detect_seasonal_anomalies(test_name, snapshots) {
            for pattern in patterns {
                result.add_pattern(pattern);
            }
        }

        // Detect backfill sensitivity
        if let Some(pattern) = self.detect_backfill_sensitivity(test_name, snapshots) {
            result.add_pattern(pattern);
        }

        // Detect volume surge
        if let Some(pattern) = self.detect_volume_surge(test_name, snapshots) {
            result.add_pattern(pattern);
        }

        // Calculate anomalies
        let anomalies = self.calculate_column_anomalies(snapshots);
        for anomaly in anomalies {
            result.add_anomaly(anomaly);
        }

        // Generate recommendations
        self.generate_recommendations(&result);

        result
    }

    fn detect_duplicate_spike(
        &self,
        test_name: &str,
        snapshots: &[TableSnapshot],
    ) -> Option<FailurePattern> {
        if snapshots.len() < 2 {
            return None;
        }

        let mut pattern = FailurePattern::new(PatternType::DuplicateSpike, test_name.to_string());
        let mut found = false;

        for i in 1..snapshots.len() {
            let prev = &snapshots[i - 1];
            let curr = &snapshots[i];

            // Check for cardinality spike in any column
            for col in &curr.columns {
                if let Some(prev_col) = prev.columns.iter().find(|c| c.column_name == col.column_name) {
                    if col.unique_count > 0 && prev_col.unique_count > 0 {
                        let cardinality_ratio = (col.unique_count as f64) / (prev_col.unique_count as f64);
                        if cardinality_ratio < 0.5 {
                            // Cardinality dropped by >50%
                            pattern.evidence.push(format!(
                                "Column {} cardinality dropped from {} to {}",
                                col.column_name, prev_col.unique_count, col.unique_count
                            ));
                            pattern.confidence += 0.3;
                            found = true;
                        }
                    }
                }
            }
        }

        if found {
            pattern.confidence = pattern.confidence.min(1.0);
            pattern.severity = if pattern.confidence > 0.7 {
                "HIGH".to_string()
            } else {
                "MEDIUM".to_string()
            };
            pattern.description = "Detected duplicate spike: cardinality decreased significantly".to_string();
            pattern.suggested_fix = "Check for duplicate rows or incorrect joins".to_string();
            Some(pattern)
        } else {
            None
        }
    }

    fn detect_seasonal_anomalies(
        &self,
        test_name: &str,
        snapshots: &[TableSnapshot],
    ) -> Option<Vec<FailurePattern>> {
        if snapshots.len() < 7 {
            return None;
        }

        let mut patterns = Vec::new();

        // Simplified: detect if row count varies significantly
        let row_counts: Vec<u64> = snapshots.iter().map(|s| s.row_count).collect();
        let mean = (row_counts.iter().sum::<u64>() as f64) / (row_counts.len() as f64);
        let variance = row_counts
            .iter()
            .map(|&v| ((v as f64) - mean).powi(2))
            .sum::<f64>()
            / (row_counts.len() as f64);
        let stddev = variance.sqrt();

        // If coefficient of variation > 0.2, likely seasonal
        if stddev / mean > 0.2 {
            let mut pattern = FailurePattern::new(PatternType::SeasonalAnomaly, test_name.to_string());
            pattern.description = "Detected seasonal variation in table size".to_string();
            pattern.confidence = (stddev / mean / 0.4).min(1.0);
            pattern.severity = "MEDIUM".to_string();
            pattern.evidence.push(format!("Row count mean: {:.0}, stddev: {:.0}", mean, stddev));
            pattern.suggested_fix = "Consider using seasonal adjustments in test logic".to_string();
            patterns.push(pattern);
        }

        if patterns.is_empty() {
            None
        } else {
            Some(patterns)
        }
    }

    fn detect_backfill_sensitivity(
        &self,
        test_name: &str,
        snapshots: &[TableSnapshot],
    ) -> Option<FailurePattern> {
        if snapshots.len() < 2 {
            return None;
        }

        let curr = &snapshots[snapshots.len() - 1];
        let prev = &snapshots[snapshots.len() - 2];

        let row_increase = (curr.row_count as i64) - (prev.row_count as i64);
        if row_increase > (prev.row_count as i64 / 2) {
            // > 50% increase
            let mut pattern = FailurePattern::new(PatternType::BackfillSensitivity, test_name.to_string());
            pattern.description = "Detected bulk insert/backfill operation".to_string();
            pattern.confidence = 0.8;
            pattern.severity = "MEDIUM".to_string();
            pattern.evidence.push(format!("Row count increased by {} ({:.1}%)",
                row_increase,
                (row_increase as f64 / prev.row_count as f64 * 100.0)
            ));
            pattern.suggested_fix = "Consider adding incremental validation or sample-based testing".to_string();
            Some(pattern)
        } else {
            None
        }
    }

    fn detect_volume_surge(
        &self,
        test_name: &str,
        snapshots: &[TableSnapshot],
    ) -> Option<FailurePattern> {
        if snapshots.len() < 3 {
            return None;
        }

        let recent = &snapshots[snapshots.len() - 3..];
        let bytes: Vec<u64> = recent.iter().map(|_| 1000).collect(); // Placeholder
        let mean = (bytes.iter().sum::<u64>() as f64) / (bytes.len() as f64);
        let max = bytes.iter().max().copied().unwrap_or(0) as f64;

        if max > mean * 2.0 {
            let mut pattern = FailurePattern::new(PatternType::VolumeSurge, test_name.to_string());
            pattern.description = "Detected volume surge in data".to_string();
            pattern.confidence = 0.7;
            pattern.severity = "MEDIUM".to_string();
            pattern.evidence.push(format!("Max volume {:.1}x mean", max / mean));
            pattern.suggested_fix = "Consider adding volume-aware assertions".to_string();
            Some(pattern)
        } else {
            None
        }
    }

    fn calculate_column_anomalies(&self, snapshots: &[TableSnapshot]) -> Vec<AnomalyScore> {
        let mut anomalies = Vec::new();

        if snapshots.len() < 3 {
            return anomalies;
        }

        // Collect metrics per column
        let mut column_history: HashMap<String, Vec<f64>> = HashMap::new();

        for snapshot in snapshots {
            for col in &snapshot.columns {
                column_history
                    .entry(col.column_name.clone())
                    .or_insert_with(Vec::new)
                    .push(col.distinct_ratio);
            }
        }

        // Calculate z-scores for latest values
        for (col_name, ratios) in column_history {
            if ratios.len() < 3 {
                continue;
            }

            let mean = ratios.iter().sum::<f64>() / (ratios.len() as f64);
            let variance = ratios
                .iter()
                .map(|r| (r - mean).powi(2))
                .sum::<f64>()
                / (ratios.len() as f64);
            let stddev = variance.sqrt();

            if stddev > 0.0 {
                let latest = ratios[ratios.len() - 1];
                let z_score = (latest - mean) / stddev;
                let is_anomaly = z_score.abs() > 2.0;

                anomalies.push(AnomalyScore {
                    metric_name: format!("distinct_ratio:{}", col_name),
                    current_value: latest,
                    historical_mean: mean,
                    historical_stddev: stddev,
                    z_score,
                    is_anomaly,
                });
            }
        }

        anomalies
    }

    fn generate_recommendations(&self, result: &PatternDetectionResult) {
        if result.high_severity_count > 0 {
            // recommendations handled elsewhere
        }
    }
}

impl Default for FailurePatternDetector {
    fn default() -> Self {
        Self::new()
    }
}
