"""
Data Source Models - Multi-source data collection across 15 dimensions.

Maps to the diagram's data source boxes:
- 纳税和财报 (Tax & Financial Reports)
- 征信报告 (Credit Reports)
- 结算流水 (Settlement Records)
- 销项发票 / 进项发票 (Output/Input Invoices)
- ERP/物流系统 (ERP/Logistics)
- 司法涉诉解析 (Legal Litigation)
- 资产线索 (Asset Clues)
- 动产融资登记 (Movable Property Registration)
- 工商变更&异常 (Business Changes)
- 新闻舆情 (News Sentiment)
- 商品&服务交易 (Goods & Service Transactions)
- 票据支付 (Bill Payment)
- 违约黑名单 (Default Blacklist)
- 招投标 (Bidding)
"""

from django.db import models


class DataSourceBase(models.Model):
    """Abstract base for all data sources."""

    enterprise = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='%(class)s_records',
    )
    source_system = models.CharField(max_length=128, blank=True)
    data_quality_score = models.FloatField(null=True, blank=True)
    collected_at = models.DateTimeField(auto_now_add=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True


class TaxFinancialReport(DataSourceBase):
    """
    纳税和财报 - Tax filing and financial report data.
    Entity: Tax filing/payment records.
    Properties: filing type, filing date, tax amount, etc.
    Relations: tax filing -> bank, occurrence -> bank.
    Indicators: net profit, assets, liabilities, tax revenue,
                tax credit rating, abnormal filing behavior.
    """

    REPORT_TYPE_CHOICES = [
        ('TAX_FILING', 'Tax Filing'),
        ('ANNUAL_REPORT', 'Annual Financial Report'),
        ('QUARTERLY_REPORT', 'Quarterly Report'),
        ('MONTHLY_TAX', 'Monthly Tax Declaration'),
    ]

    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    filing_date = models.DateField()
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    net_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    total_assets = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    total_liabilities = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    tax_credit_rating = models.CharField(max_length=4, blank=True)
    is_abnormal = models.BooleanField(default=False)
    abnormal_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Tax & Financial Report'
        ordering = ['-filing_date']


class CreditReport(DataSourceBase):
    """
    征信报告 - Credit report from financial institutions.
    Entity: Financial institution.
    Properties: credit amount, loan balance, loan interest.
    Relations: credit application -> bank.
    Indicators: recent loan count, historical overdue, avg loan rate, debt-to-income.
    """

    reporting_institution = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='issued_credit_reports',
        null=True, blank=True,
    )
    report_date = models.DateField()
    credit_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    loan_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    loan_interest_rate = models.FloatField(null=True, blank=True)
    recent_inquiry_count = models.IntegerField(default=0)
    recent_loan_count = models.IntegerField(default=0)
    historical_overdue_count = models.IntegerField(default=0)
    historical_overdue_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
    )
    average_loan_rate = models.FloatField(null=True, blank=True)
    debt_to_income_ratio = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = 'Credit Report'
        ordering = ['-report_date']


class SettlementRecord(DataSourceBase):
    """
    结算流水 - Settlement/transaction flow records.
    Entity: Settlement counterparty.
    Properties: account usage, transaction date, balance.
    Relations: outflow -> customer, inflow -> supplier.
    Indicators: average daily balance, salary payment stability,
                operating income, operating expenses.
    """

    counterparty = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE,
        related_name='settlement_counterparty_records',
        null=True, blank=True,
    )
    account_number = models.CharField(max_length=64)
    transaction_date = models.DateField()
    transaction_amount = models.DecimalField(max_digits=20, decimal_places=2)
    direction = models.CharField(max_length=8, choices=[
        ('INFLOW', 'Inflow (收入)'),
        ('OUTFLOW', 'Outflow (支出)'),
    ])
    balance_after = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    purpose = models.CharField(max_length=256, blank=True)
    # Derived indicators
    avg_daily_balance = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    salary_stability_score = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = 'Settlement Record'
        ordering = ['-transaction_date']


class OutputInvoice(DataSourceBase):
    """
    销项发票 - Output/sales invoices from the enterprise.
    Entity: Downstream customer.
    Properties: invoice amount, tax amount, product/service description.
    Indicators: sales amount growth rate, core enterprise transaction share,
                purchased goods concentration.
    """

    customer = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE,
        related_name='received_invoices', null=True, blank=True,
    )
    invoice_number = models.CharField(max_length=64)
    invoice_date = models.DateField()
    amount_before_tax = models.DecimalField(max_digits=20, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    product_description = models.TextField(blank=True)
    is_void = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Output Invoice (销项发票)'
        ordering = ['-invoice_date']


class InputInvoice(DataSourceBase):
    """
    进项发票 - Input/purchase invoices received by the enterprise.
    Entity: Upstream supplier.
    Properties: cooperation status, duration, etc.
    Indicators: purchase amount growth rate, electricity cost ratio,
                purchased goods concentration.
    """

    supplier = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE,
        related_name='issued_invoices', null=True, blank=True,
    )
    invoice_number = models.CharField(max_length=64)
    invoice_date = models.DateField()
    amount_before_tax = models.DecimalField(max_digits=20, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    product_description = models.TextField(blank=True)
    cooperation_duration_months = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Input Invoice (进项发票)'
        ordering = ['-invoice_date']


class ERPLogisticsRecord(DataSourceBase):
    """
    ERP/物流系统 - Enterprise ERP and logistics system data.
    Entity: Orders, logistics.
    Properties: transaction/order/delivery info.
    Relations: receive -> customer, dispatch -> destination.
    Indicators: order delivery growth rate, order amount, average return rate,
                customer price evaluation.
    """

    RECORD_TYPE_CHOICES = [
        ('ORDER', 'Purchase Order'),
        ('DELIVERY', 'Delivery/Shipment'),
        ('RETURN', 'Return'),
        ('INVENTORY', 'Inventory Snapshot'),
    ]

    record_type = models.CharField(max_length=16, choices=RECORD_TYPE_CHOICES)
    order_number = models.CharField(max_length=64)
    order_date = models.DateField()
    counterparty = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE,
        related_name='erp_counterparty_records', null=True, blank=True,
    )
    product_name = models.CharField(max_length=256, blank=True)
    quantity = models.FloatField(default=0)
    unit_price = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    logistics_company = models.CharField(max_length=128, blank=True)
    tracking_number = models.CharField(max_length=128, blank=True)

    class Meta:
        verbose_name = 'ERP/Logistics Record'
        ordering = ['-order_date']


class LegalLitigation(DataSourceBase):
    """
    司法涉诉解析 - Legal litigation analysis.
    Entity: Legal cases.
    Properties: case type, judgment, subject matter.
    Relations: plaintiff -> court, defendant -> court.
    Indicators: recent financial loan litigation amount, contract amount,
                five-year loss ratio, judicial dispute count.
    """

    CASE_TYPE_CHOICES = [
        ('CIVIL', 'Civil Case'),
        ('CRIMINAL', 'Criminal Case'),
        ('ADMINISTRATIVE', 'Administrative Case'),
        ('ENFORCEMENT', 'Enforcement Case'),
    ]

    ROLE_CHOICES = [
        ('PLAINTIFF', 'Plaintiff'),
        ('DEFENDANT', 'Defendant'),
        ('THIRD_PARTY', 'Third Party'),
    ]

    case_number = models.CharField(max_length=128)
    case_type = models.CharField(max_length=16, choices=CASE_TYPE_CHOICES)
    enterprise_role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    counterparty_name = models.CharField(max_length=256, blank=True)
    case_date = models.DateField()
    subject_amount = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    court_name = models.CharField(max_length=128, blank=True)
    judgment_result = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Legal Litigation'
        ordering = ['-case_date']


class AssetClue(DataSourceBase):
    """
    资产线索 - Asset discovery clues.
    Mining client assets in real estate, equipment, patents,
    intellectual property, special qualifications, overseas investments.
    """

    ASSET_TYPE_CHOICES = [
        ('REAL_ESTATE', 'Real Estate (不动产)'),
        ('EQUIPMENT', 'Equipment (设备)'),
        ('PATENT', 'Patent (专利知识产权)'),
        ('QUALIFICATION', 'Special Qualification (特种资质)'),
        ('OVERSEAS', 'Overseas Investment (外投资)'),
        ('VEHICLE', 'Vehicle'),
        ('OTHER', 'Other'),
    ]

    asset_type = models.CharField(max_length=16, choices=ASSET_TYPE_CHOICES)
    asset_description = models.TextField()
    estimated_value = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    is_pledged = models.BooleanField(default=False)
    pledge_holder = models.CharField(max_length=256, blank=True)
    registration_number = models.CharField(max_length=128, blank=True)
    location = models.CharField(max_length=512, blank=True)

    class Meta:
        verbose_name = 'Asset Clue'


class MovablePropertyRegistration(DataSourceBase):
    """
    动产融资登记 - Movable property financing registration.
    Identifies and dynamically maintains registered movable property,
    supports transaction and risk control.
    """

    REGISTRATION_TYPE_CHOICES = [
        ('PLEDGE', 'Pledge Registration (质押登记)'),
        ('TRANSFER', 'Transfer Registration (转让登记)'),
        ('CHANGE', 'Change Registration (变更登记)'),
        ('CANCEL', 'Cancellation (注销登记)'),
    ]

    registration_number = models.CharField(max_length=128)
    registration_type = models.CharField(max_length=16, choices=REGISTRATION_TYPE_CHOICES)
    registration_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    pledgor = models.CharField(max_length=256)
    pledgee = models.CharField(max_length=256)
    property_description = models.TextField()
    property_value = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    secured_amount = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )

    class Meta:
        verbose_name = 'Movable Property Registration'
        ordering = ['-registration_date']


class BusinessChange(DataSourceBase):
    """
    工商变更&异常 - Business registration changes and anomalies.
    Recent years' representative changes, shareholder changes,
    business scope changes, registered capital changes, etc.
    """

    CHANGE_TYPE_CHOICES = [
        ('LEGAL_REP', 'Legal Representative Change'),
        ('SHAREHOLDER', 'Shareholder Change'),
        ('SCOPE', 'Business Scope Change'),
        ('CAPITAL', 'Registered Capital Change'),
        ('ADDRESS', 'Address Change'),
        ('NAME', 'Company Name Change'),
        ('ANOMALY', 'Business Anomaly'),
    ]

    change_type = models.CharField(max_length=16, choices=CHANGE_TYPE_CHOICES)
    change_date = models.DateField()
    description = models.TextField()
    before_value = models.TextField(blank=True)
    after_value = models.TextField(blank=True)
    is_anomaly = models.BooleanField(default=False)
    anomaly_severity = models.IntegerField(
        null=True, blank=True,
        help_text='1-5, with 5 being most severe',
    )

    class Meta:
        verbose_name = 'Business Change & Anomaly'
        ordering = ['-change_date']


class NewsSentiment(DataSourceBase):
    """
    新闻舆情 - News and public sentiment monitoring.
    Entity: News/public sentiment.
    Properties: news source, publish date, content.
    Relations: news -> source, news -> subject.
    Indicators: recent negative news count, enterprise clean-up
                responsible person negative info count, major
                default-related news count.
    """

    SENTIMENT_CHOICES = [
        ('POSITIVE', 'Positive'),
        ('NEUTRAL', 'Neutral'),
        ('NEGATIVE', 'Negative'),
        ('CRITICAL', 'Critical Negative'),
    ]

    title = models.CharField(max_length=512)
    source = models.CharField(max_length=128)
    publish_date = models.DateField()
    content_summary = models.TextField(blank=True)
    sentiment = models.CharField(max_length=16, choices=SENTIMENT_CHOICES)
    sentiment_score = models.FloatField(null=True, blank=True)
    relevance_score = models.FloatField(null=True, blank=True)
    topics = models.JSONField(default=list, blank=True)
    url = models.URLField(max_length=1024, blank=True)

    class Meta:
        verbose_name = 'News & Sentiment'
        ordering = ['-publish_date']


class GoodsServiceTransaction(DataSourceBase):
    """
    商品&服务交易 - Goods and services transaction data.
    Entity: Products/services.
    Properties: product category, industry attribute.
    Relations: supplier -> goods, buyer -> goods.
    Indicators: utility payment stability, brand product share.
    """

    product_name = models.CharField(max_length=256)
    product_category = models.CharField(max_length=128, blank=True)
    industry_attribute = models.CharField(max_length=128, blank=True)
    quantity = models.FloatField(default=0)
    unit_price = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2)
    transaction_date = models.DateField()
    counterparty = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE,
        related_name='goods_service_counterparty', null=True, blank=True,
    )
    is_brand_product = models.BooleanField(default=False)
    brand_name = models.CharField(max_length=128, blank=True)

    class Meta:
        verbose_name = 'Goods & Service Transaction'
        ordering = ['-transaction_date']


class BillPayment(DataSourceBase):
    """
    票据支付 - Bill/note payment records.
    Entity: Bills/notes electronic.
    Properties: maturity date, amount, endorsement.
    Relations: debtor -> creditor -> endorser -> enterprise.
    Indicators: bill payment-to-sales ratio, bearer person
                core enterprise verification.
    """

    BILL_TYPE_CHOICES = [
        ('BANK_ACCEPTANCE', 'Bank Acceptance Bill'),
        ('COMMERCIAL_ACCEPTANCE', 'Commercial Acceptance Bill'),
        ('ELECTRONIC', 'Electronic Commercial Bill'),
    ]

    bill_number = models.CharField(max_length=128)
    bill_type = models.CharField(max_length=24, choices=BILL_TYPE_CHOICES)
    issue_date = models.DateField()
    maturity_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    drawer = models.CharField(max_length=256)
    payee = models.CharField(max_length=256)
    acceptor = models.CharField(max_length=256, blank=True)
    endorsement_chain = models.JSONField(default=list, blank=True)
    is_discounted = models.BooleanField(default=False)
    is_overdue = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Bill Payment'
        ordering = ['-maturity_date']


class DefaultBlacklist(DataSourceBase):
    """
    违约黑名单 - Default/blacklist records.
    Dynamically maintains public market breach records:
    bond defaults, bill acceptance defaults, government procurement
    defaults, lost trust enforcement, financial loan defaults.
    """

    DEFAULT_TYPE_CHOICES = [
        ('BOND', 'Bond Default (发债违约)'),
        ('BILL', 'Bill Acceptance Default (票据承兑违约)'),
        ('GOV_PROCUREMENT', 'Government Procurement Default'),
        ('TRUST_BREACH', 'Lost Trust Enforcement (失信被执行)'),
        ('LOAN', 'Financial Loan Default (金融借贷违约)'),
    ]

    default_type = models.CharField(max_length=20, choices=DEFAULT_TYPE_CHOICES)
    default_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    case_number = models.CharField(max_length=128, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Default Blacklist Record'
        ordering = ['-default_date']


class BiddingRecord(DataSourceBase):
    """
    招投标 - Bidding and tender records.
    Entity: Bidding projects.
    Properties: project type, bid amount, scope.
    Relations: bidder -> project, tenderer -> winner.
    Indicators: recent winning bid amount, enterprise asset situation,
                bid success rate.
    """

    RESULT_CHOICES = [
        ('WON', 'Won Bid'),
        ('LOST', 'Lost Bid'),
        ('PENDING', 'Pending'),
        ('CANCELLED', 'Cancelled'),
    ]

    project_name = models.CharField(max_length=512)
    project_type = models.CharField(max_length=128, blank=True)
    tender_date = models.DateField()
    bid_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    winning_amount = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    tenderer = models.CharField(max_length=256, blank=True)
    result = models.CharField(max_length=16, choices=RESULT_CHOICES, default='PENDING')

    class Meta:
        verbose_name = 'Bidding Record'
        ordering = ['-tender_date']
