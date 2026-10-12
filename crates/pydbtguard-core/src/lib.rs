//! PyDBTGuard analysis engine.
//!
//! Reads real, locally-produced dbt artifacts and produces real reports. There
//! is no warehouse connection anywhere in this crate: `manifest.json`,
//! `catalog.json`, `run_results.json`, and `sources.json` are the only inputs.
//!
//! The [`api`] module is the intended entry point for host bindings: each
//! function takes artifact text and returns a JSON report string.

pub mod api;
pub mod cost;
pub mod coverage;
pub mod drift;
pub mod error;
pub mod freshness;
pub mod history;
pub mod lineage;
pub mod model;
pub mod stats;

pub use api::VERSION;
pub use error::{Error, Result};
