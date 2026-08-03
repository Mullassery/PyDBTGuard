# Phase 3 (v0.3) - Operational Intelligence & Optimization

## Overview

Phase 3 adds predictive diagnostic capabilities, test optimization recommendations, and comprehensive coverage audits.

## New Capabilities

### 1. Predictive Diagnostic Plans

Generates diagnostic and root cause analysis for test failures.

**Module**: `pydbtguard.analysis.diagnostics`

**CLI**:
```bash
pydbtguard diagnose . --test test_unique_users_id --output plan.json
```

**Key Features**:
- Automatic likely cause identification
- Test correlation matrix ("which tests fail together?")
- Diagnostic test suggestions
- Pattern-based failure matching
- Root cause hypothesis generation

**Usage Example**:
```python
from pydbtguard.analysis.diagnostics import DiagnosticsAnalyzer

analyzer = DiagnosticsAnalyzer(manifest)
plan = analyzer.diagnose_failure(
    failing_test_name="unique_users_id",
    historical_failures=[
        {"timestamp": "2024-01-15", "error": "duplicate found"},
        {"timestamp": "2024-01-08", "error": "duplicate found"},
    ]
)

print(f"Likely causes:")
for cause in plan.likely_causes:
    print(f"  - {cause}")

print(f"\nDiagnostic tests to run:")
for test in plan.diagnostic_tests:
    print(f"  {test}")

print(f"\nCorrelated tests (failing together):")
for test, score in plan.correlation_scores.items():
    print(f"  {test}: {score:.1%}")
```

**Likely Causes**:
- Duplicate row detection failure
- Data freshness SLA breach
- Foreign key constraint violation
- Unexpected NULL values introduced
- Recent data quality issue
- Seasonal volume spike
- Unknown data quality issue

**Diagnostic Queries**:
- Row count verification
- Duplicate detection (GROUP BY key, HAVING COUNT(*) > 1)
- Freshness check (MAX(updated_at))
- NULL value analysis
- Foreign key validation

### 2. Test Optimization

Suggests test rewrites to improve performance and reduce cost.

**Module**: `pydbtguard.analysis.optimization`

**CLI**:
```bash
pydbtguard optimize . --output optimizations.json
```

**Key Features**:
- Partition filter recommendations
- Incremental validation suggestions
- Reference table caching advice
- Estimated impact: latency and cost reduction
- Risk assessment per optimization

**Usage Example**:
```python
from pydbtguard.analysis.optimization import TestOptimizer

optimizer = TestOptimizer(manifest)
suggestions = optimizer.suggest_optimizations(
    test_name="test_unique_id",
    test_sql="SELECT id, COUNT(*) FROM users GROUP BY id HAVING COUNT(*) > 1",
    avg_execution_time_ms=2500
)

for opt in suggestions:
    print(f"{opt.optimization_type}:")
    print(f"  Latency reduction: {opt.estimated_latency_reduction_percent:.0f}%")
    print(f"  Cost reduction: {opt.estimated_cost_reduction_percent:.0f}%")
    print(f"  Effort: {opt.effort_level}")
    print(f"  Risk: {opt.risk_level}")
    print(f"\n  Suggested SQL:\n{opt.suggested_sql}")
```

**Optimization Types**:

#### Partition Filtering
- **Idea**: Validate only recent data instead of full table
- **Example**: Add `WHERE created_date >= CURRENT_DATE - 1`
- **Benefit**: 50-70% latency reduction, 60% cost reduction
- **Effort**: Low
- **Risk**: Low (may miss historical issues)

#### Incremental Validation
- **Idea**: Validate only last 24h of data
- **Example**: `WHERE updated_at >= CURRENT_TIMESTAMP - INTERVAL 1 DAY`
- **Benefit**: 45% latency reduction, 50% cost reduction
- **Effort**: Low
- **Risk**: Medium (assumes issues appear within 24h)

#### Reference Table Caching
- **Idea**: Cache static reference tables (lookup tables)
- **Benefit**: 30% latency reduction, 35% cost reduction
- **Effort**: Medium
- **Risk**: Low (if reference tables are truly static)

#### Sampling
- **Idea**: Test on representative sample instead of full dataset
- **Benefit**: 70% latency reduction, 80% cost reduction
- **Effort**: High
- **Risk**: High (sample may not catch edge cases)

### 3. Coverage Audit

Identifies gaps in test coverage and prioritizes them.

**Module**: `pydbtguard.analysis.coverage`

**CLI**:
```bash
pydbtguard coverage-audit . --output coverage_gaps.json
```

**Key Features**:
- Risk scoring per model
- Missing test type identification
- Test type recommendations
- Priority-based gap ranking
- Impact estimation (users affected, SLA violations)

**Usage Example**:
```python
from pydbtguard.analysis.coverage import CoverageAuditor

auditor = CoverageAuditor(manifest)
gaps = auditor.audit_coverage()

# Sort by priority
critical = [g for g in gaps if g.priority == "CRITICAL"]
high = [g for g in gaps if g.priority == "HIGH"]

print(f"Critical gaps ({len(critical)}):")
for gap in critical[:5]:
    print(f"  {gap.model_name}")
    print(f"    Risk score: {gap.risk_score:.0f}")
    print(f"    Missing tests: {', '.join(gap.missing_test_types)}")
    print(f"    Recommendations: {', '.join(gap.recommended_tests)}")
    print()
```

**Risk Scoring Factors**:
- **Freshness SLA** (40%): Tighter SLA = higher risk
- **BI Dependencies** (30%): More exposures = higher risk
- **User Impact** (20%): More downstream users = higher risk
- **Materialization** (10%): Incremental loads = higher risk

**Priority Levels**:
- **CRITICAL**: Risk > 75 OR (BI deps > 2 AND missing tests > 1)
- **HIGH**: Risk > 60 OR (BI deps > 0 AND missing tests > 0)
- **MEDIUM**: Risk > 40 OR missing tests > 1
- **LOW**: Everything else

**Test Type Coverage**:
- `unique`: Detects duplicates
- `not_null`: Detects NULL values
- `relationships`: Validates foreign keys
- `freshness`: Ensures data timeliness
- `custom`: User-defined tests

## Architecture

### Diagnostics Module

```
DiagnosticsAnalyzer
├── diagnose_failure()
│   ├── _identify_likely_causes()
│   ├── _find_correlated_tests()
│   ├── _find_pattern_matches()
│   └── _suggest_diagnostic_tests()
└── Output: DiagnosticPlan
```

**Diagnosis Algorithm**:
1. Extract test type from SQL/name
2. Lookup common failure patterns
3. Find tests on same model (correlation)
4. Match against historical failures
5. Suggest diagnostic queries
6. Output actionable plan

### Optimizer Module

```
TestOptimizer
├── suggest_optimizations()
│   ├── _parse_test_sql()
│   ├── _suggest_partition_filter()
│   ├── _suggest_incremental_validation()
│   └── _suggest_caching()
└── Output: List[OptimizationSuggestion]
```

**Optimization Selection**:
1. Parse SQL to identify full table scans
2. Check execution time (>1s triggers incremental)
3. Identify joins (multiple tables = caching candidate)
4. Calculate impact of each optimization
5. Rank by effort/benefit ratio

### Coverage Auditor Module

```
CoverageAuditor
├── audit_coverage()
│   ├── _analyze_model_coverage()
│   ├── _find_attached_tests()
│   ├── _calculate_model_risk_score()
│   ├── _recommend_tests()
│   └── _determine_priority()
└── Output: List[CoverageGap]
```

**Coverage Algorithm**:
1. Iterate through all models
2. Find attached tests by resource_type
3. Infer test type from test definition
4. Calculate risk score (SLA + dependencies)
5. Identify missing test types
6. Recommend specific tests to add
7. Assign priority based on risk

## Data Models

Defined in `pydbtguard/models/schemas.py`:

### DiagnosticPlan
```python
@dataclass
class DiagnosticPlan:
    test_name: str
    likely_causes: List[str]
    diagnostic_tests: List[str]  # SQL queries to run
    correlation_scores: Dict[str, float]  # test_name -> correlation
    pattern_matches: List[str]
```

### OptimizationSuggestion
```python
@dataclass
class OptimizationSuggestion:
    test_name: str
    test_sql: str
    optimization_type: str
    suggested_sql: str
    estimated_latency_reduction_percent: float
    estimated_cost_reduction_percent: float
    effort_level: str  # "low", "medium", "high"
    risk_level: str    # "low", "medium", "high"
```

### CoverageGap
```python
@dataclass
class CoverageGap:
    model_name: str
    model_id: str
    risk_score: float
    freshness_sla_hours: Optional[int]
    bi_dependencies: int
    row_count: int
    missing_test_types: List[str]
    recommended_tests: List[str]
    priority: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
```

## Testing

Tests in `tests/test_phase3_analysis.py`:

```bash
pytest tests/test_phase3_analysis.py -v
```

Coverage:
- Diagnostic plan generation
- Test correlation detection
- Optimization recommendation ranking
- Coverage gap detection and prioritization

## Integration with Phase 2

Phase 3 builds on Phase 2:

| Phase 2 Output | Phase 3 Usage |
|----------------|---------------|
| Historical failure data | Pattern matching in diagnostics |
| Blast radius scores | Priority weighting in coverage audit |
| Cost analysis | Optimization ROI calculation |

**Example Workflow**:
1. Run cost analysis → identify expensive tests
2. Run optimization → get rewrites for top 5 tests
3. Run coverage-audit → identify missing tests
4. For each gap, run diagnose → understand failure modes
5. Implement optimizations and new tests
6. Re-run all to validate improvements

## Performance

- Diagnostic planning: ~50ms per test
- Optimization suggestion: ~30ms per test
- Coverage audit: ~100ms for 100 models
- Correlation detection: ~200ms for 1000 tests

## Next Steps (v0.4+)

- Real-time monitoring and alerting
- Automated test generation from patterns
- Machine learning failure prediction
- Dashboard for visualization
- GitHub PR integration
- Slack/Teams notifications
- Scheduled batch analysis jobs
- Multi-warehouse comparison
- Enterprise features (RBAC, audit logs)
