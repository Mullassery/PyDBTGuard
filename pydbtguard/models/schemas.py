from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class RiskLevel(str, Enum):
    """Risk levels for tests"""

    STABLE = "STABLE"
    AT_RISK = "AT_RISK"
    DANGEROUS = "DANGEROUS"


@dataclass
class ReliabilityScore:
    """Reliability score for a test"""

    score: int
    stability_history: float
    failure_probability: float
    confidence: float

    def __post_init__(self):
        if not (0 <= self.score <= 100):
            raise ValueError("Score must be between 0 and 100")


@dataclass
class TestAnalysis:
    """Analysis of a single test"""

    name: str
    unique_id: str
    test_type: str
    attached_node: Optional[str]
    reliability_score: ReliabilityScore
    risk_level: RiskLevel
    recommendations: List[str]
    tags: List[str] = None
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.config is None:
            self.config = {}


@dataclass
class AnalysisReport:
    """Complete analysis report"""

    version: str
    total_tests: int
    tests: List[TestAnalysis]
    stable_count: int
    at_risk_count: int
    dangerous_count: int
    timestamp: str


@dataclass
class HistoricalReplayResult:
    """Result from historical replay analysis"""

    test_name: str
    pass_rate: float
    trend: str  # "improving", "degrading", "stable"
    mtbf_days: float
    failure_dates: List[str]
    consecutive_passes: int
    volatility: float  # 0-1, frequency of pass/fail transitions


@dataclass
class FailurePatternAnalysis:
    """Detected failure patterns"""

    test_name: str
    patterns: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    high_severity_count: int
    recommended_actions: List[str]


@dataclass
class BlastRadiusAnalysis:
    """Impact analysis for failing tests"""

    source_model: str
    total_affected_models: int
    critical_impact_count: int
    high_impact_count: int
    estimated_users_affected: int
    overall_score: float  # 0-100
    estimated_recovery_hours: float
    affected_models: List[Dict[str, Any]]
    exposures_at_risk: List[str]
    recommendations: List[str]


@dataclass
class TestCostAnalysis:
    """Cost analysis for test execution"""

    test_name: str
    test_type: str
    average_cost_usd: float
    average_execution_time_ms: int
    run_frequency: str
    monthly_cost_usd: float
    annual_cost_usd: float


@dataclass
class CostOptimizationOpportunity:
    """Suggested cost optimization"""

    test_name: str
    optimization_type: str  # "partition", "incremental", "caching", "sampling"
    estimated_cost_reduction_percent: float
    estimated_savings_usd_annual: float
    implementation_effort: str  # "low", "medium", "high"
    recommendation: str


@dataclass
class CostAnalysisReport:
    """Complete cost analysis"""

    total_tests: int
    total_monthly_cost_usd: float
    total_annual_cost_usd: float
    cost_by_test_type: Dict[str, float]
    most_expensive_tests: List[TestCostAnalysis]
    optimization_opportunities: List[CostOptimizationOpportunity]
    estimated_savings_usd: float


@dataclass
class DiagnosticPlan:
    """Diagnostic plan for test failure"""

    test_name: str
    likely_causes: List[str]
    diagnostic_tests: List[str]  # Tests to run to diagnose
    correlation_scores: Dict[str, float]  # Other tests correlated with this one
    pattern_matches: List[str]


@dataclass
class OptimizationSuggestion:
    """Suggested test optimization"""

    test_name: str
    test_sql: str
    optimization_type: str  # "partition", "incremental", "caching"
    suggested_sql: str
    estimated_latency_reduction_percent: float
    estimated_cost_reduction_percent: float
    effort_level: str  # "low", "medium", "high"
    risk_level: str  # "low", "medium", "high"


@dataclass
class CoverageGap:
    """Identified gap in test coverage"""

    model_name: str
    model_id: str
    risk_score: float  # 0-100
    freshness_sla_hours: Optional[int]
    bi_dependencies: int
    row_count: int
    missing_test_types: List[str]  # ["unique", "not_null", "relationships"]
    recommended_tests: List[str]
    priority: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
