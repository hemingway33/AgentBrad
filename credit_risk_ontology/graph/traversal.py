"""
Graph Traversal Algorithms for supply chain risk analysis.

Implements specialized traversal patterns for credit risk:
- Risk propagation along supply chain paths
- Circular guarantee detection
- Shell company network discovery
- Concentration risk analysis
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from .storage import SupplyChainGraph, GraphNode, GraphEdge


@dataclass
class RiskPropagationResult:
    """Result of risk propagation analysis."""
    node_id: int
    node_name: str
    propagated_risk: float
    risk_path: list[int]
    risk_factors: list[str]


@dataclass
class CircularGuaranteeResult:
    """Result of circular guarantee detection."""
    cycle: list[int]
    cycle_names: list[str]
    total_guarantee_amount: float
    risk_severity: str


@dataclass
class ConcentrationRiskResult:
    """Result of concentration risk analysis."""
    enterprise_id: int
    concentration_type: str  # 'CUSTOMER', 'SUPPLIER', 'INDUSTRY'
    concentration_ratio: float  # HHI or top-N ratio
    top_counterparties: list[dict]
    risk_level: str


class RiskPropagationTraversal:
    """
    Propagates risk scores through the supply chain graph.
    When an upstream supplier has high risk, that risk propagates
    downstream with decay factors based on relationship strength.
    """

    DEFAULT_DECAY = 0.6  # Risk decays 40% per hop
    EDGE_TYPE_WEIGHTS = {
        'GUARANTEE': 0.9,       # Guarantees carry high risk propagation
        'SHAREHOLDER': 0.8,     # Ownership implies shared risk
        'SUPPLY_CHAIN': 0.5,    # Supply chain has moderate propagation
        'TRANSACTION': 0.3,     # Transaction links have lower propagation
        'RELATIONSHIP': 0.6,    # General relationships
    }

    def __init__(self, graph: SupplyChainGraph):
        self.graph = graph

    def propagate_from_node(
        self,
        source_id: int,
        max_depth: int = 3,
        decay: Optional[float] = None,
    ) -> list[RiskPropagationResult]:
        """Propagate risk from a high-risk node to its neighbors."""
        decay = decay or self.DEFAULT_DECAY
        source = self.graph.get_node(source_id)
        if not source:
            return []

        results = []
        visited = set()
        # BFS with risk decay
        queue = [(source_id, source.risk_score, [source_id], [], 0)]

        while queue:
            current_id, current_risk, path, factors, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)

            if current_id != source_id:
                node = self.graph.get_node(current_id)
                if node:
                    results.append(RiskPropagationResult(
                        node_id=current_id,
                        node_name=node.name,
                        propagated_risk=current_risk,
                        risk_path=list(path),
                        risk_factors=list(factors),
                    ))

            # Propagate to neighbors
            for node, edge in self.graph.get_neighbors(current_id, direction='both'):
                if node.id not in visited:
                    edge_weight = self.EDGE_TYPE_WEIGHTS.get(edge.edge_type, 0.5)
                    propagated = current_risk * decay * edge_weight
                    if propagated > 5.0:  # Minimum threshold
                        new_factors = factors + [
                            f"{edge.edge_type}:{edge.relation} (decay={decay * edge_weight:.2f})"
                        ]
                        queue.append((
                            node.id, propagated,
                            path + [node.id], new_factors, depth + 1,
                        ))

        # Sort by propagated risk (highest first)
        results.sort(key=lambda r: r.propagated_risk, reverse=True)
        return results


class CircularGuaranteeDetector:
    """
    Detects circular guarantee chains in the enterprise network.
    Circular guarantees (互保圈) are a major risk factor in Chinese
    supply chain finance - if one entity defaults, the entire circle
    can cascade.
    """

    def __init__(self, graph: SupplyChainGraph):
        self.graph = graph

    def detect_all_circles(self, min_length: int = 2) -> list[CircularGuaranteeResult]:
        """Find all circular guarantee chains."""
        guarantee_edges = {}
        for node_id, edges in self.graph.adjacency.items():
            for edge in edges:
                if edge.relation == 'GUARANTEE':
                    guarantee_edges.setdefault(node_id, []).append(edge)

        all_cycles = []
        visited_cycles = set()

        for start_id in guarantee_edges:
            cycles = self._find_cycles(start_id, guarantee_edges)
            for cycle in cycles:
                if len(cycle) - 1 >= min_length:
                    # Normalize cycle to avoid duplicates
                    cycle_key = tuple(sorted(cycle[:-1]))
                    if cycle_key not in visited_cycles:
                        visited_cycles.add(cycle_key)
                        names = [
                            self.graph.get_node(nid).name
                            for nid in cycle
                            if self.graph.get_node(nid)
                        ]
                        total_amount = sum(
                            e.weight for e in guarantee_edges.get(nid, [])
                            for nid in cycle[:-1]
                            if e.target_id in cycle
                        )
                        severity = self._classify_severity(len(cycle) - 1, total_amount)
                        all_cycles.append(CircularGuaranteeResult(
                            cycle=cycle,
                            cycle_names=names,
                            total_guarantee_amount=total_amount,
                            risk_severity=severity,
                        ))

        return all_cycles

    def _find_cycles(self, start_id: int, edges: dict) -> list[list[int]]:
        cycles = []

        def dfs(current, path, visited):
            for edge in edges.get(current, []):
                next_id = edge.target_id
                if next_id == start_id and len(path) > 1:
                    cycles.append(path + [next_id])
                elif next_id not in visited:
                    visited.add(next_id)
                    dfs(next_id, path + [next_id], visited)
                    visited.discard(next_id)

        dfs(start_id, [start_id], {start_id})
        return cycles

    @staticmethod
    def _classify_severity(chain_length: int, total_amount: float) -> str:
        if chain_length >= 4 or total_amount > 100_000_000:
            return 'CRITICAL'
        elif chain_length >= 3 or total_amount > 50_000_000:
            return 'HIGH'
        elif chain_length >= 2 or total_amount > 10_000_000:
            return 'MEDIUM'
        return 'LOW'


class ShellCompanyDetector:
    """
    Detects potential shell companies using graph structure analysis.
    Shell companies often show specific patterns:
    - Hub nodes with many edges but no real business
    - Newly created nodes in dense subgraphs
    - Unusual transaction patterns (round-tripping)
    """

    def __init__(self, graph: SupplyChainGraph):
        self.graph = graph

    def detect_suspicious_nodes(self) -> list[dict]:
        """Identify nodes that exhibit shell company patterns."""
        suspicious = []
        centrality = self.graph.compute_degree_centrality()
        pagerank = self.graph.compute_pagerank()

        for node_id, node in self.graph.nodes.items():
            score = 0.0
            reasons = []

            # Check for round-trip transactions
            round_trips = self._check_round_trips(node_id)
            if round_trips:
                score += 30
                reasons.append(f"Round-trip transactions detected: {len(round_trips)} patterns")

            # Check for pass-through patterns (high in-degree + high out-degree, similar amounts)
            in_edges = self.graph.reverse_adjacency.get(node_id, [])
            out_edges = self.graph.adjacency.get(node_id, [])
            txn_in = [e for e in in_edges if e.edge_type == 'TRANSACTION']
            txn_out = [e for e in out_edges if e.edge_type == 'TRANSACTION']

            if txn_in and txn_out:
                total_in = sum(e.weight for e in txn_in)
                total_out = sum(e.weight for e in txn_out)
                if total_in > 0 and abs(total_in - total_out) / total_in < 0.05:
                    score += 20
                    reasons.append("Pass-through pattern: in/out amounts nearly equal")

            # Low centrality but connected to high-centrality nodes
            node_centrality = centrality.get(node_id, 0)
            neighbors = self.graph.get_neighbors(node_id, direction='both')
            if neighbors:
                avg_neighbor_centrality = sum(
                    centrality.get(n.id, 0) for n, _ in neighbors
                ) / len(neighbors)
                if node_centrality < 0.1 and avg_neighbor_centrality > 0.3:
                    score += 15
                    reasons.append("Low centrality node connected to high-centrality hub")

            if score >= 30:
                suspicious.append({
                    'node_id': node_id,
                    'name': node.name,
                    'shell_score': score,
                    'reasons': reasons,
                    'centrality': node_centrality,
                    'pagerank': pagerank.get(node_id, 0),
                })

        suspicious.sort(key=lambda x: x['shell_score'], reverse=True)
        return suspicious

    def _check_round_trips(self, node_id: int) -> list[list[int]]:
        """Check for A -> B -> A transaction patterns."""
        round_trips = []
        out_edges = self.graph.adjacency.get(node_id, [])
        for edge in out_edges:
            if edge.edge_type == 'TRANSACTION':
                return_edges = self.graph.adjacency.get(edge.target_id, [])
                for ret_edge in return_edges:
                    if ret_edge.target_id == node_id and ret_edge.edge_type == 'TRANSACTION':
                        round_trips.append([node_id, edge.target_id, node_id])
        return round_trips


class ConcentrationRiskAnalyzer:
    """
    Analyzes concentration risk in the supply chain:
    - Customer concentration (over-reliance on few buyers)
    - Supplier concentration (over-reliance on few suppliers)
    - Industry concentration
    """

    def __init__(self, graph: SupplyChainGraph):
        self.graph = graph

    def analyze_enterprise(self, enterprise_id: int) -> list[ConcentrationRiskResult]:
        """Analyze all types of concentration risk for an enterprise."""
        results = []

        # Customer concentration
        customer_result = self._analyze_direction(enterprise_id, 'outgoing', 'CUSTOMER')
        if customer_result:
            results.append(customer_result)

        # Supplier concentration
        supplier_result = self._analyze_direction(enterprise_id, 'incoming', 'SUPPLIER')
        if supplier_result:
            results.append(supplier_result)

        return results

    def _analyze_direction(
        self,
        enterprise_id: int,
        direction: str,
        concentration_type: str,
    ) -> Optional[ConcentrationRiskResult]:
        neighbors = self.graph.get_neighbors(
            enterprise_id,
            edge_type='TRANSACTION',
            direction=direction,
        )
        if not neighbors:
            return None

        # Calculate HHI (Herfindahl-Hirschman Index)
        total_volume = sum(e.weight for _, e in neighbors)
        if total_volume == 0:
            return None

        shares = [(n.name, e.weight / total_volume) for n, e in neighbors]
        hhi = sum(s ** 2 for _, s in shares) * 10000  # Scale to 0-10000

        # Top counterparties
        shares.sort(key=lambda x: x[1], reverse=True)
        top = [{'name': name, 'share': round(share * 100, 1)} for name, share in shares[:5]]

        # Top 3 concentration ratio
        top3_ratio = sum(s for _, s in shares[:3])

        if hhi > 2500 or top3_ratio > 0.7:
            risk_level = 'HIGH'
        elif hhi > 1500 or top3_ratio > 0.5:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        return ConcentrationRiskResult(
            enterprise_id=enterprise_id,
            concentration_type=concentration_type,
            concentration_ratio=round(hhi, 1),
            top_counterparties=top,
            risk_level=risk_level,
        )
