"""
Palantir Foundry-style Ontology Model Definitions.

Implements the core ontology primitives:
- ObjectType: Defines categories of real-world objects (enterprises, invoices, etc.)
- PropertyType: Defines attributes on object types
- LinkType: Defines typed relationships between object types
- ActionType: Defines operations that can be performed on object types

This mirrors Palantir's Ontology SDK where everything in the data universe
is modeled as typed objects with typed links between them.
"""

from django.db import models
from django.core.validators import RegexValidator


class ObjectType(models.Model):
    """
    A type definition in the ontology, analogous to Palantir's Object Type.
    Each ObjectType represents a class of real-world entities
    (e.g., CoreEnterprise, Invoice, CreditReport).
    """

    CATEGORY_CHOICES = [
        ('ENTITY', 'Business Entity'),
        ('DATA_SOURCE', 'Data Source'),
        ('INDICATOR', 'Risk Indicator'),
        ('EVENT', 'Business Event'),
        ('DOCUMENT', 'Document'),
        ('PRODUCT', 'Product/Service'),
    ]

    name = models.CharField(max_length=128, unique=True)
    display_name = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    icon = models.CharField(max_length=64, blank=True)
    # JSON schema defining the expected shape of instances
    schema_definition = models.JSONField(default=dict, blank=True)
    # Palantir-style: primary key property for this type
    primary_key_property = models.CharField(max_length=128, default='id')
    # Title property used for display
    title_property = models.CharField(max_length=128, default='name')
    is_abstract = models.BooleanField(default=False)
    parent_type = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='child_types',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Object Type'

    def __str__(self):
        return f"{self.display_name} ({self.category})"

    def get_all_properties(self):
        """Get properties including inherited ones from parent types."""
        props = list(self.properties.all())
        if self.parent_type:
            props.extend(self.parent_type.get_all_properties())
        return props

    def get_outgoing_links(self):
        return self.outgoing_link_types.all()

    def get_incoming_links(self):
        return self.incoming_link_types.all()


class PropertyType(models.Model):
    """
    A property definition on an ObjectType, analogous to Palantir's Property Type.
    Defines the schema of individual fields on objects.
    """

    DATA_TYPE_CHOICES = [
        ('STRING', 'String'),
        ('INTEGER', 'Integer'),
        ('FLOAT', 'Float'),
        ('DECIMAL', 'Decimal'),
        ('BOOLEAN', 'Boolean'),
        ('DATE', 'Date'),
        ('DATETIME', 'DateTime'),
        ('JSON', 'JSON Object'),
        ('ARRAY', 'Array'),
        ('GEOLOCATION', 'Geolocation'),
        ('CURRENCY', 'Currency Amount'),
        ('PERCENTAGE', 'Percentage'),
        ('ENUM', 'Enumeration'),
    ]

    object_type = models.ForeignKey(
        ObjectType, on_delete=models.CASCADE, related_name='properties',
    )
    name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    data_type = models.CharField(max_length=32, choices=DATA_TYPE_CHOICES)
    is_required = models.BooleanField(default=False)
    is_indexed = models.BooleanField(default=False)
    is_searchable = models.BooleanField(default=False)
    default_value = models.JSONField(null=True, blank=True)
    # For ENUM type: list of allowed values
    enum_values = models.JSONField(null=True, blank=True)
    # Validation constraints
    validation_rules = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('object_type', 'name')
        ordering = ['object_type', 'name']
        verbose_name = 'Property Type'

    def __str__(self):
        return f"{self.object_type.name}.{self.name} ({self.data_type})"


class LinkType(models.Model):
    """
    A relationship type between two ObjectTypes, analogous to Palantir's Link Type.
    Defines typed, directed edges in the ontology graph.
    """

    CARDINALITY_CHOICES = [
        ('ONE_TO_ONE', 'One to One'),
        ('ONE_TO_MANY', 'One to Many'),
        ('MANY_TO_ONE', 'Many to One'),
        ('MANY_TO_MANY', 'Many to Many'),
    ]

    name = models.CharField(max_length=128, unique=True)
    display_name = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    source_type = models.ForeignKey(
        ObjectType, on_delete=models.CASCADE, related_name='outgoing_link_types',
    )
    target_type = models.ForeignKey(
        ObjectType, on_delete=models.CASCADE, related_name='incoming_link_types',
    )
    cardinality = models.CharField(max_length=16, choices=CARDINALITY_CHOICES)
    # Inverse link name (e.g., "supplies" <-> "supplied_by")
    inverse_name = models.CharField(max_length=128, blank=True)
    # Properties carried on the link itself (edge properties)
    edge_properties = models.JSONField(default=dict, blank=True)
    is_directed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Link Type'

    def __str__(self):
        return f"{self.source_type.name} --[{self.name}]--> {self.target_type.name}"


class ActionType(models.Model):
    """
    An action that can be performed on an ObjectType, analogous to Palantir's Action Type.
    Defines mutations/operations within the ontology (e.g., 'assess_risk', 'flag_fraud').
    """

    ACTION_TRIGGER_CHOICES = [
        ('MANUAL', 'Manual Trigger'),
        ('SCHEDULED', 'Scheduled'),
        ('EVENT_DRIVEN', 'Event Driven'),
        ('THRESHOLD', 'Threshold Based'),
    ]

    name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    object_type = models.ForeignKey(
        ObjectType, on_delete=models.CASCADE, related_name='actions',
    )
    # Parameters the action accepts
    parameter_schema = models.JSONField(default=dict, blank=True)
    # Logic definition: rules to execute
    logic_definition = models.JSONField(default=dict, blank=True)
    trigger_type = models.CharField(
        max_length=16, choices=ACTION_TRIGGER_CHOICES, default='MANUAL',
    )
    # Side effects: what the action modifies
    side_effects = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('object_type', 'name')
        verbose_name = 'Action Type'

    def __str__(self):
        return f"{self.object_type.name}.{self.name}"
