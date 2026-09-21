"""Blast radius analysis for test failures."""

from typing import List, Dict, Any, Optional, Set
from dataclasses import asdict

from pydbtguard.models.schemas import BlastRadiusAnalysis


class BlastRadiusAnalyzer:
    """Analyzes impact of test failures on downstream models and exposures."""

    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.nodes = manifest.get("nodes", {})
        self.exposures = manifest.get("exposures", {})

    def analyze_failure_impact(
        self,
        model_id: str,
        model_metadata: Optional[Dict[str, Any]] = None,
    ) -> BlastRadiusAnalysis:
        """
        Analyze blast radius for a failed model.

        Args:
            model_id: dbt node ID of the failed model
            model_metadata: Optional metadata about the model (criticality, SLA, etc.)

        Returns:
            BlastRadiusAnalysis with affected models, exposures, score
        """
        affected_models = self._get_downstream_models(model_id)
        affected_exposures = self._get_downstream_exposures(model_id)

        critical_count = len([m for m in affected_models if m["impact_level"] == "critical"])
        high_count = len([m for m in affected_models if m["impact_level"] == "high"])

        # Calculate overall blast radius score (0-100)
        score = self._calculate_blast_radius_score(affected_models, affected_exposures)

        # Estimate recovery time
        recovery_hours = self._estimate_recovery_time(affected_models, affected_exposures)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            affected_models, affected_exposures, critical_count
        )

        estimated_users = sum(
            int(m.get("estimated_users", 0))
            for m in affected_models
        )

        return BlastRadiusAnalysis(
            source_model=model_id,
            total_affected_models=len(affected_models),
            critical_impact_count=critical_count,
            high_impact_count=high_count,
            estimated_users_affected=estimated_users,
            overall_score=score,
            estimated_recovery_hours=recovery_hours,
            affected_models=affected_models,
            exposures_at_risk=affected_exposures,
            recommendations=recommendations,
        )

    def _get_downstream_models(self, model_id: str, visited: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """
        Recursively find all downstream models.

        Args:
            model_id: Starting model ID
            visited: Set of already visited node IDs

        Returns:
            List of affected models with impact level and metadata
        """
        if visited is None:
            visited = set()

        affected = []

        if model_id in visited:
            return affected

        visited.add(model_id)

        # Find models that depend ON this one (i.e. list model_id in their
        # own depends_on.nodes) — that's what makes them downstream of it.
        for dep_id, dep_node in self.nodes.items():
            if dep_id in visited:
                continue
            if dep_node.get("resource_type") != "model":
                continue

            upstream = dep_node.get("depends_on", {}).get("nodes", [])
            if model_id not in upstream:
                continue

            distance = self._calculate_distance(model_id, dep_id)
            impact_level = self._determine_impact_level(distance)

            affected.append({
                "model_id": dep_id,
                "model_name": dep_node.get("name", dep_id),
                "impact_level": impact_level,
                "distance": distance,
                "criticality_score": self._calculate_criticality(dep_node),
                "estimated_users": dep_node.get("config", {}).get("estimated_users", 0),
                "sla_freshness_hours": dep_node.get("config", {}).get("freshness", {}).get("warn_after", {}).get("count", None),
                "bi_dependencies": self._count_bi_dependencies(dep_id),
            })

            # Recursively get downstream models
            downstream = self._get_downstream_models(dep_id, visited)
            affected.extend(downstream)

        return affected

    def _get_downstream_exposures(self, model_id: str) -> List[str]:
        """
        Find all exposures that depend on this model.

        Args:
            model_id: Model ID

        Returns:
            List of exposure IDs at risk
        """
        at_risk = []

        for exp_id, exposure in self.exposures.items():
            depends_on = exposure.get("depends_on", {}).get("nodes", [])
            if model_id in depends_on or self._is_transitive_dependency(model_id, depends_on):
                at_risk.append(exp_id)

        return at_risk

    def _calculate_distance(self, source: str, target: str) -> int:
        """Calculate shortest path distance between nodes.

        `target` is downstream of `source`, so `target` depends on `source`
        (not the other way around) when they're directly connected.
        """
        # Simplified: assume direct dependency edges are distance 1
        if source in self.nodes.get(target, {}).get("depends_on", {}).get("nodes", []):
            return 1
        return 2  # Default to 2 for transitive

    def _determine_impact_level(self, distance: int) -> str:
        """Determine impact level based on distance."""
        if distance == 1:
            return "critical"
        elif distance == 2:
            return "high"
        elif distance == 3:
            return "medium"
        else:
            return "low"

    def _calculate_criticality(self, node: Dict[str, Any]) -> float:
        """Calculate criticality score (0-100)."""
        score = 50.0  # Base

        # Freshness SLA: tighter = more critical
        freshness = node.get("config", {}).get("freshness", {}).get("warn_after", {})
        if freshness:
            hours = freshness.get("count", 24)
            score += (24 - hours) / 24 * 25

        # BI dependencies
        score += self._count_bi_dependencies(node.get("unique_id", "")) * 2

        return min(score, 100.0)

    def _count_bi_dependencies(self, model_id: str) -> int:
        """Count how many exposures depend on this model."""
        count = 0
        for exposure in self.exposures.values():
            if model_id in exposure.get("depends_on", {}).get("nodes", []):
                count += 1
        return count

    def _is_transitive_dependency(self, source: str, targets: List[str]) -> bool:
        """Check if source is a transitive dependency of any target."""
        visited = set()

        def find_dependency(node_id: str) -> bool:
            if node_id in visited:
                return False
            visited.add(node_id)

            if node_id == source:
                return True

            if node_id in self.nodes:
                deps = self.nodes[node_id].get("depends_on", {}).get("nodes", [])
                for dep in deps:
                    if find_dependency(dep):
                        return True

            return False

        for target in targets:
            if find_dependency(target):
                return True

        return False

    def _calculate_blast_radius_score(
        self,
        affected_models: List[Dict[str, Any]],
        affected_exposures: List[str],
    ) -> float:
        """Calculate overall blast radius score (0-100)."""
        if not affected_models:
            return 0.0

        # Score based on critical/high counts and exposure impact
        critical_weight = len([m for m in affected_models if m["impact_level"] == "critical"]) * 30
        high_weight = len([m for m in affected_models if m["impact_level"] == "high"]) * 20
        exposure_weight = len(affected_exposures) * 10

        score = (critical_weight + high_weight + exposure_weight) / (len(affected_models) + 1)

        return min(score, 100.0)

    def _estimate_recovery_time(
        self,
        affected_models: List[Dict[str, Any]],
        affected_exposures: List[str],
    ) -> float:
        """Estimate recovery time in hours."""
        # Base recovery time
        recovery = 1.0  # 1 hour base

        # Add time for each affected model
        recovery += (len(affected_models) / 10.0)

        # Add time for exposures (high user impact)
        recovery += (len(affected_exposures) * 2.0)

        return recovery

    def _generate_recommendations(
        self,
        affected_models: List[Dict[str, Any]],
        affected_exposures: List[str],
        critical_count: int,
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if critical_count > 0:
            recommendations.append(
                "Critical impact detected. Stage deployment with limited rollout."
            )

        if affected_exposures:
            recommendations.append(
                f"Notify stakeholders: {len(affected_exposures)} exposures at risk."
            )

        if len(affected_models) > 5:
            recommendations.append(
                f"Large blast radius ({len(affected_models)} models). Prepare comprehensive rollback plan."
            )

        if any(
            m.get("sla_freshness_hours") is not None and m["sla_freshness_hours"] < 4
            for m in affected_models
        ):
            recommendations.append(
                "High-SLA models affected. Prioritize incident response."
            )

        return recommendations
