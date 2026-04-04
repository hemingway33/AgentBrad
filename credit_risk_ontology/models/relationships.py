"""
Graph Relationship Models - Edges in the supply chain knowledge graph.

Three core relationship layers:
1. EnterpriseRelationship - Ownership, control, guarantee relationships
2. SupplyChainLink - Upstream/downstream supply chain connections
3. TransactionEdge - Actual financial transaction flows
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class EnterpriseRelationship(models.Model):
    """
    Enterprise relationship graph edges (企业关系图谱).
    Entity: Related enterprises.
    Properties: equity share, relationship type.
    Relations: investment -> related enterprise, control -> subsidiary.
    Indicators: related party transaction share, related enterprise
                open case ratio, related enterprise execution amount.
    """

    RELATION_TYPE_CHOICES = [
        ('SHAREHOLDER', 'Shareholding (股权投资)'),
        ('BENEFICIAL_OWNER', 'Beneficial Ownership (受益所有)'),
        ('DIRECTOR', 'Common Director/Officer (共同董事)'),
        ('LEGAL_REP', 'Common Legal Representative'),
        ('FAMILY', 'Family Relationship'),
        ('GUARANTEE', 'Mutual Guarantee (互保)'),
        ('SUPPLY', 'Supply Relationship'),
        ('CUSTOMER', 'Customer Relationship'),
        ('SUBSIDIARY', 'Subsidiary/Branch'),
        ('ACTUAL_CONTROL', 'Actual Controller'),
    ]

    source = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='outgoing_relationships',
    )
    target = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='incoming_relationships',
    )
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPE_CHOICES)
    equity_ratio = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    confidence_score = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text='Confidence in the relationship, 0-1',
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    properties = models.JSONField(default=dict, blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('source', 'target', 'relation_type')
        indexes = [
            models.Index(fields=['source', 'relation_type']),
            models.Index(fields=['target', 'relation_type']),
        ]
        verbose_name = 'Enterprise Relationship'

    def __str__(self):
        return f"{self.source.name} --[{self.get_relation_type_display()}]--> {self.target.name}"


class SupplyChainLink(models.Model):
    """
    Supply chain link edges - connecting upstream suppliers to
    downstream buyers through the core enterprise.
    """

    LINK_TYPE_CHOICES = [
        ('RAW_MATERIAL', 'Raw Material Supply'),
        ('COMPONENT', 'Component Supply'),
        ('FINISHED_GOODS', 'Finished Goods'),
        ('SERVICE', 'Service Provision'),
        ('LOGISTICS', 'Logistics/Transport'),
        ('DISTRIBUTION', 'Distribution/Sales'),
    ]

    upstream = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='downstream_links',
    )
    downstream = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='upstream_links',
    )
    link_type = models.CharField(max_length=16, choices=LINK_TYPE_CHOICES)
    # Core enterprise that anchors this supply chain
    core_enterprise = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE,
        related_name='supply_chain_links', null=True, blank=True,
    )
    annual_volume = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
    )
    volume_share = models.FloatField(
        null=True, blank=True,
        help_text='Share of total volume this link represents',
    )
    cooperation_start_date = models.DateField(null=True, blank=True)
    contract_duration_months = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    stability_score = models.FloatField(null=True, blank=True)
    properties = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['upstream', 'link_type']),
            models.Index(fields=['downstream', 'link_type']),
            models.Index(fields=['core_enterprise']),
        ]
        verbose_name = 'Supply Chain Link'

    def __str__(self):
        return f"{self.upstream.name} --[{self.get_link_type_display()}]--> {self.downstream.name}"


class TransactionEdge(models.Model):
    """
    Financial transaction edges - actual money/goods flows
    between enterprises, providing evidence for relationship inference.
    """

    TRANSACTION_TYPE_CHOICES = [
        ('PAYMENT', 'Payment'),
        ('INVOICE', 'Invoice'),
        ('BILL', 'Bill/Note'),
        ('ORDER', 'Purchase Order'),
        ('DELIVERY', 'Goods Delivery'),
        ('RETURN', 'Return/Refund'),
        ('GUARANTEE', 'Guarantee'),
        ('LOAN', 'Loan'),
    ]

    from_enterprise = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='outgoing_transactions',
    )
    to_enterprise = models.ForeignKey(
        'Enterprise', on_delete=models.CASCADE, related_name='incoming_transactions',
    )
    transaction_type = models.CharField(max_length=16, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=3, default='CNY')
    transaction_date = models.DateField()
    reference_number = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    # Links to source documents
    invoice_reference = models.CharField(max_length=128, blank=True)
    order_reference = models.CharField(max_length=128, blank=True)
    properties = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['from_enterprise', 'transaction_type']),
            models.Index(fields=['to_enterprise', 'transaction_type']),
            models.Index(fields=['transaction_date']),
        ]
        verbose_name = 'Transaction Edge'

    def __str__(self):
        return (
            f"{self.from_enterprise.name} --[{self.get_transaction_type_display()} "
            f"¥{self.amount}]--> {self.to_enterprise.name}"
        )
