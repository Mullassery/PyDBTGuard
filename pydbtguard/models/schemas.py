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
