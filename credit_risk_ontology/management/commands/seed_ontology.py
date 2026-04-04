"""
Management command to seed the credit risk ontology system:
1. Bootstrap ontology schema (ObjectTypes, LinkTypes, ActionTypes)
2. Create 15 dimensions x 48 indicator categories
3. Create ~80 key IndicatorDefinitions as a representative starter set
   (the full 1800+ would be loaded from a data file in production)

Usage:
    python manage.py seed_ontology
    python manage.py seed_ontology --reset
"""

from django.core.management.base import BaseCommand

from credit_risk_ontology.models.indicators import IndicatorCategory, IndicatorDefinition
from credit_risk_ontology.services.ontology_service import OntologyService


# 48 indicator categories across 15 dimensions
INDICATOR_CATEGORIES = [
    # 1. Tax & Financial (纳税和财报)
    ('TAX_FINANCIAL', '税务合规性', 'Tax Compliance'),
    ('TAX_FINANCIAL', '盈利能力', 'Profitability'),
    ('TAX_FINANCIAL', '资产质量', 'Asset Quality'),
    ('TAX_FINANCIAL', '负债结构', 'Liability Structure'),
    # 2. Credit Report (征信报告)
    ('CREDIT', '信贷规模', 'Credit Scale'),
    ('CREDIT', '还款历史', 'Repayment History'),
    ('CREDIT', '查询频次', 'Inquiry Frequency'),
    ('CREDIT', '负债水平', 'Debt Level'),
    # 3. Settlement Flow (结算流水)
    ('SETTLEMENT', '账户活跃度', 'Account Activity'),
    ('SETTLEMENT', '现金流稳定性', 'Cash Flow Stability'),
    ('SETTLEMENT', '工资发放规律性', 'Payroll Regularity'),
    ('SETTLEMENT', '收支结构', 'Income/Expense Structure'),
    # 4. Output Invoice (销项发票)
    ('OUTPUT_INVOICE', '销售规模', 'Sales Scale'),
    ('OUTPUT_INVOICE', '客户集中度', 'Customer Concentration'),
    ('OUTPUT_INVOICE', '销售增长', 'Sales Growth'),
    ('OUTPUT_INVOICE', '品类集中度', 'Product Concentration'),
    # 5. Input Invoice (进项发票)
    ('INPUT_INVOICE', '采购规模', 'Purchase Scale'),
    ('INPUT_INVOICE', '供应商集中度', 'Supplier Concentration'),
    ('INPUT_INVOICE', '采购增长', 'Purchase Growth'),
    ('INPUT_INVOICE', '成本结构', 'Cost Structure'),
    # 6. ERP/Logistics (ERP/物流系统)
    ('ERP_LOGISTICS', '订单履约率', 'Order Fulfillment Rate'),
    ('ERP_LOGISTICS', '库存周转', 'Inventory Turnover'),
    ('ERP_LOGISTICS', '物流效率', 'Logistics Efficiency'),
    ('ERP_LOGISTICS', '退货率', 'Return Rate'),
    # 7. Legal Litigation (司法涉诉)
    ('LEGAL', '涉诉频率', 'Litigation Frequency'),
    ('LEGAL', '金融借贷纠纷', 'Loan Disputes'),
    ('LEGAL', '被执行情况', 'Enforcement Status'),
    ('LEGAL', '五年败诉率', 'Five-Year Loss Rate'),
    # 8. Asset Clues (资产线索)
    ('ASSET', '不动产规模', 'Real Estate Scale'),
    ('ASSET', '设备价值', 'Equipment Value'),
    ('ASSET', '知识产权', 'IP Assets'),
    ('ASSET', '资产抵押率', 'Asset Pledge Rate'),
    # 9. Movable Property (动产融资登记)
    ('MOVABLE_PROPERTY', '动产融资规模', 'Movable Property Scale'),
    ('MOVABLE_PROPERTY', '押品到期情况', 'Pledge Maturity'),
    # 10. Business Changes (工商变更&异常)
    ('BUSINESS_CHANGE', '经营稳定性', 'Business Stability'),
    ('BUSINESS_CHANGE', '股权变更频率', 'Shareholder Change Rate'),
    ('BUSINESS_CHANGE', '异常记录', 'Anomaly Records'),
    ('BUSINESS_CHANGE', '法定代表人变更', 'Legal Rep Changes'),
    # 11. News Sentiment (新闻舆情)
    ('NEWS_SENTIMENT', '负面舆情数量', 'Negative News Count'),
    ('NEWS_SENTIMENT', '舆情严重程度', 'Sentiment Severity'),
    ('NEWS_SENTIMENT', '行业整体舆情', 'Industry Sentiment'),
    # 12. Goods & Services (商品&服务交易)
    ('TRANSACTION', '交易规模', 'Transaction Scale'),
    ('TRANSACTION', '交易品类匹配度', 'Category Match Rate'),
    ('TRANSACTION', '水电费稳定性', 'Utility Stability'),
    # 13. Bill Payment (票据支付)
    ('BILL_PAYMENT', '票据承兑规模', 'Bill Acceptance Scale'),
    ('BILL_PAYMENT', '票据逾期情况', 'Bill Overdue Status'),
    # 14. Default Blacklist (违约黑名单)
    ('DEFAULT_BLACKLIST', '违约黑名单状态', 'Default Blacklist Status'),
    ('DEFAULT_BLACKLIST', '失信被执行', 'Lost Trust Enforcement'),
    # 15. Bidding (招投标)
    ('BIDDING', '中标能力', 'Bid Win Rate'),
    ('BIDDING', '项目规模', 'Project Scale'),
]

# Key indicator definitions (representative starter set)
INDICATOR_DEFINITIONS = [
    # --- TAX & FINANCIAL ---
    ('TAX_FINANCIAL', '盈利能力', 'FIN_001', '净利润率', 'Net Profit Margin',
     'PERCENTAGE', 'NEGATIVE', 'HIGH', 'net_profit / revenue'),
    ('TAX_FINANCIAL', '盈利能力', 'FIN_002', '资产收益率(ROA)', 'Return on Assets',
     'PERCENTAGE', 'NEGATIVE', 'HIGH', 'net_profit / total_assets'),
    ('TAX_FINANCIAL', '盈利能力', 'FIN_003', '营收增长率(YoY)', 'Revenue Growth YoY',
     'PERCENTAGE', 'NEGATIVE', 'HIGH', '(revenue_t - revenue_t1) / revenue_t1'),
    ('TAX_FINANCIAL', '资产质量', 'FIN_004', '资产负债率', 'Debt-to-Asset Ratio',
     'PERCENTAGE', 'POSITIVE', 'CRITICAL', 'total_liabilities / total_assets'),
    ('TAX_FINANCIAL', '资产质量', 'FIN_005', '流动比率', 'Current Ratio',
     'NUMERIC', 'POSITIVE', 'HIGH', 'current_assets / current_liabilities'),
    ('TAX_FINANCIAL', '资产质量', 'FIN_006', '速动比率', 'Quick Ratio',
     'NUMERIC', 'POSITIVE', 'HIGH', '(current_assets - inventory) / current_liabilities'),
    ('TAX_FINANCIAL', '负债结构', 'FIN_007', '债务权益比', 'Debt-to-Equity',
     'NUMERIC', 'POSITIVE', 'HIGH', 'total_liabilities / equity'),
    ('TAX_FINANCIAL', '税务合规性', 'FIN_008', '纳税信用等级', 'Tax Credit Rating',
     'CATEGORY', 'NEUTRAL', 'HIGH', 'tax_authority_rating'),
    ('TAX_FINANCIAL', '税务合规性', 'FIN_009', '异常申报标记', 'Abnormal Filing Flag',
     'BOOLEAN', 'POSITIVE', 'CRITICAL', 'is_abnormal_filing'),
    # --- CREDIT ---
    ('CREDIT', '还款历史', 'CR_001', '历史逾期次数', 'Historical Overdue Count',
     'NUMERIC', 'POSITIVE', 'CRITICAL', 'historical_overdue_count'),
    ('CREDIT', '还款历史', 'CR_002', '历史逾期金额', 'Historical Overdue Amount',
     'NUMERIC', 'POSITIVE', 'HIGH', 'historical_overdue_amount'),
    ('CREDIT', '查询频次', 'CR_003', '近半年查询次数', 'Recent 6M Inquiries',
     'NUMERIC', 'POSITIVE', 'MEDIUM', 'recent_inquiry_count'),
    ('CREDIT', '负债水平', 'CR_004', '债务收入比', 'Debt-to-Income Ratio',
     'PERCENTAGE', 'POSITIVE', 'HIGH', 'loan_balance / annual_income'),
    ('CREDIT', '信贷规模', 'CR_005', '授信使用率', 'Credit Utilization Rate',
     'PERCENTAGE', 'POSITIVE', 'MEDIUM', 'loan_balance / credit_amount'),
    ('CREDIT', '信贷规模', 'CR_006', '平均贷款利率', 'Average Loan Rate',
     'PERCENTAGE', 'NEUTRAL', 'MEDIUM', 'average_loan_rate'),
    # --- SETTLEMENT ---
    ('SETTLEMENT', '现金流稳定性', 'SET_001', '日均余额趋势', 'Avg Daily Balance Trend',
     'SCORE', 'POSITIVE', 'HIGH', 'linear_regression_slope(daily_balances)'),
    ('SETTLEMENT', '工资发放规律性', 'SET_002', '工资发放稳定性评分', 'Payroll Stability Score',
     'SCORE', 'POSITIVE', 'MEDIUM', 'payroll_regularity_score'),
    ('SETTLEMENT', '收支结构', 'SET_003', '经营性收入', 'Operating Income',
     'NUMERIC', 'NEGATIVE', 'HIGH', 'sum(inflows)'),
    ('SETTLEMENT', '收支结构', 'SET_004', '收支比', 'Income-to-Expense Ratio',
     'NUMERIC', 'NEGATIVE', 'HIGH', 'operating_income / operating_expenses'),
    # --- OUTPUT INVOICE ---
    ('OUTPUT_INVOICE', '销售规模', 'INV_OUT_001', '年销售总额', 'Annual Sales Total',
     'NUMERIC', 'NEGATIVE', 'HIGH', 'sum(output_invoice_amount)'),
    ('OUTPUT_INVOICE', '客户集中度', 'INV_OUT_002', '前三大客户占比', 'Top-3 Customer Share',
     'PERCENTAGE', 'POSITIVE', 'HIGH', 'top3_customer_amount / total_sales'),
    ('OUTPUT_INVOICE', '销售增长', 'INV_OUT_003', '销售额增长率', 'Sales Growth Rate',
     'PERCENTAGE', 'NEGATIVE', 'HIGH', '(sales_t - sales_t1) / sales_t1'),
    ('OUTPUT_INVOICE', '客户集中度', 'INV_OUT_004', '核心企业交易占比',
     'Core Enterprise Transaction Share',
     'PERCENTAGE', 'NEGATIVE', 'HIGH', 'core_enterprise_sales / total_sales'),
    # --- INPUT INVOICE ---
    ('INPUT_INVOICE', '采购规模', 'INV_IN_001', '年采购总额', 'Annual Purchase Total',
     'NUMERIC', 'NEUTRAL', 'MEDIUM', 'sum(input_invoice_amount)'),
    ('INPUT_INVOICE', '供应商集中度', 'INV_IN_002', '前三大供应商占比', 'Top-3 Supplier Share',
     'PERCENTAGE', 'POSITIVE', 'HIGH', 'top3_supplier_amount / total_purchases'),
    ('INPUT_INVOICE', '成本结构', 'INV_IN_003', '电费/采购额比值', 'Electricity-to-Purchase Ratio',
     'PERCENTAGE', 'NEUTRAL', 'MEDIUM', 'electricity_cost / total_purchases'),
    # --- LEGAL ---
    ('LEGAL', '被执行情况', 'LEG_001', '被执行案件数', 'Enforcement Case Count',
     'NUMERIC', 'POSITIVE', 'CRITICAL', 'enforcement_case_count'),
    ('LEGAL', '金融借贷纠纷', 'LEG_002', '金融借贷涉诉金额', 'Loan Litigation Amount',
     'NUMERIC', 'POSITIVE', 'CRITICAL', 'loan_related_litigation_amount'),
    ('LEGAL', '涉诉频率', 'LEG_003', '五年败诉率', 'Five-Year Loss Rate',
     'PERCENTAGE', 'POSITIVE', 'HIGH', 'lost_cases / total_cases_5y'),
    ('LEGAL', '涉诉频率', 'LEG_004', '司法纠纷总数', 'Total Disputes Count',
     'NUMERIC', 'POSITIVE', 'MEDIUM', 'total_litigation_count'),
    # --- BUSINESS CHANGES ---
    ('BUSINESS_CHANGE', '经营稳定性', 'BIZ_001', '变更次数(2年)', 'Changes Count (2Y)',
     'NUMERIC', 'POSITIVE', 'MEDIUM', 'change_count_2_years'),
    ('BUSINESS_CHANGE', '法定代表人变更', 'BIZ_002', '法定代表人变更次数', 'Legal Rep Changes',
     'NUMERIC', 'POSITIVE', 'HIGH', 'legal_rep_changes_count'),
    ('BUSINESS_CHANGE', '异常记录', 'BIZ_003', '工商异常次数', 'Business Anomaly Count',
     'NUMERIC', 'POSITIVE', 'HIGH', 'business_anomaly_count'),
    # --- NEWS SENTIMENT ---
    ('NEWS_SENTIMENT', '负面舆情数量', 'NEWS_001', '近期负面新闻数', 'Recent Negative News Count',
     'NUMERIC', 'POSITIVE', 'HIGH', 'negative_news_count_90d'),
    ('NEWS_SENTIMENT', '舆情严重程度', 'NEWS_002', '严重负面新闻数', 'Critical Negative News',
     'NUMERIC', 'POSITIVE', 'CRITICAL', 'critical_news_count'),
    ('NEWS_SENTIMENT', '舆情严重程度', 'NEWS_003', '平均舆情情绪分', 'Avg Sentiment Score',
     'SCORE', 'POSITIVE', 'MEDIUM', 'avg(sentiment_score)'),
    # --- BILL PAYMENT ---
    ('BILL_PAYMENT', '票据逾期情况', 'BILL_001', '票据逾期次数', 'Bill Overdue Count',
     'NUMERIC', 'POSITIVE', 'CRITICAL', 'overdue_bill_count'),
    ('BILL_PAYMENT', '票据承兑规模', 'BILL_002', '票据承兑规模', 'Bill Acceptance Scale',
     'NUMERIC', 'NEGATIVE', 'MEDIUM', 'total_bill_amount'),
    ('BILL_PAYMENT', '票据承兑规模', 'BILL_003', '票据销售占比', 'Bill-to-Sales Ratio',
     'PERCENTAGE', 'NEUTRAL', 'MEDIUM', 'bill_amount / total_sales'),
    # --- DEFAULT BLACKLIST ---
    ('DEFAULT_BLACKLIST', '违约黑名单状态', 'BL_001', '违约记录数', 'Active Default Count',
     'NUMERIC', 'POSITIVE', 'CRITICAL', 'active_default_count'),
    ('DEFAULT_BLACKLIST', '失信被执行', 'BL_002', '失信被执行人标记', 'Lost Trust Flag',
     'BOOLEAN', 'POSITIVE', 'CRITICAL', 'is_lost_trust_executor'),
    ('DEFAULT_BLACKLIST', '违约黑名单状态', 'BL_003', '政府采购违约标记', 'Gov Procurement Default',
     'BOOLEAN', 'POSITIVE', 'CRITICAL', 'is_gov_procurement_default'),
    # --- BIDDING ---
    ('BIDDING', '中标能力', 'BID_001', '中标率', 'Bid Win Rate',
     'PERCENTAGE', 'NEGATIVE', 'MEDIUM', 'won_bids / total_bids'),
    ('BIDDING', '项目规模', 'BID_002', '近期中标金额', 'Recent Winning Amount',
     'NUMERIC', 'NEGATIVE', 'MEDIUM', 'sum(winning_amount_12m)'),
    # --- ASSET ---
    ('ASSET', '资产抵押率', 'ASSET_001', '资产抵押率', 'Asset Pledge Rate',
     'PERCENTAGE', 'POSITIVE', 'HIGH', 'pledged_assets / total_assets'),
    ('ASSET', '不动产规模', 'ASSET_002', '不动产估值', 'Real Estate Value',
     'NUMERIC', 'NEGATIVE', 'MEDIUM', 'sum(real_estate_value)'),
    # --- TRANSACTION ---
    ('TRANSACTION', '水电费稳定性', 'TXN_001', '水电费支付稳定性', 'Utility Payment Stability',
     'SCORE', 'POSITIVE', 'MEDIUM', 'utility_regularity_score'),
    ('TRANSACTION', '交易品类匹配度', 'TXN_002', '品牌商品占比', 'Brand Product Share',
     'PERCENTAGE', 'NEGATIVE', 'MEDIUM', 'brand_product_amount / total_goods_amount'),
    # --- ERP/LOGISTICS ---
    ('ERP_LOGISTICS', '订单履约率', 'ERP_001', '订单准时交付率', 'On-Time Delivery Rate',
     'PERCENTAGE', 'POSITIVE', 'HIGH', 'on_time_deliveries / total_orders'),
    ('ERP_LOGISTICS', '库存周转', 'ERP_002', '库存周转率', 'Inventory Turnover Rate',
     'NUMERIC', 'POSITIVE', 'MEDIUM', 'cogs / avg_inventory'),
    ('ERP_LOGISTICS', '退货率', 'ERP_003', '订单退货率', 'Return Rate',
     'PERCENTAGE', 'POSITIVE', 'MEDIUM', 'returned_orders / total_orders'),
]


class Command(BaseCommand):
    help = 'Seed the credit risk ontology with standard schema and indicators'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing categories and indicators before seeding',
        )
        parser.add_argument(
            '--ontology-only',
            action='store_true',
            help='Only bootstrap ontology schema, skip indicators',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting existing data...')
            IndicatorDefinition.objects.all().delete()
            IndicatorCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing indicators cleared.'))

        # Step 1: Bootstrap ontology schema
        self.stdout.write('Bootstrapping ontology schema...')
        result = OntologyService.bootstrap_ontology()
        self.stdout.write(self.style.SUCCESS(
            f'  Created {result["object_types"]} object types, '
            f'{result["link_types"]} link types, '
            f'{result["action_types"]} action types'
        ))

        if options['ontology_only']:
            self.stdout.write(self.style.SUCCESS('Ontology-only mode. Done.'))
            return

        # Step 2: Seed indicator categories
        self.stdout.write('Seeding indicator categories (15 dimensions, 48 categories)...')
        category_map = {}
        for dimension, name_zh, name_en in INDICATOR_CATEGORIES:
            cat, created = IndicatorCategory.objects.get_or_create(
                dimension=dimension,
                name=name_zh,
                defaults={'description': name_en},
            )
            category_map[(dimension, name_zh)] = cat
            if created:
                self.stdout.write(f'  + [{dimension}] {name_zh}')

        self.stdout.write(self.style.SUCCESS(
            f'  {len(INDICATOR_CATEGORIES)} categories seeded.'
        ))

        # Step 3: Seed indicator definitions
        self.stdout.write('Seeding indicator definitions...')
        created_count = 0
        for (dim, cat_name, code, name_zh, name_en,
             dtype, direction, importance, formula) in INDICATOR_DEFINITIONS:
            cat = category_map.get((dim, cat_name))
            if not cat:
                self.stdout.write(self.style.WARNING(
                    f'  Category not found: [{dim}] {cat_name}, skipping {code}'
                ))
                continue
            _, created = IndicatorDefinition.objects.get_or_create(
                code=code,
                defaults={
                    'category': cat,
                    'name': name_zh,
                    'description': name_en,
                    'data_type': dtype,
                    'direction': direction,
                    'importance': importance,
                    'formula': formula,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'  {created_count} indicator definitions seeded '
            f'(starter set from 1800+ total).'
        ))

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Seed complete ==='))
        self.stdout.write(
            f'  IndicatorCategories: {IndicatorCategory.objects.count()}'
        )
        self.stdout.write(
            f'  IndicatorDefinitions: {IndicatorDefinition.objects.count()}'
        )
        self.stdout.write('')
        self.stdout.write(
            'Next step: python manage.py makemigrations credit_risk_ontology && '
            'python manage.py migrate'
        )
