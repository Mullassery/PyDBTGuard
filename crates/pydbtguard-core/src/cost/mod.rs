use serde::{Deserialize, Serialize};

pub mod calculator;

pub use calculator::CostCalculator;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryCost {
    pub query_id: String,
    pub bytes_scanned: u64,
    pub warehouse_credits: f64,
    pub estimated_cost_usd: f64,
    pub execution_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestCost {
    pub test_name: String,
    pub test_type: String,
    pub average_cost_usd: f64,
    pub average_execution_time_ms: u64,
    pub run_frequency: String, // "on-every-commit", "nightly", "weekly"
    pub monthly_cost_usd: f64,
    pub annual_cost_usd: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostAnalysisResult {
    pub total_tests: usize,
    pub total_monthly_cost_usd: f64,
    pub total_annual_cost_usd: f64,
    pub cost_by_test_type: std::collections::HashMap<String, f64>,
    pub cost_by_model: std::collections::HashMap<String, f64>,
    pub most_expensive_tests: Vec<TestCost>,
    pub cost_optimization_opportunities: Vec<OptimizationOpportunity>,
    pub estimated_savings_usd: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationOpportunity {
    pub test_name: String,
    pub optimization_type: String, // "partition", "incremental", "caching", "sampling"
    pub estimated_cost_reduction_percent: f64,
    pub estimated_savings_usd_annual: f64,
    pub implementation_effort: String, // "low", "medium", "high"
    pub recommendation: String,
}

impl CostAnalysisResult {
    pub fn new() -> Self {
        Self {
            total_tests: 0,
            total_monthly_cost_usd: 0.0,
            total_annual_cost_usd: 0.0,
            cost_by_test_type: std::collections::HashMap::new(),
            cost_by_model: std::collections::HashMap::new(),
            most_expensive_tests: Vec::new(),
            cost_optimization_opportunities: Vec::new(),
            estimated_savings_usd: 0.0,
        }
    }

    pub fn add_test_cost(&mut self, test: TestCost) {
        self.total_tests += 1;
        self.total_monthly_cost_usd += test.monthly_cost_usd;
        self.total_annual_cost_usd += test.annual_cost_usd;

        *self
            .cost_by_test_type
            .entry(test.test_type.clone())
            .or_insert(0.0) += test.annual_cost_usd;

        self.most_expensive_tests.push(test);
        self.most_expensive_tests.sort_by(|a, b| {
            b.annual_cost_usd
                .partial_cmp(&a.annual_cost_usd)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        if self.most_expensive_tests.len() > 10 {
            self.most_expensive_tests.pop();
        }
    }

    pub fn add_optimization(&mut self, opportunity: OptimizationOpportunity) {
        self.estimated_savings_usd += opportunity.estimated_savings_usd_annual;
        self.cost_optimization_opportunities.push(opportunity);
    }
}

impl Default for CostAnalysisResult {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone)]
pub struct CostOptions {
    pub warehouse_type: String,
    pub cost_per_credit_usd: f64,
    pub bytes_scanned_per_credit: u64,
}

impl Default for CostOptions {
    fn default() -> Self {
        Self {
            warehouse_type: "snowflake".to_string(),
            cost_per_credit_usd: 4.0,
            bytes_scanned_per_credit: 1024 * 1024 * 1024, // 1 GB = 1 credit
        }
    }
}
