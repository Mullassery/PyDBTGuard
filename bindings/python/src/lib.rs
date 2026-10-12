//! Thin PyO3 shim over `pydbtguard_core::api`.
//!
//! Each function takes the exact text of a dbt artifact (or the accumulated
//! history file) and returns a JSON report string. All parsing, analysis, and
//! error handling live in the Rust core, so the Python layer is only I/O and
//! presentation. Errors surface as `ValueError` with the core's message.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

fn wrap(result: Result<String, pydbtguard_core::Error>) -> PyResult<String> {
    result.map_err(|err| PyValueError::new_err(err.to_string()))
}

/// Reliability scoring + failure prediction for every test.
#[pyfunction]
fn analyze(manifest_json: &str, history_jsonl: &str) -> PyResult<String> {
    wrap(pydbtguard_core::api::analyze(manifest_json, history_jsonl))
}

/// Test-coverage gap analysis. `catalog_json` may be empty.
#[pyfunction]
fn coverage(manifest_json: &str, catalog_json: &str) -> PyResult<String> {
    wrap(pydbtguard_core::api::coverage_report(
        manifest_json,
        catalog_json,
    ))
}

/// Blast radius for a single model id.
#[pyfunction]
fn blast_radius(manifest_json: &str, model_id: &str) -> PyResult<String> {
    wrap(pydbtguard_core::api::blast_radius_report(
        manifest_json,
        model_id,
    ))
}

/// Per-scan cost estimate from real catalog bytes.
#[pyfunction]
#[pyo3(signature = (manifest_json, catalog_json, adapter_override=None))]
fn cost(
    manifest_json: &str,
    catalog_json: &str,
    adapter_override: Option<String>,
) -> PyResult<String> {
    wrap(pydbtguard_core::api::cost_report(
        manifest_json,
        catalog_json,
        adapter_override.as_deref(),
    ))
}

/// Historical reliability from the accumulated run-history file.
#[pyfunction]
fn history(history_jsonl: &str) -> PyResult<String> {
    wrap(pydbtguard_core::api::history_report(history_jsonl))
}

/// Source freshness from `sources.json`. `manifest_json` may be empty.
#[pyfunction]
fn freshness(sources_json: &str, manifest_json: &str) -> PyResult<String> {
    wrap(pydbtguard_core::api::freshness_report(
        sources_json,
        manifest_json,
    ))
}

/// Schema/volume drift between two catalog snapshots.
#[pyfunction]
fn drift(old_catalog_json: &str, new_catalog_json: &str) -> PyResult<String> {
    wrap(pydbtguard_core::api::drift_report(
        old_catalog_json,
        new_catalog_json,
    ))
}

/// The engine version, shared with `pydbtguard.__version__`.
#[pyfunction]
fn engine_version() -> &'static str {
    pydbtguard_core::VERSION
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(analyze, m)?)?;
    m.add_function(wrap_pyfunction!(coverage, m)?)?;
    m.add_function(wrap_pyfunction!(blast_radius, m)?)?;
    m.add_function(wrap_pyfunction!(cost, m)?)?;
    m.add_function(wrap_pyfunction!(history, m)?)?;
    m.add_function(wrap_pyfunction!(freshness, m)?)?;
    m.add_function(wrap_pyfunction!(drift, m)?)?;
    m.add_function(wrap_pyfunction!(engine_version, m)?)?;
    m.add("__version__", pydbtguard_core::VERSION)?;
    Ok(())
}
