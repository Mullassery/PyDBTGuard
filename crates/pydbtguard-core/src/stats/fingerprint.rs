use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnFingerprint {
    pub column_name: String,
    pub row_count: u64,
    pub null_count: u64,
    pub unique_count: u64,
    pub cardinality_ratio: f64,
    pub min_value: Option<String>,
    pub max_value: Option<String>,
    pub value_distribution: HashMap<String, u64>,
}

impl ColumnFingerprint {
    pub fn new(column_name: String) -> Self {
        Self {
            column_name,
            row_count: 0,
            null_count: 0,
            unique_count: 0,
            cardinality_ratio: 0.0,
            min_value: None,
            max_value: None,
            value_distribution: HashMap::new(),
        }
    }

    pub fn null_ratio(&self) -> f64 {
        if self.row_count == 0 {
            0.0
        } else {
            self.null_count as f64 / self.row_count as f64
        }
    }

    pub fn distinctness(&self) -> f64 {
        if self.row_count == 0 {
            0.0
        } else {
            self.unique_count as f64 / self.row_count as f64
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataDrift {
    pub column_name: String,
    pub drift_detected: bool,
    pub null_ratio_change: f64,
    pub cardinality_change: f64,
    pub top_values_changed: bool,
}

pub fn detect_drift(
    baseline: &ColumnFingerprint,
    current: &ColumnFingerprint,
    null_threshold: f64,
    cardinality_threshold: f64,
) -> DataDrift {
    let null_ratio_change = (current.null_ratio() - baseline.null_ratio()).abs();
    let cardinality_change = (current.distinctness() - baseline.distinctness()).abs();

    let drift_detected =
        null_ratio_change > null_threshold || cardinality_change > cardinality_threshold;

    DataDrift {
        column_name: baseline.column_name.clone(),
        drift_detected,
        null_ratio_change,
        cardinality_change,
        top_values_changed: false,
    }
}
