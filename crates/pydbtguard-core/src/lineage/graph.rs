use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize, Eq, PartialEq, Hash)]
pub enum NodeType {
    Source,
    Model,
    Test,
    Exposure,
}

#[derive(Debug, Clone, Serialize, Deserialize, Eq, PartialEq, Hash)]
pub struct Node {
    pub id: String,
    pub name: String,
    pub node_type: NodeType,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Edge {
    pub from: String,
    pub to: String,
    pub edge_type: String,
}

#[derive(Debug, Clone)]
pub struct LineageGraph {
    pub nodes: HashMap<String, Node>,
    pub edges: Vec<Edge>,
}

impl LineageGraph {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
        }
    }

    pub fn add_node(&mut self, node: Node) {
        self.nodes.insert(node.id.clone(), node);
    }

    pub fn add_edge(&mut self, edge: Edge) {
        self.edges.push(edge);
    }

    pub fn downstream_nodes(&self, node_id: &str) -> HashSet<String> {
        let mut downstream = HashSet::new();
        let mut to_visit = vec![node_id.to_string()];

        while let Some(current) = to_visit.pop() {
            for edge in &self.edges {
                if edge.from == current && !downstream.contains(&edge.to) {
                    downstream.insert(edge.to.clone());
                    to_visit.push(edge.to.clone());
                }
            }
        }

        downstream
    }

    pub fn upstream_nodes(&self, node_id: &str) -> HashSet<String> {
        let mut upstream = HashSet::new();
        let mut to_visit = vec![node_id.to_string()];

        while let Some(current) = to_visit.pop() {
            for edge in &self.edges {
                if edge.to == current && !upstream.contains(&edge.from) {
                    upstream.insert(edge.from.clone());
                    to_visit.push(edge.from.clone());
                }
            }
        }

        upstream
    }

    pub fn impact_score(&self, node_id: &str) -> f64 {
        let downstream = self.downstream_nodes(node_id);
        let exposure_count = downstream
            .iter()
            .filter(|id| {
                self.nodes
                    .get(*id)
                    .map(|n| n.node_type == NodeType::Exposure)
                    .unwrap_or(false)
            })
            .count();

        (exposure_count as f64) / (downstream.len().max(1) as f64)
    }
}

impl Default for LineageGraph {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_downstream_traversal() {
        let mut graph = LineageGraph::new();
        graph.add_node(Node {
            id: "source".to_string(),
            name: "source".to_string(),
            node_type: NodeType::Source,
            metadata: HashMap::new(),
        });
        graph.add_node(Node {
            id: "model1".to_string(),
            name: "model1".to_string(),
            node_type: NodeType::Model,
            metadata: HashMap::new(),
        });
        graph.add_edge(Edge {
            from: "source".to_string(),
            to: "model1".to_string(),
            edge_type: "depends_on".to_string(),
        });

        let downstream = graph.downstream_nodes("source");
        assert!(downstream.contains("model1"));
    }
}
