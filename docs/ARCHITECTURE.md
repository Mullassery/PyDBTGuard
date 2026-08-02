# PyDBTGuard Architecture

## System Design

PyDBTGuard is a hybrid Rust + Python platform designed for predictive validation of dbt tests before deployment.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Python CLI (Click)                       │
│              pydbtguard analyze . --warehouse sf             │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌────▼─────┐
   │ dbt     │   │Analysis │   │Warehouse │
   │Manifest │   │Engines  │   │Connectors│
   │Loader   │   │(Python) │   │(Python)  │
   └────┬────┘   └────┬────┘   └────┬─────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
          ┌───────────▼────────────┐
          │   Rust Core Library    │
          │  (pydbtguard-core)     │
          │                        │
          │  - Fingerprinting      │
          │  - Prediction          │
          │  - Lineage Graphs      │
          │  - Statistical Models  │
          └────────────────────────┘
```

## Layers

### 1. Python CLI Layer (`pydbtguard/cli.py`)
- **Responsibility**: User-facing commands
- **Commands**: `analyze`, `replay`, `simulate`, `pr-check`
- **Framework**: Click
- **Output**: JSON reports, console summaries

### 2. Integration Layer
- **dbt Manifest Loader** (`pydbtguard/dbt/manifest.py`): Parses `target/manifest.json`
- **Warehouse Connectors** (`pydbtguard/warehouse/`):
  - Abstract base class for all warehouses
  - Snowflake, BigQuery implementations
  - Factory pattern for connector instantiation

### 3. Analysis Layer (`pydbtguard/analysis/`)
- **Reliability Analyzer**: Computes test quality scores
- **Cost Analyzer** (v0.2): Query cost estimation
- **Blast Radius Analyzer** (v0.2): Lineage-based impact scoring
- **Diagnostic Engine** (v0.3): Predictive failure diagnosis

### 4. Rust Core (`crates/pydbtguard-core/`)
Heavy computational lifting:

#### `stats/fingerprint.rs`
- Column-level statistics (nulls, cardinality, distribution)
- Data drift detection (comparing baseline vs. current state)
- Anomaly scoring (statistical outlier detection)

#### `stats/predictor.rs`
- Historical failure pattern analysis
- ML-based failure probability estimation
- Confidence scoring based on sample size

#### `lineage/graph.rs`
- DAG construction from dbt manifest
- Upstream/downstream traversal
- Impact scoring (exposure coverage)

#### `manifest/parser.rs`
- dbt manifest JSON parsing
- Test metadata extraction
- Dependency graph construction

### 5. Data Models (`pydbtguard/models/schemas.py`)
Type-safe schemas using dataclasses:
- `ReliabilityScore`: 0-100 with stability/failure probability
- `TestAnalysis`: Single test analysis result
- `AnalysisReport`: Aggregated report
- `RiskLevel` enum: STABLE / AT_RISK / DANGEROUS

## Data Flow

### `pydbtguard analyze .` Command Flow

```
1. CLI parses project path & warehouse type
2. ManifestLoader reads target/manifest.json
3. Extract tests & models from manifest
4. For each test:
   a. Call ReliabilityAnalyzer
   b. Analyzer calls Rust core for statistical analysis
   c. Compute reliability score (0-100)
   d. Map test to downstream models (blast radius)
5. Generate AnalysisReport with recommendations
6. Output JSON or console summary
```

## Warehouse Connector Interface

```python
class WarehouseConnector(ABC):
    def connect(self) -> None
    def execute_query(self, query: str) -> List[Dict]
    def get_table_stats(self, schema: str, table: str) -> Dict
    def disconnect(self) -> None
```

Each warehouse implements:
- Authentication (credentials, key paths)
- Query execution (SQL dialect, result parsing)
- Metadata retrieval (row counts, bytes scanned, costs)
- Connection pooling (if needed)

## Test Reliability Scoring Algorithm

### Input
- Test type (unique, not_null, relationships, custom SQL)
- Test metadata (tags, config)
- Attached model (schema, size, freshness)
- Historical failure rate (if available)

### Scoring Dimensions (v0.1)
1. **Test Type Baseline** (40 points)
   - Generic tests: +10 (more stable)
   - Singular tests: baseline
2. **Risk Factors** (-points)
   - Unique tests: -5 (cardinality drift)
   - Relationships: -3 (upstream dependency)
   - Late-arriving data: -5
3. **Stability** (+/-points)
   - Historical pass rate > 95%: +15
   - Historical pass rate 85-95%: +5
   - Recent failures: -10

### Output
- Score: 0-100
- Risk Level: STABLE (80+), AT_RISK (50-79), DANGEROUS (<50)
- Recommendations: List of actions

## Extensibility Points

### Adding a Warehouse
1. Create `pydbtguard/warehouse/newdb.py`
2. Inherit `WarehouseConnector`
3. Implement required methods
4. Update factory

### Adding Analysis Engine
1. Create `pydbtguard/analysis/newengine.py`
2. Accept manifest + warehouse connector
3. Return structured result
4. Integrate in CLI

### Rust Core Extensions
1. Add module to `crates/pydbtguard-core/src/`
2. Export via `lib.rs`
3. Bind in `bindings/python/src/lib.rs`
4. Test and document

## Performance Considerations

- **Manifest Parsing**: Single JSON load, O(n) traversal
- **Lineage Analysis**: O(V+E) DAG traversal (typically <1s for 1000 nodes)
- **Warehouse Queries**: Depends on table size; partition pruning recommended
- **Rust Statistics**: Parallel computation (rayon) for large datasets

## Dependencies

### Python
- `click`: CLI framework
- `pydantic`: Validation (future)
- `sqlglot`: SQL parsing
- `networkx`: Graph algorithms (future)
- `snowflake-connector-python`, `google-cloud-bigquery`: Warehouse clients

### Rust
- `polars`: DataFrame analysis
- `statrs`: Statistical functions
- `serde`: Serialization
- `pyo3`: Python bindings

## Security

- Warehouse credentials: Loaded from environment or profiles.yml, never logged
- dbt manifest: Read-only, no modifications
- Output: Sanitized JSON, no credential exposure
- Queries: Built dynamically; use parameterized queries where possible (v0.2)

## Testing Strategy

- **Unit Tests**: Isolated Rust/Python functions
- **Integration Tests**: Full workflow with test fixtures
- **Fixtures**: Sample manifests, warehouse mocks
- **Coverage Target**: >80%

## Version Support

- **dbt**: 1.0 - 1.8+
- **Python**: 3.10+
- **Rust**: 1.70+
- **Warehouses**: Snowflake (3.0+), BigQuery (v2 API)
