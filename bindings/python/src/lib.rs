use pyo3::prelude::*;
use pydbtguard_core::stats::{fingerprint, predictor};

#[pyclass]
pub struct ColumnFingerprint {
    inner: fingerprint::ColumnFingerprint,
}

#[pymethods]
impl ColumnFingerprint {
    #[new]
    fn new(column_name: String) -> Self {
        Self {
            inner: fingerprint::ColumnFingerprint::new(column_name),
        }
    }

    fn null_ratio(&self) -> f64 {
        self.inner.null_ratio()
    }

    fn distinctness(&self) -> f64 {
        self.inner.distinctness()
    }

    fn __repr__(&self) -> String {
        format!(
            "ColumnFingerprint(name={}, nulls={}, distinct={})",
            self.inner.column_name,
            self.inner.null_count,
            self.inner.unique_count
        )
    }
}

#[pyclass]
pub struct FailurePredictor {
    inner: predictor::FailurePredictor,
}

#[pymethods]
impl FailurePredictor {
    #[new]
    fn new(lookback_days: u32) -> Self {
        Self {
            inner: predictor::FailurePredictor::new(lookback_days),
        }
    }

    fn predict_py(&self, failure_history: Vec<bool>) -> PyResult<(f64, f64, Vec<String>)> {
        let pattern =
            predictor::TestFailurePattern::new("test".to_string(), failure_history);
        let prediction = self.inner.predict(&pattern);

        Ok((
            prediction.failure_probability,
            prediction.confidence_score,
            prediction.likely_causes,
        ))
    }
}

#[pymodule]
fn pydbtguard(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<ColumnFingerprint>()?;
    m.add_class::<FailurePredictor>()?;
    Ok(())
}
