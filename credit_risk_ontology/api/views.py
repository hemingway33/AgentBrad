"""
REST API Views for the Credit Risk Ontology system.

Endpoints:
- /ontology/ - Ontology schema management
- /enterprises/ - Enterprise CRUD
- /relationships/ - Enterprise relationship graph
- /indicators/ - Risk indicator management
- /assessment/ - Risk assessment execution
- /graph/ - Knowledge graph queries
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from credit_risk_ontology.models.ontology import ObjectType, LinkType
from credit_risk_ontology.models.entities import Enterprise, CoreEnterprise
from credit_risk_ontology.models.relationships import (
    EnterpriseRelationship, SupplyChainLink, TransactionEdge,
)
from credit_risk_ontology.models.indicators import (
    IndicatorCategory, IndicatorDefinition, IndicatorValue,
    RiskScore, ComprehensiveRiskProfile,
)
from credit_risk_ontology.services.ontology_service import OntologyService
from credit_risk_ontology.services.risk_assessment import RiskAssessmentService
from credit_risk_ontology.graph.storage import GraphStorageManager
from credit_risk_ontology.graph.query import OntologyQuery

from .serializers import (
    ObjectTypeSerializer, LinkTypeSerializer,
    EnterpriseListSerializer, EnterpriseDetailSerializer,
    CoreEnterpriseSerializer,
    EnterpriseRelationshipSerializer, SupplyChainLinkSerializer,
    TransactionEdgeSerializer,
    IndicatorCategorySerializer, IndicatorDefinitionSerializer,
    IndicatorValueSerializer, RiskScoreSerializer,
    ComprehensiveRiskProfileSerializer,
    RiskAssessmentRequestSerializer, BatchAssessmentRequestSerializer,
    GraphQueryRequestSerializer,
)


class OntologyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Ontology schema management.
    List and inspect object types, link types, and the full ontology graph.
    """
    queryset = ObjectType.objects.all()
    serializer_class = ObjectTypeSerializer

    @action(detail=False, methods=['post'])
    def bootstrap(self, request):
        """Bootstrap the standard supply chain credit risk ontology."""
        result = OntologyService.bootstrap_ontology()
        return Response({
            'status': 'success',
            'message': 'Ontology bootstrapped successfully',
            'created': result,
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get ontology schema summary."""
        return Response(OntologyService.get_ontology_summary())

    @action(detail=False, methods=['get'])
    def link_types(self, request):
        """List all link types."""
        links = LinkType.objects.all()
        serializer = LinkTypeSerializer(links, many=True)
        return Response(serializer.data)


class EnterpriseViewSet(viewsets.ModelViewSet):
    """
    Enterprise CRUD with risk-aware filtering.
    """
    queryset = Enterprise.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return EnterpriseListSerializer
        return EnterpriseDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Filter by enterprise type
        etype = self.request.query_params.get('type')
        if etype:
            qs = qs.filter(enterprise_type=etype)
        # Filter by risk level
        risk = self.request.query_params.get('risk_level')
        if risk:
            qs = qs.filter(risk_level=risk)
        # Filter by blacklist
        blacklisted = self.request.query_params.get('blacklisted')
        if blacklisted is not None:
            qs = qs.filter(is_blacklisted=blacklisted.lower() == 'true')
        return qs

    @action(detail=True, methods=['get'])
    def risk_profile(self, request, pk=None):
        """Get the latest comprehensive risk profile."""
        profiles = ComprehensiveRiskProfile.objects.filter(
            enterprise_id=pk,
        ).order_by('-evaluated_at')[:1]
        if profiles:
            serializer = ComprehensiveRiskProfileSerializer(profiles[0])
            return Response(serializer.data)
        return Response(
            {'detail': 'No risk profile found. Run assessment first.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    @action(detail=True, methods=['get'])
    def indicators(self, request, pk=None):
        """Get indicator values for an enterprise."""
        values = IndicatorValue.objects.filter(
            enterprise_id=pk,
        ).select_related('indicator').order_by('-evaluated_at')[:100]
        serializer = IndicatorValueSerializer(values, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def relationships(self, request, pk=None):
        """Get all relationships for an enterprise."""
        outgoing = EnterpriseRelationship.objects.filter(source_id=pk)
        incoming = EnterpriseRelationship.objects.filter(target_id=pk)
        return Response({
            'outgoing': EnterpriseRelationshipSerializer(outgoing, many=True).data,
            'incoming': EnterpriseRelationshipSerializer(incoming, many=True).data,
        })

    @action(detail=True, methods=['get'])
    def supply_chain(self, request, pk=None):
        """Get supply chain links for an enterprise."""
        upstream = SupplyChainLink.objects.filter(downstream_id=pk)
        downstream = SupplyChainLink.objects.filter(upstream_id=pk)
        return Response({
            'upstream': SupplyChainLinkSerializer(upstream, many=True).data,
            'downstream': SupplyChainLinkSerializer(downstream, many=True).data,
        })


class RelationshipViewSet(viewsets.ModelViewSet):
    """Enterprise relationship graph edges."""
    queryset = EnterpriseRelationship.objects.all()
    serializer_class = EnterpriseRelationshipSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        relation_type = self.request.query_params.get('relation_type')
        if relation_type:
            qs = qs.filter(relation_type=relation_type)
        return qs


class SupplyChainLinkViewSet(viewsets.ModelViewSet):
    """Supply chain link edges."""
    queryset = SupplyChainLink.objects.all()
    serializer_class = SupplyChainLinkSerializer


class IndicatorViewSet(viewsets.ReadOnlyModelViewSet):
    """Risk indicator definitions and categories."""
    queryset = IndicatorDefinition.objects.all()
    serializer_class = IndicatorDefinitionSerializer

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """List all indicator categories."""
        categories = IndicatorCategory.objects.all()
        serializer = IndicatorCategorySerializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_dimension(self, request):
        """Group indicators by dimension."""
        dimension = request.query_params.get('dimension')
        qs = self.queryset
        if dimension:
            qs = qs.filter(category__dimension=dimension)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class RiskAssessmentViewSet(viewsets.ViewSet):
    """
    Risk assessment execution endpoints.
    Trigger assessments and retrieve results.
    """

    @action(detail=False, methods=['post'])
    def assess(self, request):
        """Run risk assessment for a single enterprise."""
        serializer = RiskAssessmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enterprise_id = serializer.validated_data['enterprise_id']
        try:
            service = RiskAssessmentService()
            result = service.assess_enterprise(enterprise_id)
            return Response({
                'status': 'success',
                'enterprise_id': enterprise_id,
                'assessment': result,
            })
        except Enterprise.DoesNotExist:
            return Response(
                {'detail': 'Enterprise not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {'detail': f'Assessment failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'])
    def batch_assess(self, request):
        """Run risk assessment for multiple enterprises."""
        serializer = BatchAssessmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enterprise_ids = serializer.validated_data['enterprise_ids']
        service = RiskAssessmentService()
        results = service.batch_assess(enterprise_ids)
        return Response({
            'status': 'success',
            'count': len(results),
            'results': results,
        })

    @action(detail=False, methods=['get'])
    def scores(self, request):
        """Get risk scores with filtering."""
        enterprise_id = request.query_params.get('enterprise_id')
        score_type = request.query_params.get('score_type')

        qs = RiskScore.objects.all()
        if enterprise_id:
            qs = qs.filter(enterprise_id=enterprise_id)
        if score_type:
            qs = qs.filter(score_type=score_type)

        qs = qs.order_by('-evaluated_at')[:100]
        serializer = RiskScoreSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def profiles(self, request):
        """Get comprehensive risk profiles."""
        enterprise_id = request.query_params.get('enterprise_id')
        risk_level = request.query_params.get('risk_level')

        qs = ComprehensiveRiskProfile.objects.all()
        if enterprise_id:
            qs = qs.filter(enterprise_id=enterprise_id)
        if risk_level:
            qs = qs.filter(overall_risk_level=risk_level)

        qs = qs.order_by('-evaluated_at')[:50]
        serializer = ComprehensiveRiskProfileSerializer(qs, many=True)
        return Response(serializer.data)


class GraphViewSet(viewsets.ViewSet):
    """
    Knowledge graph query endpoints.
    Build and query the supply chain knowledge graph.
    """

    @action(detail=False, methods=['post'])
    def subgraph(self, request):
        """Get the subgraph centered on an enterprise."""
        serializer = GraphQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enterprise_id = serializer.validated_data['enterprise_id']
        max_depth = serializer.validated_data['max_depth']

        graph = GraphStorageManager.build_enterprise_subgraph(
            enterprise_id, max_depth,
        )
        return Response(graph.to_dict())

    @action(detail=False, methods=['post'])
    def query(self, request):
        """
        Run an ontology query on the graph.

        Body: {
            "object_type": "CORE",
            "filters": [{"field": "risk_level", "operator": "eq", "value": "HIGH"}],
            "linked_to": {"target_type": "SUPPLIER", "via": "SUPPLY_CHAIN"},
            "limit": 20
        }
        """
        graph = GraphStorageManager.build_graph()
        query = OntologyQuery(graph)

        object_type = request.data.get('object_type')
        if object_type:
            query = query.objects(object_type)

        for f in request.data.get('filters', []):
            query = query.where(f['field'], f['operator'], f['value'])

        link = request.data.get('linked_to')
        if link:
            query = query.linked_to(
                link['target_type'],
                via=link.get('via'),
                direction=link.get('direction', 'outgoing'),
            )

        limit = request.data.get('limit', 50)
        query = query.limit(limit)

        result = query.execute()
        return Response({
            'total_count': result.total_count,
            'nodes': [
                {
                    'id': n.id,
                    'name': n.name,
                    'type': n.entity_type,
                    'risk_level': n.risk_level,
                    'risk_score': n.risk_score,
                }
                for n in result.nodes
            ],
            'aggregations': result.aggregations,
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get overall graph statistics."""
        graph = GraphStorageManager.build_graph(include_transactions=False)
        centrality = graph.compute_degree_centrality()
        pagerank = graph.compute_pagerank()

        top_centrality = sorted(
            centrality.items(), key=lambda x: x[1], reverse=True,
        )[:10]
        top_pagerank = sorted(
            pagerank.items(), key=lambda x: x[1], reverse=True,
        )[:10]

        return Response({
            'node_count': graph.node_count,
            'edge_count': graph.edge_count,
            'top_centrality': [
                {
                    'id': nid,
                    'name': graph.get_node(nid).name if graph.get_node(nid) else '',
                    'centrality': round(c, 4),
                }
                for nid, c in top_centrality
            ],
            'top_pagerank': [
                {
                    'id': nid,
                    'name': graph.get_node(nid).name if graph.get_node(nid) else '',
                    'pagerank': round(pr, 6),
                }
                for nid, pr in top_pagerank
            ],
        })
