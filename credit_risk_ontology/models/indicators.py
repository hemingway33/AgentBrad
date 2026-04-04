"""
Risk Indicator Models - 15 dimensions, 48 categories, 1800+ indicators.

Implements the indicator framework for credit risk assessment:
- IndicatorCategory: 48 indicator categories across 15 dimensions
- IndicatorDefinition: 1800+ individual indicator definitions
- IndicatorValue: Computed indicator values per enterprise
- RiskScore: Aggregated risk scores by dimension
- ComprehensiveRiskProfile: Overall enterprise risk profile
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class IndicatorCategory(models.Model):
    """
    48 indicator categories organized under 15 risk dimensions.
    Dimensions map to the diagram's data source types.
    """

    DIMENSION_CHOICES = [
        ('TAX_FINANCIAL', 'Tax & Financial (纳税和财报)'),
        ('CREDIT', 'Credit Report (征信报告)'),
        ('SETTLEMENT', 'Settlement Flow (结算流水)'),
        ('OUTPUT_INVOICE', 'Output Invoice (销项发票)'),
        ('INPUT_INVOICE', 'Input Invoice (进项发票)'),
        ('ERP_LOGISTICS', 'ERP/Logistics (ERP/物流系统)'),
        ('LEGAL', 'Legal Litigation (司法涉诉)'),
        ('ASSET', 'Asset Clues (资产线索)'),
        ('MOVABLE_PROPERTY', 'Movable Property (动产融资登记)'),
        ('BUSINESS_CHANGE', 'Business Changes (工商变更&异常)'),
        ('NEWS_SENTIMENT', 'News Sentiment (新闻舆情)'),
        ('TRANSACTION', 'Goods & Services (商品&服务交易)'),
        ('BILL_PAYMENT', 'Bill Payment (票据支付)'),
        ('DEFAULT_BLACKLIST', 'Default Blacklist (违约黑名单)'),
        ('BIDDING', 'Bidding & Tender (招投标)'),
    ]

    name = models.CharField(max_length=128)
    dimension = models.CharField(max_length=20, choices=DIMENSION_CHOICES)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.CASCADE, related_name='children',
    )
    weight = models.FloatField(
        default=1.0,
        help_text='Weight in risk scoring aggregation',
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['dimension', 'sort_order']
        verbose_name = 'Indicator Category'
        verbose_name_plural = 'Indicator Categories'

    def __str__(self):
        return f"[{self.get_dimension_display()}] {self.name}"


class IndicatorDefinition(models.Model):
    """
    Individual indicator definition - one of 1800+ risk indicators.
    Each defines a specific metric that can be computed from data sources.
    """

    DATA_TYPE_CHOICES = [
        ('NUMERIC', 'Numeric'),
        ('PERCENTAGE', 'Percentage'),
        ('BOOLEAN', 'Boolean Flag'),
        ('CATEGORY', 'Categorical'),
        ('SCORE', 'Computed Score'),
    ]

    IMPORTANCE_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]

    DIRECTION_CHOICES = [
        ('POSITIVE', 'Higher is Better'),
        ('NEGATIVE', 'Lower is Better'),
        ('NEUTRAL', 'No Direction'),
    ]

    category = models.ForeignKey(
        IndicatorCategory, on_delete=models.CASCADE, related_name='indicators',
    )
    name = models.CharField(max_length=256)
    code = models.CharField(max_length=64, unique=True, help_text='Unique indicator code')
    description = models.TextField(blank=True)
    data_type = models.CharField(max_length=16, choices=DATA_TYPE_CHOICES)
    importance = models.CharField(max_length=16, choices=IMPORTANCE_CHOICES, default='MEDIUM')
    direction = models.CharField(max_length=16, choices=DIRECTION_CHOICES, default='NEUTRAL')
    # Computation
    formula = models.TextField(
        blank=True,
        help_text='Python expression or rule for computing this indicator',
    )
    data_source_fields = models.JSONField(
        default=list, blank=True,
        help_text='List of data source fields this indicator depends on',
    )
    # Thresholds for risk classification
    thresholds = models.JSONField(
        default=dict, blank=True,
        help_text='{"low": 0, "medium": 30, "high": 60, "critical": 80}',
    )
    unit = models.CharField(max_length=32, blank=True)
    weight = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'code']
        verbose_name = 'Indicator Definition'

    def __str__(self):
        return f"{self.code}: {self.name}"


class IndicatorValue(models.Model):
    """
    Computed indicator values for a specific enterprise at a point in time.
    """

    enterprise = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='indicator_values',
    )
    indicator = models.ForeignKey(
        IndicatorDefinition, on_delete=models.CASCADE, related_name='values',
    )
    numeric_value = models.FloatField(null=True, blank=True)
    text_value = models.CharField(max_length=256, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    json_value = models.JSONField(null=True, blank=True)
    # Risk classification for this specific indicator
    risk_classification = models.CharField(
        max_length=16, blank=True,
        choices=[
            ('LOW', 'Low Risk'),
            ('MEDIUM', 'Medium Risk'),
            ('HIGH', 'High Risk'),
            ('CRITICAL', 'Critical Risk'),
        ],
    )
    confidence = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    evaluated_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['enterprise', 'indicator']),
            models.Index(fields=['evaluated_at']),
        ]
        verbose_name = 'Indicator Value'

    def __str__(self):
        val = self.numeric_value or self.text_value or self.boolean_value
        return f"{self.enterprise.name} | {self.indicator.code} = {val}"


class RiskScore(models.Model):
    """
    Aggregated risk scores per dimension for an enterprise.
    Supports: anti-fraud, KYB, risk rating, credit assessment, post-loan monitoring.
    """

    SCORE_TYPE_CHOICES = [
        ('ANTI_FRAUD', 'Anti-Fraud Score (反欺诈)'),
        ('KYB', 'Know Your Business (KYB)'),
        ('RISK_RATING', 'Risk Rating (风险评级)'),
        ('CREDIT_ASSESSMENT', 'Credit Assessment (授信测额)'),
        ('POST_LOAN', 'Post-Loan Monitoring (贷后监控)'),
        ('DIMENSION', 'Dimension Score'),
    ]

    RISK_LEVEL_CHOICES = [
        ('AAA', 'AAA - Excellent'),
        ('AA', 'AA - Very Good'),
        ('A', 'A - Good'),
        ('BBB', 'BBB - Adequate'),
        ('BB', 'BB - Below Average'),
        ('B', 'B - Poor'),
        ('CCC', 'CCC - Very Poor'),
        ('CC', 'CC - High Risk'),
        ('C', 'C - Very High Risk'),
        ('D', 'D - Default'),
    ]

    enterprise = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='risk_scores',
    )
    score_type = models.CharField(max_length=20, choices=SCORE_TYPE_CHOICES)
    dimension = models.CharField(max_length=20, blank=True)
    score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    risk_level = models.CharField(max_length=4, choices=RISK_LEVEL_CHOICES, blank=True)
    contributing_factors = models.JSONField(default=list, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    model_version = models.CharField(max_length=32, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['enterprise', 'score_type']),
            models.Index(fields=['evaluated_at']),
        ]
        verbose_name = 'Risk Score'

    def __str__(self):
        return (
            f"{self.enterprise.name} | {self.get_score_type_display()}: "
            f"{self.score} ({self.risk_level})"
        )


class ComprehensiveRiskProfile(models.Model):
    """
    Overall comprehensive risk profile integrating all dimensions.
    This is the top-level output of the ontology reasoning system.
    """

    enterprise = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='risk_profiles',
    )
    overall_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    overall_risk_level = models.CharField(
        max_length=16,
        choices=[
            ('LOW', 'Low Risk'),
            ('MEDIUM', 'Medium Risk'),
            ('HIGH', 'High Risk'),
            ('CRITICAL', 'Critical Risk'),
        ],
    )
    # Per-dimension breakdown
    dimension_scores = models.JSONField(
        default=dict, blank=True,
        help_text='Scores per dimension: {"TAX_FINANCIAL": 85, ...}',
    )
    # Application-specific scores
    anti_fraud_score = models.FloatField(null=True, blank=True)
    kyb_score = models.FloatField(null=True, blank=True)
    risk_rating = models.CharField(max_length=4, blank=True)
    recommended_credit_limit = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    # Alerts and flags
    risk_alerts = models.JSONField(default=list, blank=True)
    is_shell_company_suspected = models.BooleanField(default=False)
    is_fraud_suspected = models.BooleanField(default=False)
    # Metadata
    evaluated_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    evaluation_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-evaluated_at']
        verbose_name = 'Comprehensive Risk Profile'

    def __str__(self):
        return (
            f"{self.enterprise.name} | Overall: {self.overall_score} "
            f"({self.overall_risk_level})"
        )
