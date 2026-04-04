"""
Ontology Service - Manages ontology type definitions and bootstraps
the standard supply chain credit risk ontology schema.

Provides CRUD operations on ObjectTypes, PropertyTypes, LinkTypes,
and seeds the system with the standard schema from the diagram.
"""

from credit_risk_ontology.models.ontology import (
    ObjectType, PropertyType, LinkType, ActionType,
)


class OntologyService:
    """Service for managing the ontology schema."""

    @staticmethod
    def bootstrap_ontology():
        """
        Bootstrap the standard supply chain credit risk ontology.
        Creates all ObjectTypes, PropertyTypes, and LinkTypes
        matching the diagram's entity and relationship structure.
        """
        # --- Object Types (Entity layer) ---
        entity_types = [
            ('CoreEnterprise', 'Core Enterprise (核心企业)', 'ENTITY'),
            ('FinancialInstitution', 'Financial Institution (金融机构)', 'ENTITY'),
            ('Supplier', 'Supplier (供应商)', 'ENTITY'),
            ('ProductionSupplier', 'Production Supplier (生产型供应商)', 'ENTITY'),
            ('Distributor', 'Distributor (经销商)', 'ENTITY'),
            ('SalesTrader', 'Sales Trader (销售型贸易商)', 'ENTITY'),
            ('TerminalEcommerce', 'Terminal & E-commerce (终端&电商)', 'ENTITY'),
            ('RelatedEnterprise', 'Related Enterprise (关联企业)', 'ENTITY'),
            ('ShellCompany', 'Shell Company (空壳和包装公司)', 'ENTITY'),
        ]

        # --- Object Types (Data Source layer) ---
        data_source_types = [
            ('TaxFinancialReport', 'Tax & Financial Report (纳税和财报)', 'DATA_SOURCE'),
            ('CreditReport', 'Credit Report (征信报告)', 'DATA_SOURCE'),
            ('SettlementRecord', 'Settlement Record (结算流水)', 'DATA_SOURCE'),
            ('OutputInvoice', 'Output Invoice (销项发票)', 'DATA_SOURCE'),
            ('InputInvoice', 'Input Invoice (进项发票)', 'DATA_SOURCE'),
            ('ERPLogistics', 'ERP/Logistics System (ERP/物流系统)', 'DATA_SOURCE'),
            ('LegalLitigation', 'Legal Litigation (司法涉诉解析)', 'DATA_SOURCE'),
            ('AssetClue', 'Asset Clue (资产线索)', 'DATA_SOURCE'),
            ('MovableProperty', 'Movable Property Registration (动产融资登记)', 'DATA_SOURCE'),
            ('BusinessChange', 'Business Change & Anomaly (工商变更&异常)', 'DATA_SOURCE'),
            ('NewsSentiment', 'News & Sentiment (新闻舆情)', 'DATA_SOURCE'),
            ('GoodsTransaction', 'Goods & Service Transaction (商品&服务交易)', 'DATA_SOURCE'),
            ('BillPayment', 'Bill Payment (票据支付)', 'DATA_SOURCE'),
            ('DefaultBlacklist', 'Default Blacklist (违约黑名单)', 'DATA_SOURCE'),
            ('BiddingRecord', 'Bidding Record (招投标)', 'DATA_SOURCE'),
        ]

        # --- Object Types (Knowledge Base layer) ---
        kb_types = [
            ('CoreEnterpriseWhitelist', 'Core Enterprise Whitelist (核企白名单库)', 'DOCUMENT'),
            ('IndustryRiskFactor', 'Industry Risk Factor Library (行业风险因子库)', 'DOCUMENT'),
            ('BrandProductLibrary', 'Brand Product Library (品牌商品库)', 'PRODUCT'),
            ('IndustryChainProductLibrary', 'Industry Chain Product Library (产业链商品库)', 'PRODUCT'),
        ]

        all_types = entity_types + data_source_types + kb_types
        created_types = {}

        for name, display, category in all_types:
            obj_type, _ = ObjectType.objects.update_or_create(
                name=name,
                defaults={
                    'display_name': display,
                    'category': category,
                },
            )
            created_types[name] = obj_type

        # --- Link Types (Relationship layer) ---
        link_definitions = [
            # Supply chain links
            ('supplies_to', 'Supplies To', 'Supplier', 'CoreEnterprise',
             'MANY_TO_MANY', 'supplied_by'),
            ('produces_for', 'Produces For', 'ProductionSupplier', 'CoreEnterprise',
             'MANY_TO_MANY', 'produced_by'),
            ('distributes_from', 'Distributes From', 'CoreEnterprise', 'Distributor',
             'ONE_TO_MANY', 'distributed_by'),
            ('sells_to', 'Sells To', 'Distributor', 'TerminalEcommerce',
             'MANY_TO_MANY', 'purchased_from'),
            ('trades_with', 'Trades With', 'SalesTrader', 'CoreEnterprise',
             'MANY_TO_MANY', 'traded_with'),
            # Financial links
            ('provides_credit', 'Provides Credit Report', 'FinancialInstitution',
             'CoreEnterprise', 'ONE_TO_MANY', 'credit_from'),
            ('guarantees', 'Guarantees', 'CoreEnterprise', 'CoreEnterprise',
             'MANY_TO_MANY', 'guaranteed_by'),
            # Related party links
            ('related_to', 'Related To', 'RelatedEnterprise', 'CoreEnterprise',
             'MANY_TO_MANY', 'has_related'),
            ('controls', 'Controls', 'CoreEnterprise', 'RelatedEnterprise',
             'ONE_TO_MANY', 'controlled_by'),
            # Data source links
            ('has_tax_report', 'Has Tax Report', 'CoreEnterprise',
             'TaxFinancialReport', 'ONE_TO_MANY', 'tax_report_of'),
            ('has_credit_report', 'Has Credit Report', 'CoreEnterprise',
             'CreditReport', 'ONE_TO_MANY', 'credit_report_of'),
            ('has_settlement', 'Has Settlement', 'CoreEnterprise',
             'SettlementRecord', 'ONE_TO_MANY', 'settlement_of'),
            ('issues_invoice', 'Issues Invoice', 'CoreEnterprise',
             'OutputInvoice', 'ONE_TO_MANY', 'invoice_from'),
            ('receives_invoice', 'Receives Invoice', 'CoreEnterprise',
             'InputInvoice', 'ONE_TO_MANY', 'invoice_to'),
            # Industry/product links
            ('belongs_to_industry', 'Belongs To Industry', 'CoreEnterprise',
             'IndustryRiskFactor', 'MANY_TO_ONE', 'industry_enterprises'),
            ('in_whitelist', 'In Whitelist', 'CoreEnterprise',
             'CoreEnterpriseWhitelist', 'MANY_TO_ONE', 'whitelist_members'),
        ]

        for (name, display, src, tgt, card, inverse) in link_definitions:
            if src in created_types and tgt in created_types:
                LinkType.objects.update_or_create(
                    name=name,
                    defaults={
                        'display_name': display,
                        'source_type': created_types[src],
                        'target_type': created_types[tgt],
                        'cardinality': card,
                        'inverse_name': inverse,
                    },
                )

        # --- Action Types ---
        action_definitions = [
            ('assess_risk', 'Assess Risk', 'CoreEnterprise',
             'Run comprehensive risk assessment'),
            ('detect_fraud', 'Detect Fraud', 'CoreEnterprise',
             'Run anti-fraud detection rules'),
            ('compute_credit_limit', 'Compute Credit Limit', 'CoreEnterprise',
             'Calculate recommended credit limit'),
            ('flag_shell', 'Flag Shell Company', 'ShellCompany',
             'Flag enterprise as suspected shell company'),
            ('update_blacklist', 'Update Blacklist', 'CoreEnterprise',
             'Check and update default blacklist status'),
        ]

        for name, display, obj_type_name, desc in action_definitions:
            if obj_type_name in created_types:
                ActionType.objects.update_or_create(
                    name=name,
                    object_type=created_types[obj_type_name],
                    defaults={
                        'display_name': display,
                        'description': desc,
                    },
                )

        return {
            'object_types': len(all_types),
            'link_types': len(link_definitions),
            'action_types': len(action_definitions),
        }

    @staticmethod
    def get_ontology_summary() -> dict:
        """Return a summary of the current ontology schema."""
        return {
            'object_types': list(
                ObjectType.objects.values('name', 'display_name', 'category')
            ),
            'link_types': list(
                LinkType.objects.values(
                    'name', 'display_name',
                    'source_type__name', 'target_type__name', 'cardinality',
                )
            ),
            'action_types': list(
                ActionType.objects.values('name', 'display_name', 'object_type__name')
            ),
            'stats': {
                'total_object_types': ObjectType.objects.count(),
                'total_link_types': LinkType.objects.count(),
                'total_action_types': ActionType.objects.count(),
                'total_property_types': PropertyType.objects.count(),
            },
        }
