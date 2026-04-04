"""
Ontology Query Language - Palantir-style typed queries over the knowledge graph.

Provides a fluent query interface for:
- Object search with property filters
- Link traversal with type constraints
- Aggregation across the graph
- Pattern matching for risk detection
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .storage import SupplyChainGraph, GraphNode, GraphEdge


@dataclass
class QueryFilter:
    """A filter condition on node or edge properties."""
    field: str
    operator: str  # 'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'contains'
    value: Any


@dataclass
class QueryResult:
    """Result of an ontology query."""
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    aggregations: dict = field(default_factory=dict)
    total_count: int = 0


class OntologyQuery:
    """
    Fluent query builder for the supply chain knowledge graph.

    Usage:
        query = OntologyQuery(graph)
        results = (
            query
            .objects('CORE')
            .where('risk_level', 'eq', 'HIGH')
            .linked_to('SUPPLIER', via='SUPPLY_CHAIN')
            .execute()
        )
    """

    def __init__(self, graph: SupplyChainGraph):
        self.graph = graph
        self._object_type: Optional[str] = None
        self._filters: list[QueryFilter] = []
        self._link_traversals: list[dict] = []
        self._aggregations: list[str] = []
        self._limit: Optional[int] = None
        self._offset: int = 0
        self._order_by: Optional[tuple[str, bool]] = None  # (field, ascending)

    def objects(self, object_type: str) -> 'OntologyQuery':
        """Start query with a specific object type."""
        self._object_type = object_type
        return self

    def where(self, field: str, operator: str, value: Any) -> 'OntologyQuery':
        """Add a filter condition."""
        self._filters.append(QueryFilter(field=field, operator=operator, value=value))
        return self

    def linked_to(
        self,
        target_type: str,
        via: Optional[str] = None,
        direction: str = 'outgoing',
    ) -> 'OntologyQuery':
        """Add a link traversal step."""
        self._link_traversals.append({
            'target_type': target_type,
            'edge_type': via,
            'direction': direction,
        })
        return self

    def aggregate(self, *aggregation_types: str) -> 'OntologyQuery':
        """Add aggregation operations ('count', 'avg_risk', 'sum_amount')."""
        self._aggregations.extend(aggregation_types)
        return self

    def limit(self, n: int) -> 'OntologyQuery':
        self._limit = n
        return self

    def offset(self, n: int) -> 'OntologyQuery':
        self._offset = n
        return self

    def order_by(self, field: str, ascending: bool = True) -> 'OntologyQuery':
        self._order_by = (field, ascending)
        return self

    def execute(self) -> QueryResult:
        """Execute the query and return results."""
        # Step 1: Get initial node set
        if self._object_type:
            nodes = self.graph.get_nodes_by_type(self._object_type)
        else:
            nodes = list(self.graph.nodes.values())

        # Step 2: Apply property filters
        for f in self._filters:
            nodes = [n for n in nodes if self._apply_filter(n, f)]

        # Step 3: Apply link traversals
        result_edges = []
        for traversal in self._link_traversals:
            expanded_nodes = []
            for node in nodes:
                neighbors = self.graph.get_neighbors(
                    node.id,
                    edge_type=traversal.get('edge_type'),
                    direction=traversal.get('direction', 'outgoing'),
                )
                for neighbor, edge in neighbors:
                    target_type = traversal.get('target_type')
                    if not target_type or neighbor.entity_type == target_type:
                        expanded_nodes.append(neighbor)
                        result_edges.append(edge)
            nodes = expanded_nodes

        # Step 4: Ordering
        if self._order_by:
            field_name, ascending = self._order_by
            nodes.sort(
                key=lambda n: self._get_field(n, field_name) or 0,
                reverse=not ascending,
            )

        total_count = len(nodes)

        # Step 5: Pagination
        if self._offset:
            nodes = nodes[self._offset:]
        if self._limit:
            nodes = nodes[:self._limit]

        # Step 6: Aggregations
        aggregations = {}
        if 'count' in self._aggregations:
            aggregations['count'] = total_count
        if 'avg_risk' in self._aggregations:
            scores = [n.risk_score for n in nodes if n.risk_score]
            aggregations['avg_risk'] = sum(scores) / len(scores) if scores else 0
        if 'sum_amount' in self._aggregations:
            aggregations['sum_amount'] = sum(
                e.weight for e in result_edges
            )

        return QueryResult(
            nodes=nodes,
            edges=result_edges,
            aggregations=aggregations,
            total_count=total_count,
        )

    @staticmethod
    def _apply_filter(node: GraphNode, f: QueryFilter) -> bool:
        """Apply a single filter to a node."""
        value = OntologyQuery._get_field(node, f.field)
        if value is None:
            return False

        op = f.operator
        if op == 'eq':
            return value == f.value
        elif op == 'ne':
            return value != f.value
        elif op == 'gt':
            return value > f.value
        elif op == 'gte':
            return value >= f.value
        elif op == 'lt':
            return value < f.value
        elif op == 'lte':
            return value <= f.value
        elif op == 'in':
            return value in f.value
        elif op == 'contains':
            return f.value in str(value)
        return False

    @staticmethod
    def _get_field(node: GraphNode, field: str) -> Any:
        """Get a field value from a node."""
        if hasattr(node, field):
            return getattr(node, field)
        return node.properties.get(field)


class PatternMatcher:
    """
    Graph pattern matching for detecting specific risk patterns.
    Similar to Palantir's "Functions on Objects" but for risk patterns.
    """

    def __init__(self, graph: SupplyChainGraph):
        self.graph = graph

    def match_triangle(
        self,
        edge_type: str = 'TRANSACTION',
    ) -> list[tuple[int, int, int]]:
        """Find triangular transaction patterns (A->B->C->A)."""
        triangles = []
        visited = set()

        for node_id in self.graph.nodes:
            neighbors_out = {
                e.target_id: e
                for e in self.graph.adjacency.get(node_id, [])
                if e.edge_type == edge_type
            }
            for n1_id in neighbors_out:
                n1_out = {
                    e.target_id: e
                    for e in self.graph.adjacency.get(n1_id, [])
                    if e.edge_type == edge_type
                }
                for n2_id in n1_out:
                    if n2_id in neighbors_out or node_id in {
                        e.target_id
                        for e in self.graph.adjacency.get(n2_id, [])
                        if e.edge_type == edge_type
                    }:
                        tri = tuple(sorted([node_id, n1_id, n2_id]))
                        if tri not in visited:
                            visited.add(tri)
                            triangles.append((node_id, n1_id, n2_id))

        return triangles

    def match_star_pattern(
        self,
        min_spokes: int = 5,
        edge_type: Optional[str] = None,
    ) -> list[dict]:
        """Find star patterns (one hub connected to many nodes)."""
        stars = []
        for node_id, node in self.graph.nodes.items():
            out_edges = self.graph.adjacency.get(node_id, [])
            if edge_type:
                out_edges = [e for e in out_edges if e.edge_type == edge_type]
            if len(out_edges) >= min_spokes:
                stars.append({
                    'hub_id': node_id,
                    'hub_name': node.name,
                    'spoke_count': len(out_edges),
                    'spoke_ids': [e.target_id for e in out_edges],
                })
        return stars

    def match_chain_pattern(
        self,
        start_type: str,
        end_type: str,
        max_length: int = 5,
    ) -> list[list[int]]:
        """Find chain patterns from start_type to end_type nodes."""
        chains = []
        start_nodes = self.graph.get_nodes_by_type(start_type)

        for start in start_nodes:
            self._dfs_chain(
                start.id, end_type, [start.id], set(), max_length, chains,
            )

        return chains

    def _dfs_chain(self, current_id, end_type, path, visited, max_len, results):
        if len(path) > max_len + 1:
            return
        node = self.graph.get_node(current_id)
        if node and node.entity_type == end_type and len(path) > 1:
            results.append(list(path))
            return

        visited.add(current_id)
        for neighbor, edge in self.graph.get_neighbors(current_id, direction='outgoing'):
            if neighbor.id not in visited:
                path.append(neighbor.id)
                self._dfs_chain(neighbor.id, end_type, path, visited, max_len, results)
                path.pop()
        visited.discard(current_id)
