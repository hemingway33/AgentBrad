from django.contrib import admin

from .models.ontology import ObjectType, PropertyType, LinkType, ActionType
from .models.entities import (
    Enterprise, CoreEnterprise, FinancialInstitution, Supplier,
    ProductionSupplier, Distributor, SalesTrader, TerminalEcommerce,
    RelatedEnterprise, ShellCompany,
)
from .models.data_sources import (
    TaxFinancialReport, CreditReport, SettlementRecord,
    OutputInvoice, InputInvoice, ERPLogisticsRecord,
    LegalLitigation, AssetClue, MovablePropertyRegistration,
    BusinessChange, NewsSentiment, GoodsServiceTransaction,
    BillPayment, DefaultBlacklist, BiddingRecord,
)
from .models.relationships import (
    EnterpriseRelationship, SupplyChainLink, TransactionEdge,
)
from .models.indicators import (
    IndicatorCategory, IndicatorDefinition, IndicatorValue,
    RiskScore, ComprehensiveRiskProfile,
)


# --- Ontology Admin ---

@admin.register(ObjectType)
class ObjectTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('name', 'description')


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'object_type', 'data_type', 'is_required')
    list_filter = ('data_type', 'is_required', 'object_type')


@admin.register(LinkType)
class LinkTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'target_type', 'cardinality')
    list_filter = ('cardinality',)


@admin.register(ActionType)
class ActionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'object_type', 'created_at')


# --- Entity Admin ---

@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ('name', 'unified_credit_code', 'enterprise_type', 'risk_level', 'is_active')
    list_filter = ('enterprise_type', 'risk_level', 'is_active')
    search_fields = ('name', 'unified_credit_code')


@admin.register(CoreEnterprise)
class CoreEnterpriseAdmin(admin.ModelAdmin):
    list_display = ('enterprise', 'whitelist_grade', 'credit_limit', 'is_in_whitelist')
    list_filter = ('whitelist_grade', 'is_in_whitelist')


@admin.register(FinancialInstitution)
class FinancialInstitutionAdmin(admin.ModelAdmin):
    list_display = ('enterprise', 'institution_type', 'license_number')


for model_class in [
    Supplier, ProductionSupplier, Distributor, SalesTrader,
    TerminalEcommerce, RelatedEnterprise, ShellCompany,
]:
    admin.site.register(model_class)


# --- Data Sources Admin ---

for model_class in [
    TaxFinancialReport, CreditReport, SettlementRecord,
    OutputInvoice, InputInvoice, ERPLogisticsRecord,
    LegalLitigation, AssetClue, MovablePropertyRegistration,
    BusinessChange, NewsSentiment, GoodsServiceTransaction,
    BillPayment, DefaultBlacklist, BiddingRecord,
]:
    admin.site.register(model_class)


# --- Relationships Admin ---

@admin.register(EnterpriseRelationship)
class EnterpriseRelationshipAdmin(admin.ModelAdmin):
    list_display = ('source', 'target', 'relation_type', 'confidence_score')
    list_filter = ('relation_type',)


@admin.register(SupplyChainLink)
class SupplyChainLinkAdmin(admin.ModelAdmin):
    list_display = ('upstream', 'downstream', 'link_type', 'is_active')
    list_filter = ('link_type', 'is_active')


@admin.register(TransactionEdge)
class TransactionEdgeAdmin(admin.ModelAdmin):
    list_display = ('from_enterprise', 'to_enterprise', 'transaction_type', 'amount')
    list_filter = ('transaction_type',)


# --- Indicators Admin ---

@admin.register(IndicatorCategory)
class IndicatorCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'dimension', 'parent')
    list_filter = ('dimension',)


@admin.register(IndicatorDefinition)
class IndicatorDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'data_type', 'importance')
    list_filter = ('category', 'importance', 'data_type')
    search_fields = ('name', 'code')


@admin.register(IndicatorValue)
class IndicatorValueAdmin(admin.ModelAdmin):
    list_display = ('enterprise', 'indicator', 'numeric_value', 'evaluated_at')
    list_filter = ('indicator__category',)


@admin.register(RiskScore)
class RiskScoreAdmin(admin.ModelAdmin):
    list_display = ('enterprise', 'score_type', 'score', 'risk_level', 'evaluated_at')
    list_filter = ('score_type', 'risk_level')


@admin.register(ComprehensiveRiskProfile)
class ComprehensiveRiskProfileAdmin(admin.ModelAdmin):
    list_display = ('enterprise', 'overall_score', 'overall_risk_level', 'evaluated_at')
    list_filter = ('overall_risk_level',)
