"""
Graph Storage Engine - In-memory and persistent graph for supply chain knowledge graph.

Implements a Palantir Foundry-style object graph using Django ORM as the
persistent layer with an in-memory adjacency list for fast traversal.

Key concepts:
- Nodes are Enterprise instances (or any ontology object)
- Edges are EnterpriseRelationship, SupplyChainLink, or TransactionEdge instances
- The graph supports typed edges, weighted traversal, and subgraph extraction
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from django.db.models import Q, Sum, Count, Avg


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id: int
    entity_type: str
    name: str
    properties: dict = field(default_factory=dict)
    risk_level: str = 'UNKNOWN'
    risk_score: float = 0.0


@dataclass
class GraphEdge:
    """An edge in the knowledge graph."""
    source_id: int
    target_id: int
    edge_type: str
    relation: str
    weight: float = 1.0
    properties: dict = field(default_factory=dict)


class SupplyChainGraph:
    """
    In-memory graph representation of the supply chain knowledge graph.
    Built from Django ORM models, optimized for traversal and analysis.
    """

    def __init__(self):
        self.nodes: dict[int, GraphNode] = {}
        self.adjacency: dict[int, list[GraphEdge]] = defaultdict(list)
        self.reverse_adjacency: dict[int, list[GraphEdge]] = defaultdict(list)
        self._type_index: dict[str, set[int]] = defaultdict(set)

    def add_node(self, node: GraphNode):
        self.nodes[node.id] = node
        self._type_index[node.entity_type].add(node.id)

    def add_edge(self, edge: GraphEdge):
        self.adjacency[edge.source_id].append(edge)
        self.reverse_adjacency[edge.target_id].append(edge)

    def get_node(self, node_id: int) -> Optional[GraphNode]:
        return self.nodes.get(node_id)

    def get_neighbors(
        self,
        node_id: int,
        edge_type: Optional[str] = None,
        direction: str = 'outgoing',
    ) -> list[tuple[GraphNode, GraphEdge]]:
        """Get neighboring nodes with optional edge type filter."""
        if direction == 'outgoing':
            edges = self.adjacency.get(node_id, [])
        elif direction == 'incoming':
            edges = self.reverse_adjacency.get(node_id, [])
        else:  # both
            edges = self.adjacency.get(node_id, []) + self.reverse_adjacency.get(node_id, [])

        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]

        result = []
        for edge in edges:
            neighbor_id = edge.target_id if direction != 'incoming' else edge.source_id
            node = self.nodes.get(neighbor_id)
            if node:
                result.append((node, edge))
        return result

    def get_nodes_by_type(self, entity_type: str) -> list[GraphNode]:
        return [self.nodes[nid] for nid in self._type_index.get(entity_type, set())]

    def get_subgraph(self, center_id: int, max_depth: int = 2) -> 'SupplyChainGraph':
        """Extract a subgraph centered on a node up to max_depth hops."""
        subgraph = SupplyChainGraph()
        visited = set()
        queue = [(center_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)

            node = self.nodes.get(current_id)
            if not node:
                continue
            subgraph.add_node(node)

            if depth < max_depth:
                for edges in [self.adjacency.get(current_id, []),
                              self.reverse_adjacency.get(current_id, [])]:
                    for edge in edges:
                        subgraph.add_edge(edge)
                        neighbor_id = (
                            edge.target_id if edge.source_id == current_id
                            else edge.source_id
                        )
                        if neighbor_id not in visited:
                            queue.append((neighbor_id, depth + 1))

        return subgraph

    def find_paths(
        self,
        start_id: int,
        end_id: int,
        max_depth: int = 5,
    ) -> list[list[int]]:
        """Find all paths between two nodes up to max_depth."""
        paths = []

        def dfs(current, target, path, depth):
            if depth > max_depth:
                return
            if current == target:
                paths.append(list(path))
                return
            for edge in self.adjacency.get(current, []):
                if edge.target_id not in path:
                    path.append(edge.target_id)
                    dfs(edge.target_id, target, path, depth + 1)
                    path.pop()

        dfs(start_id, end_id, [start_id], 0)
        return paths

    def detect_cycles(self, node_id: int) -> list[list[int]]:
        """Detect cycles involving a specific node (circular guarantee detection)."""
        cycles = []

        def dfs(current, path, visited):
            for edge in self.adjacency.get(current, []):
                next_id = edge.target_id
                if next_id == node_id and len(path) > 1:
                    cycles.append(list(path) + [next_id])
                elif next_id not in visited:
                    visited.add(next_id)
                    path.append(next_id)
                    dfs(next_id, path, visited)
                    path.pop()
                    visited.discard(next_id)

        dfs(node_id, [node_id], {node_id})
        return cycles

    def compute_degree_centrality(self) -> dict[int, float]:
        """Compute degree centrality for all nodes."""
        n = len(self.nodes)
        if n <= 1:
            return {nid: 0.0 for nid in self.nodes}
        centrality = {}
        for nid in self.nodes:
            degree = len(self.adjacency.get(nid, [])) + len(self.reverse_adjacency.get(nid, []))
            centrality[nid] = degree / (n - 1)
        return centrality

    def compute_pagerank(
        self, damping: float = 0.85, iterations: int = 100, tolerance: float = 1e-6,
    ) -> dict[int, float]:
        """Compute PageRank for risk propagation analysis."""
        n = len(self.nodes)
        if n == 0:
            return {}

        node_ids = list(self.nodes.keys())
        rank = {nid: 1.0 / n for nid in node_ids}

        for _ in range(iterations):
            new_rank = {}
            for nid in node_ids:
                incoming = self.reverse_adjacency.get(nid, [])
                rank_sum = 0.0
                for edge in incoming:
                    out_degree = len(self.adjacency.get(edge.source_id, []))
                    if out_degree > 0:
                        rank_sum += rank[edge.source_id] / out_degree
                new_rank[nid] = (1 - damping) / n + damping * rank_sum

            # Check convergence
            diff = sum(abs(new_rank[nid] - rank[nid]) for nid in node_ids)
            rank = new_rank
            if diff < tolerance:
                break

        return rank

    def community_detection_label_propagation(self) -> dict[int, int]:
        """Simple label propagation for community detection."""
        import random
        labels = {nid: nid for nid in self.nodes}
        node_ids = list(self.nodes.keys())

        for _ in range(50):
            random.shuffle(node_ids)
            changed = False
            for nid in node_ids:
                neighbors = (
                    [e.target_id for e in self.adjacency.get(nid, [])]
                    + [e.source_id for e in self.reverse_adjacency.get(nid, [])]
                )
                if not neighbors:
                    continue
                label_count = defaultdict(int)
                for nb in neighbors:
                    label_count[labels[nb]] += 1
                max_label = max(label_count, key=label_count.get)
                if labels[nid] != max_label:
                    labels[nid] = max_label
                    changed = True
            if not changed:
                break

        return labels

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self.adjacency.values())

    def to_dict(self) -> dict:
        """Serialize graph to dictionary for API responses."""
        return {
            'nodes': [
                {
                    'id': n.id,
                    'type': n.entity_type,
                    'name': n.name,
                    'risk_level': n.risk_level,
                    'risk_score': n.risk_score,
                    'properties': n.properties,
                }
                for n in self.nodes.values()
            ],
            'edges': [
                {
                    'source': e.source_id,
                    'target': e.target_id,
                    'type': e.edge_type,
                    'relation': e.relation,
                    'weight': e.weight,
                    'properties': e.properties,
                }
                for edges in self.adjacency.values()
                for e in edges
            ],
            'stats': {
                'node_count': self.node_count,
                'edge_count': self.edge_count,
            },
        }


class GraphStorageManager:
    """
    Manages persistence of the supply chain graph using Django ORM.
    Loads from database models into the in-memory SupplyChainGraph.
    """

    @staticmethod
    def build_graph(
        enterprise_ids: Optional[list[int]] = None,
        include_transactions: bool = True,
    ) -> SupplyChainGraph:
        """Build an in-memory graph from the database."""
        from credit_risk_ontology.models.entities import Enterprise
        from credit_risk_ontology.models.relationships import (
            EnterpriseRelationship, SupplyChainLink, TransactionEdge,
        )

        graph = SupplyChainGraph()

        # Load enterprises as nodes
        qs = Enterprise.objects.all()
        if enterprise_ids:
            qs = qs.filter(id__in=enterprise_ids)

        for ent in qs:
            graph.add_node(GraphNode(
                id=ent.id,
                entity_type=ent.enterprise_type,
                name=ent.name,
                risk_level=ent.risk_level,
                risk_score=ent.risk_score or 0.0,
                properties={
                    'unified_credit_code': ent.unified_credit_code,
                    'industry': ent.industry_name,
                    'is_blacklisted': ent.is_blacklisted,
                },
            ))

        node_ids = set(graph.nodes.keys())

        # Load enterprise relationships as edges
        rel_filter = Q(source_id__in=node_ids) | Q(target_id__in=node_ids)
        for rel in EnterpriseRelationship.objects.filter(rel_filter, is_active=True):
            graph.add_edge(GraphEdge(
                source_id=rel.source_id,
                target_id=rel.target_id,
                edge_type='RELATIONSHIP',
                relation=rel.relation_type,
                weight=rel.confidence_score,
                properties={'equity_ratio': rel.equity_ratio},
            ))

        # Load supply chain links
        link_filter = Q(upstream_id__in=node_ids) | Q(downstream_id__in=node_ids)
        for link in SupplyChainLink.objects.filter(link_filter, is_active=True):
            graph.add_edge(GraphEdge(
                source_id=link.upstream_id,
                target_id=link.downstream_id,
                edge_type='SUPPLY_CHAIN',
                relation=link.link_type,
                weight=link.stability_score or 1.0,
                properties={'volume_share': link.volume_share},
            ))

        # Load transaction edges (optional, can be heavy)
        if include_transactions:
            txn_filter = Q(from_enterprise_id__in=node_ids) | Q(to_enterprise_id__in=node_ids)
            # Aggregate transactions by pair and type
            txn_agg = (
                TransactionEdge.objects
                .filter(txn_filter)
                .values('from_enterprise_id', 'to_enterprise_id', 'transaction_type')
                .annotate(
                    total_amount=Sum('amount'),
                    txn_count=Count('id'),
                    avg_amount=Avg('amount'),
                )
            )
            for txn in txn_agg:
                graph.add_edge(GraphEdge(
                    source_id=txn['from_enterprise_id'],
                    target_id=txn['to_enterprise_id'],
                    edge_type='TRANSACTION',
                    relation=txn['transaction_type'],
                    weight=float(txn['total_amount'] or 0),
                    properties={
                        'total_amount': float(txn['total_amount'] or 0),
                        'count': txn['txn_count'],
                        'avg_amount': float(txn['avg_amount'] or 0),
                    },
                ))

        return graph

    @staticmethod
    def build_enterprise_subgraph(
        enterprise_id: int,
        max_depth: int = 2,
    ) -> SupplyChainGraph:
        """Build a subgraph centered on a specific enterprise."""
        # First build a broader graph, then extract subgraph
        full_graph = GraphStorageManager.build_graph()
        return full_graph.get_subgraph(enterprise_id, max_depth)
