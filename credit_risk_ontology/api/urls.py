from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    OntologyViewSet,
    EnterpriseViewSet,
    RelationshipViewSet,
    SupplyChainLinkViewSet,
    IndicatorViewSet,
    RiskAssessmentViewSet,
    GraphViewSet,
)

router = DefaultRouter()
router.register('ontology', OntologyViewSet, basename='ontology')
router.register('enterprises', EnterpriseViewSet, basename='enterprise')
router.register('relationships', RelationshipViewSet, basename='relationship')
router.register('supply-chain-links', SupplyChainLinkViewSet, basename='supply-chain-link')
router.register('indicators', IndicatorViewSet, basename='indicator')
router.register('assessment', RiskAssessmentViewSet, basename='assessment')
router.register('graph', GraphViewSet, basename='graph')

urlpatterns = [
    path('', include(router.urls)),
]
