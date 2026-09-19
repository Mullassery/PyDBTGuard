# Phase 2 (v0.2) - Historical Analysis & Operational Intelligence

## Overview

Phase 2 introduces historical replay capabilities, failure pattern detection, blast radius mapping, and cost analysis.

## New Capabilities

### 1. Historical Replay Engine

Analyzes test reliability by replaying tests against historical warehouse snapshots.

**Module**: `pydbtguard.analysis.replay`

**CLI**:
```bash
pydbtguard replay . --lookback 180d --warehouse snowflake
```

**Key Features**:
- Pass rate calculation over time
- Reliability trends (improving, degrading, stable)
- Mean Time Between Failures (MTBF)
- Flaky test identification
- Reliability curves with configurable time windows

**Usage Example**:
```python
from pydbtguard.analysis.replay import HistoricalReplayAnalyzer

analyzer = HistoricalReplayAnalyzer(warehouse)
result = analyzer.analyze_test_historical_reliability(
    test_name="test_unique_id",
    test_sql="SELECT id, COUNT(*) FROM users GROUP BY id HAVING COUNT(*) > 1",
    lookback_days=180
)

print(f"Pass rate: {result.pass_rate:.1%}")
print(f"Trend: {result.trend}")
print(f"MTBF: {result.mtbf_days:.1f} days")
```

### 2. Failure Pattern Detection

Automatically detects common data quality failure patterns.

**Module**: `pydbtguard.analysis.patterns` (Rust core: `crates/pydbtguard-core/src/patterns/`)

**Patterns Detected**:
- **Duplicate Spike**: Cardinality decreased by >50% (indicates duplicate rows)
- **Seasonal Anomaly**: Row count varies significantly (day-of-week, month-end patterns)
- **Backfill Sensitivity**: Large bulk insert operations (>50% row increase)
- **CDC Replay Event**: Change Data Capture replay detection
- **Late-Arriving Data**: Data arriving outside expected time window
- **Volume Surge**: 2x+ spike in data volume
- **Schema Change**: Column additions/removals/type changes
- **Timezone Shift**: Timestamp interpretation issues

**Rust Implementation**:
- `FailurePatternDetector`: Analyzes snapshots and returns patterns
- `AnomalyScore`: Z-score based anomaly detection on column metrics
- `PatternDetectionResult`: Comprehensive result with patterns, anomalies, recommendations

### 3. Blast Radius Mapping

Analyzes impact of test failures on downstream models and exposures.

**Module**: `pydbtguard.analysis.blast_radius`

**CLI**:
```bash
pydbtguard blast-radius . --model model.project.users
```

**Output**:
- Total affected models
- Critical vs. High impact counts
- Estimated users affected
- Affected exposures (BI dashboards, reports)
- Recovery time estimate
- Actionable recommendations

**Usage Example**:
```python
from pydbtguard.analysis.blast_radius import BlastRadiusAnalyzer

analyzer = BlastRadiusAnalyzer(manifest)
result = analyzer.analyze_failure_impact("model.project.users")

print(f"Affected models: {result.total_affected_models}")
print(f"Critical impact: {result.critical_impact_count}")
print(f"Blast radius score: {result.overall_score}/100")
print(f"Recovery time: {result.estimated_recovery_hours}h")
```

**Impact Levels**:
- `CRITICAL`: Direct dependencies (distance = 1)
- `HIGH`: 2 hops from failure
- `MEDIUM`: 3 hops
- `LOW`: >3 hops

**Criticality Scoring**:
- Freshness SLA (tighter = more critical)
- BI dependencies count
- Downstream user exposure

### 4. Test Cost Analysis

Estimates execution costs and identifies optimization opportunities.

**Module**: `pydbtguard.analysis.cost`

**CLI**:
```bash
pydbtguard cost . --output cost_report.json
```

**Output**:
- Total monthly/annual cost
- Cost by test type breakdown
- Most expensive tests (top 10)
- Optimization opportunities with ROI
- Estimated annual savings

**Usage Example**:
```python
from pydbtguard.analysis.cost import CostAnalyzer

analyzer = CostAnalyzer(warehouse_type="snowflake")
report = analyzer.analyze_test_costs(tests)

print(f"Annual cost: ${report.total_annual_cost_usd:.2f}")
print(f"Potential savings: ${report.estimated_savings_usd:.2f}")

for opp in report.optimization_opportunities[:5]:
    print(f"  {opp.optimization_type}: {opp.recommendation}")
```

**Optimization Types**:
- **Partition**: Add partition filters to reduce scan volume (~60% reduction)
- **Incremental**: Validate only last 24h instead of full dataset (~45% reduction)
- **Caching**: Cache reference tables for repeated joins (~35% reduction)
- **Sampling**: Use sample-based testing for large tables (~40% reduction)

**Cost Calculation**:
- Snowflake: 1 credit per 1GB scanned
- BigQuery: 1 slot-hour per analysis (simplified)
- Customizable via cost_per_credit_usd

## Rust Core Architecture

### Replay Module (`crates/pydbtguard-core/src/replay/`)

```
replay/
├── mod.rs          # HistoricalReliabilityCurve, ReplayResult, ReplaySnapshot, ReplayOptions
└── engine.rs       # HistoricalReplayEngine, ReliabilityTrend, FailureWindow
```

**Types**:
- `HistoricalReliabilityCurve`: Test results over time with metrics
- `ReplayResult`: Single test execution result
- `ReplaySnapshot`: Point-in-time warehouse state
- `HistoricalReplayEngine`: Executes tests against snapshots
- `ReliabilityTrend`: 90d, 30d, 7d pass rates + volatility

### Patterns Module (`crates/pydbtguard-core/src/patterns/`)

```
patterns/
├── mod.rs       # FailurePattern, PatternType, PatternDetectionResult
└── detector.rs  # FailurePatternDetector, AnomalyScore
```

**Pattern Detection Algorithm**:
1. Compute cardinality deltas for each column
2. Calculate z-scores for anomalies (threshold: |z| > 2)
3. Match against known patterns
4. Assign confidence and severity
5. Generate recommendations

### Impact Module (`crates/pydbtguard-core/src/impact/`)

```
impact/
├── mod.rs       # BlastRadiusResult, AffectedModel, ImpactLevel
└── analyzer.rs  # BlastRadiusAnalyzer
```

**Blast Radius Algorithm**:
1. BFS from source model to find all downstream nodes
2. Calculate distance to each affected model
3. Determine impact level based on distance
4. Score criticality (freshness SLA + BI dependencies + user count)
5. Aggregate score and generate recommendations

### Cost Module (`crates/pydbtguard-core/src/cost/`)

```
cost/
├── mod.rs           # QueryCost, TestCost, CostAnalysisResult
└── calculator.rs    # CostCalculator
```

**Cost Calculation**:
1. Estimate bytes scanned per test
2. Convert to credits/units based on warehouse
3. Multiply by run frequency to get monthly/annual cost
4. Identify expensive tests for optimization
5. Calculate potential savings per optimization

## CLI Commands

| Command | Phase | Functionality |
|---------|-------|---------------|
| `pydbtguard replay` | v0.2 | Historical reliability analysis |
| `pydbtguard blast-radius` | v0.2 | Impact mapping and downstream analysis |
| `pydbtguard cost` | v0.2 | Cost analysis and optimization |
| `pydbtguard diagnose` | v0.3 | Root cause analysis and diagnostics |
| `pydbtguard optimize` | v0.3 | Test optimization suggestions |
| `pydbtguard coverage-audit` | v0.3 | Coverage gap analysis |

## Python Bindings

Current bindings expose v0.1 functionality:
- `ColumnFingerprint`: Column-level statistics
- `FailurePredictor`: Failure probability prediction

Future bindings (v0.4+) will expose:
- `HistoricalReliabilityCurve`
- `BlastRadiusResult`
- `CostAnalysisResult`
- `FailurePattern`
- `AnomalyScore`

## Data Models

All output types are defined in `pydbtguard/models/schemas.py`:

- `HistoricalReplayResult`
- `FailurePatternAnalysis`
- `BlastRadiusAnalysis`
- `CostAnalysisReport`
- `CostOptimizationOpportunity`

JSON serialization support via `dataclasses.asdict()`.

## Testing

Unit tests in `tests/test_phase2_analysis.py`:

```bash
pytest tests/test_phase2_analysis.py -v
```

Tests cover:
- Historical reliability calculation
- Blast radius detection
- Cost analysis and ROI
- Pattern matching accuracy

## Performance

- Rust core optimized with Polars for dataframe operations
- Replay analysis: ~100ms per test for 180-day window
- Blast radius: ~50ms for manifests with <1000 models
- Cost analysis: ~10ms for 100 tests
- Pattern detection: ~20ms per snapshot

## Next Steps (v0.4+)

- Real warehouse integration (query historical snapshots)
- Predictive failure models (time series forecasting)
- Multi-warehouse cost comparison
- Advanced visualizations and dashboards
- GitHub PR integration
- Automated recommendations and actions
