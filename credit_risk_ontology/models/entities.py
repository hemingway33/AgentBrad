"""
Enterprise Entity Models - the core business objects in the supply chain credit risk graph.

Maps directly to the diagram's entity nodes:
- 核心企业 A/B (Core Enterprise)
- 金融机构 (Financial Institution)
- 供应商 (Supplier)
- 生产型供应商 (Production Supplier)
- 经销商 (Distributor)
- 销售型贸易商 (Sales Trader)
- 终端&电商 (Terminal & E-commerce)
- 关联企业 (Related Enterprise)
- 空壳和包装公司 (Shell Company)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Enterprise(models.Model):
    """
    Base entity for all enterprises in the supply chain graph.
    Every node in the knowledge graph that represents a business entity
    inherits from this base.
    """

    ENTERPRISE_TYPE_CHOICES = [
        ('CORE', 'Core Enterprise (核心企业)'),
        ('FINANCIAL', 'Financial Institution (金融机构)'),
        ('SUPPLIER', 'Supplier (供应商)'),
        ('PRODUCTION_SUPPLIER', 'Production Supplier (生产型供应商)'),
        ('DISTRIBUTOR', 'Distributor (经销商)'),
        ('SALES_TRADER', 'Sales Trader (销售型贸易商)'),
        ('TERMINAL_ECOM', 'Terminal & E-commerce (终端&电商)'),
        ('RELATED', 'Related Enterprise (关联企业)'),
        ('SHELL', 'Shell Company (空壳和包装公司)'),
    ]

    RISK_LEVEL_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
        ('UNKNOWN', 'Unknown'),
    ]

    # Basic identification
    name = models.CharField(max_length=256, verbose_name='Enterprise Name (企业名称)')
    unified_credit_code = models.CharField(
        max_length=18, unique=True, verbose_name='Unified Social Credit Code (统一社会信用代码)',
    )
    enterprise_type = models.CharField(max_length=32, choices=ENTERPRISE_TYPE_CHOICES)
    legal_representative = models.CharField(max_length=128, blank=True)
    registered_capital = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    registered_address = models.TextField(blank=True)
    business_scope = models.TextField(blank=True)
    establishment_date = models.DateField(null=True, blank=True)
    industry_code = models.CharField(max_length=16, blank=True)
    industry_name = models.CharField(max_length=128, blank=True)

    # Risk assessment summary
    risk_level = models.CharField(
        max_length=16, choices=RISK_LEVEL_CHOICES, default='UNKNOWN',
    )
    risk_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['unified_credit_code']),
            models.Index(fields=['enterprise_type']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['industry_code']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_enterprise_type_display()})"


class CoreEnterprise(models.Model):
    """
    核心企业 - The anchor enterprise in supply chain finance.
    Maintains whitelist (~220k Grade A, B, C enterprises).
    Accepts purchase orders, dispatches goods, manages logistics.
    """

    WHITELIST_GRADE_CHOICES = [
        ('A', 'Grade A'),
        ('B', 'Grade B'),
        ('C', 'Grade C'),
    ]

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='core_profile',
    )
    whitelist_grade = models.CharField(
        max_length=1, choices=WHITELIST_GRADE_CHOICES, blank=True,
    )
    is_in_whitelist = models.BooleanField(default=False)
    credit_limit = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
        verbose_name='Credit Limit (授信额度)',
    )
    # Counterparty transaction list maintained by the core enterprise
    counterparty_list = models.JSONField(default=list, blank=True)
    # Supply chain position
    upstream_count = models.IntegerField(default=0)
    downstream_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Core Enterprise Profile'

    def __str__(self):
        return f"Core: {self.enterprise.name} (Grade {self.whitelist_grade})"


class FinancialInstitution(models.Model):
    """
    金融机构 - Banks and financial institutions providing credit reports
    and financing services.

    Data: credit amount, loan balance, loan interest, credit history.
    Relations: credit application -> bank, occurrence -> bank.
    Indicators: recent loan count, historical overdue, average loan rate, debt ratio.
    """

    INSTITUTION_TYPE_CHOICES = [
        ('BANK', 'Commercial Bank'),
        ('POLICY_BANK', 'Policy Bank'),
        ('NBFI', 'Non-Bank Financial Institution'),
        ('GUARANTEE', 'Guarantee Company'),
        ('FACTORING', 'Factoring Company'),
        ('LEASING', 'Financial Leasing'),
    ]

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='financial_profile',
    )
    institution_type = models.CharField(max_length=16, choices=INSTITUTION_TYPE_CHOICES)
    license_number = models.CharField(max_length=64, blank=True)
    total_credit_extended = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
    )
    total_loan_balance = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
    )

    class Meta:
        verbose_name = 'Financial Institution Profile'

    def __str__(self):
        return f"FI: {self.enterprise.name} ({self.get_institution_type_display()})"


class Supplier(models.Model):
    """
    供应商 - Supplies goods/services, forming accounts receivable.
    """

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='supplier_profile',
    )
    supply_category = models.CharField(max_length=128, blank=True)
    annual_supply_volume = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    accounts_receivable = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
    )
    average_payment_days = models.IntegerField(null=True, blank=True)
    cooperation_years = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Supplier Profile'

    def __str__(self):
        return f"Supplier: {self.enterprise.name}"


class ProductionSupplier(models.Model):
    """
    生产型供应商 - Production-oriented supplier.
    Provides produced goods/services, forming accounts receivable.
    Connected to core enterprise via purchase orders, invoices, logistics.
    """

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='production_supplier_profile',
    )
    production_capacity = models.JSONField(default=dict, blank=True)
    main_products = models.JSONField(default=list, blank=True)
    quality_certification = models.JSONField(default=list, blank=True)
    equipment_value = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    factory_area = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = 'Production Supplier Profile'

    def __str__(self):
        return f"Prod Supplier: {self.enterprise.name}"


class Distributor(models.Model):
    """
    经销商 - Distributors/dealers in the downstream supply chain.

    Data sources: order reviews, order sales growth rate, order amount, etc.
    Relations: customer -> distributor.
    Indicators: customer price evaluation.
    """

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='distributor_profile',
    )
    distribution_region = models.JSONField(default=list, blank=True)
    annual_sales_volume = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    order_growth_rate = models.FloatField(null=True, blank=True)
    sales_growth_rate = models.FloatField(null=True, blank=True)
    gross_margin = models.FloatField(null=True, blank=True)
    customer_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Distributor Profile'

    def __str__(self):
        return f"Distributor: {self.enterprise.name}"


class SalesTrader(models.Model):
    """
    销售型贸易商 - Sales-oriented trading company.
    """

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='sales_trader_profile',
    )
    trading_products = models.JSONField(default=list, blank=True)
    annual_trading_volume = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    supplier_count = models.IntegerField(default=0)
    customer_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Sales Trader Profile'

    def __str__(self):
        return f"Trader: {self.enterprise.name}"


class TerminalEcommerce(models.Model):
    """
    终端&电商 - Terminal retail and e-commerce platforms.

    Data: industry sentiment, average gross margin, average account period,
    normal inventory turnover, industry leader enterprise bond and credit
    rating info, key enterprise status in the industry.
    """

    CHANNEL_TYPE_CHOICES = [
        ('OFFLINE', 'Offline Retail'),
        ('ONLINE', 'Online E-commerce'),
        ('HYBRID', 'Omni-channel'),
    ]

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='terminal_ecom_profile',
    )
    channel_type = models.CharField(max_length=16, choices=CHANNEL_TYPE_CHOICES)
    platform_name = models.CharField(max_length=128, blank=True)
    monthly_gmv = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    average_order_value = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    inventory_turnover_rate = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = 'Terminal & E-commerce Profile'

    def __str__(self):
        return f"Terminal: {self.enterprise.name}"


class RelatedEnterprise(models.Model):
    """
    关联企业 - Entities related to the target enterprise through
    shareholding, common directors, family ties, etc.

    Key indicators: related party transaction share, related enterprise
    open case ratio, related enterprise execution amount.
    """

    RELATION_NATURE_CHOICES = [
        ('SHAREHOLDER', 'Shareholding Relationship'),
        ('DIRECTOR', 'Common Director'),
        ('FAMILY', 'Family Relationship'),
        ('GUARANTEE', 'Mutual Guarantee'),
        ('INVESTMENT', 'Investment Relationship'),
        ('CONTROL', 'Actual Control'),
    ]

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='related_profile',
    )
    relation_nature = models.CharField(max_length=16, choices=RELATION_NATURE_CHOICES)
    related_to = models.ForeignKey(
        Enterprise, on_delete=models.CASCADE, related_name='related_enterprises',
    )
    equity_share = models.FloatField(null=True, blank=True)
    transaction_share = models.FloatField(
        null=True, blank=True,
        help_text='Percentage of transactions with the related party',
    )
    execution_amount = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )

    class Meta:
        verbose_name = 'Related Enterprise Profile'

    def __str__(self):
        return f"Related: {self.enterprise.name} -> {self.related_to.name}"


class ShellCompany(models.Model):
    """
    空壳和包装公司 - Shell and packaging companies.
    Identified and dynamically maintained to flag fabricated entities.
    Used in fraud detection to discover fictitious supply chain participants.
    """

    DETECTION_METHOD_CHOICES = [
        ('RULE_BASED', 'Rule-based Detection'),
        ('ML_MODEL', 'Machine Learning'),
        ('MANUAL', 'Manual Investigation'),
        ('GRAPH_ANALYSIS', 'Graph Pattern Analysis'),
    ]

    enterprise = models.OneToOneField(
        Enterprise, on_delete=models.CASCADE, related_name='shell_profile',
    )
    is_confirmed_shell = models.BooleanField(default=False)
    detection_method = models.CharField(
        max_length=16, choices=DETECTION_METHOD_CHOICES, blank=True,
    )
    shell_indicators = models.JSONField(
        default=dict, blank=True,
        help_text='Evidence indicators suggesting shell company status',
    )
    # Common shell company signals
    has_real_office = models.BooleanField(default=True)
    has_real_employees = models.BooleanField(default=True)
    has_real_business = models.BooleanField(default=True)
    tax_anomaly_score = models.FloatField(default=0)
    detected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Shell Company Profile'
        verbose_name_plural = 'Shell Company Profiles'

    def __str__(self):
        status = "Confirmed" if self.is_confirmed_shell else "Suspected"
        return f"Shell({status}): {self.enterprise.name}"
