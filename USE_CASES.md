# PyDBTGuard - Use Cases

## Overview

Pre-deployment validation for dbt tests: analyze risk, impact, and cost from local dbt artifacts (`manifest.json`, `run_results.json`) without connecting to a warehouse. > **Not to be confused with [PyAirflowTester](https://github.com/Mullassery/PyAirflowTester) or [PyBlastRadius](https://github.com/Mullassery/PyBlastRadius):** PyDBTGuard statically analyzes a dbt `manifest.json`; PyAirflowTester validates Airflow DAGs and dbt runs; PyBlastRadius simulates cascading-failure impact across whole systems.

## Use Cases

See README.md for details.

## Common Scenarios

- Development and testing with PyDBTGuard
- Integration into existing workflows
- Exploration and prototyping

