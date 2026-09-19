use super::{CostAnalysisResult, CostOptions, OptimizationOpportunity, QueryCost, TestCost};

pub struct CostCalculator {
    options: CostOptions,
}

impl CostCalculator {
    pub fn new(options: CostOptions) -> Self {
        Self { options }
    }

    pub fn calculate_query_cost(&self, bytes_scanned: u64) -> QueryCost {
        let credits = (bytes_scanned as f64) / (self.options.bytes_scanned_per_credit as f64);
        let cost_usd = credits * self.options.cost_per_credit_usd;

        QueryCost {
            query_id: format!("query_{}", chrono::Utc::now().timestamp()),
            bytes_scanned,
            warehouse_credits: credits,
            estimated_cost_usd: cost_usd,
            execution_time_ms: (bytes_scanned / 1024 / 1024 + 50), // Simplified estimation
        }
    }

    pub fn analyze_tests(
        &self,
        test_definitions: &[(String, String, String, u64)], // (name, type, frequency, avg_bytes)
    ) -> CostAnalysisResult {
        let mut result = CostAnalysisResult::new();

        for (test_name, test_type, frequency, avg_bytes) in test_definitions {
            let query_cost = self.calculate_query_cost(*avg_bytes);
            let runs_per_month = self.estimate_runs_per_month(frequency);

            let test_cost = TestCost {
                test_name: test_name.clone(),
                test_type: test_type.clone(),
                average_cost_usd: query_cost.estimated_cost_usd,
                average_execution_time_ms: query_cost.execution_time_ms,
                run_frequency: frequency.clone(),
                monthly_cost_usd: query_cost.estimated_cost_usd * (runs_per_month as f64),
                annual_cost_usd: query_cost.estimated_cost_usd * (runs_per_month as f64) * 12.0,
            };

            result.add_test_cost(test_cost);
        }

        // Identify optimization opportunities
        self.identify_optimizations(&mut result);

        result
    }

    fn estimate_runs_per_month(&self, frequency: &str) -> u32 {
        match frequency {
            "on-every-commit" => 250, // Roughly 8-10 commits per day, 25 days/month
            "daily" => 30,
            "nightly" => 30,
            "weekly" => 4,
            "monthly" => 1,
            _ => 30,
        }
    }

    fn identify_optimizations(&self, result: &mut CostAnalysisResult) {
        // Collect expensive tests first to avoid borrow conflicts
        let expensive_tests: Vec<_> = result
            .most_expensive_tests
            .iter()
            .take(5)
            .filter(|test| test.annual_cost_usd > 100.0)
            .map(|test| (test.test_name.clone(), test.annual_cost_usd))
            .collect();

        for (test_name, annual_cost) in expensive_tests {
            // Partition optimization
            let partition_savings = OptimizationOpportunity {
                test_name: test_name.clone(),
                optimization_type: "partition".to_string(),
                estimated_cost_reduction_percent: 60.0,
                estimated_savings_usd_annual: annual_cost * 0.6,
                implementation_effort: "medium".to_string(),
                recommendation: format!(
                    "Add partition filtering to reduce scan volume by ~60%. Estimated annual savings: ${:.2}",
                    annual_cost * 0.6
                ),
            };
            result.add_optimization(partition_savings);

            // Incremental validation
            let incremental_savings = OptimizationOpportunity {
                test_name: test_name.clone(),
                optimization_type: "incremental".to_string(),
                estimated_cost_reduction_percent: 45.0,
                estimated_savings_usd_annual: annual_cost * 0.45,
                implementation_effort: "medium".to_string(),
                recommendation: format!(
                    "Switch to incremental validation (last 24h). Estimated annual savings: ${:.2}",
                    annual_cost * 0.45
                ),
            };
            result.add_optimization(incremental_savings);
        }
    }
}

impl Default for CostCalculator {
    fn default() -> Self {
        Self::new(Default::default())
    }
}
