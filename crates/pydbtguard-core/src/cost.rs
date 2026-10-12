//! Cost estimation from real `catalog.json` table statistics.
//!
//! There is no warehouse connection here and no measured query cost. The
//! honest inputs available locally are the real `bytes`/`row_count` values
//! that `dbt docs generate` writes into `catalog.json` by querying the
//! warehouse's own metadata tables. A test is modelled as scanning the table
//! its attached model materialises, so `scanned_bytes` is that table's real
//! size, and the dollar figure is a transparent estimate:
//! `bytes / 1e12 * price_per_tb_usd`. Adapters without a configured per-byte
//! price report `null` cost rather than a fabricated number.

use crate::model::{Catalog, Manifest};
use serde::Serialize;

const GIB: u64 = 1 << 30;

#[derive(Debug, Clone, Serialize)]
pub struct TestCost {
    pub test_name: String,
    pub test_type: String,
    pub attached_model: Option<String>,
    pub scanned_bytes: Option<u64>,
    pub row_count: Option<u64>,
    pub estimated_cost_usd_per_scan: Option<f64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Optimization {
    pub test_name: String,
    pub attached_model: String,
    pub optimization_type: String,
    pub recommendation: String,
    pub basis_bytes: u64,
    pub estimated_savings_usd_per_scan: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct CostReport {
    pub adapter_type: Option<String>,
    pub price_per_tb_usd: Option<f64>,
    pub total_tests: usize,
    pub priced_tests: usize,
    pub total_estimated_cost_usd_per_scan: f64,
    pub most_expensive_tests: Vec<TestCost>,
    pub optimizations: Vec<Optimization>,
    pub note: String,
}

/// On-demand, per-terabyte-scanned list prices. Snowflake is credit-priced
/// rather than byte-priced; its entry is a documented nominal
/// bytes-scanned-equivalent, not an invoice figure. Local engines are free.
fn price_per_tb(adapter: Option<&str>) -> Option<f64> {
    match adapter.map(str::to_lowercase).as_deref() {
        Some("bigquery") => Some(6.25),
        Some("snowflake") => Some(2.00),
        Some("duckdb") | Some("postgres") | Some("sqlite") | Some("redshift") => Some(0.0),
        _ => None,
    }
}

fn cost_for(bytes: Option<u64>, price: Option<f64>) -> Option<f64> {
    match (bytes, price) {
        (Some(b), Some(p)) => Some(b as f64 / 1e12 * p),
        _ => None,
    }
}

/// Estimate per-scan cost for every test in the manifest.
pub fn analyze(
    manifest: &Manifest,
    catalog: &Catalog,
    adapter_override: Option<&str>,
) -> CostReport {
    let adapter = adapter_override
        .map(str::to_string)
        .or_else(|| manifest.metadata.adapter_type.clone());
    let price = price_per_tb(adapter.as_deref());

    let mut tests = Vec::new();
    let mut optimizations = Vec::new();

    for (_, test) in manifest.tests() {
        let attached = test.attached_node().map(str::to_string);
        let model_stat = attached.as_deref().and_then(|id| catalog.get(id));

        let bytes = model_stat.and_then(|n| n.bytes());
        let row_count = model_stat.and_then(|n| n.row_count());
        let cost = cost_for(bytes, price);

        tests.push(TestCost {
            test_name: test.name.clone(),
            test_type: test.test_type(),
            attached_model: attached.clone(),
            scanned_bytes: bytes,
            row_count,
            estimated_cost_usd_per_scan: cost,
        });

        if let (Some(model_id), Some(b)) = (attached.as_deref(), bytes) {
            if b >= GIB {
                optimizations.push(Optimization {
                    test_name: test.name.clone(),
                    attached_model: model_id.to_string(),
                    optimization_type: "partition".to_string(),
                    recommendation: format!(
                        "Add a date/partition filter (or 'where' config) to {}; the attached \
                         table is {:.1} GiB and is scanned in full.",
                        test.name,
                        b as f64 / GIB as f64
                    ),
                    basis_bytes: b,
                    estimated_savings_usd_per_scan: cost_for(Some(b), price).unwrap_or(0.0) * 0.6,
                });
            }
        }
    }

    let total: f64 = tests
        .iter()
        .filter_map(|t| t.estimated_cost_usd_per_scan)
        .sum();
    let priced_tests = tests
        .iter()
        .filter(|t| t.estimated_cost_usd_per_scan.is_some())
        .count();

    tests.sort_by(|a, b| {
        b.estimated_cost_usd_per_scan
            .unwrap_or(0.0)
            .partial_cmp(&a.estimated_cost_usd_per_scan.unwrap_or(0.0))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    optimizations.sort_by(|a, b| {
        b.estimated_savings_usd_per_scan
            .partial_cmp(&a.estimated_savings_usd_per_scan)
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    let note = match price {
        Some(0.0) => {
            "Local/self-hosted engine: no per-scan cloud cost. Byte volumes are still real."
                .to_string()
        }
        Some(_) => "Estimated from real catalog.json table bytes and a fixed per-TB price; \
                    this is an estimate, not a warehouse invoice."
            .to_string(),
        None => format!(
            "No per-byte price configured for adapter {:?}; byte volumes are real, costs are null.",
            adapter.as_deref().unwrap_or("unknown")
        ),
    };

    let mut most_expensive = tests.clone();
    most_expensive.truncate(10);

    CostReport {
        adapter_type: adapter,
        price_per_tb_usd: price,
        total_tests: tests.len(),
        priced_tests,
        total_estimated_cost_usd_per_scan: total,
        most_expensive_tests: most_expensive,
        optimizations,
        note,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn manifest() -> Manifest {
        let json = serde_json::json!({
            "metadata": {"adapter_type": "bigquery"},
            "nodes": {
                "model.pkg.big": {
                    "unique_id": "model.pkg.big", "name": "big", "resource_type": "model"
                },
                "test.pkg.unique_big_id": {
                    "unique_id": "test.pkg.unique_big_id", "name": "unique_big_id",
                    "resource_type": "test", "test_metadata": {"name": "unique"},
                    "depends_on": {"nodes": ["model.pkg.big"]}
                }
            }
        });
        let mut m: Manifest = serde_json::from_value(json).unwrap();
        m.normalize();
        m
    }

    fn catalog() -> Catalog {
        let json = serde_json::json!({
            "nodes": {
                "model.pkg.big": {
                    "unique_id": "model.pkg.big",
                    "stats": {
                        "row_count": {"value": 2000000},
                        "bytes": {"value": 2_000_000_000_000u64}
                    }
                }
            }
        });
        serde_json::from_value(json).unwrap()
    }

    #[test]
    fn cost_is_real_arithmetic_on_catalog_bytes() {
        let report = analyze(&manifest(), &catalog(), None);
        assert_eq!(report.adapter_type.as_deref(), Some("bigquery"));
        assert_eq!(report.price_per_tb_usd, Some(6.25));
        let t = &report.most_expensive_tests[0];
        assert_eq!(t.scanned_bytes, Some(2_000_000_000_000));
        // 2 TB * 6.25 = 12.50
        assert!((t.estimated_cost_usd_per_scan.unwrap() - 12.5).abs() < 1e-9);
        assert_eq!(report.optimizations.len(), 1);
        assert!((report.optimizations[0].estimated_savings_usd_per_scan - 7.5).abs() < 1e-9);
    }

    #[test]
    fn unknown_adapter_reports_null_cost_but_real_bytes() {
        let mut m = manifest();
        m.metadata.adapter_type = Some("mystery".into());
        let report = analyze(&m, &catalog(), None);
        assert!(report.price_per_tb_usd.is_none());
        assert_eq!(
            report.most_expensive_tests[0].scanned_bytes,
            Some(2_000_000_000_000)
        );
        assert!(report.most_expensive_tests[0]
            .estimated_cost_usd_per_scan
            .is_none());
        assert!(report.note.contains("No per-byte price"));
    }
}
