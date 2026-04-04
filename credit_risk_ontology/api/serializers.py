"""
REST API Serializers for the Credit Risk Ontology system.
"""

from rest_framework import serializers

from credit_risk_ontology.models.ontology import ObjectType, LinkType, ActionType
from credit_risk_ontology.models.entities import Enterprise, CoreEnterprise
from credit_risk_ontology.models.relationships import (
    EnterpriseRelationship, SupplyChainLink, TransactionEdge,
)
from credit_risk_ontology.models.indicators import (
    IndicatorCategory, IndicatorDefinition, IndicatorValue,
    RiskScore, ComprehensiveRiskProfile,
)


# --- Ontology Serializers ---

class ObjectTypeSerializer(serializers.ModelSerializer):
    properties_count = serializers.IntegerField(
        source='properties.count', read_only=True,
    )

    class Meta:
        model = ObjectType
        fields = [
            'id', 'name', 'display_name', 'description', 'category',
            'primary_key_property', 'title_property', 'is_abstract',
            'properties_count', 'created_at',
        ]


class LinkTypeSerializer(serializers.ModelSerializer):
    source_type_name = serializers.CharField(source='source_type.name', read_only=True)
    target_type_name = serializers.CharField(source='target_type.name', read_only=True)

    class Meta:
        model = LinkType
        fields = [
            'id', 'name', 'display_name', 'description',
            'source_type', 'source_type_name',
            'target_type', 'target_type_name',
            'cardinality', 'inverse_name',
        ]


# --- Enterprise Serializers ---

class EnterpriseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enterprise
        fields = [
            'id', 'name', 'unified_credit_code', 'enterprise_type',
            'industry_name', 'risk_level', 'risk_score', 'is_active',
            'is_blacklisted',
        ]


class EnterpriseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enterprise
        fields = '__all__'


class CoreEnterpriseSerializer(serializers.ModelSerializer):
    enterprise = EnterpriseListSerializer(read_only=True)

    class Meta:
        model = CoreEnterprise
        fields = '__all__'


# --- Relationship Serializers ---

class EnterpriseRelationshipSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    target_name = serializers.CharField(source='target.name', read_only=True)

    class Meta:
        model = EnterpriseRelationship
        fields = [
            'id', 'source', 'source_name', 'target', 'target_name',
            'relation_type', 'equity_ratio', 'confidence_score',
            'is_active', 'start_date',
        ]


class SupplyChainLinkSerializer(serializers.ModelSerializer):
    upstream_name = serializers.CharField(source='upstream.name', read_only=True)
    downstream_name = serializers.CharField(source='downstream.name', read_only=True)

    class Meta:
        model = SupplyChainLink
        fields = [
            'id', 'upstream', 'upstream_name', 'downstream', 'downstream_name',
            'link_type', 'annual_volume', 'volume_share',
            'stability_score', 'is_active',
        ]


class TransactionEdgeSerializer(serializers.ModelSerializer):
    from_name = serializers.CharField(source='from_enterprise.name', read_only=True)
    to_name = serializers.CharField(source='to_enterprise.name', read_only=True)

    class Meta:
        model = TransactionEdge
        fields = [
            'id', 'from_enterprise', 'from_name',
            'to_enterprise', 'to_name',
            'transaction_type', 'amount', 'transaction_date',
        ]


# --- Indicator Serializers ---

class IndicatorCategorySerializer(serializers.ModelSerializer):
    indicator_count = serializers.IntegerField(
        source='indicators.count', read_only=True,
    )

    class Meta:
        model = IndicatorCategory
        fields = [
            'id', 'name', 'dimension', 'description',
            'weight', 'indicator_count',
        ]


class IndicatorDefinitionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = IndicatorDefinition
        fields = [
            'id', 'code', 'name', 'description', 'category', 'category_name',
            'data_type', 'importance', 'direction', 'unit', 'weight',
        ]


class IndicatorValueSerializer(serializers.ModelSerializer):
    indicator_code = serializers.CharField(source='indicator.code', read_only=True)
    indicator_name = serializers.CharField(source='indicator.name', read_only=True)

    class Meta:
        model = IndicatorValue
        fields = [
            'id', 'enterprise', 'indicator', 'indicator_code', 'indicator_name',
            'numeric_value', 'text_value', 'boolean_value',
            'risk_classification', 'confidence', 'evaluated_at',
        ]


class RiskScoreSerializer(serializers.ModelSerializer):
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)

    class Meta:
        model = RiskScore
        fields = [
            'id', 'enterprise', 'enterprise_name', 'score_type',
            'dimension', 'score', 'risk_level', 'contributing_factors',
            'evaluated_at',
        ]


class ComprehensiveRiskProfileSerializer(serializers.ModelSerializer):
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)

    class Meta:
        model = ComprehensiveRiskProfile
        fields = [
            'id', 'enterprise', 'enterprise_name',
            'overall_score', 'overall_risk_level',
            'dimension_scores', 'anti_fraud_score', 'kyb_score',
            'risk_rating', 'recommended_credit_limit',
            'risk_alerts', 'is_shell_company_suspected', 'is_fraud_suspected',
            'evaluated_at', 'evaluation_notes',
        ]


# --- Assessment Request/Response Serializers ---

class RiskAssessmentRequestSerializer(serializers.Serializer):
    enterprise_id = serializers.IntegerField()


class BatchAssessmentRequestSerializer(serializers.Serializer):
    enterprise_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100,
    )


class GraphQueryRequestSerializer(serializers.Serializer):
    enterprise_id = serializers.IntegerField()
    max_depth = serializers.IntegerField(default=2, min_value=1, max_value=5)
    include_transactions = serializers.BooleanField(default=True)
